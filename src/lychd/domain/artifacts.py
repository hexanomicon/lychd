"""Shared immutable references to artifacts stored outside run/checkpoint records."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ArtifactRef"]


class ArtifactRef(BaseModel):
    """Immutable metadata for a blob stored outside the owning domain record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str = Field(min_length=1)
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    media_type: str = Field(min_length=1)
    size: int = Field(ge=0)
    classification: Literal["public", "internal", "private", "restricted"] = "private"
