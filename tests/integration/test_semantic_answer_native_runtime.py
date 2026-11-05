"""Fixed opt-in public semantic answer through the full native application.

Four real embedding operations and one real plain-text Chat POST qualify only
this visible synthetic example. The original nodes, application assembly,
registry, ledger, PostgreSQL queues, worker and Context remain the owners.
The scheduling gate orders source revocation after B's real selection. It does
not supply a result. Root separately admits the fresh warm-service relay and
independently evaluates the generated answer and deterministic empty-recall
outcome against the frozen public oracle. The semantic-answer-v1 outer resource
envelope remains unchanged; generated-answer-and-empty-recall-v2 uses less Chat.
No browser, general quality, crash recovery or all-attempt spend claim follows.
"""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import stat
import sys
import time
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx2
import pytest
from pydantic import SecretStr
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    ThinkingPart,
    UserPromptPart,
)
from pydantic_ai.models import override_allow_model_requests
from scripts.local_model_probe import ProbeProfile

from lychd.agents.services import default_sigil
from lychd.agents.workflows import semantic_chat as semantic_chat_module
from lychd.agents.workflows.semantic_chat import (
    ARCHIVE_ANSWER_PURPOSE,
    BRIDGE_CHAT_SEMANTIC,
    AnswerSemanticNotes,
    RecallSemanticNotes,
    SemanticChatState,
    semantic_recall_request,
)
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import Settings, SettingsSnapshot
from lychd.db.models.archive import ArchiveNote
from lychd.db.models.archive_derivation import ArchiveEmbeddingGeneration, ArchiveNoteEmbedding
from lychd.domain.animation.capabilities import CapabilityGrant
from lychd.domain.animation.embeddings import EmbeddingBinding, embedding_vector_digest
from lychd.domain.animation.schemas import ConcurrencyIntent, GenerationProfile
from lychd.domain.archive import ArchiveProfile, ArchiveRefused, ArchiveSubject, NoteProposal, NoteRecord, text_digest
from lychd.domain.archive.derivation import DerivationReceipt, DerivationRequest, DerivationStatus
from lychd.domain.archive.semantic import SemanticRecallReceipt
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.ledger import DbRunLedger
from lychd.domain.cortex.runs import TERMINAL_STATUSES, RunStatus
from lychd.domain.cortex.substrate import get_run_substrate
from lychd.extensions.builtin.animator.llamacpp.embedding import LlamaCppEmbeddingDriver
from lychd.extensions.builtin.animator.llamacpp.embedding_profile import IMAGE, PROFILE
from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppSoulstoneConfig
from lychd.extensions.builtin.animator.soulstones.vllm import VllmSoulstoneConfig
from lychd.extensions.host import AssembledExtensions
from lychd.extensions.manager import ExtensionManager
from lychd.ghouls.runs import _FAILURE_MESSAGE
from tests.integration import test_local_bridge_runtime as bridge
from tests.integration.test_production_wiring import _csrf_headers
from tests.support import archive_semantic_runtime as proof

pytestmark = [pytest.mark.integration, pytest.mark.container]
_SOURCE_KEY = "copper-lantern-hours"
_SOURCE_REVISION = "public-fixture-1"
_SOURCE = "Public synthetic fixture: the copper lantern kiosk opens at 14:20 on Moonday."
_QUESTION = "When does the copper lantern kiosk open on Moonday?"
_BASE = "31b39d03c389f09bbfe5d918f5f532cf636eb35b"
_OPERATIONS, _POSTS, _TOKENS = 4, 8, 2044
_CASE_PROFILE = "generated-answer-and-empty-recall-v2"
_PROFILE_FIELDS = {"base_url", "model_id", "source_revision", "context_tokens", "max_tokens", "deadline_seconds"}
_WIRE_RECEIPT_FIELDS = {
    "receipt_id",
    "receipt_digest",
    "namespace_id",
    "purpose",
    "policy_revision",
    "retrieval_policy",
    "omitted_for_budget",
    "schema_version",
    "generation",
    "generation_version",
    "coverage",
    "min_cosine",
    "max_results",
    "char_budget",
}


@pytest.fixture
def semantic_answer_profile() -> ProbeProfile:
    if os.environ.get("LYCHD_REQUIRE_SEMANTIC_ANSWER_NATIVE_PROOF") != "1":
        pytest.skip("explicit native semantic answer proof is not requested")
    assert "PYTEST_XDIST_WORKER" not in os.environ
    location = os.environ.get("LYCHD_SEMANTIC_ANSWER_CHAT_PROFILE")
    assert location, "fresh_scoped_warm_chat_profile_required"
    return _chat_profile(Path(location))


def _chat_profile(path: Path) -> ProbeProfile:
    """Read only one private six-key operator declaration; perform no endpoint probe."""
    assert path.is_absolute()
    assert path.resolve(strict=True) == path
    assert not path.is_relative_to(Path(__file__).resolve().parents[2])
    metadata = path.lstat()
    assert stat.S_ISREG(metadata.st_mode)
    assert metadata.st_uid == os.getuid()
    assert stat.S_IMODE(metadata.st_mode) == 0o600
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC), "rb") as stream:
        opened = os.fstat(stream.fileno())
        assert (opened.st_dev, opened.st_ino) == (metadata.st_dev, metadata.st_ino)
        raw = stream.read(8193)
    assert len(raw) <= 8192
    supplied = json.loads(raw)
    assert set(supplied) == _PROFILE_FIELDS
    profile = ProbeProfile.model_validate(supplied)
    target = urlsplit(profile.base_url)
    assert target.scheme == "http"
    assert target.hostname == "127.0.0.1"
    assert target.username is None
    assert target.password is None
    assert not target.query
    assert not target.fragment
    assert profile.source_revision == _BASE
    assert profile.model_id == "Qwen3.8-27B"
    assert profile.context_tokens == 4096
    assert profile.max_tokens == 256
    assert profile.deadline_seconds == 30
    return profile


