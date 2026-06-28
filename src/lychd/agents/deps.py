"""`LychDDeps` — the per-step covenant carried into every agent run (§5.2).

Built fresh per node run because the grant is a per-step lease (Grant Lease
Doctrine). Carries authority (`Sigil`) and hydrated surfaces, never raw secrets:
credentials stay in connector construction inside the control plane.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilityGrant
    from lychd.domain.cortex.context import ContextOrchestrator
    from lychd.domain.cortex.dispatcher import Dispatcher


@dataclass(frozen=True, kw_only=True)
class Sigil:
    """The Magus's authority handle: a name and a set of scopes, never the secret."""

    name: str
    scopes: frozenset[str]


@dataclass(frozen=True, kw_only=True)
class LychDDeps:
    """Per-step run dependencies handed to `THE_FIRST_ONE`."""

    sigil: Sigil
    grant: CapabilityGrant
    dispatcher: Dispatcher
    phylactery: Any | None
    context: ContextOrchestrator
    run_id: str
    step_id: str
