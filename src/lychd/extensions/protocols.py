from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic_graph.persistence import NodeSnapshot


@runtime_checkable
class PhylacteryProtocol(Protocol):
    """Persistence contract for graph state and resumable jobs."""

    job_id: str

    async def snapshot_node(self, state: Any, next_node: Any) -> None:
        """Commit the current state and next node to persistence."""
        ...

    async def snapshot_node_if_new(self, snapshot_id: str, state: Any, next_node: Any) -> None:
        """Commit a node only when its snapshot id is not already present."""
        ...

    async def snapshot_end(self, state: Any, end: Any) -> None:
        """Commit the final state to persistence."""
        ...

    async def load_next(self) -> NodeSnapshot[Any, Any] | None:
        """Retrieve the next 'created' snapshot for rehydration."""
        ...

    async def load_all(self) -> list[Any]:
        """Load the complete snapshot history required by Pydantic Graph."""
        ...

    def record_run(self, snapshot_id: str) -> AbstractAsyncContextManager[None]:
        """Record the run of the node. Implementation must handle suspension signals."""
        ...

    async def rehydrate_stasis(self, state: Any, node: Any) -> None:
        """Update suspended state and reset its status to ``created`` for pickup."""
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