def _warm_inventory(request: httpx2.Request, profile: ProbeProfile, journal: list[dict[str, Any]]) -> dict[str, Any]:
    """Admit only the real registry's separately bounded warm inventory GET."""
    assert request.method == "GET", "warm_inventory_get_only"
    assert str(request.url) == profile.base_url + "/models", "warm_inventory_exact_endpoint"
    assert not request.content, "warm_inventory_no_body"
    # Retain the separately admitted outer ceiling. Only A may acquire Chat;
    # this inventory allowance does not authorize inference for B or C.
    assert len(journal) < 5, "warm_inventory_budget"
    entry: dict[str, Any] = {"method": request.method, "url": str(request.url)}
    journal.append(entry)
    return entry


@dataclass
class _AnswerBoundary(bridge._ModelBoundary):
    """Observe the actual provider request; return no substituted response."""

    run_id: str | None = None
    case: str | None = None
    receipt: dict[str, Any] | None = None
    observations: list[dict[str, Any]] = field(default_factory=list)
    previous_answer: str | None = None

    async def check(self, request: httpx2.Request) -> None:
        payload = json.loads(request.content)
        output = [name for name in ("max_tokens", "max_completion_tokens") if name in payload]
        allowed = (
            self.admitted
            and time.monotonic() < self.deadline
            and self.posts < 1
            and request.method == "POST"
            and str(request.url) == f"{self.profile.base_url}/chat/completions"
            and payload.get("model") == self.profile.model_id
            and payload.get("stream") is True
            and len(output) == 1
            and type(payload[output[0]]) is int
            and payload[output[0]] == 256
            and payload.get("tools") in (None, [])
            and payload.get("tool_choice") in (None, "none")
            and self.case == "A"
            and self.run_id is not None
        )
        if not allowed:
            self.violations.append("semantic_answer_model_post_refused")
            code = "semantic_answer_model_post_refused"
            raise AssertionError(code)
        messages = payload["messages"]
        users = [item["content"] for item in messages if item["role"] == "user"]
        assert _QUESTION in users
        envelopes = [json.loads(item) for item in users if isinstance(item, str) and item.startswith("{")]
        assert len(envelopes) == 1
        envelope = envelopes[0]
        assert envelope["kind"] == "archive_semantic_recall"
        assert envelope["instruction_authority"] == "none"
        assert self.receipt is not None
        assert set(envelope["receipt"]) == _WIRE_RECEIPT_FIELDS
        assert envelope["receipt"] == {name: self.receipt[name] for name in _WIRE_RECEIPT_FIELDS}
        assert envelope["receipt"]["schema_version"] == 2
        assert not any(_SOURCE in json.dumps(item) for item in messages if item["role"] in {"system", "developer"})
        assert len(envelope["items"]) == 1
        assert envelope["items"][0]["text"] == _SOURCE
        selection = envelope["items"][0]["selection"]
        assert (selection["source_key"], selection["source_revision"]) == (_SOURCE_KEY, _SOURCE_REVISION)
        self.posts += 1
        self.observations.append({"case": self.case, "run_id": self.run_id, "payload": payload})


def _settings(access: dict[str, Any], root: Path, key: str, password: SecretStr, profile: ArchiveProfile) -> Settings:
    """Extend the existing fixture declaration before any services are constructed."""
    url = f"postgresql://{access['user']}:{access['password']}@127.0.0.1:{access['port']}/{access['database']}"
    captured = SettingsSnapshot.capture(bridge._settings(url, root, key, password))
    payload = json.loads(captured.payload)
    payload["extensions"]["builtins"] = ["animator/vllm", "animator/llamacpp"]
    payload["weaver"]["bridge"] = {
        "revision": "5",
        "capability_key": key,
        "semantic": {"min_cosine": -1.0, "max_results": 1, "char_budget": 512},
    }
    payload["archive"] = {
        "profile": profile.model_dump(mode="json"),
        "derivation": {
            "generation_id": str(uuid4()),
            "binding": EmbeddingBinding(
                capability_key=f"answer-embedding:embedding:{PROFILE.model_id}", profile_digest=PROFILE.digest
            ).model_dump(mode="json"),
        },
        "semantic": True,
    }
    return replace(captured, payload=json.dumps(payload)).materialize()


def _transient(messages: list[Any]) -> None:
    """Source input stays absent from retained requests; assistant output may quote it."""
    for message in ModelMessagesTypeAdapter.validate_python(messages):
        if isinstance(message, ModelRequest):
            body = json.dumps(ModelMessagesTypeAdapter.dump_python([message], mode="json"))
            assert _SOURCE not in body
            assert "instruction_authority" not in body
            for part in message.parts:
                if isinstance(part, UserPromptPart):
                    assert part.content == _QUESTION


def _response(
    history: list[Any], profile: ProbeProfile, run_id: str, *, answer: str, observed: dict[str, Any]
) -> dict[str, Any]:
    selected = [item for item in history if item.get("run_id") == run_id]
    _transient(selected)
    responses = [item for item in ModelMessagesTypeAdapter.validate_python(selected) if isinstance(item, ModelResponse)]
    observed["response_count"] = len(responses)
    observed["part_types"] = [[part.part_kind for part in response.parts] for response in responses]
    assert len(responses) == 1
    response = responses[0]
    observed.update(
        model=response.model_name,
        response_id=response.provider_response_id,
        state=response.state,
        finish_reason=response.finish_reason,
        provider_finish_reason=(response.provider_details or {}).get("finish_reason"),
    )
    assert response.model_name == profile.model_id
    assert response.provider_response_id
    assert len(response.provider_response_id) <= 512
    assert response.state == "complete"
    assert response.finish_reason == "stop"
    assert (response.provider_details or {}).get("finish_reason") == "stop"
    assert all(isinstance(part, (TextPart, ThinkingPart)) for part in response.parts)
    texts = [part.content for part in response.parts if isinstance(part, TextPart)]
    assert texts
    visible = "".join(texts)
    assert visible.strip()
    assert isinstance(answer, str)
    assert answer.strip()
    # Match the installed Agent Graph's str output exactly. ThinkingPart content
    # never contributes to this value or the retained diagnostic metadata.
    assert visible == answer
    return observed


