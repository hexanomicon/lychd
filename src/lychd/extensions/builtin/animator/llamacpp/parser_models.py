from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(slots=True)
class LlamaCppRuntimeInference:
    """Best-effort runtime metadata inferred from command/env inputs."""

    mode: Literal["single", "router"] | None = None
    model_provider: str | None = None
    model_path: str | None = None
    models_dir: str | None = None
    models_preset: str | None = None
    n_ctx: int | None = None
    n_predict: int | None = None
    temperature: float | None = None
    top_p: float | None = None


@dataclass(slots=True)
class LlamaCppPresetDocument:
    """Parsed preset file plus load status."""

    path: Path
    sections: dict[str, dict[str, str]]
    error: Literal["missing", "read_error"] | None = None


__all__ = [
    "LlamaCppPresetDocument",
    "LlamaCppRuntimeInference",
]
