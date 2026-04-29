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
    SglangStone,
)
from lychd.extensions.builtin.animator.soulstones import SglangSoulstone


class SglangRuntimeAdapter:
    """SGLang planner and runtime animator factory (OpenAI-compatible)."""

    runtime = "sglang"

    def supports(self, runtime: str) -> bool:
        return runtime == self.runtime

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None:
        """Build SGLang runtime handle with OpenAI-compatible connector surface."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=SglangSoulstone,
            runtime=self.runtime,
        )
        connector = build_openai_connector(soulstone=stone, runtime=self.runtime)
        return SglangStone(rune=stone, connector=connector)

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Plan SGLang runtime args from typed or passthrough mode."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=SglangSoulstone,
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


__all__ = ["SglangRuntimeAdapter"]
