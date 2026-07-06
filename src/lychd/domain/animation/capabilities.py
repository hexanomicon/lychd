from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from pydantic_ai.settings import ModelSettings

from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.animation.schemas.generation import GenerationProfile
from lychd.domain.animation.schemas.model_info import ModelSurface


class CapabilityLifecycle(StrEnum):
    """How a capability becomes warm. Doctrine: static vs dynamic."""

    STATIC = "static"  # resident whenever the animator unit is up
    DYNAMIC = "dynamic"  # needs an in-runtime activation step after the unit is up


class CapabilityPhase(StrEnum):
    """Observed position in the warm-up ladder. THE dispatch decision input."""

    COLD = "cold"  # animator unit down / endpoint unreachable
    ACTIVATABLE = "activatable"  # unit up; DYNAMIC model not loaded (router: status != loaded)
    WARMING = "warming"  # activation in flight (/health 503 "Loading model")
    WARM = "warm"  # /health ok — requests accepted now
    ERROR = "error"
    UNKNOWN = "unknown"


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
    lifecycle: CapabilityLifecycle = CapabilityLifecycle.STATIC
    concurrency: ConcurrencyIntent = Field(default_factory=ConcurrencyIntent)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityState(BaseModel):
    """Observed live state for a synthesized capability.

    ``phase`` is the canonical field; the historical booleans are derived
    properties so existing Dispatcher/OrchestratorManager read-sites keep
    compiling while probe producers migrate to the phase model (A3-U4).
    """

    model_config = ConfigDict(extra="forbid")

    capability_key: str = Field(min_length=1)
    lifecycle: CapabilityLifecycle
    phase: CapabilityPhase
    health: str = "unknown"
    active_model_id: str | None = None
    loaded_model_ids: list[str] = Field(default_factory=list)
    reason: str | None = None
    checked_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def warm(self) -> bool:
        return self.phase is CapabilityPhase.WARM

    @property
    def is_static(self) -> bool:
        return self.lifecycle is CapabilityLifecycle.STATIC

    @property
    def is_active(self) -> bool:
        return self.phase in {CapabilityPhase.WARM, CapabilityPhase.WARMING}

    @property
    def is_available(self) -> bool:
        return self.phase is not CapabilityPhase.ERROR


@dataclass(frozen=True, slots=True)
class ActivationResult:
    """Outcome of a runtime-native capability activation request (A3-U4 §2).

    ``accepted`` reports whether the runtime took the activation request;
    ``phase`` is the capability phase observed immediately after the request;
    ``reason`` explains a rejection (e.g. a STATIC-lifecycle capability whose
    warmth is owned by the animator unit, not an in-runtime load).
    """

    accepted: bool
    phase: CapabilityPhase
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class GrantLease:
    """Identity + accounting for one issued grant. THE row the LeaseLedger counts."""

    grant_id: str  # uuid4().hex — unique per issue
    holder: str  # "run:<run_id>" | "cli:<command>"
    issued_at: datetime  # aware UTC
    scope: Literal["step", "run"] = "step"  # doctrine today: per-step lease
    expires_at: datetime | None = None  # None = until released/superseded


@dataclass(frozen=True, slots=True)
class CapabilityGrant:
    """Canonical dispatch handoff for one granted capability (spec-00-FINAL C1).

    Frozen dataclass (not pydantic): carries live runtime handles. ``model`` and
    ``toolsets`` are typed ``Any`` so the module stays import-light — at runtime
    they are a hydrated pydantic-ai ``Model`` and a tuple of ``AbstractToolset``.
    """

    spec: CapabilitySpec
    state: CapabilityState  # snapshot at issue time (phase == WARM)
    lease: GrantLease
    generation: GenerationProfile  # RESOLVED (runtime < animator < model)
    animator: Any  # RuntimeAnimator live handle
    model: Any | None  # hydrated pydantic-ai Model (None: tool-only)
    toolsets: tuple[Any, ...] = field(default_factory=tuple)

    @property
    def key(self) -> str:
        return self.spec.key

    def model_settings(self) -> ModelSettings | None:
        """Bridge the resolved generation profile to pydantic-ai ModelSettings."""
        from lychd.domain.animation.services.binder import generation_to_model_settings

        return generation_to_model_settings(self.generation)
