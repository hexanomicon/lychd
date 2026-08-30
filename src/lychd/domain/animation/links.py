"""Runtime link state primitives for orchestration.

``Link`` is the basic connector liveness and lifecycle observation for an
animator. It is a status snapshot, not a transport client, capability grant,
or pool.

Orchestration policy can combine ``link.up`` with exact capability/profile
evidence. Liveness alone never authorizes immediate routing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Link:
    """Snapshot of connector liveness and lifecycle reachability.

    ``up`` answers the core orchestration question:
    "Is this connector alive enough to inspect or use, subject to an exact
    capability state and grant?"

    Connectors may update this object in place as readiness changes.
    """

    up: bool
    """True when the connector is live; exact profile readiness remains separate."""

    reason: str | None = None
    """Human-readable explanation for the current state (usually when down)."""
