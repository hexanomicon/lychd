from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast
from uuid import uuid4

import structlog
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_graph import BaseNode, End, EndMarker, EndNode, Graph, GraphTask, GraphTaskRequest, StartNode
from pydantic_graph.id_types import NodeID
from pydantic_graph.step import NodeStep

from lychd.domain.animation.errors import HardwareTransitionRequired
from lychd.domain.cortex.execution_context import bind_occurrence, reset_occurrence
from lychd.domain.cortex.graph import serial_graph_topology
from lychd.domain.cortex.runs import ConsentPending, RunParked
from lychd.domain.cortex.stasis import NodeSnapshot, PhylacteryProtocol
from lychd.domain.delegation.signals import DelegatedAgentParked, DelegatedAgentPending
from lychd.domain.orchestration.journal import TransitionRecord, notify_transition

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from lychd.domain.cortex.priority import Priority
    from lychd.domain.orchestration.schema import TransitionTrace


logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class StasisPolicy:
    """Convergence bounds evaluated against one Run's checkpoint-owned counters."""

    max_resumes: int = 8  # total transition retries per run
    max_same_key: int = 3  # identical-capability convergence bound


class HardwareResumeBudget(BaseModel):
    """Checkpoint-owned hardware-resume counters for one Run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_resumes: int = Field(default=0, ge=0)
    same_capability_key: str | None = Field(default=None, min_length=1)
    same_capability_resumes: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _validate_counter_shape(self) -> HardwareResumeBudget:
        has_same_key = self.same_capability_key is not None
        has_same_count = self.same_capability_resumes > 0
        if has_same_key != has_same_count or (self.total_resumes > 0) != has_same_count:
            msg = "Hardware-resume totals, capability key, and consecutive count must describe the same history."
            raise ValueError(msg)
        if self.same_capability_resumes > self.total_resumes:
            msg = "Consecutive hardware resumes cannot exceed total hardware resumes."
            raise ValueError(msg)
        return self

    def advance(self, capability_key: str) -> HardwareResumeBudget:
        """Return the next immutable budget observation for one transition request."""
        same_capability_resumes = self.same_capability_resumes + 1 if capability_key == self.same_capability_key else 1
        return HardwareResumeBudget(
            total_resumes=self.total_resumes + 1,
            same_capability_key=capability_key,
            same_capability_resumes=same_capability_resumes,
        )


class _HardwareResumeCheckpoint(Protocol):
    hardware_resume_budget: HardwareResumeBudget


def _require_hardware_resume_checkpoint(state: BaseModel) -> _HardwareResumeCheckpoint:
    budget = getattr(state, "hardware_resume_budget", None)
    if not isinstance(budget, HardwareResumeBudget):
        msg = "Graph workflow state must declare a typed hardware_resume_budget checkpoint field."
        raise TypeError(msg)
    return cast("_HardwareResumeCheckpoint", state)


@dataclass(frozen=True, kw_only=True)
class NodeOccurrenceEvent:
    """One lifecycle edge for a single logical node invocation attempt."""

    occurrence_id: str
    node_type: type[BaseNode[Any, Any, Any]]
    phase: Literal["entered", "settled", "waiting", "failed"]
    wait_kind: Literal["hardware", "consent", "delegate"] | None = None
    transition_request_id: str | None = None
    delegated_job_id: str | None = None
    delegated_runtime: str | None = None


def _extract_signal[T: BaseException](exc: BaseException, kind: type[T], *, max_depth: int = 5) -> T | None:
    """Find one unambiguous `kind` signal through cause/context or an exception group.

    The old walk was depth-1 over ``__cause__`` only — it missed the ``ExceptionGroup``
    wrapping anyio task groups can produce around a tool raised mid-stream. A mixed
    group must remain a failure: parking on one child may not swallow its siblings.
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
            candidates = [walk(sub, depth - 1) for sub in group.exceptions]
            if candidates:
                first = candidates[0]
                if first is not None and all(candidate is first for candidate in candidates[1:]):
                    return first
            return None
        chained = current.__cause__
        if chained is None and not current.__suppress_context__:
            chained = current.__context__
        for nxt in (chained,):
            if (found := walk(nxt, depth - 1)) is not None:
                return found
        return None

    return walk(exc, max_depth)


