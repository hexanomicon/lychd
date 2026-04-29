"""Animation domain public surface.

This package now exposes the new runtime core (animators/connectors/link) and
the schema layers (rune configs + connector model summaries). Builtin extension
implementations are not re-exported here; they live under ``extensions``.
"""

from lychd.domain.animation.animators import Animator, Portal, Soulstone
from lychd.domain.animation.connectors import Connector, ModelConnector, ToolConnector
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import (
    AnimatorConfig,
    ExternalToolConfig,
    LLMGenerationConfig,
    LLMGenerationDefaults,
    LocalLLMModelConfig,
    LocalModelConfig,
    ModelCapabilityHints,
    ModelFormat,
    ModelInfo,
    PortalConfig,
    SoulstoneConfig,
    is_placeholder,
)

__all__ = [
    "Animator",
    "AnimatorConfig",
    "Connector",
    "ExternalToolConfig",
    "LLMGenerationConfig",
    "LLMGenerationDefaults",
    "Link",
    "LocalLLMModelConfig",
    "LocalModelConfig",
    "ModelCapabilityHints",
    "ModelConnector",
    "ModelFormat",
    "ModelInfo",
    "Portal",
    "PortalConfig",
    "Soulstone",
    "SoulstoneConfig",
    "ToolConnector",
    "is_placeholder",
]
