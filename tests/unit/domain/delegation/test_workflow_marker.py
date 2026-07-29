from __future__ import annotations

from dataclasses import dataclass

import pytest
from pydantic import BaseModel
from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from lychd.agents.workflows.base import (
    DelegatedAgentNode,
    PatternEdge,
    PatternManifest,
    PatternNode,
    Trigger,
    Workflow,
)


class _State(BaseModel):
    run_id: str


@dataclass
class _Delegate(DelegatedAgentNode, BaseNode[_State, None, None]):
    async def run(self, ctx: GraphRunContext[_State, None]) -> End[None]:
        _ = ctx
        return End(None)


def _workflow() -> Workflow:
    graph = Graph(nodes=(_Delegate,), name="delegated")
    return Workflow(
        name="delegated",
        title="Delegated",
        description="",
        trigger=Trigger(hint="", match=lambda _intent: True),
        graph=graph,
        start_node=_Delegate,
        make_state=lambda _intent: _State(run_id="run-1"),
        manifest=PatternManifest(
            key="delegated",
            revision="1",
            checkpoint_schema="delegated-v1",
            nodes=(
                PatternNode(
                    key="delegate",
                    label="Delegate",
                    kind="delegate",
                    implementation=_Delegate,
                ),
                PatternNode(key="end", label="End", kind="terminal"),
            ),
            edges=(PatternEdge(key="delegate-to-end", source="delegate", target="end"),),
        ),
    )


def test_delegated_agent_marker_forces_durable_workflow() -> None:
    assert _workflow().durable is True


def test_delegated_agent_marker_requires_delegate_manifest_kind() -> None:
    with pytest.raises(ValueError, match="kind='delegate'"):
        PatternNode(key="delegate", label="Delegate", implementation=_Delegate)
