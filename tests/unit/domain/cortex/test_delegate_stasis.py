from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import BaseModel
from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from lychd.domain.cortex.graph_runner import GraphRunner, NodeOccurrenceEvent
from lychd.domain.cortex.runs import RunStatus, can_transition
from lychd.domain.cortex.stasis import LiveStasisPhylactery
from lychd.domain.delegation import (
    DelegatedAgentJobRef,
    DelegatedAgentParked,
    DelegatedAgentPending,
    DelegatedAgentProfile,
)


class _State(BaseModel):
    run_id: str
    delegated_job: DelegatedAgentJobRef | None = None


@dataclass
class _DelegateNode(BaseNode[_State, None, None]):
    async def run(self, ctx: GraphRunContext[_State, None]) -> End[None]:
        job = DelegatedAgentJobRef(
            job_id="job-1",
            request_id="request-1",
            run_id=ctx.state.run_id,
            runtime="fake",
            profile=DelegatedAgentProfile.READ,
        )
        ctx.state.delegated_job = job
        raise DelegatedAgentPending(job)


class _UnusedOrchestrator:
    async def handle_transition(self, *_args: Any, **_kwargs: Any) -> None:
        pytest.fail("delegated-agent parking must not invoke hardware orchestration")


@pytest.mark.asyncio
async def test_graph_runner_checkpoints_and_parks_delegated_agent_signal() -> None:
    persistence = LiveStasisPhylactery(job_id="run-1")
    events: list[NodeOccurrenceEvent] = []
    runner: GraphRunner[_State] = GraphRunner(
        orchestrator=_UnusedOrchestrator(),
        persistence=persistence,
        signal_priority=50,
        on_node_event=events.append,
        run_id="run-1",
    )
    graph = Graph(nodes=(_DelegateNode,), name="delegate")

    parked = await runner.run_graph(
        graph,
        _DelegateNode(),
        _State(run_id="run-1"),
    )

    assert isinstance(parked, DelegatedAgentParked)
    assert parked.job.job_id == "job-1"
    assert [(event.phase, event.wait_kind) for event in events] == [
        ("entered", None),
        ("waiting", "delegate"),
    ]
    waiting = events[-1]
    assert waiting.delegated_job_id == "job-1"
    assert waiting.delegated_runtime == "fake"
    snapshots = await persistence.load_all()
    assert snapshots


def test_delegated_wait_has_only_resume_or_cancel_edges() -> None:
    assert can_transition(RunStatus.RUNNING, RunStatus.AWAITING_DELEGATE)
    assert can_transition(RunStatus.AWAITING_DELEGATE, RunStatus.QUEUED)
    assert can_transition(RunStatus.AWAITING_DELEGATE, RunStatus.CANCELLING)
    assert can_transition(RunStatus.CANCELLING, RunStatus.CANCELLED)
    assert not can_transition(RunStatus.AWAITING_DELEGATE, RunStatus.DONE)
