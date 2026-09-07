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
from lychd.agents.workflows import BRIDGE_CHAT, BRIDGE_CHAT_BOUND, DELEGATED_RITE, builtin_workflow_registry
from lychd.agents.workflows.base import (
    Gate,
    PatternEdge,
    PatternManifest,
    PatternNode,
    Trigger,
    Workflow,
    pattern_snapshot_is_valid,
)
from lychd.agents.workflows.bridge_chat import BridgeChatState
from lychd.agents.workflows.nodes import ConsentToolBinding
from lychd.domain.cortex.runs import RunRecord, RunStatus
from lychd.domain.cortex.stasis import DurableStasisPhylactery, InMemoryStasisStore, LiveStasisPhylactery
from lychd.ghouls.runs import _phylactery_for

pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


def _intent() -> Intent:
    return Intent(session_id="s1", run_id="r1", prompt="hello", source="bridge")


def test_every_workflow_state_round_trips() -> None:
    for workflow in builtin_workflow_registry().all():
        intent = _intent()
        if workflow is BRIDGE_CHAT_BOUND:
            intent = intent.model_copy(update={"admitted_capability_key": "chat:offline"})
        state = workflow.make_state(intent)
        # A live handle typed into State would break schema generation.
        state.model_json_schema()
        restored = type(state).model_validate_json(state.model_dump_json())
        assert restored == state


@pytest.mark.parametrize(
    ("workflow", "expected_digest"),
    [
        (BRIDGE_CHAT, "e23ba8136df95af26744f1c9eee6ba28ae74a3de4578e9769a775d9985b9d163"),
        (DELEGATED_RITE, "83958866654c06a62276b3894a117cac0a69fa97553451ec59b038c8f64f89ca"),
    ],
)
def test_builtin_pattern_v2_digests_are_frozen(workflow: Workflow, expected_digest: str) -> None:
    assert workflow.manifest.schema_version == 2
    assert workflow.manifest.digest == expected_digest
    assert workflow.manifest.snapshot()["digest"] == expected_digest


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
        pending_consent_tool_binding=ConsentToolBinding(
            capability_key="chat:test",
            toolset_id="test-coven-transition",
            toolset_type="pydantic_ai.toolsets.function.FunctionToolset",
            tool_name="request_coven_swap",
            effect_id="coven.transition",
            effect_revision="test-v1",
            definition_digest="a" * 64,
        ),
        consent_rounds=1,
    )
    restored = BridgeChatState.model_validate_json(state.model_dump_json())
    assert restored == state
    assert restored.pending_call_ids == ("call_a", "call_b")
    assert restored.paused_messages == state.paused_messages
    assert restored.pending_consent_tool_binding == state.pending_consent_tool_binding


# -- tier selection ----------------------------------------------------------


class _GateNode(Gate, BaseNode[BridgeChatState, None, None]):
    async def run(self, ctx: Any) -> End[None]:  # noqa: ARG002
        return End(None)


class _PlainNode(BaseNode[BridgeChatState, None, None]):
    async def run(self, ctx: Any) -> End[None]:  # noqa: ARG002
        return End(None)


class _SecondPlainNode(BaseNode[BridgeChatState, None, None]):
    async def run(self, ctx: Any) -> End[None]:  # noqa: ARG002
        return End(None)


def test_pattern_terminal_remains_declarative() -> None:
    with pytest.raises(ValueError, match="must remain declarative"):
        PatternNode(key="end", label="End", kind="terminal", implementation=_PlainNode)


def _run() -> RunRecord:
    return RunRecord(
        run_id="r1",
        session_id="s1",
        workflow_name="w",
        pattern_manifest={
            "schema_version": 0,
            "key": "w",
            "revision": "legacy-unversioned",
            "checkpoint_schema": "unknown",
            "nodes": [],
            "edges": [],
            "digest": None,
        },
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
        manifest=PatternManifest(
            key="t",
            revision="1",
            implementation_revision="py.test.1",
            checkpoint_schema="test-v1",
            entry_node="node",
            nodes=(
                PatternNode(
                    key="node",
                    label="Node",
                    kind="gate" if issubclass(node, Gate) else "step",
                    implementation=node,
                ),
                PatternNode(key="end", label="End", kind="terminal"),
            ),
            edges=(PatternEdge(key="node-to-end", source="node", target="end"),),
        ),
    )


@pytest.mark.parametrize(
    ("node", "durable", "phylactery_type"),
    [
        (_GateNode, True, DurableStasisPhylactery),
        (_PlainNode, False, LiveStasisPhylactery),
    ],
)
def test_workflow_stasis_tier_follows_gate_presence(
    node: type[BaseNode[Any, Any, Any]],
    *,
    durable: bool,
    phylactery_type: type[object],
) -> None:
    workflow = _workflow_for(node)
    assert workflow.durable is durable
    substrate = SimpleNamespace(stasis_store=InMemoryStasisStore())
    phy = _phylactery_for(_run(), workflow, substrate)  # type: ignore[arg-type]
    assert isinstance(phy, phylactery_type)


