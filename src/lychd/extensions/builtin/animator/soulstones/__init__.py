"""Builtin animator soulstone schemas."""

from lychd.extensions.builtin.animator.soulstones.llamacpp import LlamaCppMode, LlamaCppSoulstone
from lychd.extensions.builtin.animator.soulstones.sglang import SglangSoulstone
from lychd.extensions.builtin.animator.soulstones.vllm import VllmSoulstone

__all__ = [
    "LlamaCppMode",
    "LlamaCppSoulstone",
    "SglangSoulstone",
    "VllmSoulstone",
]
