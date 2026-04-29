"""Registry-level runtime adapter dispatch and portal runtime construction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lychd.domain.animation.schemas import ModelInfo, PortalConfig, SoulstoneConfig
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
            )
            return OpenAIPortal(rune=portal, connector=connector)

        return None

    def _build_passive_portal(self, portal: PortalConfig) -> RuntimeAnimator:
        """Build readiness-only portal runtime when no factory matches provider."""
        provider = portal.provider_type.strip().lower()
        link = portal_link_default(base_url=portal.base_url)
        connector = PassiveConnector(kind=f"portal:{provider}", link=link)
        return GenericPortal(rune=portal, connector=connector)


def portal_external_toolsets(portal: PortalConfig) -> Sequence[AbstractToolset]:
    """Build Pydantic AI external toolsets declared on a portal rune."""
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
