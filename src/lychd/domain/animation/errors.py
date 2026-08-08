"""Shared capability/activation exceptions (A3-U4 / spec §9).

Single home for the dispatch-and-activation error taxonomy. ``await_warm`` and
the registry raise ``CapabilityUnavailable`` (and its ``ActivationTimeout`` /
``ActivationFailed`` refinements). ``HardwareTransitionRequired`` is rehomed here
per spec §9 so the Dispatcher/OrchestratorManager (agents builder) can import the
canonical type instead of the dispatcher-local copy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import ActivationResult, CapabilityState


class CapabilityUnavailable(Exception):  # noqa: N818
    """Raised when a capability cannot be granted and no transition will fix it."""

    def __init__(self, capability_key: str, reason: str | None = None) -> None:
        """Store the offending capability key and an optional human reason."""
        detail = f": {reason}" if reason else ""
        super().__init__(f"Capability unavailable: {capability_key}{detail}")
        self.capability_key = capability_key
        self.reason = reason


class HardwareTransitionRequired(Exception):  # noqa: N818
    """A managed capability needs readiness convergence before re-dispatch.

    The observed phase may be COLD, ACTIVATABLE, or WARMING, and the
    Orchestrator may settle with no-op, soft swap, or hard transition. The
    signal is deliberately handle-free and park-safe: consumers re-fetch the
    spec from the registry by key.
    """

    def __init__(
        self,
        capability_key: str,
        animator_name: str,
        estimated_ready_ms: int | None = None,
    ) -> None:
        """Store the decoupled transition signal (key + animator name + optional ETA)."""
        super().__init__(f"Hardware transition required for capability: {capability_key}")
        self.capability_key = capability_key
        self.animator_name = animator_name
        self.estimated_ready_ms = estimated_ready_ms


class ActivationTimeout(CapabilityUnavailable):
    """Raised when a capability did not reach WARM before the deadline."""

    def __init__(self, capability_key: str, last_state: CapabilityState | None, reason: str | None = None) -> None:
        """Store the last observed state alongside the unavailability signal."""
        super().__init__(capability_key, reason or "activation timed out before warm")
        self.last_state = last_state


class ActivationFailed(CapabilityUnavailable):
    """Raised when activation observed a terminal ERROR phase."""

    def __init__(
        self,
        capability_key: str,
        result: ActivationResult | None = None,
        reason: str | None = None,
    ) -> None:
        """Store the failing activation result alongside the unavailability signal."""
        super().__init__(capability_key, reason or "activation failed")
        self.result = result


__all__ = [
    "ActivationFailed",
    "ActivationTimeout",
    "CapabilityUnavailable",
    "HardwareTransitionRequired",
]
