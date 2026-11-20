"""Closed host transport and pipe routing, with no live model or container daemon."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import httpx2
import pytest
from scripts import reach_operator as operator
from scripts import reach_operator_transport as transport
from scripts.reach_model_broker import OperatorModelBroker, validate_endpoint

from lychd.compositions.reach.operator_model_wire import (
    MAX_MODEL_PAYLOAD_BYTES,
    OperatorConversationProfile,
    OperatorModelRequest,
    canonical_json,
)
from lychd.compositions.reach.operator_trace import ReachTraceEvent, trace_bytes


def profile() -> OperatorConversationProfile:
    return OperatorConversationProfile(
        animator_id="night-qwen38",
        model_id="Qwen3.8-27B",
        persona_name="Fixture",
        persona_instructions="Answer plainly.",
    )


def request(operation: Literal["probe", "generate"] = "generate", **changes: Any) -> OperatorModelRequest:
    selected = profile()
    body: dict[str, Any] = {
        "model": selected.model_id,
        "messages": [{"role": "system", "content": "Answer plainly."}, {"role": "user", "content": "Hello"}],
        "max_tokens": selected.max_tokens,
        "temperature": selected.temperature,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    body.update(changes)
    return OperatorModelRequest(
        call_id=str(uuid4()),
        binding_digest=selected.digest,
        operation=operation,
        payload_json="{}" if operation == "probe" else canonical_json(body),
    )


def completion(**changes: Any) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": "Hello back"}
    message.update(changes)
    return {"model": "Qwen3.8-27B", "choices": [{"message": message, "finish_reason": "stop"}]}


@pytest.mark.asyncio
async def test_fresh_probe_exact_model_and_one_closed_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://foreign.invalid")
    observed: list[httpx2.Request] = []

    def handle(value: httpx2.Request) -> httpx2.Response:
        observed.append(value)
        assert str(value.url).startswith("http://127.0.0.1:28000/")
        assert "authorization" not in value.headers
        if value.url.path == "/health":
            return httpx2.Response(200, json={"status": "ok"})
        if value.url.path == "/v1/models":
            return httpx2.Response(200, json={"data": [{"id": "Qwen3.8-27B"}]})
        assert value.method == "POST"
        assert value.url.path == "/v1/chat/completions"
        body = json.loads(value.content)
        assert set(body) == {"model", "messages", "max_tokens", "temperature", "stream"}
        return httpx2.Response(200, json=completion())

    broker = OperatorModelBroker(profile(), endpoint="http://127.0.0.1:28000", transport=httpx2.MockTransport(handle))
    for _ in range(2):
        result = await broker.handle(request("probe"))
        assert result.status == "ok"
        assert json.loads(result.payload_json) == {"healthy": True, "model_ids": ["Qwen3.8-27B"]}
    result = await broker.handle(request())
    assert result.status == "ok"
    assert json.loads(result.payload_json)["choices"][0]["message"]["content"] == "Hello back"
    assert [item.url.path for item in observed] == [
        "/health",
        "/v1/models",
        "/health",
        "/v1/models",
        "/v1/chat/completions",
    ]


@pytest.mark.parametrize(
    "changes", [{"model": "other"}, {"tools": []}, {"headers": {"X-Test": "bad"}}, {"max_tokens": 2048}]
)
@pytest.mark.asyncio
async def test_forbidden_generation_fields_never_reach_http(changes: dict[str, Any]) -> None:
    def handle(_value: httpx2.Request) -> httpx2.Response:
        pytest.fail("Unadmitted payload reached HTTP")

    broker = OperatorModelBroker(profile(), endpoint="http://127.0.0.1:28000", transport=httpx2.MockTransport(handle))
    result = await broker.handle(request(**changes))
    assert result.status == "error"
    assert result.reason == "model_protocol"
    assert result.payload_json == "{}"


@pytest.mark.parametrize("scenario", ["redirect", "wrong_model", "oversized", "tool_calls", "timeout"])
@pytest.mark.asyncio
async def test_foreign_failure_is_bounded_content_free_and_never_retried(scenario: str) -> None:
    calls = 0

    def handle(value: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if scenario == "redirect":
            return httpx2.Response(307, headers={"Location": "http://foreign.invalid"})
        if scenario == "timeout":
            message = "private foreign diagnostic"
            raise httpx2.ReadTimeout(message, request=value)
        if scenario == "oversized":
            return httpx2.Response(200, content=b"x" * (MAX_MODEL_PAYLOAD_BYTES + 1))
        body = completion(tool_calls=[{"function": {"name": "unsafe"}}]) if scenario == "tool_calls" else completion()
        if scenario == "wrong_model":
            body["model"] = "other"
        return httpx2.Response(200, json=body)

    result = await OperatorModelBroker(
        profile(), endpoint="http://127.0.0.1:28000", transport=httpx2.MockTransport(handle)
    ).handle(request())
    assert calls == 1
    assert result.status in {"unavailable", "error"}
    assert result.payload_json == "{}"
    assert "private" not in result.model_dump_json()


@pytest.mark.asyncio
async def test_cancellation_joins_http_and_releases_single_outstanding_slot() -> None:
    entered, settled = asyncio.Event(), asyncio.Event()

    async def handle(_value: httpx2.Request) -> httpx2.Response:
        if settled.is_set():
            return httpx2.Response(200, json=completion())
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            settled.set()
        return httpx2.Response(200, json=completion())

    broker = OperatorModelBroker(profile(), endpoint="http://127.0.0.1:28000", transport=httpx2.MockTransport(handle))
    task = asyncio.create_task(broker.handle(request()))
    await entered.wait()
    with pytest.raises(ValueError, match="model_binding"):
        await broker.handle(request())
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert settled.is_set()
    resumed = await broker.handle(request())
    assert resumed.status == "ok"


@pytest.mark.asyncio
async def test_source_authority_callback_crosses_transport_as_non_wire_state() -> None:
    phases: list[str] = []

    def authorize() -> None:
        phases.append("authorize")

    def handle(value: httpx2.Request) -> httpx2.Response:
        phases.append("http")
        assert value.extensions["lychd_research_authorize"] is authorize
        assert all("research" not in name for name in value.headers)
        body = json.loads(value.content)
        assert set(body) == {"model", "messages", "max_tokens", "temperature", "stream", "chat_template_kwargs"}
        assert body["chat_template_kwargs"] == {"enable_thinking": False}
        assert "lychd_research_authorize" not in value.content.decode()
        return httpx2.Response(200, json=completion())

    broker = OperatorModelBroker(
        profile(), endpoint="http://127.0.0.1:28000", transport=httpx2.MockTransport(handle), vllm_options=True
    )
    result = await broker.handle(request(), authorize=authorize)
    assert result.status == "ok"
    assert phases.count("http") == 1
    assert phases[0] == phases[-1] == "authorize"
    assert phases.index("http") > 0
    assert phases.index("http") < len(phases) - 1


@pytest.mark.asyncio
async def test_revoked_source_authority_refuses_before_http() -> None:
    observed: list[httpx2.Request] = []

    def authorize() -> None:
        message = "research_consume"
        raise ValueError(message)

    def handle(value: httpx2.Request) -> httpx2.Response:
        observed.append(value)
        return httpx2.Response(200, json=completion())

    result = await OperatorModelBroker(
        profile(), endpoint="http://127.0.0.1:28000", transport=httpx2.MockTransport(handle)
    ).handle(request(), authorize=authorize)
    assert observed == []
    assert result.status == "error"
    assert result.reason == "model_protocol"
    assert result.payload_json == "{}"


@pytest.mark.asyncio
async def test_revocation_while_awaiting_response_blocks_source_result_adoption() -> None:
    entered, release_response = asyncio.Event(), asyncio.Event()
    current = True
    checked: list[bool] = []
    requests = 0
    provider_answer = "source-derived result that must remain unadopted"

    def authorize() -> None:
        checked.append(current)
        if not current:
            message = "research_consume"
            raise ValueError(message)

    async def handle(value: httpx2.Request) -> httpx2.Response:
        nonlocal requests
        requests += 1
        assert value.extensions["lychd_research_authorize"] is authorize
        entered.set()
        await release_response.wait()
        return httpx2.Response(200, json=completion(content=provider_answer))

    broker = OperatorModelBroker(profile(), endpoint="http://127.0.0.1:28000", transport=httpx2.MockTransport(handle))
    frame = request()
    task = asyncio.create_task(broker.handle(frame, authorize=authorize))
    async with asyncio.timeout(3):
        await entered.wait()
        assert checked
        assert all(checked)
        current = False
        release_response.set()
        result = await task
    assert requests == 1
    assert checked[-1] is False
    assert result.call_id == frame.call_id
    assert result.binding_digest == frame.binding_digest
    assert result.status == "error"
    assert result.reason == "model_protocol"
    assert result.payload_json == "{}"
    assert provider_answer not in result.model_dump_json()
    current = True
    reauthorized = await broker.handle(request(), authorize=authorize)
    assert reauthorized.status == "ok"
    assert requests == 2


@pytest.mark.parametrize(("operation", "profile_timeout", "expected_budget"), [("generate", 5, 5), ("probe", 60, 5)])
@pytest.mark.asyncio
async def test_profile_deadline_and_probe_cap_retire_http_before_response(
    monkeypatch: pytest.MonkeyPatch,
    operation: Literal["probe", "generate"],
    profile_timeout: int,
    expected_budget: int,
) -> None:
    observed: list[int] = []
    settled = asyncio.Event()
    original_timeout = asyncio.timeout

    @asynccontextmanager
    async def immediate_timeout(delay: int) -> AsyncGenerator[None]:
        observed.append(delay)
        async with original_timeout(0):
            yield

    async def handle(value: httpx2.Request) -> httpx2.Response:
        assert value.extensions["timeout"] == dict.fromkeys(("connect", "read", "write", "pool"), expected_budget)
        try:
            await asyncio.Event().wait()
        finally:
            settled.set()
        return httpx2.Response(200, json=completion())

    selected = profile().model_copy(update={"timeout_seconds": profile_timeout})
    frame = request(operation).model_copy(update={"binding_digest": selected.digest})
    monkeypatch.setattr("scripts.reach_model_broker.asyncio.timeout", immediate_timeout)
    response = await OperatorModelBroker(
        selected, endpoint="http://127.0.0.1:28000", transport=httpx2.MockTransport(handle)
    ).handle(frame)
    assert observed == [expected_budget]
    assert settled.is_set()
    assert response.status == "unavailable"
    assert response.reason == "model_timeout"


class Writer:
    def __init__(self) -> None:
        self.raw = bytearray()

    def write(self, raw: bytes) -> None:
        self.raw.extend(raw)

    async def drain(self) -> None:
        return


@pytest.mark.asyncio
async def test_multiplexer_keeps_model_payload_off_discord_pipe_and_refuses_unknown_frames() -> None:
    model_call = request()
    reader = asyncio.StreamReader(limit=operator.WIRE_LIMIT)
    reader.feed_data(b'{"kind":"ready"}\n' + model_call.model_dump_json().encode() + b'\n{"kind":"result"}\n')
    reader.feed_eof()
    edge, core = Writer(), Writer()
    broker = OperatorModelBroker(
        profile(),
        endpoint="http://127.0.0.1:28000",
        transport=httpx2.MockTransport(lambda _value: httpx2.Response(200, json=completion())),
    )
    await transport.model_relay(reader, edge, core, broker)  # type: ignore[arg-type] - write-only pipe fixtures
    assert edge.raw == b'{"kind":"ready"}\n{"kind":"result"}\n'
    response = json.loads(core.raw)
    assert response["kind"] == "model_response"
    assert response["call_id"] == model_call.call_id
    reader = asyncio.StreamReader()
    reader.feed_data(b'{"kind":"execute"}\n')
    reader.feed_eof()
    with pytest.raises(ValueError, match="operator_core_frame"):
        await transport.model_relay(reader, edge, core, broker)  # type: ignore[arg-type] - write-only pipe fixtures


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://localhost:28000",
        "http://127.0.0.1:28000/",
        "http://127.0.0.1:28000?q=1",
        "http://127.0.0.1",
        "http://127.0.0.1:0",
        "http://127.0.0.1:28000/v1",
        "http://10.0.0.5:28000",
        "http://user:pass@127.0.0.1:28000",
        "https://gateway.example",
        "https://gateway.example:8443/zen/go",
        "https://user:pass@gateway.example",
        "https://gateway.example/",
        "https://gateway.example/v1?q=1",
        "https://gateway.example#fragment",
        "ftp://gateway.example",
    ],
)
def test_endpoint_refuses_plain_remote_http_credentials_and_url_state(endpoint: str) -> None:
    with pytest.raises(ValueError, match="model_endpoint"):
        validate_endpoint(endpoint)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://127.0.0.1:28000",
        "http://127.0.0.1:9000",
        "http://[::1]:28000",
    ],
)
def test_endpoint_admits_exact_loopback_http(endpoint: str) -> None:
    assert validate_endpoint(endpoint) == endpoint


@pytest.mark.asyncio
@pytest.mark.parametrize("reported", ["other-model", "vendor/other", "", None])
async def test_completion_from_a_different_model_is_still_refused(reported: object) -> None:
    def handle(value: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=completion() | {"model": reported})

    result = await OperatorModelBroker(
        profile(), endpoint="http://127.0.0.1:28000", transport=httpx2.MockTransport(handle)
    ).handle(request())
    assert (result.status, result.reason) == ("error", "model_protocol")


def test_profile_is_frozen_worker_only_and_publication_mount_is_edge_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.unit.cli.test_reach_operator import files

    policy, token, images, state = files(tmp_path)

    def resolve_route(_selected: OperatorConversationProfile, *, podman: bool) -> operator.ModelRoute:
        assert not podman
        return operator.ModelRoute("http://127.0.0.1:28000", None)

    monkeypatch.setattr(operator, "resolve_model_route", resolve_route)
    selected = tmp_path / "conversation.json"
    operator.write_private(selected, profile().model_dump_json().encode())
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "manifest.json").write_text("{}")
    publications = tmp_path / "publications"
    observed: list[list[str]] = []
    original = operator.read_regular

    def read(path: Path, limit: int, *, private: bool = False) -> bytes:
        assert path != token
        return original(path, limit, private=private)

    async def supervise(
        _engine: str,
        commands: tuple[list[str], list[str]],
        _ids: tuple[Path, Path],
        *,
        broker: OperatorModelBroker,
        read_identity: object,
        research_broker: object | None = None,
        capture: object | None = None,
    ) -> int:
        assert capture is not None
        assert research_broker is None
        observed.extend(commands)
        core, edge = commands
        mount = next(item for item in core if ":/run/reach/conversation.json:ro" in item)
        frozen = Path(mount.split(":", 1)[0])
        assert frozen != selected
        assert await asyncio.to_thread(frozen.read_bytes) == profile().model_dump_json().encode()
        metadata = await asyncio.to_thread(frozen.stat)
        assert metadata.st_mode & 0o777 == 0o600
        assert broker.profile.digest == profile().digest
        assert str(selected) not in " ".join(core + edge)
        assert "conversation.json" not in " ".join(edge)
        return 0

    monkeypatch.setattr(operator, "read_regular", read)
    monkeypatch.setattr(operator, "supervise", supervise)
    args = operator.parser().parse_args(
        [
            "run",
            "--policy",
            str(policy),
            "--token-file",
            str(token),
            "--images",
            str(images),
            "--state-dir",
            str(state),
            "--corpus-dir",
            str(corpus),
            "--conversation-profile",
            str(selected),
            "--publications-dir",
            str(publications),
            "--publication-channel",
            "104",
            "--command-name",
            "nadir",
        ]
    )
    assert operator.run_containers(args) == 0
    core, edge = observed
    assert "--network=none" in core
    assert "--conversation-profile" in core
    assert "--conversation" in edge
    assert str(publications) not in " ".join(core)
    assert f"{publications}:/state/publications:rw,Z" in edge
    assert "--publication-channel" in edge
    assert edge[edge.index("--command-name") + 1] == "nadir"


@pytest.mark.parametrize(
    "frame", [b'{"kind":"model_response"}\n', b'{"kind":"model_request"}\n', b'{"kind":"request"}\n']
)
@pytest.mark.asyncio
async def test_conversation_edge_cannot_inject_model_frames_or_invalid_requests(frame: bytes) -> None:
    reader = asyncio.StreamReader(limit=operator.WIRE_LIMIT)
    reader.feed_data(frame)
    reader.feed_eof()
    core = Writer()
    with pytest.raises(ValueError, match="validation error"):
        await transport.relay(reader, core, requests_only=True)  # type: ignore[arg-type] - write-only pipe fixture
    assert core.raw == b""


@pytest.mark.parametrize(
    ("finish", "content", "finish_state", "content_state", "status"),
    [
        ("stop", "answer", "stop", "text", "ok"),
        ("length", "answer", "length", "text", "ok"),
        ("tool_calls", "answer", "tool_calls", "text", "error"),
        ("function_call", "answer", "function_call", "text", "error"),
        ("content_filter", "", "content_filter", "empty", "ok"),
        (None, " \t", "null", "blank", "ok"),
        ("PRIVATE_UNKNOWN_FINISH", None, "other", "null", "error"),
        (123, {"PRIVATE_BODY": "secret"}, "other", "non_string", "error"),
    ],
)
@pytest.mark.asyncio
async def test_completion_diagnostics_are_finite_terminal_only_and_do_not_change_control(
    finish: object, content: object, finish_state: str, content_state: str, status: str
) -> None:
    records: list[ReachTraceEvent] = []
    value = completion(content=content)
    value["choices"][0]["finish_reason"] = finish
    broker = OperatorModelBroker(
        profile(),
        endpoint="http://127.0.0.1:28000",
        transport=httpx2.MockTransport(lambda _request: httpx2.Response(200, json=value)),
        trace=records.append,
    )
    result = await broker.handle(request())
    assert result.status == status
    terminal = records[-1]
    assert terminal.name == "model_call"
    assert terminal.completion_finish_reason == finish_state
    assert terminal.content_state == content_state
    assert all(event.completion_finish_reason is None and event.content_state is None for event in records[:-1])
    assert "PRIVATE" not in b"".join(trace_bytes(event) for event in records).decode()


@pytest.mark.asyncio
async def test_missing_completion_fields_and_unobserved_next_call_do_not_leak_metadata() -> None:
    records: list[ReachTraceEvent] = []
    value = completion()
    del value["choices"][0]["finish_reason"]
    del value["choices"][0]["message"]["content"]
    calls = 0

    def handle(_request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(200, json=value) if calls == 1 else httpx2.Response(200, content=b"not JSON")

    broker = OperatorModelBroker(
        profile(), endpoint="http://127.0.0.1:28000", transport=httpx2.MockTransport(handle), trace=records.append
    )
    assert (await broker.handle(request())).reason == "model_protocol"
    assert records[-1].completion_finish_reason == "missing"
    assert records[-1].content_state == "missing"
    assert (await broker.handle(request())).reason == "model_protocol"
    assert records[-1].completion_finish_reason is None
    assert records[-1].content_state is None
    assert calls == 2


@pytest.mark.asyncio
async def test_probe_has_no_provider_completion_observation() -> None:
    records: list[ReachTraceEvent] = []

    def handle(value: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200, json={"status": "ok"} if value.url.path == "/health" else {"data": [{"id": profile().model_id}]}
        )

    result = await OperatorModelBroker(
        profile(), endpoint="http://127.0.0.1:28000", transport=httpx2.MockTransport(handle), trace=records.append
    ).handle(request("probe"))
    assert result.status == "ok"
    assert all(event.completion_finish_reason is None and event.content_state is None for event in records)


@pytest.fixture
def local_codex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from lychd.config.settings import root as settings
    from lychd.system import constants

    codex = tmp_path / "codex"
    runes = codex / "runes"
    leaf = runes / "animator" / "soulstones" / "llamacpp"
    leaf.mkdir(parents=True)
    config = codex / "lychd.toml"
    config.write_text('[extensions]\nbuiltins = ["animator/llamacpp"]\n')
    monkeypatch.setattr(settings, "PATH_LYCHD_TOML", config)
    monkeypatch.setattr(settings, "get_settings", settings.Settings)
    monkeypatch.setattr(constants, "PATH_RUNES_DIR", runes)
    rune = leaf / "other.toml"
    rune.write_text(
        """name = "other-soulstone"
