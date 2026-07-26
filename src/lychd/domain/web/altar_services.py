"""`AltarServices` — the one fully constructed web-layer service container.

Everything the Altar and in-process ghoul need is assembled once per app lifespan
and placed on ``app.state.services``.  The queue map is a required input: there is
no pre-wire broker, unbound engine facade, or post-construction dependency mutation.
``deps.py`` contains only pure readers; ``interface/web/lifespan.py`` is the sole
assembly and publication site.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from lychd.agents.services import default_sigil
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import builtin_workflow_registry
from lychd.config.settings.root import get_settings
from lychd.domain.animation.services.declarations import (
    compile_animator_declarations,
)
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.cancellation import RunCancellationCoordinator
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.orchestration.arbiter import TransitionArbiter
from lychd.domain.orchestration.broker import GhoulBroker
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.policies import resolve_switch_policy
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.projection import EventProjector
from lychd.domain.web.tickets import TicketStore
from lychd.system.services.runtime import build_runtime_actuator

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from lychd.config.runes.registry import RuneRegistry
    from lychd.config.settings.root import Settings
    from lychd.domain.animation.services.adapters.contracts import PortalRuntimeFactory, SoulstoneRuntimeAdapter
    from lychd.domain.codex.ledger import ConsentLedger
    from lychd.domain.cortex.engine import RunQueue
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.web.fragments import FragmentRegistry
    from lychd.domain.web.sessions import SessionStorePort


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
    projector: EventProjector
    ledger: RunLedger
    bus: InProcessEventBus
    substrate: RunSubstrate

    async def aclose(self) -> None:
        """Cancel tracked tasks and drain per-run resources on shutdown.

        R10: drain the bus's in-flight ledger-tee/close tasks before returning so a
        tail Step write scheduled just before shutdown is not dropped.
        """
        await self.tickets.aclose()
        await self.bus.aclose()


def _routing_from_settings(settings: Settings) -> dict[str, RouteRule]:
    """Convert the `[orchestration.routing]` settings table into engine `RouteRule`s."""
    routing = settings.orchestration.routing
    return {source: RouteRule(queue=rule.queue, priority=rule.priority) for source, rule in routing.items()}


def _validate_routed_queues(routing: Mapping[str, RouteRule], queues: Mapping[str, RunQueue]) -> None:
    """Reject a composition that can persist work onto a nonexistent queue."""
    required = {rule.queue for rule in routing.values()}
    missing = sorted(required.difference(queues))
    if missing:
        names = ", ".join(missing)
        msg = f"Run routing references unavailable queue(s): {names}."
        raise RuntimeError(msg)


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


def _build_session_store(profile: str, *, sigil_name: str) -> SessionStorePort:
    """Select the `SessionStore` from the SAME persistence profile (§3.5; third leg).

    ``memory`` → the loop-confined `BridgeSessionStore`; ``postgres`` →
    `DbBridgeSessionStore` over the `session` table (survives a restart).
    """
    from lychd.domain.web.sessions import BridgeSessionStore

    if profile == "memory":
        return BridgeSessionStore()
    from lychd.db.engine import get_session_factory
    from lychd.domain.web.sessions import DbBridgeSessionStore

    return DbBridgeSessionStore(get_session_factory(), sigil_name=sigil_name)


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
    queues: Mapping[str, RunQueue],
    runes: RuneRegistry,
    runtime_adapters: Sequence[SoulstoneRuntimeAdapter],
    portal_factories: Sequence[PortalRuntimeFactory] = (),
    profile: str | None = None,
    settings: Settings | None = None,
) -> AltarServices:
    """Assemble the `AltarServices` container (the sole construction site).

    The run ledger is chosen by the persistence ``profile`` (defaults to
    ``settings.server.database.profile`` — ``postgres`` in production, ``memory`` in DB-free
    tests). The bus tees non-TOKEN events into whichever ledger is selected, so the
    choice MUST happen here, before the bus is built.
    """
    if settings is None:
        settings = get_settings()
    if profile is None:
        profile = settings.server.database.profile
    routing = _routing_from_settings(settings)
    policy = resolve_switch_policy(settings.orchestration.switching.policy)
    _validate_routed_queues(routing, queues)
    registry = AnimatorRegistry(
        settings=settings,
        declarations=compile_animator_declarations(
            settings=settings,
            runes=runes,
        ),
        runtime_adapters=runtime_adapters,
        portal_factories=portal_factories,
    )
    leases = LeaseLedger()
    dispatcher = Dispatcher(registry=registry, leases=leases)
    switching = settings.orchestration.switching
    worker_broker = GhoulBroker(queues=queues, leases=leases)
    orchestrator = OrchestratorManager(
        worker_broker,
        registry,
        leases=leases,
        policy=policy,
        arbiter=TransitionArbiter(),
        actuator=build_runtime_actuator(switching, registry),
        switching=switching,
    )
    context_orchestrator = ContextOrchestrator(registry=registry)
    fragments = build_fragment_registry()
    bridge_sessions = _build_session_store(profile, sigil_name=default_sigil().name)
    consents = _build_consent_ledger(profile)
    tickets = TicketStore()
    projector = EventProjector(fragments=fragments, sessions=bridge_sessions, consents=consents)
    ledger = _build_run_ledger(profile)
    bus = InProcessEventBus(ledger=ledger)
    workflows = builtin_workflow_registry()
    cancellations = RunCancellationCoordinator()
    if profile == "postgres":
        from lychd.db.checkpoints import PostgresStasisStore
        from lychd.db.engine import get_session_factory

        stasis_store = PostgresStasisStore(get_session_factory())
    else:
        from lychd.domain.cortex.stasis import InMemoryStasisStore

        stasis_store = InMemoryStasisStore()
    substrate = RunSubstrate(
        ledger=ledger,
        bus=bus,
        workflows=workflows,
        orchestrator=orchestrator,
        dispatcher=dispatcher,
        context=context_orchestrator,
        fragments=fragments,
        turns=bridge_sessions,
        consents=consents,
        forge=default_forge(),
        sigil_provider=default_sigil,
        leases=leases,
        queues=queues,
        cancellations=cancellations,
        stasis_store=stasis_store,
    )
    run_engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=workflows,
        queue_router=QueueRouter(routing=routing),
        queues=queues,
        cancellations=cancellations,
        stasis_store=stasis_store,
    )
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
        run_engine=run_engine,
        projector=projector,
        ledger=ledger,
        bus=bus,
        substrate=substrate,
    )
