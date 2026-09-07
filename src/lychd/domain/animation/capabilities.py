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

from lychd.domain.animation.errors import CapabilityUnavailable
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.animation.schemas.generation import GenerationProfile


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

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(min_length=1)
    animator_name: str = Field(min_length=1)
    runtime: str = Field(min_length=1)
    source_kind: SourceKind
    family: CapabilityFamily
    model_id: str = Field(min_length=1)
    # The most operationally important model fact — promoted to a real field (a metadata
    # key read by domain code must be a field). Overlaid by generation_profile.max_context.
    max_context: int | None = None
    modalities_in: tuple[str, ...] = Field(default_factory=tuple)
    supports_tools: bool | None = None
    generation_profile: GenerationProfile = Field(default_factory=GenerationProfile)
    is_dynamic: bool = False
    concurrency: ConcurrencyIntent = Field(default_factory=ConcurrencyIntent)

    def require_executable_v1_family(self) -> None:
        """Refuse metadata-only labels before readiness can request physical work.

        A supported family still requires its connector's admitted callable surface.
        """
        if self.family not in {CapabilityFamily.CHAT, CapabilityFamily.TOOL_EXECUTION}:
            raise CapabilityUnavailable(
                self.key,
                f"v1 {self.family.value} is routing metadata without an executable grant surface",
            )

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
    """Observed live state for a synthesized capability."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    capability_key: str = Field(min_length=1)
    phase: CapabilityPhase
    health: str = "unknown"
    reason: str | None = None
    checked_at: datetime | None = None

    @property
    def warm(self) -> bool:
        return self.phase is CapabilityPhase.WARM

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
    """Outcome of a runtime-native capability activation request."""

    accepted: bool
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
    """Canonical immutable dispatch handoff plus intentionally live call handles."""

    spec: CapabilitySpec
    state: CapabilityState
    lease: GrantLease
    model: Model | None
    toolsets: tuple[AbstractToolset[Any], ...] = ()

    def model_settings(self) -> ModelSettings | None:
        """Bridge the resolved generation profile to pydantic-ai ModelSettings."""
        profile = self.spec.generation_profile
        settings: ModelSettings = {}
        if profile.max_tokens is not None:
            settings["max_tokens"] = profile.max_tokens
        if profile.temperature is not None:
            settings["temperature"] = profile.temperature
        if profile.top_p is not None:
            settings["top_p"] = profile.top_p
        return settings or None
