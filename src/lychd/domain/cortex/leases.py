"""The LeaseLedger — the one truth seam for live capability grants (wave3 §1.6).

In-process, loop-confined registry of live capability grants. Drain honesty comes
from THIS: "no leases remain on the evictee animators", never job counts. A run
parked in stasis holds no lease, so the transition-requesting run never blocks its
own drain.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from lychd.domain.animation.capabilities import CapabilityGrant

__all__ = ["AnimatorAdmission", "LeaseAdmissionClosed", "LeaseLedger", "LeaseRow"]


class AnimatorAdmission(StrEnum):
    """Whether an animator may receive new leases."""

    OPEN = "open"
    DRAINING = "draining"


class LeaseAdmissionClosed(RuntimeError):  # noqa: N818 - domain signal, not an implementation error
    """A lease was refused because its animator entered the drain barrier.

    This is deliberately narrower than ``RuntimeError`` so the Dispatcher can turn
    the expected dispatch/drain race into Live Stasis without hiding genuine ledger
    defects such as duplicate grant ids.
    """

    def __init__(self, animator_name: str) -> None:
        """Record the animator whose admission gate is closed."""
        super().__init__(f"Animator '{animator_name}' is draining; new leases are not admitted.")
        self.animator_name = animator_name


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
        self._draining_animators: set[str] = set()
        # One waiter Event per in-flight `drained()` call. A single shared slot
        # would let two concurrent drains clobber each other's wakeup (the loser
        # sleeps its full timeout even after its animators empty); a set notifies
        # every waiter on release.
        self._release_waiters: set[asyncio.Event] = set()

    def acquire(self, grant: CapabilityGrant, *, priority: int) -> None:
        """Register ``grant.lease`` as a LeaseRow. Duplicate grant_id → RuntimeError."""
        grant_id = grant.lease.grant_id
        animator_name = grant.spec.animator_name
        if self.admission(animator_name) is AnimatorAdmission.DRAINING:
            raise LeaseAdmissionClosed(animator_name)
        if grant_id in self._rows:
            msg = f"Lease already registered for grant_id={grant_id} (double-issue bug)."
            raise RuntimeError(msg)
        self._rows[grant_id] = LeaseRow(
            grant_id=grant_id,
            holder=grant.lease.holder,
            capability_key=grant.spec.key,
            animator_name=animator_name,
            priority=priority,
            issued_at=grant.lease.issued_at,
        )

    def admission(self, animator_name: str) -> AnimatorAdmission:
        """Return the current lease-admission state for one animator."""
        if animator_name in self._draining_animators:
            return AnimatorAdmission.DRAINING
        return AnimatorAdmission.OPEN

    def begin_drain(self, animator_names: Sequence[str]) -> None:
        """Close lease admission for the animators before waiting for them to drain."""
        self._draining_animators.update(animator_names)

    def end_drain(self, animator_names: Sequence[str]) -> None:
        """Reopen lease admission for the animators after a drain attempt finishes."""
        self._draining_animators.difference_update(animator_names)

    def release(self, grant_id: str) -> None:
        """Drop the lease (idempotent) and wake every drain waiter."""
        self._rows.pop(grant_id, None)
        for waiter in self._release_waiters:
            waiter.set()

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
        with contextlib.suppress(TimeoutError):
            async with asyncio.timeout(timeout):
                while True:
                    waiter = asyncio.Event()
                    self._release_waiters.add(waiter)
                    try:
                        await waiter.wait()
                    finally:
                        self._release_waiters.discard(waiter)
                    if _clear():
                        return True
        return _clear()
