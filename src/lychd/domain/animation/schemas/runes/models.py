from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.generation import GenerationProfile
from lychd.domain.animation.schemas.model_info import ModelSurface
from lychd.domain.animation.schemas.shared import ModelFormat


class ModelCapabilityHints(BaseModel):
    """Optional connector-facing capability hints for runtime model summaries."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    families: tuple[CapabilityFamily, ...] | None = None
    surface: ModelSurface | None = None
    modalities_in: tuple[str, ...] | None = None
    supports_tools: bool | None = None


class LocalModelConfig(BaseModel):
    """Local model declaration owned by a Soulstone-style runtime.

    This models a local artifact/runtime slot (path + optional format).
    It does *not* include connector/provider strings or endpoint URIs. Those are
    runtime connector concerns resolved later.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, description="Stable local model id within the Soulstone.")
    path: Path = Field(description="Folder path containing the local model artifact(s).")
    format: ModelFormat | None = Field(default=None, description="Model weight format.")
    generation: GenerationProfile | None = Field(
        default=None,
        description="Optional generation profile overlay for this specific local model.",
    )
    capabilities: ModelCapabilityHints | None = Field(
        default=None,
        description="Optional model-level capability hints (surface/modalities/tool support).",
    )


class PortalModelConfig(BaseModel):
    """Remote/API model declaration owned by a Portal.

    A Portal exposes zero or more models it is allowed to route to. Unlike a
    local model there is no artifact path — only the provider-facing model id,
    optional capability hints, and an optional per-model generation overlay.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, description="Provider-facing model id routed by this Portal.")
    capabilities: ModelCapabilityHints | None = Field(
        default=None,
        description="Optional model-level capability hints (surface/modalities/tool support).",
    )
    generation: GenerationProfile | None = Field(
        default=None,
        description="Optional generation profile overlay for this specific portal model.",
    )
