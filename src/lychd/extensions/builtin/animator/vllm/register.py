from __future__ import annotations

from lychd.domain.animation.services.adapters.contracts import SoulstoneDefinition
from lychd.extensions.context import ExtensionRegistrationContext


def register(context: ExtensionRegistrationContext) -> None:
    """Register the built-in vLLM Soulstone schema and runtime adapter."""
    from lychd.domain.animation.services.adapters.runtimes.openai_compat import OpenAICompatibleRuntimeAdapter
    from lychd.extensions.builtin.animator.soulstones import VllmSoulstoneConfig

    context.soulstones.add(
        SoulstoneDefinition(
            rune_schema=VllmSoulstoneConfig,
            runtime_adapter=OpenAICompatibleRuntimeAdapter(
                runtime="vllm",
                config_type=VllmSoulstoneConfig,
            ),
        )
    )
