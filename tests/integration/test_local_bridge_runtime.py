"""Opt-in native Bridge/SAQ/PostgreSQL receipt against one external warm vLLM.

Requires LYCHD_REQUIRE_LOCAL_BRIDGE_PROOF=1 and an external
LYCHD_LOCAL_BRIDGE_PROFILE JSON accepted by ProbeProfile. The runner must admit
an idle endpoint and a compatible Testcontainers backend (including cached Ryuk
when enabled); a runner may explicitly select its own cleanup profile.
This test creates one disposable PostgreSQL container from an admitted cached
image, migrates its schema, and sends at most three synthetic streamed model POSTs.
It never starts, stops or loads the external model, and supplies no executable
tools except the production BridgeReply output contract. Lifecycle actuation is
an explicitly refusing fixture port; model, dispatch, Graph, SAQ and stores stay
real. HTTP uses TestClient, and two application lifespans share one database:
this is not a browser, deployed Vessel, process-crash, or managed-runtime receipt.

The model budget is cooperative; cancellation and ordinary lifespan shutdown
retain their cleanup bounds. Run under an outer process timeout as well. A missing
final receipt or incomplete cleanup cannot count as success. Only metadata is
written below pytest's basetemp; prompts, history and credentials are not emitted.
"""

# pyright: reportPrivateUsage=false
# The Docker SDK is an optional integration-test dependency.
# pyright: reportMissingImports=false

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Never, cast
from urllib.parse import unquote, urlsplit
from uuid import uuid4

import httpx2
import pytest
from pydantic import SecretStr, ValidationError
from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelResponse, NativeToolCallPart, ToolCallPart
from pydantic_ai.models import override_allow_model_requests
from scripts.local_model_probe import ProbeProfile

from lychd.agents.outputs import BridgeReply
from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT_BOUND
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import SettingsSnapshot
from lychd.domain.animation.capabilities import CapabilityPhase
from lychd.domain.animation.schemas import ConcurrencyIntent, GenerationProfile
from lychd.domain.cortex.runs import TERMINAL_STATUSES, RunStatus
from lychd.domain.cortex.substrate import get_run_substrate
from lychd.extensions.builtin.animator.soulstones.vllm import VllmSoulstoneConfig
from lychd.extensions.host import AssembledExtensions
from lychd.extensions.manager import ExtensionManager
from tests.integration.test_production_wiring import _assert_orb_done, _csrf_headers

if TYPE_CHECKING:
    from litestar import Litestar

    from lychd.config.settings.root import Settings
    from lychd.domain.orchestration.actuator import TransitionIntent
    from lychd.interface.web.altar_services import AltarServices

pytestmark = [pytest.mark.integration, pytest.mark.container]
_PG_ALIASES = ("pgvector/pgvector:pg18-trixie", "docker.io/pgvector/pgvector:pg18-trixie")
_POST_LIMIT = 3
_CLEANUP_SECONDS = 30


def _require(condition: bool, code: str) -> None:  # noqa: FBT001 - named content-free assertion helper
    """Keep failures content-free, including pytest's assertion rendering."""
    if not condition:
        raise AssertionError(code)


@pytest.fixture
def local_bridge_profile() -> ProbeProfile:
    if os.environ.get("LYCHD_REQUIRE_LOCAL_BRIDGE_PROOF") != "1":
        pytest.skip("explicit local Bridge runtime proof is not requested")
    _require("PYTEST_XDIST_WORKER" not in os.environ, "local_bridge_requires_serial_process")
    location = os.environ.get("LYCHD_LOCAL_BRIDGE_PROFILE")
    _require(location is not None, "local_bridge_profile_required")
    try:
        supplied = Path(cast("str", location))
        _require(supplied.is_absolute(), "local_bridge_profile_must_be_absolute")
        path = supplied.resolve(strict=True)
        _require(not path.is_relative_to(Path(__file__).resolve().parents[2]), "local_bridge_profile_must_be_external")
        _require(path.stat().st_size <= 8192, "local_bridge_profile_too_large")
        profile = ProbeProfile.model_validate_json(path.read_bytes())
        _require(
            profile.deadline_seconds <= 30 and profile.context_tokens <= 4096 and profile.max_tokens <= 256,
            "local_bridge_profile_exceeds_admitted_budget",
        )
    except (OSError, ValidationError, ValueError):
        pytest.fail("local_bridge_profile_invalid", pytrace=False)
    return profile


