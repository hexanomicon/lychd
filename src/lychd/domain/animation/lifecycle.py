"""Runtime-neutral animator lifecycle DTO.

``AnimatorLifecycle`` is the domain-level generalization of the extension's
``LlamaCppLifecycle`` (A3-U2 / spec §5): the domain owns the seam type so that
``AnimatorRegistry.inspect_lifecycle`` no longer imports a concrete extension
runtime. The llama.cpp control plane returns this type directly and keeps
``LlamaCppLifecycle`` as a backwards-compatible alias.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnimatorLifecycle(BaseModel):
    """Observed runtime lifecycle state reported by an animator control plane."""

    model_config = ConfigDict(extra="forbid")

    runtime: str = "unknown"
    base_url: str
    mode: str
    health: str = "unknown"
    sleeping: bool | None = None
    supports_router: bool = False
    active_model: str | None = None
    loaded_models: list[str] = Field(default_factory=list)
    available_models: list[str] = Field(default_factory=list)
    model_capabilities: dict[str, list[str]] = Field(default_factory=dict)
    total_slots: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


__all__ = ["AnimatorLifecycle"]
