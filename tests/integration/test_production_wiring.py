"""Production-wiring proof (F1/H1): Topology A without ctx injection.

This is the F1 lesson made structural. Every OTHER run test injects the substrate
via ``ctx["run_substrate"]``; this one does NOT. It drives the real composition
seam — `set_run_substrate` publishes ONE substrate, `perform_run` reads it from the
process memo (empty ctx), and submit → QUEUED → RUNNING → DONE + SSE events all flow
on ONE event loop through ONE shared `RunEventBus`.

Two passes:
- DB-free (runs on the Mac / CI): the `memory` persistence profile with an offline
  `TestModel`, replacing only the live dispatcher in the otherwise-real substrate.
- [LINUX] real factory over Postgres: gated behind `testcontainers`; written here,
  deferred to the Linux/PG runtime pass (it forks nothing — `separate_process=False`).
"""
# Structural offline fakes stand in for GrantPort/registry.
# pyright: reportArgumentType=false

from __future__ import annotations

# Litestar's create_test_client callback surface contains third-party Unknowns.
# pyright: reportUnknownVariableType=false
import asyncio
from pathlib import Path
from typing import Any

import pydantic_ai.models
import pytest
from litestar.contrib.jinja import JinjaTemplateEngine
from pydantic_ai.models.test import TestModel

from lychd.agents.router import Intent
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import builtin_workflow_registry
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.engine import QueueRouter
from lychd.domain.cortex.engine import RunEngine as CortexRunEngine
from lychd.domain.cortex.events import RunEventKind
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.substrate import RunSubstrate, reset_run_substrate, set_run_substrate
from lychd.domain.web.altar_services import build_altar_services
from tests.agents.fakes import FakeDispatcher, FakeOrchestrator, FakeRegistry

pydantic_ai.models.ALLOW_MODEL_REQUESTS = False

_TEMPLATES_DIR = Path(__file__).resolve().parents[1].parent / "src" / "lychd" / "domain" / "web" / "templates"


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
                resume=bool(kwargs.get("resume", False)),
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
    engine_template = JinjaTemplateEngine(directory=_TEMPLATES_DIR)
    queues = {"runs": _InProcessQueue(), "rites": _InProcessQueue()}
    services = build_altar_services(
        template_engine=engine_template,
        queues=queues,
        rune_schemas=[],
        runtime_adapters=[],
        profile="memory",  # DB-free: the InMemoryRunLedger
    )
    assert services.run_engine.cancellations is services.substrate.cancellations

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


@pytest.mark.asyncio
async def test_queues_api_reads_real_substrate_zero_injection(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /orchestrator/queues through the REAL composition root — zero substrate injection.

    Exit-gate item 9 (the F1 lesson made structural): `build_altar_services` returns
    one complete substrate, which the lifespan publishes; the controller reads
    the queues from that process memo (NOT an injected value) and the leases from the
    services container, returning real SAQ numbers + live lease rows.
    """
    from contextlib import asynccontextmanager
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import create_test_client

    from lychd.domain.animation.capabilities import GrantLease
    from lychd.domain.animation.schemas.capability_family import CapabilityFamily
    from lychd.domain.cortex.substrate import reset_run_substrate as _reset
    from lychd.domain.cortex.substrate import set_run_substrate as _publish
    from lychd.interface.api.orchestrator import OrchestratorController
    from lychd.interface.web.deps import web_dependencies

    # This focused controller app intentionally omits the production auth
    # middleware; select the documented test/dev guard floor explicitly.
    monkeypatch.setattr(
        "lychd.domain.codex.guards.get_settings",
        lambda: SimpleNamespace(sigil=SimpleNamespace(enforce=False)),
    )

    engine_template = JinjaTemplateEngine(directory=_TEMPLATES_DIR)
    queues = {"runs": _InfoQueue(queued=3, active=1), "rites": _InfoQueue(queued=0, active=0)}
    services = build_altar_services(
        template_engine=engine_template,
        queues=queues,
        rune_schemas=[],
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

    @asynccontextmanager
    async def _lifespan(app: Litestar) -> Any:
        app.state.services = services
        yield

    try:
        with create_test_client(
            route_handlers=[OrchestratorController],
            dependencies=web_dependencies,
            lifespan=[_lifespan],
        ) as client:
            resp = client.get("/orchestrator/queues")
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
def test_production_wiring_real_factory_over_postgres() -> None:
    """[LINUX] End-to-end through the REAL `create_app()` factory on Postgres.

    Written here, DEFERRED to the Linux/PG runtime pass (skipped where `testcontainers`
    is absent, i.e. the Mac dev box). Under Topology A the SAQ worker runs in-process
    (`separate_process=False`) on the web loop, so this proves — with zero substrate
    injection — that submitting through the Bridge drives a run to DONE and its SSE
    stream carries the events, over the durable `DbRunLedger`.
    """
    pytest.importorskip("testcontainers", reason="[LINUX] PG runtime pass only")

    # Skeleton of the Linux pass (kept unrun on the Mac):
    #   1. PostgresContainer("pgvector/pgvector:pg18") → set DB_* env + DB_PROFILE=postgres.
    #   2. Apply migration 0001 (alembic upgrade head).
    #   3. app = create_app(); with TestClient(app) as client:  (on_app_startup launches
    #      the in-process worker on the web loop — no forks).
    #   4. POST /bridge/{session}/messages → 200; GET /bridge/runs/{id}/stream →
    #      status→…→done; assert the Run row is DONE and Step.seq == emit order.
    pytest.skip("[LINUX] production-wiring over real Postgres — deferred to the Linux runtime pass")
