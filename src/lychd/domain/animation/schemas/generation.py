from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GenerationProfile(BaseModel):
    """All-optional generation overlay. The ONLY generation-param schema."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_context: int | None = Field(default=None, ge=1)
    max_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0, allow_inf_nan=False)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0, allow_inf_nan=False)

    def overlay(self, other: GenerationProfile | None) -> GenerationProfile:
        """Return self with other's non-None fields winning."""
        if other is None:
            return self
        merged = self.model_dump() | {k: v for k, v in other.model_dump().items() if v is not None}
        return GenerationProfile.model_validate(merged)
