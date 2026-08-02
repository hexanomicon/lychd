from __future__ import annotations

from lychd.extensions.context import ExtensionRegistrationContext


def register(context: ExtensionRegistrationContext) -> None:
    """Register the built-in Phoenix observability rune schema + Quadlet contributor."""
    from lychd.extensions.builtin.observability.phoenix.config import ObservabilityConfig, PhoenixSettings
    from lychd.extensions.builtin.observability.phoenix.contributor import PhoenixQuadletContributor

    context.runes.add_schema(ObservabilityConfig)
    context.runes.add_schema(PhoenixSettings)
    context.transmutation.add_contributor(PhoenixQuadletContributor())
