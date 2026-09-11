"""Native node membership cannot widen the admitted serial edge contract."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Literal, cast
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel, ValidationError
from pydantic_graph import BaseNode, End, GraphBuilder, GraphRunContext, StepContext

from lychd.domain.cortex.graph import build_serial_graph, serial_graph_topology
from lychd.domain.cortex.graph_runner import GraphRunner, NodeOccurrenceEvent
from lychd.domain.cortex.stasis import DurableStasisPhylactery, InMemoryStasisStore, NodeSnapshot


class RouteState(BaseModel):
    route: Literal["permitted", "skip", "end"] = "permitted"


@dataclass
class RouteEffects:
    visited: list[str] = field(default_factory=list)


@dataclass
class FirstRoute(BaseNode[RouteState, RouteEffects, str]):
    async def run(self, ctx: GraphRunContext[RouteState, RouteEffects]) -> SecondRoute:
        ctx.deps.visited.append("first")
        if ctx.state.route == "skip":
            # Deliberate implementation drift: membership in the graph is not
            # permission to skip the declared successor.
            return cast("SecondRoute", ThirdRoute())
        if ctx.state.route == "end":
            return cast("SecondRoute", End("unpermitted"))
        return SecondRoute()


@dataclass
class SecondRoute(BaseNode[RouteState, RouteEffects, str]):
    async def run(self, ctx: GraphRunContext[RouteState, RouteEffects]) -> ThirdRoute:
        ctx.deps.visited.append("second")
        return ThirdRoute()


@dataclass
class ThirdRoute(BaseNode[RouteState, RouteEffects, str]):
    async def run(self, ctx: GraphRunContext[RouteState, RouteEffects]) -> End[str]:
        ctx.deps.visited.append("third")
        return End("permitted")


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["skip", "end", "permitted"])
async def test_native_graph_enforces_each_declared_successor(route: Literal["skip", "end", "permitted"]) -> None:
    graph = build_serial_graph(
        nodes=(FirstRoute, SecondRoute, ThirdRoute),
        state_type=RouteState,
        deps_type=RouteEffects,
        output_type=str,
    )
    persistence = DurableStasisPhylactery(job_id="route", store=InMemoryStasisStore())
    orchestrator = AsyncMock()
    runner = GraphRunner[RouteState](orchestrator=orchestrator, persistence=persistence, signal_priority=50)
    effects = RouteEffects()

    if route == "permitted":
        result = await runner.run_graph(graph, FirstRoute(), RouteState(route=route), deps=effects)
        assert result == "permitted"
        assert effects.visited == ["first", "second", "third"]
    else:
        with pytest.raises(ValueError, match="undeclared successor"):
            await runner.run_graph(graph, FirstRoute(), RouteState(route=route), deps=effects)
        assert effects.visited == ["first"]
        snapshots = await persistence.load_all()
        assert len(snapshots) == 1
        assert isinstance(snapshots[0], NodeSnapshot)
        assert snapshots[0].status == "error"
        assert await persistence.load_next() is None
    orchestrator.handle_transition.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("resume", [False, True])
async def test_nonentry_station_requires_a_retained_cursor(*, resume: bool) -> None:
    graph = build_serial_graph(
        nodes=(FirstRoute, SecondRoute, ThirdRoute),
        state_type=RouteState,
        deps_type=RouteEffects,
        output_type=str,
    )
    persistence = DurableStasisPhylactery(job_id="entry", store=InMemoryStasisStore())
    persistence.set_graph_types(graph)
    runner = GraphRunner[RouteState](orchestrator=AsyncMock(), persistence=persistence, signal_priority=50)
    effects = RouteEffects()
    if resume:
        await persistence.snapshot_node(RouteState(), SecondRoute())
        assert await runner.resume_graph(graph, deps=effects) == "permitted"
        assert effects.visited == ["second", "third"]
    else:
        with pytest.raises(ValueError, match="declared entry station"):
            await runner.run_graph(graph, SecondRoute(), RouteState(), deps=effects)
        assert effects.visited == []
        assert await persistence.load_all() == []


@dataclass
class CallerOwnedRoute(BaseNode[RouteState, None, int]):
    invocations: int = 0

    async def run(self, ctx: GraphRunContext[RouteState, None]) -> End[int]:
        _ = ctx
        self.invocations += 1
        return End(self.invocations)


@pytest.mark.asyncio
async def test_fresh_node_preserves_caller_identity_and_initial_snapshot() -> None:
    graph = build_serial_graph(nodes=(CallerOwnedRoute,), state_type=RouteState, deps_type=type(None), output_type=int)
    persistence = DurableStasisPhylactery(job_id="caller", store=InMemoryStasisStore())
    runner = GraphRunner[RouteState](orchestrator=AsyncMock(), persistence=persistence, signal_priority=50)
    node = CallerOwnedRoute()
    assert await runner.run_graph(graph, node, RouteState()) == 1
    assert node.invocations == 1
    snapshots = await persistence.load_all()
    assert isinstance(snapshots[0], NodeSnapshot)
    assert isinstance(snapshots[0].node, CallerOwnedRoute)
    assert snapshots[0].node.invocations == 0
    assert snapshots[0].status == "success"


class TypedCompletionState(BaseModel):
    counter: int = 0
    invalid: Literal["state", "output"] | None = None


@dataclass
class TypedCompletionRoute(BaseNode[TypedCompletionState, None, int]):
    async def run(self, ctx: GraphRunContext[TypedCompletionState, None]) -> End[int]:
        if ctx.state.invalid == "state":
            # Pydantic does not validate ordinary assignment by default.
            ctx.state.counter = cast("int", "not-an-integer")
        if ctx.state.invalid == "output":
            return End(cast("int", "not-an-integer"))
        return End(1)


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["state", "output"])
async def test_invalid_completion_cannot_write_an_unreadable_checkpoint(invalid: Literal["state", "output"]) -> None:
    graph = build_serial_graph(
        nodes=(TypedCompletionRoute,), state_type=TypedCompletionState, deps_type=type(None), output_type=int
    )
    store = InMemoryStasisStore()
    persistence = DurableStasisPhylactery(job_id="invalid-completion", store=store)
    events: list[NodeOccurrenceEvent] = []
    runner = GraphRunner[TypedCompletionState](
        orchestrator=AsyncMock(), persistence=persistence, signal_priority=50, on_node_event=events.append
    )

    with pytest.raises(ValidationError, match="valid integer"):
        await runner.run_graph(graph, TypedCompletionRoute(), TypedCompletionState(invalid=invalid))

    # The prior valid history remains readable and cannot authorize replay.
    snapshots = await persistence.load_all()
    assert len(snapshots) == 1
    assert isinstance(snapshots[0], NodeSnapshot)
    assert snapshots[0].state.counter == 0
    assert await persistence.load_next() is None
    assert [event.phase for event in events] == ["entered", "failed"]


@dataclass
class TypedNodeFirst(BaseNode[RouteState, RouteEffects, int]):
    async def run(self, ctx: GraphRunContext[RouteState, RouteEffects]) -> TypedNodeLast:
        ctx.deps.visited.append("first")
        return TypedNodeLast(value=cast("int", "not-an-integer"))


@dataclass
class TypedNodeLast(BaseNode[RouteState, RouteEffects, int]):
    value: int = 1

    async def run(self, ctx: GraphRunContext[RouteState, RouteEffects]) -> End[int]:
        ctx.deps.visited.append("last")
        return End(self.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["first", "next"])
async def test_invalid_node_fields_cannot_replace_readable_history(stage: Literal["first", "next"]) -> None:
    graph = build_serial_graph(
        nodes=(TypedNodeLast,) if stage == "first" else (TypedNodeFirst, TypedNodeLast),
        state_type=RouteState,
        deps_type=RouteEffects,
        output_type=int,
    )
    start = TypedNodeLast(value=cast("int", "not-an-integer")) if stage == "first" else TypedNodeFirst()
    store = InMemoryStasisStore()
    persistence = DurableStasisPhylactery(job_id="invalid-node", store=store)
    runner = GraphRunner[RouteState](orchestrator=AsyncMock(), persistence=persistence, signal_priority=50)
    effects = RouteEffects()

    with pytest.raises(ValidationError, match="valid integer"):
        await runner.run_graph(graph, start, RouteState(), deps=effects)

    assert effects.visited == ([] if stage == "first" else ["first"])
    snapshots = await persistence.load_all()
    if stage == "first":
        assert snapshots == []
        assert await store.load("invalid-node") is None
    else:
        assert len(snapshots) == 1
        assert isinstance(snapshots[0], NodeSnapshot)
        assert isinstance(snapshots[0].node, TypedNodeFirst)
        assert snapshots[0].status == "success"
    assert await persistence.load_next() is None


@dataclass
class InternalFieldRoute(CallerOwnedRoute):
    invocations: int = field(default=0, init=False)


@dataclass
class InternalFieldEntry(BaseNode[RouteState, None, int]):
    async def run(self, ctx: GraphRunContext[RouteState, None]) -> InternalFieldRoute:
        _ = ctx
        return InternalFieldRoute()


@pytest.mark.asyncio
@pytest.mark.parametrize("retained_history", [False, True])
async def test_noninit_node_fields_refuse_before_replacing_history(*, retained_history: bool) -> None:
    graph = build_serial_graph(
        nodes=(InternalFieldEntry, InternalFieldRoute),
        state_type=RouteState,
        deps_type=type(None),
        output_type=int,
    )
    store = InMemoryStasisStore()
    persistence = DurableStasisPhylactery(job_id="internal-field", store=store)
    persistence.set_graph_types(graph)
    if retained_history:
        await persistence.snapshot_node(RouteState(), InternalFieldEntry())
    before = await store.load("internal-field")

    with pytest.raises(ValueError, match="unknown fields"):
        await persistence.snapshot_node(RouteState(), InternalFieldRoute())

    assert await store.load("internal-field") == before
    snapshots = await persistence.load_all()
    assert len(snapshots) == int(retained_history)
    if retained_history:
        assert isinstance(snapshots[0], NodeSnapshot)
        assert type(snapshots[0].node) is InternalFieldEntry
        assert snapshots[0].status == "created"


@dataclass
class ReservedNodeIdentity(BaseNode[RouteState, None, int]):
    node_id: str

    async def run(self, ctx: GraphRunContext[RouteState, None]) -> End[int]:
        _ = ctx
        pytest.fail("A node with conflicting checkpoint identity must never execute")


@dataclass
class DefaultedReservedNodeIdentity(ReservedNodeIdentity):
    node_id: str = "default-value"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "node", [ReservedNodeIdentity(node_id="operator-value"), DefaultedReservedNodeIdentity(node_id="operator-value")]
)
async def test_node_fields_cannot_collide_with_checkpoint_identity(node: BaseNode[RouteState, None, int]) -> None:
    graph = build_serial_graph(nodes=(type(node),), state_type=RouteState, deps_type=type(None), output_type=int)
    store = InMemoryStasisStore()
    persistence = DurableStasisPhylactery(job_id="reserved-node-identity", store=store)
    persistence.set_graph_types(graph)

    with pytest.raises(ValueError, match=r"reserved.*node_id"):
        await persistence.snapshot_node(RouteState(), node)

    assert await store.load("reserved-node-identity") is None
    assert await persistence.load_all() == []


def test_native_function_step_has_no_admitted_serial_checkpoint_contract() -> None:
    builder = GraphBuilder[RouteState, None, None, str](state_type=RouteState, output_type=str)

    @builder.step
    async def effect(ctx: StepContext[RouteState, None, None]) -> str:
        _ = ctx
        pytest.fail("topology admission must not execute a function step")

    builder.add(builder.edge_from(builder.start_node).to(effect), builder.edge_from(effect).to(builder.end_node))
    with pytest.raises(TypeError, match="serial BaseNode stations"):
        serial_graph_topology(builder.build())


@dataclass
class CancellationEffects:
    entered: asyncio.Event = field(default_factory=asyncio.Event)
    release: asyncio.Event = field(default_factory=asyncio.Event)
    settled: asyncio.Event = field(default_factory=asyncio.Event)
    invocations: int = 0


@dataclass
class CancellationRoute(BaseNode[RouteState, CancellationEffects, str]):
    async def run(self, ctx: GraphRunContext[RouteState, CancellationEffects]) -> End[str]:
        ctx.deps.invocations += 1
        ctx.deps.entered.set()
        try:
            await ctx.deps.release.wait()
        finally:
            ctx.deps.settled.set()
        return End("settled")


class PausedCheckpointStore(InMemoryStasisStore):
    """Stop immediately before the selected atomic in-memory replacement."""

    def __init__(self, status: str | None) -> None:
        super().__init__()
        self.status = status
        self.entered = asyncio.Event()

    async def replace(self, run_id: str, snapshots: list[Any]) -> None:
        if self.status is not None and snapshots[-1].get("status") == self.status:
            self.entered.set()
            await asyncio.Event().wait()
        await super().replace(run_id, snapshots)


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["before-body", "in-body", "after-body"])
async def test_native_cancellation_retains_only_safe_reentry(stage: str) -> None:
    graph = build_serial_graph(
        nodes=(CancellationRoute,), state_type=RouteState, deps_type=CancellationEffects, output_type=str
    )
    store = PausedCheckpointStore({"before-body": "running", "after-body": "success"}.get(stage))
    persistence = DurableStasisPhylactery(job_id="cancel", store=store)
    runner = GraphRunner[RouteState](orchestrator=AsyncMock(), persistence=persistence, signal_priority=50)
    effects = CancellationEffects()
    if stage != "in-body":
        effects.release.set()
    execution = asyncio.create_task(runner.run_graph(graph, CancellationRoute(), RouteState(), deps=effects))
    await asyncio.wait_for((effects.entered if stage == "in-body" else store.entered).wait(), timeout=1)
    execution.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(execution, timeout=1)

    snapshots = await persistence.load_all()
    assert len(snapshots) == 1
    assert isinstance(snapshots[0], NodeSnapshot)
    if stage == "before-body":
        assert effects.invocations == 0
        assert snapshots[0].status == "created"
        store.status = None
        assert await runner.resume_graph(graph, deps=effects) == "settled"
        assert effects.invocations == 1
    else:
        assert effects.invocations == 1
        assert effects.settled.is_set()  # Native child cleanup finishes before cancellation returns.
        assert snapshots[0].status == "running"
        with pytest.raises(ValueError, match="No created checkpoint"):
            await runner.resume_graph(graph, deps=effects)
        assert effects.invocations == 1
