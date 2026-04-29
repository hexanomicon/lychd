"""Animation schema models (domain model-info DTOs + rune config schemas).

This package defines TOML-loaded configuration shapes for animation.
Rune/config models live under ``schemas.runes``. Domain DTO contracts (for
example connector-local model summaries for orchestration/model selection) live
directly under ``schemas``.
"""

from lychd.domain.animation.schemas.model_info import ModelInfo, ModelSurface
from lychd.domain.animation.schemas.runes.animators import (
    AnimatorConfig,
    ExternalToolConfig,
    PortalConfig,
    SoulstoneConfig,
)
from lychd.domain.animation.schemas.runes.models import (
    LLMGenerationConfig,
    LLMGenerationDefaults,
    LocalLLMModelConfig,
    LocalModelConfig,
    ModelCapabilityHints,
)
from lychd.domain.animation.schemas.shared import ModelFormat, is_placeholder

__all__ = [
    "AnimatorConfig",
    "ExternalToolConfig",
    "LLMGenerationConfig",
    "LLMGenerationDefaults",
    "LocalLLMModelConfig",
    "LocalModelConfig",
    "ModelCapabilityHints",
    "ModelFormat",
    "ModelInfo",
    "ModelSurface",
    "PortalConfig",
    "SoulstoneConfig",
    "is_placeholder",
]
