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
from lychd.domain.cortex.engine import QueueRouter, RouteRule
from lychd.domain.cortex.engine import RunEngine as CortexRunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.substrate import RunSubstrate, set_run_substrate
from lychd.domain.orchestration.arbiter import TransitionArbiter
from lychd.domain.orchestration.broker import GhoulBroker, QuiescentBroker
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.policies import resolve_switch_policy
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.projection import Projector
from lychd.domain.web.tickets import TicketStore

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from litestar.contrib.jinja import JinjaTemplateEngine

    from lychd.agents.router import Intent
    from lychd.domain.animation.services.adapters.contracts import PortalRuntimeFactory, SoulstoneRuntimeAdapter
    from lychd.domain.codex.ledger import ConsentLedger
    from lychd.domain.cortex.engine import RunQueue
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.cortex.runs import RunHandle
    from lychd.domain.web.fragments import FragmentRegistry
    from lychd.domain.web.sessions import SessionStorePort


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
    bridge_sessions: SessionStorePort
    consents: ConsentLedger
    tickets: TicketStore
    run_engine: RunEngine
    projector: Projector
    ledger: RunLedger
    bus: InProcessEventBus

    def wire_runtime(self, queues: Mapping[str, RunQueue]) -> CortexRunEngine:
        """Build + publish the run substrate and the real engine (lifespan seam).

        Called once the SAQ queues exist (Topology A: same process). The queues are
        born HERE, so this is where the honest `GhoulBroker` late-binds onto the
        orchestrator's plain `worker_broker` attribute (the `QuiescentBroker` was the
        pre-wire stand-in; with an empty queue map `GhoulBroker` is inert and drain
        still answers from leases). Publishes the process `RunSubstrate` (so the
        in-process ghoul shares this bus + lease ledger) and binds the real engine.
        """
        self.orchestrator.worker_broker = GhoulBroker(queues=queues, leases=self.leases)
        substrate = RunSubstrate(
            ledger=self.ledger,
            bus=self.bus,
            workflows=builtin_workflow_registry(),
            orchestrator=self.orchestrator,
            dispatcher=self.dispatcher,
            context=self.context_orchestrator,
            fragments=self.fragments,
            turns=self.bridge_sessions,
            consents=self.consents,
            forge=default_forge(),
            leases=self.leases,
            queues=queues,
            stasis_dir=get_settings().stasis.dir,
        )
        set_run_substrate(substrate)
        engine = CortexRunEngine(
            ledger=self.ledger,
            bus=self.bus,
            workflows=substrate.workflows,
            queue_router=QueueRouter(routing=_routing_from_settings()),
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


def _routing_from_settings() -> dict[str, RouteRule]:
    """Convert the `[orchestration.routing]` settings table into engine `RouteRule`s."""
    routing = get_settings().orchestration.routing
    return {source: RouteRule(queue=rule.queue, priority=rule.priority) for source, rule in routing.items()}


def _build_run_ledger(profile: str) -> RunLedger:
    """Select the `RunLedger` implementation from the persistence profile (F4/H5, S3).

    ``postgres`` (default) → the durable `DbRunLedger` over the run/step tables;
    ``memory`` → the loop-confined `InMemoryRunLedger` used by DB-free tests. This is
    the one profile flag Wave 4 extends to the ConsentLedger + SessionStore.
    """
    if profile == "memory":
        return InMemoryRunLedger()
    from lychd.db.engine import get_session_factory
    from lychd.domain.cortex.ledger import DbRunLedger

    return DbRunLedger(session_factory=get_session_factory())


def _build_session_store(profile: str) -> SessionStorePort:
    """Select the `SessionStore` from the SAME persistence profile (§3.5; third leg).

    ``memory`` → the loop-confined `BridgeSessionStore`; ``postgres`` →
    `DbBridgeSessionStore` over the `session` table (survives a restart).
    """
    from lychd.domain.web.sessions import BridgeSessionStore

    if profile == "memory":
        return BridgeSessionStore()
    from lychd.db.engine import get_session_factory
    from lychd.domain.web.sessions import DbBridgeSessionStore

    return DbBridgeSessionStore(get_session_factory(), sigil_name=get_settings().sigil.name)


def _build_consent_ledger(profile: str) -> ConsentLedger:
    """Select the `ConsentLedger` from the SAME persistence profile (§3.5; no second flag).

    ``memory`` → `InMemoryConsentLedger` (process-local, pairs with the in-memory run
    ledger); ``postgres`` → `CodexConsentLedger` over the consent/preauth tables.
    """
    from lychd.domain.codex.ledger import InMemoryConsentLedger

    if profile == "memory":
        return InMemoryConsentLedger()
    from lychd.db.engine import get_session_factory
    from lychd.domain.codex.ledger import CodexConsentLedger

    return CodexConsentLedger(session_factory=get_session_factory())


def build_altar_services(
    *,
    template_engine: JinjaTemplateEngine,
    rune_schemas: Sequence[type],
    runtime_adapters: Sequence[SoulstoneRuntimeAdapter],
    portal_factories: Sequence[PortalRuntimeFactory] = (),
    profile: str | None = None,
) -> AltarServices:
    """Assemble the `AltarServices` container (the sole construction site).

    The run ledger is chosen by the persistence ``profile`` (defaults to
    ``settings.db.profile`` — ``postgres`` in production, ``memory`` in DB-free
    tests). The bus tees non-TOKEN events into whichever ledger is selected, so the
    choice MUST happen here, before the bus is built.
    """
    settings = get_settings()
    if profile is None:
        profile = settings.db.profile
    registry = AnimatorRegistry(
        rune_schemas=rune_schemas,
        runtime_adapters=runtime_adapters,
        portal_factories=portal_factories,
    )
    leases = LeaseLedger()  # one per process; threaded onto the substrate + broker in wire_runtime
    dispatcher = Dispatcher(registry=registry, leases=leases)
    switching = settings.orchestration.switching
    orchestrator = OrchestratorManager(
        QuiescentBroker(),  # pre-wire stand-in; wire_runtime late-binds the GhoulBroker
        registry,
        leases=leases,
        policy=resolve_switch_policy(switching.policy),
        arbiter=TransitionArbiter(),
        switching=switching,
    )
    context_orchestrator = ContextOrchestrator(registry=registry)
    fragments = build_fragment_registry()
    bridge_sessions = _build_session_store(profile)
    consents = _build_consent_ledger(profile)
    tickets = TicketStore()
    projector = Projector(engine=template_engine, fragments=fragments, sessions=bridge_sessions, consents=consents)
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
        consents=consents,
        tickets=tickets,
        run_engine=RunEngine(),
        projector=projector,
        ledger=ledger,
        bus=bus,
    )
