"""`AltarServices` — the one web-layer service container (§TD-5, spec-00-FINAL C6).

Everything the Altar's web surface needs, built once per app lifespan and placed on
`app.state.services`. Replaces the two module-global singleton nests
(`bridge_chat.wire()` and `nexus._TICKETS`). `deps.py` provides only pure readers of
this container; the sole assembly site is `interface/web/lifespan.py`.

Wave 2 keystone: the transitional `RunEngine` facade now delegates to the REAL
`domain/cortex/engine.RunEngine` (swapped internals; `submit()` shape unchanged so
controllers never thread `state=`). The bus/ledger are built here; the real engine
and the process `RunSubstrate` are wired in the lifespan (`wire_runtime`) once the
SAQ queues exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import builtin_workflow_registry
from lychd.config.settings import get_settings
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.engine import QueueRouter
from lychd.domain.cortex.engine import RunEngine as CortexRunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.substrate import RunSubstrate, set_run_substrate
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.projection import Projector
from lychd.domain.web.sessions import BridgeSessionStore
from lychd.domain.web.tickets import TicketStore

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from litestar.contrib.jinja import JinjaTemplateEngine

    from lychd.agents.router import Intent
    from lychd.domain.animation.services.adapters.contracts import SoulstoneRuntimeAdapter
    from lychd.domain.cortex.engine import RunQueue
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.cortex.runs import RunHandle
    from lychd.domain.web.fragments import FragmentRegistry


class QuiescentBroker:
    """A no-op worker broker satisfying `OrchestratorManager`'s drain protocol.

    The v1 in-process profile drains via leases (Wave 3); this stand-in keeps the
    manager happy until the honest `GhoulBroker` lands. Draining is instantaneous
    and the active-worker count is always zero.
    """

    async def pause_queues(self) -> None:
        """Pause intake queues (no-op: lease-drain is Wave 3)."""

    async def broadcast_soft_stop(self) -> None:
        """Ask workers to finish their current job (no-op)."""

    async def unpause_queues(self) -> None:
        """Resume intake queues (no-op)."""

    async def get_active_worker_count(self) -> int:
        """Return the number of still-draining workers (always zero here)."""
        return 0


class RunEngine:
    """Transitional facade over the real `domain/cortex/engine.RunEngine` (C2).

    Controllers call `submit(intent)`; Wave 2 swaps the internals to the real engine
    (`wire_runtime` binds it in the lifespan once the SAQ queues exist), keeping the
    `submit()` shape so the web never changes its call.
    """

    def __init__(self) -> None:
        """Create an unbound facade (the lifespan calls `bind_engine`)."""
        self._engine: CortexRunEngine | None = None

    def bind_engine(self, engine: CortexRunEngine) -> None:
        """Bind the facade to the real, queue-wired engine."""
        self._engine = engine

    def _require(self) -> CortexRunEngine:
        if self._engine is None:  # pragma: no cover - lifespan always wires
            msg = "RunEngine facade is not wired to the real engine."
            raise RuntimeError(msg)
        return self._engine

    async def submit(self, intent: Intent) -> RunHandle:
        """Route, persist QUEUED, and enqueue the run onto SAQ (real engine)."""
        return await self._require().submit(intent)

    async def approve(self, consent_id: str, *, approved: bool) -> None:
        """Consent verdict seam: re-enqueue the parked run (Wave-4 honest resume)."""
        await self._require().approve(consent_id, approved=approved)

    async def cancel(self, run_id: str) -> None:
        """Cancel a run: abort the SAQ job, mark CANCELLED, emit the terminal DONE."""
        await self._require().cancel(run_id)


@dataclass(frozen=True, kw_only=True)
class AltarServices:
    """Everything the web layer needs, built once per app lifespan."""

    registry: AnimatorRegistry
    dispatcher: Dispatcher
    orchestrator: OrchestratorManager
    leases: LeaseLedger
    context_orchestrator: ContextOrchestrator
    fragments: FragmentRegistry
    bridge_sessions: BridgeSessionStore
    tickets: TicketStore
    run_engine: RunEngine
    projector: Projector
    ledger: RunLedger
    bus: InProcessEventBus

    def wire_runtime(self, queues: Mapping[str, RunQueue]) -> CortexRunEngine:
        """Build + publish the run substrate and the real engine (lifespan seam).

        Called once the SAQ queues exist (Topology A: same process). Publishes the
        process `RunSubstrate` (so the in-process ghoul shares this bus) and binds
        the real engine onto the facade.
        """
        substrate = RunSubstrate(
            ledger=self.ledger,
            bus=self.bus,
            workflows=builtin_workflow_registry(),
            orchestrator=self.orchestrator,
            dispatcher=self.dispatcher,
            context=self.context_orchestrator,
            fragments=self.fragments,
            sessions=self.bridge_sessions,
            forge=default_forge(),
        )
        set_run_substrate(substrate)
        engine = CortexRunEngine(
            ledger=self.ledger,
            bus=self.bus,
            workflows=substrate.workflows,
            queue_router=QueueRouter(),
            queues=queues,
        )
        self.run_engine.bind_engine(engine)
        return engine

    async def aclose(self) -> None:
        """Cancel tracked tasks and drain per-run resources on shutdown.

        R10: drain the bus's in-flight ledger-tee/close tasks before returning so a
        tail Step write scheduled just before shutdown is not dropped.
        """
        await self.tickets.aclose()
        await self.bus.aclose()


def _build_run_ledger(profile: str) -> RunLedger:
    """Select the `RunLedger` implementation from the persistence profile (F4/H5, S3).

    ``postgres`` (default) → the durable `DbRunLedger` over the run/step tables;
    ``memory`` → the loop-confined `InMemoryRunLedger` used by DB-free tests. This is
    the one profile flag Wave 4 later extends to the ConsentLedger + SessionStore.
    """
    if profile == "memory":
        return InMemoryRunLedger()
    from lychd.db.engine import get_session_factory
    from lychd.domain.cortex.ledger import DbRunLedger

    return DbRunLedger(session_factory=get_session_factory())


def build_altar_services(
    *,
    template_engine: JinjaTemplateEngine,
    rune_schemas: Sequence[type],
    runtime_adapters: Sequence[SoulstoneRuntimeAdapter],
    profile: str | None = None,
) -> AltarServices:
    """Assemble the `AltarServices` container (the sole construction site).

    The run ledger is chosen by the persistence ``profile`` (defaults to
    ``settings.db.profile`` — ``postgres`` in production, ``memory`` in DB-free
    tests). The bus tees non-TOKEN events into whichever ledger is selected, so the
    choice MUST happen here, before the bus is built.
    """
    if profile is None:
        profile = get_settings().db.profile
    registry = AnimatorRegistry(rune_schemas=rune_schemas, runtime_adapters=runtime_adapters)
    leases = LeaseLedger()  # one per process; Track O threads it onto the substrate + broker
    dispatcher = Dispatcher(registry=registry, leases=leases)
    orchestrator = OrchestratorManager(worker_broker=QuiescentBroker(), registry=registry, leases=leases)
    context_orchestrator = ContextOrchestrator(registry=registry)
    fragments = build_fragment_registry()
    bridge_sessions = BridgeSessionStore()
    tickets = TicketStore()
    projector = Projector(engine=template_engine, fragments=fragments, sessions=bridge_sessions)
    ledger = _build_run_ledger(profile)
    bus = InProcessEventBus(ledger=ledger)
    return AltarServices(
        registry=registry,
        dispatcher=dispatcher,
        orchestrator=orchestrator,
        leases=leases,
        context_orchestrator=context_orchestrator,
        fragments=fragments,
        bridge_sessions=bridge_sessions,
        tickets=tickets,
        run_engine=RunEngine(),
        projector=projector,
        ledger=ledger,
        bus=bus,
    )
