"""Production-wiring proof (F1/H1): Topology A without ctx injection.

This is the F1 lesson made structural. Every OTHER run test injects the substrate
via ``ctx["run_substrate"]``; this one does NOT. It drives the real composition
seam — `set_run_substrate` publishes ONE substrate, `perform_run` reads it from the
process memo (empty ctx), and submit → QUEUED → RUNNING → DONE + SSE events all flow
on ONE event loop through ONE shared `RunEventBus`.

Three passes:
- DB-free (runs on the Mac / CI): the `memory` persistence profile with an offline
  `TestModel`, replacing only the live dispatcher in the otherwise-real substrate.
- real factory over Postgres: gated only by `testcontainers`/Docker; it boots the
  actual app and in-process SAQ worker twice around one durable run.
"""
# Structural offline fakes stand in for GrantPort/registry.
# pyright: reportArgumentType=false
# pyright: reportMissingImports=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false

from __future__ import annotations

# Litestar's create_test_client callback surface contains third-party Unknowns.
# pyright: reportUnknownVariableType=false
import asyncio
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx
import pydantic_ai.models
import pytest
from pydantic_ai.models.test import TestModel

from lychd.agents.router import Intent
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import builtin_workflow_registry
from lychd.config.runes.registry import RuneRegistry
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.engine import QueueRouter
from lychd.domain.cortex.engine import RunEngine as CortexRunEngine
from lychd.domain.cortex.events import RunEventKind
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate, reset_run_substrate, set_run_substrate
from lychd.domain.web.altar_services import build_altar_services
from tests.agents.fakes import FakeDispatcher, FakeOrchestrator, FakeRegistry

pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


class _InProcessQueue:
    """A SAQ-queue stand-in that runs `perform_run` on the loop with an EMPTY ctx.

    The empty ctx is the whole point: `perform_run` must resolve the substrate from
    the process memo (`get_run_substrate`), NOT from an injected `ctx["run_substrate"]`.
    """

    def __init__(self) -> None:
        self.tasks: list[asyncio.Task[Any]] = []

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
        from lychd.ghouls.runs import perform_run

        _ = job_or_func
        task = asyncio.create_task(
            perform_run(
                {},  # NO ctx["run_substrate"] — reads the published process memo
                run_id=kwargs["run_id"],
                enqueue_seq=int(kwargs["enqueue_seq"]),
            )
        )
        self.tasks.append(task)

    async def job(self, job_key: str, /) -> Any:
        _ = job_key
        return None

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (job, error, ttl)


@pytest.mark.asyncio
async def test_production_wiring_no_injection_queued_running_done_and_sse() -> None:
    """Submit → QUEUED → RUNNING → DONE + SSE, all on one loop, substrate read from the memo."""
    queues = {"runs": _InProcessQueue(), "rites": _InProcessQueue()}
    services = build_altar_services(
        queues=queues,
        runes=RuneRegistry(()),
        runtime_adapters=[],
        profile="memory",  # DB-free: the InMemoryRunLedger
    )
    assert services.run_engine.cancellations is services.substrate.cancellations
    assert services.workflows is services.run_engine.workflows
    assert services.workflows is services.substrate.workflows

    # Replace the live dispatcher with an offline one so the graph completes without
    # a Soulstone. The publication and worker lookup still use the production memo path.
    model = TestModel(custom_output_args={"answer": "risen", "fragments": []}, call_tools=[])
    substrate = RunSubstrate(
        ledger=services.ledger,
        bus=services.bus,
        workflows=builtin_workflow_registry(),
        orchestrator=FakeOrchestrator(),
        dispatcher=FakeDispatcher(model=model),
        context=ContextOrchestrator(registry=FakeRegistry()),
        fragments=services.fragments,
        turns=services.bridge_sessions,
        forge=default_forge(),
        cancellations=services.substrate.cancellations,
    )
    set_run_substrate(substrate)
    engine = CortexRunEngine(
        ledger=services.ledger,
        bus=services.bus,
        workflows=substrate.workflows,
        queue_router=QueueRouter(),
        queues=queues,
        cancellations=substrate.cancellations,
    )

    try:
        session = await services.bridge_sessions.create_session()
        handle = await engine.submit(Intent(session_id=session.id, prompt="raise the dead", source="bridge"))

        # The run was persisted QUEUED before the ghoul claimed it (canonical id, S3).
        assert handle.run_id
        queued = await services.ledger.get(handle.run_id)
        assert queued is not None

        # Subscribe on the SAME bus and observe the run reach DONE (never-hang: DONE ends it).
        seen: list[RunEventKind] = []
        async for event in services.bus.subscribe(handle.run_id):
            seen.append(event.kind)
            if event.kind is RunEventKind.DONE:
                break

        assert RunEventKind.STATUS in seen  # RUNNING status crossed the shared bus
        assert seen[-1] is RunEventKind.DONE  # single terminal ended the stream

        settled = await services.ledger.get(handle.run_id)
        assert settled is not None
        assert settled.status is RunStatus.DONE  # QUEUED → RUNNING → DONE
        assert settled.started_at is not None
        assert settled.finished_at is not None
    finally:
        reset_run_substrate()
        await services.aclose()


