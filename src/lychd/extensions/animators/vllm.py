"""Extension-facing vLLM animator primitives."""

from lychd.extensions.builtin.animator import VllmSoulstoneConfig
from lychd.extensions.builtin.animator.runtimes import VllmRuntimeAdapter

__all__ = ["VllmRuntimeAdapter", "VllmSoulstoneConfig"]
