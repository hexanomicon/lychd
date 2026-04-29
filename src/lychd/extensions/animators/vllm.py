"""Extension-facing vLLM animator primitives."""

from lychd.extensions.builtin.animator import VllmSoulstone
from lychd.extensions.builtin.animator.runtimes import VllmRuntimeAdapter

__all__ = ["VllmRuntimeAdapter", "VllmSoulstone"]
