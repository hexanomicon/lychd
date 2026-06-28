from __future__ import annotations

from typing import cast

from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import capability_specs_from_soulstone
from lychd.domain.animation.services.adapters.contracts import RuntimeAnimator, RuntimePlan
from lychd.domain.animation.services.adapters.runtimes.shared import (
    build_openai_connector,
    probe_openai_compatible_link,
    require_runtime_soulstone,
)
from lychd.domain.animation.services.adapters.surfaces import (
    OpenAICompatibleConnector,
    SglangStone,
)
from lychd.extensions.builtin.animator.soulstones import SglangSoulstoneConfig
from lychd.system.schemas import QuadletContainer


class SglangRuntimeAdapter:
    """SGLang planner and runtime animator factory (OpenAI-compatible).

    The adapter only owns the container envelope and the capability/probe
    plumbing. SGLang framework flags are never re-typed here; the operator's
    ``exec`` list is authoritative.
    """

    runtime = "sglang"

    def supports(self, runtime: str) -> bool:
        return runtime == self.runtime

    def build_runtime(self, soulstone: SoulstoneConfig, quadlet: QuadletContainer) -> RuntimeAnimator | None:
        """Build SGLang runtime handle with OpenAI-compatible connector surface."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=SglangSoulstoneConfig,
            runtime=self.runtime,
        )
        connector = build_openai_connector(
            soulstone=stone,
            runtime=self.runtime,
            metadata=self._runtime_metadata(),
        )
        return SglangStone(rune=stone, connector=connector, quadlet=quadlet)

    def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]:
        """Synthesize capability specs for an SGLang soulstone."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=SglangSoulstoneConfig,
            runtime=self.runtime,
        )
        return capability_specs_from_soulstone(
            stone,
            runtime_metadata=self._runtime_metadata(),
        )

    def probe_capability_states(self, animator: RuntimeAnimator, specs: list[CapabilitySpec]) -> list[CapabilityState]:
        """Probe the OpenAI-compatible endpoint and project live capability states."""
        connector = cast("OpenAICompatibleConnector", animator.connector)
        link = probe_openai_compatible_link(connector)
        connector.set_link(link)
        up = link.up
        active_model_id = getattr(connector, "default_model_id", None)
        loaded_model_ids = [spec.model_id for spec in specs]
        return [
            CapabilityState(
                capability_key=spec.key,
                is_static=True,
                is_active=up,
                is_available=True,
                warm=up,
                health="ok" if up else "down",
                active_model_id=active_model_id,
                loaded_model_ids=loaded_model_ids if up else [],
                reason=link.reason,
                metadata=connector.metadata,
            )
            for spec in specs
        ]

    def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> bool:
        """SGLang currently exposes no canonical dynamic activation path."""
        _ = animator
        _ = spec
        return False

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Plan the SGLang container envelope; framework flags come from ``exec`` verbatim."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=SglangSoulstoneConfig,
            runtime=self.runtime,
        )
        podman_args = self._container_podman_args(stone)
        return RuntimePlan(
            exec_args=list(stone.exec),
            env_overrides={},
            podman_args=podman_args,
        )

    def _container_podman_args(self, soulstone: SglangSoulstoneConfig) -> list[str]:
        """Build deterministic podman flags required by the Soulstone container envelope."""
        args: list[str] = []
        if soulstone.ipc_host:
            args.append("--ipc=host")
        if soulstone.network_host:
            args.append("--network=host")
        return args

    def _runtime_metadata(self) -> dict[str, object]:
        """Return adapter-owned metadata surfaced on connector/capability records."""
        return {"runtime": self.runtime}


__all__ = ["SglangRuntimeAdapter"]
