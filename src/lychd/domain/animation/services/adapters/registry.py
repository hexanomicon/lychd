"""Registry-level runtime adapter dispatch and portal runtime construction."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityLifecycle,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
)
from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig
from lychd.domain.animation.services.adapters.contracts import RuntimeAnimator, RuntimePlan, SoulstoneRuntimeAdapter
from lychd.domain.animation.services.adapters.runtimes.generic import GenericRuntimeAdapter
from lychd.domain.animation.services.adapters.runtimes.shared import transmute_single_soulstone_quadlet
from lychd.domain.animation.services.adapters.surfaces import (
    GenericPortal,
    OpenAICompatibleConnector,
    OpenAIPortal,
    PassiveConnector,
    portal_link_default,
)
from lychd.system.schemas import QuadletContainer

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

type PortalRuntimeFactory = Callable[[PortalConfig], RuntimeAnimator | None]

_OPENAI_COMPATIBLE_PROVIDERS = {
    "openai",
    "openai_compatible",
    "openai-compatible",
    "google-gemini",
    "openrouter",
    "ollama",
    "litellm",
}


class RuntimeAdapterRegistry:
    """Runtime switchboard for command planning and runtime-handle construction.

    Soulstones are dispatched by runtime name to registered adapters.
    Portals are dispatched by registered portal factories, in order.
    """

    def __init__(
        self,
        adapters: Sequence[SoulstoneRuntimeAdapter] | None = None,
        *,
        portal_factories: Sequence[PortalRuntimeFactory] | None = None,
    ) -> None:
        """Initialize active runtime adapters plus generic fallback."""
        self._fallback: SoulstoneRuntimeAdapter = GenericRuntimeAdapter()
        self._adapters = list(adapters or [])
        self._portal_factories: list[PortalRuntimeFactory] = list(portal_factories or [self._build_openai_portal])

    def register_portal_factory(self, factory: PortalRuntimeFactory) -> None:
        """Register an additional portal runtime factory."""
        self._portal_factories.append(factory)

    def adapter_for(self, soulstone: SoulstoneConfig) -> SoulstoneRuntimeAdapter:
        """Return the first runtime adapter that supports the Soulstone runtime."""
        runtime = soulstone.runtime_name
        for adapter in self._adapters:
            if adapter.supports(runtime):
                return adapter
        return self._fallback

    def adapter_for_animator(self, animator: RuntimeAnimator) -> SoulstoneRuntimeAdapter | None:
        """Return the runtime adapter backing a resolved soulstone animator."""
        rune = animator.rune
        if isinstance(rune, PortalConfig):
            return None
        return self.adapter_for(rune)

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Build a host-facing runtime plan for a Soulstone."""
        adapter = self.adapter_for(soulstone)
        return adapter.plan(soulstone)

    def build_runtime(
        self,
        rune: SoulstoneConfig | PortalConfig,
        quadlet: QuadletContainer | None = None,
    ) -> RuntimeAnimator | None:
        """Build runtime handle for Soulstone/Portal rune declarations."""
        if isinstance(rune, PortalConfig):
            return self._build_portal_runtime(rune)

        adapter = self.adapter_for(rune)
        resolved_quadlet = quadlet or transmute_single_soulstone_quadlet(rune, runtime_planner=self)
        return adapter.build_runtime(rune, resolved_quadlet)

    def runtime_factory(
        self,
        rune: SoulstoneConfig | PortalConfig,
        quadlet: QuadletContainer | None = None,
    ) -> RuntimeAnimator | None:
        """Adapter-compatible callable used by ``AnimatorRegistry`` factories."""
        return self.build_runtime(rune, quadlet=quadlet)

    def build_capability_specs(
        self,
        rune: SoulstoneConfig | PortalConfig,
        animator: RuntimeAnimator | None = None,
    ) -> list[CapabilitySpec]:
        """Build capability specs for either a Soulstone Rune or Portal Rune."""
        if isinstance(rune, PortalConfig):
            runtime = animator or self._build_portal_runtime(rune)
            return self._build_portal_capability_specs(rune, runtime)

        adapter = self.adapter_for(rune)
        return adapter.build_capability_specs(rune)

    async def probe_capability_states(
        self,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
    ) -> list[CapabilityState]:
        """Probe capability states for either a soulstone or portal runtime."""
        rune = animator.rune
        if isinstance(rune, PortalConfig):
            return self._probe_portal_capability_states(animator, specs)

        adapter = self.adapter_for(rune)
        return await adapter.probe_capability_states(animator, specs)

    async def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> ActivationResult:
        """Delegate runtime-specific capability activation when supported."""
        rune = animator.rune
        if isinstance(rune, PortalConfig):
            return ActivationResult(
                accepted=False,
                phase=CapabilityPhase.WARM if animator.connector.link.up else CapabilityPhase.COLD,
                reason="fixed capability; lifecycle owned by unit",
            )

        adapter = self.adapter_for(rune)
        return await adapter.activate_capability(animator, spec)

    def _build_portal_runtime(self, portal: PortalConfig) -> RuntimeAnimator:
        """Resolve portal runtime by custom factories, then passive fallback."""
        for factory in self._portal_factories:
            runtime = factory(portal)
            if runtime is not None:
                return runtime

        return self._build_passive_portal(portal)

    def _build_openai_portal(self, portal: PortalConfig) -> RuntimeAnimator | None:
        """Build OpenAI-compatible portal runtime for known provider aliases."""
        base_url = str(portal.base_url) if portal.base_url is not None else ""
        provider = portal.provider_name.strip().lower()

        link = portal_link_default(base_url=base_url)

        if provider in _OPENAI_COMPATIBLE_PROVIDERS:
            connector = OpenAICompatibleConnector(
                kind=f"portal:{provider}",
                link=link,
                base_url=base_url,
                api_key_secret_name=portal.api_key_secret_name,
                metadata={
                    "provider_name": portal.provider_name,
                    "base_url": base_url,
                },
            )
            return OpenAIPortal(rune=portal, connector=connector)

        return None

    def _build_passive_portal(self, portal: PortalConfig) -> RuntimeAnimator:
        """Build readiness-only portal runtime when no factory matches provider."""
        provider = portal.provider_name.strip().lower()
        base_url = str(portal.base_url) if portal.base_url is not None else ""
        link = portal_link_default(base_url=base_url)
        connector = PassiveConnector(
            kind=f"portal:{provider}",
            link=link,
            base_url=base_url,
        )
        return GenericPortal(rune=portal, connector=connector)

    def _build_portal_capability_specs(self, portal: PortalConfig, runtime: RuntimeAnimator) -> list[CapabilitySpec]:
        """Synthesize capability specs for a portal runtime."""
        _ = portal
        _ = runtime
        return []

    def _probe_portal_capability_states(
        self, animator: RuntimeAnimator, specs: list[CapabilitySpec]
    ) -> list[CapabilityState]:
        """Project passive portal readiness into phase-canonical capability states."""
        link = animator.connector.link
        up = link.up
        health = "ok" if up else "down"
        checked_at = datetime.now(UTC)
        return [
            CapabilityState(
                capability_key=spec.key,
                lifecycle=CapabilityLifecycle.STATIC,
                phase=CapabilityPhase.WARM if up else CapabilityPhase.COLD,
                health=health,
                active_model_id=spec.model_id if up else None,
                loaded_model_ids=[spec.model_id] if up else [],
                reason=None if up else link.reason,
                checked_at=checked_at,
                metadata=cast("dict[str, object]", getattr(animator.connector, "metadata", {})),
            )
            for spec in specs
        ]


__all__ = ["RuntimeAdapterRegistry"]
