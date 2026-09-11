"""Process-owned collaborators shared by HTTP admission and the in-process worker.

Application lifespan publishes the substrate before workers claim jobs. Both use
the same event bus, leases and cancellation coordinator on one event loop.
``build_services`` binds these handles to the persisted caller for Graph execution;
the process handoff itself carries no durable recovery authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from lychd.domain.cortex.cancellation import RunCancellationCoordinator
from lychd.domain.cortex.claims import RunClaimCoordinator
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.cortex.stasis import InMemoryStasisStore

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from lychd.agents.deps import Sigil
    from lychd.agents.factory import AgentForge
    from lychd.agents.services import GrantPort, WorkflowServices
    from lychd.agents.workflows import WorkflowRegistry
    from lychd.domain.cortex.context import ContextOrchestrator
    from lychd.domain.cortex.engine import RunQueue
    from lychd.domain.cortex.events import RunEventBus
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.cortex.stasis import StasisStore
    from lychd.domain.delegation.ports import DelegatedAgentCoordinatorPort
    from lychd.domain.web.fragments import FragmentRegistry

__all__ = [
    "RunSubstrate",
    "get_run_substrate",
    "reset_run_substrate",
    "set_run_substrate",
]


def _default_sigil_provider() -> Callable[[], Sigil]:
    from lychd.agents.services import default_sigil

    return default_sigil


def _empty_queues() -> dict[str, RunQueue]:
    return {}


@dataclass
class RunSubstrate:
    """The run collaborators `perform_run`/`reconcile_runs` execute against."""

    ledger: RunLedger
    bus: RunEventBus
    workflows: WorkflowRegistry
    orchestrator: Any  # TransitionOrchestrator (OrchestratorManager); Any avoids import weight
    dispatcher: GrantPort
    context: ContextOrchestrator
    fragments: FragmentRegistry
    turns: Any  # SessionStore (settled turns; presented via TurnLedgerPort)
    forge: AgentForge
    sigil_provider: Callable[[], Sigil] = field(default_factory=_default_sigil_provider)
    # ConsentLedger is both the Graph park target and the web projection source.
    # Cortex must not import Codex (import law), so this is an opaque handle: the
    # application assembly root and the consent tests thread the real ledger.
    # A run that never parks (a linear/non-Gate workflow) never touches it.
    consents: Any = None
    # Lease ledger and queues are shared per process. Defaults keep isolated domain
    # construction DB-free; application assembly injects the production instances.
    leases: LeaseLedger = field(default_factory=LeaseLedger)
    queues: Mapping[str, RunQueue] = field(default_factory=_empty_queues)
    # Topology A: API cancellation and the in-process worker share this settlement
    # fence so an abort-triggered CancelledError cannot race CANCELLED with FAILED.
    cancellations: RunCancellationCoordinator = field(default_factory=RunCancellationCoordinator)
    claims: RunClaimCoordinator = field(default_factory=RunClaimCoordinator)
    # Durable Stasis is a run-keyed store. Production injects Postgres; the memory
    # profile uses this DB-free implementation only for tests/local memory mode.
    stasis_store: StasisStore = field(default_factory=InMemoryStasisStore)
    # Optional until a concrete sandboxed runtime is composed. Delegation-bearing
    # workflows fail closed when this port is absent; no adapter is fabricated here.
    delegates: DelegatedAgentCoordinatorPort | None = None

    def build_services(self, *, sigil: Sigil | None = None) -> WorkflowServices:
        """Assemble run services with the persisted caller identity.

        The process-level provider remains a test/manual fallback. Normal ghoul
        execution supplies the run's persisted Sigil so a restart cannot silently
        widen authority to the daemon's default identity.
        """
        from lychd.agents.services import WorkflowServices

        sigil_provider = self.sigil_provider if sigil is None else lambda: sigil

        return WorkflowServices(
            dispatcher=self.dispatcher,
            orchestrator=self.orchestrator,
            context=self.context,
            fragments=self.fragments,
            turns=self.turns,
            consents=self.consents,
            events=self.bus,
            forge=self.forge,
            sigil_provider=sigil_provider,
            delegates=self.delegates,
        )


_active: RunSubstrate | None = None


def set_run_substrate(substrate: RunSubstrate) -> None:
    """Publish the process run substrate (application assembly root: web lifespan / CLI)."""
    global _active  # noqa: PLW0603 - process handoff seat, mirrors db.engine.get_engine
    _active = substrate


def get_run_substrate() -> RunSubstrate:
    """Return the published run substrate, or raise if the root has not set it."""
    if _active is None:
        msg = "RunSubstrate is not published; the application assembly root must call set_run_substrate()."
        raise RuntimeError(msg)
    return _active


def reset_run_substrate() -> None:
    """Clear the process run substrate (test teardown)."""
    global _active  # noqa: PLW0603 - test teardown of the handoff seat
    _active = None
