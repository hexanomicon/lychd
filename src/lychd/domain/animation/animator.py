from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel

from lychd.extensions.protocols import (
    AnimatorProtocol,
    CapabilityProtocol,
    ReasoningCapability,
)

class Animator(AnimatorProtocol, ABC):
    """
    Abstract base for all Animator implementations.
    Provides the shared foundation for capability state tracking.
    
    This class belongs in the Core Domain as it defines the interface 
    shape for the Switchboard (Dispatcher).
    """
    
    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        self._capabilities: list[CapabilityProtocol] = []
        self._active_capability_id: str | None = None

    async def list_capabilities(self) -> list[CapabilityProtocol]:
        """
        Synchronizes internal state flags with the physical reality.
        """
        for cap in self._capabilities:
            cap.is_active = (cap.identifier == self._active_capability_id)
        return self._capabilities

    @abstractmethod
    async def activate_capability(self, capability: CapabilityProtocol) -> None:
        """The LlamaSwap hook to be implemented by concrete provider bridges."""
        ...

    @abstractmethod
    def bind_model(self, capability: ReasoningCapability) -> Any:
        """
        Materializes the abstract capability into a concrete AI model object
        (e.g., pydantic_ai.models.openai.OpenAIModel).
        """
        ...
