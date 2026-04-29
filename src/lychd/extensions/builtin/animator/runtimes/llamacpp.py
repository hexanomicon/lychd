from __future__ import annotations

from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.contracts import LISTEN_HOST, RuntimeAnimator, RuntimePlan
from lychd.domain.animation.services.adapters.runtimes.shared import require_runtime_soulstone
from lychd.domain.animation.services.adapters.surfaces import (
    LlamacppConnector,
    LlamacppStone,
    local_link_default,
)
from lychd.extensions.builtin.animator.llamacpp.parser import LlamaCppCommandParser, LlamaCppRuntimeInference
from lychd.extensions.builtin.animator.llamacpp.runtime import LlamaCppDescriptor, LlamaCppRuntimePlanner
from lychd.extensions.builtin.animator.soulstones import LlamaCppSoulstone


class LlamaCppRuntimeAdapter:
    """llama.cpp planner and runtime animator factory."""

    runtime = "llamacpp"

    def __init__(
        self,
        parser: LlamaCppCommandParser | None = None,
        planner: LlamaCppRuntimePlanner | None = None,
    ) -> None:
        """Initialize adapter with optional parser/planner overrides."""
        self._parser = parser or LlamaCppCommandParser()
        self._planner = planner or LlamaCppRuntimePlanner()

    def supports(self, runtime: str) -> bool:
        return runtime == self.runtime

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None:
        """Build llama.cpp runtime handle with control-plane metadata attached."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=LlamaCppSoulstone,
            runtime=self.runtime,
        )
        descriptor = self._describe_runtime(stone)
        connector = LlamacppConnector(
            link=local_link_default(runtime=self.runtime),
            base_url=stone.base_url,
            model_infos=descriptor.model_infos,
            default_model_id=descriptor.default_model_id,
            mode=descriptor.mode,
            router_query_model_id=descriptor.router_query_model_id,
            metadata=descriptor.metadata,
        )
        return LlamacppStone(rune=stone, connector=connector)

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Plan llama.cpp command args from passthrough or managed fields."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=LlamaCppSoulstone,
            runtime=self.runtime,
        )

        if stone.exec:
            return RuntimePlan(exec_args=list(stone.exec), env_overrides={})

        inferred = self._infer_runtime(stone)
        mode = inferred.mode or stone.resolved_mode()
        args = self._planner.plan_exec_args(
            soulstone=stone,
            inferred=inferred,
            mode=mode,
            listen_host=LISTEN_HOST,
        )
        return RuntimePlan(exec_args=args, env_overrides={})

    def _describe_runtime(self, soulstone: LlamaCppSoulstone) -> LlamaCppDescriptor:
        """Produce connector-facing runtime descriptor for llama.cpp orchestration."""
        inferred = self._infer_runtime(soulstone)
        mode = inferred.mode or soulstone.resolved_mode()
        return self._planner.describe_runtime(
            soulstone=soulstone,
            inferred=inferred,
            mode=mode,
            parser=self._parser,
        )

    def _infer_runtime(self, soulstone: LlamaCppSoulstone) -> LlamaCppRuntimeInference:
        """Infer runtime metadata from command/extra args and env vars."""
        cmd_inference = LlamaCppRuntimeInference()
        if soulstone.exec:
            cmd_inference = self._parser.infer_args(list(soulstone.exec), source="exec")
        elif soulstone.extra_args:
            cmd_inference = self._parser.infer_args(list(soulstone.extra_args), source="extra_args")

        env_inference = self._parser.infer_env(soulstone.env_vars)
        return self._parser.merge(primary=cmd_inference, secondary=env_inference)


__all__ = ["LlamaCppRuntimeAdapter"]
