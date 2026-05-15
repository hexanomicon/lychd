from typing import Any, Generic, TypeVar
from pydantic import BaseModel
from pydantic_graph import Graph, BaseNode
from lychd.extensions.protocols import PhylacteryProtocol
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.cortex.dispatcher import Dispatcher, HardwareTransitionRequired

StateT = TypeVar("StateT", bound=BaseModel)

class GraphRunner(Generic[StateT]):
    """
    Executes the Pydantic AI cognitive loops.
    Total binding with pydantic-graph: uses native persistence and iteration
    to manage the Stasis and Rehydration rituals.
    """
    
    def __init__(self, dispatcher: Dispatcher, orchestrator: OrchestratorManager, persistence: PhylacteryProtocol) -> None:
        """
        :param dispatcher: The intent resolution engine.
        :param orchestrator: The physical transmutation engine.
        :param persistence: The LychD Phylactery (implements BaseStatePersistence).
        """
        self.dispatcher = dispatcher
        self.orchestrator = orchestrator
        self.persistence = persistence 

    async def run_graph(self, graph: Graph[StateT, Any, Any], start_node: BaseNode[StateT, Any, Any], state: StateT) -> Any:
        """
        Executes a fresh Pydantic Graph run with native Stasis support.
        """
        return await self._execute_ritual(
            graph, 
            is_resume=False,
            start_node=start_node,
            state=state
        )

    async def resume_graph(self, graph: Graph[StateT, Any, Any]) -> Any:
        """
        Reanimates a dormant Agent from the Phylactery with Stasis support.
        """
        result = await self._execute_ritual(graph, is_resume=True)
        
        # Awakening cleanup
        await self.persistence.mark_job_resumed(self.persistence.job_id)
        return result

    async def _execute_ritual(
        self, 
        graph: Graph[StateT, Any, Any], 
        is_resume: bool,
        start_node: BaseNode[StateT, Any, Any] | None = None,
        state: StateT | None = None
    ) -> Any:
        """
        The Core Ritual: Executes the graph loop and handles Stasis signals iteratively.
        """
        current_is_resume = is_resume
        
        while True:
            # We use the native iterator to ensure we have access to the live state
            # even if an exception occurs during node execution.
            if not current_is_resume:
                context_manager = graph.iter(start_node, state=state, persistence=self.persistence)
            else:
                context_manager = graph.iter_from_persistence(self.persistence)

            async with context_manager as graph_run:
                try:
                    async for _ in graph_run:
                        pass
                    result = graph_run.result
                    return result.output if result else None

                except Exception as e:
                    # THE STASIS TRIGGER
                    signal = None
                    for candidate in [e, getattr(e, "__cause__", None)]:
                        if candidate and candidate.__class__.__name__ == "HardwareTransitionRequired":
                            signal = candidate
                            break
                    
                    if signal:
                        # 1. Manually persist the state from the interrupted run.
                        # This ensures the 'warm=True' flag (or any other state change)
                        # is saved and the node is reset to 'created' status.
                        await self.persistence.rehydrate_stasis(graph_run.state, graph_run.next_node)

                        # 2. Flip the physical switches
                        await self.orchestrator.handle_transition(signal, signal_priority=100.0)
                        
                        # 3. Prepare for Reanimation in the next iteration
                        current_is_resume = True
                        continue
                    
                    raise e
            # Loop continues here after 'break' exits the 'async with'

    async def _execute_pydantic_ai_step(self, mind_bundle: Any, state: StateT) -> StateT:
        """Deprecated: Replaced by run_graph/resume_graph native loop."""
        return state
