from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import BaseModel
from pydantic_graph import BaseNode, End, FullStatePersistence, Graph, GraphRunContext
from pydantic_graph.persistence import NodeSnapshot

from lychd.domain.animation.capabilities import (
    CapabilityGrant,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    GrantLease,
    SourceKind,
)
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.cortex.dispatcher import Dispatcher, HardwareTransitionRequired
from lychd.domain.cortex.graph_runner import GraphRunner
from lychd.domain.cortex.leases import LeaseLedger


class MockState(BaseModel):
    data: str = "initial"
    warm: bool = False


MOCK_SPEC = CapabilitySpec(
    key="mock-anim:chat:mock-cap",
    animator_name="mock-anim",
    runtime="llamacpp",
    source_kind=SourceKind.SOULSTONE,
    family=CapabilityFamily.CHAT,
    model_id="mock-cap",
)


@dataclass
class MockNode(BaseNode[MockState, None, str]):
    """Terminal node used to verify persistence resume."""

    async def run(self, ctx: GraphRunContext[MockState, None]) -> End[str]:
        _ = ctx
        return End("done")


@dataclass
class SuccessNode(BaseNode[MockState, None, str]):
    """Terminal node used after stasis rehydration."""

    async def run(self, ctx: GraphRunContext[MockState, None]) -> End[str]:
        _ = ctx
        return End("victory")


@dataclass
class StasisNode(BaseNode[MockState, None, str]):
    """Node that raises one hardware transition before completing."""

    async def run(self, ctx: GraphRunContext[MockState, None]) -> SuccessNode:
        if not ctx.state.warm:
            ctx.state.warm = True
            raise HardwareTransitionRequired(MOCK_SPEC.key, MOCK_SPEC.animator_name)
        return SuccessNode()


@dataclass
class LeaseAfterDrainRaceNode(BaseNode[MockState, Dispatcher, str]):
    """Acquire through the real Dispatcher after its first issue loses admission."""

    async def run(self, ctx: GraphRunContext[MockState, Dispatcher]) -> End[str]:
        async with ctx.deps.lease_grant_key(MOCK_SPEC.key, holder="run:dispatch-race"):
            return End("leased")


class DrainRaceRegistry:
    """Hold the first async grant issue across an Orchestrator drain barrier."""

    def __init__(self) -> None:
        self.state = CapabilityState(
            capability_key=MOCK_SPEC.key,
            is_dynamic=False,
            phase=CapabilityPhase.WARM,
        )
        self.issue_started = asyncio.Event()
        self.finish_first_issue = asyncio.Event()
        self.issue_count = 0

    def get_capability(self, key: str) -> CapabilitySpec | None:
        return MOCK_SPEC if key == MOCK_SPEC.key else None

    def get_capability_state(self, key: str) -> CapabilityState | None:
        return self.state if key == MOCK_SPEC.key else None

    def get_runtime(self, _name: str) -> None:
        return None

    async def refresh_capability_state(self, key: str) -> CapabilityState | None:
        return self.get_capability_state(key)

    async def issue_grant(
        self,
        key: str,
        *,
        holder: str,
        scope: Literal["step", "run"] = "step",
    ) -> CapabilityGrant:
        assert key == MOCK_SPEC.key
        self.issue_count += 1
        if self.issue_count == 1:
            self.issue_started.set()
            await self.finish_first_issue.wait()
        return CapabilityGrant(
            spec=MOCK_SPEC,
            state=self.state,
            lease=GrantLease(
                grant_id=uuid4().hex,
                holder=holder,
                issued_at=datetime.now(UTC),
                scope=scope,
            ),
            generation=MOCK_SPEC.generation_profile,
            model=None,
        )


class ReopenAdmissionOrchestrator:
    """Finish the competing drain so GraphRunner can retry the parked node."""

    def __init__(self, leases: LeaseLedger) -> None:
        self.leases = leases
        self.calls: list[str] = []

    async def handle_transition(
        self,
        exception: HardwareTransitionRequired,
        signal_priority: float,
        **_kwargs: Any,
    ) -> None:
        _ = signal_priority
        self.calls.append(exception.capability_key)
        self.leases.end_drain([exception.animator_name])


class LychDTestPersistence(FullStatePersistence[MockState, str]):
    """Full in-memory persistence plus the LychD rehydration hooks."""

    def __init__(self) -> None:
        super().__init__()
        self.job_id = "test-job"
        self.mark_job_resumed_mock = AsyncMock()

    async def rehydrate_stasis(self, state: MockState, node: BaseNode[MockState, Any, str]) -> None:
        snapshot_id = node.get_snapshot_id()
        for snapshot in self.history:
            if isinstance(snapshot, NodeSnapshot) and snapshot.id == snapshot_id:
                snapshot.state = copy.deepcopy(state)
                snapshot.status = "created"
                return

        await self.snapshot_node(state, node)

    async def mark_job_resumed(self, job_id: str) -> None:
        await self.mark_job_resumed_mock(job_id)


class FailingStasisPersistence(LychDTestPersistence):
    """Reject checkpoint writes so evidence cannot claim a completed park."""

    async def rehydrate_stasis(self, state: MockState, node: BaseNode[MockState, Any, str]) -> None:
        _ = (state, node)
        raise _CheckpointUnavailableError


class _CheckpointUnavailableError(RuntimeError):
    """Sentinel for a rejected stasis write."""


