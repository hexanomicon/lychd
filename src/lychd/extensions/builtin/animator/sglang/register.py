from __future__ import annotations

from lychd.domain.animation.services.adapters.contracts import SoulstoneDefinition
from lychd.extensions.context import ExtensionRegistrationContext


def register(context: ExtensionRegistrationContext) -> None:
    """Register the built-in SGLang Soulstone schema and runtime adapter."""
    from lychd.domain.animation.services.adapters.runtimes.openai_compat import OpenAICompatibleRuntimeAdapter
    from lychd.extensions.builtin.animator.soulstones import SglangSoulstoneConfig

    context.soulstones.add(
        SoulstoneDefinition(
            rune_schema=SglangSoulstoneConfig,
            runtime_adapter=OpenAICompatibleRuntimeAdapter(
                runtime="sglang",
                config_type=SglangSoulstoneConfig,
            ),
        )
    )
