"""Real disposable composition: lifecycle, isolation, security, and linked projections."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from litestar.datastructures import State
from pydantic import SecretStr

from lychd import developer
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.substrate import get_run_substrate, reset_run_substrate
from lychd.domain.web.tickets import TicketStore
from tests.web.conftest import TEST_ACCESS_PASSWORD, TEST_AUTHORIZATION

if TYPE_CHECKING:
    from pathlib import Path

    from litestar import Litestar

    from lychd.interface.web.altar_services import AltarServices

_ORIGIN = "http://127.0.0.1:5173"


def _forbidden_credential(_length: int) -> str:
    pytest.fail("credential issued before policy")


def _app() -> Litestar:
    return developer.create_developer_app(
        access_password=SecretStr(TEST_ACCESS_PASSWORD), signing_key=SecretStr("synthetic-fixture-signing-key")
    )


def _client(app: Litestar) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),  # pyright: ignore[reportArgumentType] - ASGI typing differs
        base_url="http://127.0.0.1:8000",
        headers={"authorization": TEST_AUTHORIZATION},
    )


@asynccontextmanager
async def fixture_client() -> AsyncGenerator[httpx.AsyncClient]:
    app = _app()
    async with app.lifespan(), _client(app) as client:
        yield client
    assert "services" not in app.state
    with pytest.raises(RuntimeError, match="not published"):
        get_run_substrate()


@pytest.mark.asyncio
async def test_fixture_real_lifespan_never_reaches_ambient_or_effectful_seams(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bomb owners of forbidden I/O rather than replacing the composition under test."""
    from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin
    from litestar_saq import SAQPlugin

    from lychd import app as app_module
    from lychd.agents.factory import AgentForge
    from lychd.config import components
    from lychd.config.runes import registry as runes
    from lychd.config.settings import root
    from lychd.db import engine
    from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
    from lychd.extensions import host
    from lychd.interface.web import altar_services, lifespan
    from lychd.system.services import runtime
    from lychd.system.services.queues import RuntimeQueuePlugin

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("The developer fixture reached an ambient/effectful owner")

    for owner, name in (
        (root.Settings, "settings_customise_sources"),
        (root, "get_settings"),
        (app_module, "get_settings"),
        (altar_services, "get_settings"),
        (runes, "load_rune_registry"),
        (host, "get_extensions"),
        (components, "build_db_config"),
        (components, "build_saq_config"),
        (engine, "get_engine"),
        (engine, "get_session_factory"),
        (SQLAlchemyPlugin, "__init__"),
        (SAQPlugin, "__init__"),
        (RuntimeQueuePlugin, "__init__"),
        (runtime, "wait_for_host_reactor_idle"),
        (altar_services, "build_runtime_actuator"),
        (lifespan, "connect_run_queues"),
        (lifespan, "_recover_durable_state"),
        (lifespan, "_start_delivery_relay"),
        (lifespan, "_start_delegate_relay"),
        (lifespan, "_start_consent_relay"),
        (RuntimeAdapterRegistry, "build_runtime"),
        (RuntimeAdapterRegistry, "probe_capability_states"),
        (AgentForge, "agent_for"),
    ):
        monkeypatch.setattr(owner, name, forbidden)
    monkeypatch.setenv("SERVER__DATABASE__PROFILE", "postgres")
    monkeypatch.setenv("SERVER__WEB__ACCESS_PASSWORD", "ambient-credential-that-must-never-be-read")
    app = _app()
    async with app.lifespan(), _client(app) as client:
        services = app.state.services
        assert services.registry.list_capabilities() == []
        assert services.delegates is None
        for path in (
            "/api/v1/altar/status",
            "/api/v1/bridge",
            "/api/v1/bridge/sessions",
            "/api/v1/nexus",
            "/api/v1/loom",
            "/api/v1/atlas/projects",
            "/schema/openapi.json",
        ):
            assert (await client.get(path)).status_code == 200, path
        assert (await client.get("/orchestrator/plan?target=missing")).status_code == 404
        assert (await client.get("/api/v1/nexus/plan?target=missing")).status_code == 404
        unavailable = await client.get("/orchestrator/queues")
        assert unavailable.status_code == 503
        assert "unavailable" in unavailable.json()["detail"]
    assert "services" not in app.state


