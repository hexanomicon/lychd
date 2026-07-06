"""`WorkflowServices` — the one shared graph DepsT (A5 §3).

Retires the module-global singleton indirection.
adw-kit's "one shared `GraphDeps` for all workflows keeps the worker generic",
translated to LychD: a single frozen `WorkflowServices` is threaded as
`graph.iter(..., deps=services)` and read by every node via `ctx.deps.<port>`.
Nothing here is loop- or process-bound except through the ports, so a future SAQ
ghoul builds its own instance at worker startup.

Per-run data (run_id, session_id, priority) lives in graph **State**, never in
deps — that is what keeps durable snapshots clean and workers generic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from lychd.agents.deps import Sigil

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic_ai import DeferredToolRequests

    from lychd.agents.factory import AgentForge
    from lychd.domain.animation.capabilities import CapabilityGrant
    from lychd.domain.cortex.context import ContextOrchestrator
    from lychd.domain.cortex.events import RunEmitter, RunEventBus
    from lychd.domain.orchestration.schema import TransitionPlan
    from lychd.domain.web.fragments import FragmentRegistry


# ---------------------------------------------------------------------------
# Narrow ports — the seams the nodes and tools depend on
# ---------------------------------------------------------------------------


class RunEventPort(Protocol):
    """The run event surface: hands a run its bus-backed `RunEmitter`.

    Today an `InProcessEventBus`; later a `PostgresEventBus` — the emitter tees
    non-TOKEN events to the `RunLedger` and pushes to the run's channel.
    """

    def emitter(self, run_id: str) -> RunEmitter: ...


class TurnLedgerPort(Protocol):
    """Session/turn writes. Today: `BridgeSessionStore`; later a DB-backed store.

    Run *status* is NOT written here — the `RunLedger` owns it (single-writer
    discipline, A4 §2). This port carries only settled turns + history reads.
    """

    def add_turn(self, session_id: str, turn: Any) -> None: ...

    def get_session(self, session_id: str) -> Any | None: ...


class ConsentLedgerPort(Protocol):
    """Parked-consent records. Today: `BridgeSessionStore._consents`; later a Consent table."""

    def park_consent(
        self,
        *,
        run_id: str,
        session_id: str,
        tool_name: str,
        args: dict[str, Any],
        requests: DeferredToolRequests,
    ) -> str: ...


class TransitionPort(Protocol):
    """The narrow slice of `OrchestratorManager` the consent tool needs."""

    async def calculate_transition_plan(self, target_capability_key: str) -> TransitionPlan: ...

    async def request_transition(self, target_capability_key: str, priority: float) -> TransitionPlan: ...


class GrantPort(Protocol):
    """The narrow slice of `Dispatcher` a node needs (A3 owns `CapabilityGrant`)."""

    def resolve_capability_grant(self, intent_type: str) -> CapabilityGrant: ...


# ---------------------------------------------------------------------------
# The single graph DepsT
# ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class WorkflowServices:
    """THE single graph DepsT for every LychD workflow.

    Built once per run in `router.submit` from handles that live on `app.state`
    (the web/composition root owns those handles); passed to
    `graph.iter(..., deps=services)`.
    """

    dispatcher: GrantPort
    orchestrator: TransitionPort
    context: ContextOrchestrator
    fragments: FragmentRegistry
    turns: TurnLedgerPort
    consents: ConsentLedgerPort
    events: RunEventBus
    forge: AgentForge
    sigil_provider: Callable[[], Sigil]


# ---------------------------------------------------------------------------
# Sigil provider (v1 single-identity stand-in for the Ward)
# ---------------------------------------------------------------------------

_DEFAULT_SIGIL = Sigil(name="magus", scopes=frozenset({"bridge:send", "nexus:swap", "consent:grant"}))


def default_sigil() -> Sigil:
    """Return the process default Sigil (v1 single-identity stand-in for the Ward).

    A frozen constant, not mutable module state: the Ward replaces this callable
    at app startup by overriding `WorkflowServices.sigil_provider`.
    """
    return _DEFAULT_SIGIL


def build_workflow_services(
    *,
    dispatcher: GrantPort,
    orchestrator: TransitionPort,
    context: ContextOrchestrator,
    fragments: FragmentRegistry,
    sessions: Any,
    events: RunEventBus,
    forge: AgentForge,
    sigil_provider: Callable[[], Sigil] = default_sigil,
) -> WorkflowServices:
    """Assemble `WorkflowServices` from run-scoped service handles.

    `sessions` (today a `BridgeSessionStore`) structurally satisfies the
    `TurnLedgerPort`/`ConsentLedgerPort` pair (turns + consents). `events` is the
    shared `RunEventBus` — the event plane now lives on the bus, not the session
    store (channels were shed to the bus in Wave 2).
    """
    return WorkflowServices(
        dispatcher=dispatcher,
        orchestrator=orchestrator,
        context=context,
        fragments=fragments,
        turns=sessions,
        consents=sessions,
        events=events,
        forge=forge,
        sigil_provider=sigil_provider,
    )


__all__ = [
    "ConsentLedgerPort",
    "GrantPort",
    "RunEventPort",
    "TransitionPort",
    "TurnLedgerPort",
    "WorkflowServices",
    "build_workflow_services",
    "default_sigil",
]
