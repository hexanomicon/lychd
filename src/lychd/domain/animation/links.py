"""Runtime link state primitives for orchestration.

``Link`` is the basic orchestration readiness primitive for an animator's
connector. It is a status snapshot, not a transport client and not a pool.

Orchestration policy can use ``link.up`` for immediate routing and inspect the
additional hints (activation possibility/cost and reason) to decide whether a
down link is worth bringing up.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class Link:
    """Snapshot of connector readiness for request dispatch.

    ``up`` answers the core orchestration question:
    "Can requests be sent to this animator *right now*?"

    Connectors may update this object in place as readiness changes. The
    remaining fields are policy hints. They allow the orchestrator to make a
    "bring it up or switch elsewhere" decision without coupling orchestration to
    connector-specific probing internals.
    """

    up: bool
    """True when requests can be sent immediately."""

    activatable: bool = False
    """True when the connector/runtime can potentially transition to ``up``."""

    estimated_ready_ms: int | None = None
    """Estimated time to become ready, when activation is possible/known."""

    reason: str | None = None
    """Human-readable explanation for the current state (usually when down)."""

    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    """UTC timestamp for when this snapshot was produced."""
