from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.animation.schemas.generation import GenerationProfile
from lychd.domain.animation.schemas.model_info import ModelSurface


class CapabilitySpec(BaseModel):
    """Synthesized capability declaration for one animator/runtime/model binding."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    animator_name: str = Field(min_length=1)
    runtime: str = Field(min_length=1)
    source_kind: str = Field(min_length=1)
    family: CapabilityFamily
    model_id: str = Field(min_length=1)
    surface: ModelSurface | None = None
    modalities_in: list[str] = Field(default_factory=list)
    modalities_out: list[str] = Field(default_factory=list)
    supports_tools: bool | None = None
    supports_streaming: bool | None = None
    generation_profile: GenerationProfile = Field(default_factory=GenerationProfile)
    lifecycle_mode: str = Field(default="static", min_length=1)
    concurrency: ConcurrencyIntent = Field(default_factory=ConcurrencyIntent)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityState(BaseModel):
    """Observed live state for a synthesized capability."""

    model_config = ConfigDict(extra="forbid")

    capability_key: str = Field(min_length=1)
    is_static: bool
    is_active: bool
    is_available: bool
    warm: bool
    health: str = "unknown"
    active_model_id: str | None = None
    loaded_model_ids: list[str] = Field(default_factory=list)
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityGrant(BaseModel):
    """Canonical dispatch handoff for one granted capability."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    spec: CapabilitySpec
    state: CapabilityState
    animator: Any
    model: Any | None = None
    toolsets: tuple[Any, ...] = ()
