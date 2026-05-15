from __future__ import annotations

import httpx
from typing import Any
from pydantic_ai.models.openai import OpenAIModel

from lychd.domain.animation.animator import Animator
from lychd.extensions.protocols import ReasoningCapability, CapabilityProtocol
from lychd.extensions.builtin.vllm.schema import VllmRuneConfig

class VllmAnimator(Animator):
    """
    The physical bridge residing in the Vessel that speaks to a vLLM Coven.
    Implements the vendor-specific LlamaSwap dialect.
    """
    
    def __init__(self, identifier: str, config: VllmRuneConfig) -> None:
        """
        :param identifier: The stable name of this animator instance (from the TOML filename).
        :param config: The hydrated configuration from the Codex.
        """
        super().__init__(identifier)
        self.config = config

    async def activate_capability(self, capability: CapabilityProtocol) -> None:
        """
        The LlamaSwap Mechanic: vLLM Implementation.
        Hot-swaps model weights in VRAM without restarting the container.
        """
        if capability.is_active:
            return

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.config.base_url}/v1/models/load",
                json={"model": capability.identifier},
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=300.0
            )
            response.raise_for_status()
            
        self._active_capability_id = capability.identifier
        capability.is_active = True

    def bind_model(self, capability: ReasoningCapability) -> OpenAIModel:
        """
        Binds the abstract capability to a concrete Pydantic AI OpenAIModel.
        """
        return OpenAIModel(
            model_name=capability.identifier,
            base_url=f"{self.config.base_url}/v1",
            api_key=self.config.api_key
        )
