"""Claim gate used while the orchestrator mutates runtime state."""

from __future__ import annotations

import asyncio

__all__ = ["GhoulBroker"]


class GhoulBroker:
    """Pause new run claims while an existing lease set drains."""

    def __init__(self) -> None:
        """Create an open claim gate."""
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

    async def unpause_queues(self) -> None:
        """Re-open the claim gate: parked intake resumes."""
        self._claim_gate.set()
