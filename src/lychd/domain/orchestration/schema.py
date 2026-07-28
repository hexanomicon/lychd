from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from collections.abc import Callable


class TransitionPlan(BaseModel):
    """The formal contract for a hardware state change.

    Calculated by the transition planner to determine the physical steps
    required to manifest a capability.
    """

    total_metabolic_cost: float = Field(description="Number of animator evictions selected for the transition")
    evict_coven_ids: list[str] = Field(description="Animator ids selected for stop/eviction")
    launch_coven_ids: list[str] = Field(description="Animator ids selected for start/activation")
    action_type: Literal["HARD_SWAP", "SOFT_SWAP", "NO_OP"] = Field(
        description="The physical intensity of the transition"
    )
    policy: str = Field(default="", description="Name of the switch policy that produced this plan")
    reason: str | None = Field(default=None, description="Optional human-readable rationale for the plan")


TransitionPhase = Literal[
    "requested",
    "arbitrating",
    "draining",
    "actuating",
    "verifying",
    "compensating",
    "completed",
    "declined_no_effect",
    "failed_restored",
    "cancelled_restored",
    "contained_uncertain",
    "failed",
]


@dataclass(slots=True, kw_only=True)
class TransitionTrace:
    """Vessel-owned correlation record around a narrow physical TransitionIntent."""

    target_capability_key: str
    priority: float
    run_id: str | None = None
    occurrence_id: str | None = None
    request_id: str = field(default_factory=lambda: uuid4().hex)
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    phase: TransitionPhase = "requested"
    plan: TransitionPlan | None = None
    physical_transition_id: str | None = None
    compensation_transition_id: str | None = None
    detail: str | None = None
    observer: Callable[[TransitionTrace], None] | None = field(default=None, repr=False, compare=False)
