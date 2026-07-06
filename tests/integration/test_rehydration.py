from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel
from pydantic_graph import BaseNode, End, FullStatePersistence, Graph, GraphRunContext
from pydantic_graph.persistence import NodeSnapshot

from lychd.domain.animation.capabilities import CapabilitySpec
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.cortex.dispatcher import HardwareTransitionRequired
from lychd.domain.cortex.graph_runner import GraphRunner


class MockState(BaseModel):
    data: str = "initial"
    warm: bool = False


MOCK_SPEC = CapabilitySpec(
    key="mock-anim:chat:mock-cap",
    animator_name="mock-anim",
    runtime="llamacpp",
    source_kind="soulstone",
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


class SimpleMockOrchestrator:
    def __init__(self) -> None:
        self.handle_transition_mock = AsyncMock()

    async def handle_transition(self, exception: HardwareTransitionRequired, signal_priority: float) -> None:
        await self.handle_transition_mock(exception, signal_priority=signal_priority)


@pytest.mark.asyncio
async def test_graph_runner_native_rehydration_ritual() -> None:
    """Verify resume marks a persisted graph job as resumed."""
    persistence = LychDTestPersistence()
    graph = Graph[MockState, None, str](nodes=[MockNode])
    await graph.initialize(MockNode(), state=MockState(data="frozen"), persistence=persistence)

    runner = GraphRunner[MockState](
        orchestrator=SimpleMockOrchestrator(),
        persistence=persistence,
    )

    result = await runner.resume_graph(graph)

    assert result == "done"
    persistence.mark_job_resumed_mock.assert_called_once_with("test-job")


@pytest.mark.asyncio
async def test_graph_runner_stasis_and_reanimation_loop() -> None:
    """Verify interruption, orchestration, and reanimation in one loop."""
    persistence = LychDTestPersistence()
    graph = Graph[MockState, None, str](nodes=[StasisNode, SuccessNode])
    mock_orchestrator = SimpleMockOrchestrator()

    runner = GraphRunner[MockState](
        orchestrator=mock_orchestrator,
        persistence=persistence,
    )

    result = await runner.run_graph(graph, StasisNode(), MockState())

    assert result == "victory"
    mock_orchestrator.handle_transition_mock.assert_called_once()
    assert len(persistence.history) > 0
