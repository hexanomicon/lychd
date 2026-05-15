from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field, ConfigDict
from pydantic_graph.persistence import NodeSnapshot

@runtime_checkable
class CapabilityProtocol(Protocol):
    """
    A concrete functional contract bound to the Agent Graph (e.g., a specific
    Reasoning Model or a structural Tool).
    """
    identifier: str
    
    # State flags for the Dispatcher/Orchestrator
    is_static: bool  # True if baked-in and immutable. False if dynamically loaded.
    is_active: bool  # True if currently occupying VRAM/Memory in the Coven.
    
    # THE MATRIX DSL
    evict_cost: int         # Penalty for unloading this model (e.g. 50 for 70B, 10 for 8B)
    matrix_sets: list[str]  # Logical groups this model can belong to (e.g. ["coding", "vision"])

@runtime_checkable
class ReasoningCapability(CapabilityProtocol, Protocol):
    """Text reasoning models returning Pydantic objects."""
    async def reason(self, prompt: str, **kwargs: Any) -> BaseModel:
        ...

@runtime_checkable
class SensoryCapability(CapabilityProtocol, Protocol):
    """Vision/Audio perception engines handling BinaryContent."""
    async def perceive(self, content: bytes, **kwargs: Any) -> str:
        ...

@runtime_checkable
class EmbeddingCapability(CapabilityProtocol, Protocol):
    """Vectorization engines."""
    async def embed(self, text: str, **kwargs: Any) -> list[float]:
        ...

@runtime_checkable
class AnimatorProtocol(Protocol):
    """
    The software bridge residing in the Vessel, communicating with a specific 
    physical Coven boundary.
    """
    identifier: str
    
    async def list_capabilities(self) -> list[CapabilityProtocol]:
        """Returns all Capabilities this Animator could provide."""
        ...
        
    async def activate_capability(self, capability: CapabilityProtocol) -> None:
        """
        The 'LlamaSwap' mechanic. 
        If a Capability has is_static=False and is_active=False, the Orchestrator 
        invokes this method. The Animator then hits the Coven's internal API to 
        dynamically swap the model into VRAM without restarting the container.
        """
        ...

@runtime_checkable
class PhylacteryProtocol(Protocol):
    """
    The formal interface for persisting the Agent's consciousness.
    Duck-typed to align with pydantic_graph.persistence.BaseStatePersistence
    while maintaining LychD-specific job context.
    """
    job_id: str
    
    async def snapshot_node(self, state: Any, next_node: Any) -> None:
        """Commit the current state and next node to persistence."""
        ...

    async def snapshot_end(self, state: Any, end: Any) -> None:
        """Commit the final state to persistence."""
        ...

    async def load_next(self) -> NodeSnapshot[Any, Any] | None:
        """Retrieve the next 'created' snapshot for rehydration."""
        ...

    def record_run(self, snapshot_id: str) -> AbstractAsyncContextManager[None]:
        """Record the run of the node. Implementation must handle suspension signals."""
        ...

    async def rehydrate_stasis(self, state: Any, node: Any) -> None:
        """
        Updates a suspended node's state and resets its status to 'created'
        to allow the rehydration ritual to pick it up.
        """
        ...

    async def mark_job_resumed(self, job_id: str) -> None:
        """Finalizes the rehydration ritual."""
        ...

    def set_graph_types(self, graph: Any) -> None:
        """Sets types for serialization (Pydantic Graph hook)."""
        ...

@runtime_checkable
class ExtensionSchemaProtocol(Protocol):
    """
    Schema-discovery branch of the Extension Protocol.
    Allows independent organs to surface Codex-visible rune schemas without
    inheriting from mutable Core ABCs.
    """
    relative_path: str | None
    singleton: bool | None
    
    # THE MATRIX DSL
    evict_cost: int | None
    matrix_sets: list[str] | None

class MindBundle(BaseModel):
    """
    The configuration package granted by the Dispatcher to the Agent.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    animator: Any = Field(description="The selected model implementation")
    capabilities: list[CapabilityProtocol] = Field(description="Granted capabilities")
    limits: Any = Field(description="Usage limits derived from economic policy")
