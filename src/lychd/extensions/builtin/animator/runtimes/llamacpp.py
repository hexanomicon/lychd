from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import capability_specs_from_model_infos
from lychd.domain.animation.services.adapters.contracts import LISTEN_HOST, RuntimeAnimator, RuntimePlan
from lychd.domain.animation.services.adapters.runtimes.shared import require_runtime_soulstone
from lychd.domain.animation.services.adapters.surfaces import (
    LlamacppConnector,
    LlamacppStone,
    local_link_default,
)
from lychd.system.schemas import QuadletContainer
from lychd.extensions.builtin.animator.llamacpp.control_plane import LlamaCppControlPlane, LlamaCppControlPlaneError
from lychd.extensions.builtin.animator.llamacpp.parser import LlamaCppCommandParser, LlamaCppRuntimeInference
from lychd.extensions.builtin.animator.llamacpp.runtime import LlamaCppDescriptor, LlamaCppRuntimePlanner
from lychd.extensions.builtin.animator.soulstones import LlamaCppSoulstoneConfig


class LlamaCppRuntimeAdapter:
    """llama.cpp planner and runtime animator factory."""

    runtime = "llamacpp"

    def __init__(
        self,
        parser: LlamaCppCommandParser | None = None,
        planner: LlamaCppRuntimePlanner | None = None,
        control_plane: LlamaCppControlPlane | None = None,
    ) -> None:
        """Initialize adapter with optional parser/planner overrides."""
        self._parser = parser or LlamaCppCommandParser()
        self._planner = planner or LlamaCppRuntimePlanner()
        self._control_plane = control_plane or LlamaCppControlPlane()

    def supports(self, runtime: str) -> bool:
        return runtime == self.runtime

    def build_runtime(self, soulstone: SoulstoneConfig, quadlet: QuadletContainer) -> RuntimeAnimator | None:
        """Build llama.cpp runtime handle with control-plane metadata attached."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=LlamaCppSoulstoneConfig,
            runtime=self.runtime,
        )
        descriptor = self._describe_runtime(stone)
        base_url = str(stone.base_url) if stone.base_url is not None else f"http://localhost:{stone.port}/v1"
        connector = LlamacppConnector(
            link=local_link_default(runtime=self.runtime),
            base_url=base_url,
            model_infos=descriptor.model_infos,
            default_model_id=descriptor.default_model_id,
            mode=descriptor.mode,
            router_query_model_id=descriptor.router_query_model_id,
            metadata=descriptor.metadata,
        )
        return LlamacppStone(rune=stone, connector=connector, quadlet=quadlet)

    def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]:
        """Synthesize capability specs for llama.cpp single or router runtimes."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=LlamaCppSoulstoneConfig,
            runtime=self.runtime,
        )
        descriptor = self._describe_runtime(stone)
        return capability_specs_from_model_infos(
            stone,
            descriptor.model_infos,
            runtime_metadata=descriptor.metadata,
            runtime_defaults=self._runtime_defaults(descriptor),
            lifecycle_mode="dynamic_soft" if descriptor.mode == "router" else "static",
        )

    def probe_capability_states(self, animator: RuntimeAnimator, specs: list[CapabilitySpec]) -> list[CapabilityState]:
        """Map llama.cpp connector and optional control-plane data into capability states."""
        connector = animator.connector
        mode = getattr(connector, "mode", "single")
        if connector.link.up:
            try:
                lifecycle = self._control_plane.inspect_animator(animator)
            except LlamaCppControlPlaneError as exc:
                return self._fallback_states(
                    animator=animator,
                    specs=specs,
                    mode=mode,
                    health="error",
                    reason=str(exc),
                )

            loaded_ids = list(lifecycle.loaded_models)
            active_model = self._normalize_active_model_id(lifecycle, specs)
            states: list[CapabilityState] = []
            for spec in specs:
                is_static = mode != "router"
                is_active = spec.model_id == active_model if mode == "router" else lifecycle.health == "ok"
                states.append(
                    CapabilityState(
                        capability_key=spec.key,
                        is_static=is_static,
                        is_active=is_active,
                        is_available=True,
                        warm=lifecycle.health == "ok" and (is_active or is_static),
                        health=lifecycle.health,
                        active_model_id=active_model,
                        loaded_model_ids=loaded_ids,
                        reason=None if is_active or is_static else "model_not_loaded",
                        metadata=dict(lifecycle.raw),
                    )
                )
            return states

        return self._fallback_states(
            animator=animator,
            specs=specs,
            mode=mode,
            health="down",
            reason=connector.link.reason or "runtime_not_probed",
        )

    def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> bool:
        """Perform router-native model activation when the runtime supports it."""
        connector = animator.connector
        if getattr(connector, "mode", "single") != "router":
            return False
        return self._control_plane.load_model(animator.connector.base_url, spec.model_id)

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Plan llama.cpp command args from passthrough or managed fields."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=LlamaCppSoulstoneConfig,
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

    def _describe_runtime(self, soulstone: LlamaCppSoulstoneConfig) -> LlamaCppDescriptor:
        """Produce connector-facing runtime descriptor for llama.cpp orchestration."""
        inferred = self._infer_runtime(soulstone)
        mode = inferred.mode or soulstone.resolved_mode()
        return self._planner.describe_runtime(
            soulstone=soulstone,
            inferred=inferred,
            mode=mode,
            parser=self._parser,
        )

    def _infer_runtime(self, soulstone: LlamaCppSoulstoneConfig) -> LlamaCppRuntimeInference:
        """Infer runtime metadata from command/extra args and env vars."""
        cmd_inference = LlamaCppRuntimeInference()
        if soulstone.exec:
            cmd_inference = self._parser.infer_args(list(soulstone.exec), source="exec")
        elif soulstone.extra_args:
            cmd_inference = self._parser.infer_args(list(soulstone.extra_args), source="extra_args")

        env_inference = self._parser.infer_env(soulstone.env_vars)
        return self._parser.merge(primary=cmd_inference, secondary=env_inference)

    def _runtime_defaults(self, descriptor: LlamaCppDescriptor) -> dict[str, object]:
        """Translate llama.cpp planner defaults into shared generation-profile keys."""
        effective = descriptor.metadata.get("effective_defaults", {})
        if not isinstance(effective, Mapping):
            return {}
        effective_defaults = cast("Mapping[str, object]", effective)

        defaults: dict[str, object] = {}
        n_ctx = effective_defaults.get("n_ctx")
        if isinstance(n_ctx, int):
            defaults["max_context"] = n_ctx
        n_predict = effective_defaults.get("n_predict")
        if isinstance(n_predict, int):
            defaults["max_tokens"] = n_predict
        top_k = effective_defaults.get("top_k")
        if isinstance(top_k, int):
            defaults["top_k"] = top_k
        top_p = effective_defaults.get("top_p")
        if isinstance(top_p, int | float):
            defaults["top_p"] = float(top_p)
        temperature = effective_defaults.get("temperature")
        if isinstance(temperature, int | float):
            defaults["temperature"] = float(temperature)
        reasoning_format = effective_defaults.get("reasoning_format")
        if isinstance(reasoning_format, str):
            defaults["reasoning_format"] = reasoning_format
        return defaults

    def _fallback_states(
        self,
        *,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
        mode: str,
        health: str,
        reason: str | None,
    ) -> list[CapabilityState]:
        """Create conservative capability states when live probes are unavailable."""
        is_static = mode != "router"
        active_model_id = getattr(animator.connector, "default_model_id", None) if is_static else None
        loaded_ids = [active_model_id] if active_model_id is not None and is_static else []
        return [
            CapabilityState(
                capability_key=spec.key,
                is_static=is_static,
                is_active=is_static and animator.connector.link.up,
                is_available=True,
                warm=is_static and animator.connector.link.up,
                health=health,
                active_model_id=active_model_id,
                loaded_model_ids=loaded_ids,
                reason=reason,
                metadata=getattr(animator.connector, "metadata", {}),
            )
            for spec in specs
        ]

    def _normalize_active_model_id(self, lifecycle: object, specs: list[CapabilitySpec]) -> str | None:
        """Map lifecycle active model payloads back onto capability model ids."""
        active_model = getattr(lifecycle, "active_model", None)
        if not isinstance(active_model, str) or not active_model:
            loaded = getattr(lifecycle, "loaded_models", None)
            if isinstance(loaded, list) and loaded:
                loaded_candidates = cast("list[object]", loaded)
                for candidate in loaded_candidates:
                    if isinstance(candidate, str):
                        return candidate
            return None

        for spec in specs:
            metadata_path = spec.metadata.get("path")
            if isinstance(metadata_path, str) and metadata_path == active_model:
                return spec.model_id
            if isinstance(metadata_path, str):
                metadata_stem = metadata_path.rsplit("/", maxsplit=1)[-1].removesuffix(".gguf")
                if metadata_stem == spec.model_id:
                    return spec.model_id
            if active_model.rsplit("/", maxsplit=1)[-1].removesuffix(".gguf") == spec.model_id:
                return spec.model_id
        return active_model


__all__ = ["LlamaCppRuntimeAdapter"]
