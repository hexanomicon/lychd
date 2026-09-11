"""Broken node projections preserve execution, park, failure, and cancellation truth."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Literal

import pytest
from pydantic import BaseModel, Field
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.domain.animation.errors import HardwareTransitionRequired
from lychd.domain.cortex.graph import build_serial_graph
from lychd.domain.cortex.graph_runner import GraphRunner, HardwareResumeBudget, NodeOccurrenceEvent
from lychd.domain.cortex.runs import ConsentPending, RunParked
from lychd.domain.cortex.stasis import DurableStasisPhylactery, InMemoryStasisStore
from lychd.domain.delegation import (
    DelegatedAgentJobRef,
    DelegatedAgentParked,
    DelegatedAgentPending,
    DelegatedAgentProfile,
)


class _State(BaseModel):
    outcome: Literal["success", "failure", "consent", "delegate", "hardware"] = "success"
    calls: int = 0
    hardware_resume_budget: HardwareResumeBudget = Field(default_factory=HardwareResumeBudget)


class _WorkFailedError(RuntimeError):
    pass


@dataclass
class _Work(BaseNode[_State, None, str]):
    async def run(self, ctx: GraphRunContext[_State, None]) -> End[str]:
        ctx.state.calls += 1
        match ctx.state.outcome:
            case "failure":
                msg = "The work failed."
                raise _WorkFailedError(msg)
            case "consent":
                consent_id = "consent-1"
                raise ConsentPending(consent_id, "run-1", "effect")
            case "delegate":
                raise DelegatedAgentPending(
                    DelegatedAgentJobRef(
                        job_id="job-1",
                        request_id="request-1",
                        run_id="run-1",
                        runtime="inert",
                        profile=DelegatedAgentProfile.READ,
                    )
                )
            case "hardware" if ctx.state.calls == 1:
                capability_key = "inert:chat:model"
                raise HardwareTransitionRequired(capability_key)
            case "success" | "hardware":
                pass
        return End("completed")


class _InertOrchestrator:
    calls: int = 0

    async def handle_transition(self, *_args: Any, **_kwargs: Any) -> None:
        self.calls += 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("outcome", "broken_phase"),
    [
        ("success", "entered"),
        ("success", "settled"),
        ("failure", "entered"),
        ("failure", "failed"),
        ("consent", "waiting"),
        ("delegate", "waiting"),
        ("hardware", "waiting"),
    ],
)
async def test_broken_node_observer_preserves_execution_outcome(
    outcome: Literal["success", "failure", "consent", "delegate", "hardware"],
    broken_phase: str,
) -> None:
    events: list[NodeOccurrenceEvent] = []

    def observe(event: NodeOccurrenceEvent) -> None:
        events.append(event)
        if event.phase == broken_phase:
            msg = "The projection is unavailable."
            raise ValueError(msg)

    store = InMemoryStasisStore()
    orchestrator = _InertOrchestrator()
    runner = GraphRunner[_State](
        orchestrator=orchestrator,
        persistence=DurableStasisPhylactery(job_id="run-1", store=store),
        signal_priority=50,
        on_node_event=observe,
        run_id="run-1",
    )
    state = _State(outcome=outcome)
    graph = build_serial_graph(nodes=(_Work,), state_type=_State, deps_type=type(None), output_type=str)
    if outcome == "failure":
        with pytest.raises(_WorkFailedError, match="The work failed"):
            await runner.run_graph(graph, _Work(), state)
        assert [event.phase for event in events] == ["entered", "failed"]
    else:
        result = await runner.run_graph(graph, _Work(), state)
        if outcome == "consent":
            assert isinstance(result, RunParked)
            assert result.consent_id == "consent-1"
        elif outcome == "delegate":
            assert isinstance(result, DelegatedAgentParked)
            assert result.job.job_id == "job-1"
        else:
            assert result == "completed"
        if outcome in {"consent", "delegate"}:
            assert [event.phase for event in events] == ["entered", "waiting"]
            assert events[-1].wait_kind == outcome
            assert await store.exists("run-1")
        elif outcome == "hardware":
            assert [event.phase for event in events] == ["entered", "waiting", "entered", "settled"]
            assert events[1].wait_kind == "hardware"
    assert state.calls == 1
    assert orchestrator.calls == int(outcome == "hardware")
    assert any(event.phase == broken_phase for event in events)


@pytest.mark.asyncio
async def test_node_observer_cancellation_remains_control_flow() -> None:
    cancellation = asyncio.CancelledError("The caller cancelled.")

    def observe(_event: NodeOccurrenceEvent) -> None:
        raise cancellation

    runner = GraphRunner[_State](
        orchestrator=_InertOrchestrator(),
        persistence=DurableStasisPhylactery(job_id="run-1", store=InMemoryStasisStore()),
        signal_priority=50,
        on_node_event=observe,
    )
    state = _State()
    with pytest.raises(asyncio.CancelledError) as caught:
        await runner.run_graph(
            build_serial_graph(nodes=(_Work,), state_type=_State, deps_type=type(None), output_type=str), _Work(), state
        )
    assert caught.value is cancellation
    assert state.calls == 0
