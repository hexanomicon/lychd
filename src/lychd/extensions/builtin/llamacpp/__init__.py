from __future__ import annotations

from lychd.extensions.context import ExtensionContext
from lychd.extensions.builtin.llamacpp.relic import LlamaCppConfig, LlamaCppAnimator

__all__ = ["LlamaCppConfig", "LlamaCppAnimator", "register"]

def register(context: ExtensionContext) -> None:
    """
    Boot ritual for the llama.cpp organ.
    """
    pass
