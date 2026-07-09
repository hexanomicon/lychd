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

    @property
    def requires_model(self) -> bool:
        """Whether a grant of this family must carry a hydrated model.

        Every family but TOOL_EXECUTION is model-bearing; ``model=None`` on a grant then
        means exactly one thing — a tool-only capability — never a silent hydration failure.
        """
        return self is not CapabilityFamily.TOOL_EXECUTION
