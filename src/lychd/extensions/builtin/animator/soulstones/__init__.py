"""Builtin animator soulstone schemas."""

from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppMode, LlamaCppSoulstoneConfig
from lychd.extensions.builtin.animator.soulstones.sglang import SglangSoulstoneConfig
from lychd.extensions.builtin.animator.soulstones.vllm import VllmSoulstoneConfig

__all__ = [
    "LlamaCppMode",
    "LlamaCppSoulstoneConfig",
    "SglangSoulstoneConfig",
    "VllmSoulstoneConfig",
]
