from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
)
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import (
    capability_specs_from_model_infos,
    default_model_id_for_soulstone,
    model_infos_from_soulstone,
)
from lychd.domain.animation.services.adapters.contracts import (
    LISTEN_HOST,
    RuntimeAnimator,
    RuntimePlan,
)
from lychd.domain.animation.services.adapters.runtimes.shared import require_runtime_soulstone
from lychd.domain.animation.services.adapters.surfaces import SoulstoneAnimator, local_link_default
from lychd.extensions.builtin.animator.llamacpp.connector import LlamacppConnector
from lychd.extensions.builtin.animator.llamacpp.control_plane import LlamaCppControlPlane, LlamaCppControlPlaneError
from lychd.extensions.builtin.animator.llamacpp.parser_cli import LlamaCppCliInferenceParser
from lychd.extensions.builtin.animator.llamacpp.parser_models import LlamaCppRuntimeInference
from lychd.extensions.builtin.animator.llamacpp.runtime import LlamaCppDescriptor, LlamaCppRuntimePlanner
from lychd.extensions.builtin.animator.soulstones import LlamaCppSoulstoneConfig

_REACHABLE_HEALTH = {"ok", "loading"}


class LlamaCppRuntimeAdapter:
    """llama.cpp planner and runtime animator factory."""

    runtime: str = "llamacpp"

    def __init__(
        self,
        control_plane: LlamaCppControlPlane | None = None,
    ) -> None:
        """Initialize the runtime adapter and its control plane."""
        self._parser = LlamaCppCliInferenceParser()
        self._planner = LlamaCppRuntimePlanner()
        self._control_plane = control_plane or LlamaCppControlPlane()

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None:
        """Build llama.cpp runtime handle with control-plane metadata attached."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=LlamaCppSoulstoneConfig,
            runtime=self.runtime,
        )
        descriptor = self._describe_runtime(stone)
        model_infos = model_infos_from_soulstone(stone, discovered=descriptor.model_infos)
        base_url = str(stone.base_url) if stone.base_url is not None else f"http://localhost:{stone.port}/v1"
        connector = LlamacppConnector(
            link=local_link_default(runtime=self.runtime),
            base_url=base_url,
            model_infos=model_infos,
            default_model_id=default_model_id_for_soulstone(stone, model_infos),
            mode=descriptor.mode,
            router_query_model_id=descriptor.router_query_model_id,
        )
        return SoulstoneAnimator(rune=stone, connector=connector)

    def build_capability_specs(self, soulstone: SoulstoneConfig) -> list[CapabilitySpec]:
        """Synthesize capability specs for llama.cpp single or router runtimes."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=LlamaCppSoulstoneConfig,
            runtime=self.runtime,
        )
        descriptor = self._describe_runtime(stone)
        hints_by_id = {model.id: model.capabilities for model in stone.models if model.capabilities is not None}
        # Operator-declared [[models]] ARE the catalog when present (matched, no
        # spurious name-fallback spec); otherwise fall back to runtime discovery.
        model_infos = model_infos_from_soulstone(stone, discovered=descriptor.model_infos)
        return capability_specs_from_model_infos(
            stone,
            model_infos,
            runtime_defaults=self._runtime_defaults(descriptor),
            is_dynamic=descriptor.mode == "router",
            hints_by_id=hints_by_id,
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
        checked_at = datetime.now(UTC)

        try:
            lifecycle = await self._control_plane.inspect_animator(animator)
        except LlamaCppControlPlaneError as exc:
            connector.set_link(Link(up=False, reason=str(exc)))
            return [
                CapabilityState(
                    capability_key=spec.key,
                    phase=CapabilityPhase.ERROR,
                    health="error",
                    reason=str(exc),
                    checked_at=checked_at,
                )
                for spec in specs
            ]

        health = lifecycle.health
        reachable = health in _REACHABLE_HEALTH or lifecycle.supports_router
        health_error = lifecycle.error
        connector.set_link(
            Link(
                up=health in _REACHABLE_HEALTH,
                reason=None
                if health in _REACHABLE_HEALTH
                else (str(health_error) if health_error else "runtime_unreachable"),
            )
        )

        loaded_ids = list(lifecycle.loaded_models)
        return [
            self._state_for_spec(
                spec=spec,
                mode=mode,
                health=health,
                reachable=reachable,
                loaded_ids=loaded_ids,
                health_error=str(health_error) if health_error else None,
                checked_at=checked_at,
            )
            for spec in specs
        ]

    def _state_for_spec(
        self,
        *,
        spec: CapabilitySpec,
        mode: str,
        health: str,
        reachable: bool,
        loaded_ids: list[str],
        health_error: str | None,
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
            reason = health_error or "runtime_error"
        elif phase is CapabilityPhase.ACTIVATABLE:
            reason = "model_not_loaded"
        elif phase is CapabilityPhase.COLD:
            reason = "runtime_unreachable"
        return CapabilityState(
            capability_key=spec.key,
            phase=phase,
            health=health,
            reason=reason,
            checked_at=checked_at,
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
                reason="fixed capability; lifecycle owned by unit",
            )

        try:
            lifecycle = await self._control_plane.inspect_animator(animator)
            if spec.model_id not in lifecycle.available_models:
                return ActivationResult(
                    accepted=False,
                    reason="model not in /models",
                )
            accepted = await self._control_plane.load_model(connector.base_url, spec.model_id)
            if not accepted:
                return ActivationResult(
                    accepted=False,
                    reason="router rejected model load",
                )
        except LlamaCppControlPlaneError as exc:
            return ActivationResult(accepted=False, reason=str(exc))
        return ActivationResult(accepted=True)

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
        )

    def _infer_runtime(self, soulstone: LlamaCppSoulstoneConfig) -> LlamaCppRuntimeInference:
        """Infer runtime metadata from command/extra args and env vars."""
        cmd_inference = LlamaCppRuntimeInference()
        if soulstone.exec:
            cmd_inference = self._parser.infer_args(list(soulstone.exec))
        elif soulstone.extra_args:
            cmd_inference = self._parser.infer_args(list(soulstone.extra_args))

        env_inference = self._parser.infer_env(soulstone.env_vars)
        return self._parser.merge(primary=cmd_inference, secondary=env_inference)

    def _runtime_defaults(self, descriptor: LlamaCppDescriptor) -> dict[str, object]:
        """Translate llama.cpp planner defaults into shared generation-profile keys."""
        defaults: dict[str, object] = {}
        n_ctx = descriptor.generation_defaults.get("n_ctx")
        if isinstance(n_ctx, int):
            defaults["max_context"] = n_ctx
        n_predict = descriptor.generation_defaults.get("n_predict")
        if isinstance(n_predict, int):
            defaults["max_tokens"] = n_predict
        top_p = descriptor.generation_defaults.get("top_p")
        if isinstance(top_p, int | float):
            defaults["top_p"] = float(top_p)
        temperature = descriptor.generation_defaults.get("temperature")
        if isinstance(temperature, int | float):
            defaults["temperature"] = float(temperature)
        return defaults


__all__ = ["LlamaCppRuntimeAdapter"]
