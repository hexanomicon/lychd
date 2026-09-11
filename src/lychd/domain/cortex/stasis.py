"""LychD-owned typed checkpoints around native Pydantic builder execution.

The wire envelope retains the supported v1 snapshot fields so pinned parked Runs
can be decoded against their exact graph's node allowlist and state/output types.
No dependency objects or builder task/fork state are serialized.
"""

from __future__ import annotations

import asyncio
import copy
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast, runtime_checkable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from pydantic_graph import BaseNode, End, Graph

from lychd.domain.cortex.graph import serial_graph_topology

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

__all__ = [
    "DurableStasisPhylactery",
    "EndSnapshot",
    "InMemoryStasisStore",
    "LiveStasisPhylactery",
    "NodeSnapshot",
    "PhylacteryProtocol",
    "Snapshot",
    "StasisStore",
]

type SnapshotStatus = Literal["created", "pending", "running", "success", "error"]


@dataclass(kw_only=True)
class NodeSnapshot[StateT, OutputT]:
    """One serial station cursor and its execution status, owned by the Run."""

    state: StateT
    node: BaseNode[StateT, Any, OutputT]
    id: str
    status: SnapshotStatus = "created"
    start_ts: datetime | None = None
    duration: float | None = None


@dataclass(kw_only=True)
class EndSnapshot[StateT, OutputT]:
    """A recorded graph result; the caller still owns terminal Run settlement."""

    state: StateT
    result: End[OutputT]
    id: str
    ts: datetime


type Snapshot[StateT, OutputT] = NodeSnapshot[StateT, OutputT] | EndSnapshot[StateT, OutputT]


class _NodeDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["node"]
    id: str = Field(min_length=1)
    state: Any
    node: dict[str, Any]
    status: SnapshotStatus
    start_ts: datetime | None
    duration: float | None = Field(ge=0)


class _EndDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["end"]
    id: str = Field(min_length=1)
    state: Any
    result: dict[str, Any]
    ts: datetime


@runtime_checkable
class PhylacteryProtocol(Protocol):
    """Run-owned serial checkpoint custody, independent of Pydantic's scheduler."""

    job_id: str

    async def snapshot_node(self, state: Any, next_node: BaseNode[Any, Any, Any]) -> NodeSnapshot[Any, Any]: ...
    async def snapshot_end(self, state: Any, end: End[Any]) -> None: ...
    async def load_next(self) -> NodeSnapshot[Any, Any] | None: ...
    async def load_all(self) -> list[Snapshot[Any, Any]]: ...
    def record_run(self, snapshot_id: str) -> AbstractAsyncContextManager[None]: ...
    async def rehydrate_stasis(self, state: Any, node: BaseNode[Any, Any, Any]) -> None: ...
    def set_graph_types(self, graph: Graph[Any, Any, Any, Any]) -> None: ...


class StasisStore(Protocol):
    """Durable checkpoint document store, keyed by the authoritative run id."""

    async def load(self, run_id: str) -> list[Any] | None: ...
    async def replace(self, run_id: str, snapshots: list[Any]) -> None: ...
    async def delete(self, run_id: str) -> None: ...
    async def exists(self, run_id: str) -> bool: ...


class InMemoryStasisStore:
    """DB-free store used only by the memory profile and focused tests."""

    def __init__(self) -> None:
        """Create an empty process-local document map."""
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


def _validate_node_fields(node_id: str, node_type: type[BaseNode[Any, Any, Any]], values: dict[str, Any]) -> None:
    """Keep restorable constructor fields separate from envelope identity."""
    allowed = {item.name for item in fields(node_type) if item.init} if is_dataclass(node_type) else set[str]()
    if "node_id" in allowed:
        msg = f"Checkpoint node {node_id!r} declares reserved field 'node_id'."
        raise ValueError(msg)
    if values.keys() - allowed:
        msg = f"Checkpoint node {node_id!r} has unknown fields."
        raise ValueError(msg)


