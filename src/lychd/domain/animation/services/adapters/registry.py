"""Registry-level runtime adapter dispatch and portal runtime construction."""

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
from lychd.domain.animation.schemas import (
    ConcurrencyIntent,
    GenerationProfile,
    ModelInfo,
    ModelSurface,
    PortalConfig,
    PortalModelConfig,
    SoulstoneConfig,
)
from lychd.domain.animation.services.adapters.catalog import synthesize_families
from lychd.domain.animation.services.adapters.contracts import (
    ActivationObserver,
    PortalRuntimeFactory,
    RuntimeAnimator,
    RuntimePlan,
    SoulstoneRuntimeAdapter,
)
from lychd.domain.animation.services.adapters.runtimes.generic import GenericRuntimeAdapter
from lychd.domain.animation.services.adapters.runtimes.shared import (
    probe_openai_compatible_link,
    transmute_single_soulstone_quadlet,
)
from lychd.domain.animation.services.adapters.surfaces import (
    GenericPortal,
    OpenAICompatibleConnector,
    PassiveConnector,
    portal_link_default,
)
from lychd.system.schemas import QuadletContainer

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lychd.domain.animation.schemas import ModelCapabilityHints


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
        """Initialize active runtime adapters plus generic fallback.

        Portal factories are injected by the composition root (the OpenAI factory
        is an extension, no longer a domain-side default); the passive fallback
        still applies when no factory matches a provider.
        """
        self._fallback: SoulstoneRuntimeAdapter = GenericRuntimeAdapter()
        self._adapters = list(adapters or [])
        self._portal_factories: list[PortalRuntimeFactory] = list(portal_factories or [])

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
            return await self._probe_portal_capability_states(animator, specs)

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

    async def abandon_activation(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> None:
        """Stop adapter-owned observation after canonical warm convergence ends."""
        rune = animator.rune
        if isinstance(rune, PortalConfig):
            return
        adapter = self.adapter_for(rune)
        if isinstance(adapter, ActivationObserver):
            await adapter.abandon_activation(animator, spec)

    def _build_portal_runtime(self, portal: PortalConfig) -> RuntimeAnimator:
        """Resolve portal runtime by custom factories, then passive fallback."""
        for factory in self._portal_factories:
            runtime = factory(portal)
            if runtime is not None:
                return runtime

        return self._build_passive_portal(portal)

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
        """Synthesize capability specs from a Portal's declared ``[[models]]``.

        Zero declared models ⇒ zero specs (reachable but unadvertised). Families
        are synthesized under the two-axis law (probe facts are absent at synthesis).
        """
        _ = runtime
        specs: list[CapabilitySpec] = []
        for model in portal.models:
            hints = model.capabilities
            info = self._info_from_portal_model(portal, model, hints)
            generation = GenerationProfile().overlay(portal.generation).overlay(model.generation)
            specs.extend(
                CapabilitySpec(
                    key=f"{portal.name}:{family}:{model.id}",
                    animator_name=portal.name,
                    runtime=f"portal:{portal.provider_name}",
                    source_kind=SourceKind.PORTAL,
                    family=family,
                    model_id=model.id,
                    surface=info.surface,
                    max_context=info.max_context,
                    modalities_in=list(info.modalities_in),
                    modalities_out=list(info.modalities_out),
                    supports_tools=info.supports_tools,
                    supports_streaming=info.supports_streaming,
                    generation_profile=generation,
                    is_dynamic=False,
                    # A Portal is remote: LychD does not own its lifecycle (ADR-22).
                    concurrency=ConcurrencyIntent(dedicated=False),
                    metadata={"provider_name": portal.provider_name},
                )
                for family in synthesize_families(info, hints, None)
            )
        return specs

    def _info_from_portal_model(
        self,
        portal: PortalConfig,
        model: PortalModelConfig,
        hints: ModelCapabilityHints | None,
    ) -> ModelInfo:
        """Build a ``ModelInfo`` from a Portal model declaration + optional hints."""
        _ = portal
        return ModelInfo(
            id=model.id,
            description=model.description,
            surface=(hints.surface if hints is not None else None) or ModelSurface.CHAT,
            modalities_in=list((hints.modalities_in if hints is not None else None) or ["text"]),
            modalities_out=list((hints.modalities_out if hints is not None else None) or ["text"]),
            supports_tools=hints.supports_tools if hints is not None else None,
            supports_streaming=(hints.supports_streaming if hints is not None else None) or True,
        )

    async def _probe_portal_capability_states(
        self, animator: RuntimeAnimator, specs: list[CapabilitySpec]
    ) -> list[CapabilityState]:
        """Project portal readiness into phase-canonical states (opt-in live probe).

        With ``rune.probe`` true and an OpenAI-compatible connector, run a live
        reachability probe and push the refreshed link (a legitimate ``Link``
        writer). Otherwise the connector's passive/static link is read as-is.
        """
        connector = animator.connector
        rune = animator.rune
        if isinstance(rune, PortalConfig) and getattr(rune, "probe", False) and hasattr(connector, "set_link"):
            openai_connector = cast("OpenAICompatibleConnector", connector)
            link = await probe_openai_compatible_link(openai_connector)
            openai_connector.set_link(link)

        link = connector.link
        up = link.up
        health = "ok" if up else "down"
        checked_at = datetime.now(UTC)
        return [
            CapabilityState(
                capability_key=spec.key,
                is_dynamic=False,
                phase=CapabilityPhase.WARM if up else CapabilityPhase.COLD,
                health=health,
                active_model_id=spec.model_id if up else None,
                loaded_model_ids=[spec.model_id] if up else [],
                reason=None if up else link.reason,
                checked_at=checked_at,
                metadata=cast("dict[str, object]", getattr(connector, "metadata", {})),
            )
            for spec in specs
        ]


__all__ = ["RuntimeAdapterRegistry"]