class SimpleMockOrchestrator:
    def __init__(self) -> None:
        self.handle_transition_mock = AsyncMock()

    async def handle_transition(
        self,
        exception: HardwareTransitionRequired,
        signal_priority: float,
        **_kwargs: Any,
    ) -> None:
        await self.handle_transition_mock(exception, signal_priority=signal_priority)


@pytest.mark.asyncio
async def test_graph_runner_native_rehydration_ritual() -> None:
    """A graph resume returns its result without finalizing the caller-owned checkpoint."""
    persistence = LychDTestPersistence()
    graph = Graph[MockState, None, str](nodes=[MockNode])
    await graph.initialize(MockNode(), state=MockState(data="frozen"), persistence=persistence)

    runner = GraphRunner[MockState](
        orchestrator=SimpleMockOrchestrator(),
        persistence=persistence,
        signal_priority=50,
    )

    result = await runner.resume_graph(graph)

    assert result == "done"
    persistence.mark_job_resumed_mock.assert_not_called()


@pytest.mark.asyncio
async def test_graph_runner_stasis_and_reanimation_loop() -> None:
    """Verify interruption, orchestration, and reanimation in one loop."""
    persistence = LychDTestPersistence()
    graph = Graph[MockState, None, str](nodes=[StasisNode, SuccessNode])
    mock_orchestrator = SimpleMockOrchestrator()
    occurrences: list[tuple[str, str, str, str | None]] = []

    runner = GraphRunner[MockState](
        orchestrator=mock_orchestrator,
        persistence=persistence,
        signal_priority=50,
        on_node_event=lambda event: occurrences.append(
            (event.occurrence_id, event.node_type.__name__, event.phase, event.wait_kind)
        ),
    )

    result = await runner.run_graph(graph, StasisNode(), MockState())

    assert result == "victory"
    mock_orchestrator.handle_transition_mock.assert_called_once()
    assert len(persistence.history) > 0
    assert [(node, phase, wait) for _, node, phase, wait in occurrences] == [
        ("StasisNode", "entered", None),
        ("StasisNode", "waiting", "hardware"),
        ("StasisNode", "entered", None),
        ("StasisNode", "settled", None),
        ("SuccessNode", "entered", None),
        ("SuccessNode", "settled", None),
    ]
    first_wait = occurrences[0][0]
    assert occurrences[1][0] == first_wait
    assert occurrences[2][0] != first_wait  # retry/resume is a new logical occurrence


@pytest.mark.asyncio
async def test_graph_runner_does_not_report_waiting_when_checkpoint_fails() -> None:
    graph = Graph[MockState, None, str](nodes=[StasisNode, SuccessNode])
    occurrences: list[str] = []
    runner = GraphRunner[MockState](
        orchestrator=SimpleMockOrchestrator(),
        persistence=FailingStasisPersistence(),
        signal_priority=50,
        on_node_event=lambda event: occurrences.append(event.phase),
    )

    with pytest.raises(_CheckpointUnavailableError):
        await runner.run_graph(graph, StasisNode(), MockState())

    assert occurrences == ["entered", "failed"]


@pytest.mark.asyncio
async def test_dispatch_drain_race_parks_and_retries_through_graph_runner() -> None:
    """Losing admission is Live Stasis, not a generic run-failing RuntimeError."""
    leases = LeaseLedger()
    registry = DrainRaceRegistry()
    dispatcher = Dispatcher(registry=registry, leases=leases)  # type: ignore[arg-type]
    orchestrator = ReopenAdmissionOrchestrator(leases)
    graph = Graph[MockState, Dispatcher, str](nodes=[LeaseAfterDrainRaceNode])
    runner = GraphRunner[MockState](
        orchestrator=orchestrator,
        persistence=LychDTestPersistence(),
        signal_priority=70,
    )

    run_task = asyncio.create_task(runner.run_graph(graph, LeaseAfterDrainRaceNode(), MockState(), deps=dispatcher))
    await registry.issue_started.wait()
    leases.begin_drain([MOCK_SPEC.animator_name])
    registry.finish_first_issue.set()

    assert await run_task == "leased"
    assert orchestrator.calls == [MOCK_SPEC.key]
    assert registry.issue_count == 2
    assert leases.active() == []


@pytest.mark.asyncio
async def test_graph_runner_threads_signal_priority_and_fires_stasis_callbacks() -> None:
    """O5: the run's priority reaches handle_transition; callbacks bracket the park."""
    persistence = LychDTestPersistence()
    graph = Graph[MockState, None, str](nodes=[StasisNode, SuccessNode])
    mock_orchestrator = SimpleMockOrchestrator()
    order: list[str] = []

    async def _enter() -> None:
        order.append("enter")

    async def _exit() -> None:
        order.append("exit")

    runner = GraphRunner[MockState](
        orchestrator=mock_orchestrator,
        persistence=persistence,
        signal_priority=42,
        on_stasis_enter=_enter,
        on_stasis_exit=_exit,
    )

    result = await runner.run_graph(graph, StasisNode(), MockState())

    assert result == "victory"
    _, kwargs = mock_orchestrator.handle_transition_mock.call_args
    assert kwargs["signal_priority"] == 42.0  # the run's priority, not the hardcoded 100.0
    # enter (RUNNING→AWAITING_HARDWARE) precedes the transition; exit (→RUNNING) follows it.
    assert order == ["enter", "exit"]
