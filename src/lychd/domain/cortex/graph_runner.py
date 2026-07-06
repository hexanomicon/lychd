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

    def __init__(self, *, orchestrator: TransitionOrchestrator, persistence: PhylacteryProtocol) -> None:
        """Initialize graph runner dependencies."""
        self.orchestrator = orchestrator
        self.persistence = persistence

    async def run_graph(
        self,
        graph: Graph[StateT, Any, Any],
        start_node: BaseNode[StateT, Any, Any],
        state: StateT,
        *,
        deps: Any = None,
    ) -> Any:
        """Execute a fresh Pydantic Graph run with native stasis support."""
        return await self._execute_ritual(
            graph,
            is_resume=False,
            start_node=start_node,
            state=state,
            deps=deps,
        )

    async def resume_graph(self, graph: Graph[StateT, Any, Any], *, deps: Any = None) -> Any:
        """Resume a persisted graph run with stasis support."""
        result = await self._execute_ritual(graph, is_resume=True, deps=deps)
        await self.persistence.mark_job_resumed(self.persistence.job_id)
        return result

    async def _execute_ritual(  # noqa: C901, PLR0912 - bounded-retry stasis loop is intentionally branchy
        self,
        graph: Graph[StateT, Any, Any],
        *,
        is_resume: bool,
        start_node: BaseNode[StateT, Any, Any] | None = None,
        state: StateT | None = None,
        deps: Any = None,
    ) -> Any:
        """Execute the graph loop and handle stasis signals iteratively."""
        current_is_resume = is_resume
        resume_count = 0
        repeated_key: str | None = None
        repeated_count = 0
        max_resumes = 8
        max_same_key = 3

        while True:
            if not current_is_resume:
                if start_node is None or state is None:
                    msg = "Fresh graph execution requires both start_node and state."
                    raise ValueError(msg)
                context_manager = graph.iter(
                    start_node,
                    state=state,
                    deps=deps,
                    persistence=cast("BaseStatePersistence[StateT, Any]", self.persistence),
                )
            else:
                context_manager = graph.iter_from_persistence(
                    cast("BaseStatePersistence[StateT, Any]", self.persistence),
                    deps=deps,
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
                        resume_count += 1
                        if signal.spec.key == repeated_key:
                            repeated_count += 1
                        else:
                            repeated_key, repeated_count = signal.spec.key, 1
                        if resume_count > max_resumes or repeated_count >= max_same_key:
                            msg = (
                                f"Stasis did not converge for capability '{signal.spec.key}' after "
                                f"{resume_count} transition(s); aborting the run."
                            )
                            raise RuntimeError(msg) from signal
                        await self.persistence.rehydrate_stasis(graph_run.state, graph_run.next_node)
                        await self.orchestrator.handle_transition(signal, signal_priority=100.0)
                        current_is_resume = True
                        continue

                    raise
                else:
                    result = graph_run.result
                    return result.output if result else None