@dataclass
class _ModelBoundary:
    profile: ProbeProfile
    deadline: float = 0
    admitted: bool = False
    posts: int = 0
    violations: list[str] = field(default_factory=list)

    async def check(self, request: httpx2.Request) -> None:
        """Append to the real client's hooks; refuse before its real transport."""
        try:
            payload = json.loads(request.content)
        except (ValueError, UnicodeError):
            payload = None
        valid = isinstance(payload, dict)
        data = cast("dict[str, Any]", payload) if valid else {}
        output_fields = [name for name in ("max_tokens", "max_completion_tokens") if name in data]
        tools = data.get("tools")
        valid_tools = False
        if isinstance(tools, list) and tools:
            valid_tools = True
            for candidate in cast("list[Any]", tools):
                if not isinstance(candidate, dict):
                    valid_tools = False
                    break
                tool = cast("dict[str, Any]", candidate)
                function = tool.get("function")
                if (
                    tool.get("type") != "function"
                    or not isinstance(function, dict)
                    or cast("dict[str, Any]", function).get("name") != "final_result"
                ):
                    valid_tools = False
                    break
        allowed = (
            self.admitted
            and time.monotonic() < self.deadline
            and self.posts < _POST_LIMIT
            and request.method == "POST"
            and str(request.url) == f"{self.profile.base_url}/chat/completions"
            and valid
            and data.get("model") == self.profile.model_id
            and data.get("stream") is True
            and len(output_fields) == 1
            and type(data[output_fields[0]]) is int
            and data[output_fields[0]] == self.profile.max_tokens
            and valid_tools
        )
        if not allowed:
            self.violations.append("model_post_refused")
            msg = "local_bridge_model_post_refused"
            raise RuntimeError(msg)
        self.posts += 1


class _RefusingActuator:
    calls = 0

    async def apply(self, intent: TransitionIntent) -> None:
        _ = intent
        self.calls += 1
        msg = "local_bridge_lifecycle_forbidden"
        raise RuntimeError(msg)


def _cached_postgres(monkeypatch: pytest.MonkeyPatch, receipt: dict[str, Any]) -> Any:
    """Pin one admitted cached image and prohibit pulls, including a Reaper cache miss."""
    from docker.api.image import ImageApiMixin
    from docker.errors import ImageNotFound
    from testcontainers.community.postgres import PostgresContainer
    from testcontainers.core.config import testcontainers_config

    _require(not testcontainers_config.hub_image_name_prefix, "local_bridge_image_prefix_not_admitted")

    def refuse_pull(*_args: Any, **_kwargs: Any) -> Never:
        msg = "local_bridge_image_pull_forbidden"
        raise AssertionError(msg)

    monkeypatch.setattr(ImageApiMixin, "pull", refuse_pull)
    postgres = PostgresContainer(
        _PG_ALIASES[0],
        driver="asyncpg",
        username="bridge_proof",
        password=secrets.token_urlsafe(24),
        dbname="bridge_proof",
        mem_limit="512m",
        nano_cpus=1_000_000_000,
        pids_limit=128,
    )
    client = postgres.get_docker_client().client
    try:
        cached: set[str] = set()
        for alias in _PG_ALIASES:
            try:
                image = client.images.get(alias)
            except ImageNotFound:
                continue
            _require(
                isinstance(image.id, str) and image.id.startswith("sha256:"),
                "local_bridge_cached_image_identity_invalid",
            )
            cached.add(cast("str", image.id))
        _require(len(cached) == 1, "local_bridge_cached_postgres_missing_or_ambiguous")
        image_id = cached.pop()
        postgres.image = image_id
        receipt["postgres_image_id"] = image_id
    except BaseException:
        client.close()
        raise
    cast("Any", postgres.ports)["5432"] = ("127.0.0.1", None)
    postgres.with_env("POSTGRES_INITDB_ARGS", "--auth-host=scram-sha-256")
    return postgres


