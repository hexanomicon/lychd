from __future__ import annotations

from lychd.domain.animation.services.adapters.contracts import SoulstoneDefinition
from lychd.extensions.context import ExtensionRegistrationContext


def register(context: ExtensionRegistrationContext) -> None:
    """Register the built-in llama.cpp Soulstone schema and runtime adapter."""
    from lychd.extensions.builtin.animator.runtimes import LlamaCppRuntimeAdapter
    from lychd.extensions.builtin.animator.soulstones import LlamaCppSoulstoneConfig

    context.soulstones.add(
        SoulstoneDefinition(
            rune_schema=LlamaCppSoulstoneConfig,
            runtime_adapter=LlamaCppRuntimeAdapter(),
        )
    )
