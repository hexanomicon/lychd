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
from lychd.domain.animation.capabilities import SourceKind
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.services.declarations import (
    compile_animator_declarations,
)
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.bridge_preference import BridgePreferenceSelector
from lychd.domain.cortex.cancellation import RunCancellationCoordinator
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.semantic_answer import SemanticAnswerBinding
from lychd.domain.cortex.substrate import RunSubstrate
from lychd.domain.delegation.services import (
    DelegatedAgentCoordinator,
    InMemoryDelegatedAgentJobStore,
)
from lychd.domain.oculus.models import RuntimeComponent
from lychd.domain.oculus.runtime import RegisteredInspection, RegisteredObservation, RuntimeCatalogue
from lychd.domain.orchestration.arbiter import TransitionArbiter
from lychd.domain.orchestration.broker import GhoulBroker
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.policies import resolve_switch_policy
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.projection import EventProjector
from lychd.domain.web.tickets import TicketStore
from lychd.interface.web.archive_derivation_factory import build_archive_derivation
from lychd.interface.web.archive_semantic_factory import build_archive_semantic
from lychd.system.services.queues import protect_run_queues
from lychd.system.services.runtime import build_runtime_actuator

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from lychd.agents.factory import AgentForge
    from lychd.agents.workflows import WorkflowRegistry
    from lychd.compositions.creation.services import InvestigationService
    from lychd.compositions.scavenger.services import ScavengerService
    from lychd.config.runes.registry import RuneRegistry
    from lychd.config.settings import BridgeCastingSettings, ScavengerCastingSettings
    from lychd.config.settings.root import Settings
    from lychd.domain.animation.extension import RegisteredPortalDefinition, RegisteredSoulstoneDefinition
    from lychd.domain.animation.services.adapters.contracts import PortalDefinition, SoulstoneRuntimeAdapter
    from lychd.domain.archive import ArchiveProfile, ArchiveService, ArchiveSubject
    from lychd.domain.archive.derivation_service import ArchiveDerivationService
    from lychd.domain.archive.semantic_service import ArchiveSemanticService
    from lychd.domain.codex.ledger import ConsentLedger
    from lychd.domain.codex.local_access import LocalOperatorAccess
    from lychd.domain.codex.sigil import Sigil
    from lychd.domain.cortex.engine import RunQueue
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.delegation.ports import DelegatedAgentRuntime
    from lychd.domain.delegation.routing import DelegatedRuntimeBinding
    from lychd.domain.dictation_lexicon_service import DictationLexiconService
    from lychd.domain.dictation_service import DictationService
    from lychd.domain.naming import NamingStore
    from lychd.domain.orchestration.actuator import RuntimeActuator
    from lychd.domain.orchestration.containment import SoftActivationGuard
    from lychd.domain.scout.authority import ScoutHostAuthorizer
    from lychd.domain.scout.feed import ScoutFeedProfile
    from lychd.domain.scout.profile import ScoutProfile
    from lychd.domain.web.atlas import AtlasStorePort
    from lychd.domain.web.consent_reviews import ConsentReviewProducer
    from lychd.domain.web.fragments import FragmentRegistry
    from lychd.domain.web.sessions import SessionStorePort
    from lychd.domain.web.swap_requests import SwapRequestLedger
    from lychd.extensions.delegation import RegisteredDelegatedRuntime
    from lychd.interface.web.scout_admission import ScoutAdmissionService
    from lychd.interface.web.scout_feed_admission import ScoutFeedAdmissionService
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
    dictation: DictationService
    dictation_lexicon: DictationLexiconService
    consents: ConsentLedger
    tickets: TicketStore
    swap_requests: SwapRequestLedger
    workflows: WorkflowRegistry
    run_engine: RunEngine
    projector: EventProjector
    ledger: RunLedger
    bus: InProcessEventBus
    substrate: RunSubstrate
    naming: NamingStore | None = None
    scavenger: ScavengerService | None = None
    feed_admission: ScoutFeedAdmissionService | None = None
    creation: InvestigationService | None = None
    archive: ArchiveService | None = None
    archive_derivation: ArchiveDerivationService | None = None
    archive_semantic: ArchiveSemanticService | None = None
    delegates: DelegatedAgentCoordinator | None
    delegated_runtime_catalog: tuple[RegisteredDelegatedRuntime, ...]
    scout: ScoutWorkflowService | None = None
    scout_admission: ScoutAdmissionService | None = None
    runtime_observations: RuntimeCatalogue | None = None

    async def aclose(self) -> None:
        """Cancel tracked tasks and drain pending ledger writes before shutdown."""
        failures: list[BaseException] = []
        if self.scout is not None:
            self.scout.fence_all("service_close")
            try:
                await self.scout.contain_all()
            except BaseException as exc:  # noqa: BLE001 - retain containment uncertainty
                failures.append(exc)
        for close in (self.dictation.aclose, self.tickets.aclose, self.bus.aclose):
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


