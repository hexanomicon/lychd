"""Native builder migration keeps exact typed v1 cursors without replaying uncertain work."""

# Exercise the production worker's initial-resume validator with captured Run truth.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import copy
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, Field
from pydantic_ai.models.function import DeltaToolCall, FunctionModel
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.agents.workflows import BRIDGE_CHAT, DELEGATED_RITE, builtin_workflow_registry, resolve_pinned_workflow
from lychd.agents.workflows.bridge_chat import BridgeChatState
from lychd.domain.cortex.graph import build_serial_graph
from lychd.domain.cortex.graph_runner import GraphRunner, HardwareResumeBudget
from lychd.domain.cortex.runs import RunRecord, RunStatus
from lychd.domain.cortex.stasis import DurableStasisPhylactery, InMemoryStasisStore, NodeSnapshot
from lychd.ghouls.runs import _validate_resume_owner
from tests.agents.conftest import make_services
from tests.agents.fakes import FakeConsents, FakeEvents, FakeOrchestrator, FakeTurns, approval_test_toolset

_FIXTURES = Path(__file__).parents[1] / "fixtures" / "graph" / "v1"


class _NoHardwareOrchestrator(FakeOrchestrator):
    async def handle_transition(self, *_args: Any, **_kwargs: Any) -> None:
        pytest.fail("a captured consent continuation must not request hardware")


def _fixture(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES / f"{name}.json").read_text())


@pytest.mark.parametrize("name", ["consent-created", "consent-pending", "delegate-created"])
@pytest.mark.asyncio
async def test_v1_checkpoint_decodes_against_its_exact_retained_pattern(name: str) -> None:
    captured = _fixture(name)
    saved_run = captured["run"]
    workflow = resolve_pinned_workflow(
        builtin_workflow_registry(), workflow_name=saved_run["workflow_name"], snapshot=saved_run["pattern_manifest"]
    )
    assert workflow in (BRIDGE_CHAT, DELEGATED_RITE)
    assert workflow is not None
    store = InMemoryStasisStore()
    await store.replace(saved_run["run_id"], captured["snapshots"])
    persistence = DurableStasisPhylactery(job_id=saved_run["run_id"], store=store)
    persistence.set_graph_types(workflow.graph)

    decoded = await persistence.load_all()
    assert [item.id for item in decoded] == [item["id"] for item in captured["snapshots"]]
    last = decoded[-1]
    assert isinstance(last, NodeSnapshot)
    assert last.status == ("pending" if name == "consent-pending" else "created")
    assert last.state.model_dump(mode="json") == captured["snapshots"][-1]["state"]
    assert last.node.get_node_id() == captured["snapshots"][-1]["node"]["node_id"]
    if name == "consent-pending":
        assert await persistence.load_next() is None
    else:
        resumed = await persistence.load_next()
        assert resumed is not None
        assert resumed.id == last.id
        assert resumed.status == "pending"


