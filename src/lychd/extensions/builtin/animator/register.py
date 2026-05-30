from __future__ import annotations

from lychd.extensions.context import ExtensionContext


def register(context: ExtensionContext) -> None:
    """Register core animator rune branches and portal leaves."""
    from lychd.domain.animation.schemas import (
        AnimatorConfig,
        GenericSoulstoneConfig,
        GoogleGeminiPortalConfig,
        OpenAIPortalConfig,
        PortalConfig,
        SoulstoneConfig,
    )

    for schema in (
        AnimatorConfig,
        SoulstoneConfig,
        GenericSoulstoneConfig,
        PortalConfig,
        OpenAIPortalConfig,
        GoogleGeminiPortalConfig,
    ):
        context.runes.add_schema(schema)
