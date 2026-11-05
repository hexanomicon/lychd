"""Configured embedding execution through registry, Dispatcher and bounded HTTP."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from hashlib import sha256
from typing import Any

import httpx
import httpx2
import pytest
import respx
from pydantic import ValidationError

from lychd.config import QuadletConfig
from lychd.domain.animation.embeddings import (
    EmbeddingBinding,
    EmbeddingGrant,
    EmbeddingInput,
    EmbeddingOperation,
    EmbeddingRefused,
    embedding_vector_digest,
)
from lychd.domain.animation.errors import CapabilityUnavailable, HardwareTransitionRequired
from lychd.domain.animation.services.declarations import AnimatorDeclarations
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.leases import LeaseLedger
from lychd.extensions.builtin.animator.llamacpp.embedding_profile import IMAGE, PROFILE
from lychd.extensions.builtin.animator.runtimes.llamacpp import LlamaCppRuntimeAdapter
from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppSoulstoneConfig

pytestmark = pytest.mark.httpx2(assert_all_called=False)


def stone(**updates: object) -> LlamaCppSoulstoneConfig:
    values: dict[str, object] = {
        "name": "embedding",
        "port": 8080,
        "base_url": "http://127.0.0.1:8080/v1",
        "embedding_profile": PROFILE.profile_id,
        "model_path": "/models/embedding.gguf",
        "quadlet": {"image": IMAGE},
    }
    values.update(updates)
    return LlamaCppSoulstoneConfig.model_validate(values)


def setup(httpx2_mock: respx.MockRouter) -> tuple[AnimatorRegistry, Dispatcher, LeaseLedger, EmbeddingBinding]:
    httpx2_mock.get("http://127.0.0.1:8080/health").respond(200, json={"status": "ok"})
    httpx2_mock.get("http://127.0.0.1:8080/v1/models").respond(200, json={"data": [{"id": PROFILE.model_id}]})
    registry = AnimatorRegistry(
        declarations=AnimatorDeclarations(soulstones=(stone(),), portals=()),
        runtime_adapters=(LlamaCppRuntimeAdapter(),),
    )
    registry.load()
    ledger = LeaseLedger()
    binding = EmbeddingBinding(capability_key=registry.list_capabilities()[0].key, profile_digest=PROFILE.digest)
    return registry, Dispatcher(registry, leases=ledger), ledger, binding


@pytest.mark.asyncio
async def test_fresh_registry_admits_binding_before_probing(httpx2_mock: respx.MockRouter) -> None:
    health = httpx2_mock.get("http://127.0.0.1:8080/health").respond(200, json={"status": "ok"})
    models = httpx2_mock.get("http://127.0.0.1:8080/v1/models").respond(200, json={"data": [{"id": PROFILE.model_id}]})
    registry = AnimatorRegistry(
        declarations=AnimatorDeclarations(soulstones=(stone(),), portals=()),
        runtime_adapters=(LlamaCppRuntimeAdapter(),),
    )
    binding = EmbeddingBinding(capability_key=f"embedding:embedding:{PROFILE.model_id}", profile_digest=PROFILE.digest)
    with pytest.raises(EmbeddingRefused, match="binding"):
        registry.require_embedding(binding.model_copy(update={"profile_digest": "0" * 64}), "embed_document")
    assert not httpx2_mock.calls
    registry.require_embedding(binding, "embed_document")
    assert not httpx2_mock.calls

    ledger = LeaseLedger()
    async with Dispatcher(registry, leases=ledger).lease_embedding(binding, operation="embed_document", run_id="fresh"):
        assert health.call_count == models.call_count == 1
        assert len(ledger.active()) == 1
    assert not ledger.active()


def item(text: str = "Paris is the capital of France.") -> EmbeddingInput:
    return EmbeddingInput("source:1", sha256(text.encode()).hexdigest(), text)


def response(vector: list[float] | None = None) -> dict[str, object]:
    return {
        "model": PROFILE.model_id,
        "data": [{"index": 0, "embedding": vector or [0.03125] * 1024}],
        "usage": {"prompt_tokens": 3, "total_tokens": 3},
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["embed_document", "embed_query"])
async def test_configured_document_and_query_wire(httpx2_mock: respx.MockRouter, operation: EmbeddingOperation) -> None:
    registry, dispatcher, ledger, binding = setup(httpx2_mock)
    calls: list[dict[str, object]] = []
    checks: list[int] = []

    def receive(request: httpx.Request) -> httpx.Response:
        assert request.headers["accept-encoding"] == "identity"
        assert "authorization" not in request.headers
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"tokens": [1, 2, 3]} if request.url.path == "/tokenize" else response())

    httpx2_mock.post("http://127.0.0.1:8080/tokenize").mock(side_effect=receive)
    httpx2_mock.post("http://127.0.0.1:8080/v1/embeddings").mock(side_effect=receive)
    async with dispatcher.lease_embedding(binding, operation=operation, run_id="test") as grant:
        assert len(ledger.active()) == 1
        batch = await grant.driver.embed((item(),), authorize=lambda: checks.append(len(calls)))
        assert batch.profile_digest == PROFILE.digest
        assert batch.items[0].vector_digest == embedding_vector_digest(batch.items[0].vector)
    assert ledger.active() == []
    assert checks == [0, 1, 2]
    text = (PROFILE.query_prefix if operation == "embed_query" else "") + item().text
    assert calls[0] == {"content": text, "add_special": True, "parse_special": True, "with_pieces": False}
    assert calls[1]["input"] == text
    with pytest.raises(EmbeddingRefused, match="scope"):
        await grant.driver.embed((item(),), authorize=lambda: None)
    with pytest.raises(CapabilityUnavailable, match="metadata"):
        await registry.issue_grant(binding.capability_key, holder="legacy")


@pytest.mark.asyncio
async def test_revocation_after_tokenization_sends_no_embedding(httpx2_mock: respx.MockRouter) -> None:
    _, dispatcher, ledger, binding = setup(httpx2_mock)
    token = httpx2_mock.post("http://127.0.0.1:8080/tokenize").respond(200, json={"tokens": [1, 2, 3]})
    embedding = httpx2_mock.post("http://127.0.0.1:8080/v1/embeddings").respond(200, json=response())

    def authorize() -> None:
        if token.called:
            raise EmbeddingRefused("authority")  # noqa: EM101 - safe code

    with pytest.raises(EmbeddingRefused, match="authority"):
        async with dispatcher.lease_embedding(binding, operation="embed_document", run_id="test") as grant:
            await grant.driver.embed((item(),), authorize=authorize)
    assert not embedding.called
    assert not ledger.active()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["oversize", "compression", "dimension", "norm", "nan", "index", "tokens", "http"])
async def test_bounded_safe_provider_failure(httpx2_mock: respx.MockRouter, kind: str) -> None:
    _, dispatcher, ledger, binding = setup(httpx2_mock)
    httpx2_mock.post("http://127.0.0.1:8080/tokenize").respond(200, json={"tokens": [1, 2, 3]})
    value = response()
    if kind == "dimension":
        value = response([1.0])
    elif kind == "norm":
        value = response([1.0] * 1024)
    elif kind == "nan":
        value = response([float("nan")] * 1024)
    elif kind == "index":
        value["data"] = [{"index": True, "embedding": [0.03125] * 1024}]
    elif kind == "tokens":
        value["usage"] = {"prompt_tokens": 2}
    raw = json.dumps(value).encode()
    if kind == "oversize":
        raw = b"private sentinel" * 5000
    reply = httpx.Response(
        500 if kind == "http" else 200,
        content=raw,
        headers={"Content-Encoding": "unexpected"} if kind == "compression" else {},
    )
    httpx2_mock.post("http://127.0.0.1:8080/v1/embeddings").mock(return_value=reply)
    with pytest.raises(EmbeddingRefused) as error:
        async with dispatcher.lease_embedding(binding, operation="embed_document", run_id="test") as grant:
            await grant.driver.embed((item(),), authorize=lambda: None)
    assert "private sentinel" not in str(error.value)
    assert not ledger.active()


@pytest.mark.asyncio
async def test_limits_before_embedding_and_tampered_binding_before_probe(httpx2_mock: respx.MockRouter) -> None:
    _, dispatcher, _, binding = setup(httpx2_mock)
    httpx2_mock.post("http://127.0.0.1:8080/tokenize").respond(200, json={"tokens": list(range(512))})
    embedding = httpx2_mock.post("http://127.0.0.1:8080/v1/embeddings").respond(200, json=response())
    for inputs in ((item(), item()), (item("x" * 4097),), (EmbeddingInput("a", "0" * 64, "text"),), (item(),)):
        with pytest.raises(EmbeddingRefused):
            async with dispatcher.lease_embedding(binding, operation="embed_document", run_id="bounds") as grant:
                await grant.driver.embed(inputs, authorize=lambda: None)
    assert not embedding.called
    before = len(httpx2_mock.calls)
    with pytest.raises(EmbeddingRefused, match="binding"):
        async with dispatcher.lease_embedding(
            binding.model_copy(update={"profile_digest": "0" * 64}), operation="embed_document", run_id="bad"
        ):
            pytest.fail("tampered binding admitted")
    assert len(httpx2_mock.calls) == before


@pytest.mark.asyncio
async def test_drain_reopen_during_issue_fences_grant(
    httpx2_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, dispatcher, ledger, binding = setup(httpx2_mock)
    issue = registry.issue_embedding_grant

    async def crossed(binding: EmbeddingBinding, *, operation: EmbeddingOperation, holder: str) -> EmbeddingGrant:
        grant = await issue(binding, operation=operation, holder=holder)
        ledger.begin_drain(["embedding"])
        ledger.end_drain(["embedding"])
        return grant

    monkeypatch.setattr(registry, "issue_embedding_grant", crossed)
    with pytest.raises(HardwareTransitionRequired):
        async with dispatcher.lease_embedding(binding, operation="embed_document", run_id="drain"):
            pytest.fail("stale grant admitted")
    assert not ledger.active()


@pytest.mark.asyncio
async def test_scope_exit_cancels_and_joins_escaped_request(httpx2_mock: respx.MockRouter) -> None:
    _, dispatcher, ledger, binding = setup(httpx2_mock)
    entered = asyncio.Event()
    stopped = asyncio.Event()

    async def blocked(request: httpx.Request) -> httpx.Response:
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            assert ledger.active()
            stopped.set()
        return httpx.Response(200, json={"tokens": [1]})

    httpx2_mock.post("http://127.0.0.1:8080/tokenize").mock(side_effect=blocked)
    async with dispatcher.lease_embedding(binding, operation="embed_document", run_id="escape") as grant:
        task = asyncio.create_task(grant.driver.embed((item(),), authorize=lambda: None))
        await asyncio.wait_for(entered.wait(), 1)
    assert stopped.is_set()
    assert task.cancelled()
    assert not ledger.active()


@pytest.mark.parametrize(
    "updates",
    [
        {"quadlet": QuadletConfig(image="mutable:latest")},
        {"base_url": "https://example.com/v1"},
        {"exec": ("--embedding",)},
        {"extra_args": ("--model-url", "https://example.com/model")},
        {"env_vars": {"LLAMA_ARG_MODEL": "other"}},
        {"devices": ("nvidia.com/gpu=all",)},
        {"n_gpu_layers": 1},
        {"models_dir": "/models"},
    ],
)
def test_profile_overrides_refused(updates: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        stone(**updates)


def test_cpu_managed_plan() -> None:
    command = LlamaCppRuntimeAdapter().plan(stone()).exec_args
    assert command[command.index("-ngl") + 1] == "0"
    assert command[command.index("-c") + 1] == "512"
    assert command[command.index("--alias") + 1] == PROFILE.model_id
    assert "--offline" in command
    assert "--embedding" in command


@pytest.mark.asyncio
async def test_recursive_body_and_streaming_error_are_bounded(httpx2_mock: respx.MockRouter) -> None:
    _, dispatcher, ledger, binding = setup(httpx2_mock)
    httpx2_mock.post("http://127.0.0.1:8080/tokenize").respond(200, json={"tokens": [1, 2, 3]})
    closed: list[bool] = []
    yielded: list[int] = []

    class StreamingError(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            for index in range(100):
                yielded.append(index)
                yield b"private sentinel" * 256

        async def aclose(self) -> None:
            closed.append(True)

    route = httpx2_mock.post("http://127.0.0.1:8080/v1/embeddings")
    route.mock(return_value=httpx.Response(500, stream=StreamingError()))
    with pytest.raises(EmbeddingRefused, match="response_size"):
        async with dispatcher.lease_embedding(binding, operation="embed_document", run_id="stream") as grant:
            await grant.driver.embed((item(),), authorize=lambda: None)
    assert closed == [True]
    assert len(yielded) < 20
    assert not ledger.active()
    route.mock(return_value=httpx.Response(200, content=b"[" * 10000 + b"]" * 10000))
    with pytest.raises(EmbeddingRefused, match=r"response_(json|shape)"):
        async with dispatcher.lease_embedding(binding, operation="embed_document", run_id="json") as grant:
            await grant.driver.embed((item(),), authorize=lambda: None)


@pytest.mark.asyncio
async def test_total_deadline_spans_both_requests(
    httpx2_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, dispatcher, ledger, binding = setup(httpx2_mock)
    timeout = asyncio.timeout

    def shortened_timeout(_seconds: float | None) -> asyncio.Timeout:
        return timeout(0.04)

    monkeypatch.setattr("lychd.extensions.builtin.animator.llamacpp.embedding.asyncio.timeout", shortened_timeout)

    async def delayed(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.025)
        return httpx.Response(200, json={"tokens": [1, 2, 3]} if request.url.path == "/tokenize" else response())

    httpx2_mock.post("http://127.0.0.1:8080/tokenize").mock(side_effect=delayed)
    httpx2_mock.post("http://127.0.0.1:8080/v1/embeddings").mock(side_effect=delayed)
    with pytest.raises(EmbeddingRefused, match="transport"):
        async with dispatcher.lease_embedding(binding, operation="embed_document", run_id="deadline") as grant:
            await grant.driver.embed((item(),), authorize=lambda: None)
    assert not ledger.active()


@pytest.mark.asyncio
async def test_interface_tampering_refused_without_probe(httpx2_mock: respx.MockRouter) -> None:
    _, dispatcher, _, binding = setup(httpx2_mock)
    count = len(httpx2_mock.calls)
    with pytest.raises(EmbeddingRefused, match="binding"):
        async with dispatcher.lease_embedding(
            binding.model_copy(update={"interface": "model.chat@1"}), operation="embed_document", run_id="tamper"
        ):
            pytest.fail("tampered interface admitted")
    assert len(httpx2_mock.calls) == count


@pytest.mark.parametrize("updates", [{"port": None}, {"base_url": None}, {"port": 8081}])
def test_profile_requires_usable_explicit_endpoint(updates: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        stone(**updates)


def test_retained_public_manifest_and_float32_digest() -> None:
    import struct
    from pathlib import Path

    from lychd.domain.animation.embeddings import canonical_float32_vector

    receipt = Path(__file__).parents[1] / "fixtures/embeddings/qwen3-06b-q8-b9445.json"
    assert sha256(receipt.read_bytes()).hexdigest() == PROFILE.conformance_digest
    projected = canonical_float32_vector((0.1, -0.0, 0.0))
    assert projected[0] != 0.1
    assert embedding_vector_digest(projected) == sha256(struct.pack("<3f", 0.1, -0.0, 0.0)).hexdigest()


@pytest.mark.asyncio
async def test_repeated_cancellation_keeps_lease_until_wire_stops(httpx2_mock: respx.MockRouter) -> None:
    _, dispatcher, ledger, binding = setup(httpx2_mock)
    entered = asyncio.Event()
    cleanup_started = asyncio.Event()
    finish_cleanup = asyncio.Event()
    tasks: list[asyncio.Task[Any]] = []

    async def blocked(_request: httpx.Request) -> httpx.Response:
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleanup_started.set()
            await finish_cleanup.wait()
        return httpx.Response(200, json={"tokens": [1]})

    httpx2_mock.post("http://127.0.0.1:8080/tokenize").mock(side_effect=blocked)

    async def consume() -> None:
        async with dispatcher.lease_embedding(binding, operation="embed_document", run_id="cancel") as grant:
            tasks.append(asyncio.create_task(grant.driver.embed((item(),), authorize=lambda: None)))
            await asyncio.Event().wait()

    owner = asyncio.create_task(consume())
    try:
        await asyncio.wait_for(entered.wait(), 1)
        owner.cancel()
        await asyncio.wait_for(cleanup_started.wait(), 1)
        owner.cancel()
        await asyncio.sleep(0)
        owner.cancel()
        assert ledger.active()
        finish_cleanup.set()
        with pytest.raises(asyncio.CancelledError):
            await owner
        assert all(task.cancelled() for task in tasks)
        assert not ledger.active()
    finally:
        finish_cleanup.set()
        owner.cancel()
        await asyncio.gather(owner, *tasks, return_exceptions=True)


@pytest.mark.asyncio
async def test_entry_allocation_failure_and_immediate_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    from lychd.extensions.builtin.animator.llamacpp.embedding import LlamaCppEmbeddingDriver

    factory = httpx2.AsyncClient
    clients: list[httpx2.AsyncClient] = []

    def fail(**_kwargs: object) -> httpx2.AsyncClient:
        raise MemoryError

    monkeypatch.setattr("lychd.extensions.builtin.animator.llamacpp.embedding.httpx2.AsyncClient", fail)
    driver = LlamaCppEmbeddingDriver(base_url="http://127.0.0.1:8080/v1", operation="embed_document")
    with pytest.raises(MemoryError):
        await driver.__aenter__()
    await driver.__aexit__(None, None, None)

    def cancelling(**_kwargs: object) -> httpx2.AsyncClient:
        client = factory(trust_env=False)
        clients.append(client)
        current = asyncio.current_task()
        assert current is not None
        current.cancel()
        return client

    monkeypatch.setattr("lychd.extensions.builtin.animator.llamacpp.embedding.httpx2.AsyncClient", cancelling)

    async def consume() -> None:
        async with LlamaCppEmbeddingDriver(base_url="http://127.0.0.1:8080/v1", operation="embed_document"):
            await asyncio.sleep(0)

    with pytest.raises(asyncio.CancelledError):
        await asyncio.create_task(consume())
    assert len(clients) == 1
    assert clients[0].is_closed


def test_tampered_config_refuses_hydration() -> None:
    tampered = stone().model_copy(update={"env_vars": {"LLAMA_ARG_MODEL": "other"}})
    with pytest.raises(EmbeddingRefused, match="profile_overrides"):
        LlamaCppRuntimeAdapter().build_runtime(tampered)


@pytest.mark.parametrize("operation", ["build_runtime", "plan"])
def test_tampered_profile_selector_refuses_hydration_and_planning(operation: str) -> None:
    tampered = stone().model_copy(update={"embedding_profile": "unknown-profile@2"})
    adapter = LlamaCppRuntimeAdapter()
    invoke = adapter.build_runtime if operation == "build_runtime" else adapter.plan
    with pytest.raises(EmbeddingRefused, match="profile_identity"):
        invoke(tampered)
