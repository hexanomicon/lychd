from __future__ import annotations

from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import (
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
from lychd.extensions.builtin.animator.soulstones import VllmSoulstone


class VllmRuntimeAdapter:
    """vLLM planner and runtime animator factory (OpenAI-compatible)."""

    runtime = "vllm"

    def supports(self, runtime: str) -> bool:
        return runtime == self.runtime

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None:
        """Build vLLM runtime handle with OpenAI-compatible connector surface."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=VllmSoulstone,
            runtime=self.runtime,
        )
        connector = build_openai_connector(soulstone=stone, runtime=self.runtime)
        return VllmStone(rune=stone, connector=connector)

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Plan vLLM runtime and container args from typed or passthrough mode."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=VllmSoulstone,
            runtime=self.runtime,
        )

        podman_args = self._container_podman_args(stone)

        if stone.exec:
            return RuntimePlan(exec_args=list(stone.exec), env_overrides={}, podman_args=podman_args)

        args = self._managed_exec_args(stone)
        return RuntimePlan(exec_args=args, env_overrides={}, podman_args=podman_args)

    def _managed_exec_args(self, soulstone: VllmSoulstone) -> list[str]:
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

    def _container_podman_args(self, soulstone: VllmSoulstone) -> list[str]:
        """Build deterministic podman flags required by vLLM profile toggles."""
        args: list[str] = []
        if soulstone.ipc_host:
            args.append("--ipc=host")
        if soulstone.network_host:
            args.append("--network=host")
        return args


__all__ = ["VllmRuntimeAdapter"]
