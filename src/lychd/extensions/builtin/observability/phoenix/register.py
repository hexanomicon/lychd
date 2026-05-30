from __future__ import annotations

from lychd.extensions.context import ExtensionContext


def register(context: ExtensionContext) -> None:
    """Register the built-in Phoenix observability rune schema."""
    from lychd.extensions.builtin.observability.phoenix.config import ObservabilityConfig, PhoenixSettings

    context.runes.add_schema(ObservabilityConfig)
    context.runes.add_schema(PhoenixSettings)