async def _terminal(services: Any, run_id: str, deadline: float, releases: list[str]) -> Any:
    try:
        async with asyncio.timeout_at(deadline):
            while True:
                run = await services.ledger.get(run_id)
                if (
                    run is not None
                    and run.status in TERMINAL_STATUSES
                    and run_id in releases
                    and services.substrate.context.get(run_id) is None
                ):
                    assert not services.leases.active()
                    return run
                await asyncio.sleep(0.02)
    except TimeoutError:
        async with asyncio.timeout(30):
            await services.run_engine.cancel(run_id)
        raise


async def _sql_derivation(services: Any, note: NoteRecord, status: DerivationStatus) -> dict[str, Any]:
    from lychd.db.engine import get_session_factory

    async with get_session_factory()() as session:
        row = await session.get(ArchiveNoteEmbedding, status.derivation_id)
        assert row is not None
        assert row.vector is not None
        assert row.receipt is not None
        receipt = DerivationReceipt.model_validate(row.receipt)
        digest = embedding_vector_digest(tuple(float(value) for value in row.vector))
        assert digest == status.vector_digest == receipt.vector_digest
        assert receipt.profile_digest == PROFILE.digest
        assert receipt.input_digest == note.source_digest
        generation = await session.get(ArchiveEmbeddingGeneration, services.archive_derivation.reference.generation_id)
        assert generation is not None
        return {
            "status": status.model_dump(mode="json"),
            "receipt": receipt.model_dump(mode="json"),
            "float32_vector_digest": digest,
        }


async def _revoked_sql(note_id: UUID, derivation_id: UUID) -> dict[str, bool]:
    from lychd.db.engine import get_session_factory

    async with get_session_factory()() as session:
        note = await session.get(ArchiveNote, note_id)
        row = await session.get(ArchiveNoteEmbedding, derivation_id)
        assert note is not None
        assert note.content is None
        assert row is not None
        assert row.vector is None
        assert row.attempt_token is None
        return {"source_cleared": True, "vector_cleared": True, "attempt_cleared": True}


@contextmanager
def _remember_body_failure(failures: list[BaseException]) -> Generator[None]:
    try:
        yield
    except BaseException as exc:
        failures.append(exc)
        raise


async def _observe_service_close(
    service: Any, *, close: Callable[[Any], Awaitable[None]], observation: dict[str, Any]
) -> None:
    """Attribute a successful return to the exact service and running loop."""
    observed = {"service_id": id(service), "loop_id": id(asyncio.get_running_loop()), "status": "closing"}
    observation["service_close"] = observed
    try:
        await close(service)
    except BaseException as exc:
        observed["error_type"] = type(exc).__name__
        observed["status"] = "failed"
        raise
    observed["status"] = "returned"


async def _disconnect_and_dispose(
    queues: Any,
    *,
    disconnect: Callable[[Any], Awaitable[None]],
    dispose: Callable[[], Awaitable[None]],
    observation: dict[str, Any],
) -> None:
    """Dispose only after the owning lifespan disconnects queues on its loop."""
    assert observation["calls"] == 0, "single_app_sql_disposal_required"
    observation["calls"] = 1
    observation["loop_id"] = id(asyncio.get_running_loop())
    observation["status"] = "disconnecting"
    try:
        await disconnect(queues)
        closed = observation.get("service_close", {})
        if (
            closed.get("status") != "returned"
            or closed.get("service_id") != observation.get("service_id")
            or closed.get("loop_id") != observation["loop_id"]
        ):
            observation["status"] = "services_unsettled"
            return
        observation["status"] = "disposing"
        await dispose()
    except BaseException as exc:
        observation["error_type"] = type(exc).__name__
        raise
    observation["status"] = "dispose_returned"