def _build_naming_store(profile: str) -> NamingStore:
    """Use the shared persistence profile for accepted forms of address."""
    from lychd.domain.naming import InMemoryNamingStore

    if profile == "memory":
        return InMemoryNamingStore()
    from lychd.db.engine import get_session_factory
    from lychd.db.naming import DbNamingStore

    return DbNamingStore(get_session_factory())


def _build_dictation_services(profile: str, settings: Settings) -> tuple[DictationService, DictationLexiconService]:
    """Compose private retention and an optional already-running CPU binding."""
    from lychd.domain.dictation_lexicon import DictationLexiconStore, MemoryDictationLexiconStore
    from lychd.domain.dictation_lexicon_service import DictationLexiconService
    from lychd.domain.dictation_service import DictationService
    from lychd.domain.dictation_store import DictationStore, MemoryDictationStore

    pinned = settings.server.web.dictation
    if pinned is not None and profile != "postgres":
        msg = "Configured dictation requires PostgreSQL persistence."
        raise ValueError(msg)
    store: DictationStore
    lexicon_store: DictationLexiconStore
    if profile == "memory":
        store = MemoryDictationStore()
        lexicon_store = MemoryDictationLexiconStore()
    else:
        from lychd.db.dictation import DbDictationStore
        from lychd.db.dictation_lexicon import DbDictationLexiconStore
        from lychd.db.engine import get_session_factory

        store = DbDictationStore(get_session_factory())
        lexicon_store = DbDictationLexiconStore(get_session_factory())
    adapter = None
    if pinned is not None:
        from lychd.system.services.dictation_transcriber import LocalDictationTranscriber

        adapter = LocalDictationTranscriber(pinned)
    dictation = DictationService(store=store, profile=pinned, transcriber=adapter)
    return dictation, DictationLexiconService(store=lexicon_store, attempts=store)


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


