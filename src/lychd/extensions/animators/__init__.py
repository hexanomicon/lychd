"""Builtin animator schema and adapter exports for extension authors."""

from lychd.extensions.builtin.animator import LlamaCppSoulstone, SglangSoulstone, VllmSoulstone
from lychd.extensions.builtin.animator.runtimes import (
    LlamaCppRuntimeAdapter,
    SglangRuntimeAdapter,
    VllmRuntimeAdapter,
)

__all__ = [
    "LlamaCppRuntimeAdapter",
    "LlamaCppSoulstone",
    "SglangRuntimeAdapter",
    "SglangSoulstone",
    "VllmRuntimeAdapter",
    "VllmSoulstone",
]