def _configure_factory(
    monkeypatch: pytest.MonkeyPatch,
    *,
    settings: Settings,
    rune: VllmSoulstoneConfig,
    actuator: _RefusingActuator,
    boundary: _ModelBoundary,
) -> None:
    from lychd import app as app_module
    from lychd.config.runes import registry as rune_module
    from lychd.config.settings import root as settings_module
    from lychd.db import engine as engine_module
    from lychd.domain.animation import model_factory
    from lychd.extensions import host as extension_module
    from lychd.interface.web import lifespan

    extensions = AssembledExtensions(context=ExtensionManager(builtins=("animator/vllm",), crypt=()).assemble())
    for module in (settings_module, app_module, engine_module):
        monkeypatch.setattr(module, "get_settings", lambda: settings)
    monkeypatch.setattr(extension_module, "get_extensions", lambda: extensions)

    def load_runes(_extensions: AssembledExtensions) -> RuneRegistry:
        return RuneRegistry((rune,))

    monkeypatch.setattr(rune_module, "load_rune_registry", load_runes)
    real_build = lifespan.build_altar_services

    def build_services(**kwargs: Any) -> AltarServices:
        return real_build(**kwargs, runtime_actuator=actuator)

    monkeypatch.setattr(lifespan, "build_altar_services", build_services)
    original_factory = model_factory._model_http_client

    def model_client() -> httpx2.AsyncClient:
        client = original_factory()
        client.event_hooks["request"].append(boundary.check)
        return client

    monkeypatch.setattr(model_factory, "_model_http_client", model_client)
    monkeypatch.setattr(sys, "argv", ["python"])
    monkeypatch.setattr(sys, "orig_argv", ["python"])
    for key in tuple(os.environ):
        if key.startswith(("GRANIAN_", "LITESTAR_")) or key == "WEB_CONCURRENCY":
            monkeypatch.delenv(key)


def _settings(pg_url: str, root: Path, key: str, password: SecretStr) -> Settings:
    parsed = urlsplit(pg_url)
    for directory in (root / "inbox", root / "journal", root / "runtime-guard"):
        directory.mkdir(mode=0o700, parents=True)
    return SettingsSnapshot(
        payload=json.dumps(
            {
                "server": {
                    "port": 7134,
                    "database": {
                        "profile": "postgres",
                        "host": "127.0.0.1",
                        "port": parsed.port,
                        "user": unquote(parsed.username or ""),
                        "database": parsed.path.lstrip("/"),
                    },
                    "jobs": {"interactive_concurrency": 1, "background_concurrency": 1},
                },
                "extensions": {"builtins": ["animator/vllm"], "crypt": []},
                "orchestration": {"switching": {"actuator": "host-reactor", "host_reactor_dir": str(root / "inbox")}},
                "weaver": {"bridge": {"revision": "2", "capability_key": key}},
            }
        ),
        database_password=SecretStr(unquote(parsed.password or "")),
        database_runtime_password=SecretStr(secrets.token_urlsafe(24)),
        database_phoenix_password=SecretStr(secrets.token_urlsafe(24)),
        web_secret_key=SecretStr(secrets.token_urlsafe(48)),
        web_access_password=password,
    ).materialize()


async def _wait_settled(services: AltarServices, run_id: str, deadline: float) -> None:
    try:
        async with asyncio.timeout_at(deadline):
            while True:
                run = await services.ledger.get(run_id)
                if run is not None and run.status in TERMINAL_STATUSES:
                    _require(run.status is RunStatus.DONE, "local_bridge_run_not_done")
                    return
                await asyncio.sleep(0.05)
    except TimeoutError:
        async with asyncio.timeout(_CLEANUP_SECONDS):
            await services.run_engine.cancel(run_id)
        pytest.fail("local_bridge_inference_deadline", pytrace=False)


async def _history(services: AltarServices, session_id: str, run_id: str, key: str) -> list[Any]:
    session = await services.bridge_sessions.get_session(session_id)
    run = await services.ledger.get(run_id)
    _require(session is not None and run is not None, "local_bridge_durable_owner_missing")
    _require(run is not None and run.status is RunStatus.DONE, "local_bridge_durable_run_not_done")
    _require(run is not None and run.admitted_capability_key == key, "local_bridge_wrong_retained_capability")
    _require(
        run is not None and run.pattern_manifest == BRIDGE_CHAT_BOUND.manifest.snapshot(), "local_bridge_wrong_manifest"
    )
    _require(session is not None and bool(session.message_history), "local_bridge_history_missing")
    _require(not services.leases.active(), "local_bridge_live_lease_remaining")
    return cast("Any", session).message_history


