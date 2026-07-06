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

if TYPE_CHECKING:
    from collections.abc import Callable

    from lychd.agents.deps import Sigil
    from lychd.agents.factory import AgentForge
    from lychd.agents.services import GrantPort, WorkflowServices
    from lychd.agents.workflows import WorkflowRegistry
    from lychd.domain.cortex.context import ContextOrchestrator
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
    sessions: Any  # BridgeSessionStore (turns + consents; presented via the ledger ports)
    forge: AgentForge
    sigil_provider: Callable[[], Sigil] = field(default_factory=_default_sigil_provider)

    def build_services(self) -> WorkflowServices:
        """Assemble the run's `WorkflowServices` (events = the shared bus)."""
        from lychd.agents.services import build_workflow_services

        return build_workflow_services(
            dispatcher=self.dispatcher,
            orchestrator=self.orchestrator,
            context=self.context,
            fragments=self.fragments,
            sessions=self.sessions,
            events=self.bus,
            forge=self.forge,
            sigil_provider=self.sigil_provider,
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
