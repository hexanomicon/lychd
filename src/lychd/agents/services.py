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
    from contextlib import AbstractAsyncContextManager

    from lychd.agents.factory import AgentForge
    from lychd.domain.animation.capabilities import CapabilityGrant
    from lychd.domain.animation.schemas.capability_family import CapabilityFamily
    from lychd.domain.codex.schemas import ConsentDecision
    from lychd.domain.cortex.context import ContextOrchestrator
    from lychd.domain.cortex.events import RunEventBus
    from lychd.domain.cortex.priority import Priority
    from lychd.domain.orchestration.schema import TransitionPlan
    from lychd.domain.web.fragments import FragmentRegistry


# ---------------------------------------------------------------------------
# Narrow ports — the seams the nodes and tools depend on
# ---------------------------------------------------------------------------


class TurnLedgerPort(Protocol):
    """Session/turn writes. Today: `BridgeSessionStore`; later a DB-backed store.

    Run *status* is NOT written here — the `RunLedger` owns it (single-writer
    discipline, A4 §2). This port carries only settled turns + history reads.
    Async (4C-2): the DB-backed `SessionStore` awaits; in-memory bodies are trivially
    async.
    """

    async def add_turn(self, session_id: str, turn: Any) -> None: ...

    async def get_session(self, session_id: str) -> Any | None: ...


class ConsentLedgerPort(Protocol):
    """The consent surface the graph parks into (v2 — the verdict lives in the ledger).

    `park` records the pause (returning the ledger's decision); `verdict` reads the
    tri-state (True granted / False denied|expired / None pending). The non-serializable
    `DeferredToolRequests` is NEVER stored — only its `tool_call_id`s (in graph state).
    """

    async def park(
        self,
        *,
        run_id: str,
        tool_name: str,
        tool_call_id: str,
        call_ids: tuple[str, ...],
        args: dict[str, Any],
        sigil: Sigil,
    ) -> ConsentDecision: ...

    async def verdict(self, consent_id: str) -> bool | None: ...


class TransitionPort(Protocol):
    """The narrow slice of `OrchestratorManager` the consent tool needs."""

    async def calculate_transition_plan(self, target_capability_key: str) -> TransitionPlan: ...

    async def request_transition(self, target_capability_key: str, priority: Priority) -> TransitionPlan: ...


class GrantPort(Protocol):
    """The narrow slice of `Dispatcher` a node needs — the C1 lease CM.

    ``@asynccontextmanager``-decorated methods satisfy this structurally.
    """

    def lease_grant(
        self,
        *,
        family: CapabilityFamily | str,
        model_name: str | None = None,
        run_id: str,
        priority: int = 50,
        require_modalities: tuple[str, ...] = (),
        requires_tools: bool = False,
    ) -> AbstractAsyncContextManager[CapabilityGrant]: ...


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

# Test/dev fallback only: the §3.2 grammar (a held `"*"` grants every scope). The
# composition root threads `settings_sigil_provider` in production (4C-1 tail).
_DEFAULT_SIGIL = Sigil(name="magus", scopes=frozenset({"*"}))


def default_sigil() -> Sigil:
    """Return the process default Sigil (test fallback stand-in for the Ward).

    A frozen constant, not mutable module state: the Ward replaces this callable
    at app startup by overriding `WorkflowServices.sigil_provider`.
    """
    return _DEFAULT_SIGIL


def settings_sigil_provider(settings: Any) -> Callable[[], Sigil]:
    """Build a `sigil_provider` from settings (built once at the composition root)."""
    sigil = Sigil(name=settings.sigil.name, scopes=frozenset(settings.sigil.scopes))

    def provider() -> Sigil:
        return sigil

    return provider


def build_workflow_services(
    *,
    dispatcher: GrantPort,
    orchestrator: TransitionPort,
    context: ContextOrchestrator,
    fragments: FragmentRegistry,
    turns: Any,
    consents: ConsentLedgerPort,
    events: RunEventBus,
    forge: AgentForge,
    sigil_provider: Callable[[], Sigil] = default_sigil,
) -> WorkflowServices:
    """Assemble `WorkflowServices` from run-scoped service handles.

    The graph parks into the SAME `consents` ledger the web reads (C3's one-record
    rule). `turns` (a `SessionStore`) supplies the `TurnLedgerPort`. `events` is the
    shared `RunEventBus`. The two ledger ports are threaded from DISTINCT sources — the
    old single-`sessions` alias is gone.
    """
    return WorkflowServices(
        dispatcher=dispatcher,
        orchestrator=orchestrator,
        context=context,
        fragments=fragments,
        turns=turns,
        consents=consents,
        events=events,
        forge=forge,
        sigil_provider=sigil_provider,
    )


__all__ = [
    "ConsentLedgerPort",
    "GrantPort",
    "TransitionPort",
    "TurnLedgerPort",
    "WorkflowServices",
    "build_workflow_services",
    "default_sigil",
    "settings_sigil_provider",
]
