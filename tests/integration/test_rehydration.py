import pytest
import copy
from dataclasses import dataclass
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from typing import Any
from pydantic import BaseModel
from pydantic_graph import Graph, BaseNode, End, GraphRunContext, FullStatePersistence
from pydantic_graph.persistence import NodeSnapshot
from lychd.domain.cortex.graph_runner import GraphRunner
from lychd.domain.cortex.dispatcher import HardwareTransitionRequired

class MockState(BaseModel):
    data: str = "initial"
    warm: bool = False

# Helper objects to avoid Pydantic serialization errors with MagicMock
@dataclass
class MockCap:
    identifier: str = "mock-cap"
    matrix_sets: list = None
    evict_cost: int = 0
    is_active: bool = True

    def __post_init__(self):
        if self.matrix_sets is None:
            self.matrix_sets = ["test"]

@dataclass
class MockAnim:
    identifier: str = "mock-anim"
    async def activate_capability(self, cap): pass

# Nodes at module level for Pydantic serialization stability
@dataclass
class MockNode(BaseNode[MockState]):
    async def run(self, ctx: GraphRunContext[MockState]) -> End[str]:
        return End("done")

@dataclass
class SuccessNode(BaseNode[MockState]):
    async def run(self, ctx: GraphRunContext[MockState]) -> End[str]:
        return End("victory")

@dataclass
class StasisNode(BaseNode[MockState]):
    async def run(self, ctx: GraphRunContext[MockState]) -> SuccessNode:
        if not ctx.state.warm:
            ctx.state.warm = True # The State is persisted!
            raise HardwareTransitionRequired(MockCap(), MockAnim())
        return SuccessNode()

# Custom Persistence for testing that includes LychD-specific rituals
class LychDTestPersistence(FullStatePersistence):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_id = "test-job"
        self.mark_job_resumed = AsyncMock()

    async def rehydrate_stasis(self, state: Any, node: Any) -> None:
        """Finds the snapshot and resets it with the new state."""
        snapshot_id = node.get_snapshot_id()
        for snapshot in self.history:
            if snapshot.id == snapshot_id:
                snapshot.state = copy.deepcopy(state)
                snapshot.status = 'created'
                return
        # If not found, create a new one (fallback)
        await self.snapshot_node(state, node)

class SimpleMockDispatcher:
    pass

class SimpleMockOrchestrator:
    def __init__(self):
        self.handle_transition = AsyncMock()

@pytest.mark.asyncio
async def test_graph_runner_native_rehydration_ritual():
    """THE NATIVE REHYDRATION CRUCIBLE."""
    persistence = LychDTestPersistence()
    graph = Graph(nodes=[MockNode])
    await graph.initialize(MockNode(), state=MockState(data="frozen"), persistence=persistence)
    
    runner = GraphRunner(
        dispatcher=SimpleMockDispatcher(),
        orchestrator=SimpleMockOrchestrator(),
        persistence=persistence
    )
    
    result = await runner.resume_graph(graph)
    assert result == "done"
    persistence.mark_job_resumed.assert_called_once()

@pytest.mark.asyncio
async def test_graph_runner_stasis_and_reanimation_loop():
    """Verifies the complete loop: Interruption -> Orchestration -> Reanimation."""
    persistence = LychDTestPersistence()
    graph = Graph(nodes=[StasisNode, SuccessNode])
    
    mock_orchestrator = SimpleMockOrchestrator()
    
    # No side effect needed anymore! 
    # GraphRunner now handles snapshotting manually on stasis.
    
    runner = GraphRunner(
        dispatcher=SimpleMockDispatcher(), 
        orchestrator=mock_orchestrator, 
        persistence=persistence
    )
    
    # 1. Run initial graph
    result = await runner.run_graph(graph, StasisNode(), MockState())
    
    # 2. Assertions
    assert result == "victory"
    mock_orchestrator.handle_transition.assert_called_once()
    assert len(persistence.history) > 0
