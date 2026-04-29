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
    n_parallel: int | None = None
    n_predict: int | None = None
    temperature: float | None = None
    top_k: int | None = None
    top_p: float | None = None
    min_p: float | None = None
    reasoning_format: str | None = None
    source: str | None = None


@dataclass(slots=True)
class LlamaCppPresetDefaults:
    """Known llama.cpp defaults extracted from a preset file."""

    values: dict[str, object]
    model_section: str | None = None


@dataclass(slots=True)
class LlamaCppPresetDocument:
    """Parsed preset file plus load status."""

    path: Path
    sections: dict[str, dict[str, str]]
    error: Literal["missing", "read_error"] | None = None


__all__ = [
    "LlamaCppPresetDefaults",
    "LlamaCppPresetDocument",
    "LlamaCppRuntimeInference",
]
