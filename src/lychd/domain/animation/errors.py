"""Shared capability/activation exceptions (A3-U4 / spec §9).

Single home for the dispatch-and-activation error taxonomy. ``await_warm`` and
the registry raise ``CapabilityUnavailable`` (and its ``ActivationTimeout`` /
``ActivationFailed`` refinements). ``HardwareTransitionRequired`` is rehomed here
per spec §9 so the Dispatcher/OrchestratorManager (agents builder) can import the
canonical type instead of the dispatcher-local copy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import ActivationResult, CapabilitySpec, CapabilityState


class CapabilityUnavailable(Exception):  # noqa: N818
    """Raised when a capability cannot be granted and no transition will fix it."""

    def __init__(self, capability_key: str, reason: str | None = None) -> None:
        """Store the offending capability key and an optional human reason."""
        detail = f": {reason}" if reason else ""
        super().__init__(f"Capability unavailable: {capability_key}{detail}")
        self.capability_key = capability_key
        self.reason = reason


class HardwareTransitionRequired(Exception):  # noqa: N818
    """Raised when a capability exists but its substrate needs a hard transition.

    Canonical home (spec §9). Wave 1 keeps the handle-bearing
    ``(spec, state, animator)`` signature the ``OrchestratorManager`` transition
    solver consumes (``exception.spec``/``.state``/``.animator``). The decoupled
    ``(capability_key, animator_name, estimated_ready_ms)`` shape lands in Wave 3
    (A3-U7 / A4-U5) alongside the grant-lease dispatcher surface and the matching
    solver refactor.
    """

    def __init__(self, spec: CapabilitySpec, state: CapabilityState, animator: Any) -> None:
        """Store the canonical capability record that requires a transition."""
        super().__init__(f"Hardware transition required for capability: {spec.key}")
        self.spec = spec
        self.state = state
        self.animator = animator


class ActivationTimeout(CapabilityUnavailable):
    """Raised when a capability did not reach WARM before the deadline."""

    def __init__(self, capability_key: str, last_state: CapabilityState, reason: str | None = None) -> None:
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
