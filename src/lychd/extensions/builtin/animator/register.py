from __future__ import annotations

from typing import TYPE_CHECKING

from lychd.domain.animation.model_factory import validate_openai_interface_target
from lychd.domain.animation.schemas import ModelSurface, PortalConfig
from lychd.domain.animation.services.adapters.catalog import model_info_from_portal_model
from lychd.domain.animation.services.adapters.surfaces import (
    OpenAICompatibleConnector,
    OpenAIPortal,
    portal_link_default,
)

if TYPE_CHECKING:
    from lychd.domain.animation.services.adapters.contracts import RuntimeAnimator
    from lychd.extensions.context import ExtensionContext

_OPENAI_COMPATIBLE_PROVIDERS = {
    "openai",
    "openai_compatible",
    "openai-compatible",
    "google-gemini",
    "openrouter",
    "ollama",
    "litellm",
}


def build_openai_portal(portal: PortalConfig) -> RuntimeAnimator | None:
    """Build an OpenAI-compatible portal runtime for known provider aliases.

    Extension-owned portal factory (the domain no longer defaults to OpenAI —
    import law). Returns ``None`` for unknown providers so the domain's passive
    fallback applies.
    """
    base_url = str(portal.base_url) if portal.base_url is not None else ""
    provider = portal.provider_name.strip().lower()
    if provider not in _OPENAI_COMPATIBLE_PROVIDERS:
        return None

    model_infos = [model_info_from_portal_model(model) for model in portal.models]
    for model in model_infos:
        validate_openai_interface_target(
            provider_name=provider,
            model_id=model.id,
            responses=model.surface is ModelSurface.RESPONSES,
        )

    link = portal_link_default(base_url=base_url)
    connector = OpenAICompatibleConnector(
        kind=f"portal:{provider}",
        link=link,
        base_url=base_url,
        model_infos=model_infos,
        default_model_id=model_infos[0].id if model_infos else None,
        api_key_secret_name=portal.api_key_secret_name,
        provider_name=provider,
        metadata={
            "provider_name": portal.provider_name,
            "base_url": base_url,
        },
    )
    return OpenAIPortal(rune=portal, connector=connector)


def register(context: ExtensionContext) -> None:
    """Register core animator rune branches and builtin portal provider families."""
    from lychd.domain.animation.schemas import (
        AnimatorConfig,
        GenericSoulstoneConfig,
        GoogleGeminiPortalConfig,
        OpenAIPortalConfig,
        SoulstoneConfig,
    )
    from lychd.domain.animation.services.adapters.contracts import PortalDefinition

    for schema in (
        AnimatorConfig,
        SoulstoneConfig,
        GenericSoulstoneConfig,
        PortalConfig,
    ):
        context.runes.add_schema(schema)

    # PortalStore.add registers each provider's rune schema (dedup by identity).
    context.portals.add(PortalDefinition(rune_schema=OpenAIPortalConfig, factory=build_openai_portal))
    context.portals.add(PortalDefinition(rune_schema=GoogleGeminiPortalConfig, factory=build_openai_portal))
