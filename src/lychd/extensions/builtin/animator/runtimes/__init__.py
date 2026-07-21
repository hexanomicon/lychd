"""Builtin runtime adapters for animator soulstones."""

from lychd.extensions.builtin.animator.runtimes.exllamav3 import ExLlamaV3RuntimeAdapter
from lychd.extensions.builtin.animator.runtimes.llamacpp import LlamaCppRuntimeAdapter
from lychd.extensions.builtin.animator.runtimes.sglang import SglangRuntimeAdapter
from lychd.extensions.builtin.animator.runtimes.vllm import VllmRuntimeAdapter

__all__ = [
    "ExLlamaV3RuntimeAdapter",
    "LlamaCppRuntimeAdapter",
    "SglangRuntimeAdapter",
    "VllmRuntimeAdapter",
]
