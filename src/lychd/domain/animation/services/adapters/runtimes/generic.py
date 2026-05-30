from __future__ import annotations

from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import capability_specs_from_soulstone
from lychd.domain.animation.services.adapters.contracts import RuntimeAnimator, RuntimePlan
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
from lychd.system.schemas import QuadletContainer


class GenericRuntimeAdapter:
    """Fallback Soulstone planner/runtime builder for unknown runtimes."""

    runtime = "generic"
    openai_compatible_runtimes = frozenset(
        {
            "openai_compatible",
            "openai-compatible",
            "openai",
        }
    )

    def supports(self, runtime: str) -> bool:
        return runtime == self.runtime

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Preserve explicit command passthrough for unknown runtimes."""
        return RuntimePlan(exec_args=list(soulstone.exec), env_overrides={})

    def build_runtime(self, soulstone: SoulstoneConfig, quadlet: QuadletContainer) -> RuntimeAnimator | None:
        """Create a generic runtime handle without assuming an unknown API grammar."""
        if soulstone.runtime_name in self.openai_compatible_runtimes:
            connector = build_openai_connector(
                soulstone=soulstone,
                runtime=soulstone.runtime_name,
                kind="generic-openai-compatible",
            )
            return OpenAICompatibleStone(rune=soulstone, connector=connector, quadlet=quadlet)

        connector = PassiveConnector(
            kind=f"generic:{soulstone.runtime_name}",
            link=local_link_default(runtime=soulstone.runtime_name),
            base_url=resolved_soulstone_base_url(soulstone),
        )
        return GenericStone(rune=soulstone, connector=connector, quadlet=quadlet)

    def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]:
        """Synthesize capability specs only when the generic runtime declares intent."""
        if soulstone.runtime_name not in self.openai_compatible_runtimes:
            return []
        return capability_specs_from_soulstone(soulstone)

    def probe_capability_states(self, animator: RuntimeAnimator, specs: list[CapabilitySpec]) -> list[CapabilityState]:
        """Project connector readiness into conservative capability states."""
        active_model_id = getattr(animator.connector, "default_model_id", None)
        loaded_model_ids = [spec.model_id for spec in specs] if animator.connector.link.up else []
        return [
            CapabilityState(
                capability_key=spec.key,
                is_static=True,
                is_active=animator.connector.link.up,
                is_available=True,
                warm=animator.connector.link.up,
                health="ok" if animator.connector.link.up else "down",
                active_model_id=active_model_id,
                loaded_model_ids=loaded_model_ids,
                reason=None if animator.connector.link.up else "connector_down",
            )
            for spec in specs
        ]

    def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> bool:
        """Return ``False`` because generic runtimes have no canonical activation path."""
        _ = animator
        _ = spec
        return False


__all__ = ["GenericRuntimeAdapter"]
