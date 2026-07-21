"""Builtin animator schema and adapter exports for extension authors."""

from lychd.extensions.builtin.animator import (
    ExLlamaV3SoulstoneConfig,
    LlamaCppSoulstoneConfig,
    SglangSoulstoneConfig,
    VllmSoulstoneConfig,
)
from lychd.extensions.builtin.animator.runtimes import (
    ExLlamaV3RuntimeAdapter,
    LlamaCppRuntimeAdapter,
    SglangRuntimeAdapter,
    VllmRuntimeAdapter,
)

__all__ = [
    "ExLlamaV3RuntimeAdapter",
    "ExLlamaV3SoulstoneConfig",
    "LlamaCppRuntimeAdapter",
    "LlamaCppSoulstoneConfig",
    "SglangRuntimeAdapter",
    "SglangSoulstoneConfig",
    "VllmRuntimeAdapter",
    "VllmSoulstoneConfig",
]
