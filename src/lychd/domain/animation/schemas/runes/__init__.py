"""TOML Rune schemas for the animation domain.

Only TOML-loaded ``RuneConfig``-style declarations live here. Runtime animator
ABCs and connector contracts live outside ``schemas.runes``.
"""

from lychd.domain.animation.schemas.runes.animators import (
    AnimatorConfig,
    GenericSoulstoneConfig,
    GoogleGeminiPortalConfig,
    OpenAIPortalConfig,
    PortalConfig,
    SoulstoneConfig,
)
from lychd.domain.animation.schemas.runes.models import (
    LocalLLMModelConfig,
    LocalModelConfig,
)

__all__ = [
    "AnimatorConfig",
    "GenericSoulstoneConfig",
    "GoogleGeminiPortalConfig",
    "LocalLLMModelConfig",
    "LocalModelConfig",
    "OpenAIPortalConfig",
    "PortalConfig",
    "SoulstoneConfig",
]