class _InfoQueue:
    """A SAQ-queue stand-in exposing `info()` — for the queues-API production-root test."""

    def __init__(self, *, queued: int, active: int) -> None:
        self._info = {"queued": queued, "active": active, "name": "runs"}

    async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> Any:
        _ = (job_or_func, kwargs)

    async def job(self, job_key: str, /) -> Any:
        _ = job_key
        return None

    async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
        _ = (job, error, ttl)

    async def info(self, jobs: bool = False, offset: int = 0, limit: int = 10) -> dict[str, Any]:  # noqa: FBT001, FBT002
        _ = (jobs, offset, limit)
        return dict(self._info)


def _configure_postgres_app_environment(
    monkeypatch: pytest.MonkeyPatch,
    *,
    pg_url: str,
    reactor_inbox: Path,
) -> None:
    """Point the real application factory at one disposable deployment."""
    parsed = urlsplit(pg_url)
    for key in (
        "GRANIAN_RELOAD",
        "GRANIAN_WORKERS",
        "LITESTAR_RELOAD",
        "LITESTAR_WEB_CONCURRENCY",
        "WEB_CONCURRENCY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(sys, "argv", ["python"])
    monkeypatch.setattr(sys, "orig_argv", ["python"])
    monkeypatch.setenv("LYCHD_APP_SECRET_KEY", "test-app-secret")
    monkeypatch.setenv("LYCHD_DB_PASSWORD", unquote(parsed.password or "test"))
    monkeypatch.setenv("SERVER__PORT", "7134")
    monkeypatch.setenv("SERVER__DATABASE__PROFILE", "postgres")
    monkeypatch.setenv("SERVER__DATABASE__HOST", parsed.hostname or "localhost")
    monkeypatch.setenv("SERVER__DATABASE__PORT", str(parsed.port or 5432))
    monkeypatch.setenv("SERVER__DATABASE__USER", unquote(parsed.username or "test"))
    monkeypatch.setenv("SERVER__DATABASE__DATABASE", parsed.path.lstrip("/"))
    monkeypatch.setenv("ORCHESTRATION__SWITCHING__ACTUATOR", "host-reactor")
    monkeypatch.setenv("ORCHESTRATION__SWITCHING__HOST_REACTOR_DIR", str(reactor_inbox))


def _migrate_postgres(pg_url: str) -> None:
    """Apply the same linear Alembic head the production plugin declares."""
    from advanced_alchemy.alembic.commands import AlembicCommandConfig
    from alembic import command
    from sqlalchemy.ext.asyncio import create_async_engine

    from lychd.config.constants import DB_MIGRATION_VERSION_TABLE, PATH_MIGRATION_CONFIG

    command.upgrade(
        AlembicCommandConfig(
            engine=create_async_engine(pg_url),
            version_table_name=DB_MIGRATION_VERSION_TABLE,
            file_=PATH_MIGRATION_CONFIG,
            render_as_batch=False,
        ),
        "head",
    )


def _install_minimal_extensions() -> None:
    """Install one empty, explicit extension generation for the lifecycle test."""
    from lychd.extensions.host import AssembledExtensions, install_extensions, reset_extensions
    from lychd.extensions.manager import ExtensionManager

    reset_extensions()
    context = ExtensionManager(builtins=(), crypt=()).assemble()
    install_extensions(AssembledExtensions(context=context, active_ids=()))


def _configure_offline_dispatch(app: Any) -> None:
    """Replace only unavailable model/hardware collaborators after real startup."""
    services = app.state.services
    model = TestModel(custom_output_args={"answer": "risen", "fragments": []}, call_tools=[])
    services.substrate.dispatcher = FakeDispatcher(model=model)
    services.substrate.orchestrator = FakeOrchestrator()
    services.substrate.context = ContextOrchestrator(registry=FakeRegistry())


def _csrf_headers(client: Any) -> dict[str, str]:
    """Acquire the production CSRF cookie/header contract."""
    status = client.get("/api/v1/altar/status")
    assert status.status_code == 200
    csrf = client.cookies.get("csrftoken")
    assert csrf is not None
    return {"x-csrftoken": csrf}


def _submit_and_wait_done(client: Any) -> tuple[str, dict[str, Any]]:
    """Submit through Bridge and wait for the in-process SAQ worker to settle."""
    headers = _csrf_headers(client)
    created = client.post("/api/v1/bridge/sessions", headers=headers)
    assert created.status_code == 201
    session_id = created.json()["session"]["id"]
    accepted = client.post(
        f"/api/v1/bridge/sessions/{session_id}/messages",
        json={"prompt": "raise the durable dead", "request_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert accepted.status_code == 200
    run_id = accepted.json()["run_id"]

    deadline = time.monotonic() + 15
    projection: dict[str, Any] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/bridge/runs/{run_id}")
        assert response.status_code == 200
        projection = response.json()
        if projection["terminal"]:
            break
        time.sleep(0.05)
    return run_id, projection


def _assert_done_projection(projection: dict[str, Any]) -> None:
    """Require terminal Bridge truth."""
    assert projection["terminal"] is True
    assert projection["run_status"] == "done"


def _assert_orb_done(client: Any, run_id: str) -> None:
    """Require the durable Orb page to retain a gapless terminal trail."""
    response = client.get(f"/api/v1/orb/runs/{run_id}?limit=100")
    assert response.status_code == 200
    evidence = response.json()["evidence"]
    assert [event["seq"] for event in evidence] == list(range(len(evidence)))
    assert evidence[-1]["kind"] == "done"


@pytest.mark.asyncio
async def test_queues_api_reads_real_substrate_zero_injection(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /orchestrator/queues through the REAL composition root — zero substrate injection.

    Exit-gate item 9 (the F1 lesson made structural): `build_altar_services` returns
    one complete substrate, which the lifespan publishes; the controller reads
    the queues from that process memo (NOT an injected value) and the leases from the
    services container, returning real SAQ numbers + live lease rows.
    """
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.datastructures import State

    from lychd.domain.animation.capabilities import GrantLease
    from lychd.domain.animation.schemas.capability_family import CapabilityFamily
    from lychd.domain.codex.middleware import sigil_auth_middleware
    from lychd.domain.cortex.substrate import reset_run_substrate as _reset
    from lychd.domain.cortex.substrate import set_run_substrate as _publish
    from lychd.interface.api.orchestrator import OrchestratorController
    from lychd.interface.web.deps import web_dependencies

    queues = {"runs": _InfoQueue(queued=3, active=1), "rites": _InfoQueue(queued=0, active=0)}
    services = build_altar_services(
        queues=queues,
        runes=RuneRegistry(()),
        runtime_adapters=[],
        profile="memory",
    )
    _publish(services.substrate)

    # A live lease so the API's lease view is exercised.
    spec = SimpleNamespace(key="titan:chat:m", animator_name="titan")
    grant = SimpleNamespace(
        lease=GrantLease(grant_id="lease-1", holder="run:z", issued_at=datetime.now(UTC)), spec=spec
    )
    services.leases.acquire(grant, priority=70)
    _ = CapabilityFamily  # imported for parity with the rest of the suite

    try:
        app = Litestar(
            route_handlers=[OrchestratorController],
            dependencies=web_dependencies,
            middleware=[sigil_auth_middleware()],
            state=State({"services": services}),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver.local",
        ) as client:
            resp = await client.get("/orchestrator/queues")
        assert resp.status_code == 200
        body = resp.json()
        depths = {q["name"]: q for q in body["queues"]}
        assert depths["runs"]["depth"] == 3
        assert depths["runs"]["active"] == 1
        assert depths["runs"]["paused"] is False  # GhoulBroker claim gate open
        assert [row["grant_id"] for row in body["leases"]] == ["lease-1"]
        assert body["leases"][0]["capability_key"] == "titan:chat:m"
    finally:
        _reset()
        await services.aclose()


@pytest.mark.integration
@pytest.mark.container
def test_production_wiring_real_factory_over_postgres_survives_second_boot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Run the real app + SAQ + PostgreSQL composition and recover it on boot two."""
    pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

    from litestar.testing import TestClient
    from testcontainers.community.postgres import PostgresContainer

    from lychd.app import create_app
    from lychd.config.runes import registry as rune_registry_module
    from lychd.config.settings.root import get_settings
    from lychd.db.engine import dispose_engine
    from lychd.extensions.host import AssembledExtensions, reset_extensions

    def empty_rune_registry(
        _extensions: AssembledExtensions,
        runes_dir: Path | None = None,
    ) -> RuneRegistry:
        _ = runes_dir
        return RuneRegistry(())

    reactor_root = tmp_path / "reactor"
    reactor_inbox = reactor_root / "inbox"
    reactor_journal = reactor_root / "journal"
    reactor_inbox.mkdir(parents=True)
    reactor_journal.mkdir()
    reactor_inbox.chmod(0o700)
    reactor_journal.chmod(0o700)

    monkeypatch.setattr(
        rune_registry_module,
        "load_rune_registry",
        empty_rune_registry,
    )
    _install_minimal_extensions()

    try:
        with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as pg:
            pg_url = pg.get_connection_url()
            _configure_postgres_app_environment(
                monkeypatch,
                pg_url=pg_url,
                reactor_inbox=reactor_inbox,
            )
            get_settings.cache_clear()
            asyncio.run(dispose_engine())
            _migrate_postgres(pg_url)

            app = create_app()
            with TestClient(app=app, base_url="http://127.0.0.1:7134") as client:
                _configure_offline_dispatch(app)
                headers = _csrf_headers(client)
                assert client.get("/api/v1/bridge/sessions/not-a-uuid").status_code == 404
                assert client.get("/api/v1/bridge/runs/not-a-uuid").status_code == 404
                assert (
                    client.post(
                        "/api/v1/bridge/consents/not-a-uuid/decision",
                        json={"verdict": "approve"},
                        headers=headers,
                    ).status_code
                    == 404
                )
                run_id, projection = _submit_and_wait_done(client)
                _assert_done_projection(projection)
                _assert_orb_done(client, run_id)

            asyncio.run(dispose_engine())
            second_app = create_app()
            with TestClient(app=second_app, base_url="http://127.0.0.1:7134") as second_client:
                restored = second_client.get(f"/api/v1/bridge/runs/{run_id}")
                assert restored.status_code == 200
                _assert_done_projection(restored.json())
                _assert_orb_done(second_client, run_id)
    finally:
        asyncio.run(dispose_engine())
        reset_extensions()
        get_settings.cache_clear()
