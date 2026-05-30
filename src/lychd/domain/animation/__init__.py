"""Animation domain public surface.

This package now exposes the new runtime core (animators/connectors/link) and
the schema layers (TOML Runes + connector model summaries). Builtin extension
implementations are not re-exported here; they live under ``extensions``.
"""

from lychd.domain.animation.animators import Animator, Portal, Soulstone
from lychd.domain.animation.capabilities import (
    CapabilityFamily,
    CapabilityGrant,
    CapabilitySpec,
    CapabilityState,
)
from lychd.domain.animation.connectors import Connector, ModelConnector, ToolConnector
from lychd.domain.animation.extension import PortalStore, SoulstoneStore
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import (
    AnimatorConfig,
    ConcurrencyIntent,
    GenerationProfile,
    GoogleGeminiPortalConfig,
    LLMGenerationConfig,
    LLMGenerationDefaults,
    LocalLLMModelConfig,
    LocalModelConfig,
    ModelCapabilityHints,
    ModelFormat,
    ModelInfo,
    OpenAIPortalConfig,
    PortalConfig,
    SoulstoneConfig,
    is_placeholder,
)

__all__ = [
    "Animator",
    "AnimatorConfig",
    "CapabilityFamily",
    "CapabilityGrant",
    "CapabilitySpec",
    "CapabilityState",
    "ConcurrencyIntent",
    "Connector",
    "GenerationProfile",
    "GoogleGeminiPortalConfig",
    "LLMGenerationConfig",
    "LLMGenerationDefaults",
    "Link",
    "LocalLLMModelConfig",
    "LocalModelConfig",
    "ModelCapabilityHints",
    "ModelConnector",
    "ModelFormat",
    "ModelInfo",
    "OpenAIPortalConfig",
    "Portal",
    "PortalConfig",
    "PortalStore",
    "Soulstone",
    "SoulstoneConfig",
    "SoulstoneStore",
    "ToolConnector",
    "is_placeholder",
]
