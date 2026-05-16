from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TransitionPlan(BaseModel):
    """The formal contract for a hardware state change.

    Calculated by the Matrix Solver to determine the metabolic cost and
    physical steps required to manifest a capability.
    """

    total_metabolic_cost: float = Field(description="Sum of eviction costs for the selected transition")
    evict_coven_ids: list[str] = Field(description="Animator ids selected for stop/eviction")
    launch_coven_ids: list[str] = Field(description="Animator ids selected for start/activation")
    action_type: Literal["HARD_SWAP", "SOFT_SWAP", "NO_OP"] = Field(
        description="The physical intensity of the transition"
    )