@pytest.mark.parametrize("approved", [True, False])
@pytest.mark.asyncio
async def test_v1_consent_checkpoint_resumes_native_builder_with_its_exact_verdict(*, approved: bool) -> None:
    captured = _fixture("consent-created")
    saved_run = captured["run"]
    run = RunRecord(
        run_id=saved_run["run_id"],
        session_id=saved_run["session_id"],
        workflow_name=saved_run["workflow_name"],
        pattern_manifest=saved_run["pattern_manifest"],
        source=saved_run["source"],
        queue_name=saved_run["queue_name"],
        priority=saved_run["priority"],
        status=RunStatus.RUNNING,
        prompt=saved_run["prompt"],
        consent_id=saved_run["consent_id"],
    )
    store = InMemoryStasisStore()
    await store.replace(run.run_id, captured["snapshots"])
    persistence = DurableStasisPhylactery(job_id=run.run_id, store=store)
    events, turns, orchestrator = FakeEvents(), FakeTurns(), _NoHardwareOrchestrator()

    async def settle(_messages: Any, info: Any) -> AsyncIterator[dict[int, DeltaToolCall]]:
        yield {
            0: DeltaToolCall(
                name=info.output_tools[0].name, json_args='{"answer":"done","fragments":[]}', tool_call_id="reply"
            )
        }

    services = make_services(
        model=FunctionModel(stream_function=settle),
        events=events,
        turns=turns,
        consents=FakeConsents(verdicts={saved_run["consent_id"]: approved}),
        orchestrator=orchestrator,
        toolsets=(approval_test_toolset(),),
    )
    assert BRIDGE_CHAT.validate_state is not None
    runner = GraphRunner[BridgeChatState](
        orchestrator=orchestrator,
        persistence=persistence,
        signal_priority=run.priority,
        validate_state=partial(BRIDGE_CHAT.validate_state, run.to_intent()),
        validate_resume=partial(_validate_resume_owner, run),
    )
    output = await runner.resume_graph(BRIDGE_CHAT.graph, deps=services)
    assert output.answer == "done"
    assert len(orchestrator.calls) == int(approved)
    assert await store.exists(run.run_id)  # caller still owns terminal settlement and deletion


class _BudgetState(BaseModel):
    data: str
    warm: bool
    hardware_resume_budget: HardwareResumeBudget = Field(default_factory=HardwareResumeBudget)


@dataclass
class StasisAcrossDurableParkNode(BaseNode[_BudgetState, None, None]):
    async def run(self, ctx: GraphRunContext[_BudgetState, None]) -> End[None]:
        _ = ctx
        pytest.fail("decoding a hardware checkpoint must not execute its station")


@pytest.mark.asyncio
async def test_v1_hardware_resume_budget_survives_codec_replacement() -> None:
    graph = build_serial_graph(
        nodes=[StasisAcrossDurableParkNode], state_type=_BudgetState, deps_type=type(None), output_type=type(None)
    )
    store = InMemoryStasisStore()
    await store.replace("hardware", _fixture("hardware-budget")["snapshots"])
    persistence = DurableStasisPhylactery(job_id="hardware", store=store)
    persistence.set_graph_types(graph)
    restored = await persistence.load_next()
    assert restored is not None
    assert restored.state.hardware_resume_budget.total_resumes == 1
    assert restored.state.hardware_resume_budget.same_capability_resumes == 1
    assert restored.state.hardware_resume_budget.same_capability_key == "mock-anim:chat:mock-cap"


@pytest.mark.parametrize(
    "corruption", ["unknown-node", "unknown-node-field", "duplicate-id", "multiple-created", "invalid-state"]
)
@pytest.mark.asyncio
async def test_checkpoint_codec_refuses_unbound_or_ambiguous_history(corruption: str) -> None:
    snapshots = _fixture("consent-created")["snapshots"]
    if corruption == "unknown-node":
        snapshots[-1]["node"]["node_id"] = "ForeignEffect"
    elif corruption == "unknown-node-field":
        snapshots[-1]["node"]["effect"] = "injected"
    elif corruption == "duplicate-id":
        snapshots[-1]["id"] = snapshots[0]["id"]
    elif corruption == "multiple-created":
        duplicate = copy.deepcopy(snapshots[-1])
        duplicate["id"] += "-extra"
        snapshots.append(duplicate)
    else:
        snapshots[-1]["state"]["priority"] = "not-a-priority"
    store = InMemoryStasisStore()
    await store.replace("hostile", snapshots)
    persistence = DurableStasisPhylactery(job_id="hostile", store=store)
    persistence.set_graph_types(BRIDGE_CHAT.graph)
    message = {
        "unknown-node": "not in its admitted graph",
        "unknown-node-field": "unknown fields",
        "duplicate-id": "snapshot ids must be unique",
        "multiple-created": "multiple resumable stations",
        "invalid-state": "priority",
    }[corruption]
    with pytest.raises(ValueError, match=message):
        await persistence.load_next()