port = 9192
startup_mode = "single"
model_path = "/models/tiny.gguf"
served_model_id = "vendor/tiny"
n_gpu_layers = 0

[[models]]
id = "vendor/tiny"
path = "/models/tiny.gguf"

[models.capabilities]
families = ["chat"]
"""
    )
    return rune


def test_route_reads_actual_codex_and_uses_exact_declared_port_and_podman_target(local_codex: Path) -> None:
    selected = profile().model_copy(update={"animator_id": "other-soulstone", "model_id": "vendor/tiny"})
    assert operator.resolve_model_route(selected, podman=False) == operator.ModelRoute("http://127.0.0.1:9192", None)
    route = operator.resolve_model_route(selected, podman=True)
    assert route.endpoint == "http://127.0.0.1:9192"
    assert route.transport is not None
    assert not route.vllm_options


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"animator_id": "another-soulstone"}, "selected local Soulstone"),
        ({"model_id": "tiny"}, "exact Chat Completions model"),
        ({"model_id": "vendor/something-else"}, "exact Chat Completions model"),
    ],
)
def test_route_never_substitutes_missing_soulstone_or_model(
    local_codex: Path, change: dict[str, str], error: str
) -> None:
    selected = profile().model_copy(update={"animator_id": "other-soulstone", "model_id": "vendor/tiny"} | change)
    with pytest.raises(operator.ModelSelectionError, match=error):
        operator.resolve_model_route(selected, podman=True)


def test_ipv6_soulstone_remains_available_to_host_but_podman_refuses_at_configuration(local_codex: Path) -> None:
    local_codex.write_text('base_url = "http://[::1]:9192/v1"\n' + local_codex.read_text())
    selected = profile().model_copy(update={"animator_id": "other-soulstone", "model_id": "vendor/tiny"})
    assert operator.resolve_model_route(selected, podman=False) == operator.ModelRoute("http://[::1]:9192", None)
    with pytest.raises(operator.ModelSelectionError, match="requires IPv4 loopback"):
        operator.resolve_model_route(selected, podman=True)


@pytest.mark.parametrize("missing", ["animator_id", "model_id"])
def test_old_conversation_profiles_fail_with_actionable_selection_message(missing: str) -> None:
    values = profile().model_dump(mode="json", exclude={missing})
    with pytest.raises(operator.ModelSelectionError, match="requires explicit animator_id and model_id"):
        operator.load_conversation_profile(json.dumps(values).encode())


def test_router_is_refused_before_an_unloaded_model_can_be_requested(local_codex: Path) -> None:
    local_codex.write_text(
        local_codex.read_text().replace('startup_mode = "single"', 'startup_mode = "router"\nmodels_dir = "/models"')
    )
    selected = profile().model_copy(update={"animator_id": "other-soulstone", "model_id": "vendor/tiny"})
    with pytest.raises(operator.ModelSelectionError, match="exact static text Chat model"):
        operator.resolve_model_route(selected, podman=True)


def test_responses_surface_is_not_substituted_with_chat_completions(local_codex: Path) -> None:
    local_codex.write_text(local_codex.read_text() + 'surface = "responses"\n')
    selected = profile().model_copy(update={"animator_id": "other-soulstone", "model_id": "vendor/tiny"})
    with pytest.raises(operator.ModelSelectionError, match="exact Chat Completions model"):
        operator.resolve_model_route(selected, podman=True)


@pytest.mark.asyncio
async def test_local_completion_never_accepts_model_suffix() -> None:
    selected = profile().model_copy(update={"model_id": "vendor/tiny"})
    payload = json.loads(request().payload_json) | {"model": selected.model_id}
    frame = request().model_copy(update={"binding_digest": selected.digest, "payload_json": canonical_json(payload)})
    broker = OperatorModelBroker(
        selected,
        endpoint="http://127.0.0.1:9192",
        transport=httpx2.MockTransport(lambda _: httpx2.Response(200, json=completion() | {"model": "tiny"})),
    )
    result = await broker.handle(frame)
    assert (result.status, result.reason) == ("error", "model_protocol")


def test_non_vllm_route_refuses_the_vllm_options(local_codex: Path) -> None:
    selected = profile().model_copy(
        update={"animator_id": "other-soulstone", "model_id": "vendor/tiny", "enable_thinking": True}
    )
    with pytest.raises(operator.ModelSelectionError, match="require a compatible vLLM Soulstone"):
        operator.resolve_model_route(selected, podman=False)


def test_host_loads_serialized_profile_with_strict_nested_tuples() -> None:
    values = profile().model_dump(mode="json")
    values.update(
        adaptive_context=True,
        json_object_output=True,
        thinking_phases=["planning"],
    )
    loaded = operator.load_conversation_profile(json.dumps(values).encode())
    assert loaded.thinking_phases == ("planning",)
    assert operator.load_conversation_profile(loaded.model_dump_json().encode()) == loaded
