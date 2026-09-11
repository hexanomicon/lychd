"""Projection callbacks must never gain authority over physical transition plans."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass
from typing import Any

import pytest
from pydantic import BaseModel, Field
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.domain.animation.errors import HardwareTransitionRequired
from lychd.domain.cortex.graph import build_serial_graph
from lychd.domain.cortex.graph_runner import GraphRunner, HardwareResumeBudget
from lychd.domain.cortex.leases import AnimatorAdmission
from lychd.domain.cortex.stasis import DurableStasisPhylactery, InMemoryStasisStore
from lychd.domain.orchestration.journal import TransitionRecord
from lychd.domain.orchestration.schema import TransitionTrace
from tests.capability_workflows import build_capability_scenario


@pytest.mark.asyncio
@pytest.mark.parametrize("exposure", ["observer-payload", "request-trace"])
async def test_observer_cannot_add_an_undrained_animator_to_the_physical_plan(exposure: str) -> None:
    scenario = build_capability_scenario(
        models={name: (f"{name}-model",) for name in ("a", "b", "c")},
        active={"a", "c"},
        coexist=("c",),
    )
    observations: list[Any] = []

    def observe(record: Any) -> None:
        observations.append(record)
        # A projection must not receive the live plan. A shallow copy would still
        # expose this list after the manager has fixed its affected drain set.
        source = record if exposure == "observer-payload" else trace
        exposed_plan = getattr(source, "plan", None)
        if record.phase == "draining" and exposed_plan is not None:
            exposed_plan.evict_coven_ids.append("c")

    trace = TransitionTrace(target_capability_key="b:chat:b-model", priority=50, observer=observe)
    async with scenario.dispatcher.lease_grant(
        run_id="coexisting-run",
        family="chat",
        model_name="c-model",
        priority=50,
    ):
        plan = await scenario.manager.request_transition("b:chat:b-model", 50, trace=trace)
        assert scenario.leases.admission("c") is AnimatorAdmission.OPEN
        assert len(scenario.leases.active(animator_name="c")) == 1

    assert plan.evict_coven_ids == ["a"]
    assert len(scenario.actuator.intents) == 1
    assert scenario.actuator.intents[0].evict_animators == ("a",)
    assert scenario.world.active == {"b", "c"}
    assert observations
    assert all(isinstance(record, TransitionRecord) for record in observations)
    assert [record.phase for record in observations] == [
        "arbitrating",
        "draining",
        "actuating",
        "verifying",
        "completed",
    ]
    assert observations[-1] is scenario.manager.transitions.get(trace.request_id)
    with pytest.raises(FrozenInstanceError):
        observations[0].phase = "contained_uncertain"
    assert trace.phase == "completed"
    assert trace.action_type == "HARD_SWAP"
    assert trace.total_metabolic_cost == 1.0


class _ObservationState(BaseModel):
    hardware_resume_budget: HardwareResumeBudget = Field(default_factory=HardwareResumeBudget)
    interrupted: bool = False


@dataclass
class _InterruptOnce(BaseNode[_ObservationState, None, str]):
    async def run(self, ctx: GraphRunContext[_ObservationState, None]) -> End[str]:
        if not ctx.state.interrupted:
            ctx.state.interrupted = True
            capability_key = "b:chat:b-model"
            raise HardwareTransitionRequired(capability_key)
        return End("completed")


@dataclass
class _UnobservedOrchestrator:
    """Exercise the graph's fallback phases without the manager's phase callbacks."""

    failure: RuntimeError | None
    calls: int = 0

    async def handle_transition(
        self,
        exception: HardwareTransitionRequired,
        signal_priority: int,
        *,
        trace: TransitionTrace | None = None,
    ) -> None:
        _ = (exception, signal_priority, trace)
        self.calls += 1
        if self.failure is not None:
            raise self.failure


@pytest.mark.asyncio
@pytest.mark.parametrize("transition_fails", [False, True], ids=["completed", "failed"])
@pytest.mark.parametrize("observer_fails", [False, True], ids=["healthy-observer", "broken-observer"])
async def test_graph_transition_observers_preserve_real_completion_or_failure(
    *,
    transition_fails: bool,
    observer_fails: bool,
) -> None:
    failure = RuntimeError("physical transition declined") if transition_fails else None
    orchestrator = _UnobservedOrchestrator(failure)
    observations: list[TransitionRecord] = []

    def observe(record: TransitionRecord) -> None:
        observations.append(record)
        if observer_fails:
            message = "projection unavailable"
            raise ValueError(message)

    store = InMemoryStasisStore()
    runner = GraphRunner[_ObservationState](
        orchestrator=orchestrator,
        persistence=DurableStasisPhylactery(job_id="observer-workflow", store=store),
        signal_priority=50,
        on_transition_event=observe,
        run_id="observer-workflow",
    )
    graph = build_serial_graph(
        nodes=[_InterruptOnce], state_type=_ObservationState, deps_type=type(None), output_type=str
    )
    if failure is not None:
        with pytest.raises(RuntimeError) as caught:
            await runner.run_graph(graph, _InterruptOnce(), _ObservationState())
        assert caught.value is failure
    else:
        assert await runner.run_graph(graph, _InterruptOnce(), _ObservationState()) == "completed"

    assert orchestrator.calls == 1
    assert [record.phase for record in observations] == ["requested", "failed" if transition_fails else "completed"]
    assert all(record.run_id == "observer-workflow" for record in observations)
    assert len({record.request_id for record in observations}) == 1
    assert len({record.occurrence_id for record in observations}) == 1
    assert await store.exists("observer-workflow")
