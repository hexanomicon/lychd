from __future__ import annotations

from datetime import UTC, datetime

from lychd.domain.animation.capabilities import (
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
)
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import capability_specs_from_soulstone
from lychd.domain.animation.services.adapters.contracts import RuntimeAnimator, RuntimePlan
from lychd.domain.animation.services.adapters.runtimes.shared import build_openai_connector
from lychd.domain.animation.services.adapters.surfaces import SoulstoneAnimator


class GenericRuntimeAdapter:
    """Fallback Soulstone planner/runtime builder for unknown runtimes."""

    runtime: str = "generic"
    openai_compatible_runtimes = frozenset(
        {
            "openai_compatible",
            "openai-compatible",
            "openai",
        }
    )

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Preserve explicit command passthrough for unknown runtimes."""
        return RuntimePlan(exec_args=list(soulstone.exec), env_overrides={})

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None:
        """Create a generic runtime handle without assuming an unknown API grammar."""
        if soulstone.runtime in self.openai_compatible_runtimes:
            connector = build_openai_connector(
                soulstone=soulstone,
                runtime=soulstone.runtime,
            )
            return SoulstoneAnimator(rune=soulstone, connector=connector)

        return None

    def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]:
        """Synthesize capability specs only when the generic runtime declares intent."""
        if soulstone.runtime not in self.openai_compatible_runtimes:
            return []
        return capability_specs_from_soulstone(soulstone)

    async def probe_capability_states(
        self,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
    ) -> list[CapabilityState]:
        """Project connector readiness into conservative non-dynamic capability states."""
        up = animator.connector.link.up
        checked_at = datetime.now(UTC)
        return [
            CapabilityState(
                capability_key=spec.key,
                phase=CapabilityPhase.WARM if up else CapabilityPhase.COLD,
                health="ok" if up else "down",
                reason=None if up else "connector_down",
                checked_at=checked_at,
            )
            for spec in specs
        ]


__all__ = ["GenericRuntimeAdapter"]
