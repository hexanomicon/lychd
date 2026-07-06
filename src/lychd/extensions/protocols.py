from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic_graph.persistence import NodeSnapshot

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState


@runtime_checkable
class PhylacteryProtocol(Protocol):
    """Persistence contract for graph state and resumable jobs."""

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
        """Update suspended state and reset its status to ``created`` for pickup."""
        ...

    async def mark_job_resumed(self, job_id: str) -> None:
        """Finalize the rehydration ritual."""
        ...

    def set_graph_types(self, graph: Any) -> None:
        """Set graph types for serialization."""
        ...


@runtime_checkable
class ExtensionSchemaProtocol(Protocol):
    """Host-side description of the provisional external schema shape.

    Crypt source experiments do not need to import this protocol. The loader
    checks for this shape at runtime; this is not a stable public API. If this
    shape proves durable through real Forge cycles, it may be harvested into a
    v1 compatibility surface.
    """

    relative_path: Path


@runtime_checkable
class AnimatorProviderProtocol(Protocol):
    """Draft coupled-runtime provider contract for constructing animator handles."""

    def build_runtime(self, rune: Any) -> Any | None:
        """Return a runtime animator handle for a rune, or ``None`` if unsupported."""
        ...


@runtime_checkable
class CapabilityProviderProtocol(Protocol):
    """Draft coupled-runtime provider contract for synthesizing capability specs."""

    def build_capability_specs(self, rune: Any, animator: Any | None = None) -> list[CapabilitySpec]:
        """Return synthesized capability specs for a rune and optional runtime animator."""
        ...


@runtime_checkable
class LiveStateProbeProtocol(Protocol):
    """Draft coupled-runtime provider contract for returning live capability state."""

    def probe_capability_states(self, animator: Any, specs: list[CapabilitySpec]) -> list[CapabilityState]:
        """Return live state records for the provided runtime animator capability specs."""
        ...


@runtime_checkable
class CapabilityActivationProviderProtocol(Protocol):
    """Draft coupled-runtime provider contract for runtime-native activation."""

    def activate_capability(self, animator: Any, spec: CapabilitySpec) -> bool:
        """Activate one cold capability on a warm runtime when supported."""
        ...
