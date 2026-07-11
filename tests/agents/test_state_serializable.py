"""Durable Stasis floor (wave4-design §2.4): workflow State round-trips JSON.

Every registered workflow's State must survive `model_dump_json → model_validate_json`
byte-stable (a durable snapshot is JSONB in Postgres). A `BridgeChatState` carrying real
`to_jsonable_python` messages + `pending_call_ids` must round-trip too. Plus the
tier-selection unit: a Gate-bearing workflow → Durable, a linear one → Live.
"""

# White-box tier-selection assertions reach the module-private helpers.
# pyright: reportPrivateUsage=false
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pydantic_ai.models
import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
from pydantic_core import to_jsonable_python
from pydantic_graph import BaseNode, End, Graph

from lychd.agents.router import Intent
from lychd.agents.workflows import builtin_workflow_registry
from lychd.agents.workflows.base import Gate, Trigger, Workflow
from lychd.agents.workflows.bridge_chat import BridgeChatState
from lychd.domain.cortex.runs import RunRecord, RunStatus
from lychd.domain.cortex.stasis import DurableStasisPhylactery, InMemoryStasisStore, LiveStasisPhylactery
from lychd.ghouls.runs import _phylactery_for

pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


def _intent() -> Intent:
    return Intent(session_id="s1", run_id="r1", prompt="hello", source="bridge")


def test_every_workflow_state_round_trips() -> None:
    for workflow in builtin_workflow_registry().all():
        state = workflow.make_state(_intent())
        # A live handle typed into State would break schema generation.
        state.model_json_schema()
        restored = type(state).model_validate_json(state.model_dump_json())
        assert restored == state


@pytest.mark.asyncio
async def test_bridge_state_round_trips_with_real_messages() -> None:
    agent: Agent[None, str] = Agent(output_type=str)
    result = await agent.run("hello", model=TestModel(custom_output_text="risen"))
    state = BridgeChatState(
        session_id="s1",
        run_id="r1",
        prompt="hello",
        paused_messages=to_jsonable_python(result.all_messages()),
        pending_call_ids=("call_a", "call_b"),
        pending_consent_tool_name="request_coven_swap",
        consent_rounds=1,
    )
    restored = BridgeChatState.model_validate_json(state.model_dump_json())
    assert restored == state
    assert restored.pending_call_ids == ("call_a", "call_b")
    assert restored.paused_messages == state.paused_messages


# -- tier selection ----------------------------------------------------------


class _GateNode(Gate, BaseNode[BridgeChatState, None, None]):
    async def run(self, ctx: Any) -> End[None]:  # noqa: ARG002
        return End(None)


class _PlainNode(BaseNode[BridgeChatState, None, None]):
    async def run(self, ctx: Any) -> End[None]:  # noqa: ARG002
        return End(None)


def _run() -> RunRecord:
    return RunRecord(
        run_id="r1",
        session_id="s1",
        workflow_name="w",
        source="bridge",
        queue_name="runs",
        priority=50,
        status=RunStatus.QUEUED,
        prompt="hi",
    )


def _workflow_for(node: type[BaseNode[Any, Any, Any]]) -> Workflow:
    """Build a minimal real Workflow so `durable` is derived at construction."""
    return Workflow(
        name="t",
        title="t",
        description="",
        trigger=Trigger(hint="", match=lambda _intent: True),
        graph=Graph(nodes=(node,), name="t"),
        start_node=node,
        make_state=lambda _intent: BridgeChatState(session_id="s", run_id="r", prompt="p"),
    )


def test_gate_workflow_selects_durable() -> None:
    workflow = _workflow_for(_GateNode)
    assert workflow.durable is True  # derived from the Gate node at construction
    substrate = SimpleNamespace(stasis_store=InMemoryStasisStore())
    phy = _phylactery_for(_run(), workflow, substrate)  # type: ignore[arg-type]
    assert isinstance(phy, DurableStasisPhylactery)


def test_linear_workflow_selects_live() -> None:
    workflow = _workflow_for(_PlainNode)
    assert workflow.durable is False
    substrate = SimpleNamespace(stasis_store=InMemoryStasisStore())
    phy = _phylactery_for(_run(), workflow, substrate)  # type: ignore[arg-type]
    assert isinstance(phy, LiveStasisPhylactery)


@pytest.mark.asyncio
async def test_durable_store_is_run_owned_and_returns_copies() -> None:
    store = InMemoryStasisStore()
    snapshots = [{"state": {"prompt": "hello"}}]

    await store.replace("r1", snapshots)
    snapshots[0]["state"]["prompt"] = "mutated after write"

    restored = await store.load("r1")
    assert restored == [{"state": {"prompt": "hello"}}]
    assert await store.exists("r1")
    assert not await store.exists("r2")

    restored[0]["state"]["prompt"] = "mutated after read"  # type: ignore[index]
    assert await store.load("r1") == [{"state": {"prompt": "hello"}}]

    await store.delete("r1")
    assert not await store.exists("r1")
