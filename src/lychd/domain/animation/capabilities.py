from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from pydantic_ai.models import Model
    from pydantic_ai.settings import ModelSettings
    from pydantic_ai.toolsets import AbstractToolset

from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.animation.schemas.generation import GenerationProfile
from lychd.domain.animation.schemas.model_info import ModelSurface


class SourceKind(StrEnum):
    """How a capability's animator came to exist — the lifecycle-management discriminator.

    An explicit trait, not "absence of a soulstone rune": a PORTAL is a remote service
    LychD cannot start/stop/swap; a SOULSTONE is a local unit LychD owns.
    """

    SOULSTONE = "soulstone"
    PORTAL = "portal"


class CapabilityPhase(StrEnum):
    """Observed position in the warm-up ladder. THE dispatch decision input."""

    COLD = "cold"  # animator unit down / endpoint unreachable
    ACTIVATABLE = "activatable"  # unit up; DYNAMIC model not loaded (router: status != loaded)
    WARMING = "warming"  # activation in flight (/health 503 "Loading model")
    WARM = "warm"  # exact admitted binding currently accepts its proved operation set
    ERROR = "error"
    UNKNOWN = "unknown"


class CapabilitySpec(BaseModel):
    """Synthesized capability declaration for one animator/runtime/model binding."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    animator_name: str = Field(min_length=1)
    runtime: str = Field(min_length=1)
    source_kind: SourceKind
    family: CapabilityFamily
    model_id: str = Field(min_length=1)
    surface: ModelSurface | None = None
    # The most operationally important model fact — promoted to a real field (a metadata
    # key read by domain code must be a field). Overlaid by generation_profile.max_context.
    max_context: int | None = None
    modalities_in: list[str] = Field(default_factory=list)
    modalities_out: list[str] = Field(default_factory=list)
    supports_tools: bool | None = None
    supports_streaming: bool | None = None
    generation_profile: GenerationProfile = Field(default_factory=GenerationProfile)
    is_dynamic: bool = False
    concurrency: ConcurrencyIntent = Field(default_factory=ConcurrencyIntent)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _enforce_portal_invariants(self) -> CapabilitySpec:
        """Enforce that a Portal is never lifecycle-managed and has no activation seam.

        ADR-22 doctrine, enforced at construction: ``PORTAL ⇒ dedicated is False`` (the
        Orchestrator cannot move a runtime it does not own) and ``is_dynamic is False``.
        """
        if self.source_kind is SourceKind.PORTAL:
            if self.concurrency.dedicated:
                msg = f"Portal capability '{self.key}' must not be dedicated (lifecycle is not LychD's)."
                raise ValueError(msg)
            if self.is_dynamic:
                msg = f"Portal capability '{self.key}' cannot be dynamic (no in-runtime activation)."
                raise ValueError(msg)
        return self


class CapabilityState(BaseModel):
    """Observed live state for a synthesized capability.

    ``phase`` is the canonical field; the historical booleans are derived
    properties so existing Dispatcher/OrchestratorManager read-sites keep
    compiling while probe producers migrate to the phase model (A3-U4).
    """

    model_config = ConfigDict(extra="forbid")

    capability_key: str = Field(min_length=1)
    is_dynamic: bool
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
        return not self.is_dynamic

    @property
    def is_active(self) -> bool:
        """Whether this specific model capability is loaded or loading."""
        return self.phase in {CapabilityPhase.WARM, CapabilityPhase.WARMING}

    @property
    def runtime_started(self) -> bool:
        """Whether the owning local runtime unit is up, even with no model loaded."""
        return self.phase in {
            CapabilityPhase.ACTIVATABLE,
            CapabilityPhase.WARMING,
            CapabilityPhase.WARM,
        }

    @property
    def is_available(self) -> bool:
        return self.phase is not CapabilityPhase.ERROR


@dataclass(frozen=True, slots=True)
class ActivationResult:
    """Outcome of a runtime-native capability activation request (A3-U4 §2).

    ``accepted`` reports whether the runtime took the activation request;
    ``phase`` is the capability phase observed immediately after the request;
    ``reason`` explains a rejection (e.g. a non-dynamic capability whose
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


@dataclass(frozen=True, init=False)
class CapabilityGrant:
    """Canonical dispatch handoff for one granted capability (spec-00-FINAL C1).

    Carries only admitted live call handles while keeping the issued spec/state snapshots private.
    Accessors return defensive copies, so a consumer cannot rewrite the grant's
    capability identity or observed issue-time truth through nested mutable fields.
    """

    _spec: CapabilitySpec
    _state: CapabilityState
    _lease: GrantLease
    _generation: GenerationProfile
    _model: Model | None
    _toolsets: tuple[AbstractToolset[Any], ...]

    def __init__(
        self,
        *,
        spec: CapabilitySpec,
        state: CapabilityState,
        lease: GrantLease,
        generation: GenerationProfile,
        model: Model | None,
        toolsets: tuple[AbstractToolset[Any], ...] = (),
    ) -> None:
        """Seal detached value snapshots beside the intentionally live handles."""
        object.__setattr__(self, "_spec", spec.model_copy(deep=True))
        object.__setattr__(self, "_state", state.model_copy(deep=True))
        object.__setattr__(self, "_lease", lease)
        object.__setattr__(self, "_generation", generation.model_copy(deep=True))
        object.__setattr__(self, "_model", model)
        object.__setattr__(self, "_toolsets", tuple(toolsets))

    @property
    def spec(self) -> CapabilitySpec:
        """Return a detached copy of the issued capability declaration."""
        return self._spec.model_copy(deep=True)

    @property
    def state(self) -> CapabilityState:
        """Return a detached copy of the issue-time observation."""
        return self._state.model_copy(deep=True)

    @property
    def lease(self) -> GrantLease:
        return self._lease

    @property
    def generation(self) -> GenerationProfile:
        return self._generation

    @property
    def model(self) -> Model | None:
        return self._model

    @property
    def toolsets(self) -> tuple[AbstractToolset[Any], ...]:
        return self._toolsets

    @property
    def key(self) -> str:
        return self._spec.key

    def model_settings(self) -> ModelSettings | None:
        """Bridge the resolved generation profile to pydantic-ai ModelSettings."""
        from lychd.domain.animation.services.binder import generation_to_model_settings

        return generation_to_model_settings(self.generation)
