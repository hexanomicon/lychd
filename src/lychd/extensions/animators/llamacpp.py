"""Extension-facing llama.cpp animator primitives."""

from lychd.extensions.builtin.animator import LlamaCppSoulstone
from lychd.extensions.builtin.animator.runtimes import LlamaCppRuntimeAdapter

__all__ = ["LlamaCppRuntimeAdapter", "LlamaCppSoulstone"]
