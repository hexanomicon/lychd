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
    VllmStone,
)
from lychd.extensions.builtin.animator.soulstones import VllmSoulstoneConfig
from lychd.system.schemas import QuadletContainer


class VllmRuntimeAdapter:
    """vLLM planner and runtime animator factory (OpenAI-compatible)."""

    runtime = "vllm"

    def supports(self, runtime: str) -> bool:
        return runtime == self.runtime

    def build_runtime(self, soulstone: SoulstoneConfig, quadlet: QuadletContainer) -> RuntimeAnimator | None:
        """Build vLLM runtime handle with OpenAI-compatible connector surface."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=VllmSoulstoneConfig,
            runtime=self.runtime,
        )
        connector = build_openai_connector(
            soulstone=stone,
            runtime=self.runtime,
            metadata=self._runtime_metadata(stone),
        )
        return VllmStone(rune=stone, connector=connector, quadlet=quadlet)

    def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]:
        """Synthesize capability specs for a vLLM soulstone."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=VllmSoulstoneConfig,
            runtime=self.runtime,
        )
        return capability_specs_from_soulstone(
            stone,
            runtime_metadata=self._runtime_metadata(stone),
            runtime_defaults=self._runtime_defaults(stone),
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
        """VLLM currently exposes no canonical dynamic activation path."""
        _ = animator
        _ = spec
        return False

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Plan vLLM runtime and container args from typed or passthrough mode."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=VllmSoulstoneConfig,
            runtime=self.runtime,
        )

        podman_args = self._container_podman_args(stone)

        if stone.exec:
            return RuntimePlan(exec_args=list(stone.exec), env_overrides={}, podman_args=podman_args)

        args = self._managed_exec_args(stone)
        return RuntimePlan(exec_args=args, env_overrides={}, podman_args=podman_args)

    def _managed_exec_args(self, soulstone: VllmSoulstoneConfig) -> list[str]:
        """Build deterministic vLLM managed-mode command arguments."""
        model_infos = model_infos_from_soulstone(soulstone)
        default_model_id = default_model_id_for_soulstone(soulstone, model_infos) or soulstone.name
        model_ref = soulstone.model_path or default_model_id
        args = [
            "serve",
            model_ref,
            "--host",
            LISTEN_HOST,
            "--port",
            str(soulstone.port),
            "--served-model-name",
            default_model_id,
            "--tensor-parallel-size",
            str(soulstone.tensor_parallel_size),
            "--gpu-memory-utilization",
            str(soulstone.gpu_memory_utilization),
        ]

        if soulstone.language_model_only:
            args.append("--language-model-only")
        if soulstone.max_model_len is not None:
            args.extend(["--max-model-len", str(soulstone.max_model_len)])
        if soulstone.max_num_seqs is not None:
            args.extend(["--max-num-seqs", str(soulstone.max_num_seqs)])
        if soulstone.quantization:
            args.extend(["--quantization", soulstone.quantization])
        if soulstone.tool_call_parser:
            args.extend(["--tool-call-parser", soulstone.tool_call_parser])
        if soulstone.reasoning_parser:
            args.extend(["--reasoning-parser", soulstone.reasoning_parser])
        if soulstone.enable_auto_tool_choice:
            args.append("--enable-auto-tool-choice")
        if soulstone.trust_remote_code:
            args.append("--trust-remote-code")

        args.extend(soulstone.extra_args)
        return args

    def _container_podman_args(self, soulstone: VllmSoulstoneConfig) -> list[str]:
        """Build deterministic podman flags required by vLLM profile toggles."""
        args: list[str] = []
        if soulstone.ipc_host:
            args.append("--ipc=host")
        if soulstone.network_host:
            args.append("--network=host")
        return args

    def _runtime_defaults(self, soulstone: VllmSoulstoneConfig) -> dict[str, object]:
        """Expose runtime generation defaults used for capability synthesis."""
        defaults: dict[str, object] = {}
        if soulstone.max_model_len is not None:
            defaults["max_context"] = soulstone.max_model_len
        return defaults

    def _runtime_metadata(self, soulstone: VllmSoulstoneConfig) -> dict[str, object]:
        """Return adapter-owned metadata surfaced on connector/capability records."""
        metadata: dict[str, object] = {
            "runtime": self.runtime,
            "tensor_parallel_size": soulstone.tensor_parallel_size,
            "gpu_memory_utilization": soulstone.gpu_memory_utilization,
        }
        if soulstone.max_num_seqs is not None:
            metadata["max_num_seqs"] = soulstone.max_num_seqs
        if soulstone.reasoning_parser is not None:
            metadata["reasoning_parser"] = soulstone.reasoning_parser
        if soulstone.tool_call_parser is not None:
            metadata["tool_call_parser"] = soulstone.tool_call_parser
        return metadata


__all__ = ["VllmRuntimeAdapter"]
