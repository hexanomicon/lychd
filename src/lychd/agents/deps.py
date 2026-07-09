"""`LychDDeps` — the per-step covenant carried into every agent run (A5 §4).

Built fresh per node run because the grant is a per-step lease (Grant Lease
Doctrine). Carries authority (`Sigil`) and hydrated surfaces, never raw secrets:
credentials stay in connector construction inside the control plane.

The narrow ports (`GrantPort`, `TransitionPort`) let agent tools read their
collaborators off `ctx.deps` instead of reaching back into workflow module
globals — that is what kills the old orchestrator reach-back.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

# The frozen `Sigil` lives in `domain/codex/sigil.py` (the identity floor). Re-exported
# here VERBATIM so every historical `from lychd.agents.deps import Sigil` still resolves.
from lychd.domain.codex.sigil import Sigil

if TYPE_CHECKING:
    from lychd.agents.services import GrantPort, TransitionPort
    from lychd.domain.animation.capabilities import CapabilityGrant
    from lychd.domain.cortex.context import ContextOrchestrator
    from lychd.domain.cortex.priority import Priority


@dataclass(frozen=True, kw_only=True)
class LychDDeps:
    """Per-step run dependencies handed to `THE_FIRST_ONE`."""

    sigil: Sigil
    grant: CapabilityGrant
    dispatcher: GrantPort
    orchestrator: TransitionPort
    context: ContextOrchestrator
    run_id: str
    step_id: str
    # The run's doctrine priority — so an agent-proposed transition (`request_coven_swap`)
    # enacts at the run's real standing instead of a hardcoded default that bypassed the gate.
    priority: Priority
