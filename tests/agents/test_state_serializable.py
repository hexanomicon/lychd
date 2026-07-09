"""Durable Stasis floor (wave4-design §2.4): workflow State round-trips JSON.

Every registered workflow's State must survive `model_dump_json → model_validate_json`
byte-stable (a durable snapshot is JSON on disk). A `BridgeChatState` carrying real
`to_jsonable_python` messages + `pending_call_ids` must round-trip too. Plus the
tier-selection unit: a Gate-bearing workflow → Durable, a linear one → Live.
"""

# White-box tier-selection assertions reach the module-private helpers.
# pyright: reportPrivateUsage=false
from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

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
from lychd.domain.cortex.stasis import DurableStasisPhylactery, LiveStasisPhylactery
from lychd.ghouls.runs import _phylactery_for

if TYPE_CHECKING:
    from pathlib import Path

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


def _run(stasis_path: str | None = None) -> RunRecord:
    return RunRecord(
        run_id="r1",
        session_id="s1",
        workflow_name="w",
        source="bridge",
        queue_name="runs",
        priority=50,
        status=RunStatus.QUEUED,
        prompt="hi",
        stasis_path=stasis_path,
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


def test_gate_workflow_selects_durable(tmp_path: Path) -> None:
    workflow = _workflow_for(_GateNode)
    assert workflow.durable is True  # derived from the Gate node at construction
    phy = _phylactery_for(_run(), workflow, tmp_path)
    assert isinstance(phy, DurableStasisPhylactery)


def test_linear_workflow_selects_live(tmp_path: Path) -> None:
    workflow = _workflow_for(_PlainNode)
    assert workflow.durable is False
    phy = _phylactery_for(_run(), workflow, tmp_path)
    assert isinstance(phy, LiveStasisPhylactery)


def test_resume_from_stasis_path_is_durable(tmp_path: Path) -> None:
    workflow = SimpleNamespace(graph=Graph(nodes=(_PlainNode,), name="plain"))
    checkpoint = tmp_path / "r1.json"
    phy = _phylactery_for(_run(stasis_path=str(checkpoint)), workflow, tmp_path)  # type: ignore[arg-type]
    assert isinstance(phy, DurableStasisPhylactery)
    assert phy.json_file == checkpoint


def test_durable_checkpoint_save_is_atomic_and_owner_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checkpoint = tmp_path / "r1.json"
    phy = DurableStasisPhylactery(job_id="r1", json_file=checkpoint)

    def dump_json(_snapshots: object, *, indent: int | None = None) -> bytes:
        _ = indent
        return b"[]"

    adapter: Any = SimpleNamespace(dump_json=dump_json)
    phy._snapshots_type_adapter = adapter
    phy._save_sync([])
    original = checkpoint.read_bytes()

    def fail_replace(self: Path, target: Path) -> None:
        _ = (self, target)
        msg = "simulated crash before rename"
        raise OSError(msg)

    monkeypatch.setattr(type(checkpoint), "replace", fail_replace)
    with pytest.raises(OSError, match="simulated crash"):
        phy._save_sync([])

    assert checkpoint.read_bytes() == original
    assert checkpoint.stat().st_mode & 0o777 == 0o600
    assert list(tmp_path.glob(".r1.json.*.tmp")) == []


@pytest.mark.asyncio
async def test_durable_lock_ignores_upstream_stale_marker(tmp_path: Path) -> None:
    checkpoint = tmp_path / "r1.json"
    stale = tmp_path / "r1.json.pydantic-graph-persistence-lock"
    stale.write_text("crash residue", encoding="utf-8")
    phy = DurableStasisPhylactery(job_id="r1", json_file=checkpoint)

    async with phy._lock(timeout=0.1):
        assert stale.exists()