def test_pattern_rejects_duplicate_binding_for_non_start_graph_node() -> None:
    manifest = PatternManifest(
        key="duplicate",
        revision="1",
        implementation_revision="py.test.1",
        checkpoint_schema="test-v1",
        entry_node="start",
        nodes=(
            PatternNode(key="start", label="Start", kind="step", implementation=_PlainNode),
            PatternNode(key="second-a", label="Second A", kind="step", implementation=_SecondPlainNode),
            PatternNode(key="second-b", label="Second B", kind="step", implementation=_SecondPlainNode),
        ),
        edges=(),
    )

    with pytest.raises(ValueError, match="bind every graph node exactly once"):
        Workflow(
            name="duplicate",
            title="duplicate",
            description="",
            trigger=Trigger(hint="", match=lambda _intent: True),
            graph=Graph(nodes=(_PlainNode, _SecondPlainNode), name="duplicate"),
            start_node=_PlainNode,
            make_state=lambda _intent: BridgeChatState(session_id="s", run_id="r", prompt="p"),
            manifest=manifest,
        )


def test_pattern_entry_node_is_digested_and_matches_workflow_start() -> None:
    def manifest(entry_node: str) -> PatternManifest:
        return PatternManifest(
            key="entry-bound",
            revision="1",
            implementation_revision="py.test.1",
            checkpoint_schema="test-v1",
            entry_node=entry_node,
            nodes=(
                PatternNode(key="first", label="First", implementation=_PlainNode),
                PatternNode(key="second", label="Second", implementation=_SecondPlainNode),
                PatternNode(key="end", label="End", kind="terminal"),
            ),
            edges=(
                PatternEdge(key="first-to-end", source="first", target="end"),
                PatternEdge(key="second-to-end", source="second", target="end"),
            ),
        )

    first = manifest("first")
    second = manifest("second")
    assert pattern_snapshot_is_valid(first.snapshot())
    assert first.digest != second.digest

    with pytest.raises(ValueError, match="start node must match Pattern entry node 'second'"):
        Workflow(
            name="entry-bound",
            title="entry-bound",
            description="",
            trigger=Trigger(hint="", match=lambda _intent: True),
            graph=Graph(nodes=(_PlainNode, _SecondPlainNode), name="entry-bound"),
            start_node=_PlainNode,
            make_state=lambda _intent: BridgeChatState(session_id="s", run_id="r", prompt="p"),
            manifest=second,
        )


def test_workflow_rejects_start_node_outside_its_graph() -> None:
    with pytest.raises(ValueError, match="start node must belong to its graph"):
        Workflow(
            name="foreign-start",
            title="foreign-start",
            description="",
            trigger=Trigger(hint="", match=lambda _intent: True),
            graph=Graph(nodes=(_PlainNode,), name="foreign-start"),
            start_node=_SecondPlainNode,
            make_state=lambda _intent: BridgeChatState(session_id="s", run_id="r", prompt="p"),
            manifest=PatternManifest(
                key="foreign-start",
                revision="1",
                implementation_revision="py.test.1",
                checkpoint_schema="test-v1",
                entry_node="node",
                nodes=(
                    PatternNode(key="node", label="Node", implementation=_PlainNode),
                    PatternNode(key="end", label="End", kind="terminal"),
                ),
                edges=(PatternEdge(key="node-to-end", source="node", target="end"),),
            ),
        )


@pytest.mark.parametrize(
    ("name", "edges", "match"),
    [
        ("missing-edge", (), r"topology differs.*missing=\[\('node', 'end'\)\]"),
        (
            "extra-edge",
            (
                PatternEdge(key="node-to-end", source="node", target="end"),
                PatternEdge(key="invented-loop", source="node", target="node"),
            ),
            r"topology differs.*extra=\[\('node', 'node'\)\]",
        ),
    ],
)
def test_pattern_edges_must_match_executable_graph(
    name: str,
    edges: tuple[PatternEdge, ...],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        Workflow(
            name=name,
            title=name,
            description="",
            trigger=Trigger(hint="", match=lambda _intent: True),
            graph=Graph(nodes=(_PlainNode,), name=name),
            start_node=_PlainNode,
            make_state=lambda _intent: BridgeChatState(session_id="s", run_id="r", prompt="p"),
            manifest=PatternManifest(
                key=name,
                revision="1",
                implementation_revision="py.test.1",
                checkpoint_schema="test-v1",
                entry_node="node",
                nodes=(
                    PatternNode(key="node", label="Node", implementation=_PlainNode),
                    PatternNode(key="end", label="End", kind="terminal"),
                ),
                edges=edges,
            ),
        )


def test_pattern_rejects_duplicate_semantic_edges() -> None:
    with pytest.raises(ValueError, match="duplicate semantic edges"):
        PatternManifest(
            key="duplicate-edges",
            revision="1",
            implementation_revision="py.test.1",
            checkpoint_schema="test-v1",
            entry_node="node",
            nodes=(
                PatternNode(key="node", label="Node", implementation=_PlainNode),
                PatternNode(key="end", label="End", kind="terminal"),
            ),
            edges=(
                PatternEdge(key="first", source="node", target="end"),
                PatternEdge(key="second", source="node", target="end"),
            ),
        )


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
