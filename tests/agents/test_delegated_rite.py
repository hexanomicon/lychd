"""Offline proof for the reference delegated Pattern."""

from __future__ import annotations

from dataclasses import replace

import pytest
from pydantic_ai.models.test import TestModel
from pydantic_graph import End, GraphRunContext

from lychd.agents.workflows.delegated_rite import (
    DelegatedRiteState,
    DispatchDelegate,
    ProjectDelegatedReply,
)
from lychd.domain.delegation.models import DelegatedAgentJobStatus
from lychd.domain.delegation.services import DelegatedAgentCoordinator, InMemoryDelegatedAgentJobStore
from lychd.domain.delegation.signals import DelegatedAgentPending
from lychd.extensions.builtin.delegation.reference import ReferenceDelegatedAgentRuntime
from tests.agents.conftest import make_services
from tests.agents.fakes import FakeConsents, FakeEvents, FakeOrchestrator, FakeTurns


@pytest.mark.asyncio
async def test_reference_delegated_rite_submits_parks_resumes_and_settles() -> None:
    events, turns, consents, orchestrator = FakeEvents(), FakeTurns(), FakeConsents(), FakeOrchestrator()
    runtime = ReferenceDelegatedAgentRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={runtime.name: runtime},
        store=InMemoryDelegatedAgentJobStore(),
    )
    services = replace(
        make_services(
            model=TestModel(),
            events=events,
            turns=turns,
            consents=consents,
            orchestrator=orchestrator,
        ),
        delegates=coordinator,
    )
    state = DelegatedRiteState(
        session_id="session-1",
        run_id="run-1",
        prompt="/delegate inspect the sealed path",
        request_id="request-1",
    )
    context = GraphRunContext(state=state, deps=services)
    node = DispatchDelegate()

    with pytest.raises(DelegatedAgentPending) as parked:
        await node.run(context)

    assert state.job_id == parked.value.job.job_id
    active = await coordinator.get(parked.value.job.job_id)
    assert active is not None
    assert active.status is DelegatedAgentJobStatus.RUNNING

    settled = await coordinator.refresh(parked.value.job.job_id)
    assert settled.status is DelegatedAgentJobStatus.SUCCEEDED
    project = await node.run(context)
    assert isinstance(project, ProjectDelegatedReply)

    result = await project.run(context)
    assert isinstance(result, End)
    assert result.data == "Reference delegate completed: inspect the sealed path"
    assert turns.added[0][1].content == result.data
    assert "settling" in [payload for _, kind, payload in events.events if kind == "status"]
