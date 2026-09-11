from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.domain.animation.capabilities import (
    CapabilityGrant,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    GrantLease,
    SourceKind,
)
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.cortex.dispatcher import Dispatcher, HardwareTransitionRequired
from lychd.domain.cortex.graph import build_serial_graph
from lychd.domain.cortex.graph_runner import GraphRunner, HardwareResumeBudget, StasisPolicy
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.cortex.runs import ConsentPending, RunParked
from lychd.domain.cortex.stasis import DurableStasisPhylactery, InMemoryStasisStore, LiveStasisPhylactery


class MockState(BaseModel):
    data: str = "initial"
    warm: bool = False
    hardware_resume_budget: HardwareResumeBudget = Field(default_factory=HardwareResumeBudget)


MOCK_SPEC = CapabilitySpec(
    key="mock-anim:chat:mock-cap",
    animator_name="mock-anim",
    runtime="llamacpp",
    source_kind=SourceKind.SOULSTONE,
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
            raise HardwareTransitionRequired(MOCK_SPEC.key)
        return SuccessNode()


@dataclass(frozen=True)
class _ResumeDeps:
    resumed: bool


@dataclass
class StasisAcrossDurableParkNode(BaseNode[MockState, _ResumeDeps, str]):
    """Request hardware, park durably, then request the same hardware after re-entry."""

    async def run(self, ctx: GraphRunContext[MockState, _ResumeDeps]) -> End[str]:
        if not ctx.state.warm:
            ctx.state.warm = True
            raise HardwareTransitionRequired(MOCK_SPEC.key)
        if not ctx.deps.resumed:
            consent_id = "consent-1"
            run_id = "run-1"
            tool_name = "test-tool"
            raise ConsentPending(consent_id, run_id, tool_name)
        raise HardwareTransitionRequired(MOCK_SPEC.key)


@dataclass
class LeaseAfterDrainRaceNode(BaseNode[MockState, Dispatcher, str]):
    """Acquire through the real Dispatcher after its first issue loses admission."""

    async def run(self, ctx: GraphRunContext[MockState, Dispatcher]) -> End[str]:
        async with ctx.deps.lease_grant(
            family=CapabilityFamily.CHAT,
            model_name=MOCK_SPEC.model_id,
            run_id="dispatch-race",
        ):
            return End("leased")


class DrainRaceRegistry:
    """Hold the first async grant issue across an Orchestrator drain barrier."""

    def __init__(self) -> None:
        self.state = CapabilityState(
            capability_key=MOCK_SPEC.key,
            phase=CapabilityPhase.WARM,
        )
        self.issue_started = asyncio.Event()
        self.finish_first_issue = asyncio.Event()
        self.issue_count = 0

    def get_capability(self, key: str) -> CapabilitySpec | None:
        return MOCK_SPEC if key == MOCK_SPEC.key else None

    def list_capabilities(self) -> list[CapabilitySpec]:
        return [MOCK_SPEC]

    def get_capability_state(self, key: str) -> CapabilityState | None:
        return self.state if key == MOCK_SPEC.key else None

    def get_runtime(self, _name: str) -> None:
        return None

    async def refresh_capability_state(self, key: str) -> CapabilityState | None:
        return self.get_capability_state(key)

    async def issue_grant(
        self,
        key: str,
        *,
        holder: str,
        scope: Literal["step", "run"] = "step",
    ) -> CapabilityGrant:
        assert key == MOCK_SPEC.key
        self.issue_count += 1
        if self.issue_count == 1:
            self.issue_started.set()
            await self.finish_first_issue.wait()
        return CapabilityGrant(
            spec=MOCK_SPEC,
            state=self.state,
            lease=GrantLease(
                grant_id=uuid4().hex,
                holder=holder,
                issued_at=datetime.now(UTC),
                scope=scope,
            ),
            model=None,
        )


class ReopenAdmissionOrchestrator:
    """Finish the competing drain so GraphRunner can retry the parked node."""

    def __init__(self, leases: LeaseLedger) -> None:
        self.leases = leases
        self.calls: list[str] = []

    async def handle_transition(
        self,
        exception: HardwareTransitionRequired,
        signal_priority: float,
        **_kwargs: Any,
    ) -> None:
        _ = signal_priority
        self.calls.append(exception.capability_key)
        self.leases.end_drain([MOCK_SPEC.animator_name])


class LychDTestPersistence(LiveStasisPhylactery):
    """Use the production live checkpoint contract in hardware retry scenarios."""

    def __init__(self) -> None:
        super().__init__(job_id="test-job")


class FailingStasisPersistence(LychDTestPersistence):
    """Reject checkpoint writes so evidence cannot claim a completed park."""

    async def rehydrate_stasis(self, state: MockState, node: BaseNode[MockState, Any, str]) -> None:
        _ = (state, node)
        raise _CheckpointUnavailableError


class _CheckpointUnavailableError(RuntimeError):
    """Sentinel for a rejected stasis write."""


class SimpleMockOrchestrator:
    def __init__(self) -> None:
        self.handle_transition_mock = AsyncMock()

    async def handle_transition(
        self,
        exception: HardwareTransitionRequired,
        signal_priority: float,
        **_kwargs: Any,
    ) -> None:
        await self.handle_transition_mock(exception, signal_priority=signal_priority)


@pytest.mark.asyncio
async def test_initial_resume_validation_is_consumed_before_hardware_reentry() -> None:
    """The durable wait owner is checked once; state checks still cover the hardware retry."""
    persistence = DurableStasisPhylactery(job_id="resume-owner", store=InMemoryStasisStore())
    graph = build_serial_graph(
        nodes=[StasisNode, SuccessNode], state_type=MockState, deps_type=type(None), output_type=str
    )
    persistence.set_graph_types(graph)
    await persistence.snapshot_node(MockState(), StasisNode())
    resumed_states: list[bool] = []
    validated_states: list[bool] = []

    def validate_resume(state: MockState, node: BaseNode[Any, Any, Any] | End[Any]) -> None:
        assert isinstance(node, StasisNode)
        resumed_states.append(state.warm)

    runner = GraphRunner(
        orchestrator=SimpleMockOrchestrator(),
        persistence=persistence,
        signal_priority=50,
        validate_state=lambda state: validated_states.append(state.warm),
        validate_resume=validate_resume,
    )
    assert await runner.resume_graph(graph) == "victory"
    assert resumed_states == [False]
    assert validated_states == [False, True]


@pytest.mark.asyncio
async def test_graph_runner_resume_preserves_caller_owned_durable_checkpoint() -> None:
    """A successful resume does not delete the checkpoint before its caller commits Run truth."""
    store = InMemoryStasisStore()
    persistence = DurableStasisPhylactery(job_id="test-job", store=store)
    graph = build_serial_graph(nodes=[MockNode], state_type=MockState, deps_type=type(None), output_type=str)
    persistence.set_graph_types(graph)
    await persistence.snapshot_node(MockState(data="frozen"), MockNode())
    assert await store.exists("test-job")

    runner = GraphRunner[MockState](
        orchestrator=SimpleMockOrchestrator(),
        persistence=persistence,
        signal_priority=50,
    )

    result = await runner.resume_graph(graph)

    assert result == "done"
    assert await store.exists("test-job")


@pytest.mark.asyncio
async def test_graph_runner_stasis_and_reanimation_loop() -> None:
    """Verify interruption, orchestration, and reanimation in one loop."""
    persistence = LychDTestPersistence()
    graph = build_serial_graph(
        nodes=[StasisNode, SuccessNode], state_type=MockState, deps_type=type(None), output_type=str
    )
    mock_orchestrator = SimpleMockOrchestrator()
    occurrences: list[tuple[str, str, str, str | None]] = []

    runner = GraphRunner[MockState](
        orchestrator=mock_orchestrator,
        persistence=persistence,
        signal_priority=50,
        on_node_event=lambda event: occurrences.append(
            (event.occurrence_id, event.node_type.__name__, event.phase, event.wait_kind)
        ),
    )

    result = await runner.run_graph(graph, StasisNode(), MockState())

    assert result == "victory"
    mock_orchestrator.handle_transition_mock.assert_called_once()
    assert len(await persistence.load_all()) > 0
    assert [(node, phase, wait) for _, node, phase, wait in occurrences] == [
        ("StasisNode", "entered", None),
        ("StasisNode", "waiting", "hardware"),
        ("StasisNode", "entered", None),
        ("StasisNode", "settled", None),
        ("SuccessNode", "entered", None),
        ("SuccessNode", "settled", None),
    ]
    first_wait = occurrences[0][0]
    assert occurrences[1][0] == first_wait
    assert occurrences[2][0] != first_wait  # retry/resume is a new logical occurrence


@pytest.mark.parametrize(
    "policy",
    [
        pytest.param(StasisPolicy(max_resumes=1, max_same_key=8), id="total"),
        pytest.param(StasisPolicy(max_resumes=8, max_same_key=1), id="same-capability"),
    ],
)
@pytest.mark.asyncio
async def test_hardware_resume_budget_survives_durable_park_and_new_runner(policy: StasisPolicy) -> None:
    store = InMemoryStasisStore()
    graph = build_serial_graph(
        nodes=[StasisAcrossDurableParkNode], state_type=MockState, deps_type=_ResumeDeps, output_type=str
    )
    first_orchestrator = SimpleMockOrchestrator()
    first_runner = GraphRunner[MockState](
        orchestrator=first_orchestrator,
        persistence=DurableStasisPhylactery(job_id="run-1", store=store),
        signal_priority=50,
        policy=policy,
    )

    parked = await first_runner.run_graph(
        graph,
        StasisAcrossDurableParkNode(),
        MockState(),
        deps=_ResumeDeps(resumed=False),
    )

    assert isinstance(parked, RunParked)
    first_orchestrator.handle_transition_mock.assert_called_once()

    second_orchestrator = SimpleMockOrchestrator()
    second_runner = GraphRunner[MockState](
        orchestrator=second_orchestrator,
        persistence=DurableStasisPhylactery(job_id="run-1", store=store),
        signal_priority=50,
        policy=policy,
    )

    with pytest.raises(RuntimeError, match="after 2 transition"):
        await second_runner.resume_graph(graph, deps=_ResumeDeps(resumed=True))

    second_orchestrator.handle_transition_mock.assert_not_called()


@pytest.mark.asyncio
async def test_graph_runner_does_not_report_waiting_when_checkpoint_fails() -> None:
    graph = build_serial_graph(
        nodes=[StasisNode, SuccessNode], state_type=MockState, deps_type=type(None), output_type=str
    )
    occurrences: list[str] = []
    runner = GraphRunner[MockState](
        orchestrator=SimpleMockOrchestrator(),
        persistence=FailingStasisPersistence(),
        signal_priority=50,
        on_node_event=lambda event: occurrences.append(event.phase),
    )

    with pytest.raises(_CheckpointUnavailableError):
        await runner.run_graph(graph, StasisNode(), MockState())

    assert occurrences == ["entered", "failed"]


@pytest.mark.asyncio
async def test_dispatch_drain_race_parks_and_retries_through_graph_runner() -> None:
    """Losing admission is Live Stasis, not a generic run-failing RuntimeError."""
    leases = LeaseLedger()
    registry = DrainRaceRegistry()
    dispatcher = Dispatcher(registry=registry, leases=leases)  # type: ignore[arg-type]
    orchestrator = ReopenAdmissionOrchestrator(leases)
    graph = build_serial_graph(
        nodes=[LeaseAfterDrainRaceNode], state_type=MockState, deps_type=Dispatcher, output_type=str
    )
    runner = GraphRunner[MockState](
        orchestrator=orchestrator,
        persistence=LychDTestPersistence(),
        signal_priority=70,
    )

    run_task = asyncio.create_task(runner.run_graph(graph, LeaseAfterDrainRaceNode(), MockState(), deps=dispatcher))
    await registry.issue_started.wait()
    leases.begin_drain([MOCK_SPEC.animator_name])
    registry.finish_first_issue.set()

    assert await run_task == "leased"
    assert orchestrator.calls == [MOCK_SPEC.key]
    assert registry.issue_count == 2
    assert leases.active() == []


@pytest.mark.asyncio
async def test_graph_runner_threads_signal_priority_and_fires_stasis_callbacks() -> None:
    """O5: the run's priority reaches handle_transition; callbacks bracket the park."""
    persistence = LychDTestPersistence()
    graph = build_serial_graph(
        nodes=[StasisNode, SuccessNode], state_type=MockState, deps_type=type(None), output_type=str
    )
    mock_orchestrator = SimpleMockOrchestrator()
    order: list[str] = []

    async def _enter() -> None:
        order.append("enter")

    async def _exit() -> None:
        order.append("exit")

    async def _transition(*_args: Any, **_kwargs: Any) -> None:
        order.append("transition")

    mock_orchestrator.handle_transition_mock.side_effect = _transition

    runner = GraphRunner[MockState](
        orchestrator=mock_orchestrator,
        persistence=persistence,
        signal_priority=42,
        on_stasis_enter=_enter,
        on_stasis_exit=_exit,
    )

    result = await runner.run_graph(graph, StasisNode(), MockState())

    assert result == "victory"
    _, kwargs = mock_orchestrator.handle_transition_mock.call_args
    assert kwargs["signal_priority"] == 42.0  # the run's priority, not the hardcoded 100.0
    # enter (RUNNING→AWAITING_HARDWARE) precedes the transition; exit (→RUNNING) follows it.
    assert order == ["enter", "transition", "exit"]
