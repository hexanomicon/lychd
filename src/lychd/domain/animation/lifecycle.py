"""Runtime-neutral animator lifecycle DTO.

The domain owns this seam so runtime registry code does not import a concrete
extension control-plane type.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AnimatorLifecycle:
    """Observed runtime lifecycle state reported by an animator control plane."""

    health: str = "unknown"
    supports_router: bool = False
    active_model: str | None = None
    loaded_models: list[str] = field(default_factory=list)
    loading_models: list[str] = field(default_factory=list)
    unloaded_models: list[str] = field(default_factory=list)
    available_models: list[str] = field(default_factory=list)
    pending_model: str | None = None
    error: str | None = None


__all__ = ["AnimatorLifecycle"]
