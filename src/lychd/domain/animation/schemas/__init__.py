"""Animation schema models (domain model-info DTOs + TOML Rune schemas).

This package defines TOML-loaded configuration shapes for animation.
Rune models live under ``schemas.runes``. Domain DTO contracts (for
example connector-local model summaries for orchestration/model selection) live
directly under ``schemas``.
"""

from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.animation.schemas.generation import GenerationProfile
from lychd.domain.animation.schemas.model_info import ModelInfo, ModelSurface
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
    ModelCapabilityHints,
    PortalModelConfig,
)
from lychd.domain.animation.schemas.shared import ModelFormat, is_placeholder

__all__ = [
    "AnimatorConfig",
    "CapabilityFamily",
    "ConcurrencyIntent",
    "GenerationProfile",
    "GenericSoulstoneConfig",
    "GoogleGeminiPortalConfig",
    "LocalLLMModelConfig",
    "LocalModelConfig",
    "ModelCapabilityHints",
    "ModelFormat",
    "ModelInfo",
    "ModelSurface",
    "OpenAIPortalConfig",
    "PortalConfig",
    "PortalModelConfig",
    "SoulstoneConfig",
    "is_placeholder",
]
