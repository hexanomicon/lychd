import asyncio
from dataclasses import dataclass
from pydantic import BaseModel
from pydantic_graph import Graph, BaseNode, End, GraphRunContext, FullStatePersistence
from pydantic_graph.persistence import NodeSnapshot
from lychd.domain.cortex.graph_runner import GraphRunner
from lychd.domain.cortex.dispatcher import HardwareTransitionRequired
from unittest.mock import AsyncMock, MagicMock

class MockState(BaseModel):
    data: str = "initial"

@dataclass
class MockCap:
    identifier: str = "mock-cap"
    matrix_sets: list = None
    evict_cost: int = 0
    is_active: bool = True
    def __post_init__(self):
        if self.matrix_sets is None: self.matrix_sets = ["test"]

@dataclass
class MockAnim:
    identifier: str = "mock-anim"
    async def activate_capability(self, cap): pass

@dataclass
class SuccessNode(BaseNode[MockState]):
    async def run(self, ctx: GraphRunContext[MockState]) -> End[str]:
        return End("victory")

@dataclass
class StasisNode(BaseNode[MockState]):
    async def run(self, ctx: GraphRunContext[MockState]) -> SuccessNode:
        raise HardwareTransitionRequired(MockCap(), MockAnim())

class LychDTestPersistence(FullStatePersistence):
    def __init__(self):
        super().__init__()
        self.job_id = "test-job"
        self.mark_job_resumed = AsyncMock()
    def reset_error_to_created(self):
        for s in self.history:
            if isinstance(s, NodeSnapshot) and s.status == 'error':
                s.status = 'created'

async def main():
    persistence = LychDTestPersistence()
    graph = Graph(nodes=[StasisNode, SuccessNode])
    mock_orchestrator = MagicMock()
    mock_orchestrator.handle_transition = AsyncMock()
    async def side_effect(*args, **kwargs):
        persistence.reset_error_to_created()
    mock_orchestrator.handle_transition.side_effect = side_effect
    
    runner = GraphRunner(MagicMock(), mock_orchestrator, persistence)
    
    print("DEBUG: Calling run_graph in plain script")
    try:
        result = await runner.run_graph(graph, StasisNode(), MockState())
        print(f"DEBUG: Result: {result}")
    except Exception as e:
        print(f"DEBUG: CAUGHT IN MAIN: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
