"""Builtin runtime adapters for animator soulstones."""

from lychd.extensions.builtin.animator.runtimes.exllamav3 import ExLlamaV3RuntimeAdapter
from lychd.extensions.builtin.animator.runtimes.llamacpp import LlamaCppRuntimeAdapter

__all__ = [
    "ExLlamaV3RuntimeAdapter",
    "LlamaCppRuntimeAdapter",
]
