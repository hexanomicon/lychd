"""Registry-level runtime adapter dispatch and portal runtime construction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lychd.domain.animation.capabilities import CapabilityFamily, CapabilitySpec, CapabilityState
from lychd.domain.animation.schemas import ModelInfo, PortalConfig, SoulstoneConfig
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.animation.schemas.generation import GenerationProfile
from lychd.domain.animation.schemas.model_info import ModelSurface
from lychd.domain.animation.services.adapters.contracts import RuntimeAnimator, RuntimePlan, SoulstoneRuntimeAdapter
from lychd.domain.animation.services.adapters.runtimes.generic import GenericRuntimeAdapter
from lychd.domain.animation.services.adapters.surfaces import (
    GenericPortal,
    OpenAICompatibleConnector,
    OpenAIPortal,
    PassiveConnector,
    portal_link_default,
)
from lychd.extensions.builtin.animator.runtimes import (
    LlamaCppRuntimeAdapter,
    SglangRuntimeAdapter,
    VllmRuntimeAdapter,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from pydantic_ai.toolsets import AbstractToolset

type PortalRuntimeFactory = Callable[[PortalConfig], RuntimeAnimator | None]

_OPENAI_COMPATIBLE_PROVIDERS = {
    "openai",
    "openai_compatible",
    "openai-compatible",
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
        adapters: list[SoulstoneRuntimeAdapter] | None = None,
        *,
        portal_factories: Sequence[PortalRuntimeFactory] | None = None,
    ) -> None:
        """Initialize built-in runtime adapters plus generic fallback."""
        self._fallback: SoulstoneRuntimeAdapter = GenericRuntimeAdapter()
        self._adapters = adapters or [
            LlamaCppRuntimeAdapter(),
            VllmRuntimeAdapter(),
            SglangRuntimeAdapter(),
        ]
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

    def plan(self, soulstone: SoulstoneConfig) -> RuntimePlan:
        """Build a host-facing runtime plan for a Soulstone."""
        adapter = self.adapter_for(soulstone)
        return adapter.plan(soulstone)

    def build_runtime(self, rune: SoulstoneConfig | PortalConfig) -> RuntimeAnimator | None:
        """Build runtime handle for Soulstone/Portal rune declarations."""
        if isinstance(rune, PortalConfig):
            return self._build_portal_runtime(rune)

        adapter = self.adapter_for(rune)
        return adapter.build_runtime(rune)

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

    def probe_capability_states(self, animator: RuntimeAnimator, specs: list[CapabilitySpec]) -> list[CapabilityState]:
        """Probe capability states for either a soulstone or portal runtime."""
        rune = animator.rune
        if isinstance(rune, PortalConfig):
            return self._probe_portal_capability_states(animator, specs)

        adapter = self.adapter_for(rune)
        return adapter.probe_capability_states(animator, specs)

    def activate_capability(self, animator: RuntimeAnimator, spec: CapabilitySpec) -> bool:
        """Delegate runtime-specific capability activation when supported."""
        rune = animator.rune
        if isinstance(rune, PortalConfig):
            return False

        adapter = self.adapter_for(rune)
        return adapter.activate_capability(animator, spec)

    def _build_portal_runtime(self, portal: PortalConfig) -> RuntimeAnimator:
        """Resolve portal runtime by custom factories, then passive fallback."""
        for factory in self._portal_factories:
            runtime = factory(portal)
            if runtime is not None:
                return runtime

        return self._build_passive_portal(portal)

    def _build_openai_portal(self, portal: PortalConfig) -> RuntimeAnimator | None:
        """Build OpenAI-compatible portal runtime for known provider aliases."""
        base_url = portal.base_url
        provider = portal.provider_type.strip().lower()
        default_model_id = portal.default_model_id

        link = portal_link_default(base_url=base_url)

        if provider in _OPENAI_COMPATIBLE_PROVIDERS:
            model_infos = [ModelInfo(id=default_model_id)] if default_model_id else []
            connector = OpenAICompatibleConnector(
                kind=f"portal:{provider}",
                link=link,
                base_url=base_url,
                model_infos=model_infos,
                default_model_id=default_model_id,
                api_key_secret=portal.api_key_secret,
                toolsets=portal_external_toolsets(portal),
                metadata={
                    "provider_type": portal.provider_type,
                    "base_url": portal.base_url,
                    "dedicated": portal.dedicated,
                    "persistent_resident": portal.persistent_resident,
                },
            )
            return OpenAIPortal(rune=portal, connector=connector)

        return None

    def _build_passive_portal(self, portal: PortalConfig) -> RuntimeAnimator:
        """Build readiness-only portal runtime when no factory matches provider."""
        provider = portal.provider_type.strip().lower()
        link = portal_link_default(base_url=portal.base_url)
        connector = PassiveConnector(
            kind=f"portal:{provider}",
            link=link,
            toolsets=portal_external_toolsets(portal),
        )
        return GenericPortal(rune=portal, connector=connector)

    def _build_portal_capability_specs(self, portal: PortalConfig, runtime: RuntimeAnimator) -> list[CapabilitySpec]:
        """Synthesize capability specs for a portal runtime."""
        families = portal.capabilities.families if portal.capabilities and portal.capabilities.families else None
        if families is None:
            families = [] if portal.external_tools and portal.default_model_id is None else [CapabilityFamily.CHAT]
        surface = (
            portal.capabilities.surface
            if portal.capabilities and portal.capabilities.surface is not None
            else ModelSurface.CHAT
        )
        modalities_in = (
            list(portal.capabilities.modalities_in)
            if portal.capabilities and portal.capabilities.modalities_in is not None
            else ["text"]
        )
        modalities_out = (
            list(portal.capabilities.modalities_out)
            if portal.capabilities and portal.capabilities.modalities_out is not None
            else ["text"]
        )
        supports_tools = portal.capabilities.supports_tools if portal.capabilities else None
        supports_streaming = portal.capabilities.supports_streaming if portal.capabilities else None
        generation_profile = GenerationProfile.model_validate(
            portal.llm_defaults.model_dump(exclude_none=True) if portal.llm_defaults is not None else {}
        )
        concurrency = ConcurrencyIntent(
            dedicated=portal.dedicated,
            persistent_resident=portal.persistent_resident,
        )
        model_id = portal.default_model_id or portal.name
        metadata: dict[str, object] = {
            "provider_type": portal.provider_type,
            "base_url": portal.base_url,
            "dedicated": portal.dedicated,
            "persistent_resident": portal.persistent_resident,
        }
        metadata.update(runtime.connector.metadata)

        specs: list[CapabilitySpec] = [
            CapabilitySpec(
                key=f"{portal.name}:{family}:{model_id}",
                animator_name=portal.name,
                runtime=portal.provider_type,
                source_kind="portal",
                family=family,
                model_id=model_id,
                surface=surface,
                modalities_in=modalities_in,
                modalities_out=modalities_out,
                supports_tools=supports_tools,
                supports_streaming=supports_streaming,
                generation_profile=generation_profile,
                lifecycle_mode="static",
                concurrency=concurrency,
                metadata=metadata,
            )
            for family in families
        ]
        if portal.external_tools:
            specs.append(
                CapabilitySpec(
                    key=f"{portal.name}:{CapabilityFamily.TOOL_EXECUTION}:{model_id}",
                    animator_name=portal.name,
                    runtime=portal.provider_type,
                    source_kind="portal",
                    family=CapabilityFamily.TOOL_EXECUTION,
                    model_id=model_id,
                    surface=surface,
                    modalities_in=modalities_in,
                    modalities_out=modalities_out,
                    supports_tools=True,
                    supports_streaming=supports_streaming,
                    generation_profile=generation_profile,
                    lifecycle_mode="static",
                    concurrency=concurrency,
                    metadata={**metadata, "external_tool_count": len(portal.external_tools)},
                )
            )
        return specs

    def _probe_portal_capability_states(self, animator: RuntimeAnimator, specs: list[CapabilitySpec]) -> list[CapabilityState]:
        """Project passive portal readiness into capability states."""
        link = animator.connector.link
        health = "ok" if link.up else "down"
        return [
            CapabilityState(
                capability_key=spec.key,
                is_static=True,
                is_active=link.up,
                is_available=bool(animator.base_url),
                warm=link.up,
                health=health,
                active_model_id=spec.model_id if link.up else None,
                loaded_model_ids=[spec.model_id] if link.up else [],
                reason=None if link.up else link.reason,
                metadata=animator.connector.metadata,
            )
            for spec in specs
        ]


def portal_external_toolsets(portal: PortalConfig) -> Sequence[AbstractToolset]:
    """Build Pydantic AI external toolsets declared on a Portal Rune."""
    if not portal.external_tools:
        return ()

    try:
        from pydantic_ai import ExternalToolset, ToolDefinition
    except ModuleNotFoundError as exc:
        msg = "Pydantic AI is required to hydrate portal external tools into ExternalToolset instances."
        raise RuntimeError(msg) from exc

    tool_defs = [
        ToolDefinition(
            name=tool.name,
            parameters_json_schema=tool.parameters_json_schema,
            description=tool.description,
            strict=tool.strict,
            sequential=tool.sequential,
        )
        for tool in portal.external_tools
    ]
    return (ExternalToolset(tool_defs, id=f"portal:{portal.name}:external"),)


__all__ = ["RuntimeAdapterRegistry"]
