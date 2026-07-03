from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.generation import GenerationProfile
from lychd.domain.animation.schemas.model_info import ModelSurface
from lychd.domain.animation.schemas.shared import ModelFormat


class ModelCapabilityHints(BaseModel):
    """Optional connector-facing capability hints for runtime model summaries."""

    model_config = ConfigDict(extra="forbid")

    families: list[CapabilityFamily] | None = None
    surface: ModelSurface | None = None
    modalities_in: list[str] | None = None
    modalities_out: list[str] | None = None
    supports_tools: bool | None = None
    supports_streaming: bool | None = None


class LocalModelConfig(BaseModel):
    """Local model declaration owned by a Soulstone-style runtime.

    This models a local artifact/runtime slot (path + optional format + metadata).
    It does *not* include connector/provider strings or endpoint URIs. Those are
    runtime connector concerns resolved later.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, description="Stable local model id within the Soulstone.")
    path: Path = Field(description="Folder path containing the local model artifact(s).")
    description: str | None = None
    format: ModelFormat | None = Field(default=None, description="Model weight format.")
    generation: GenerationProfile | None = Field(
        default=None,
        description="Optional generation profile overlay for this specific local model.",
    )
    capabilities: ModelCapabilityHints | None = Field(
        default=None,
        description="Optional model-level capability hints (surface/modalities/tool support).",
    )
    tags: list[str] = Field(default_factory=list)


class LocalLLMModelConfig(LocalModelConfig):
    """Local LLM model declaration.

    This subclass makes the modality intent explicit without forcing all future
    local model declarations (vision, audio, embeddings) into one optional-field
    soup. Additional capability-specific local model subclasses can be added
    alongside this class.
    """
