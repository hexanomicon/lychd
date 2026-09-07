"""Shared planning and exact-inventory readiness for registered OpenAI-compatible runtimes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from lychd.domain.animation.capabilities import (
    CapabilityPhase,
    CapabilityState,
)
from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import capability_specs_from_model_infos
from lychd.domain.animation.services.adapters.runtimes.shared import (
    build_openai_connector,
    probe_openai_compatible_link,
    require_runtime_soulstone,
)
from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector, SoulstoneAnimator

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilitySpec
    from lychd.domain.animation.services.adapters.contracts import RuntimeAnimator, RuntimePlan

_INFERENCE_SHARED_MEMORY_BYTES = 8 * 1024**3


class OpenAICompatibleRuntimeAdapter:
    """Base adapter for a local runtime that serves an OpenAI-compatible API.

    Always non-dynamic (``is_dynamic=False``): the server binds its port only after
    a model is loaded, but a declared capability is WARM only when the validated
    live ``/models`` inventory contains that exact model id.
    Runtime identity and the exact Rune schema are explicit registration facts.
    """

    def __init__(self, *, runtime: str, config_type: type[SoulstoneConfig]) -> None:
        """Bind one runtime key to its exact accepted Soulstone schema."""
        self.runtime = runtime
        self._config_type = config_type

    def _narrow(self, soulstone: SoulstoneConfig | PortalConfig) -> SoulstoneConfig:
        return require_runtime_soulstone(soulstone, expected_type=self._config_type, runtime=self.runtime)

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Plan the container envelope; framework flags come from ``exec`` verbatim."""
        from lychd.domain.animation.services.adapters.contracts import RuntimePlan

        stone = self._narrow(soulstone)
        return RuntimePlan(
            exec_args=list(stone.exec),
            env_overrides={},
            pod_shared_memory_bytes=_INFERENCE_SHARED_MEMORY_BYTES,
        )

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None:
        """Build a runtime handle with an OpenAI-compatible connector surface."""
        stone = self._narrow(soulstone)
        connector = build_openai_connector(soulstone=stone, runtime=self.runtime)
        return SoulstoneAnimator(rune=stone, connector=connector)

    def build_capability_specs(self, animator: RuntimeAnimator) -> list[CapabilitySpec]:
        """Synthesize non-dynamic capability specs from runtime-derived model info."""
        soulstone = animator.rune
        stone = self._narrow(soulstone)
        connector = cast("OpenAICompatibleConnector", animator.connector)
        return capability_specs_from_model_infos(
            stone,
            connector.model_infos,
            is_dynamic=False,
        )

    async def probe_capability_states(
        self,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
    ) -> list[CapabilityState]:
        """Probe the OpenAI-compatible endpoint and project non-dynamic phase states.

        Reachable plus exact inventory match ⇒ WARM; missing or malformed
        inventory ⇒ ERROR; transport-unreachable ⇒ COLD.
        """
        connector = cast("OpenAICompatibleConnector", animator.connector)
        link = await probe_openai_compatible_link(connector)
        connector.set_link(link)
        up = link.up
        observed_model_ids = connector.observed_model_ids or ()
        inventory_error = connector.inventory_error
        checked_at = datetime.now(UTC)
        states: list[CapabilityState] = []
        for spec in specs:
            model_present = spec.model_id in observed_model_ids
            phase = CapabilityPhase.WARM if up and model_present else CapabilityPhase.COLD
            health = "ok" if phase is CapabilityPhase.WARM else "down"
            reason = link.reason
            if up and inventory_error is not None:
                phase = CapabilityPhase.ERROR
                health = "inventory_invalid"
                reason = inventory_error
            elif up and not model_present:
                phase = CapabilityPhase.ERROR
                health = "model_missing"
                reason = f"declared model {spec.model_id!r} is absent from /models"
            states.append(
                CapabilityState(
                    capability_key=spec.key,
                    phase=phase,
                    health=health,
                    reason=reason,
                    checked_at=checked_at,
                )
            )
        return states


__all__ = ["OpenAICompatibleRuntimeAdapter"]
