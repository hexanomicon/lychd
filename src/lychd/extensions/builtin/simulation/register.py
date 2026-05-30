from __future__ import annotations

from lychd.extensions.context import ExtensionContext


def register(context: ExtensionContext) -> None:
    """Register the built-in Shadow simulation rune schema."""
    from lychd.extensions.builtin.simulation.config import ShadowSimulationConfig

    context.runes.add_schema(ShadowSimulationConfig)
