from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar, cast

from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityLifecycle,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
)
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import capability_specs_from_model_infos
from lychd.domain.animation.services.adapters.contracts import (
    LISTEN_HOST,
    AnimatorControlPlane,
    RuntimeAnimator,
    RuntimePlan,
)
from lychd.domain.animation.services.adapters.runtimes.shared import require_runtime_soulstone
from lychd.domain.animation.services.adapters.surfaces import local_link_default
from lychd.extensions.builtin.animator.llamacpp.connector import LlamacppConnector, LlamacppStone
from lychd.extensions.builtin.animator.llamacpp.control_plane import LlamaCppControlPlane, LlamaCppControlPlaneError
from lychd.extensions.builtin.animator.llamacpp.parser import LlamaCppCommandParser, LlamaCppRuntimeInference
from lychd.extensions.builtin.animator.llamacpp.runtime import LlamaCppDescriptor, LlamaCppRuntimePlanner
from lychd.extensions.builtin.animator.soulstones import LlamaCppSoulstoneConfig

if TYPE_CHECKING:
    from lychd.domain.animation.lifecycle import AnimatorLifecycle
    from lychd.system.schemas import QuadletContainer

_REACHABLE_HEALTH = {"ok", "loading"}


class LlamaCppRuntimeAdapter:
    """llama.cpp planner and runtime animator factory."""

    runtime: ClassVar[str] = "llamacpp"

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

    def control_plane(self, animator: RuntimeAnimator) -> AnimatorControlPlane | None:
        """Expose the llama.cpp lifecycle control plane for llama.cpp animators."""
        if getattr(animator.connector, "kind", None) != "llamacpp":
            return None
        return self._control_plane

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
            lifecycle=CapabilityLifecycle.DYNAMIC if descriptor.mode == "router" else CapabilityLifecycle.STATIC,
        )

    async def probe_capability_states(
        self,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
    ) -> list[CapabilityState]:
        """Map live llama.cpp control-plane data into phase-canonical states.

        Phase mapping (spec §2): single ``/health`` 503-loading → WARMING, 200 →
        WARM; router ``/models`` status → ACTIVATABLE/WARM; unreachable → COLD;
        control-plane exception → ERROR with reason.
        """
        connector = cast("LlamacppConnector", animator.connector)
        mode = getattr(connector, "mode", "single")
        lifecycle_mode = CapabilityLifecycle.DYNAMIC if mode == "router" else CapabilityLifecycle.STATIC
        checked_at = datetime.now(UTC)

        try:
            lifecycle = await self._control_plane.inspect_animator(animator)
        except LlamaCppControlPlaneError as exc:
            connector.set_link(Link(up=False, activatable=True, reason=str(exc), checked_at=checked_at))
            return [
                CapabilityState(
                    capability_key=spec.key,
                    lifecycle=lifecycle_mode,
                    phase=CapabilityPhase.ERROR,
                    health="error",
                    reason=str(exc),
                    checked_at=checked_at,
                )
                for spec in specs
            ]

        health = lifecycle.health
        reachable = health in _REACHABLE_HEALTH or lifecycle.supports_router
        health_error = lifecycle.raw.get("health_error")
        connector.set_link(
            Link(
                up=health in _REACHABLE_HEALTH,
                activatable=True,
                reason=None
                if health in _REACHABLE_HEALTH
                else (str(health_error) if health_error else "runtime_unreachable"),
                checked_at=checked_at,
            )
        )

        loaded_ids = list(lifecycle.loaded_models)
        active_model = self._normalize_active_model_id(lifecycle, specs)
        return [
            self._state_for_spec(
                spec=spec,
                mode=mode,
                lifecycle_mode=lifecycle_mode,
                health=health,
                reachable=reachable,
                loaded_ids=loaded_ids,
                active_model=active_model,
                raw=dict(lifecycle.raw),
                checked_at=checked_at,
            )
            for spec in specs
        ]

    def _state_for_spec(
        self,
        *,
        spec: CapabilitySpec,
        mode: str,
        lifecycle_mode: CapabilityLifecycle,
        health: str,
        reachable: bool,
        loaded_ids: list[str],
        active_model: str | None,
        raw: dict[str, object],
        checked_at: datetime,
    ) -> CapabilityState:
        phase = self._phase_for(
            mode=mode,
            health=health,
            reachable=reachable,
            model_id=spec.model_id,
            loaded_ids=loaded_ids,
        )
        reason: str | None = None
        if phase is CapabilityPhase.ERROR:
            reason = str(raw.get("health_error") or "runtime_error")
        elif phase is CapabilityPhase.ACTIVATABLE:
            reason = "model_not_loaded"
        elif phase is CapabilityPhase.COLD:
            reason = "runtime_unreachable"
        return CapabilityState(
            capability_key=spec.key,
            lifecycle=lifecycle_mode,
            phase=phase,
            health=health,
            active_model_id=active_model,
            loaded_model_ids=loaded_ids,
            reason=reason,
            checked_at=checked_at,
            metadata=raw,
        )

    def _phase_for(
        self,
        *,
        mode: str,
        health: str,
        reachable: bool,
        model_id: str,
        loaded_ids: list[str],
    ) -> CapabilityPhase:
        if health == "error":
            return CapabilityPhase.ERROR
        if health == "loading":
            return CapabilityPhase.WARMING
        if mode == "router":
            if not reachable:
                return CapabilityPhase.COLD
            loaded = model_id in loaded_ids and health == "ok"
            return CapabilityPhase.WARM if loaded else CapabilityPhase.ACTIVATABLE
        # single mode is FIXED: reachable health "ok" ⇒ WARM, else COLD.
        return CapabilityPhase.WARM if health == "ok" else CapabilityPhase.COLD

    async def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> ActivationResult:
        """Perform router-native model activation when the runtime supports it."""
        connector = animator.connector
        if getattr(connector, "mode", "single") != "router":
            return ActivationResult(
                accepted=False,
                phase=CapabilityPhase.WARM if connector.link.up else CapabilityPhase.COLD,
                reason="fixed capability; lifecycle owned by unit",
            )

        try:
            lifecycle = await self._control_plane.inspect_animator(animator)
            if spec.model_id not in lifecycle.available_models:
                return ActivationResult(
                    accepted=False,
                    phase=CapabilityPhase.COLD,
                    reason="model not in /models",
                )
            await self._control_plane.load_model(connector.base_url, spec.model_id)
        except LlamaCppControlPlaneError as exc:
            return ActivationResult(accepted=False, phase=CapabilityPhase.ERROR, reason=str(exc))
        return ActivationResult(accepted=True, phase=CapabilityPhase.WARMING)

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

    def _normalize_active_model_id(self, lifecycle: AnimatorLifecycle, specs: list[CapabilitySpec]) -> str | None:
        """Map lifecycle active model payloads back onto capability model ids."""
        active_model = lifecycle.active_model
        if not isinstance(active_model, str) or not active_model:
            return lifecycle.loaded_models[0] if lifecycle.loaded_models else None

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