def _native_application(  # noqa: C901, PLR0912, PLR0915 - one fixed ordered HTTP/worker/native custody receipt
    root: Path,
    access: dict[str, Any],
    port: int,
    monkeypatch: pytest.MonkeyPatch,
    resources: dict[str, Any],
    profile: ProbeProfile,
) -> dict[str, Any]:
    from litestar.testing import TestClient
    from sqlalchemy import select

    from lychd.app import create_app
    from lychd.config.runes import registry as rune_module
    from lychd.db import engine as engine_owner
    from lychd.db.bootstrap import bootstrap_database
    from lychd.db.engine import dispose_engine, get_session_factory
    from lychd.domain.animation import model_factory
    from lychd.extensions import host as extension_module
    from lychd.interface.web import lifespan
    from lychd.interface.web.altar_services import AltarServices

    assert engine_owner._state == {"engine": None, "session_factory": None, "migration": None}, (
        "fresh_sql_owner_required"
    )
    disposal: dict[str, Any] = {"calls": 0, "status": "not_observed"}
    body_failures: list[BaseException] = []
    disconnect_queues = lifespan.disconnect_run_queues
    close_services = AltarServices.aclose

    async def observe_service_close(service: AltarServices) -> None:
        await _observe_service_close(service, close=close_services, observation=disposal)

    monkeypatch.setattr(AltarServices, "aclose", observe_service_close)

    async def disconnect_and_dispose(queues: Any) -> None:
        await _disconnect_and_dispose(
            queues, disconnect=disconnect_queues, dispose=dispose_engine, observation=disposal
        )

    monkeypatch.setattr(lifespan, "disconnect_run_queues", disconnect_and_dispose)
    wires: list[dict[str, Any]] = []
    warm_inventory: list[dict[str, Any]] = []
    inventory_clients: dict[int, httpx2.AsyncClient] = {}
    embedding_clients: dict[int, httpx2.AsyncClient] = {}
    chat_clients: list[httpx2.AsyncClient] = []
    boundary = _AnswerBoundary(profile)
    assert urlsplit(profile.base_url).port not in {port, 7134}
    actuator = bridge._RefusingActuator()
    source_profile = ArchiveProfile(
        namespace_id=uuid4(), owner_subject=ArchiveSubject(identity="local-operator"), policy_revision="public-notes.1"
    )
    key = f"answer-chat:chat:{profile.model_id}"
    password = SecretStr(secrets.token_urlsafe(32))
    settings = _settings(access, root / "control", key, password, source_profile)
    chat = VllmSoulstoneConfig(
        name="answer-chat",
        base_url=profile.base_url,  # pyright: ignore[reportArgumentType]
        port=urlsplit(profile.base_url).port,
        served_model_id=profile.model_id,
        concurrency=ConcurrencyIntent(dedicated=False),
        generation=GenerationProfile(max_context=4096, max_tokens=256, temperature=0),
    )
    embedding = LlamaCppSoulstoneConfig.model_validate(
        {
            "name": "answer-embedding",
            "port": port,
            "base_url": f"http://127.0.0.1:{port}/v1",
            "embedding_profile": PROFILE.profile_id,
            "model_path": "/models/embedding.gguf",
            "quadlet": {"image": IMAGE},
        }
    )
    bridge._configure_factory(monkeypatch, settings=settings, rune=chat, actuator=actuator, boundary=boundary)
    extensions = AssembledExtensions(
        context=ExtensionManager(builtins=("animator/vllm", "animator/llamacpp"), crypt=()).assemble()
    )
    monkeypatch.setattr(extension_module, "get_extensions", lambda: extensions)

    def load_runes(_exts: AssembledExtensions) -> RuneRegistry:
        return RuneRegistry((chat, embedding))

    monkeypatch.setattr(rune_module, "load_rune_registry", load_runes)
    monkeypatch.setattr("lychd.system.constants.PATH_RUNTIME_GUARD_DIR", root / "control" / "runtime-guard")
    client_factory = model_factory._model_http_client

    def model_client() -> httpx2.AsyncClient:
        client = client_factory()
        client.timeout = httpx2.Timeout(profile.deadline_seconds, connect=5)
        chat_clients.append(client)
        return client

    monkeypatch.setattr(model_factory, "_model_http_client", model_client)
    original_send, original_post = httpx2.AsyncClient.send, LlamaCppEmbeddingDriver._post
    inputs = [_SOURCE, *([PROFILE.query_prefix + _QUESTION] * 3)]
    services: Any = None

    async def send(client: httpx2.AsyncClient, request: httpx2.Request, **kwargs: Any) -> httpx2.Response:
        # The model factory owns its separate request-hook fence for these clients.
        if any(client is chat_client for chat_client in chat_clients):
            return await original_send(client, request, **kwargs)
        if request.url.port == urlsplit(profile.base_url).port:
            entry = _warm_inventory(request, profile, warm_inventory)
            assert client.follow_redirects is False
            inventory_clients[id(client)] = client
            response = await original_send(client, request, **kwargs)
            entry["status"] = response.status_code
            assert not response.is_redirect
            return response
        if request.url.port == 7134:
            assert request.url.host == "127.0.0.1"
            return await original_send(client, request, **kwargs)
        assert request.url.port == port
        assert request.url.scheme == "http"
        assert request.url.host == "127.0.0.1"
        embedding_clients[id(client)] = client
        entry: dict[str, Any] = {"method": request.method, "path": request.url.path}
        posts = [item for item in wires if item["method"] == "POST"]
        if request.method == "POST":
            assert len(posts) < _POSTS
            expected = "/tokenize" if len(posts) % 2 == 0 else "/v1/embeddings"
            assert request.url.path == expected
            payload = json.loads(request.content)
            content = payload["content"] if expected == "/tokenize" else payload["input"]
            assert content == inputs[len(posts) // 2]
            assert len(services.leases.active()) == 1
            entry["rendered_digest"] = text_digest(content)
        else:
            assert request.method == "GET"
            assert request.url.path in {"/health", "/v1/models"}
            assert sum(item["method"] == "GET" for item in wires) < 16
        wires.append(entry)
        response = await original_send(client, request, **kwargs)
        entry["status"] = response.status_code
        return response

    async def post(
        driver: LlamaCppEmbeddingDriver, path: str, payload: dict[str, object], *, authorize: Callable[[], None]
    ) -> dict[str, Any]:
        result = await original_post(driver, path, payload, authorize=authorize)
        if path == "/tokenize":
            wires[-1]["native_input_tokens"] = len(result["tokens"])
        return result

    monkeypatch.setattr(httpx2.AsyncClient, "send", send)
    monkeypatch.setattr(LlamaCppEmbeddingDriver, "_post", post)
    states: dict[str, SemanticChatState] = {}
    receipts: dict[str, SemanticRecallReceipt] = {}
    refusals: dict[str, str] = {}
    terminal_truth: set[str] = set()
    releases: list[str] = []
    assembly_attempts: list[str] = []
    assemblies: list[dict[str, Any]] = []
    chat_calls: list[dict[str, Any]] = []
    chat_attempts: list[str] = []
    chat_grants: list[dict[str, Any]] = []
    lease_grant = Dispatcher.lease_grant

    @asynccontextmanager
    async def observe_grant(dispatcher: Dispatcher, **kwargs: Any) -> AsyncGenerator[CapabilityGrant]:
        assert dispatcher is services.dispatcher
        assert kwargs["requires_tools"] is False
        assert kwargs["capability_key"] == key
        assert not services.leases.active()
        assert all(item.is_closed for item in embedding_clients.values())
        chat_attempts.append(kwargs["run_id"])
        async with lease_grant(dispatcher, **kwargs) as grant:
            chat_grants.append(
                {"run_id": kwargs["run_id"], "grant_id": grant.lease.grant_id, "model_id": grant.spec.model_id}
            )
            yield grant

    monkeypatch.setattr(Dispatcher, "lease_grant", observe_grant)
    # Observe original call boundaries without supplying SDK or provider results.
    archive_model = semantic_chat_module.ArchiveModel
    count_tokens, model_request = archive_model.count_tokens, archive_model.request
    request_stream = archive_model.request_stream
    pump = semantic_chat_module.pump_agent_events

    def chat_call(operation: str) -> None:
        chat_calls.append({"case": boundary.case, "run_id": boundary.run_id, "operation": operation})

    async def observe_count(model: Any, *args: Any, **kwargs: Any) -> Any:
        chat_call("count_tokens")
        return await count_tokens(model, *args, **kwargs)

    async def observe_request(model: Any, *args: Any, **kwargs: Any) -> Any:
        chat_call("request")
        return await model_request(model, *args, **kwargs)

    @asynccontextmanager
    async def observe_stream(model: Any, *args: Any, **kwargs: Any) -> AsyncGenerator[Any]:
        chat_call("request_stream")
        async with request_stream(model, *args, **kwargs) as response:
            yield response

    async def observe_pump(*args: Any, **kwargs: Any) -> Any:
        chat_call("pump_agent_events")
        return await pump(*args, **kwargs)

    monkeypatch.setattr(archive_model, "count_tokens", observe_count)
    monkeypatch.setattr(archive_model, "request", observe_request)
    monkeypatch.setattr(archive_model, "request_stream", observe_stream)
    monkeypatch.setattr(semantic_chat_module, "pump_agent_events", observe_pump)
    answer = AnswerSemanticNotes.run
    assemble, release = ContextOrchestrator.assemble, ContextOrchestrator.release
    set_status = DbRunLedger.set_status
    reached: asyncio.Event | None = None
    proceed: asyncio.Event | None = None

    async def status(ledger: DbRunLedger, run_id: str, status: RunStatus, **kwargs: Any) -> Any:
        result = await set_status(ledger, run_id, status, **kwargs)
        if status in TERMINAL_STATUSES:
            terminal_truth.add(run_id)
        return result

    def context_assemble(owner: ContextOrchestrator, **kwargs: Any) -> Any:
        assembly_attempts.append(kwargs["run_id"])
        value = assemble(owner, **kwargs)
        grant = kwargs.get("grant")
        if grant is not None:
            assert owner is services.substrate.context
            assert owner.registry is services.registry
            assert value.state_window == []
            assert value.continuation == []
            assert value.query == _QUESTION
            assert value.context_window == 4096
            assert value.transient_chars > 0
            assert len(services.leases.active()) == 1
            assemblies.append(
                {
                    "run_id": kwargs["run_id"],
                    "grant_id": grant.lease.grant_id,
                    "context_window": value.context_window,
                    "transient_chars": value.transient_chars,
                }
            )
        return value

    def context_release(owner: ContextOrchestrator, run_id: str) -> None:
        assert run_id in terminal_truth, "context_release_before_terminal_truth"
        release(owner, run_id)
        assert owner.get(run_id) is None
        releases.append(run_id)

    async def gate(node: AnswerSemanticNotes, ctx: Any) -> Any:
        assert boundary.case is not None
        case = boundary.case
        run = await services.ledger.get(ctx.state.run_id)
        assert run is not None
        assert run.status is RunStatus.RUNNING
        assert run.pattern_manifest == BRIDGE_CHAT_SEMANTIC.manifest.snapshot()
        assert run.admitted_capability_key == key
        assert run.admitted_semantic == services.run_engine.bridge_semantic
        assert run.sigil_name == default_sigil().name
        assert run.sigil_scopes == default_sigil().scopes
        assert ctx.deps.sigil_provider() == default_sigil()
        assert run.to_intent().admitted_semantic == run.admitted_semantic
        expected = BRIDGE_CHAT_SEMANTIC.make_state(run.to_intent())
        assert ctx.state.model_dump(
            include={"session_id", "run_id", "prompt", "priority", "capability_key", "semantic"}
        ) == expected.model_dump(include={"session_id", "run_id", "prompt", "priority", "capability_key", "semantic"})
        assert ctx.state.current_query_execution is not None
        assert not services.leases.active()
        assert all(item.is_closed for item in embedding_clients.values())
        request = semantic_recall_request(binding=ctx.state.semantic, run_id=run.run_id, prompt=_QUESTION)
        receipt = await services.archive_semantic.inspect_recall(
            source_profile.owner_subject, request, recall_purpose=ARCHIVE_ANSWER_PURPOSE, purpose="archive:manage"
        )
        assert receipt is not None
        assert receipt.query_execution == ctx.state.current_query_execution
        assert (receipt.receipt_id, receipt.receipt_digest) == (ctx.state.receipt_id, ctx.state.receipt_digest)
        assert receipt.query_digest == text_digest(_QUESTION)
        assert receipt.request_digest == request.binding_digest(
            ctx.state.semantic.manifest, source_profile.owner_subject, ARCHIVE_ANSWER_PURPOSE
        )
        assert receipt.query_execution.rendered_digest == text_digest(PROFILE.query_prefix + _QUESTION)
        assert receipt.query_execution.profile_digest == PROFILE.digest
        assert (receipt.min_cosine, receipt.max_results, receipt.char_budget, receipt.omitted_for_budget) == (
            -1.0,
            1,
            512,
            0,
        )
        assert receipt.generation == services.archive_semantic.reference
        assert receipt.coverage.promoted_notes == receipt.coverage.eligible_notes == (0 if case == "C" else 1)
        if case != "C":
            assert len(receipt.selected) == 1
            selection = receipt.selected[0]
            assert (selection.source_key, selection.source_revision) == (_SOURCE_KEY, _SOURCE_REVISION)
            assert selection.source_digest == text_digest(_SOURCE)
        states[case], receipts[case] = ctx.state, receipt
        boundary.run_id, boundary.receipt = run.run_id, receipt.model_dump(mode="json")
        if case == "B":
            assert reached is not None
            assert proceed is not None
            assert boundary.posts == 1
            reached.set()
            await proceed.wait()
        try:
            return await answer(node, ctx)
        except ArchiveRefused as exc:
            refusals[case] = exc.code
            raise

    monkeypatch.setattr(AnswerSemanticNotes, "run", gate)
    monkeypatch.setattr(ContextOrchestrator, "assemble", context_assemble)
    monkeypatch.setattr(ContextOrchestrator, "release", context_release)
    monkeypatch.setattr(DbRunLedger, "set_status", status)

    def observe_terminal(original: Callable[..., Any]) -> Callable[..., Any]:
        async def observed(ledger: DbRunLedger, run_id: str, **kwargs: Any) -> Any:
            result = await original(ledger, run_id, **kwargs)
            if result:
                retained = await ledger.get(run_id)
                assert retained is not None
                assert retained.status in TERMINAL_STATUSES
                terminal_truth.add(run_id)
            return result

        return observed

    for method in ("try_settle_claim", "try_fail_claimed"):
        monkeypatch.setattr(DbRunLedger, method, observe_terminal(getattr(DbRunLedger, method)))
    recall = RecallSemanticNotes.run

    async def admitted_recall(node: RecallSemanticNotes, ctx: Any) -> Any:
        retained = await services.ledger.get(ctx.state.run_id)
        assert retained is not None
        assert retained.pattern_manifest == BRIDGE_CHAT_SEMANTIC.manifest.snapshot()
        assert retained.admitted_capability_key == key
        assert retained.admitted_semantic == ctx.state.semantic
        assert retained.sigil_name == default_sigil().name
        assert retained.sigil_scopes == default_sigil().scopes
        return await recall(node, ctx)

    monkeypatch.setattr(RecallSemanticNotes, "run", admitted_recall)
    result: dict[str, Any] = {
        "status": "failed",
        "case_profile": _CASE_PROFILE,
        "public_oracle": {
            "source_key": _SOURCE_KEY,
            "source_revision": _SOURCE_REVISION,
            "source": _SOURCE,
            "question": _QUESTION,
        },
        "cases": {},
    }
    try:
        bootstrap_database(settings)
        app = create_app()
        with TestClient(app=app, base_url="http://127.0.0.1:7134") as client, _remember_body_failure(body_failures):

            async def app_loop() -> int:
                return id(asyncio.get_running_loop())

            disposal["app_loop_id"] = client.blocking_portal.call(app_loop)
            disposal["service_id"] = id(app.state.services)
            client.auth = ("magus", password.get_secret_value())
            services = bridge._ready(app, key)
            assert services.dispatcher is services.substrate.dispatcher
            assert services.dispatcher._registry is services.registry
            assert services.dispatcher._leases is services.leases
            assert services.archive_semantic is services.substrate.archive_semantic
            for consumer in (services.archive_semantic, services.archive_derivation):
                assert consumer._dispatcher._registry is services.registry
                assert consumer._dispatcher._leases is services.leases
            assert not services.leases.active()
            assert boundary.posts == 0
            assert not any(item["method"] == "POST" for item in wires)

            async def initial() -> None:
                async with get_session_factory()() as session:
                    assert list(await session.scalars(select(ArchiveEmbeddingGeneration))) == []

            client.blocking_portal.call(initial)
            headers = _csrf_headers(client)

            def call(method: str, path: str, body: Any = None, *, expected: int = 201) -> Any:
                response = client.request(method, path, json=body, headers=headers)
                assert response.status_code == expected
                return response.json()

            configured = call("GET", "/api/v1/archive/derivations/generations/configured", expected=200)
            assert configured == services.archive_semantic.reference.model_dump(mode="json")
            call("POST", "/api/v1/archive/derivations/generations/register", configured)
            proposal = NoteProposal(
                namespace_id=source_profile.namespace_id,
                request_id=uuid4(),
                source_key=_SOURCE_KEY,
                source_revision=_SOURCE_REVISION,
                source_digest=text_digest(_SOURCE),
                text=_SOURCE,
                producer="operator",
                observed_at=datetime(2026, 10, 19, tzinfo=UTC),
            )
            note = NoteRecord.model_validate(call("POST", "/api/v1/archive/notes", proposal.model_dump(mode="json")))
            note = NoteRecord.model_validate(
                call(
                    "POST",
                    f"/api/v1/archive/notes/{note.reference.record_id}/promote",
                    {"expected_version": note.reference.lifecycle_version},
                )
            )
            derivation = DerivationStatus.model_validate(
                call(
                    "POST",
                    "/api/v1/archive/derivations/derive",
                    DerivationRequest(
                        generation=services.archive_derivation.reference, source=note.reference
                    ).model_dump(mode="json"),
                )
            )
            assert derivation.state == "complete"
            result["derivation"] = client.blocking_portal.call(_sql_derivation, services, note, derivation)
            session_id = call("POST", "/api/v1/bridge/sessions")["session"]["id"]
            for case in ("A", "B", "C"):
                history_before = client.blocking_portal.call(services.bridge_sessions.get_session, session_id)
                assert history_before is not None
                sdk_history_before = json.dumps(history_before.message_history, sort_keys=True)
                boundary.case = case
                boundary.deadline = time.monotonic() + profile.deadline_seconds
                boundary.admitted = case == "A"
                request_id = str(uuid4())
                body = {"prompt": _QUESTION, "request_id": request_id}
                if case == "B":

                    async def events() -> tuple[asyncio.Event, asyncio.Event]:
                        return asyncio.Event(), asyncio.Event()

                    reached, proceed = client.blocking_portal.call(events)
                with override_allow_model_requests(allow_model_requests=True):
                    accepted = call("POST", f"/api/v1/bridge/sessions/{session_id}/messages", body, expected=200)
                    assert accepted["pattern_id"] == "bridge_chat"
                    assert accepted["pattern_revision"] == "5"
                    run_id = accepted["run_id"]
                    if case == "B":

                        async def wait_gate(event: asyncio.Event | None) -> None:
                            assert event is not None
                            async with asyncio.timeout(20):
                                await event.wait()

                        client.blocking_portal.call(wait_gate, reached)
                        assert boundary.posts == 1
                        call(
                            "POST",
                            f"/api/v1/archive/notes/{note.reference.record_id}/revoke",
                            {"expected_version": note.reference.lifecycle_version},
                        )
                        result["revocation_sql"] = client.blocking_portal.call(
                            _revoked_sql, note.reference.record_id, derivation.derivation_id
                        )
                        assert proceed is not None
                        client.blocking_portal.call(proceed.set)
                    finished = client.blocking_portal.call(_terminal, services, run_id, boundary.deadline, releases)
                boundary.admitted = False
                assert run_id in releases
                state = states[case]
                _transient(state.new_messages)
                metadata = state.model_dump(mode="json", exclude={"answer", "new_messages"})
                assert _SOURCE not in json.dumps(metadata)
                assert '"vector"' not in json.dumps(metadata)
                assert '"query_vector"' not in json.dumps(metadata)
                snapshot = client.get(f"/api/v1/bridge/sessions/{session_id}").json()["session"]
                agents = [turn for turn in snapshot["turns"] if turn["run_id"] == run_id and turn["role"] == "agent"]
                entry = {
                    "run_id": run_id,
                    "request_id": request_id,
                    "status": finished.status.value,
                    "receipt": receipts[case].model_dump(mode="json"),
                    "current_query_execution": cast("Any", state.current_query_execution).model_dump(mode="json"),
                    "persisted_caller": {"name": finished.sigil_name, "scopes": sorted(finished.sigil_scopes)},
                    "context_assembly_attempts": assembly_attempts.count(run_id),
                    # This is an observed Run release callback, including when no
                    # Context was assembled. It is not an invented assembly.
                    "context_released": True,
                    "chat_attempts": chat_attempts.count(run_id),
                    "chat_grants": sum(item["run_id"] == run_id for item in chat_grants),
                    "chat_POSTs": sum(item["run_id"] == run_id for item in boundary.observations),
                    "chat_calls": [item for item in chat_calls if item["run_id"] == run_id],
                }
                result["cases"][case] = entry
                if case == "B":
                    assert finished.status is RunStatus.FAILED
                    # Terminal cleanup may precede the best-effort generic failure turn.
                    assert len(agents) <= 1
                    assert all(
                        turn["state"] == "failed" and turn["content"] == _FAILURE_MESSAGE and turn["fragments"] == []
                        for turn in agents
                    )
                    assert state.answer is None
                    assert state.new_messages == []
                    assert refusals[case] in {"source_integrity", "receipt_stale"}
                    assert finished.error is not None
                    assert refusals[case] in finished.error
                    assert boundary.posts == 1
                    assert run_id not in chat_attempts
                    assert not any(item["run_id"] == run_id for item in chat_grants)
                    assert run_id not in assembly_attempts
                    assert entry["chat_calls"] == []
                    history = client.blocking_portal.call(services.bridge_sessions.get_session, session_id)
                    assert history is not None
                    assert json.dumps(history.message_history, sort_keys=True) == sdk_history_before
                    entry["typed_refusal"] = {
                        "type": "ArchiveRefused",
                        "code": refusals[case],
                        "retained_error": finished.error,
                    }
                    stale = call(
                        "POST",
                        f"/api/v1/archive/semantic/recalls/{receipts[case].receipt_id}/resolve",
                        {"receipt_digest": receipts[case].receipt_digest},
                        expected=409,
                    )
                    assert stale["extra"]["code"] in {"source_integrity", "receipt_stale"}
                    retained_receipt = call(
                        "POST",
                        "/api/v1/archive/semantic/recalls/inspect",
                        semantic_recall_request(binding=state.semantic, run_id=run_id, prompt=_QUESTION).model_dump(
                            mode="json"
                        ),
                    )
                    assert retained_receipt == receipts[case].model_dump(mode="json")
                else:
                    assert finished.status is RunStatus.DONE
                    assert len(agents) == 1
                    assert agents[0]["state"] == "settled"
                    answer_text = agents[0]["content"]
                    entry["answer"] = answer_text
                    assert answer_text == state.answer
                    history = client.blocking_portal.call(services.bridge_sessions.get_session, session_id)
                    assert history is not None
                    if case == "A":
                        entry["response"] = {}
                        _response(
                            history.message_history, profile, run_id, answer=answer_text, observed=entry["response"]
                        )
                        assert re.search(r"14:20|2:20\s*p\.?m\.?", answer_text, re.IGNORECASE)
                        assert _SOURCE_KEY in answer_text
                        assert _SOURCE_REVISION in answer_text
                        boundary.previous_answer = answer_text
                        counts = (len(wires), boundary.posts)
                        assert (
                            call("POST", f"/api/v1/bridge/sessions/{session_id}/messages", body, expected=200)["run_id"]
                            == run_id
                        )
                        assert (len(wires), boundary.posts) == counts
                        assert (
                            client.get(f"/api/v1/bridge/sessions/{session_id}").json()["session"]["turns"]
                            == snapshot["turns"]
                        )
                        entry["replay_new_compute"] = 0
                    else:
                        assert state.new_messages == []
                        assert json.dumps(history.message_history, sort_keys=True) == sdk_history_before
                        assert not any(message.get("run_id") == run_id for message in history.message_history)
                        assert entry["chat_attempts"] == entry["chat_grants"] == entry["chat_POSTs"] == 0
                        assert entry["chat_calls"] == []
                        assert entry["context_assembly_attempts"] == 0
                        assert receipts[case].selected == ()
                        assert receipts[case].coverage.eligible_notes == receipts[case].coverage.promoted_notes == 0
                        # The public oracle checks meaning and observed historical
                        # counts independently of the production outcome renderer.
                        assert answer_text.startswith("Deterministic recall result:")
                        assert "no public notes were selected for this question" in answer_text
                        assert "At recall, there were no promoted public notes." in answer_text
                        coverage = receipts[case].coverage
                        assert (
                            f"At recall, {coverage.eligible_notes} of {coverage.promoted_notes} promoted public notes "
                            "were searchable in the configured generation."
                        ) in answer_text
                        assert "This recall cannot support an answer to the question." in answer_text
                        assert boundary.previous_answer is not None
                        assert boundary.previous_answer not in answer_text
                        assert _SOURCE not in answer_text
                        assert _SOURCE_KEY not in answer_text
                        assert _SOURCE_REVISION not in answer_text
                        assert not re.search(r"14:20|2:20\s*p\.?m\.?", answer_text, re.IGNORECASE)
                        entry["deterministic_empty_recall"] = True
                        entry["new_SDK_messages"] = 0
                        counts = (
                            len(wires),
                            boundary.posts,
                            len(chat_attempts),
                            len(chat_grants),
                            len(chat_calls),
                            len(assembly_attempts),
                        )
                        assert (
                            call("POST", f"/api/v1/bridge/sessions/{session_id}/messages", body, expected=200)["run_id"]
                            == run_id
                        )
                        assert (
                            len(wires),
                            boundary.posts,
                            len(chat_attempts),
                            len(chat_grants),
                            len(chat_calls),
                            len(assembly_attempts),
                        ) == counts
                        replay_history = client.blocking_portal.call(services.bridge_sessions.get_session, session_id)
                        assert replay_history is not None
                        assert json.dumps(replay_history.message_history, sort_keys=True) == sdk_history_before
                        assert (
                            client.get(f"/api/v1/bridge/sessions/{session_id}").json()["session"]["turns"]
                            == snapshot["turns"]
                        )
                        entry["replay_new_compute"] = 0
            assert len(chat_grants) == len(chat_attempts) == 1
            assert boundary.posts == 1
            assert actuator.calls == 0
            assert not boundary.violations
            assert assembly_attempts == [result["cases"]["A"]["run_id"]]
            assert [item["run_id"] for item in assemblies] == assembly_attempts
            assert {item["run_id"] for item in chat_calls} == {result["cases"]["A"]["run_id"]}
            assert sum(item["operation"] == "pump_agent_events" for item in chat_calls) == 1
            assert sum(item["operation"] == "request_stream" for item in chat_calls) == 1
            assert not services.leases.active()
        assert disposal["status"] == "dispose_returned"
        assert disposal["calls"] == 1
        assert disposal["loop_id"] == disposal["app_loop_id"]
        with pytest.raises(RuntimeError):
            get_run_substrate()
        assert all(item.is_closed for item in [*embedding_clients.values(), *inventory_clients.values(), *chat_clients])
        posts = [item for item in wires if item["method"] == "POST"]
        tokens = sum(item.get("native_input_tokens", 0) for item in posts)
        retained_tokens = result["derivation"]["receipt"]["tokens"] + sum(
            item.query_execution.tokens for item in receipts.values()
        )
        assert len(posts) == _POSTS
        assert len(receipts) + 1 == _OPERATIONS
        assert (
            sum(item["path"] == "/tokenize" for item in posts)
            == sum(item["path"] == "/v1/embeddings" for item in posts)
            == _OPERATIONS
        )
        assert tokens == retained_tokens
        assert 0 < tokens <= _TOKENS
        result.update(
            status="passed",
            operations=_OPERATIONS,
            embedding_POSTs=len(posts),
            native_input_tokens=tokens,
            chat_POSTs=boundary.posts,
            assemblies=assemblies,
            context_assembly_attempts=assembly_attempts,
            chat_attempts=chat_attempts,
            chat_grants=chat_grants,
            chat_calls=chat_calls,
            releases=releases,
            all_observed_clients_closed=True,
            substrate_unpublished=True,
            independent_answer_evaluation="required_from_operator",
            generation={
                "reference": services.archive_semantic.reference.model_dump(mode="json"),
                "manifest": services.archive_semantic.manifest.model_dump(mode="json"),
            },
        )
    except BaseException as exc:
        if body_failures and exc is not body_failures[0]:
            body_failures[0].add_note("app_teardown_failed:" + type(exc).__name__)
            raise body_failures[0] from exc
        raise
    else:
        return result
    finally:
        original_failure = sys.exception()
        boundary.admitted = False
        cleanup_errors: list[str] = []
        try:
            get_run_substrate()
        except RuntimeError:
            result["substrate_unpublished"] = True
        else:
            result["substrate_unpublished"] = False
            cleanup_errors.append("substrate_still_published")
        result["engine_disposal"] = disposal
        if disposal["status"] != "dispose_returned":
            cleanup_errors.append("engine_dispose:" + disposal["status"])
        clients_closed = all(
            item.is_closed for item in [*embedding_clients.values(), *inventory_clients.values(), *chat_clients]
        )
        if not clients_closed:
            cleanup_errors.append("observed_client_still_open")
        if cleanup_errors:
            result["status"] = "failed"
        resources["answer_workflow"] = {
            "case_profile": _CASE_PROFILE,
            "observed_chat_POST_attempts": boundary.posts,
            "lifecycle_calls": actuator.calls,
            "status": result["status"],
            "cleanup_errors": cleanup_errors,
        }
        try:
            proof.persist(
                root,
                "answer-workflow.json",
                {
                    **result,
                    "wires": wires,
                    "outbound_chat": boundary.observations,
                    "all_observed_clients_closed": clients_closed,
                    "observed_embedding_clients": len(embedding_clients),
                    "observed_chat_clients": len(chat_clients),
                    "observed_inventory_clients": len(inventory_clients),
                    "warm_readiness_GETs": warm_inventory,
                    "leases_remaining": len(services.leases.active()) if services is not None else None,
                    "cleanup_errors": cleanup_errors,
                },
            )
        except BaseException as exc:
            if original_failure is None:
                raise
            original_failure.add_note("answer_receipt_write_failed:" + type(exc).__name__)
        if cleanup_errors:
            code = "semantic_answer_cleanup_uncertain:" + ",".join(cleanup_errors)
            if original_failure is None:
                raise AssertionError(code)
            original_failure.add_note(code)


async def _workflow(
    root: Path, access: dict[str, Any], port: int, monkeypatch: pytest.MonkeyPatch, resources: dict[str, Any]
) -> dict[str, Any]:
    """Keep TestClient's application/SQL on its own portal, never the outer loop."""
    profile = ProbeProfile.model_validate(resources["admitted_chat_profile"])
    return await asyncio.to_thread(_native_application, root, access, port, monkeypatch, resources, profile)


def test_semantic_answer_native_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, semantic_answer_profile: ProbeProfile
) -> None:
    """The fixed callback reads its explicit profile before resources can start."""
    receipt = cast("Any", proof.run_native_semantic_proof)(
        tmp_path / "semantic-answer-native",
        monkeypatch,
        _workflow,
        qualification="semantic-answer-v1",
        chat_profile=semantic_answer_profile.model_dump(),
    )
    assert receipt["status"] == receipt["cleanup"] == "passed"
    assert receipt["artifact_unchanged_after_cleanup"] is True
    assert receipt["proof"]["status"] == "passed"
    assert receipt["proof"]["case_profile"] == _CASE_PROFILE
