"""The TransitionArbiter — one physical transition at a time (wave3 §5.2).

At most ONE physical transition runs at a time. Contenders are admitted by
``(-priority, arrival seq)`` (higher priority first, FIFO within a priority). A second
caller for the SAME capability key coalesces onto the first's in-flight plan instead
of planning a redundant swap. v1 orders admission only — there is NO preemption of an
in-flight transition (design risk 4, accepted).
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
        self._inflight: dict[str, asyncio.Future[TransitionPlan]] = {}

    async def run(
        self,
        key: str,
        priority: float,
        executor: Callable[[], Awaitable[TransitionPlan]],
    ) -> TransitionPlan:
        """Run ``executor`` in the single-owner critical section, priority-ordered.

        A second caller for the same ``key`` awaits the first's result (the executor
        runs once); it does NOT enqueue a waiter. An executor exception releases the
        section and propagates to ALL same-key waiters.
        """
        existing = self._inflight.get(key)
        if existing is not None:
            return await existing

        future: asyncio.Future[TransitionPlan] = asyncio.get_running_loop().create_future()
        future.add_done_callback(_swallow)
        self._inflight[key] = future

        try:
            await self._acquire(priority)
        except BaseException as exc:
            # Cancelled/failed BEFORE owning the section: _acquire has already
            # withdrawn us from the heap (or handed our slot on). Pop the in-flight
            # future we registered above so same-key retries don't hang on a future
            # that will never resolve, and relay to any coalesced waiters (F2).
            self._inflight.pop(key, None)
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
            self._inflight.pop(key, None)
            self._release()

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