@pytest.mark.asyncio
async def test_fixture_bridge_orb_and_loom_share_one_registered_revision() -> None:
    async with fixture_client() as client:
        snapshot = (await client.get("/api/v1/bridge")).json()
        session = snapshot["session"]
        assert "SYNTHETIC" in session["title"]
        run_ids = {turn["run_id"] for turn in session["turns"]}
        assert len(run_ids) == 1
        run_id = run_ids.pop()
        bridge = (await client.get(f"/api/v1/bridge/runs/{run_id}")).json()
        orb = (await client.get(f"/api/v1/orb/runs/{run_id}")).json()
        assert bridge["run_id"] == orb["run"]["run_id"] == run_id
        assert orb["run"]["session_id"] == session["id"]
        assert orb["run"]["status"] == "failed"
        assert "SYNTHETIC" in orb["evidence"][0]["summary"]
        assert "no graph, model, or host execution" in orb["evidence"][0]["summary"]
        pattern = orb["pattern"]
        assert pattern["exact"] is True
        assert pattern["loom_path"] == f"/loom/{pattern['pattern_id']}/{pattern['revision']}?run={run_id}"
        loom = (await client.get(f"/api/v1/loom/{pattern['pattern_id']}/{pattern['revision']}")).json()
        assert loom["pattern_id"] == pattern["pattern_id"]
        assert loom["revision"] == pattern["revision"]
        stream = await client.get(f"/api/v1/bridge/runs/{run_id}/events")
        assert stream.status_code == 200
        assert "event: resync" in stream.text
        assert "snapshot_required" in stream.text
        assert stream.text.count("event: resync") == 1
        assert "event: token" not in stream.text


@pytest.mark.asyncio
async def test_fixture_explicit_observation_source_keeps_custody_and_read_authority(tmp_path: Path) -> None:
    from lychd.config.settings.observability import SnapshotSourceSettings

    source = SnapshotSourceSettings(
        source_id="fixture.connected",
        registrant_id="operator:fixture",
        path=tmp_path / "not-published",
    )
    app = developer.create_developer_app(
        access_password=SecretStr(TEST_ACCESS_PASSWORD),
        signing_key=SecretStr("synthetic-observation-fixture-key"),
        observation_sources=(source,),
    )
    async with app.lifespan(), _client(app) as client:
        denied = await client.get("/api/v1/orb/runtime", headers={"authorization": ""})
        assert denied.status_code == 401
        response = await client.get("/api/v1/orb/runtime")
        assert response.status_code == 200
        selected = next(item for item in response.json()["sources"] if item["source_id"] == source.source_id)
        assert selected["status"] == "unavailable"
        assert selected["registrant_id"] == "operator:fixture"
        assert str(tmp_path) not in response.text
        runs = (await client.get("/api/v1/orb/runs")).json()["runs"]
        assert len(runs) == 1
        assert runs[0]["status"] == "failed"


@pytest.mark.asyncio
async def test_fixture_keeps_real_auth_host_origin_and_csrf() -> None:
    async with fixture_client() as client:
        assert (await client.get("/api/v1/bridge", headers={"authorization": ""})).status_code == 401
        assert (await client.get("/api/v1/bridge", auth=("magus", "wrong"))).status_code == 401
        assert (await client.get("/api/v1/bridge", headers={"host": "evil.example"})).status_code == 400
        initial = await client.get("/api/v1/bridge", headers={"origin": _ORIGIN, "host": "127.0.0.1:5173"})
        assert initial.status_code == 200
        assert initial.headers["access-control-allow-origin"] == _ORIGIN
        foreign_cors = await client.get("/api/v1/bridge", headers={"origin": "http://localhost:5173"})
        assert "access-control-allow-origin" not in foreign_cors.headers
        no_csrf = await client.post("/api/v1/bridge/sessions")
        assert no_csrf.status_code == 403
        assert "CSRF" in no_csrf.json()["detail"]
        token = client.cookies["csrftoken"]
        no_auth = await client.post("/api/v1/bridge/sessions", headers={"authorization": "", "x-csrftoken": token})
        assert no_auth.status_code == 401
        wrong_auth = await client.post(
            "/api/v1/bridge/sessions", auth=("magus", "wrong"), headers={"x-csrftoken": token}
        )
        assert wrong_auth.status_code == 401
        foreign = await client.post(
            "/api/v1/bridge/sessions", headers={"origin": "https://evil.example", "x-csrftoken": token}
        )
        assert foreign.status_code == 403
        assert "Origin" in foreign.json()["detail"]
        good = await client.post("/api/v1/bridge/sessions", headers={"origin": _ORIGIN, "x-csrftoken": token})
        assert good.status_code == 403
        assert "read-only" in good.json()["detail"]


