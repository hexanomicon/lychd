"""Durable admission identities for operator-requested Nexus transitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class SwapRequestClaim:
    """The first admitted target for one caller-owned request identity."""

    request_id: str
    target: str
    created: bool


@runtime_checkable
class SwapRequestLedger(Protocol):
    """Reserve operator transition identities before physical work may launch."""

    async def claim(self, *, request_id: str, target: str) -> SwapRequestClaim:
        """Return the immutable first admission, creating it when absent."""
        ...


class InMemorySwapRequestLedger:
    """Process-local admission ledger for the explicitly non-durable profile."""

    def __init__(self) -> None:
        """Create an empty process-lifetime request ledger."""
        self._targets: dict[str, str] = {}

    async def claim(self, *, request_id: str, target: str) -> SwapRequestClaim:
        """Claim without yielding so callers on one event loop cannot race."""
        existing = self._targets.get(request_id)
        if existing is not None:
            return SwapRequestClaim(request_id=request_id, target=existing, created=False)
        self._targets[request_id] = target
        return SwapRequestClaim(request_id=request_id, target=target, created=True)


__all__ = ["InMemorySwapRequestLedger", "SwapRequestClaim", "SwapRequestLedger"]
