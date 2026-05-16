import pytest
import copy
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock
from typing import Any
from pydantic import BaseModel
from pydantic_graph import Graph, BaseNode, End, GraphRunContext, FullStatePersistence
from pydantic_graph.persistence import NodeSnapshot
from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.cortex.graph_runner import GraphRunner
from lychd.domain.cortex.dispatcher import HardwareTransitionRequired

class MockState(BaseModel):
    data: str = "initial"
    warm: bool = False

@dataclass
class MockAnim:
    id: str = "mock-anim"
    base_url: str = "http://localhost:8080/v1"


MOCK_SPEC = CapabilitySpec(
    key="mock-anim:chat:mock-cap",
    animator_name="mock-anim",
    runtime="llamacpp",
    source_kind="soulstone",
    family=CapabilityFamily.CHAT,
    model_id="mock-cap",
)
MOCK_STATE = CapabilityState(
    capability_key=MOCK_SPEC.key,
    is_static=False,
    is_active=False,
    is_available=True,
    warm=False,
)

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
            raise HardwareTransitionRequired(MOCK_SPEC, MOCK_STATE, MockAnim())
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