class DurableStasisPhylactery:
    """One Run's typed serial history, retained in a complete JSONB document.

    Decode uses only the already resolved graph's node classes. The decoder never
    imports a class named by stored data and never makes a running/error snapshot
    replayable. The worker separately validates the pinned Pattern and wait owner.
    """

    def __init__(self, *, job_id: str, store: StasisStore) -> None:
        """Bind checkpoint writes and reads to one authoritative Run id."""
        self.job_id = job_id
        self._store = store
        self._state_adapter: TypeAdapter[Any] | None = None
        self._output_adapter: TypeAdapter[Any] | None = None
        self._nodes: dict[str, type[BaseNode[Any, Any, Any]]] = {}
        self._node_adapters: dict[str, TypeAdapter[Any]] = {}
        self._lock = asyncio.Lock()

    def set_graph_types(self, graph: Graph[Any, Any, Any, Any]) -> None:
        """Bind decoding to one admitted native graph's exact types and node catalog."""
        self._nodes, _ = serial_graph_topology(graph)
        self._state_adapter = TypeAdapter(graph.state_type)
        self._output_adapter = TypeAdapter(graph.output_type)
        self._node_adapters = {
            key: TypeAdapter(node_type) for key, node_type in self._nodes.items() if is_dataclass(node_type)
        }

    async def rehydrate_stasis(self, state: Any, node: BaseNode[Any, Any, Any]) -> None:
        await self.snapshot_node(state, node)

    async def snapshot_node(self, state: Any, next_node: BaseNode[Any, Any, Any]) -> NodeSnapshot[Any, Any]:
        snapshot = NodeSnapshot(
            state=copy.deepcopy(state), node=copy.deepcopy(next_node), id=f"{next_node.get_node_id()}:{uuid4().hex}"
        )
        async with self._lock:
            snapshots = await self._load()
            snapshots.append(snapshot)
            await self._save(snapshots)
        return snapshot

    async def snapshot_end(self, state: Any, end: End[Any]) -> None:
        async with self._lock:
            snapshots = await self._load()
            snapshots.append(
                EndSnapshot(
                    state=copy.deepcopy(state), result=copy.deepcopy(end), id=f"end:{uuid4().hex}", ts=datetime.now(UTC)
                )
            )
            await self._save(snapshots)

    @asynccontextmanager
    async def record_run(self, snapshot_id: str) -> AsyncGenerator[None]:
        async with self._lock:
            snapshots = await self._load()
            snapshot = self._node_snapshot(snapshots, snapshot_id)
            if snapshot.status not in {"created", "pending"}:
                msg = f"Snapshot {snapshot_id!r} cannot execute from status {snapshot.status!r}."
                raise ValueError(msg)
            snapshot.status = "running"
            snapshot.start_ts = datetime.now(UTC)
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
            created = [item for item in snapshots if isinstance(item, NodeSnapshot) and item.status == "created"]
            if len(created) > 1:
                msg = "A serial checkpoint cannot contain multiple resumable stations."
                raise ValueError(msg)
            if not created:
                return None
            snapshot = created[0]
            snapshot.status = "pending"
            await self._save(snapshots)
            return snapshot

    async def load_all(self) -> list[Snapshot[Any, Any]]:
        async with self._lock:
            return await self._load()

    async def _finish(self, snapshot_id: str, duration: float, status: SnapshotStatus) -> None:
        async with self._lock:
            snapshots = await self._load()
            snapshot = self._node_snapshot(snapshots, snapshot_id)
            snapshot.duration = duration
            snapshot.status = status
            await self._save(snapshots)

    def _node_snapshot(self, snapshots: list[Snapshot[Any, Any]], snapshot_id: str) -> NodeSnapshot[Any, Any]:
        snapshot = next((item for item in snapshots if item.id == snapshot_id), None)
        if snapshot is None:
            msg = f"No node snapshot found with id={snapshot_id!r}."
            raise LookupError(msg)
        if not isinstance(snapshot, NodeSnapshot):
            msg = "A terminal checkpoint cannot execute as a station."
            raise TypeError(msg)
        return snapshot

    async def _load(self) -> list[Snapshot[Any, Any]]:
        if self._state_adapter is None or self._output_adapter is None:
            msg = "snapshot graph types must be set"
            raise RuntimeError(msg)
        documents = await self._store.load(self.job_id)
        snapshots: list[Snapshot[Any, Any]] = []
        for raw in documents or ():
            if not isinstance(raw, dict):
                msg = "Checkpoint snapshots must be objects."
                raise TypeError(msg)
            raw = cast("dict[str, Any]", raw)
            if raw.get("kind") == "node":
                document = _NodeDocument.model_validate(raw)
                node_id = document.node.get("node_id")
                if not isinstance(node_id, str) or node_id not in self._nodes:
                    msg = f"Checkpoint node {node_id!r} is not in its admitted graph."
                    raise ValueError(msg)
                node_type = self._nodes[node_id]
                values = {key: value for key, value in document.node.items() if key != "node_id"}
                _validate_node_fields(node_id, node_type, values)
                adapter = self._node_adapters.get(node_id)
                node = adapter.validate_python(values) if adapter is not None else node_type()
                snapshots.append(
                    NodeSnapshot(
                        state=self._state_adapter.validate_python(document.state),
                        node=node,
                        id=document.id,
                        status=document.status,
                        start_ts=document.start_ts,
                        duration=document.duration,
                    )
                )
            else:
                terminal = _EndDocument.model_validate(raw)
                if terminal.result.keys() != {"data"}:
                    msg = "Checkpoint terminal result must contain exactly its data."
                    raise ValueError(msg)
                snapshots.append(
                    EndSnapshot(
                        state=self._state_adapter.validate_python(terminal.state),
                        result=End(self._output_adapter.validate_python(terminal.result["data"])),
                        id=terminal.id,
                        ts=terminal.ts,
                    )
                )
        if len({snapshot.id for snapshot in snapshots}) != len(snapshots):
            msg = "Checkpoint snapshot ids must be unique."
            raise ValueError(msg)
        return snapshots

    async def _save(self, snapshots: list[Snapshot[Any, Any]]) -> None:
        """Validate serialized state, nodes, and output before replacing retained history."""
        if self._state_adapter is None or self._output_adapter is None:
            msg = "snapshot graph types must be set"
            raise RuntimeError(msg)
        documents: list[dict[str, Any]] = []
        for snapshot in snapshots:
            state = self._state_adapter.dump_python(snapshot.state, mode="json")
            self._state_adapter.validate_python(state)
            if isinstance(snapshot, NodeSnapshot):
                node_id = snapshot.node.get_node_id()
                if self._nodes.get(node_id) is not type(snapshot.node):
                    msg = f"Checkpoint node {node_id!r} is not in its admitted graph."
                    raise ValueError(msg)
                adapter = self._node_adapters.get(node_id)
                values = cast("dict[str, Any]", adapter.dump_python(snapshot.node, mode="json")) if adapter else {}
                _validate_node_fields(node_id, type(snapshot.node), values)
                if adapter is not None:
                    adapter.validate_python(values)
                documents.append(
                    _NodeDocument(
                        kind="node",
                        id=snapshot.id,
                        state=state,
                        node={**values, "node_id": node_id},
                        status=snapshot.status,
                        start_ts=snapshot.start_ts,
                        duration=snapshot.duration,
                    ).model_dump(mode="json")
                )
            else:
                output = self._output_adapter.dump_python(snapshot.result.data, mode="json")
                self._output_adapter.validate_python(output)
                documents.append(
                    _EndDocument(
                        kind="end",
                        id=snapshot.id,
                        state=state,
                        result={"data": output},
                        ts=snapshot.ts,
                    ).model_dump(mode="json")
                )
        await self._store.replace(self.job_id, documents)


class LiveStasisPhylactery(DurableStasisPhylactery):
    """The same serial codec backed by private memory for a resident hardware wait."""

    def __init__(self, *, job_id: str) -> None:
        """Keep the Run's serial checkpoints within this resident process."""
        super().__init__(job_id=job_id, store=InMemoryStasisStore())
