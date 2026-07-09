"""Worker brokers — the orchestrator's drain/pause seam (wave3 §5.3).

`GhoulBroker` is the real broker over the SAQ queues + the LeaseLedger. Drain honesty
comes from the leases (parked runs hold no lease and never count), NEVER from job
counts. Pausing is a claim-gate ``asyncio.Event`` checked by `perform_run` on entry:
the installed saq ``Queue`` exposes no pause/suspend API (verified at build time —
``hasattr(Queue, "pause")`` is False), so the in-loop claim gate is the sanctioned
mechanism. `QuiescentBroker` is retained only as a small DB-free test double; the
production composition root always constructs `GhoulBroker` directly.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from lychd.domain.cortex.engine import RunQueue
    from lychd.domain.cortex.leases import LeaseLedger

__all__ = ["GhoulBroker", "QuiescentBroker"]


class GhoulBroker:
    """Real broker over the SAQ queues + the LeaseLedger.

    ``pause_queues``/``unpause_queues`` toggle a claim gate that `perform_run` awaits
    on entry (there is no saq-native pause). ``broadcast_soft_stop`` is an honest
    no-op in v1 (workers finish their current job; drain is proven by leases).
    ``get_active_worker_count`` counts LIVE LEASES — a run parked AWAITING_HARDWARE
    holds no lease, so it never blocks its own drain.
    """

    def __init__(self, *, queues: Mapping[str, RunQueue], leases: LeaseLedger) -> None:
        """Bind the broker to the process SAQ queues + the lease ledger."""
        self._queues = queues
        self._leases = leases
        self._claim_gate = asyncio.Event()
        self._claim_gate.set()  # open by default: intake proceeds until paused

    @property
    def paused(self) -> bool:
        """True while the claim gate is closed (intake suspended)."""
        return not self._claim_gate.is_set()

    @property
    def claim_gate(self) -> asyncio.Event:
        """The intake gate `perform_run` awaits on entry (`await broker.claim_gate.wait()`)."""
        return self._claim_gate

    async def pause_queues(self) -> None:
        """Close the claim gate: new `perform_run` claims park until unpaused."""
        self._claim_gate.clear()

    async def broadcast_soft_stop(self) -> None:
        """Ask workers to finish their current job (honest no-op in v1; drain = leases)."""
        return

    async def unpause_queues(self) -> None:
        """Re-open the claim gate: parked intake resumes."""
        self._claim_gate.set()

    async def get_active_worker_count(self) -> int:
        """Return the live-lease count (leases, not jobs: parked runs don't count)."""
        return len(self._leases.active())


class QuiescentBroker:
    """A no-op worker broker satisfying `OrchestratorManager`'s drain protocol.

    The v1 in-process profile drains via leases; this stand-in is for focused
    DB-free tests. Production never places it in the runtime container.
    Draining is instantaneous and the active-worker count is always zero.
    """

    async def pause_queues(self) -> None:
        """Pause intake queues (no-op: lease-drain is the truth)."""

    async def broadcast_soft_stop(self) -> None:
        """Ask workers to finish their current job (no-op)."""

    async def unpause_queues(self) -> None:
        """Resume intake queues (no-op)."""

    async def get_active_worker_count(self) -> int:
        """Return the number of still-draining workers (always zero here)."""
        return 0
