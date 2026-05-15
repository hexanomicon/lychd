from __future__ import annotations

import httpx
from pathlib import Path
from typing import ClassVar, Any, Optional
from pydantic import BaseModel, Field
from pydantic_ai.models.openai import OpenAIModel

from lychd.domain.animation.animator import Animator
from lychd.extensions.protocols import ReasoningCapability, CapabilityProtocol
from lychd.extensions.context import ExtensionContext

# 1. THE SCHEMA (The Codex Paradox Resolution)
class LlamaCppConfig(BaseModel):
    """
    Configuration schema for llama.cpp Animator instances.
    Supports the 'Magus Heritage' by allowing external .ini presets.
    """
    # Schema attributes for the Extension Protocol discovery branch
    relative_path: ClassVar[str] = "animator/soulstones"
    singleton: ClassVar[bool] = False 
    
    # Instance fields
    base_url: str = Field(
        default="http://localhost:8080",
        description="The internal network URL of the llama-server Coven (Container)."
    )
    api_key: str = Field(
        default="llama-local-auth",
        description="The access token required by the llama-server instance."
    )
    
    # THE MAGUS HERITAGE: Accepting existing optimized presets
    preset_path: Optional[Path] = Field(
        default=None,
        description="Path to a llama-server --models-preset .ini file. If provided, LychD respects the Magus's external config."
    )
    
    # THE COVEN ALLIANCE
    always_on: bool = Field(
        default=False,
        description="If True, this Coven coexists in VRAM and bypasses the Systemd Hard Swap (Conflicts=) protocol."
    )

# 2. THE CONCRETE BRIDGE (The Relic)
class LlamaCppAnimator(Animator):
    """
    The physical bridge for llama.cpp/llama-server containers.
    Implements the 'LlamaSwap Masterstroke' dialect for router-mode engines.
    """
    
    def __init__(self, identifier: str, config: LlamaCppConfig) -> None:
        """
        :param identifier: The stable name of this animator instance.
        :param config: The hydrated configuration from the Codex.
        """
        super().__init__(identifier)
        self.config = config

    async def activate_capability(self, capability: CapabilityProtocol) -> None:
        """
        The LlamaSwap Masterstroke: llama-server Implementation (Soft Swap).
        Commands the router-mode engine to load/swap weights via the native /models/load API.
        """
        if capability.is_active:
            return

        async with httpx.AsyncClient() as client:
            # THE MASTERSTROKE: Direct HTTP-based model swapping
            # This allows the llama-server to manage its own memory arenas internally.
            response = await client.post(
                f"{self.config.base_url}/models/load",
                json={"model": capability.identifier},
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=300.0  # Weight loading can be synchronous and heavy
            )
            response.raise_for_status()
            
        self._active_capability_id = capability.identifier
        capability.is_active = True

    def bind_model(self, capability: ReasoningCapability) -> OpenAIModel:
        """
        Materializes the abstract capability into a concrete Pydantic AI OpenAIModel.
        Configures the client to route through the llama-server's local API.
        """
        return OpenAIModel(
            model_name=capability.identifier,
            base_url=f"{self.config.base_url}/v1",
            api_key=self.config.api_key
        )

# 3. THE HOOK
def register(context: ExtensionContext) -> None:
    """
    The entry point called by the Vessel during the boot ritual.
    Binds the llama.cpp Relic to the Sovereign Core.
    """
    # Registry and schema discovery happen automatically during the Crypt scan.
    pass
