"""Process-local exclusion between worker claim, park, and failure containment.

The Run ledger remains authoritative. This Topology-A guard keeps a successor
worker from acquiring execution while an earlier claim contains child effects.
API cancellation may still fence the Run as CANCELLING; that state admits no
successor and must remain available while broker abort waits for a worker to exit.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field


@dataclass
class _ClaimGuard:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    users: int = 0


class RunClaimCoordinator:
    """Retain one guard only while workers hold or await it."""

    def __init__(self) -> None:
        """Create an empty loop-confined guard registry."""
        self._guards: dict[str, _ClaimGuard] = {}

    @asynccontextmanager
    async def hold(self, run_id: str) -> AsyncGenerator[None]:
        """Exclude competing worker authority changes for one Run."""
        guard = self._guards.setdefault(run_id, _ClaimGuard())
        guard.users += 1
        try:
            async with guard.lock:
                yield
        finally:
            guard.users -= 1
            if not guard.users:
                self._guards.pop(run_id)
