from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    SourceKind,
)
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import CapabilityFamily, GenerationProfile, ModelInfo, SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import (
    capability_specs_from_model_infos,
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
from lychd.extensions.builtin.animator.llamacpp.embedding_profile import (
    PROFILE,
    profile_command,
    require_profile_config,
)
from lychd.extensions.builtin.animator.llamacpp.parser_cli import LlamaCppCliInferenceParser
from lychd.extensions.builtin.animator.llamacpp.parser_models import LlamaCppRuntimeInference
from lychd.extensions.builtin.animator.llamacpp.runtime import LlamaCppDescriptor, LlamaCppRuntimePlanner
from lychd.extensions.builtin.animator.soulstones import LlamaCppSoulstoneConfig
from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppMode

if TYPE_CHECKING:
    from lychd.domain.animation.lifecycle import AnimatorLifecycle

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
        if stone.embedding_profile is not None:
            require_profile_config(stone)
            connector = LlamacppConnector(
                link=local_link_default(runtime=self.runtime),
                base_url=str(stone.base_url) if stone.base_url is not None else f"http://127.0.0.1:{stone.port}/v1",
                model_infos=[ModelInfo(id=PROFILE.model_id, modalities_in=("text",), supports_tools=False)],
                default_model_id=PROFILE.model_id,
                mode="single",
                router_query_model_id=None,
                generation_defaults=GenerationProfile(),
                embedding_profile=PROFILE,
            )
            return SoulstoneAnimator(rune=stone, connector=connector)
        descriptor = self._describe_runtime(stone)
        model_infos = model_infos_from_soulstone(stone, discovered=descriptor.model_infos)
        base_url = str(stone.base_url) if stone.base_url is not None else f"http://localhost:{stone.port}/v1"
        connector = LlamacppConnector(
            link=local_link_default(runtime=self.runtime),
            base_url=base_url,
            model_infos=model_infos,
            default_model_id=model_infos[0].id if model_infos else None,
            mode=descriptor.mode,
            schema_without_tools=stone.structured_output == "json-schema",
            router_query_model_id=descriptor.router_query_model_id,
            generation_defaults=GenerationProfile.model_validate(self._runtime_defaults(descriptor)),
        )
        return SoulstoneAnimator(rune=stone, connector=connector)

    def build_capability_specs(self, animator: RuntimeAnimator) -> list[CapabilitySpec]:
        """Synthesize specs from the catalogue and defaults captured at construction."""
        soulstone = animator.rune
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=LlamaCppSoulstoneConfig,
            runtime=self.runtime,
        )
        connector = cast("LlamacppConnector", animator.connector)
        if stone.embedding_profile is not None:
            return [
                CapabilitySpec(
                    key=f"{stone.name}:embedding:{PROFILE.model_id}",
                    animator_name=stone.name,
                    runtime=self.runtime,
                    source_kind=SourceKind.SOULSTONE,
                    family=CapabilityFamily.EMBEDDING,
                    model_id=PROFILE.model_id,
                    max_context=512,
                    modalities_in=("text",),
                    supports_tools=False,
                    embedding_profile=PROFILE,
                    concurrency=stone.concurrency,
                )
            ]
        return capability_specs_from_model_infos(
            stone,
            connector.model_infos,
            runtime_defaults=connector.generation_defaults.model_dump(exclude_none=True),
            is_dynamic=connector.mode == "router",
        )

    async def probe_capability_states(
        self,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
    ) -> list[CapabilityState]:
        """Map live llama.cpp control-plane data into phase-canonical states.

        Phase mapping: single ``/health`` 503-loading → WARMING, healthy plus
        an exact inventory match → WARM; router ``/models`` status →
        ACTIVATABLE/WARMING/WARM; a missing declared model → ERROR; unreachable → COLD;
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
        health_error = lifecycle.error
        connector.set_link(
            Link(
                up=health in _REACHABLE_HEALTH,
                reason=None
                if health in _REACHABLE_HEALTH
                else (str(health_error) if health_error else "runtime_unreachable"),
            )
        )

        return [
            self._state_for_spec(
                spec=spec,
                mode=mode,
                lifecycle=lifecycle,
                checked_at=checked_at,
            )
            for spec in specs
        ]

    def _state_for_spec(
        self,
        *,
        spec: CapabilitySpec,
        mode: str,
        lifecycle: AnimatorLifecycle,
        checked_at: datetime,
    ) -> CapabilityState:
        phase = self._phase_for(
            mode=mode,
            model_id=spec.model_id,
            lifecycle=lifecycle,
        )
        reason: str | None = None
        if phase is CapabilityPhase.ERROR:
            reason = lifecycle.error or (
                f"declared model {spec.model_id!r} is absent from /models"
                if lifecycle.health == "ok"
                else "runtime_error"
            )
        elif phase is CapabilityPhase.ACTIVATABLE:
            reason = "model_not_loaded"
        elif phase is CapabilityPhase.COLD:
            reason = "runtime_unreachable"
        elif phase is CapabilityPhase.UNKNOWN:
            reason = "router model has no admitted load state"
        return CapabilityState(
            capability_key=spec.key,
            phase=phase,
            health=lifecycle.health,
            reason=reason,
            checked_at=checked_at,
        )

    def _phase_for(
        self,
        *,
        mode: str,
        model_id: str,
        lifecycle: AnimatorLifecycle,
    ) -> CapabilityPhase:
        health = lifecycle.health
        if health == "error":
            return CapabilityPhase.ERROR
        if mode == "router":
            if health not in _REACHABLE_HEALTH and not lifecycle.supports_router:
                phase = CapabilityPhase.COLD
            elif model_id not in lifecycle.available_models:
                phase = CapabilityPhase.ERROR
            elif model_id in lifecycle.loading_models:
                phase = CapabilityPhase.WARMING
            elif model_id in lifecycle.loaded_models and health == "ok":
                phase = CapabilityPhase.WARM
            elif model_id in lifecycle.unloaded_models:
                phase = CapabilityPhase.ACTIVATABLE
            else:
                phase = CapabilityPhase.UNKNOWN
            return phase
        if health == "loading":
            return CapabilityPhase.WARMING
        if health == "ok":
            return CapabilityPhase.WARM if model_id in lifecycle.loaded_models else CapabilityPhase.ERROR
        return CapabilityPhase.COLD

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
            if spec.model_id in lifecycle.loaded_models or spec.model_id in lifecycle.loading_models:
                return ActivationResult(accepted=True)
            if spec.model_id not in lifecycle.unloaded_models:
                return ActivationResult(accepted=False, reason="router model has no admitted load state")
            accepted = await self._control_plane.load_model(connector.base_url, spec.model_id)
            return ActivationResult(accepted=accepted, reason=None if accepted else "router rejected model load")
        except LlamaCppControlPlaneError as exc:
            return ActivationResult(accepted=False, reason=str(exc))

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Plan llama.cpp command args from passthrough or managed fields."""
        stone = require_runtime_soulstone(
            soulstone,
            expected_type=LlamaCppSoulstoneConfig,
            runtime=self.runtime,
        )

        command, _ = self._planned_inference(stone)
        return RuntimePlan(exec_args=command, env_overrides={})

    def _describe_runtime(self, soulstone: LlamaCppSoulstoneConfig) -> LlamaCppDescriptor:
        """Describe the admitted final command and its projected environment."""
        _, inferred = self._planned_inference(soulstone)
        return self._planner.describe_runtime(
            soulstone=soulstone,
            inferred=inferred,
            mode=inferred.mode or "router",
        )

    def _planned_inference(self, soulstone: LlamaCppSoulstoneConfig) -> tuple[list[str], LlamaCppRuntimeInference]:
        """Keep AUTO planning precedence while classifying the actual emitted inputs."""
        if soulstone.embedding_profile is not None:
            command = profile_command(soulstone)
            return command, self._parser.infer_args(command)
        command = list(soulstone.exec or soulstone.extra_args)
        command_inference = self._parser.infer_args(command)
        env_inference = self._parser.infer_env(soulstone.inference_env())
        inferred = self._parser.merge(primary=command_inference, secondary=env_inference)
        if not soulstone.exec:
            # AUTO historically lets a router CLI/env fragment omit the typed
            # model fallback. That planning choice does not erase a main source
            # in the other fragment from the final process environment.
            planning_mode = soulstone.resolved_mode(command_inference.mode or env_inference.mode)
            command = self._planner.plan_exec_args(
                soulstone=soulstone,
                inferred=inferred,
                mode=planning_mode,
                listen_host=LISTEN_HOST,
            )
            inferred = self._parser.merge(primary=self._parser.infer_args(command), secondary=env_inference)
        actual_mode = inferred.mode or "router"
        if soulstone.startup_mode not in {LlamaCppMode.AUTO, actual_mode}:
            msg = "The llama.cpp final command contradicts the forced startup mode."
            raise ValueError(msg)
        return command, inferred

    def _runtime_defaults(self, descriptor: LlamaCppDescriptor) -> dict[str, object]:
        """Translate llama.cpp planner defaults into shared generation-profile keys."""
        defaults: dict[str, object] = {}
        request_context = self._request_context(descriptor)
        if request_context is not None:
            defaults["max_context"] = request_context
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

    def _request_context(self, descriptor: LlamaCppDescriptor) -> int | None:
        """Derive a conservative configured bound only from known positive slot inputs."""
        n_ctx = descriptor.generation_defaults.get("n_ctx")
        n_parallel = descriptor.generation_defaults.get("n_parallel")
        if not isinstance(n_ctx, int) or not isinstance(n_parallel, int) or n_ctx <= 0 or n_parallel <= 0:
            return None
        # --ctx-size allocates total context. A per-slot share is safe for
        # both split and unified KV layouts, subject to an explicit slot cap.
        request_context = n_ctx // n_parallel
        slot_cap = descriptor.generation_defaults.get("n_ctx_per_slot")
        if slot_cap is not None:
            if not isinstance(slot_cap, int) or slot_cap <= 0:
                return None
            request_context = min(request_context, slot_cap)
        return request_context if request_context > 0 else None


__all__ = ["LlamaCppRuntimeAdapter"]
