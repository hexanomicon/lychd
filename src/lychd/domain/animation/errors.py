"""Shared capability/activation exceptions (A3-U4 / spec §9).

Single home for the dispatch-and-activation error taxonomy. ``await_warm`` and
the registry raise ``CapabilityUnavailable`` (and its ``ActivationTimeout`` /
``ActivationFailed`` refinements). ``HardwareTransitionRequired`` is rehomed here
per spec §9 so the Dispatcher/OrchestratorManager (agents builder) can import the
canonical type instead of the dispatcher-local copy.
"""

from __future__ import annotations


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

    def __init__(self, capability_key: str) -> None:
        """Store the capability identity required to resume dispatch."""
        super().__init__(f"Hardware transition required for capability: {capability_key}")
        self.capability_key = capability_key


class ActivationTimeout(CapabilityUnavailable):
    """Raised when a capability did not reach WARM before the deadline."""

    def __init__(self, capability_key: str, reason: str | None = None) -> None:
        """Report that the capability did not converge before its deadline."""
        super().__init__(capability_key, reason or "activation timed out before warm")


class ActivationFailed(CapabilityUnavailable):
    """Raised when activation observed a terminal ERROR phase."""

    def __init__(self, capability_key: str, reason: str | None = None) -> None:
        """Report the terminal runtime reason for an activation failure."""
        super().__init__(capability_key, reason or "activation failed")


__all__ = [
    "ActivationFailed",
    "ActivationTimeout",
    "CapabilityUnavailable",
    "HardwareTransitionRequired",
]
