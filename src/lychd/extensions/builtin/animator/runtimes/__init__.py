"""Builtin runtime adapters for animator soulstones."""

from lychd.extensions.builtin.animator.runtimes.llamacpp import LlamaCppRuntimeAdapter
from lychd.extensions.builtin.animator.runtimes.sglang import SglangRuntimeAdapter
from lychd.extensions.builtin.animator.runtimes.vllm import VllmRuntimeAdapter

__all__ = [
    "LlamaCppRuntimeAdapter",
    "SglangRuntimeAdapter",
    "VllmRuntimeAdapter",
]
