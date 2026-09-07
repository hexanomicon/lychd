"""Registry-level runtime adapter dispatch and portal runtime construction."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

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
    CapabilityActivator,
    PortalDefinition,
    RuntimeAnimator,
    RuntimePlan,
    SoulstoneRuntimeAdapter,
)
from lychd.domain.animation.services.adapters.runtimes.generic import GenericRuntimeAdapter

if TYPE_CHECKING:
    from collections.abc import Sequence


def _declaration_provenance(declaration: SoulstoneConfig | PortalConfig) -> str:
    source_file = str(declaration.source_file) if declaration.source_file is not None else None
    return f"{type(declaration).__name__}(name={declaration.name!r}, source_file={source_file!r})"


def runtime_provenance(runtime: RuntimeAnimator) -> str:
    return f"{type(runtime).__name__} from {_declaration_provenance(runtime.rune)}"


def _require_runtime_identity(
    declaration: SoulstoneConfig | PortalConfig,
    runtime: RuntimeAnimator,
) -> None:
    """Reject a factory result that does not preserve its exact Rune and identity."""
    if runtime.rune != declaration:
        msg = (
            f"Runtime factory for {_declaration_provenance(declaration)} returned "
            f"{runtime_provenance(runtime)}, which does not retain the declared Rune value."
        )
        raise ValueError(msg)
    if runtime.name != declaration.name:
        msg = (
            f"Runtime for {_declaration_provenance(declaration)} must use canonical name "
            f"{declaration.name!r}; received name={runtime.name!r}."
        )
        raise ValueError(msg)


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
        """Initialize active runtime adapters and exact Portal definitions."""
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
            existing = self._portal_definitions.get(definition.rune_schema)
            if existing is not None:
                msg = f"Portal schema {definition.rune_schema.__name__} already has a runtime definition."
                raise ValueError(msg)
            self._portal_definitions[definition.rune_schema] = definition

    def _adapter_for(self, soulstone: SoulstoneConfig) -> SoulstoneRuntimeAdapter:
        """Return the adapter that owns the exact declared Soulstone runtime key."""
        return self._adapters.get(soulstone.runtime, self._fallback)

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Build a host-facing runtime plan for a Soulstone."""
        adapter = self._adapter_for(soulstone)
        return adapter.plan(soulstone)

    def build_runtime(self, rune: SoulstoneConfig | PortalConfig) -> RuntimeAnimator | None:
        """Build runtime handle for Soulstone/Portal rune declarations."""
        if isinstance(rune, PortalConfig):
            runtime = self._build_portal_runtime(rune)
        else:
            runtime = self._adapter_for(rune).build_runtime(rune)
        if runtime is not None:
            _require_runtime_identity(rune, runtime)
        return runtime

    def build_capability_specs(
        self,
        animator: RuntimeAnimator,
    ) -> list[CapabilitySpec]:
        """Derive specs from the same runtime generation that will execute them."""
        rune = animator.rune
        if isinstance(rune, PortalConfig):
            if type(rune) not in self._portal_definitions:
                return []
            return self._build_portal_capability_specs(rune)

        adapter = self._adapter_for(rune)
        return adapter.build_capability_specs(animator)

    async def probe_capability_states(
        self,
        animator: RuntimeAnimator,
        specs: list[CapabilitySpec],
    ) -> list[CapabilityState]:
        """Probe capability states for either a soulstone or portal runtime."""
        rune = animator.rune
        if isinstance(rune, PortalConfig):
            return await self._probe_portal_capability_states(animator, specs)

        adapter = self._adapter_for(rune)
        return await adapter.probe_capability_states(animator, specs)

    async def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> ActivationResult:
        """Delegate runtime-specific capability activation when supported."""
        if not spec.is_dynamic:
            return ActivationResult(
                accepted=False,
                reason="fixed capability; lifecycle owned by unit",
            )
        rune = animator.rune
        if isinstance(rune, PortalConfig):
            return ActivationResult(
                accepted=False,
                reason="portal capabilities cannot be activated locally",
            )

        adapter = self._adapter_for(rune)
        if not isinstance(adapter, CapabilityActivator):
            return ActivationResult(
                accepted=False,
                reason=f"runtime {rune.runtime!r} has no capability activation contract",
            )
        return await adapter.activate_capability(animator, spec)

    async def abandon_activation(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> None:
        """Stop adapter-owned observation after canonical warm convergence ends."""
        rune = animator.rune
        if isinstance(rune, PortalConfig):
            return
        adapter = self._adapter_for(rune)
        if isinstance(adapter, ActivationObserver):
            await adapter.abandon_activation(animator, spec)

    def _build_portal_runtime(self, portal: PortalConfig) -> RuntimeAnimator | None:
        """Resolve a Portal only through its exact registered schema owner."""
        definition = self._portal_definitions.get(type(portal))
        return definition.factory(portal) if definition is not None else None

    def _build_portal_capability_specs(self, portal: PortalConfig) -> list[CapabilitySpec]:
        """Synthesize capability specs from a Portal's declared ``[[models]]``.

        Zero declared models ⇒ zero specs (reachable but unadvertised). Families
        are synthesized under the two-axis law (probe facts are absent at synthesis).
        """
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
                    max_context=info.max_context,
                    modalities_in=info.modalities_in,
                    supports_tools=info.supports_tools,
                    generation_profile=generation,
                    is_dynamic=False,
                    # A Portal is remote: LychD does not own its lifecycle (ADR-22).
                    concurrency=ConcurrencyIntent(dedicated=False),
                )
                for family in synthesize_families(info, hints)
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
        observed_model_ids = getattr(connector, "observed_model_ids", None)
        inventory_error = getattr(connector, "inventory_error", None)
        states: list[CapabilityState] = []
        for spec in specs:
            spec_phase = phase
            spec_health = health
            reason = None if up else link.reason
            if probed and up and inventory_error is not None:
                spec_phase = CapabilityPhase.ERROR
                spec_health = "inventory_invalid"
                reason = str(inventory_error)
            elif probed and up and observed_model_ids is not None:
                model_present = spec.model_id in observed_model_ids
                if not model_present:
                    spec_phase = CapabilityPhase.ERROR
                    spec_health = "model_missing"
                    reason = f"declared model {spec.model_id!r} is absent from /models"
            states.append(
                CapabilityState(
                    capability_key=spec.key,
                    phase=spec_phase,
                    health=spec_health,
                    reason=reason,
                    checked_at=checked_at,
                )
            )
        return states


__all__ = ["RuntimeAdapterRegistry"]
