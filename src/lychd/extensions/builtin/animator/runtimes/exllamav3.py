from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
)
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import ModelInfo, PortalConfig, SoulstoneConfig
from lychd.domain.animation.services.adapters.catalog import capability_specs_from_model_infos
from lychd.domain.animation.services.adapters.contracts import RuntimeAnimator, RuntimePlan
from lychd.domain.animation.services.adapters.runtimes.shared import require_runtime_soulstone
from lychd.domain.animation.services.adapters.surfaces import SoulstoneAnimator, local_link_default
from lychd.extensions.builtin.animator.exllamav3.connector import ExLlamaV3Connector
from lychd.extensions.builtin.animator.exllamav3.control_plane import (
    TabbyAPIControlPlane,
    TabbyAPIControlPlaneError,
)
from lychd.extensions.builtin.animator.soulstones import (
    ExLlamaV3SoulstoneConfig,
    exllamav3_runtime_model_name,
)

if TYPE_CHECKING:
    from lychd.domain.animation.lifecycle import AnimatorLifecycle

_REACHABLE_HEALTH = {"ok", "loading"}
_VESSEL_SERVICE = "lychd-vessel.service"
_TABBY_SHARED_MEMORY_BYTES = 8 * 1024**3


class ExLlamaV3RuntimeAdapter:
    """Dynamic ExLlamaV3 runtime backed by the official TabbyAPI server."""

    runtime: str = "exllamav3"

    def __init__(self, control_plane: TabbyAPIControlPlane | None = None) -> None:
        """Initialize with an injectable control plane for contract tests."""
        self._control_plane = control_plane or TabbyAPIControlPlane()

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Build the pinned private-pod TabbyAPI container envelope."""
        stone = self._narrow(soulstone)
        return RuntimePlan(
            env_overrides={
                "TABBY_NETWORK_HOST": "0.0.0.0",  # noqa: S104 - private pod listener
                "TABBY_NETWORK_PORT": str(stone.resolved_port),
                "TABBY_NETWORK_DISABLE_AUTH": "false",
                "TABBY_NETWORK_DISABLE_FETCH_REQUESTS": "true",
                "TABBY_NETWORK_SSE_PING_INTERVAL": "5",
                "TABBY_MODEL_MODEL_DIR": str(stone.model_dir),
                "TABBY_MODEL_MODEL_NAME": "",
                "TABBY_MODEL_INLINE_MODEL_LOADING": "false",
                "TABBY_MODEL_USE_DUMMY_MODELS": "false",
                "TABBY_MODEL_BACKEND": "exllamav3",
                # Tabby logs generated auth keys at INFO; keep credentials out of journald.
                "TABBY_LOG_LEVEL": "WARNING",
            },
            podman_args=[
                "--tmpfs=/app/logs:rw,nosuid,nodev,noexec,mode=1777",
            ],
            secrets=[f"{stone.auth_secret_name},target=/app/api_tokens.yml,mode=0444"],
            # Tabby detaches loads from HTTP clients. Binding its process to the
            # Vessel prevents a load from surviving loss of LychD's mutation fence.
            unit_binds_to=[_VESSEL_SERVICE],
            unit_after=[_VESSEL_SERVICE],
            pod_shared_memory_bytes=_TABBY_SHARED_MEMORY_BYTES,
        )

    def build_runtime(self, soulstone: SoulstoneConfig) -> RuntimeAnimator | None:
        """Build the OpenAI data plane with Tabby model-name metadata."""
        stone = self._narrow(soulstone)
        model_infos = self._model_infos(stone)
        runtime_names = {model.id: exllamav3_runtime_model_name(model) for model in stone.models}
        base_url = str(stone.base_url) if stone.base_url is not None else f"http://localhost:{stone.resolved_port}/v1"
        self._control_plane.register_runtime(base_url, stone.auth_secret_name)
        connector = ExLlamaV3Connector(
            link=local_link_default(runtime=self.runtime),
            base_url=base_url,
            model_infos=model_infos,
            default_model_id=stone.models[0].id,
            runtime_names=runtime_names,
            auth_secret_name=stone.auth_secret_name,
        )
        return SoulstoneAnimator(rune=stone, connector=connector)

    def build_capability_specs(self, animator: RuntimeAnimator) -> list[CapabilitySpec]:
        """Publish every declared TabbyAPI model as a dynamic capability."""
        soulstone = animator.rune
        stone = self._narrow(soulstone)
        connector = cast("ExLlamaV3Connector", animator.connector)
        return capability_specs_from_model_infos(
            stone,
            connector.model_infos,
            is_dynamic=True,
        )

    async def probe_capability_states(
        self,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
    ) -> list[CapabilityState]:
        """Project Tabby service/model truth into canonical dynamic phases."""
        connector = cast("ExLlamaV3Connector", animator.connector)
        checked_at = datetime.now(UTC)
        try:
            lifecycle = await self._control_plane.inspect_animator(animator)
        except TabbyAPIControlPlaneError as exc:
            phase = CapabilityPhase.COLD if exc.unreachable else CapabilityPhase.ERROR
            connector.set_link(Link(up=False, reason=str(exc)))
            return [
                CapabilityState(
                    capability_key=spec.key,
                    phase=phase,
                    health="down" if phase is CapabilityPhase.COLD else "error",
                    reason=str(exc),
                    checked_at=checked_at,
                )
                for spec in specs
            ]

        reachable = lifecycle.health in _REACHABLE_HEALTH
        connector.set_link(
            Link(
                up=reachable,
                reason=None if reachable else lifecycle.error or "tabbyapi_unhealthy",
            )
        )
        return [
            self._state_for_spec(
                connector=connector,
                lifecycle=lifecycle,
                spec=spec,
                checked_at=checked_at,
            )
            for spec in specs
        ]

    async def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> ActivationResult:
        """Ask TabbyAPI to load a declared model without blocking readiness polling."""
        connector = cast("ExLlamaV3Connector", animator.connector)
        runtime_name = connector.runtime_model_name(spec.model_id)
        if runtime_name is None:
            return ActivationResult(accepted=False, reason="undeclared TabbyAPI model")

        try:
            lifecycle = await self._control_plane.inspect_animator(animator)
            preflight = self._activation_preflight(lifecycle, runtime_name)
            if preflight is not None:
                return preflight

            accepted = await self._control_plane.load_model(connector.base_url, runtime_name)
        except TabbyAPIControlPlaneError as exc:
            if exc.ambiguous:
                return ActivationResult(accepted=True, reason=str(exc))
            return ActivationResult(accepted=False, reason=str(exc))
        if not accepted:
            return ActivationResult(
                accepted=False,
                reason="TabbyAPI rejected model load",
            )
        return ActivationResult(accepted=True)

    async def abandon_activation(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> None:
        """Cancel only the SSE observer; containment retains ambiguous server truth."""
        connector = cast("ExLlamaV3Connector", animator.connector)
        runtime_name = connector.runtime_model_name(spec.model_id)
        if runtime_name is not None:
            await self._control_plane.abandon_model_load(connector.base_url, runtime_name)

    def _activation_preflight(
        self,
        lifecycle: AnimatorLifecycle,
        runtime_name: str,
    ) -> ActivationResult | None:
        if lifecycle.health == "error":
            return ActivationResult(
                accepted=False,
                reason=lifecycle.error or "tabbyapi_unhealthy",
            )
        if lifecycle.active_model == runtime_name and lifecycle.health == "ok":
            return ActivationResult(accepted=True)
        if runtime_name not in lifecycle.available_models:
            return ActivationResult(
                accepted=False,
                reason=f"declared model directory '{runtime_name}' is absent from /v1/models",
            )
        if lifecycle.pending_model == runtime_name:
            return ActivationResult(accepted=True)
        return None

    def _state_for_spec(
        self,
        *,
        connector: ExLlamaV3Connector,
        lifecycle: AnimatorLifecycle,
        spec: CapabilitySpec,
        checked_at: datetime,
    ) -> CapabilityState:
        runtime_name = connector.runtime_model_name(spec.model_id)
        phase, reason = self._phase_and_reason(lifecycle, runtime_name)
        return CapabilityState(
            capability_key=spec.key,
            phase=phase,
            health=lifecycle.health,
            reason=reason,
            checked_at=checked_at,
        )

    def _phase_and_reason(
        self,
        lifecycle: AnimatorLifecycle,
        runtime_name: str | None,
    ) -> tuple[CapabilityPhase, str | None]:
        phase = CapabilityPhase.ACTIVATABLE
        reason: str | None = "model_not_loaded"
        if lifecycle.health == "error":
            phase = CapabilityPhase.ERROR
            reason = lifecycle.error or "tabbyapi_error"
        elif lifecycle.health not in _REACHABLE_HEALTH:
            phase, reason = CapabilityPhase.COLD, "runtime_unreachable"
        elif runtime_name is None:
            phase, reason = CapabilityPhase.ERROR, "undeclared_tabby_model"
        elif runtime_name not in lifecycle.available_models:
            phase, reason = CapabilityPhase.ERROR, "declared_model_directory_missing"
        elif lifecycle.active_model == runtime_name and lifecycle.health == "ok":
            phase, reason = CapabilityPhase.WARM, None
        elif lifecycle.pending_model == runtime_name and lifecycle.health == "loading":
            phase, reason = CapabilityPhase.WARMING, "model_loading"
        return phase, reason

    def _model_infos(self, stone: ExLlamaV3SoulstoneConfig) -> tuple[ModelInfo, ...]:
        return tuple(
            ModelInfo(
                id=model.id,
            )
            for model in stone.models
        )

    def _narrow(self, soulstone: SoulstoneConfig | PortalConfig) -> ExLlamaV3SoulstoneConfig:
        return require_runtime_soulstone(
            soulstone,
            expected_type=ExLlamaV3SoulstoneConfig,
            runtime=self.runtime,
        )


__all__ = ["ExLlamaV3RuntimeAdapter"]
