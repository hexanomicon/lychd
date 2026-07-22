"""Narrow, structured host-runtime mutation port consumed by the Orchestrator."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Annotated, Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from lychd.domain.animation.protocols import CapabilityRegistry

__all__ = [
    "RuntimeActuator",
    "RuntimePreconditionError",
    "TransitionIntent",
    "build_compensation_intent",
    "capability_config_generation",
]

AnimatorId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")]


class RuntimePreconditionError(RuntimeError):
    """A runtime transition was declined before any new physical effect."""


class TransitionIntent(BaseModel):
    """Allowlisted physical transition expressed only in animator identities.

    It deliberately has no shell command, unit name, filesystem path, environment,
    or arbitrary payload field. Trusted actuators map these canonical identities to
    their own bounded effect surface.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    transition_id: str = Field(default_factory=lambda: uuid4().hex, pattern=r"^[0-9a-f]{32}$")
    operation: Literal["forward", "compensation"] = "forward"
    rollback_of: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    config_generation: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_animator: AnimatorId
    evict_animators: tuple[AnimatorId, ...] = ()
    launch_animators: tuple[AnimatorId, ...] = ()
    expected_active_animators: tuple[AnimatorId, ...] = ()

    @model_validator(mode="after")
    def _validate_transition_sets(self) -> TransitionIntent:
        """Reject ambiguous or internally impossible physical transition plans."""
        evict = set(self.evict_animators)
        launch = set(self.launch_animators)
        expected = set(self.expected_active_animators)
        collections = (
            ("evict_animators", self.evict_animators, evict),
            ("launch_animators", self.launch_animators, launch),
            ("expected_active_animators", self.expected_active_animators, expected),
        )
        for label, values, unique in collections:
            if len(values) != len(unique):
                msg = f"{label} must not contain duplicate animator identities."
                raise ValueError(msg)
        overlap = evict & launch
        if overlap:
            msg = f"Animators cannot be both evicted and launched: {sorted(overlap)}."
            raise ValueError(msg)
        self._validate_operation_target(evict=evict, launch=launch)
        missing = evict - expected
        if missing:
            msg = f"Evicted animators must be present in expected_active_animators: {sorted(missing)}."
            raise ValueError(msg)
        already_active = launch & expected
        if already_active:
            msg = f"Launched animators must not already be expected active: {sorted(already_active)}."
            raise ValueError(msg)
        return self

    def _validate_operation_target(self, *, evict: set[str], launch: set[str]) -> None:
        """Validate the operation-specific target and rollback reference."""
        if self.operation == "forward":
            if self.rollback_of is not None:
                msg = "A forward transition cannot reference rollback_of."
                raise ValueError(msg)
            if self.target_animator not in launch:
                msg = "target_animator must be present in launch_animators."
                raise ValueError(msg)
        else:
            if self.rollback_of is None:
                msg = "A compensation transition must reference rollback_of."
                raise ValueError(msg)
            if self.rollback_of == self.transition_id:
                msg = "A compensation transition cannot roll back itself."
                raise ValueError(msg)
            if self.target_animator not in evict:
                msg = "A compensation target_animator must be present in evict_animators."
                raise ValueError(msg)


def build_compensation_intent(intent: TransitionIntent) -> TransitionIntent:
    """Build the exact typed inverse of one completed forward transition."""
    if intent.operation != "forward":
        msg = "Only a forward transition can be compensated."
        raise ValueError(msg)
    expected_after = tuple(
        sorted((set(intent.expected_active_animators) - set(intent.evict_animators)) | set(intent.launch_animators))
    )
    return TransitionIntent(
        operation="compensation",
        rollback_of=intent.transition_id,
        config_generation=intent.config_generation,
        target_animator=intent.target_animator,
        evict_animators=intent.launch_animators,
        launch_animators=intent.evict_animators,
        expected_active_animators=expected_after,
    )


class RuntimeActuator(Protocol):
    """Apply one validated transition without exposing generic host execution."""

    async def apply(self, intent: TransitionIntent) -> None:
        """Apply an allowlisted transition intent."""
        ...


def capability_config_generation(registry: CapabilityRegistry) -> str:
    """Digest the immutable capability projection shared by Vessel and Reactor."""
    payload = [spec.model_dump(mode="json") for spec in sorted(registry.list_capabilities(), key=lambda item: item.key)]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
