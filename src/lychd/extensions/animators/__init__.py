"""Builtin animator schema and adapter exports for extension authors."""

from lychd.extensions.builtin.animator import LlamaCppSoulstoneConfig, SglangSoulstoneConfig, VllmSoulstoneConfig
from lychd.extensions.builtin.animator.runtimes import (
    LlamaCppRuntimeAdapter,
    SglangRuntimeAdapter,
    VllmRuntimeAdapter,
)

__all__ = [
    "LlamaCppRuntimeAdapter",
    "LlamaCppSoulstoneConfig",
    "SglangRuntimeAdapter",
    "SglangSoulstoneConfig",
    "VllmRuntimeAdapter",
    "VllmSoulstoneConfig",
]
