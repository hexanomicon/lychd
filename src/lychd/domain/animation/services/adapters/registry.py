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
    PortalConfig,
    SoulstoneConfig,
)
from lychd.domain.animation.services.adapters.catalog import model_info_from_portal_model, synthesize_families
from lychd.domain.animation.services.adapters.contracts import (
    ActivationObserver,
    PortalDefinition,
    RuntimeAnimator,
    RuntimePlan,
    SoulstoneRuntimeAdapter,
)
from lychd.domain.animation.services.adapters.runtimes.generic import GenericRuntimeAdapter
from lychd.domain.animation.services.adapters.surfaces import (
    GenericPortal,
    PassiveConnector,
    portal_link_default,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class RuntimeAdapterRegistry:
    """Runtime switchboard for command planning and runtime-handle construction.

    Soulstones are dispatched by runtime name to registered adapters.
    Portals are dispatched by the factory that owns their exact Rune schema.
    """

    def __init__(
        self,
        adapters: Sequence[SoulstoneRuntimeAdapter] | None = None,
        *,
        portal_definitions: Sequence[PortalDefinition] | None = None,
    ) -> None:
        """Initialize active runtime adapters plus generic fallback.

        Portal definitions are injected by the composition root (the OpenAI
        definition is an extension, no longer a domain-side default); the passive
        fallback applies only when no extension owns the exact Rune schema.
        """
        self._fallback: SoulstoneRuntimeAdapter = GenericRuntimeAdapter()
        self._adapters: dict[str, SoulstoneRuntimeAdapter] = {}
        for adapter in adapters or ():
            runtime = adapter.runtime
            existing = self._adapters.get(runtime)
            if existing is not None:
                msg = (
                    f"Soulstone runtime {runtime!r} already has adapter "
                    f"{type(existing).__name__}; refusing {type(adapter).__name__}."
                )
                raise ValueError(msg)
            self._adapters[runtime] = adapter
        self._portal_definitions: dict[type[PortalConfig], PortalDefinition] = {}
        for definition in portal_definitions or ():
            self.register_portal_definition(definition)

    def register_portal_definition(self, definition: PortalDefinition) -> None:
        """Register the sole runtime factory allowed to claim one Rune schema."""
        existing = self._portal_definitions.get(definition.rune_schema)
        if existing is not None:
            msg = f"Portal schema {definition.rune_schema.__name__} already has a runtime definition."
            raise ValueError(msg)
        self._portal_definitions[definition.rune_schema] = definition

    def adapter_for(self, soulstone: SoulstoneConfig) -> SoulstoneRuntimeAdapter:
        """Return the adapter that owns the exact declared Soulstone runtime key."""
        return self._adapters.get(soulstone.runtime_name, self._fallback)

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

    def build_runtime(self, rune: SoulstoneConfig | PortalConfig) -> RuntimeAnimator | None:
        """Build runtime handle for Soulstone/Portal rune declarations."""
        if isinstance(rune, PortalConfig):
            return self._build_portal_runtime(rune)

        return self.adapter_for(rune).build_runtime(rune)

    def runtime_factory(self, rune: SoulstoneConfig | PortalConfig) -> RuntimeAnimator | None:
        """Adapter-compatible callable used by ``AnimatorRegistry`` factories."""
        return self.build_runtime(rune)

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
        """Resolve a Portal by exact schema ownership, then passive fallback."""
        definition = self._portal_definitions.get(type(portal))
        if definition is not None:
            return definition.factory(portal)

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
        provider = portal.provider_name.strip().lower()
        specs: list[CapabilitySpec] = []
        for model in portal.models:
            hints = model.capabilities
            info = model_info_from_portal_model(model)
            generation = GenerationProfile().overlay(portal.generation).overlay(model.generation)
            specs.extend(
                CapabilitySpec(
                    key=f"{portal.name}:{family}:{model.id}",
                    animator_name=portal.name,
                    runtime=f"portal:{provider}",
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
                    metadata={"provider_name": provider},
                )
                for family in synthesize_families(info, hints, None)
            )
        return specs

    async def _probe_portal_capability_states(
        self, animator: RuntimeAnimator, specs: list[CapabilitySpec]
    ) -> list[CapabilityState]:
        """Project portal readiness into phase-canonical states (opt-in live probe).

        With ``rune.probe`` true, only the exact Portal definition's typed probe
        may perform egress and update readiness. Otherwise the connector's
        passive/static link is read as-is.
        """
        connector = animator.connector
        rune = animator.rune
        if isinstance(rune, PortalConfig) and rune.probe:
            definition = self._portal_definitions.get(type(rune))
            if definition is None or definition.probe is None:
                msg = (
                    f"Portal {rune.name!r} requests live probing, but schema "
                    f"{type(rune).__name__} has no exact probe strategy."
                )
                raise RuntimeError(msg)
            await definition.probe(animator)

        link = connector.link
        probed = isinstance(rune, PortalConfig) and rune.probe
        up = link.up
        phase = CapabilityPhase.WARM if up else CapabilityPhase.COLD
        if not probed:
            phase = CapabilityPhase.UNKNOWN
        health = "ok" if up else ("down" if probed else "unverified")
        checked_at = datetime.now(UTC) if probed else None
        return [
            CapabilityState(
                capability_key=spec.key,
                is_dynamic=False,
                phase=phase,
                health=health,
                active_model_id=spec.model_id if phase is CapabilityPhase.WARM else None,
                loaded_model_ids=[spec.model_id] if phase is CapabilityPhase.WARM else [],
                reason=None if up else link.reason,
                checked_at=checked_at,
                metadata=cast("dict[str, object]", getattr(connector, "metadata", {})),
            )
            for spec in specs
        ]


__all__ = ["RuntimeAdapterRegistry"]
