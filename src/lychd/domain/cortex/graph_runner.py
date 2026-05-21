from __future__ import annotations

from typing import Any, Protocol, cast

from pydantic import BaseModel
from pydantic_graph import BaseNode, Graph
from pydantic_graph.persistence import BaseStatePersistence

from lychd.domain.cortex.dispatcher import HardwareTransitionRequired
from lychd.extensions.protocols import PhylacteryProtocol


class TransitionOrchestrator(Protocol):
    """Orchestration surface required by graph stasis recovery."""

    async def handle_transition(self, exception: HardwareTransitionRequired, signal_priority: float) -> None: ...


class GraphRunner[StateT: BaseModel]:
    """Execute Pydantic Graph loops with LychD stasis and rehydration support."""

    def __init__(self, dispatcher: object, orchestrator: TransitionOrchestrator, persistence: PhylacteryProtocol) -> None:
        """Initialize graph runner dependencies."""
        self.dispatcher = dispatcher
        self.orchestrator = orchestrator
        self.persistence = persistence

    async def run_graph(self, graph: Graph[StateT, Any, Any], start_node: BaseNode[StateT, Any, Any], state: StateT) -> Any:
        """Execute a fresh Pydantic Graph run with native stasis support."""
        return await self._execute_ritual(
            graph,
            is_resume=False,
            start_node=start_node,
            state=state,
        )

    async def resume_graph(self, graph: Graph[StateT, Any, Any]) -> Any:
        """Resume a persisted graph run with stasis support."""
        result = await self._execute_ritual(graph, is_resume=True)
        await self.persistence.mark_job_resumed(self.persistence.job_id)
        return result

    async def _execute_ritual(
        self,
        graph: Graph[StateT, Any, Any],
        *,
        is_resume: bool,
        start_node: BaseNode[StateT, Any, Any] | None = None,
        state: StateT | None = None,
    ) -> Any:
        """Execute the graph loop and handle stasis signals iteratively."""
        current_is_resume = is_resume

        while True:
            if not current_is_resume:
                if start_node is None or state is None:
                    msg = "Fresh graph execution requires both start_node and state."
                    raise ValueError(msg)
                context_manager = graph.iter(
                    start_node,
                    state=state,
                    persistence=cast("BaseStatePersistence[StateT, Any]", self.persistence),
                )
            else:
                context_manager = graph.iter_from_persistence(
                    cast("BaseStatePersistence[StateT, Any]", self.persistence)
                )

            async with context_manager as graph_run:
                try:
                    async for _ in graph_run:
                        pass

                except Exception as exc:
                    signal: HardwareTransitionRequired | None = None
                    for candidate in (exc, getattr(exc, "__cause__", None)):
                        if isinstance(candidate, HardwareTransitionRequired):
                            signal = candidate
                            break

                    if signal:
                        await self.persistence.rehydrate_stasis(graph_run.state, graph_run.next_node)
                        await self.orchestrator.handle_transition(signal, signal_priority=100.0)
                        current_is_resume = True
                        continue

                    raise
                else:
                    result = graph_run.result
                    return result.output if result else None
