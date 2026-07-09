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
    probe_openai_compatible_link,
    require_runtime_soulstone,
)
from lychd.domain.animation.services.adapters.surfaces import OpenAICompatibleConnector, SoulstoneAnimator

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilitySpec
    from lychd.domain.animation.services.adapters.contracts import AnimatorControlPlane, RuntimeAnimator, RuntimePlan
    from lychd.system.schemas import QuadletContainer


class OpenAICompatibleRuntimeAdapter:
    """Base adapter for a local runtime that serves an OpenAI-compatible API.

    Always non-dynamic (``is_dynamic=False``): the server binds its port only after
    the model is loaded, so a reachable endpoint means WARM and an unreachable one
    means COLD.
    Subclasses set two class attributes; hooks may be overridden as needed.
    """

    runtime: ClassVar[str] = "openai_compatible"
    config_type: ClassVar[type[SoulstoneConfig]] = SoulstoneConfig

    def supports(self, runtime: str) -> bool:
        return runtime == self.runtime

    def _narrow(self, soulstone: SoulstoneConfig) -> SoulstoneConfig:
        return require_runtime_soulstone(soulstone, expected_type=self.config_type, runtime=self.runtime)

    def runtime_metadata(self) -> dict[str, object]:
        """Adapter-owned metadata surfaced on connector/capability records."""
        return {"runtime": self.runtime}

    def podman_args(self, stone: SoulstoneConfig) -> list[str]:
        """Deterministic podman flags from the host-envelope config fields."""
        args: list[str] = []
        if getattr(stone, "ipc_host", False):
            args.append("--ipc=host")
        if getattr(stone, "network_host", False):
            args.append("--network=host")
        return args

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Plan the container envelope; framework flags come from ``exec`` verbatim."""
        from lychd.domain.animation.services.adapters.contracts import RuntimePlan

        stone = self._narrow(soulstone)
        return RuntimePlan(exec_args=list(stone.exec), env_overrides={}, podman_args=self.podman_args(stone))

    def build_runtime(self, soulstone: SoulstoneConfig, quadlet: QuadletContainer) -> RuntimeAnimator | None:
        """Build a runtime handle with an OpenAI-compatible connector surface."""
        stone = self._narrow(soulstone)
        connector = build_openai_connector(soulstone=stone, runtime=self.runtime, metadata=self.runtime_metadata())
        return SoulstoneAnimator(rune=stone, connector=connector, quadlet=quadlet)

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

        Reachable ⇒ WARM, unreachable ⇒ COLD (spec §2 phase table).
        """
        connector = cast("OpenAICompatibleConnector", animator.connector)
        link = await probe_openai_compatible_link(connector)
        connector.set_link(link)
        up = link.up
        phase = CapabilityPhase.WARM if up else CapabilityPhase.COLD
        active_model_id = getattr(connector, "default_model_id", None)
        loaded_model_ids = [spec.model_id for spec in specs] if up else []
        checked_at = datetime.now(UTC)
        return [
            CapabilityState(
                capability_key=spec.key,
                is_dynamic=False,
                phase=phase,
                health="ok" if up else "down",
                active_model_id=active_model_id,
                loaded_model_ids=loaded_model_ids,
                reason=link.reason,
                checked_at=checked_at,
                metadata=connector.metadata,
            )
            for spec in specs
        ]

    async def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> ActivationResult:
        """Report that non-dynamic runtimes expose no in-runtime activation (unit-owned)."""
        _ = spec
        up = animator.connector.link.up
        phase = CapabilityPhase.WARM if up else CapabilityPhase.COLD
        return ActivationResult(accepted=False, phase=phase, reason="fixed capability; lifecycle owned by unit")

    def control_plane(self, animator: RuntimeAnimator) -> AnimatorControlPlane | None:
        """Return ``None``; non-dynamic OpenAI-compatible runtimes have no control plane."""
        _ = animator
        return None


__all__ = ["OpenAICompatibleRuntimeAdapter"]
