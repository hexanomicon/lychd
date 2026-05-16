from __future__ import annotations

from enum import StrEnum


class CapabilityFamily(StrEnum):
    """Stable semantic family labels for routable runtime capabilities."""

    CHAT = "chat"
    VISION = "vision"
    EMBEDDING = "embedding"
    STT = "stt"
    TTS = "tts"
    TOOL_EXECUTION = "tool_execution"
    RERANK = "rerank"