def _build_scout_runtime(
    *,
    persistence: str,
    profile: ScoutProfile | ScoutFeedProfile,
    capability_key: str | None,
    access: LocalOperatorAccess | None,
    ledger: RunLedger,
    consents: ConsentLedger,
    reviews: ConsentReviewProducer | None,
) -> tuple[ScoutWorkflowService, ScoutHostAuthorizer, ConsentReviewProducer]:
    """Construct the one physical Scout owner shared by both exact profile factories."""
    from lychd.domain.scout.feed import ScoutFeedProfile
    from lychd.domain.scout.profile import ScoutProfile

    if persistence != "postgres" or access is None:
        msg = "Scout requires PostgreSQL and the actual local credential owner."
        raise ValueError(msg)
    if type(profile) is ScoutFeedProfile:
        if capability_key is not None:
            msg = "The feed Scout profile cannot borrow a model capability."
            raise ValueError(msg)
    elif type(profile) is not ScoutProfile or capability_key is None:
        msg = "The page Scout profile requires an exact local chat capability."
        raise ValueError(msg)
    from lychd.db.engine import get_session_factory
    from lychd.db.scout import DbScoutAttemptStore
    from lychd.domain.cortex.cancellation import RunEffectFence
    from lychd.domain.scout.attempts import SCOUT_FEED_PURPOSE
    from lychd.domain.scout.authority import ScoutAction, ScoutHostAuthorizer, ScoutHostPolicy
    from lychd.domain.scout.profile import SCOUT_ANSWER_PURPOSE
    from lychd.interface.web.scout_review import ScoutConsentReviews
    from lychd.system.services.scout_workflow import ScoutCompletions, ScoutWorkflowService

    authorizer = ScoutHostAuthorizer(
        access=access,
        policy=ScoutHostPolicy(
            policy_revision=profile.policy_revision,
            revocation_generation=profile.revocation_generation,
            actions=frozenset(ScoutAction),
            purposes=frozenset({SCOUT_FEED_PURPOSE if type(profile) is ScoutFeedProfile else SCOUT_ANSWER_PURPOSE}),
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
    return service, authorizer, ScoutConsentReviews(access=access, authorizer=authorizer, store=store, other=reviews)


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
    """Compose the exact page profile without changing its existing typed contract."""
    if profile is None:
        return None, None, reviews
    if persistence != "postgres" or access is None or capability_key is None:
        msg = "Scout requires PostgreSQL, the actual local credential owner and an exact local chat capability."
        raise ValueError(msg)
    from lychd.interface.web.scout_admission import ScoutAdmissionService

    service, authorizer, reviews = _build_scout_runtime(
        persistence=persistence,
        profile=profile,
        capability_key=capability_key,
        access=access,
        ledger=ledger,
        consents=consents,
        reviews=reviews,
    )
    return service, ScoutAdmissionService(access=access, authorizer=authorizer, profile=profile), reviews


def _build_feed_scout(
    *,
    persistence: str,
    profile: ScoutFeedProfile,
    access: LocalOperatorAccess | None,
    ledger: RunLedger,
    consents: ConsentLedger,
    reviews: ConsentReviewProducer | None,
) -> tuple[ScoutWorkflowService, ScoutFeedAdmissionService, ConsentReviewProducer]:
    """Compose the distinct model-free issuer with the same physical Scout owner."""
    if persistence != "postgres" or access is None:
        msg = "Scout requires PostgreSQL and the actual local credential owner."
        raise ValueError(msg)
    from lychd.interface.web.scout_feed_admission import ScoutFeedAdmissionService

    service, authorizer, reviews = _build_scout_runtime(
        persistence=persistence,
        profile=profile,
        capability_key=None,
        access=access,
        ledger=ledger,
        consents=consents,
        reviews=reviews,
    )
    return service, ScoutFeedAdmissionService(access=access, authorizer=authorizer, profile=profile), reviews


def _build_scavenger(
    *,
    settings: Settings,
    access: LocalOperatorAccess | None,
    scout: ScoutWorkflowService | None,
) -> ScavengerService | None:
    """Bind the exact receiving application to the shared credential/Scout owners."""
    selection = settings.weaver.scavenger
    if selection is None:
        return None
    if access is None or scout is None:
        msg = "Scavenger requires its actual local authority and shared native Scout."
        raise ValueError(msg)
    from lychd.agents.workflows.observe_market import OBSERVE_MARKET
    from lychd.compositions.scavenger.services import LocalScavengerPolicy, ScavengerService
    from lychd.db.engine import get_session_factory
    from lychd.db.scavenger import DbScavengerStore

    return ScavengerService(
        store=DbScavengerStore(get_session_factory(), pattern=OBSERVE_MARKET.manifest.snapshot()),
        policy=LocalScavengerPolicy(access=access, profile=selection.scout, owner=default_sigil().name),
        scout=scout,
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


def _configured_castings(
    *,
    settings: Settings,
    profile: str | None,
    operator_access: LocalOperatorAccess | None,
    workflows: WorkflowRegistry | None,
    delegated_runtime_adapters: Sequence[DelegatedAgentRuntime],
) -> tuple[BridgeCastingSettings | None, ScavengerCastingSettings | None, DelegatedRuntimeBinding | None, str]:
    """Validate persistence and native castings before constructing any process-owned services."""
    if profile is None:
        profile = settings.server.database.profile
    if profile not in ("memory", "postgres"):
        msg = "Unsupported persistence profile."
        raise ValueError(msg)
    if settings.server.web.dictation is not None and profile != "postgres":
        msg = "Configured dictation requires PostgreSQL persistence."
        raise ValueError(msg)
    bridge_casting = settings.weaver.bridge
    scavenger_casting = settings.weaver.scavenger
    if scavenger_casting is not None and workflows is not None:
        msg = "Explicit workflow registry injection cannot be combined with [weaver.scavenger] configuration."
        raise ValueError(msg)
    delegation_binding = _configured_delegation_binding(settings, delegated_runtime_adapters, workflows)
    if workflows is not None and (bridge_casting is not None or settings.weaver.creation is not None):
        msg = "Explicit workflow registry injection cannot be combined with [weaver.bridge] configuration."
        raise ValueError(msg)
    if bridge_casting is not None and bridge_casting.revision == "5":
        if profile != "postgres" or operator_access is None:
            msg = "Semantic Bridge requires PostgreSQL and the actual local credential owner."
            raise ValueError(msg)
        if settings.archive is None or not settings.archive.semantic or settings.archive.derivation is None:
            msg = "Semantic Bridge requires the independently enabled Archive semantic generation."
            raise ValueError(msg)
    if scavenger_casting is not None and (profile != "postgres" or operator_access is None):
        msg = "Scavenger requires PostgreSQL and the actual local credential owner."
        raise ValueError(msg)
    return bridge_casting, scavenger_casting, delegation_binding, profile


def _configured_semantic_answer(
    *,
    settings: Settings,
    selection: BridgeCastingSettings | None,
    registry: AnimatorRegistry,
    service: ArchiveSemanticService | None,
    subject_resolver: Callable[[Sigil], ArchiveSubject] | None,
) -> SemanticAnswerBinding | None:
    """Bind existing service identities using declaration metadata, without probing readiness."""
    if selection is None or selection.revision != "5":
        return None
    archive = settings.archive
    if (
        selection.semantic is None
        or selection.capability_key is None
        or archive is None
        or not archive.semantic
        or archive.derivation is None
        or service is None
        or subject_resolver is None
    ):
        msg = "Semantic Bridge requires its configured service, selection and exact local subject resolver."
        raise ValueError(msg)
    binding = SemanticAnswerBinding(
        **selection.semantic.model_dump(), manifest=service.manifest, generation=service.reference
    )
    if (
        binding.manifest.archive != archive.profile
        or binding.manifest.binding != archive.derivation.binding
        or binding.generation.generation_id != archive.derivation.generation_id
        or subject_resolver(default_sigil()) != archive.profile.owner_subject
    ):
        msg = "Semantic Bridge service does not match the configured generation and local subject binding."
        raise ValueError(msg)
    embedding = registry.require_embedding(binding.manifest.binding, "embed_query")
    capability = registry.get_capability(selection.capability_key)
    if (
        embedding.embedding_profile != binding.manifest.embedding
        or capability is None
        or capability.key != selection.capability_key
        or capability.source_kind is not SourceKind.SOULSTONE
        or capability.family is not CapabilityFamily.CHAT
        or not capability.model_id.strip()
        or capability.model_id != capability.model_id.strip()
        or capability.model_id == "*"
    ):
        msg = "Semantic Bridge requires the exact registered local chat model and Core embedding binding."
        raise ValueError(msg)
    return binding


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
    observation_registrations: Sequence[RegisteredObservation] = (),
    inspection_registrations: Sequence[RegisteredInspection] = (),
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
    choice happens here, before the bus is built. Unsupported profiles are refused before
    constructing any process-owned services.
    """
    if settings is None:
        settings = get_settings()
    bridge_casting, scavenger_casting, delegation_binding, profile = _configured_castings(
        settings=settings,
        profile=profile,
        operator_access=operator_access,
        workflows=workflows,
        delegated_runtime_adapters=delegated_runtime_adapters,
    )
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
    archive_derivation = build_archive_derivation(settings, registry, leases, default_sigil())
    archive_semantic = build_archive_semantic(settings, registry, leases, default_sigil())
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
    atlas, consents, naming = _build_atlas_store(profile), _build_consent_ledger(profile), _build_naming_store(profile)
    if scavenger_casting is None:
        scout, scout_admission, consent_reviews = _build_scout(
            persistence=profile,
            profile=bridge_casting.scout if bridge_casting is not None else None,
            capability_key=bridge_casting.capability_key if bridge_casting is not None else None,
            access=operator_access,
            ledger=ledger,
            consents=consents,
            reviews=consent_reviews,
        )
        feed_admission = None
    else:
        scout, feed_admission, consent_reviews = _build_feed_scout(
            persistence=profile,
            profile=scavenger_casting.scout,
            access=operator_access,
            ledger=ledger,
            consents=consents,
            reviews=consent_reviews,
        )
        scout_admission = None
    scavenger = _build_scavenger(settings=settings, access=operator_access, scout=scout)
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
        archive_semantic=archive_semantic,
        archive_subject_resolver=archive_subject_resolver,
        scout=scout if scout_admission is not None else None,
        feed_scout=scout if feed_admission is not None else None,
        scavenger=scavenger,
        effects=scout,
    )
    run_engine = RunEngine(
        naming_lookup=naming.get,
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
        bridge_preference=bridge_casting.preference if bridge_casting is not None else None,
        bridge_preference_selector=BridgePreferenceSelector(registry, leases).select,
        bridge_archive=bridge_casting.archive if bridge_casting is not None else None,
        bridge_semantic=_configured_semantic_answer(
            settings=settings,
            selection=bridge_casting,
            registry=registry,
            service=archive_semantic,
            subject_resolver=archive_subject_resolver,
        ),
        delegation_binding=delegation_binding,
        bridge_scout=bridge_casting.scout if bridge_casting is not None else None,
        scout_admission=scout_admission,
        feed_scout=scavenger_casting.scout if scavenger_casting is not None else None,
        feed_scout_admission=feed_admission,
        effects=scout,
    )
    dictation, dictation_lexicon = _build_dictation_services(profile, settings)
    return AltarServices(
        scavenger=scavenger,
        feed_admission=feed_admission,
        creation=creation,
        archive_derivation=archive_derivation,
        archive_semantic=archive_semantic,
        registry=registry,
        dispatcher=dispatcher,
        orchestrator=orchestrator,
        leases=leases,
        fragments=fragments,
        bridge_sessions=bridge_sessions,
        atlas=atlas,
        naming=naming,
        dictation=dictation,
        dictation_lexicon=dictation_lexicon,
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
        runtime_observations=_build_runtime_observations(
            settings=settings,
            registry=registry,
            observations=tuple(observation_registrations),
            inspections=tuple(inspection_registrations),
            optional_services=tuple(
                name
                for name, service in (
                    ("archive", archive),
                    ("scout", scout),
                    ("creation", creation),
                    ("scavenger", scavenger),
                    ("delegation", delegates),
                )
                if service is not None
            ),
            selected_registrants=tuple(
                sorted(
                    {
                        *(f"builtin:{name}" for name in settings.extensions.builtins),
                        *(f"crypt:{name}" for name in settings.extensions.crypt),
                        *(item.registrant_id for item in soulstone_registrations),
                        *(item.registrant_id for item in portal_registrations),
                        *(item.registrant_id for item in delegated_runtime_catalog),
                    }
                )
            ),
        ),
    )


def _build_runtime_observations(
    *,
    settings: Settings,
    registry: AnimatorRegistry,
    observations: tuple[RegisteredObservation, ...],
    inspections: tuple[RegisteredInspection, ...],
    optional_services: tuple[str, ...],
    selected_registrants: tuple[str, ...],
) -> RuntimeCatalogue:
    """Project actual assembled services and capability registrations without probes."""
    from hashlib import sha256

    def native_components() -> tuple[RuntimeComponent, ...]:
        services = ("altar", "cortex", "weaver", "animator", "orchestrator", *optional_services)
        components = [
            RuntimeComponent(
                key="vessel",
                label="Vessel",
                kind="host",
                owner="core",
                source_id="native",
                source_generation="assembly",
                registrant_id="core",
            )
        ]
        components.extend(
            RuntimeComponent(
                key=f"service:{name}",
                label=name.title(),
                kind="service",
                owner=name,
                source_id="native",
                source_generation="assembly",
                registrant_id="core",
                icon="service",
            )
            for name in services
        )
        components.extend(
            RuntimeComponent(
                key=f"extension:{sha256(registrant.encode()).hexdigest()}",
                label="".join(char if char.isalnum() or char in " .,:()-" else " " for char in registrant)[:160],
                kind="extension",
                owner="extensions",
                source_id="native",
                source_generation="assembly",
                registrant_id=registrant,
            )
            for registrant in selected_registrants
        )
        # Registry hydration has already completed before lifespan publication.
        # These are declarations, deliberately not readiness or transport evidence.
        for capability in registry.list_capabilities():
            label = "".join(char if char.isalnum() or char in " .,:()-" else " " for char in capability.key)[:160]
            components.append(
                RuntimeComponent(
                    key=f"capability:{sha256(capability.key.encode()).hexdigest()}",
                    label=label,
                    kind="capability",
                    owner="animator",
                    source_id="native",
                    source_generation="assembly",
                    registrant_id=capability.registrant_id,
                    icon="capability",
                )
            )
        return tuple(components)

    reader = None
    if settings.observability.sources:
        from lychd.system.services.oculus_snapshot import SnapshotFileReader

        reader = SnapshotFileReader(selections=settings.observability.sources)
    return RuntimeCatalogue(
        reader=reader, observations=observations, inspections=inspections, native_components=native_components
    )
