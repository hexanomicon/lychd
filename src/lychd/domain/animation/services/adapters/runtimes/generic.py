from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar

from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
)
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import capability_specs_from_soulstone
from lychd.domain.animation.services.adapters.contracts import AnimatorControlPlane, RuntimeAnimator, RuntimePlan
from lychd.domain.animation.services.adapters.runtimes.shared import (
    build_openai_connector,
    resolved_soulstone_base_url,
)
from lychd.domain.animation.services.adapters.surfaces import (
    GenericStone,
    OpenAICompatibleStone,
    PassiveConnector,
    local_link_default,
)


class GenericRuntimeAdapter:
    """Fallback Soulstone planner/runtime builder for unknown runtimes."""

    runtime: ClassVar[str] = "generic"
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
        if soulstone.runtime_name in self.openai_compatible_runtimes:
            connector = build_openai_connector(
                soulstone=soulstone,
                runtime=soulstone.runtime_name,
                kind="generic-openai-compatible",
            )
            return OpenAICompatibleStone(rune=soulstone, connector=connector)

        connector = PassiveConnector(
            kind=f"generic:{soulstone.runtime_name}",
            link=local_link_default(runtime=soulstone.runtime_name),
            base_url=resolved_soulstone_base_url(soulstone),
        )
        return GenericStone(rune=soulstone, connector=connector)

    def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]:
        """Synthesize capability specs only when the generic runtime declares intent."""
        if soulstone.runtime_name not in self.openai_compatible_runtimes:
            return []
        return capability_specs_from_soulstone(soulstone)

    async def probe_capability_states(
        self,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
    ) -> list[CapabilityState]:
        """Project connector readiness into conservative non-dynamic capability states."""
        up = animator.connector.link.up
        active_model_id = getattr(animator.connector, "default_model_id", None)
        loaded_model_ids = [spec.model_id for spec in specs] if up else []
        checked_at = datetime.now(UTC)
        return [
            CapabilityState(
                capability_key=spec.key,
                is_dynamic=False,
                phase=CapabilityPhase.WARM if up else CapabilityPhase.COLD,
                health="ok" if up else "down",
                active_model_id=active_model_id,
                loaded_model_ids=loaded_model_ids,
                reason=None if up else "connector_down",
                checked_at=checked_at,
            )
            for spec in specs
        ]

    async def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> ActivationResult:
        """Report that generic runtimes have no in-runtime activation path."""
        _ = spec
        up = animator.connector.link.up
        return ActivationResult(
            accepted=False,
            phase=CapabilityPhase.WARM if up else CapabilityPhase.COLD,
            reason="fixed capability; lifecycle owned by unit",
        )

    def control_plane(self, animator: RuntimeAnimator) -> AnimatorControlPlane | None:
        """Return ``None``; generic runtimes expose no lifecycle control plane."""
        _ = animator
        return None


__all__ = ["GenericRuntimeAdapter"]
