"""Embedded operator intent for a Quadlet-backed service body."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class QuadletConfig(BaseModel):
    """Minimum value object embedded by a Quadlet-backed Rune.

    The receiving Domain still owns every admitted lifecycle, resource, mount,
    secret, network, and command field. This object deliberately exposes only
    the OCI image identity that current Quadlet-backed Rune types have in common;
    it is neither a Rune, a raw Quadlet fragment, nor a deployment manifest.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    image: str = Field(..., min_length=1, description="OCI image used for this Quadlet service.")


__all__ = ["QuadletConfig"]
