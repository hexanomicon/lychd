"""Shared schema helpers/enums for the animation domain.

These values are reused by rune schemas and DTO schemas. They are not runtime
animator/connector contracts.
"""

from __future__ import annotations

from enum import StrEnum


def is_placeholder(value: str | None) -> bool:
    if value is None:
        return False
    return value.startswith(("<required:", "<optional:"))


class ModelFormat(StrEnum):
    """Physical representation of model weights."""

    GGUF = "GGUF"
    AWQ = "AWQ"
    GPTQ = "GPTQ"
    EXL2 = "EXL2"
    RAW = "RAW"
    OTHER = "OTHER"
