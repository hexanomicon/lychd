"""Application-layer assembly for the fully constructed `AltarServices` container.

Everything the Altar and in-process ghoul need is constructed once per app lifespan
and published on ``app.state.services``. The queue map is a required input: there is
no pre-wire broker, unbound engine facade, or post-construction dependency mutation.
This module owns persistence and system-adapter selection; domain modules supply the
contracts and services without assembling the application graph.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from lychd.agents.services import default_sigil
from lychd.agents.the_first_one import default_forge
from lychd.agents.workflows import BuiltinWorkflowRegistry, builtin_workflow_registry
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
from lychd.domain.delegation.services import (
    DelegatedAgentCoordinator,
    InMemoryDelegatedAgentJobStore,
)
from lychd.domain.orchestration.arbiter import TransitionArbiter
from lychd.domain.orchestration.broker import GhoulBroker
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.policies import resolve_switch_policy
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.projection import EventProjector
from lychd.domain.web.tickets import TicketStore
from lychd.system.services.queues import protect_run_queues
from lychd.system.services.runtime import build_runtime_actuator

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from lychd.agents.factory import AgentForge
    from lychd.agents.workflows import WorkflowRegistry
    from lychd.compositions.creation.services import InvestigationService
    from lychd.config.runes.registry import RuneRegistry
    from lychd.config.settings.root import Settings
    from lychd.domain.animation.extension import RegisteredPortalDefinition, RegisteredSoulstoneDefinition
    from lychd.domain.animation.services.adapters.contracts import PortalDefinition, SoulstoneRuntimeAdapter
    from lychd.domain.archive import ArchiveProfile, ArchiveService, ArchiveSubject
    from lychd.domain.archive.derivation_service import ArchiveDerivationService
    from lychd.domain.codex.ledger import ConsentLedger
    from lychd.domain.codex.local_access import LocalOperatorAccess
    from lychd.domain.codex.sigil import Sigil
    from lychd.domain.cortex.engine import RunQueue
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.delegation.ports import DelegatedAgentRuntime
    from lychd.domain.delegation.routing import DelegatedRuntimeBinding
    from lychd.domain.orchestration.actuator import RuntimeActuator
    from lychd.domain.orchestration.containment import SoftActivationGuard
    from lychd.domain.scout.profile import ScoutProfile
    from lychd.domain.web.atlas import AtlasStorePort
    from lychd.domain.web.consent_reviews import ConsentReviewProducer
    from lychd.domain.web.fragments import FragmentRegistry
    from lychd.domain.web.sessions import SessionStorePort
    from lychd.domain.web.swap_requests import SwapRequestLedger
    from lychd.extensions.delegation import RegisteredDelegatedRuntime
    from lychd.interface.web.scout_admission import ScoutAdmissionService
    from lychd.system.services.scout_workflow import ScoutWorkflowService


@dataclass(frozen=True, kw_only=True)
class AltarServices:
    """Everything the application publishes to web handlers and in-process workers."""

    registry: AnimatorRegistry
    dispatcher: Dispatcher
    orchestrator: OrchestratorManager
    leases: LeaseLedger
    fragments: FragmentRegistry
    bridge_sessions: SessionStorePort
    atlas: AtlasStorePort
    consents: ConsentLedger
    tickets: TicketStore
    swap_requests: SwapRequestLedger
    workflows: WorkflowRegistry
    run_engine: RunEngine
    projector: EventProjector
    ledger: RunLedger
    bus: InProcessEventBus
    substrate: RunSubstrate
    creation: InvestigationService | None = None
    archive: ArchiveService | None = None
    archive_derivation: ArchiveDerivationService | None = None
    delegates: DelegatedAgentCoordinator | None
    delegated_runtime_catalog: tuple[RegisteredDelegatedRuntime, ...]
    scout: ScoutWorkflowService | None = None
    scout_admission: ScoutAdmissionService | None = None

    async def aclose(self) -> None:
        """Cancel tracked tasks and drain pending ledger writes before shutdown."""
        failures: list[BaseException] = []
        if self.scout is not None:
            self.scout.fence_all("service_close")
            try:
                await self.scout.contain_all()
            except BaseException as exc:  # noqa: BLE001 - retain containment uncertainty
                failures.append(exc)
        for close in (self.tickets.aclose, self.bus.aclose):
            try:
                await close()
            except BaseException as exc:  # noqa: BLE001 - drain every owner and preserve cancellation
                failures.append(exc)
        if len(failures) == 1:
            raise failures[0]
        if failures:
            message = "Altar service closure failed."
            raise BaseExceptionGroup(message, failures)


def _validate_routed_queues(routing: Mapping[str, RouteRule], queues: Mapping[str, RunQueue]) -> None:
    """Reject a composition that can persist work onto a nonexistent queue."""
    required = {rule.queue for rule in routing.values()}
    missing = sorted(required.difference(queues))
    if missing:
        names = ", ".join(missing)
        msg = f"Run routing references unavailable queue(s): {names}."
        raise RuntimeError(msg)


def _build_run_ledger(profile: str, settings: Settings) -> RunLedger:
    """Select the Run ledger from the shared persistence profile."""
    if profile == "memory":
        return InMemoryRunLedger()
    from functools import partial

    from lychd.db.claim_observer import observe_claim
    from lychd.db.engine import get_session_factory
    from lychd.domain.cortex.ledger import DbRunLedger

    return DbRunLedger(
        session_factory=get_session_factory(),
        claim_observer=partial(observe_claim, settings=settings.server.database),
    )


def _build_session_store(profile: str, *, sigil_name: str) -> SessionStorePort:
    """Select the Bridge session store from the shared persistence profile."""
    from lychd.domain.web.sessions import BridgeSessionStore

    if profile == "memory":
        return BridgeSessionStore(sigil_name=sigil_name)
    from lychd.db.engine import get_session_factory
    from lychd.db.sessions import DbBridgeSessionStore

    return DbBridgeSessionStore(get_session_factory(), sigil_name=sigil_name)


def _build_atlas_store(profile: str) -> AtlasStorePort:
    """Use the shared persistence profile for Project planning records."""
    from lychd.domain.web.atlas import InMemoryAtlasStore

    if profile == "memory":
        return InMemoryAtlasStore()
    from lychd.db.atlas import DbAtlasStore
    from lychd.db.engine import get_session_factory

    return DbAtlasStore(get_session_factory())


def _build_consent_ledger(profile: str) -> ConsentLedger:
    """Select the consent ledger from the shared persistence profile."""
    from lychd.domain.codex.ledger import InMemoryConsentLedger

    if profile == "memory":
        return InMemoryConsentLedger()
    from lychd.db.engine import get_session_factory
    from lychd.domain.codex.ledger import CodexConsentLedger

    return CodexConsentLedger(session_factory=get_session_factory())


def _build_swap_request_ledger(profile: str) -> SwapRequestLedger:
    """Select the admission fence from the same persistence profile."""
    from lychd.domain.web.swap_requests import InMemorySwapRequestLedger

    if profile == "memory":
        return InMemorySwapRequestLedger()
    from lychd.db.engine import get_session_factory
    from lychd.db.nexus import DbSwapRequestLedger

    return DbSwapRequestLedger(get_session_factory())


def _build_delegation_coordinator(
    profile: str,
    runtimes: Sequence[DelegatedAgentRuntime],
) -> DelegatedAgentCoordinator | None:
    """Compose one AgentJob coordinator only when an admitted adapter exists."""
    if not runtimes:
        return None
    adapters = {runtime.name: runtime for runtime in runtimes}
    if len(adapters) != len(runtimes):
        msg = "Duplicate delegated runtime identities cannot own retained jobs."
        raise ValueError(msg)
    if profile == "memory":
        store = InMemoryDelegatedAgentJobStore()
    else:
        from lychd.db.delegation import DbDelegatedAgentJobStore
        from lychd.db.engine import get_session_factory

        store = DbDelegatedAgentJobStore(get_session_factory())
    return DelegatedAgentCoordinator(
        runtimes=adapters,
        store=store,
    )


def _build_archive(
    profile: str,
    binding: ArchiveProfile | None,
) -> tuple[ArchiveService | None, Callable[[Sigil], ArchiveSubject] | None]:
    """Compose only the explicit PostgreSQL same-host public-note profile."""
    if binding is None:
        return None, None
    if profile != "postgres":
        msg = "The public-note Archive profile requires PostgreSQL persistence."
        raise ValueError(msg)
    from lychd.db.archive import DbArchiveStore
    from lychd.db.engine import get_session_factory
    from lychd.domain.archive import ArchiveService
    from lychd.interface.web.archive_access import LocalArchivePolicy

    policy = LocalArchivePolicy(profile=binding, caller=default_sigil())
    return ArchiveService(
        profile=binding, store=DbArchiveStore(get_session_factory()), authorizer=policy
    ), policy.subject_for


def _build_scout(
    *,
    persistence: str,
    profile: ScoutProfile | None,
    capability_key: str | None,
    access: LocalOperatorAccess | None,
    ledger: RunLedger,
    consents: ConsentLedger,
    reviews: ConsentReviewProducer | None,
) -> tuple[ScoutWorkflowService | None, ScoutAdmissionService | None, ConsentReviewProducer | None]:
    """Compose one explicit PostgreSQL profile with actual credential-backed authority."""
    if profile is None:
        return None, None, reviews
    if persistence != "postgres" or access is None or capability_key is None:
        msg = "Scout requires PostgreSQL, the actual local credential owner and an exact local chat capability."
        raise ValueError(msg)
    from lychd.db.engine import get_session_factory
    from lychd.db.scout import DbScoutAttemptStore
    from lychd.domain.cortex.cancellation import RunEffectFence
    from lychd.domain.scout.authority import ScoutAction, ScoutHostAuthorizer, ScoutHostPolicy
    from lychd.domain.scout.profile import SCOUT_ANSWER_PURPOSE
    from lychd.interface.web.scout_admission import ScoutAdmissionService
    from lychd.interface.web.scout_review import ScoutConsentReviews
    from lychd.system.services.scout_workflow import ScoutCompletions, ScoutWorkflowService

    authorizer = ScoutHostAuthorizer(
        access=access,
        policy=ScoutHostPolicy(
            policy_revision=profile.policy_revision,
            revocation_generation=profile.revocation_generation,
            actions=frozenset(ScoutAction),
            purposes=frozenset({SCOUT_ANSWER_PURPOSE}),
            categories=frozenset({"public-web-locator"}),
            binding_digests=frozenset({profile.binding_digest}),
            resolver_custody_digests=frozenset({profile.resolver_custody_digest}),
        ),
    )
    completions = ScoutCompletions()
    store = DbScoutAttemptStore(
        get_session_factory(),
        authorizer=authorizer,
        budget_limits=profile.budget_limits,
        settlement_verifier=completions,
    )
    service = ScoutWorkflowService(
        store=store,
        completions=completions,
        ledger=ledger,
        consents=consents,
        profile=profile,
        capability_key=capability_key,
        authorizer=authorizer,
        fence=RunEffectFence(),
    )
    return (
        service,
        ScoutAdmissionService(access=access, authorizer=authorizer, profile=profile),
        ScoutConsentReviews(access=access, authorizer=authorizer, store=store, other=reviews),
    )


def _configured_delegation_binding(
    settings: Settings,
    runtimes: Sequence[DelegatedAgentRuntime],
    workflows: WorkflowRegistry | None,
) -> DelegatedRuntimeBinding | None:
    """Validate exact registration without claiming runtime or host admission."""
    selection = settings.weaver.delegation
    if selection is None:
        return None
    if workflows is not None:
        msg = "Explicit workflow registry injection cannot be combined with [weaver.delegation] configuration."
        raise ValueError(msg)
    if sum(runtime.name == selection.runtime for runtime in runtimes) != 1:
        msg = "Configured delegation requires exactly one registered adapter matching its runtime."
        raise ValueError(msg)
    return selection.binding()


def _build_creation(
    *,
    settings: Settings,
    persistence: str,
    access: LocalOperatorAccess | None,
    registry: AnimatorRegistry,
    leases: LeaseLedger,
    workflows: WorkflowRegistry,
) -> tuple[InvestigationService | None, WorkflowRegistry, AgentForge]:
    """Compose only the explicitly selected PostgreSQL investigation application."""
    forge = default_forge()
    selection = settings.weaver.creation
    if selection is None:
        return None, workflows, forge
    if persistence != "postgres" or access is None or not isinstance(workflows, BuiltinWorkflowRegistry):
        msg = "Creation investigation requires PostgreSQL, local credentials and the built-in registry assembly."
        raise ValueError(msg)
    from lychd.compositions.creation.services import InvestigationService, LocalCreationPolicy, register_agents
    from lychd.compositions.creation.workflow import investigation_workflow
    from lychd.db.creation import DbCreationStore
    from lychd.db.engine import get_session_factory

    policy = LocalCreationPolicy(access)
    creation = InvestigationService(
        store=DbCreationStore(get_session_factory(), policy),
        policy=policy,
        registry=registry,
        leases=leases,
        capability_key=selection.capability_key,
    )
    workflow = investigation_workflow(creation)
    workflows = replace(
        workflows,
        workflows=(*workflows.workflows, workflow),
        active_revisions=(*workflows.active_revisions, (workflow.name, workflow.manifest.revision)),
        route_precedence=(workflow.name, *workflows.route_precedence),
    )
    register_agents(forge)
    return creation, workflows, forge


def build_altar_services(
    *,
    queues: Mapping[str, RunQueue],
    runes: RuneRegistry,
    runtime_adapters: Sequence[SoulstoneRuntimeAdapter] = (),
    portal_definitions: Sequence[PortalDefinition] = (),
    soulstone_registrations: Sequence[RegisteredSoulstoneDefinition] = (),
    portal_registrations: Sequence[RegisteredPortalDefinition] = (),
    delegated_runtime_adapters: Sequence[DelegatedAgentRuntime] = (),
    delegated_runtime_catalog: Sequence[RegisteredDelegatedRuntime] = (),
    workflows: WorkflowRegistry | None = None,
    profile: str | None = None,
    settings: Settings | None = None,
    systemctl_bin: str | None = None,
    soft_activation_guard: SoftActivationGuard | None = None,
    runtime_actuator: RuntimeActuator | None = None,
    consent_reviews: ConsentReviewProducer | None = None,
    operator_access: LocalOperatorAccess | None = None,
) -> AltarServices:
    """Assemble `AltarServices` at the application composition boundary.

    The run ledger is chosen by the persistence ``profile`` (defaults to
    ``settings.server.database.profile`` — ``postgres`` in production, ``memory`` in DB-free
    tests and the isolated developer fixture). The bus tees non-TOKEN events into whichever ledger is selected, so the
    choice happens here, before the bus is built.
    """
    if settings is None:
        settings = get_settings()
    bridge_casting = settings.weaver.bridge
    delegation_binding = _configured_delegation_binding(settings, delegated_runtime_adapters, workflows)
    if workflows is not None and (bridge_casting is not None or settings.weaver.creation is not None):
        msg = "Explicit workflow registry injection cannot be combined with [weaver.bridge] configuration."
        raise ValueError(msg)
    if profile is None:
        profile = settings.server.database.profile
    archive, archive_subject_resolver = _build_archive(profile, settings.archive_profile)
    queues = protect_run_queues(queues)
    routing = {
        source: RouteRule(queue=rule.queue, priority=rule.priority)
        for source, rule in settings.orchestration.routing.items()
    }
    policy = resolve_switch_policy(settings.orchestration.switching.policy)
    _validate_routed_queues(routing, queues)
    registry = AnimatorRegistry(
        declarations=compile_animator_declarations(
            settings=settings,
            runes=runes,
        ),
        runtime_adapters=runtime_adapters,
        portal_definitions=portal_definitions,
        soulstone_registrations=soulstone_registrations,
        portal_registrations=portal_registrations,
    )
    leases = LeaseLedger()
    ledger = _build_run_ledger(profile, settings)
    bus = InProcessEventBus(ledger=ledger)
    dispatcher = Dispatcher(registry=registry, leases=leases, events=bus)
    from lychd.interface.web.archive_derivation_factory import build_archive_derivation

    archive_derivation = build_archive_derivation(settings, registry, leases, default_sigil())
    switching = settings.orchestration.switching
    if soft_activation_guard is None:
        from lychd.system.constants import PATH_RUNTIME_GUARD_DIR
        from lychd.system.services.runtime_guard import FileSoftActivationGuard

        soft_activation_guard = FileSoftActivationGuard(PATH_RUNTIME_GUARD_DIR)
    worker_broker = GhoulBroker()
    orchestrator = OrchestratorManager(
        worker_broker,
        registry,
        leases=leases,
        policy=policy,
        arbiter=TransitionArbiter(),
        actuator=runtime_actuator
        if runtime_actuator is not None
        else build_runtime_actuator(
            switching,
            registry,
            systemctl_bin=systemctl_bin,
        ),
        switching=switching,
        soft_activation_guard=soft_activation_guard,
    )
    context_orchestrator = ContextOrchestrator(registry=registry)
    fragments = build_fragment_registry()
    bridge_sessions = _build_session_store(profile, sigil_name=default_sigil().name)
    atlas = _build_atlas_store(profile)
    consents = _build_consent_ledger(profile)
    scout, scout_admission, consent_reviews = _build_scout(
        persistence=profile,
        profile=bridge_casting.scout if bridge_casting is not None else None,
        capability_key=bridge_casting.capability_key if bridge_casting is not None else None,
        access=operator_access,
        ledger=ledger,
        consents=consents,
        reviews=consent_reviews,
    )
    tickets, swap_requests = TicketStore(), _build_swap_request_ledger(profile)
    projector = EventProjector(
        fragments=fragments, sessions=bridge_sessions, consents=consents, consent_reviews=consent_reviews
    )
    workflows = workflows if workflows is not None else builtin_workflow_registry(weaver=settings.weaver)
    creation, workflows, forge = _build_creation(
        settings=settings,
        persistence=profile,
        access=operator_access,
        registry=registry,
        leases=leases,
        workflows=workflows,
    )
    delegates = _build_delegation_coordinator(profile, delegated_runtime_adapters)
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
        forge=forge,
        sigil_provider=default_sigil,
        leases=leases,
        queues=queues,
        cancellations=cancellations,
        stasis_store=stasis_store,
        delegates=delegates,
        archive=archive,
        archive_subject_resolver=archive_subject_resolver,
        scout=scout,
        effects=scout,
    )
    run_engine = RunEngine(
        ledger=ledger,
        bus=bus,
        workflows=workflows,
        queue_router=QueueRouter(routing=routing),
        queues=queues,
        cancellations=cancellations,
        stasis_store=stasis_store,
        delegates=delegates,
        consents=consents,
        release_context=context_orchestrator.release,
        bridge_capability_key=bridge_casting.capability_key if bridge_casting is not None else None,
        bridge_archive=bridge_casting.archive if bridge_casting is not None else None,
        delegation_binding=delegation_binding,
        bridge_scout=bridge_casting.scout if bridge_casting is not None else None,
        scout_admission=scout_admission,
        effects=scout,
    )
    return AltarServices(
        creation=creation,
        archive_derivation=archive_derivation,
        registry=registry,
        dispatcher=dispatcher,
        orchestrator=orchestrator,
        leases=leases,
        fragments=fragments,
        bridge_sessions=bridge_sessions,
        atlas=atlas,
        consents=consents,
        tickets=tickets,
        swap_requests=swap_requests,
        workflows=workflows,
        run_engine=run_engine,
        projector=projector,
        ledger=ledger,
        bus=bus,
        substrate=substrate,
        archive=archive,
        delegates=delegates,
        delegated_runtime_catalog=tuple(delegated_runtime_catalog),
        scout=scout,
        scout_admission=scout_admission,
    )
