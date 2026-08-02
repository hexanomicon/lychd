from __future__ import annotations

from typing import TYPE_CHECKING

from lychd.domain.animation.model_factory import validate_openai_interface_target
from lychd.domain.animation.schemas import ModelSurface, OpenAICompatibleProvider, PortalConfig
from lychd.domain.animation.services.adapters.catalog import model_info_from_portal_model
from lychd.domain.animation.services.adapters.runtimes.shared import probe_openai_compatible_link
from lychd.domain.animation.services.adapters.surfaces import (
    OpenAICompatibleConnector,
    OpenAIPortal,
    portal_link_default,
)

if TYPE_CHECKING:
    from lychd.domain.animation.services.adapters.contracts import RuntimeAnimator
    from lychd.extensions.context import ExtensionRegistrationContext


def build_openai_portal(portal: PortalConfig) -> RuntimeAnimator:
    """Build an OpenAI-compatible Portal runtime for one schema-valid provider alias.

    Extension-owned portal factory (the domain no longer defaults to OpenAI —
    import law). The registered Rune schemas reject aliases this factory cannot
    construct; a direct call with another Portal type fails loudly.
    """
    base_url = str(portal.base_url) if portal.base_url is not None else ""
    try:
        provider = OpenAICompatibleProvider(portal.provider_name.strip().lower()).value
    except ValueError as exc:
        msg = f"Unsupported OpenAI-compatible Portal provider alias: {portal.provider_name!r}."
        raise ValueError(msg) from exc

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


async def probe_openai_portal(animator: RuntimeAnimator) -> None:
    """Probe the exact OpenAI-compatible connector owned by this Portal definition."""
    connector = animator.connector
    if not isinstance(connector, OpenAICompatibleConnector):
        msg = "OpenAI-compatible Portal probe received a runtime with another connector contract."
        raise TypeError(msg)
    connector.set_link(await probe_openai_compatible_link(connector))


def register(context: ExtensionRegistrationContext) -> None:
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
    context.portals.add(
        PortalDefinition(
            rune_schema=OpenAIPortalConfig,
            factory=build_openai_portal,
            probe=probe_openai_portal,
        )
    )
    context.portals.add(
        PortalDefinition(
            rune_schema=GoogleGeminiPortalConfig,
            factory=build_openai_portal,
            probe=probe_openai_portal,
        )
    )
