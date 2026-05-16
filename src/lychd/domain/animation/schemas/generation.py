from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GenerationProfile(BaseModel):
    """Normalized generation defaults attached to a capability offer."""

    model_config = ConfigDict(extra="forbid")

    max_context: int | None = Field(default=None, ge=1)
    max_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    top_k: int | None = Field(default=None, ge=0)
    repetition_penalty: float | None = Field(default=None, ge=0.0)
    reasoning_format: str | None = None
