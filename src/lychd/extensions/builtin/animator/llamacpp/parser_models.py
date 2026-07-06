from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from lychd.domain.animation.services.adapters.catalog import ProbedModelFacts

if TYPE_CHECKING:
    from collections.abc import Sequence

_IMAGE_MARKERS = {"multimodal", "vision"}
_EMBEDDING_MARKERS = {"embedding", "embeddings"}
_RERANK_MARKERS = {"rerank", "reranking"}


def facts_from_markers(markers: Sequence[str]) -> ProbedModelFacts:
    """Translate llama.cpp ``/models`` capability markers into probe facts.

    Tolerance-first (design risk 1): unknown/absent markers never raise. ``audio``
    is an admission modality only — it NEVER becomes a family (two-axis law).
    """
    modalities_in: list[str] = []
    embedding = False
    rerank = False
    for marker in markers:
        normalized = marker.strip().lower()
        if normalized in _IMAGE_MARKERS:
            if "image" not in modalities_in:
                modalities_in.append("image")
        elif normalized == "audio":
            if "audio" not in modalities_in:
                modalities_in.append("audio")
        elif normalized in _EMBEDDING_MARKERS:
            embedding = True
        elif normalized in _RERANK_MARKERS:
            rerank = True
        # completion / absent / unknown markers are ignored.
    return ProbedModelFacts(modalities_in=tuple(modalities_in), embedding=embedding, rerank=rerank)


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
    "facts_from_markers",
]
