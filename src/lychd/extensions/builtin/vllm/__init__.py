from __future__ import annotations

from lychd.extensions.context import ExtensionContext
from lychd.extensions.builtin.vllm.schema import VllmRuneConfig
from lychd.extensions.builtin.vllm.animator import VllmAnimator

__all__ = ["VllmRuneConfig", "VllmAnimator", "register"]

def register(context: ExtensionContext) -> None:
    """
    The entry point called by the Vessel during the boot ritual.
    Binds this Built-in Extension to the Sovereign Core.
    """
    # Procedures to graft the vLLM logic onto the Vessel would go here.
    # Discovery of VllmRuneConfig is handled by the Crypt scan.
    pass
