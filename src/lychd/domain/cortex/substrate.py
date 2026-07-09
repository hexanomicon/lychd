"""`RunSubstrate` — the run collaborators the ghoul plane needs, shared per process.

Topology A (v1): the SAQ worker runs *inside the web server process* on the same
event loop, so the in-process ghoul (`perform_run`) and the SSE handler must share
the SAME `RunEventBus` instance — otherwise a run's tokens would never reach its
open stream. The substrate bundles the run-scoped collaborators once and exposes
them to both contexts.

Cross-context handoff is a process memo (`get/set/reset_run_substrate`), mirroring
`db.engine.get_engine`/`extensions.host.get_extensions` — the established codebase
pattern for a value built once in the composition root and read from the SAQ worker
context. It is lazily read (never at import), so the web lifespan sets it before any
job is ever claimed. It is NOT a mutable module-global singleton of behavior: it is
a test-resettable handoff seat for a value the composition root owns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from lychd.domain.cortex.cancellation import RunCancellationCoordinator
from lychd.domain.cortex.leases import LeaseLedger

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

    from lychd.agents.deps import Sigil
    from lychd.agents.factory import AgentForge
    from lychd.agents.services import GrantPort, WorkflowServices
    from lychd.agents.workflows import WorkflowRegistry
    from lychd.domain.cortex.context import ContextOrchestrator
    from lychd.domain.cortex.engine import RunQueue
    from lychd.domain.cortex.events import RunEventBus
    from lychd.domain.cortex.ledger import RunLedger
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


def _default_stasis_dir() -> Path:
    from lychd.config.settings import get_settings

    return get_settings().stasis.dir


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
    # Wave 4: the ConsentLedger the graph parks into + the web reads (one-record rule).
    # Cortex must NOT import codex (import law), so this is an opaque handle: the
    # composition root and the consent tests thread the real ledger.
    # A run that never parks (a linear/non-Gate workflow) never touches it.
    consents: Any = None
    # Wave 3: the lease ledger + SAQ queues, shared per process. Defaulted so existing
    # test construction sites keep compiling; the root threads the real ones.
    leases: LeaseLedger = field(default_factory=LeaseLedger)
    queues: Mapping[str, RunQueue] = field(default_factory=_empty_queues)
    # Topology A: API cancellation and the in-process worker share this settlement
    # fence so an abort-triggered CancelledError cannot race CANCELLED with FAILED.
    cancellations: RunCancellationCoordinator = field(default_factory=RunCancellationCoordinator)
    # Wave 4: the Durable Stasis checkpoint root (consent tier). Defaulted from
    # settings so existing test construction sites keep compiling; the root threads
    # settings.stasis.dir explicitly.
    stasis_dir: Path = field(default_factory=_default_stasis_dir)

    def build_services(self, *, sigil: Sigil | None = None) -> WorkflowServices:
        """Assemble run services with the persisted caller identity.

        The process-level provider remains a test/manual fallback. Normal ghoul
        execution supplies the run's persisted Sigil so a restart cannot silently
        widen authority to the daemon's default identity.
        """
        from lychd.agents.services import build_workflow_services

        sigil_provider = self.sigil_provider if sigil is None else lambda: sigil

        return build_workflow_services(
            dispatcher=self.dispatcher,
            orchestrator=self.orchestrator,
            context=self.context,
            fragments=self.fragments,
            turns=self.turns,
            consents=self.consents,
            events=self.bus,
            forge=self.forge,
            sigil_provider=sigil_provider,
        )


_active: RunSubstrate | None = None


def set_run_substrate(substrate: RunSubstrate) -> None:
    """Publish the process run substrate (composition root: web lifespan / CLI)."""
    global _active  # noqa: PLW0603 - process handoff seat, mirrors db.engine.get_engine
    _active = substrate


def get_run_substrate() -> RunSubstrate:
    """Return the published run substrate, or raise if the root has not set it."""
    if _active is None:
        msg = "RunSubstrate is not published; the composition root must call set_run_substrate()."
        raise RuntimeError(msg)
    return _active


def reset_run_substrate() -> None:
    """Clear the process run substrate (test teardown)."""
    global _active  # noqa: PLW0603 - test teardown of the handoff seat
    _active = None
