from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from lychd.domain.animation.schemas.model_info import ModelSurface
from lychd.domain.animation.schemas.shared import ModelFormat


class LLMGenerationConfig(BaseModel):
    """Concrete LLM/chat generation settings.

    Use this only when a fully specified generation profile is required.
    """

    model_config = ConfigDict(extra="forbid")

    max_context: int = Field(default=4096, ge=1)
    max_tokens: int = Field(default=4096, ge=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=0)
    repetition_penalty: float = Field(default=1.0, ge=0.0)


class LLMGenerationDefaults(BaseModel):
    """Partial LLM/chat generation overlay.

    This is a merge-only schema. All fields are optional so it can be used for
    defaults (animator-level, Soulstone-level, or model-level) without forcing a
    fake "complete" configuration when the runtime/connector will infer values.
    """

    model_config = ConfigDict(extra="forbid")

    max_context: int | None = Field(default=None, ge=1)
    max_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    top_k: int | None = Field(default=None, ge=0)
    repetition_penalty: float | None = Field(default=None, ge=0.0)


class ModelCapabilityHints(BaseModel):
    """Optional connector-facing capability hints for runtime model summaries."""

    model_config = ConfigDict(extra="forbid")

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
    llm_defaults: LLMGenerationDefaults | None = Field(
        default=None,
        description="Optional LLM generation defaults overlay for this specific local model.",
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
