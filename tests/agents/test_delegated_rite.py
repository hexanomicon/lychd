"""Offline proof for the reference delegated Pattern."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from pydantic_ai.models.test import TestModel
from pydantic_graph import End, GraphRunContext

from lychd.agents.router import Intent
from lychd.agents.workflows.delegated_rite import (
    DELEGATED_RITE,
    DelegatedRiteState,
    DispatchDelegate,
    ProjectDelegatedReply,
)
from lychd.domain.delegation.models import DelegatedAgentJobStatus, DelegatedAgentRequest
from lychd.domain.delegation.services import DelegatedAgentCoordinator, InMemoryDelegatedAgentJobStore
from lychd.domain.delegation.signals import DelegatedAgentPending
from lychd.extensions.builtin.delegation.reference import ReferenceDelegatedAgentRuntime
from tests.agents.conftest import make_services
from tests.agents.fakes import FakeConsents, FakeEvents, FakeOrchestrator, FakeTurns

if TYPE_CHECKING:
    from lychd.agents.services import WorkflowServices


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


@pytest.mark.parametrize("field", ["run_id", "session_id", "prompt"])
def test_delegated_rite_checkpoint_must_match_admitted_run(field: str) -> None:
    intent = Intent(session_id="session-1", run_id="run-1", prompt="/delegate inspect")
    state = DELEGATED_RITE.make_state(intent)
    assert DELEGATED_RITE.validate_state is not None
    DELEGATED_RITE.validate_state(intent, state)

    restored = DelegatedRiteState.model_validate_json(state.model_copy(update={field: "changed"}).model_dump_json())
    with pytest.raises(ValueError, match="checkpoint does not match its admitted Run"):
        DELEGATED_RITE.validate_state(intent, restored)


@pytest.mark.asyncio
@pytest.mark.parametrize("settled", [False, True], ids=["running", "succeeded"])
@pytest.mark.parametrize("field", ["run_id", "request_id", "step_id", "prompt"])
async def test_delegated_rite_rejects_job_from_another_request(field: str, *, settled: bool) -> None:
    runtime = ReferenceDelegatedAgentRuntime()
    coordinator = DelegatedAgentCoordinator(
        runtimes={runtime.name: runtime},
        store=InMemoryDelegatedAgentJobStore(),
    )
    request = DelegatedAgentRequest(
        request_id="request-1",
        run_id="run-1",
        step_id="dispatch_delegate",
        runtime="reference",
        prompt="inspect",
    )
    foreign = request.model_copy(update={field: "another"})
    ref = await coordinator.submit(foreign)
    if settled:
        await coordinator.refresh(ref.job_id)
    state = DelegatedRiteState(
        session_id="session-1", run_id="run-1", prompt="/delegate inspect", request_id="request-1", job_id=ref.job_id
    )
    services = cast("WorkflowServices", SimpleNamespace(delegates=coordinator))

    with pytest.raises(ValueError, match="does not match this station's admitted request"):
        await DispatchDelegate().run(GraphRunContext(state=state, deps=services))

    assert state.reply is None
    assert len(await coordinator.jobs_for_run(foreign.run_id)) == 1
