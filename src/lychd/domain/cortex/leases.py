"""The LeaseLedger — the one truth seam for live capability grants (wave3 §1.6).

In-process, loop-confined registry of live capability grants. Drain honesty comes
from THIS: "no leases remain on the evictee animators", never job counts. A run
parked in stasis holds no lease, so the transition-requesting run never blocks its
own drain.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

import anyio

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from lychd.domain.animation.capabilities import CapabilityGrant

__all__ = ["LeaseLedger", "LeaseRow"]


@dataclass(frozen=True, slots=True)
class LeaseRow:
    """Derived accounting row for one live grant."""

    grant_id: str
    holder: str
    capability_key: str
    animator_name: str
    priority: int
    issued_at: datetime


class LeaseLedger:
    """In-process, loop-confined registry of live capability grants.

    THE truth seam: drain = 'no leases remain on the evictee animators', never
    job counts.
    """

    def __init__(self) -> None:
        """Initialize an empty, loop-confined ledger."""
        self._rows: dict[str, LeaseRow] = {}
        self._release_event: asyncio.Event | None = None

    def acquire(self, grant: CapabilityGrant, *, priority: int) -> None:
        """Register ``grant.lease`` as a LeaseRow. Duplicate grant_id → RuntimeError."""
        grant_id = grant.lease.grant_id
        if grant_id in self._rows:
            msg = f"Lease already registered for grant_id={grant_id} (double-issue bug)."
            raise RuntimeError(msg)
        self._rows[grant_id] = LeaseRow(
            grant_id=grant_id,
            holder=grant.lease.holder,
            capability_key=grant.spec.key,
            animator_name=grant.spec.animator_name,
            priority=priority,
            issued_at=grant.lease.issued_at,
        )

    def release(self, grant_id: str) -> None:
        """Drop the lease (idempotent) and wake any drain waiters."""
        self._rows.pop(grant_id, None)
        if self._release_event is not None:
            self._release_event.set()

    def active(self, *, animator_name: str | None = None) -> list[LeaseRow]:
        """Return live lease rows, optionally filtered to one animator."""
        rows = list(self._rows.values())
        if animator_name is None:
            return rows
        return [row for row in rows if row.animator_name == animator_name]

    async def drained(self, animator_names: Sequence[str], *, timeout: float) -> bool:  # noqa: ASYNC109
        """Return True once no leases remain on the given animators; False on timeout."""
        names = set(animator_names)

        def _clear() -> bool:
            return not any(row.animator_name in names for row in self._rows.values())

        if _clear():
            return True
        with anyio.move_on_after(timeout):
            while True:
                self._release_event = asyncio.Event()
                await self._release_event.wait()
                if _clear():
                    return True
        return _clear()
