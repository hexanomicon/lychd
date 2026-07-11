"""Stasis Phylacteries: live memory and durable database-backed graph state."""

from __future__ import annotations

import asyncio
import copy
from contextlib import asynccontextmanager, suppress
from time import perf_counter
from typing import TYPE_CHECKING, Any, Protocol

import pydantic
from pydantic_graph import exceptions
from pydantic_graph.nodes import BaseNode, End, generate_snapshot_id
from pydantic_graph.persistence import (
    BaseStatePersistence,
    EndSnapshot,
    NodeSnapshot,
    Snapshot,
    SnapshotStatus,
    build_snapshot_list_type_adapter,
)
from pydantic_graph.persistence.in_mem import FullStatePersistence

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

__all__ = [
    "DurableStasisPhylactery",
    "InMemoryStasisStore",
    "LiveStasisPhylactery",
    "StasisStore",
]


class StasisStore(Protocol):
    """Durable checkpoint document store, keyed by the authoritative run id."""

    async def load(self, run_id: str) -> list[Any] | None: ...

    async def replace(self, run_id: str, snapshots: list[Any]) -> None: ...

    async def delete(self, run_id: str) -> None: ...

    async def exists(self, run_id: str) -> bool: ...


class InMemoryStasisStore:
    """DB-free store used only by the memory profile and focused tests."""

    def __init__(self) -> None:
        """Create an empty checkpoint map."""
        self._documents: dict[str, list[Any]] = {}

    async def load(self, run_id: str) -> list[Any] | None:
        document = self._documents.get(run_id)
        return copy.deepcopy(document) if document is not None else None

    async def replace(self, run_id: str, snapshots: list[Any]) -> None:
        self._documents[run_id] = copy.deepcopy(snapshots)

    async def delete(self, run_id: str) -> None:
        self._documents.pop(run_id, None)

    async def exists(self, run_id: str) -> bool:
        return run_id in self._documents


def _refresh_snapshot_id(node: Any) -> None:
    """Assign a fresh public snapshot id before requeueing a suspended node."""
    with suppress(AttributeError):
        node.set_snapshot_id(generate_snapshot_id(node.get_node_id()))


class LiveStasisPhylactery(FullStatePersistence[Any, Any]):
    """In-memory persistence for a resident graph during ordinary hardware waits."""

    def __init__(self, *, job_id: str) -> None:
        """Bind this live persistence history to one run."""
        super().__init__()
        self.job_id = job_id

    async def rehydrate_stasis(self, state: Any, node: Any) -> None:
        _refresh_snapshot_id(node)
        await self.snapshot_node(state, node)


class DurableStasisPhylactery(BaseStatePersistence[Any, Any]):
    """One run's typed graph history persisted as a JSONB checkpoint document.

    The store is intentionally a narrow port: production supplies Postgres while
    the memory profile supplies an in-memory implementation. No control-directory
    path or filesystem checkpoint participates in durable run recovery.
    """

    def __init__(self, *, job_id: str, store: StasisStore) -> None:
        """Bind one run's checkpoint history to its durable store."""
        self.job_id = job_id
        self._store = store
        self._snapshots_type_adapter: pydantic.TypeAdapter[list[Snapshot[Any, Any]]] | None = None
        self._lock = asyncio.Lock()

    async def rehydrate_stasis(self, state: Any, node: Any) -> None:
        _refresh_snapshot_id(node)
        await self.snapshot_node(state, node)

    async def snapshot_node(self, state: Any, next_node: BaseNode[Any, Any, Any]) -> None:
        await self._append(NodeSnapshot(state=copy.deepcopy(state), node=next_node.deep_copy()))

    async def snapshot_node_if_new(self, snapshot_id: str, state: Any, next_node: BaseNode[Any, Any, Any]) -> None:
        async with self._lock:
            snapshots = await self._load()
            if not any(snapshot.id == snapshot_id for snapshot in snapshots):
                snapshots.append(NodeSnapshot(state=copy.deepcopy(state), node=next_node.deep_copy()))
                await self._save(snapshots)

    async def snapshot_end(self, state: Any, end: End[Any]) -> None:
        await self._append(EndSnapshot(state=copy.deepcopy(state), result=end.deep_copy_data()))

    @asynccontextmanager
    async def record_run(self, snapshot_id: str) -> AsyncIterator[None]:
        async with self._lock:
            snapshots = await self._load()
            snapshot = self._node_snapshot(snapshots, snapshot_id)
            exceptions.GraphNodeStatusError.check(snapshot.status)
            snapshot.status = "running"
            from pydantic_graph.persistence import _utils

            snapshot.start_ts = _utils.now_utc()
            await self._save(snapshots)
        started = perf_counter()
        try:
            yield
        except Exception:
            await self._finish(snapshot_id, perf_counter() - started, "error")
            raise
        else:
            await self._finish(snapshot_id, perf_counter() - started, "success")

    async def load_next(self) -> NodeSnapshot[Any, Any] | None:
        async with self._lock:
            snapshots = await self._load()
            snapshot = next(
                (item for item in snapshots if isinstance(item, NodeSnapshot) and item.status == "created"),
                None,
            )
            if snapshot is None:
                return None
            snapshot.status = "pending"
            await self._save(snapshots)
            return snapshot

    async def load_all(self) -> list[Snapshot[Any, Any]]:
        async with self._lock:
            return await self._load()

    def should_set_types(self) -> bool:
        return self._snapshots_type_adapter is None

    def set_types(self, state_type: type[Any], run_end_type: type[Any]) -> None:
        self._snapshots_type_adapter = build_snapshot_list_type_adapter(state_type, run_end_type)

    async def _append(self, snapshot: Snapshot[Any, Any]) -> None:
        async with self._lock:
            snapshots = await self._load()
            snapshots.append(snapshot)
            await self._save(snapshots)

    async def _finish(self, snapshot_id: str, duration: float, status: SnapshotStatus) -> None:
        async with self._lock:
            snapshots = await self._load()
            snapshot = self._node_snapshot(snapshots, snapshot_id)
            snapshot.duration = duration
            snapshot.status = status
            await self._save(snapshots)

    def _node_snapshot(self, snapshots: list[Snapshot[Any, Any]], snapshot_id: str) -> NodeSnapshot[Any, Any]:
        try:
            snapshot = next(item for item in snapshots if item.id == snapshot_id)
        except StopIteration as exc:
            msg = f"No snapshot found with id={snapshot_id!r}"
            raise LookupError(msg) from exc
        assert isinstance(snapshot, NodeSnapshot), "Only NodeSnapshot can be recorded"  # noqa: S101
        return snapshot

    async def _load(self) -> list[Snapshot[Any, Any]]:
        if self._snapshots_type_adapter is None:
            msg = "snapshot type adapter must be set"
            raise RuntimeError(msg)
        document = await self._store.load(self.job_id)
        return [] if document is None else self._snapshots_type_adapter.validate_python(document)

    async def _save(self, snapshots: list[Snapshot[Any, Any]]) -> None:
        if self._snapshots_type_adapter is None:
            msg = "snapshot type adapter must be set"
            raise RuntimeError(msg)
        await self._store.replace(self.job_id, self._snapshots_type_adapter.dump_python(snapshots, mode="json"))
