from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
