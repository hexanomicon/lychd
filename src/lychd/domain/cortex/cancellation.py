"""Loop-confined coordination for API cancellation and in-process run workers.

Topology A executes the SAQ worker and the web request on one event loop.  Aborting
an active SAQ job therefore creates a small but important race: the worker receives
``CancelledError`` before the request has durably written ``CANCELLED``.  This
coordinator lets the worker wait for that write instead of racing it with ``FAILED``.

It is deliberately process-local.  A future multi-process worker topology needs a
durable ``CANCELLING`` state or equivalent broker/database protocol, not a larger
version of this object.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

__all__ = ["RunCancellationCoordinator"]


@dataclass
class _PendingCancellation:
    """One run's shared completion signal."""

    event: asyncio.Event = field(default_factory=asyncio.Event)


class RunCancellationCoordinator:
    """Coordinate cancellation writers on the single Topology-A event loop."""

    __slots__ = ("_pending",)

    def __init__(self) -> None:
        """Create an empty run-to-cancellation map."""
        self._pending: dict[str, _PendingCancellation] = {}

    def begin(self, run_id: str) -> bool:
        """Elect one cancellation writer; concurrent callers become waiters."""
        if run_id in self._pending:
            return False
        self._pending[run_id] = _PendingCancellation()
        return True

    def finish(self, run_id: str) -> None:
        """Release the elected writer and wake its API/worker waiters."""
        pending = self._pending.pop(run_id, None)
        if pending is None:
            return
        pending.event.set()

    def active(self, run_id: str) -> bool:
        """Return whether an API cancellation is currently settling this run."""
        return run_id in self._pending

    async def wait(self, run_id: str) -> None:
        """Wait for current cancellation writers, if any, to finish settling."""
        pending = self._pending.get(run_id)
        if pending is not None:
            await pending.event.wait()