def _observe_history(history: list[Any], profile: ProbeProfile, marker: str) -> list[dict[str, Any]]:
    try:
        messages = ModelMessagesTypeAdapter.validate_python(history)
    except ValidationError:
        pytest.fail("local_bridge_retained_history_invalid", pytrace=False)
    responses = [message for message in messages if isinstance(message, ModelResponse)]
    _require(bool(responses) and len(responses) <= _POST_LIMIT, "local_bridge_response_history_invalid")
    observations: list[dict[str, Any]] = []
    outputs: list[ToolCallPart] = []
    for response in responses:
        _require(response.model_name == profile.model_id, "local_bridge_response_model_mismatch")
        identity = response.provider_response_id
        _require(isinstance(identity, str) and 0 < len(identity) <= 512, "local_bridge_response_id_missing")
        raw_finish = (response.provider_details or {}).get("finish_reason")
        _require(
            isinstance(raw_finish, str) and raw_finish in ("stop", "tool_calls"),
            "local_bridge_wire_finish_not_complete",
        )
        _require(
            response.finish_reason == ("tool_call" if raw_finish == "tool_calls" else "stop"),
            "local_bridge_finish_not_complete",
        )
        _require(response.state == "complete", "local_bridge_response_not_complete")
        observations.append({"response_id": identity, "model_id": response.model_name, "finish_reason": raw_finish})
        for part in response.parts:
            _require(not isinstance(part, NativeToolCallPart), "local_bridge_native_tool_unexpected")
            if isinstance(part, ToolCallPart):
                _require(part.tool_name == "final_result", "local_bridge_external_tool_unexpected")
                outputs.append(part)
    _require(len(outputs) == 1, "local_bridge_structured_output_missing_or_repeated")
    try:
        reply = BridgeReply.model_validate(outputs[0].args_as_dict(raise_if_invalid=True))
    except (ValueError, AssertionError):
        pytest.fail("local_bridge_structured_reply_invalid", pytrace=False)
    _require(reply.answer == marker and reply.fragments == [], "local_bridge_structured_reply_mismatch")
    return observations


def _ready(app: Litestar, key: str) -> AltarServices:
    services = cast("AltarServices", app.state.services)
    spec = services.registry.get_capability(key)
    state = services.registry.get_capability_state(key)
    _require(
        spec is not None and not spec.concurrency.dedicated and not spec.is_dynamic,
        "local_bridge_wrong_runtime_binding",
    )
    _require(spec is not None and spec.registrant_id == "builtin:animator/vllm", "local_bridge_unregistered_runtime")
    _require(state is not None and state.phase is CapabilityPhase.WARM, "local_bridge_startup_not_warm")
    return services