@pytest.mark.asyncio
async def test_fixture_refuses_mutations_before_domain_admission(monkeypatch: pytest.MonkeyPatch) -> None:
    from lychd.domain.codex.ledger import InMemoryConsentLedger
    from lychd.domain.cortex.engine import RunEngine
    from lychd.domain.cortex.ledger import InMemoryRunLedger
    from lychd.domain.orchestration.manager import OrchestratorManager
    from lychd.domain.web.atlas import AtlasCreate, AtlasMutation, AtlasProjectUpdate, InMemoryAtlasStore
    from lychd.domain.web.contracts import ConsentDecisionIntent, MessageIntent, SwapIntent
    from lychd.domain.web.sessions import BridgeSessionStore
    from lychd.domain.web.swap_requests import InMemorySwapRequestLedger

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("A refused HTTP mutation reached domain admission")

    async with fixture_client() as client:
        for owner, name in (
            (BridgeSessionStore, "create_session"),
            (BridgeSessionStore, "add_turn"),
            (BridgeSessionStore, "settle_agent_turn"),
            (RunEngine, "submit"),
            (RunEngine, "cancel"),
            (RunEngine, "resume_consent"),
            (InMemoryRunLedger, "create"),
            (InMemoryRunLedger, "create_idempotent"),
            (InMemoryRunLedger, "set_status"),
            (InMemoryRunLedger, "append_event"),
            (InMemoryConsentLedger, "decide"),
            (InMemoryConsentLedger, "park"),
            (InMemoryAtlasStore, "create_project"),
            (InMemoryAtlasStore, "change_project"),
            (InMemorySwapRequestLedger, "claim"),
            (TicketStore, "reserve_capacity"),
            (OrchestratorManager, "request_transition"),
        ):
            monkeypatch.setattr(owner, name, forbidden)

        before = (await client.get("/api/v1/bridge")).json()
        session_id = before["session"]["id"]
        run_id = before["session"]["turns"][0]["run_id"]
        headers = {"x-csrftoken": client.cookies["csrftoken"], "origin": _ORIGIN}
        projects_before = (await client.get("/api/v1/atlas/projects")).json()
        for method, path, body in (
            ("POST", "/api/v1/bridge/sessions", {}),
            (
                "POST",
                f"/api/v1/bridge/sessions/{session_id}/messages",
                MessageIntent(request_id=uuid4(), prompt="Never admit me").model_dump(mode="json"),
            ),
            ("POST", f"/api/v1/bridge/runs/{run_id}/cancel", {}),
            (
                "POST",
                "/api/v1/bridge/consents/missing/decision",
                ConsentDecisionIntent(verdict="approve").model_dump(mode="json"),
            ),
            (
                "POST",
                "/api/v1/nexus/swaps",
                SwapIntent(request_id=str(uuid4()), target="missing").model_dump(mode="json"),
            ),
            ("POST", "/orchestrator/activate?target=missing", {}),
            (
                "POST",
                "/api/v1/atlas/projects",
                AtlasCreate(id=uuid4(), title="Never create me").model_dump(mode="json"),
            ),
            (
                "POST",
                f"/api/v1/atlas/projects/{uuid4()}/changes",
                AtlasMutation(
                    request_id=uuid4(),
                    expected_version=1,
                    change=AtlasProjectUpdate(
                        kind="project.update", title="Refused", brief="", lifecycle="active", next_action=""
                    ),
                ).model_dump(mode="json"),
            ),
            ("PUT", "/api/v1/bridge/sessions", {}),
            ("DELETE", "/api/v1/bridge/sessions", {}),
            ("TRACE", "/api/v1/bridge/sessions", {}),
            ("CONNECT", "/orchestrator/activate", {}),
        ):
            response = await client.request(method, path, json=body, headers=headers)
            assert response.status_code == (403 if method == "POST" else 405), (method, path, response.text)
            if method == "POST":
                assert "read-only" in response.json()["detail"]
        assert (await client.get("/api/v1/bridge")).json() == before
        assert (await client.get("/api/v1/atlas/projects")).json() == projects_before


