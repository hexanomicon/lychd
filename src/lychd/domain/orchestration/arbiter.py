"""The TransitionArbiter — one physical transition at a time (wave3 §5.2).

At most ONE physical transition runs at a time. Contenders are admitted by
``(-priority, arrival seq)`` (higher priority first, FIFO within a priority). A second
caller for the SAME capability key at the SAME priority coalesces onto the in-flight
plan. Different priorities remain separate contenders so a low-priority owner can
never cause a qualifying high-priority follower to be declined. v1 orders admission
only — there is NO preemption of an in-flight transition.
"""

from __future__ import annotations

import asyncio
import heapq
from typing import TYPE_CHECKING

import anyio

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from lychd.domain.orchestration.schema import TransitionPlan

__all__ = ["TransitionArbiter", "TransitionDeclined"]


class TransitionDeclined(RuntimeError):  # noqa: N818 - brief-mandated name (design §5.2)
    """A computed HARD_SWAP was refused (priority below the hard-swap gate)."""

    def __init__(self, plan: TransitionPlan, priority: float, threshold: int) -> None:
        """Record the refused plan and the priority/threshold that gated it."""
        super().__init__(
            f"Transition declined for '{'/'.join(plan.launch_coven_ids) or 'target'}': "
            f"priority {priority} < hard-swap threshold {threshold}."
        )
        self.plan = plan
        self.priority = priority
        self.threshold = threshold


def _swallow(future: asyncio.Future[TransitionPlan]) -> None:
    """Retrieve a settled future's exception to silence 'never retrieved' warnings."""
    if not future.cancelled():
        future.exception()


class TransitionArbiter:
    """Serialize physical transitions; coalesce same-key contenders onto one plan."""

    def __init__(self) -> None:
        """Initialize an idle arbiter with no waiters and no in-flight transitions."""
        self._busy = False
        self._seq = 0
        self._waiters: list[tuple[float, int, anyio.Event]] = []
        self._inflight: dict[tuple[str, float], asyncio.Future[TransitionPlan]] = {}

    def follow_inflight(self, key: str, priority: float) -> asyncio.Future[TransitionPlan] | None:
        """Return an isolated wait for an existing same-key, same-priority plan.

        Callers use this before performing their own asynchronous preflight. That
        keeps a follower from failing on a redundant registry probe while its
        cohort owner is already changing the runtime world.
        """
        existing = self._inflight.get((key, priority))
        if existing is None:
            return None
        return asyncio.shield(existing)

    async def run(
        self,
        key: str,
        priority: float,
        executor: Callable[[], Awaitable[TransitionPlan]],
        *,
        resolve_before_acquire: Callable[[], Awaitable[TransitionPlan | None]] | None = None,
    ) -> TransitionPlan:
        """Resolve one cohort, entering the physical section only when required.

        A second caller for the same ``key`` awaits the first's result (the executor
        runs once); it does NOT enqueue a waiter. An executor exception releases the
        section and propagates to ALL same-key waiters. When supplied,
        ``resolve_before_acquire`` runs after the cohort future is registered but
        before global arbitration. A non-``None`` result is final, preserving the
        warm no-op fast path without exposing an asynchronous preflight race.
        """
        cohort = (key, priority)
        existing = self.follow_inflight(key, priority)
        if existing is not None:
            # A follower owns only its wait, not the shared transition. Without
            # shielding, cancelling one follower cancels the shared Future and
            # poisons the owner plus every other same-key follower.
            return await existing

        future: asyncio.Future[TransitionPlan] = asyncio.get_running_loop().create_future()
        future.add_done_callback(_swallow)
        self._inflight[cohort] = future

        resolved = await self._resolve_cohort_before_acquire(cohort, future, resolve_before_acquire)
        if resolved is not None:
            return resolved

        try:
            await self._acquire(priority)
        except BaseException as exc:
            # Cancelled/failed BEFORE owning the section: _acquire has already
            # withdrawn us from the heap (or handed our slot on). Pop the in-flight
            # future we registered above so same-key retries don't hang on a future
            # that will never resolve, and relay to any coalesced waiters (F2).
            self._inflight.pop(cohort, None)
            if not future.done():
                future.set_exception(exc)
            raise

        try:
            result = await executor()
        except BaseException as exc:  # relayed to coalesced waiters via the future
            if not future.done():
                future.set_exception(exc)
            raise
        else:
            if not future.done():
                future.set_result(result)
            return result
        finally:
            self._inflight.pop(cohort, None)
            self._release()

    async def _resolve_cohort_before_acquire(
        self,
        cohort: tuple[str, float],
        future: asyncio.Future[TransitionPlan],
        resolver: Callable[[], Awaitable[TransitionPlan | None]] | None,
    ) -> TransitionPlan | None:
        """Run one registered cohort's optional no-effect resolver."""
        if resolver is None:
            return None
        try:
            resolved = await resolver()
        except BaseException as exc:
            self._inflight.pop(cohort, None)
            if not future.done():
                future.set_exception(exc)
            raise
        if resolved is not None:
            self._inflight.pop(cohort, None)
            if not future.done():
                future.set_result(resolved)
        return resolved

    async def _acquire(self, priority: float) -> None:
        """Enter the critical section, or park in the priority heap until admitted.

        Cancellation-safe: a contender cancelled while parked withdraws its own heap
        entry so a later ``_release`` can't ghost-hand the section to a dead waiter
        (which would wedge ``_busy`` True forever); a contender cancelled AFTER the
        handoff already reached it passes the section straight on (F2).
        """
        if not self._busy:
            self._busy = True
            return
        self._seq += 1
        event = anyio.Event()
        entry = (-priority, self._seq, event)
        heapq.heappush(self._waiters, entry)
        try:
            await event.wait()  # admitted by _release (which keeps _busy True — a handoff)
        except BaseException:
            if event.is_set():
                # The handoff already reached us — we now own the section; pass it on.
                self._release()
            else:
                # Still parked: withdraw so _release won't set a dead waiter's event.
                self._waiters.remove(entry)
                heapq.heapify(self._waiters)
            raise

    def _release(self) -> None:
        """Hand the section to the highest-priority waiter, or go idle."""
        if self._waiters:
            _, _, event = heapq.heappop(self._waiters)
            event.set()
        else:
            self._busy = False