def test_local_bridge_runtime_retains_one_native_reply_across_two_boots(  # noqa: PLR0915 - one bounded two-lifespan receipt
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, local_bridge_profile: ProbeProfile
) -> None:
    from docker.errors import NotFound
    from litestar.testing import TestClient

    from lychd.app import create_app
    from lychd.db.bootstrap import bootstrap_database
    from lychd.db.engine import dispose_engine

    profile = local_bridge_profile
    receipt: dict[str, Any] = {"outcome": "failed", "source_revision_declared": profile.source_revision, "boots": 0}
    boundary = _ModelBoundary(profile)
    actuator = _RefusingActuator()
    receipt_path = tmp_path / "local-bridge-runtime" / "receipt.json"
    receipt_path.parent.mkdir()
    container_id: str | None = None
    postgres = None
    try:
        postgres = _cached_postgres(monkeypatch, receipt)
        with postgres:
            container_id = postgres.get_wrapped_container().id
            password = SecretStr(secrets.token_urlsafe(32))
            key = f"bootstrap-joined:chat:{profile.model_id}"
            settings = _settings(postgres.get_connection_url(host="127.0.0.1"), tmp_path / "control", key, password)
            monkeypatch.setattr("lychd.system.constants.PATH_RUNTIME_GUARD_DIR", tmp_path / "control" / "runtime-guard")
            rune = VllmSoulstoneConfig(
                name="bootstrap-joined",
                base_url=profile.base_url,  # pyright: ignore[reportArgumentType] - explicit validated profile
                port=urlsplit(profile.base_url).port,
                served_model_id=profile.model_id,
                concurrency=ConcurrencyIntent(dedicated=False),
                generation=GenerationProfile(
                    max_context=profile.context_tokens, max_tokens=profile.max_tokens, temperature=0
                ),
            )
            _configure_factory(monkeypatch, settings=settings, rune=rune, actuator=actuator, boundary=boundary)
            asyncio.run(dispose_engine())
            bootstrap_database(settings)
            bootstrap_database(settings)
            marker = f"joined-bridge-{secrets.token_hex(12)}"
            app = create_app()
            with TestClient(app=app, base_url="http://127.0.0.1:7134") as client:
                client.auth = ("magus", password.get_secret_value())
                services = _ready(app, key)
                receipt["boots"] += 1
                headers = _csrf_headers(client)
                created = client.post("/api/v1/bridge/sessions", headers=headers)
                _require(created.status_code == 201, "local_bridge_session_admission_failed")
                session_id = created.json()["session"]["id"]
                boundary.deadline = time.monotonic() + profile.deadline_seconds
                boundary.admitted = True
                with override_allow_model_requests(allow_model_requests=True):
                    accepted = client.post(
                        f"/api/v1/bridge/sessions/{session_id}/messages",
                        json={
                            "prompt": f"Return the final structured reply with answer exactly {marker} and fragments [].",
                            "request_id": str(uuid4()),
                        },
                        headers=headers,
                    )
                    _require(accepted.status_code == 200, "local_bridge_turn_admission_failed")
                    run_id = accepted.json()["run_id"]
                    client.blocking_portal.call(_wait_settled, services, run_id, boundary.deadline)
                boundary.admitted = False
                _assert_orb_done(client, run_id)
                history = client.blocking_portal.call(_history, services, session_id, run_id, key)
                receipt["responses"] = _observe_history(history, profile, marker)
                snapshot = client.get(f"/api/v1/bridge/sessions/{session_id}").json()
                turns = snapshot["session"]["turns"]
                _require(len(turns) == 2 and turns[-1]["content"] == marker, "local_bridge_settled_turns_invalid")
                _require(turns[-1]["state"] == "settled", "local_bridge_turn_not_settled")
                _require(boundary.posts == len(receipt["responses"]), "local_bridge_unretained_model_response")
                receipt.update({"run_id": run_id, "session_id": session_id, "history_sha256": _digest(history)})
            asyncio.run(dispose_engine())
            first_posts = boundary.posts
            second_app = create_app()
            with TestClient(app=second_app, base_url="http://127.0.0.1:7134") as client:
                client.auth = ("magus", password.get_secret_value())
                services = _ready(second_app, key)
                receipt["boots"] += 1
                restored = client.blocking_portal.call(_history, services, session_id, run_id, key)
                _require(_digest(restored) == _digest(history), "local_bridge_second_boot_history_changed")
                second_snapshot = client.get(f"/api/v1/bridge/sessions/{session_id}").json()
                _require(second_snapshot["session"]["turns"] == turns, "local_bridge_second_boot_turns_changed")
                _assert_orb_done(client, run_id)
                _require(boundary.posts == first_posts, "local_bridge_second_boot_replayed_inference")
            _require(not boundary.violations, "local_bridge_model_boundary_violation")
            _require(actuator.calls == 0, "local_bridge_lifecycle_attempted")
        receipt["outcome"] = "passed"
    finally:
        boundary.admitted = False
        receipt.update(
            {
                "model_posts": boundary.posts,
                "model_boundary_violations": boundary.violations,
                "lifecycle_calls": actuator.calls,
            }
        )
        try:
            get_run_substrate()
        except RuntimeError:
            receipt["substrate_unpublished"] = True
            asyncio.run(dispose_engine())
        else:
            receipt["substrate_unpublished"] = False
            receipt["outcome"] = "failed"
        if container_id is not None and postgres is not None:
            try:
                postgres.get_docker_client().client.api.inspect_container(container_id)
            except NotFound:
                receipt["postgres_removed"] = True
            else:
                receipt["postgres_removed"] = False
                receipt["outcome"] = "failed"
        if postgres is not None:
            postgres.get_docker_client().client.close()
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _require(receipt.get("substrate_unpublished") is True, "local_bridge_cleanup_substrate_still_live")
        if container_id is not None:
            _require(receipt.get("postgres_removed") is True, "local_bridge_cleanup_postgres_not_removed")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