@pytest.mark.asyncio
async def test_fixture_second_boot_is_fresh_and_withdraws_publications() -> None:
    app = _app()
    ids: list[str] = []
    for _ in range(2):
        async with app.lifespan(), _client(app) as client:
            services = app.state.services
            snapshot = (await client.get("/api/v1/bridge")).json()
            ids.append(snapshot["session"]["id"])
            assert len(snapshot["sessions"]) == 1
            assert get_run_substrate() is services.substrate
        assert "services" not in app.state
        with pytest.raises(RuntimeError, match="not published"):
            get_run_substrate()
    assert ids[0] != ids[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["construction", "warming", "seeding", "partial_seed", "substrate", "publication"])
async def test_fixture_startup_failure_withdraws_and_closes(stage: str, monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app()
    closed: list[str] = []
    original_tickets_close = TicketStore.aclose
    original_bus_close = InProcessEventBus.aclose

    async def tickets_close(self: TicketStore) -> None:
        closed.append("tickets")
        await original_tickets_close(self)

    async def bus_close(self: InProcessEventBus) -> None:
        closed.append("bus")
        await original_bus_close(self)

    def fail(*_args: Any, **_kwargs: Any) -> Any:
        message = f"failure at {stage}"
        raise RuntimeError(message)

    monkeypatch.setattr(TicketStore, "aclose", tickets_close)
    monkeypatch.setattr(InProcessEventBus, "aclose", bus_close)
    _inject_startup_failure(stage, monkeypatch, fail)
    with pytest.raises(BaseExceptionGroup) as caught:
        async with app.lifespan():
            pytest.fail("Startup unexpectedly completed")
    assert f"failure at {stage}" in str(caught.getrepr())
    assert "services" not in app.state
    with pytest.raises(RuntimeError, match="not published"):
        get_run_substrate()
    assert closed == ([] if stage == "construction" else ["tickets", "bus"])


def _inject_startup_failure(stage: str, monkeypatch: pytest.MonkeyPatch, fail: Callable[..., Any]) -> None:
    from lychd.domain.cortex import substrate

    if stage == "construction":
        monkeypatch.setattr(developer, "build_altar_services", fail)
    elif stage == "warming":
        monkeypatch.setattr(AnimatorRegistry, "ensure_loaded", fail)
    elif stage == "seeding":
        monkeypatch.setattr(developer, "_seed", AsyncMock(side_effect=RuntimeError("failure at seeding")))
    elif stage == "partial_seed":
        from lychd.domain.web.sessions import BridgeSessionStore

        monkeypatch.setattr(
            BridgeSessionStore, "settle_agent_turn", AsyncMock(side_effect=RuntimeError("failure at partial_seed"))
        )
    elif stage == "substrate":
        original_publish = substrate.set_run_substrate

        def publish_then_fail(value: Any) -> None:
            original_publish(value)
            fail()

        monkeypatch.setattr(substrate, "set_run_substrate", publish_then_fail)
    else:
        original_setattr = State.__setattr__

        def state_then_fail(self: State, name: str, value: Any) -> None:
            original_setattr(self, name, value)
            if name == "services":
                fail()

        monkeypatch.setattr(State, "__setattr__", state_then_fail)


@pytest.mark.asyncio
@pytest.mark.parametrize("startup_failure", [False, True])
@pytest.mark.parametrize("bus_failure", [False, True])
async def test_fixture_preserves_failures_and_closes_every_owner(
    monkeypatch: pytest.MonkeyPatch, *, startup_failure: bool, bus_failure: bool
) -> None:
    app = _app()
    bus_close = AsyncMock(side_effect=RuntimeError("bus close failed") if bus_failure else None)
    monkeypatch.setattr(TicketStore, "aclose", AsyncMock(side_effect=RuntimeError("ticket close failed")))
    monkeypatch.setattr(InProcessEventBus, "aclose", bus_close)
    if startup_failure:
        monkeypatch.setattr(developer, "_seed", AsyncMock(side_effect=ValueError("seed failed")))
    with pytest.raises(BaseExceptionGroup) as caught:
        async with app.lifespan():
            pass
    bus_close.assert_awaited_once()
    assert "ticket close failed" in str(caught.getrepr())
    if bus_failure:
        assert "bus close failed" in str(caught.getrepr())
    if startup_failure:
        assert "seed failed" in str(caught.getrepr())
    assert "services" not in app.state
    with pytest.raises(RuntimeError, match="not published"):
        get_run_substrate()


@pytest.mark.parametrize(
    "environment",
    [
        {"GRANIAN_WORKERS": "2"},
        {"LITESTAR_RELOAD": "true"},
        {"GRANIAN_UDS": "/fixture.sock"},
        {"GRANIAN_METRICS_ENABLED": "true"},
        {"LITESTAR_FILE_DESCRIPTOR": "3"},
    ],
)
def test_fixture_launcher_rejects_unsafe_environment_before_credentials(
    environment: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    for key in tuple(developer.os.environ):
        if key.startswith(("LITESTAR_", "GRANIAN_")) or key == "WEB_CONCURRENCY":
            monkeypatch.delenv(key)
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(developer.secrets, "token_urlsafe", _forbidden_credential)
    with pytest.raises(SystemExit) as caught:
        developer.main(("--caged",))
    assert caught.value.code == 2


@pytest.mark.parametrize(
    "arguments",
    [
        (),
        ("--caged", "--host", "0.0.0.0"),  # noqa: S104 - refusal control
        ("--workers", "2"),
        ("--reload",),
        ("--uds", "x"),
        ("--metrics",),
        ("--por", "8034"),
        ("--hos", "::1"),
        ("--por=8034",),
        ("--hos=::1",),
    ],
)
def test_fixture_launcher_rejects_unsafe_arguments(arguments: tuple[str, ...], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(developer.secrets, "token_urlsafe", _forbidden_credential)
    with pytest.raises(SystemExit) as caught:
        developer.main(arguments)
    assert caught.value.code == 2


@pytest.mark.asyncio
async def test_fixture_late_construction_failure_has_no_live_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    """Constructors allocate inert stores; failures before return own no tasks or handles."""
    from lychd.interface.web import altar_services

    buses: list[InProcessEventBus] = []
    tickets: list[TicketStore] = []
    bus_init = InProcessEventBus.__init__
    ticket_init = TicketStore.__init__

    def record_bus(self: InProcessEventBus, **kwargs: Any) -> None:
        bus_init(self, **kwargs)
        buses.append(self)

    def record_tickets(self: TicketStore, **kwargs: Any) -> None:
        ticket_init(self, **kwargs)
        tickets.append(self)

    def fail_engine(**_kwargs: Any) -> Any:
        message = "late construction failed"
        raise RuntimeError(message)

    monkeypatch.setattr(InProcessEventBus, "__init__", record_bus)
    monkeypatch.setattr(TicketStore, "__init__", record_tickets)
    monkeypatch.setattr(altar_services, "RunEngine", fail_engine)
    app = _app()
    before = asyncio.all_tasks()
    with pytest.raises(BaseExceptionGroup) as caught:
        async with app.lifespan():
            pytest.fail("Late construction unexpectedly succeeded")
    assert "late construction failed" in str(caught.getrepr())
    assert len(buses) == len(tickets) == 1
    assert tickets[0].count == 0
    # These sets are the complete resource owners documented by the constructors.
    assert buses[0]._pending == set()  # pyright: ignore[reportPrivateUsage]
    assert buses[0]._channels == {}  # pyright: ignore[reportPrivateUsage]
    assert buses[0]._writers == {}  # pyright: ignore[reportPrivateUsage]
    assert asyncio.all_tasks() == before
    assert "services" not in app.state


@pytest.mark.asyncio
async def test_fixture_competing_boot_preserves_the_published_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    """An awaited seed cannot grant two lifespans the same process publication."""
    first = _app()
    second = _app()
    seeding = asyncio.Event()
    continue_first = asyncio.Event()
    original_seed = developer._seed  # pyright: ignore[reportPrivateUsage]
    calls = 0

    async def interleaved_seed(services: AltarServices) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            seeding.set()
            await continue_first.wait()
        await original_seed(services)

    async def boot_first() -> None:
        async with first.lifespan():
            pytest.fail("The first boot must refuse a competing publication")

    monkeypatch.setattr(developer, "_seed", interleaved_seed)
    task = asyncio.create_task(boot_first())
    await seeding.wait()
    async with second.lifespan():
        owner = get_run_substrate()
        continue_first.set()
        with pytest.raises(BaseExceptionGroup) as caught:
            await task
        assert "requires an unpublished" in str(caught.getrepr())
        assert get_run_substrate() is owner
        assert "services" not in first.state
    with pytest.raises(RuntimeError, match="not published"):
        get_run_substrate()


@pytest.mark.asyncio
async def test_fixture_refuses_existing_owner_and_does_not_withdraw_foreign_replacement() -> None:
    from dataclasses import replace

    from lychd.domain.cortex.substrate import set_run_substrate

    first = _app()
    second = _app()
    try:
        async with first.lifespan():
            first_owner = get_run_substrate()
            with pytest.raises(BaseExceptionGroup) as caught:
                async with second.lifespan():
                    pytest.fail("A second owner must be refused")
            assert "requires an unpublished" in str(caught.getrepr())
            assert get_run_substrate() is first_owner
            replacement = replace(first_owner)
            set_run_substrate(replacement)
        assert get_run_substrate() is replacement
        assert "services" not in first.state
    finally:
        reset_run_substrate()


def test_fixture_image_launcher_issues_fresh_credentials_with_fixed_listener(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for key in tuple(developer.os.environ):
        if key.startswith(("LITESTAR_", "GRANIAN_")) or key == "WEB_CONCURRENCY":
            monkeypatch.delenv(key)
    serve = AsyncMock()
    monkeypatch.setattr(developer, "_serve", serve)
    passwords: list[str] = []
    for _ in range(2):
        developer.main(("--caged",))
        output = capsys.readouterr()
        password = output.out.split("Password: ", 1)[1].strip()
        assert len(password) >= 32
        assert password not in output.err
        passwords.append(password)
    assert passwords[0] != passwords[1]
    assert serve.await_count == 2
    assert serve.call_args.kwargs == {"host": "0.0.0.0", "port": 8000}  # noqa: S104 - image listener


@pytest.mark.asyncio
async def test_canvas_fixture_keeps_security_and_admits_only_memory_authoring() -> None:
    """Real HTTP saves remain isolated from Bridge execution and physical transitions."""
    app = developer.create_developer_app(
        access_password=SecretStr(TEST_ACCESS_PASSWORD),
        signing_key=SecretStr("synthetic-canvas-signing-key"),
        canvas_authoring=True,
    )
    async with app.lifespan(), _client(app) as client:
        await client.get("/api/v1/canvas/contracts")
        path = "/api/v1/canvas/workspace/bootstrap"
        assert (await client.post(path)).status_code == 403
        headers = {"origin": _ORIGIN, "x-csrftoken": client.cookies["csrftoken"]}
        assert (await client.post(path, headers={**headers, "authorization": ""})).status_code == 401
        assert (await client.post(path, headers={**headers, "origin": "https://evil.example"})).status_code == 403
        seeded = await client.post(path, headers=headers)
        assert seeded.status_code == 200, seeded.text
        builtin = seeded.json()
        assert builtin["builtin"] is True
        document = builtin["canvas_document"]
        document["scene"].update(id=str(uuid4()), title="Synthetic free drawing", nodes=[], edges=[])
        created = await client.post(
            "/api/v1/canvas/projects", json={"id": str(uuid4()), "canvas_document": document}, headers=headers
        )
        assert created.status_code == 201, created.text
        project = created.json()
        assert project["workspace_state"] == "draft"
        document["scene"]["revision"] += 1
        document["scene"]["strokes"].append(
            {
                "id": str(uuid4()),
                "points": [{"x": 10, "y": 20}, {"x": 40, "y": 50}],
                "color": "#8be7ff",
                "width": 2,
                "archived": False,
            }
        )
        saved = await client.post(
            f"/api/v1/atlas/projects/{project['id']}/changes",
            json={
                "request_id": str(uuid4()),
                "expected_version": project["version"],
                "change": {"kind": "canvas.save", "canvas_document": document},
            },
            headers=headers,
        )
        assert saved.status_code == 200, saved.text
        retained = (await client.get(f"/api/v1/atlas/projects/{project['id']}")).json()
        assert retained["canvas_document"] == document
        catalogue = (await client.get("/api/v1/atlas/projects")).json()
        assert catalogue["pinned"]["id"] == builtin["id"]
        assert [entry["id"] for entry in catalogue["projects"]] == [project["id"]]
        for refused in ("/api/v1/bridge/sessions", "/api/v1/nexus/swaps", "/orchestrator/activate?target=missing"):
            response = await client.post(refused, json={}, headers=headers)
            assert response.status_code == 403, (refused, response.text)
            assert "read-only" in response.json()["detail"]


def _substitute_embedded_transport(
    monkeypatch: pytest.MonkeyPatch, app: Litestar, events: list[str], failure: str
) -> None:
    """Replace only the physical listener, Rust HTTP worker and Rust signal."""
    from granian.constants import Interfaces
    from granian.server import embed

    loop = asyncio.get_running_loop()
    servers: list[embed.Server] = []

    class Socket:
        def is_uds(self) -> bool:
            return False

    def socket(self: embed.Server) -> None:
        assert asyncio.get_running_loop() is loop
        assert self.target is app
        assert self.interface == Interfaces.ASGINL
        assert self.workers == 1
        assert self.runtime_threads == 1
        assert self.blocking_threads == 1
        assert self.bind_addr == "127.0.0.1"
        assert self.bind_port == 8000
        assert self.bind_uds is None
        assert self.env_files == ()
        assert self.metrics_enabled is False
        assert self.reload_on_changes is False
        assert get_run_substrate() is app.state.services.substrate
        self._ssp = Socket()  # pyright: ignore[reportPrivateUsage]
        self._shd = None  # pyright: ignore[reportPrivateUsage]
        servers.append(self)
        events.append("socket")

    class Signal:
        def __init__(self) -> None:
            self.callbacks: list[Callable[[], None]] = []

        def add_cb(self, callback: Callable[[], None]) -> None:
            self.callbacks.append(callback)

        def set(self) -> None:
            for callback in self.callbacks:
                callback()

    class Worker:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def serve_async(self, _scheduler: Any, worker_loop: asyncio.AbstractEventLoop, _shutdown: Any) -> None:
            events.append("serve")
            if failure in {"serve", "serve_and_close"}:
                message = "fixture transport failed"
                raise RuntimeError(message)
            worker_loop.call_soon(servers[0].stop)

    monkeypatch.setattr(embed.Server, "_init_shared_socket", socket)
    monkeypatch.setattr(embed, "WorkerSignal", Signal)
    monkeypatch.setattr(embed, "ASGIWorker", Worker)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["none", "startup", "serve", "close", "startup_and_close", "serve_and_close"])
async def test_fixture_embedded_launcher_propagates_lifecycle_failures(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Exercise actual Server.serve and its worker coroutine around real Litestar lifespan."""
    app = _app()
    events: list[str] = []
    _substitute_embedded_transport(monkeypatch, app, events, failure)
    seed = developer._seed  # pyright: ignore[reportPrivateUsage]
    tickets_close = TicketStore.aclose
    bus_close = InProcessEventBus.aclose

    async def observed_seed(services: AltarServices) -> None:
        events.append("seed")
        await seed(services)
        if failure in {"startup", "startup_and_close"}:
            message = "fixture startup failed"
            raise RuntimeError(message)

    async def observed_tickets_close(self: TicketStore) -> None:
        events.append("tickets")
        await tickets_close(self)
        if failure in {"close", "startup_and_close", "serve_and_close"}:
            message = "fixture cleanup failed"
            raise RuntimeError(message)

    async def observed_bus_close(self: InProcessEventBus) -> None:
        events.append("bus")
        await bus_close(self)

    monkeypatch.setattr(developer, "_seed", observed_seed)
    monkeypatch.setattr(TicketStore, "aclose", observed_tickets_close)
    monkeypatch.setattr(InProcessEventBus, "aclose", observed_bus_close)
    if failure == "none":
        await developer._serve(app, host="127.0.0.1", port=8000)  # pyright: ignore[reportPrivateUsage]
    else:
        with pytest.raises(BaseExceptionGroup) as caught:
            await developer._serve(app, host="127.0.0.1", port=8000)  # pyright: ignore[reportPrivateUsage]
        evidence = str(caught.getrepr())
        if failure.startswith("startup"):
            assert "fixture startup failed" in evidence
        if failure.startswith("serve"):
            assert "fixture transport failed" in evidence
        if "close" in failure:
            assert "fixture cleanup failed" in evidence
    expected = (
        ["seed", "tickets", "bus"] if failure.startswith("startup") else ["seed", "socket", "serve", "tickets", "bus"]
    )
    assert events == expected
    assert "services" not in app.state
    with pytest.raises(RuntimeError, match="not published"):
        get_run_substrate()
