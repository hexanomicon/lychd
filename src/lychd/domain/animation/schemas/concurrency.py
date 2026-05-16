from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ConcurrencyIntent(BaseModel):
    """Orchestration-facing coexistence and lifecycle hints."""

    model_config = ConfigDict(extra="forbid")

    matrix_sets: list[str] = Field(
        default_factory=list,
        description="Coexistence sets used by transition planning.",
    )
    evict_cost: int = Field(
        default=1,
        ge=0,
        description="Relative cost of evicting this capability's animator.",
    )
    dedicated: bool = Field(
        default=True,
        description="Whether LychD owns this animator's lifecycle and may stop or start it.",
    )
    persistent_resident: bool = Field(
        default=False,
        description="Whether this capability should stay out of the default eviction set when possible.",
    )
