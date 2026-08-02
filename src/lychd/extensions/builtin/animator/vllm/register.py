from __future__ import annotations

from lychd.domain.animation.services.adapters.contracts import SoulstoneDefinition
from lychd.extensions.context import ExtensionRegistrationContext


def register(context: ExtensionRegistrationContext) -> None:
    """Register the built-in vLLM Soulstone schema and runtime adapter."""
    from lychd.extensions.builtin.animator.runtimes import VllmRuntimeAdapter
    from lychd.extensions.builtin.animator.soulstones import VllmSoulstoneConfig

    context.soulstones.add(
        SoulstoneDefinition(
            rune_schema=VllmSoulstoneConfig,
            runtime_adapter=VllmRuntimeAdapter(),
        )
    )
