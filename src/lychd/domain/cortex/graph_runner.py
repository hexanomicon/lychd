from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, cast

from pydantic import BaseModel
from pydantic_graph import BaseNode, Graph
from pydantic_graph.persistence import BaseStatePersistence

from lychd.domain.cortex.dispatcher import HardwareTransitionRequired
from lychd.domain.cortex.runs import ConsentPending, RunParked
from lychd.extensions.protocols import PhylacteryProtocol

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class TransitionOrchestrator(Protocol):
    """Orchestration surface required by graph stasis recovery."""

    async def handle_transition(self, exception: HardwareTransitionRequired, signal_priority: float) -> None: ...


class GraphRunner[StateT: BaseModel]:
    """Execute Pydantic Graph loops with LychD stasis and rehydration support."""

    def __init__(
        self,
        *,
        orchestrator: TransitionOrchestrator,
        persistence: PhylacteryProtocol,
        signal_priority: float = 100.0,
        on_stasis_enter: Callable[[], Awaitable[None]] | None = None,
        on_stasis_exit: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize graph runner dependencies.

        ``signal_priority`` is threaded to ``handle_transition`` (the run's priority,
        C7). The stasis callbacks (spec-00 C7) fire around a transition so the ledger
        can flip ``RUNNING → AWAITING_HARDWARE → RUNNING`` — ``on_stasis_enter`` after
        rehydration, ``on_stasis_exit`` after ``handle_transition`` returns.
        """
        self.orchestrator = orchestrator
        self.persistence = persistence
        self.signal_priority = signal_priority
        self._on_stasis_enter = on_stasis_enter
        self._on_stasis_exit = on_stasis_exit

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
        """Resume a persisted graph run with stasis support.

        A chained re-park (the resumed run parked AGAIN) must keep its durable file:
        `mark_job_resumed` (the tombstone) fires only on a non-parked resume.
        """
        result = await self._execute_ritual(graph, is_resume=True, deps=deps)
        if not isinstance(result, RunParked):
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
                    # Consent park (C3): a Gate raised ConsentPending. Snapshot the
                    # parked node (fresh id) and return the RunParked sentinel — the run
                    # SUSPENDS (it does not fail, and it is not a hardware transition).
                    park: ConsentPending | None = None
                    for candidate in (exc, getattr(exc, "__cause__", None)):
                        if isinstance(candidate, ConsentPending):
                            park = candidate
                            break
                    if park is not None:
                        await self.persistence.rehydrate_stasis(graph_run.state, graph_run.next_node)
                        return RunParked(consent_id=park.consent_id, tool_name=park.tool_name)

                    signal: HardwareTransitionRequired | None = None
                    for candidate in (exc, getattr(exc, "__cause__", None)):
                        if isinstance(candidate, HardwareTransitionRequired):
                            signal = candidate
                            break

                    if signal:
                        resume_count += 1
                        if signal.capability_key == repeated_key:
                            repeated_count += 1
                        else:
                            repeated_key, repeated_count = signal.capability_key, 1
                        if resume_count > max_resumes or repeated_count >= max_same_key:
                            msg = (
                                f"Stasis did not converge for capability '{signal.capability_key}' after "
                                f"{resume_count} transition(s); aborting the run."
                            )
                            raise RuntimeError(msg) from signal
                        await self.persistence.rehydrate_stasis(graph_run.state, graph_run.next_node)
                        if self._on_stasis_enter is not None:
                            await self._on_stasis_enter()
                        await self.orchestrator.handle_transition(signal, signal_priority=self.signal_priority)
                        # Exceptions from handle_transition skip the exit callback: the
                        # run is failing, and reconcile owns the row.
                        if self._on_stasis_exit is not None:
                            await self._on_stasis_exit()
                        current_is_resume = True
                        continue

                    raise
                else:
                    result = graph_run.result
                    return result.output if result else None
