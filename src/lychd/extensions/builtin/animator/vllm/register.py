from __future__ import annotations

from lychd.domain.animation.services.adapters.contracts import SoulstoneDefinition
from lychd.extensions.context import ExtensionContext


def register(context: ExtensionContext) -> None:
    """Register the built-in vLLM Soulstone schema and runtime adapter."""
    from lychd.extensions.builtin.animator.register import register as register_animator
    from lychd.extensions.builtin.animator.runtimes import VllmRuntimeAdapter
    from lychd.extensions.builtin.animator.soulstones import VllmSoulstoneConfig

    register_animator(context)
    context.soulstones.add(
        SoulstoneDefinition(
            rune_schema=VllmSoulstoneConfig,
            runtime_adapter=VllmRuntimeAdapter(),
        )
    )
