"""Runtime link state primitives for orchestration.

``Link`` is the basic connector liveness and lifecycle observation for an
animator. It is a status snapshot, not a transport client, capability grant,
or pool.

Orchestration policy can combine ``link.up`` with exact capability/profile
evidence. Liveness alone never authorizes immediate routing. The additional
hints (activation possibility/cost and reason) help decide whether a down link
is worth bringing up.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class Link:
    """Snapshot of connector liveness and lifecycle reachability.

    ``up`` answers the core orchestration question:
    "Is this connector alive enough to inspect or use, subject to an exact
    capability state and grant?"

    Connectors may update this object in place as readiness changes. The
    remaining fields are policy hints. They allow the orchestrator to make a
    "bring it up or switch elsewhere" decision without coupling orchestration to
    connector-specific probing internals.
    """

    up: bool
    """True when the connector is live; exact profile readiness remains separate."""

    activatable: bool = False
    """True when the connector/runtime can potentially transition to ``up``."""

    estimated_ready_ms: int | None = None
    """Estimated time to become ready, when activation is possible/known."""

    reason: str | None = None
    """Human-readable explanation for the current state (usually when down)."""

    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    """UTC timestamp for when this snapshot was produced."""
