from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ConcurrencyIntent(BaseModel):
    """Orchestration-facing lifecycle hints."""

    model_config = ConfigDict(extra="forbid")

    dedicated: bool = Field(
        default=True,
        description="Whether LychD owns this animator's lifecycle and may stop or start it.",
    )
    persistent_resident: bool = Field(
        default=False,
        description="Whether this capability should stay out of the default eviction set when possible.",
    )
