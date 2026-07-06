from __future__ import annotations

from typing import ClassVar

from lychd.domain.animation.schemas import SoulstoneConfig
from lychd.domain.animation.services.adapters.runtimes.openai_compat import OpenAICompatibleRuntimeAdapter
from lychd.extensions.builtin.animator.soulstones import VllmSoulstoneConfig


class VllmRuntimeAdapter(OpenAICompatibleRuntimeAdapter):
    """vLLM adapter: exec-passthrough OpenAI-compatible runtime (FIXED lifecycle).

    All shared planning/probe/activation lives in
    ``OpenAICompatibleRuntimeAdapter``; the operator's ``exec`` list is
    authoritative and framework flags are never re-typed here.
    """

    runtime: ClassVar[str] = "vllm"
    config_type: ClassVar[type[SoulstoneConfig]] = VllmSoulstoneConfig


__all__ = ["VllmRuntimeAdapter"]
