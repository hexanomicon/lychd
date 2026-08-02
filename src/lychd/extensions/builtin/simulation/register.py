from __future__ import annotations

from lychd.extensions.context import ExtensionRegistrationContext


def register(context: ExtensionRegistrationContext) -> None:
    """Register the built-in Shadow simulation rune schema."""
    from lychd.extensions.builtin.simulation.config import ShadowSimulationConfig

    context.runes.add_schema(ShadowSimulationConfig)
