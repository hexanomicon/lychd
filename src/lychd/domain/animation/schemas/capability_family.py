from __future__ import annotations

from enum import StrEnum


class CapabilityFamily(StrEnum):
    """Closed v1 compatibility labels for model-shaped capability routing."""

    CHAT = "chat"
    VISION = "vision"
    EMBEDDING = "embedding"
    STT = "stt"
    TTS = "tts"
    TOOL_EXECUTION = "tool_execution"
    RERANK = "rerank"
