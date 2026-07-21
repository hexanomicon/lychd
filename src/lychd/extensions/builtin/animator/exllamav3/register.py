from __future__ import annotations

from lychd.domain.animation.services.adapters.contracts import SoulstoneDefinition
from lychd.extensions.context import ExtensionContext


def register(context: ExtensionContext) -> None:
    """Register the built-in ExLlamaV3/TabbyAPI schema and runtime adapter."""
    from lychd.extensions.builtin.animator.register import register as register_animator
    from lychd.extensions.builtin.animator.runtimes import ExLlamaV3RuntimeAdapter
    from lychd.extensions.builtin.animator.soulstones import ExLlamaV3SoulstoneConfig

    register_animator(context)
    context.soulstones.add(
        SoulstoneDefinition(
            rune_schema=ExLlamaV3SoulstoneConfig,
            runtime_adapter=ExLlamaV3RuntimeAdapter(),
        )
    )


__all__ = ["register"]
