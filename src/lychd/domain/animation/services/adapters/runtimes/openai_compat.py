"""Shared base for OpenAI-compatible, non-dynamic runtime adapters.

vLLM and SGLang were ~90% identical exec-passthrough adapters. This base folds
the shared planning/probe/activation plumbing into one place (A3-U2 cheap dedup;
the full leaf rework is A3-U6). A concrete backend is a ~5-line leaf that sets
``runtime`` + ``config_type``. The base is fully generic — it imports no
extension types, keeping the domain-owns-contracts law intact.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar, cast

from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityPhase,
    CapabilityState,
)
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import capability_specs_from_soulstone
from lychd.domain.animation.services.adapters.runtimes.shared import (
    build_openai_connector,
    fixed_openai_activation_result,
    probe_openai_compatible_link,
    require_runtime_soulstone,
)
from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector, SoulstoneAnimator

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilitySpec
    from lychd.domain.animation.services.adapters.contracts import AnimatorControlPlane, RuntimeAnimator, RuntimePlan

_INFERENCE_SHARED_MEMORY_BYTES = 8 * 1024**3


class OpenAICompatibleRuntimeAdapter:
    """Base adapter for a local runtime that serves an OpenAI-compatible API.

    Always non-dynamic (``is_dynamic=False``): the server binds its port only after
    a model is loaded, but a declared capability is WARM only when the validated
    live ``/models`` inventory contains that exact model id.
    Subclasses set two class attributes; hooks may be overridden as needed.
    """

    runtime: ClassVar[str] = "openai_compatible"
    config_type: ClassVar[type[SoulstoneConfig]] = SoulstoneConfig

    def _narrow(self, soulstone: SoulstoneConfig) -> SoulstoneConfig:
        return require_runtime_soulstone(soulstone, expected_type=self.config_type, runtime=self.runtime)

    def runtime_metadata(self) -> dict[str, object]:
        """Adapter-owned metadata surfaced on connector/capability records."""
        return {"runtime": self.runtime}

    def podman_args(self, stone: SoulstoneConfig) -> list[str]:
        """Return no namespace overrides; every Soulstone joins the shared LychD pod."""
        _ = stone
        return []

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Plan the container envelope; framework flags come from ``exec`` verbatim."""
        from lychd.domain.animation.services.adapters.contracts import RuntimePlan

        stone = self._narrow(soulstone)
        return RuntimePlan(
            exec_args=list(stone.exec),
            env_overrides={},
            podman_args=self.podman_args(stone),
            pod_shared_memory_bytes=_INFERENCE_SHARED_MEMORY_BYTES,
        )

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None:
        """Build a runtime handle with an OpenAI-compatible connector surface."""
        stone = self._narrow(soulstone)
        connector = build_openai_connector(soulstone=stone, runtime=self.runtime, metadata=self.runtime_metadata())
        return SoulstoneAnimator(rune=stone, connector=connector)

    def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]:
        """Synthesize non-dynamic capability specs from runtime-derived model info."""
        stone = self._narrow(soulstone)
        return capability_specs_from_soulstone(
            stone,
            runtime_metadata=self.runtime_metadata(),
            runtime_defaults={},
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
                    is_dynamic=False,
                    phase=phase,
                    health=health,
                    active_model_id=spec.model_id if phase is CapabilityPhase.WARM else None,
                    loaded_model_ids=[spec.model_id] if phase is CapabilityPhase.WARM else [],
                    reason=reason,
                    checked_at=checked_at,
                    metadata=connector.metadata,
                )
            )
        return states

    async def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> ActivationResult:
        """Report that non-dynamic runtimes expose no in-runtime activation (unit-owned)."""
        connector = cast("OpenAICompatibleConnector", animator.connector)
        return fixed_openai_activation_result(connector, spec)

    def control_plane(self, animator: RuntimeAnimator) -> AnimatorControlPlane | None:
        """Return ``None``; non-dynamic OpenAI-compatible runtimes have no control plane."""
        _ = animator
        return None


__all__ = ["OpenAICompatibleRuntimeAdapter"]
