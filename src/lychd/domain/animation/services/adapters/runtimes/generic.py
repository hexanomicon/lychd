from __future__ import annotations

from typing import TYPE_CHECKING

from lychd.domain.animation.services.adapters.contracts import RuntimePlan

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState
    from lychd.domain.animation.schemas import SoulstoneConfig
    from lychd.domain.animation.services.adapters.contracts import RuntimeAnimator


class GenericRuntimeAdapter:
    """Preserve command planning without inventing an unregistered runtime contract."""

    runtime: str = "generic"

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Preserve explicit command passthrough for unknown runtimes."""
        return RuntimePlan(exec_args=list(soulstone.exec), env_overrides={})

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None:
        """Leave runtime construction to an explicitly registered adapter."""
        _ = soulstone
        return None

    def build_capability_specs(self, animator: RuntimeAnimator) -> list[CapabilitySpec]:
        """Leave an unregistered runtime without an admitted capability catalogue."""
        _ = animator
        return []

    async def probe_capability_states(
        self,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
    ) -> list[CapabilityState]:
        """Refuse to infer runtime readiness from a protocol-shaped label."""
        _ = animator, specs
        return []


__all__ = ["GenericRuntimeAdapter"]
