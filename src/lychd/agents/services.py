"""Ports shared by workflow nodes through ``ctx.deps``.

``RunSubstrate.build_services`` binds process-owned collaborators and the persisted
caller identity for worker execution. Run identity, session and priority live in
Graph state; live service handles never enter a checkpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from lychd.agents.deps import Sigil
from lychd.domain.codex.sigil import default_local_sigil

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
    from lychd.domain.delegation.ports import DelegatedAgentCoordinatorPort
    from lychd.domain.orchestration.schema import TransitionPlan
    from lychd.domain.web.fragments import FragmentRegistry


class TurnLedgerPort(Protocol):
    """Settle turns and read session history through the memory or database store.

    Run status belongs to RunLedger, outside this port.
    """

    async def settle_agent_turn(
        self,
        session_id: str,
        turn: Any,
        *,
        new_messages: list[Any],
    ) -> None: ...

    async def get_session(self, session_id: str) -> Any | None: ...


class ConsentLedgerPort(Protocol):
    """Record consent requests and read granted, denied/expired or pending verdicts.

    Graph state retains call identities, not live DeferredToolRequests objects.
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

    async def request_transition(self, target_capability_key: str, priority: Priority) -> TransitionPlan: ...


class GrantPort(Protocol):
    """Lease-scoped Dispatcher access for a workflow node.

    ``@asynccontextmanager``-decorated methods satisfy this structurally.
    """

    def lease_grant(
        self,
        *,
        family: CapabilityFamily | str,
        model_name: str | None = None,
        capability_key: str | None = None,
        run_id: str,
        priority: int = 50,
        require_modalities: tuple[str, ...] = (),
        requires_tools: bool = False,
    ) -> AbstractAsyncContextManager[CapabilityGrant]: ...


@dataclass(frozen=True, kw_only=True)
class WorkflowServices:
    """Worker-bound collaborators passed to ``graph.iter(..., deps=services)``."""

    dispatcher: GrantPort
    orchestrator: TransitionPort
    context: ContextOrchestrator
    fragments: FragmentRegistry
    turns: TurnLedgerPort
    consents: ConsentLedgerPort
    events: RunEventBus
    forge: AgentForge
    sigil_provider: Callable[[], Sigil]
    delegates: DelegatedAgentCoordinatorPort | None = None


def default_sigil() -> Sigil:
    """Return the loopback bootstrap Sigil until IAM provides a caller Sigil."""
    return default_local_sigil()


__all__ = [
    "ConsentLedgerPort",
    "GrantPort",
    "TransitionPort",
    "TurnLedgerPort",
    "WorkflowServices",
    "default_sigil",
]
