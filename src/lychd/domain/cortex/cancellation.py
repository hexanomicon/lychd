"""Loop-confined coordination for API cancellation and in-process run workers.

Topology A executes the SAQ worker and the web request on one event loop. This
coordinator elects one local cancellation writer; the Run ledger's ``CANCELLING``
state fences the exact delivery generation before broker containment. An interrupted
worker releases its resources once it sees that election. Before election it may
await its durable election instead of racing cancellation with ``FAILED``.
Workers never wait for full cancellation settlement: broker abort waits for them.

The coordinator is process-local and does not replace the durable Run ledger.
"""

from __future__ import annotations

import asyncio

__all__ = ["RunCancellationCoordinator"]


class RunCancellationCoordinator:
    """Coordinate cancellation writers on the single Topology-A event loop."""

    __slots__ = ("_elections", "_pending")

    def __init__(self) -> None:
        """Create an empty run-to-cancellation map."""
        self._pending: dict[str, asyncio.Event] = {}
        self._elections: dict[str, asyncio.Event] = {}

    def begin(self, run_id: str) -> bool:
        """Elect one cancellation writer; concurrent callers become waiters."""
        if run_id in self._pending:
            return False
        self._pending[run_id] = asyncio.Event()
        self._elections[run_id] = asyncio.Event()
        return True

    def finish(self, run_id: str) -> None:
        """Release the elected writer and wake its API/worker waiters."""
        pending = self._pending.pop(run_id, None)
        if pending is None:
            return
        pending.set()
        election = self._elections.pop(run_id)
        election.set()

    def election_finished(self, run_id: str) -> None:
        """Wake interrupted workers once the durable election has returned."""
        election = self._elections.get(run_id)
        if election is not None:
            election.set()

    async def wait_election(self, run_id: str) -> None:
        """Wait for durable election or leader failure, then re-read Run truth."""
        election = self._elections.get(run_id)
        if election is not None:
            await election.wait()

    def active(self, run_id: str) -> bool:
        """Return whether an API cancellation is currently settling this run."""
        return run_id in self._pending

    async def wait(self, run_id: str) -> None:
        """Wait for current cancellation writers, if any, to finish settling."""
        pending = self._pending.get(run_id)
        if pending is not None:
            await pending.wait()
