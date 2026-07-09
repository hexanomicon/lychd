"""The one canonical priority vocabulary (cross-cutting: engine, graph, orchestration).

Doctrine scale: an integer ``0..100`` where **higher = hotter** (more urgent). This is
the number a human reads and tunes everywhere (routing table, hard-swap gate, run rows,
transition signals). SAQ's Postgres queue dequeues ``ORDER BY priority ASC`` (lowest
first), so the doctrine number is inverted **once**, at :func:`saq_wire_priority`, and
nowhere else. Keep every stored/compared priority in doctrine units; convert only at the
SAQ enqueue boundary.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "PRIORITY_BACKGROUND",
    "PRIORITY_DEFAULT",
    "PRIORITY_INTERACTIVE",
    "PRIORITY_MAX",
    "Priority",
    "saq_wire_priority",
]

# Doctrine scale: 0..100, HIGHER = hotter. A plain int alias so it composes with the
# existing routing/ledger ``int`` columns without a wrapper type; the alias documents
# intent at the seams that pass it.
type Priority = int

PRIORITY_MAX: Final[Priority] = 100
PRIORITY_INTERACTIVE: Final[Priority] = 70  # matches routing 'bridge'
PRIORITY_DEFAULT: Final[Priority] = 50  # matches routing 'default'/'cli'
PRIORITY_BACKGROUND: Final[Priority] = 20  # matches routing 'rite'


def saq_wire_priority(priority: Priority) -> int:
    """Convert a doctrine priority (higher=hotter) to a SAQ wire number (lower=hotter).

    THE single inversion point. SAQ dequeues lowest-first, so a hotter doctrine
    priority must map to a lower wire number.
    """
    return PRIORITY_MAX - priority