class TransitionOrchestrator(Protocol):
    """Orchestration surface required by graph stasis recovery."""

    async def handle_transition(
        self,
        exception: HardwareTransitionRequired,
        signal_priority: Priority,
        *,
        trace: TransitionTrace | None = None,
    ) -> None: ...


def _single_node_task(
    graph: Graph[Any, Any, Any, Any], event: EndMarker[Any] | Sequence[GraphTask], *, check_inputs: bool = True
) -> GraphTask:
    """Refuse scheduler shapes that cannot be represented by one station cursor."""
    if isinstance(event, EndMarker) or len(event) != 1:
        msg = "A serial graph boundary must expose exactly one node task."
        raise ValueError(msg)
    task = event[0]
    step = graph.nodes.get(task.node_id)
    if not isinstance(step, NodeStep) or (check_inputs and type(task.inputs) is not step.node_type):
        msg = "A serial graph boundary must contain its declared BaseNode station."
        raise ValueError(msg)
    return task


async def _prepare_entry[StateT: BaseModel](
    persistence: PhylacteryProtocol,
    *,
    is_resume: bool,
    start_node: BaseNode[StateT, Any, Any] | None,
    state: StateT | None,
    permitted_edges: set[tuple[str, str]],
) -> tuple[NodeSnapshot[Any, Any], StateT, BaseNode[Any, Any, Any]]:
    """Keep fresh execution on caller objects; resume from one decoded cursor."""
    if is_resume:
        snapshot = await persistence.load_next()
        if snapshot is None:
            msg = "No created checkpoint remains for this graph resume."
            raise ValueError(msg)
        return snapshot, snapshot.state, snapshot.node
    if start_node is None or state is None:
        msg = "Fresh graph execution requires both start_node and state."
        raise ValueError(msg)
    if (StartNode.id, start_node.get_node_id()) not in permitted_edges:
        msg = "Fresh graph node does not match its declared entry station."
        raise ValueError(msg)
    snapshot = await persistence.snapshot_node(state, start_node)
    return snapshot, state, start_node


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
        on_node_event: Callable[[NodeOccurrenceEvent], None] | None = None,
        on_transition_event: Callable[[TransitionRecord], None] | None = None,
        validate_state: Callable[[StateT], None] | None = None,
        validate_resume: Callable[[StateT, BaseNode[Any, Any, Any] | End[Any]], None] | None = None,
        run_id: str | None = None,
        policy: StasisPolicy | None = None,
    ) -> None:
        """Initialize graph runner dependencies.

        ``signal_priority`` is REQUIRED (no default): a missing value would silently
        claim maximum urgency — the worst failure direction for a priority system. It is
        threaded to ``handle_transition`` (the run's priority, C7). The stasis callbacks
        (spec-00 C7) fire around a transition so the ledger
        can flip ``RUNNING → AWAITING_HARDWARE → RUNNING`` — ``on_stasis_enter`` after
        rehydration, ``on_stasis_exit`` after ``handle_transition`` returns.
        A workflow-owned ``validate_state`` checks fresh or restored state against
        its admitted Run before any node executes, including hardware re-entry.
        ``validate_resume`` binds the initial durable re-entry node and state to
        its caller's wait owner; later hardware re-entry has already consumed it.
        """
        self.orchestrator = orchestrator
        self.persistence = persistence
        self.signal_priority = signal_priority
        self._on_stasis_enter = on_stasis_enter
        self._on_stasis_exit = on_stasis_exit
        self._on_node_event = on_node_event
        self._on_transition_event = on_transition_event
        self._validate_state = validate_state
        self._validate_resume = validate_resume
        self._run_id = run_id
        self._policy = policy or StasisPolicy()

    def _node_event(
        self,
        *,
        occurrence_id: str,
        node: BaseNode[Any, Any, Any],
        phase: Literal["entered", "settled", "waiting", "failed"],
        wait_kind: Literal["hardware", "consent", "delegate"] | None = None,
        transition_request_id: str | None = None,
        delegated_job_id: str | None = None,
        delegated_runtime: str | None = None,
    ) -> None:
        """Project an occurrence without letting observer failure change execution truth."""
        if self._on_node_event is not None:
            try:
                self._on_node_event(
                    NodeOccurrenceEvent(
                        occurrence_id=occurrence_id,
                        node_type=type(node),
                        phase=phase,
                        wait_kind=wait_kind,
                        transition_request_id=transition_request_id,
                        delegated_job_id=delegated_job_id,
                        delegated_runtime=delegated_runtime,
                    )
                )
            except Exception:  # projection sinks cannot decide Run outcomes
                logger.warning(
                    "node_observer_failed",
                    run_id=self._run_id,
                    occurrence_id=occurrence_id,
                    phase=phase,
                    exc_info=True,
                )

    def _transition_event(self, trace: TransitionTrace) -> None:
        """Project a Graph-owned transition phase through the shared observer boundary."""
        notify_transition(TransitionRecord.from_trace(trace), self._on_transition_event)

    async def run_graph(
        self,
        graph: Graph[StateT, Any, Any, Any],
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

    async def resume_graph(self, graph: Graph[StateT, Any, Any, Any], *, deps: Any = None) -> Any:
        """Resume a persisted graph run without finalizing its checkpoint.

        Checkpoint ownership belongs to ``perform_run``: only the caller knows when the
        graph result has been committed as terminal run truth.  Deleting here creates a
        loss window between graph completion and ``RunStatus.DONE`` persistence.
        """
        return await self._run_with_stasis(graph, is_resume=True, deps=deps)

    async def _run_with_stasis(  # noqa: C901, PLR0912, PLR0915 - bounded stasis execution loop
        self,
        graph: Graph[StateT, Any, Any, Any],
        *,
        is_resume: bool,
        start_node: BaseNode[StateT, Any, Any] | None = None,
        state: StateT | None = None,
        deps: Any = None,
    ) -> Any:
        """Execute the graph loop with checkpoint-owned stasis convergence state."""
        current_is_resume = is_resume
        validate_initial_resume = is_resume
        self.persistence.set_graph_types(graph)
        _, permitted_edges = serial_graph_topology(graph)

        while True:
            snapshot, execution_state, execution_node = await _prepare_entry(
                self.persistence,
                is_resume=current_is_resume,
                start_node=start_node,
                state=state,
                permitted_edges=permitted_edges,
            )
            if self._validate_state is not None:
                self._validate_state(snapshot.state)
            if validate_initial_resume and self._validate_resume is not None:
                self._validate_resume(snapshot.state, snapshot.node)
            validate_initial_resume = False

            async with graph.iter(state=execution_state, deps=deps, inputs=execution_node) as graph_run:
                # Advancing the synthetic StartNode only exposes its first task;
                # it does not execute a workflow station. Its per-invocation fork
                # stack is used by the native scheduler, never persisted by LychD.
                initial = _single_node_task(graph, await anext(graph_run), check_inputs=False)
                tasks = [GraphTaskRequest(NodeID(execution_node.get_node_id()), execution_node, initial.fork_stack)]
                next_node: BaseNode[Any, Any, Any] | End[Any] = execution_node
                active_node: BaseNode[Any, Any, Any] | None = None
                occurrence_id: str | None = None
                try:
                    while not isinstance(next_node, End):
                        active_node = next_node
                        occurrence_id = str(uuid4())
                        self._node_event(occurrence_id=occurrence_id, node=active_node, phase="entered")
                        occurrence_token = bind_occurrence(occurrence_id)
                        try:
                            async with self.persistence.record_run(snapshot.id):
                                event = await graph_run.next(tasks)
                                target = (
                                    EndNode.id
                                    if isinstance(event, EndMarker)
                                    else _single_node_task(graph, event).node_id
                                )
                                if (active_node.get_node_id(), target) not in permitted_edges:
                                    msg = f"Graph station {active_node.get_node_id()!r} returned undeclared successor {target!r}."
                                    raise ValueError(msg)
                            if isinstance(event, EndMarker):
                                next_node = End(event.value)
                                await self.persistence.snapshot_end(graph_run.state, next_node)
                            else:
                                task = _single_node_task(graph, event)
                                next_node = cast("BaseNode[Any, Any, Any]", task.inputs)
                                snapshot = await self.persistence.snapshot_node(graph_run.state, next_node)
                                tasks = [task]
                        finally:
                            reset_occurrence(occurrence_token)
                        self._node_event(occurrence_id=occurrence_id, node=active_node, phase="settled")
                        active_node = None
                        occurrence_id = None

                except Exception as exc:
                    # Consent park (C3): a Gate raised ConsentPending. Snapshot the
                    # parked node (fresh id) and return the RunParked sentinel — the run
                    # SUSPENDS (it does not fail, and it is not a hardware transition).
                    park = _extract_signal(exc, ConsentPending)
                    if park is not None and active_node is not None:
                        try:
                            await self.persistence.rehydrate_stasis(graph_run.state, active_node)
                        except BaseException:
                            if occurrence_id is not None:
                                self._node_event(
                                    occurrence_id=occurrence_id,
                                    node=active_node,
                                    phase="failed",
                                )
                            raise
                        if occurrence_id is not None:
                            self._node_event(
                                occurrence_id=occurrence_id,
                                node=active_node,
                                phase="waiting",
                                wait_kind="consent",
                            )
                        return RunParked(consent_id=park.consent_id, tool_name=park.tool_name)

                    delegated = _extract_signal(exc, DelegatedAgentPending)
                    if delegated is not None and active_node is not None:
                        try:
                            await self.persistence.rehydrate_stasis(graph_run.state, active_node)
                        except BaseException:
                            if occurrence_id is not None:
                                self._node_event(
                                    occurrence_id=occurrence_id,
                                    node=active_node,
                                    phase="failed",
                                )
                            raise
                        if occurrence_id is not None:
                            self._node_event(
                                occurrence_id=occurrence_id,
                                node=active_node,
                                phase="waiting",
                                wait_kind="delegate",
                                delegated_job_id=delegated.job.job_id,
                                delegated_runtime=delegated.job.runtime,
                            )
                        return DelegatedAgentParked(job=delegated.job)

                    signal = _extract_signal(exc, HardwareTransitionRequired)

                    if signal and active_node is not None:
                        from lychd.domain.orchestration.schema import TransitionTrace

                        checkpoint_state = _require_hardware_resume_checkpoint(graph_run.state)
                        budget = checkpoint_state.hardware_resume_budget.advance(signal.capability_key)
                        checkpoint_state.hardware_resume_budget = budget
                        if (
                            budget.total_resumes > self._policy.max_resumes
                            or budget.same_capability_resumes > self._policy.max_same_key
                        ):
                            if occurrence_id is not None:
                                self._node_event(
                                    occurrence_id=occurrence_id,
                                    node=active_node,
                                    phase="failed",
                                )
                            msg = (
                                f"Stasis did not converge for capability '{signal.capability_key}' after "
                                f"{budget.total_resumes} transition(s); aborting the run."
                            )
                            raise RuntimeError(msg) from signal
                        trace = TransitionTrace(
                            target_capability_key=signal.capability_key,
                            priority=float(self.signal_priority),
                            run_id=self._run_id,
                            occurrence_id=occurrence_id,
                            observer=self._on_transition_event,
                        )
                        try:
                            await self.persistence.rehydrate_stasis(graph_run.state, active_node)
                        except BaseException:
                            if occurrence_id is not None:
                                self._node_event(
                                    occurrence_id=occurrence_id,
                                    node=active_node,
                                    phase="failed",
                                )
                            raise
                        if occurrence_id is not None:
                            self._node_event(
                                occurrence_id=occurrence_id,
                                node=active_node,
                                phase="waiting",
                                wait_kind="hardware",
                                transition_request_id=trace.request_id,
                            )
                        self._transition_event(trace)
                        if self._on_stasis_enter is not None:
                            await self._on_stasis_enter()
                        try:
                            await self.orchestrator.handle_transition(
                                signal,
                                signal_priority=self.signal_priority,
                                trace=trace,
                            )
                        except BaseException:
                            if trace.phase not in {
                                "declined_no_effect",
                                "failed_restored",
                                "cancelled_restored",
                                "contained_uncertain",
                                "failed",
                            }:
                                trace.phase = "failed"
                                self._transition_event(trace)
                            raise
                        if trace.phase == "requested":
                            trace.phase = "completed"
                            self._transition_event(trace)
                        # Exceptions from handle_transition skip the exit callback: the
                        # run is failing, and reconcile owns the row.
                        if self._on_stasis_exit is not None:
                            await self._on_stasis_exit()
                        current_is_resume = True
                        continue

                    if active_node is not None and occurrence_id is not None:
                        self._node_event(occurrence_id=occurrence_id, node=active_node, phase="failed")
                    raise
                else:
                    return next_node.data
