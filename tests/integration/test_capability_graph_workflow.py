"""Checkpointed workflow recovery across real capability and orchestration offices.

The host/runtime world and model responses are deterministic substitutes; the
registry, grant ledger, Dispatcher, Orchestrator, graph, and JSON checkpoint path
all retain production behavior. This is not a host or PostgreSQL receipt.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import pytest
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_graph import BaseNode, End, Graph, GraphRunContext
from pydantic_graph.persistence import NodeSnapshot

from lychd.domain.cortex.graph_runner import GraphRunner, HardwareResumeBudget, NodeOccurrenceEvent
from lychd.domain.cortex.leases import AnimatorAdmission
from lychd.domain.cortex.stasis import DurableStasisPhylactery, InMemoryStasisStore
from tests.capability_workflows import CapabilityScenario, build_capability_scenario


class WorkflowState(BaseModel):
    hardware_resume_budget: HardwareResumeBudget = Field(default_factory=HardwareResumeBudget)
    completed: list[str] = Field(default_factory=list)
    grant_ids: list[str] = Field(default_factory=list)
    draft: str = ""
    answer: str = ""


@dataclass
class WorkflowDeps:
    scenario: CapabilityScenario
    answer_model: str = "a-model"
    attempts: list[str] = field(default_factory=list)


@dataclass
class Draft(BaseNode[WorkflowState, WorkflowDeps, WorkflowState]):
    async def run(self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]) -> Answer:
        ctx.deps.attempts.append("draft")
        async with ctx.deps.scenario.dispatcher.lease_grant(
            family="chat", model_name="a-model", run_id="checkpoint-workflow"
        ) as grant:
            assert grant.model is not None
            result = await Agent(model=grant.model).run("Draft a brief answer")
            ctx.state.draft = result.output
            ctx.state.grant_ids.append(grant.lease.grant_id)
            ctx.state.completed.append("draft")
        return Answer(model_name=ctx.deps.answer_model)


@dataclass
class Answer(BaseNode[WorkflowState, WorkflowDeps, WorkflowState]):
    model_name: str = "a-model"

    async def run(self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]) -> End[WorkflowState]:
        ctx.deps.attempts.append("answer")
        async with ctx.deps.scenario.dispatcher.lease_grant(
            family="chat", model_name=self.model_name, run_id="checkpoint-workflow"
        ) as grant:
            assert grant.model is not None
            assert grant.spec.model_id == self.model_name
            assert len(ctx.deps.scenario.leases.active()) == 1
            result = await Agent(model=grant.model).run(ctx.state.draft)
            ctx.state.answer = result.output
            ctx.state.grant_ids.append(grant.lease.grant_id)
            ctx.state.completed.append("answer")
        return End(ctx.state)


async def _assert_interrupted_answer_checkpoint(
    persistence: DurableStasisPhylactery,
    store: InMemoryStasisStore,
) -> None:
    snapshots = await persistence.load_all()
    pending = [
        snapshot for snapshot in snapshots if isinstance(snapshot, NodeSnapshot) and snapshot.status == "created"
    ]
    assert len(pending) == 1
    assert isinstance(pending[0].node, Answer)
    assert pending[0].state.completed == ["draft"]
    assert len(pending[0].state.grant_ids) == 1
    assert pending[0].state.hardware_resume_budget.total_resumes == 1
    # Store values must survive ordinary JSON transport. No live model,
    # connector, lease, or runtime dependency can hide in checkpoint state.
    document = await store.load("checkpoint-workflow")
    assert json.loads(json.dumps(document)) == document


@pytest.mark.asyncio
@pytest.mark.parametrize("answer_model", ["a-model", "b-model"], ids=["issue-time-loss", "second-capability"])
async def test_hardware_wait_rehydrates_only_interrupted_node_after_real_convergence(answer_model: str) -> None:
    scenario = build_capability_scenario(active={"a"})
    observations = 0

    async def lose_model_at_second_node_issue(name: str) -> None:
        nonlocal observations
        if name == "a":
            observations += 1
            # The draft leases on observations 1/2. Answer's preflight sees
            # WARM on 3, then exact registry issue sees COLD on observation 4.
            if observations == 4:
                scenario.world.active.remove("a")

    if answer_model == "a-model":
        scenario.world.before_probe = lose_model_at_second_node_issue
    store = InMemoryStasisStore()
    persistence = DurableStasisPhylactery(job_id="checkpoint-workflow", store=store)
    graph = Graph(nodes=(Draft, Answer), name="capability-recovery")
    deps = WorkflowDeps(scenario, answer_model=answer_model)
    target_animator = "a" if answer_model == "a-model" else "b"
    occurrences: list[NodeOccurrenceEvent] = []
    stasis_edges: list[str] = []

    async def enter_stasis() -> None:
        stasis_edges.append("enter")
        assert scenario.leases.active() == []
        assert scenario.world.active == (set() if target_animator == "a" else {"a"})
        assert occurrences[-1].wait_kind == "hardware"
        await _assert_interrupted_answer_checkpoint(persistence, store)

    async def exit_stasis() -> None:
        stasis_edges.append("exit")
        assert scenario.world.active == {target_animator}
        assert scenario.leases.active() == []
        assert scenario.leases.admission("a") is AnimatorAdmission.OPEN
        assert scenario.leases.admission(target_animator) is AnimatorAdmission.OPEN

    runner: GraphRunner[WorkflowState] = GraphRunner(
        orchestrator=scenario.manager,
        persistence=persistence,
        signal_priority=50,
        on_stasis_enter=enter_stasis,
        on_stasis_exit=exit_stasis,
        on_node_event=occurrences.append,
        run_id="checkpoint-workflow",
    )
    initial = WorkflowState()
    async with asyncio.timeout(2):
        result = await runner.run_graph(graph, Draft(), initial, deps=deps)

    assert isinstance(result, WorkflowState)
    assert result is not initial
    assert result.completed == ["draft", "answer"]
    assert deps.attempts == ["draft", "answer", "answer"]
    assert result.draft
    assert result.answer
    assert len(result.grant_ids) == len(set(result.grant_ids)) == 2
    assert result.hardware_resume_budget.total_resumes == 1
    assert stasis_edges == ["enter", "exit"]
    assert [(event.node_type.__name__, event.phase) for event in occurrences] == [
        ("Draft", "entered"),
        ("Draft", "settled"),
        ("Answer", "entered"),
        ("Answer", "waiting"),
        ("Answer", "entered"),
        ("Answer", "settled"),
    ]
    assert len(scenario.actuator.intents) == 1
    assert scenario.actuator.intents[0].launch_animators == (target_animator,)
    assert scenario.actuator.intents[0].evict_animators == (() if target_animator == "a" else ("a",))
    assert scenario.leases.active() == []
    assert scenario.broker.paused is False
    assert await store.exists("checkpoint-workflow")
