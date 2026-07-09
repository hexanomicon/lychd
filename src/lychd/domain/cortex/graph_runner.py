from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from pydantic import BaseModel
from pydantic_graph import BaseNode, Graph
from pydantic_graph.persistence import BaseStatePersistence

from lychd.domain.animation.errors import HardwareTransitionRequired
from lychd.domain.cortex.runs import ConsentPending, RunParked
from lychd.extensions.protocols import PhylacteryProtocol

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from lychd.domain.cortex.priority import Priority


@dataclass(frozen=True, kw_only=True)
class StasisPolicy:
    """Convergence bounds for the stasis retry loop (was ad-hoc locals)."""

    max_resumes: int = 8  # total transition retries per run
    max_same_key: int = 3  # identical-capability convergence bound


def _extract_signal[T: BaseException](exc: BaseException, kind: type[T], *, max_depth: int = 5) -> T | None:
    """Find a `kind` signal reachable from `exc` via cause/context or a BaseExceptionGroup.

    The old walk was depth-1 over ``__cause__`` only — it missed the ``ExceptionGroup``
    wrapping anyio task groups can produce around a tool raised mid-stream. This is a
    bounded, cycle-safe transitive search.
    """
    seen: set[int] = set()

    def walk(current: BaseException | None, depth: int) -> T | None:
        if current is None or depth < 0 or id(current) in seen:
            return None
        seen.add(id(current))
        if isinstance(current, kind):
            return current
        if isinstance(current, BaseExceptionGroup):
            group = cast("BaseExceptionGroup[BaseException]", current)
            for sub in group.exceptions:
                if (found := walk(sub, depth - 1)) is not None:
                    return found
        for nxt in (current.__cause__, current.__context__):
            if (found := walk(nxt, depth - 1)) is not None:
                return found
        return None

    return walk(exc, max_depth)


class TransitionOrchestrator(Protocol):
    """Orchestration surface required by graph stasis recovery."""

    async def handle_transition(self, exception: HardwareTransitionRequired, signal_priority: Priority) -> None: ...


class GraphRunner[StateT: BaseModel]:
    """Execute Pydantic Graph loops with LychD stasis and rehydration support."""

    def __init__(
        self,
        *,
        orchestrator: TransitionOrchestrator,
        persistence: PhylacteryProtocol,
        signal_priority: Priority,
        on_stasis_enter: Callable[[], Awaitable[None]] | None = None,
        on_stasis_exit: Callable[[], Awaitable[None]] | None = None,
        policy: StasisPolicy | None = None,
    ) -> None:
        """Initialize graph runner dependencies.

        ``signal_priority`` is REQUIRED (no default): a missing value would silently
        claim maximum urgency — the worst failure direction for a priority system. It is
        threaded to ``handle_transition`` (the run's priority, C7). The stasis callbacks
        (spec-00 C7) fire around a transition so the ledger
        can flip ``RUNNING → AWAITING_HARDWARE → RUNNING`` — ``on_stasis_enter`` after
        rehydration, ``on_stasis_exit`` after ``handle_transition`` returns.
        """
        self.orchestrator = orchestrator
        self.persistence = persistence
        self.signal_priority = signal_priority
        self._on_stasis_enter = on_stasis_enter
        self._on_stasis_exit = on_stasis_exit
        self._policy = policy or StasisPolicy()

    async def run_graph(
        self,
        graph: Graph[StateT, Any, Any],
        start_node: BaseNode[StateT, Any, Any],
        state: StateT,
        *,
        deps: Any = None,
    ) -> Any:
        """Execute a fresh Pydantic Graph run with native stasis support."""
        return await self._run_with_stasis(
            graph,
            is_resume=False,
            start_node=start_node,
            state=state,
            deps=deps,
        )

    async def resume_graph(self, graph: Graph[StateT, Any, Any], *, deps: Any = None) -> Any:
        """Resume a persisted graph run without finalizing its checkpoint.

        Checkpoint ownership belongs to ``perform_run``: only the caller knows when the
        graph result has been committed as terminal run truth.  Deleting here creates a
        loss window between graph completion and ``RunStatus.DONE`` persistence.
        """
        return await self._run_with_stasis(graph, is_resume=True, deps=deps)

    async def _run_with_stasis(  # noqa: C901, PLR0912 - bounded-retry stasis loop is intentionally branchy
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
                    park = _extract_signal(exc, ConsentPending)
                    if park is not None:
                        await self.persistence.rehydrate_stasis(graph_run.state, graph_run.next_node)
                        return RunParked(consent_id=park.consent_id, tool_name=park.tool_name)

                    signal = _extract_signal(exc, HardwareTransitionRequired)

                    if signal:
                        resume_count += 1
                        if signal.capability_key == repeated_key:
                            repeated_count += 1
                        else:
                            repeated_key, repeated_count = signal.capability_key, 1
                        if resume_count > self._policy.max_resumes or repeated_count >= self._policy.max_same_key:
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
