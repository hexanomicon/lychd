from __future__ import annotations

from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import (
    capability_specs_from_soulstone,
    default_model_id_for_soulstone,
    model_infos_from_soulstone,
)
from lychd.domain.animation.services.adapters.contracts import LISTEN_HOST, RuntimeAnimator, RuntimePlan
from lychd.domain.animation.services.adapters.runtimes.shared import (
    build_openai_connector,
    require_runtime_soulstone,
)
from lychd.domain.animation.services.adapters.surfaces import (
    SglangStone,
)
from lychd.extensions.builtin.animator.soulstones import SglangSoulstoneConfig


class SglangRuntimeAdapter:
    """SGLang planner and runtime animator factory (OpenAI-compatible)."""

    runtime = "sglang"

    def supports(self, runtime: str) -> bool:
        return runtime == self.runtime

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None:
        """Build SGLang runtime handle with OpenAI-compatible connector surface."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=SglangSoulstoneConfig,
            runtime=self.runtime,
        )
        connector = build_openai_connector(
            soulstone=stone,
            runtime=self.runtime,
            metadata=self._runtime_metadata(stone),
        )
        return SglangStone(rune=stone, connector=connector)

    def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]:
        """Synthesize capability specs for an SGLang soulstone."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=SglangSoulstoneConfig,
            runtime=self.runtime,
        )
        return capability_specs_from_soulstone(
            stone,
            runtime_metadata=self._runtime_metadata(stone),
        )

    def probe_capability_states(self, animator: RuntimeAnimator, specs: list[CapabilitySpec]) -> list[CapabilityState]:
        """Project connector link state into capability states."""
        active_model_id = getattr(animator.connector, "default_model_id", None)
        loaded_model_ids = [spec.model_id for spec in specs]
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
                metadata=animator.connector.metadata,
            )
            for spec in specs
        ]

    def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> bool:
        """SGLang currently exposes no canonical dynamic activation path."""
        _ = animator
        _ = spec
        return False

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Plan SGLang runtime args from typed or passthrough mode."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=SglangSoulstoneConfig,
            runtime=self.runtime,
        )

        if stone.exec:
            return RuntimePlan(exec_args=list(stone.exec), env_overrides={})

        model_ref = (
            stone.model_path or default_model_id_for_soulstone(stone, model_infos_from_soulstone(stone)) or stone.name
        )
        args = [
            "python3",
            "-m",
            "sglang.launch_server",
            "--model-path",
            model_ref,
            "--tp",
            str(stone.tensor_parallel_size),
            "--host",
            LISTEN_HOST,
            "--port",
            str(stone.port),
        ]

        if stone.trust_remote_code:
            args.append("--trust-remote-code")
        if stone.chat_template:
            args.extend(["--chat-template", stone.chat_template])
        if stone.attention_backend:
            args.extend(["--attention-backend", stone.attention_backend])
        if stone.quantization:
            args.extend(["--quantization", stone.quantization])
        if stone.enable_marlin:
            args.append("--enable-marlin")

        args.extend(stone.extra_args)
        return RuntimePlan(exec_args=args, env_overrides={})

    def _runtime_metadata(self, soulstone: SglangSoulstoneConfig) -> dict[str, object]:
        """Return adapter-owned metadata surfaced on connector/capability records."""
        metadata: dict[str, object] = {
            "runtime": self.runtime,
            "tensor_parallel_size": soulstone.tensor_parallel_size,
            "dedicated": soulstone.dedicated,
            "persistent_resident": soulstone.persistent_resident,
        }
        if soulstone.attention_backend is not None:
            metadata["attention_backend"] = soulstone.attention_backend
        if soulstone.quantization is not None:
            metadata["quantization"] = soulstone.quantization
        if soulstone.chat_template is not None:
            metadata["chat_template"] = soulstone.chat_template
        return metadata


__all__ = ["SglangRuntimeAdapter"]
