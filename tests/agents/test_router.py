"""New admissions follow explicit routing; recovery resolves the exact pinned revision."""

from __future__ import annotations

from dataclasses import replace

import pytest
from pydantic import ValidationError
from pydantic_graph import BaseNode, End, GraphRunContext

from lychd.agents.router import Intent
from lychd.agents.workflows import (
    BRIDGE_CHAT,
    BRIDGE_CHAT_BOUND,
    DELEGATED_RITE,
    OBSERVE_MARKET,
    BuiltinWorkflowRegistry,
    builtin_workflow_registry,
    resolve_pinned_workflow,
)
from lychd.agents.workflows.base import PatternEdge, PatternManifest, PatternNode, Trigger, Workflow
from lychd.agents.workflows.bridge_chat import BridgeChatState
from lychd.domain.cortex.graph import build_serial_graph


@pytest.mark.parametrize(
    ("prompt", "source", "expected"),
    [
        ("/delegate inspect this", "bridge", DELEGATED_RITE),
        ("/delegated ordinary request", "bridge", BRIDGE_CHAT),
        ("/delegatex ordinary request", "bridge", BRIDGE_CHAT),
        ("/delegate/ordinary-request", "bridge", BRIDGE_CHAT),
        ("hi", "somewhere-else", BRIDGE_CHAT),
    ],
    ids=["command", "past-tense", "suffix", "path", "unknown-source"],
)
def test_route_matches_commands_and_defaults(prompt: str, source: str, expected: Workflow) -> None:
    workflow = builtin_workflow_registry().route(Intent(session_id="s", prompt=prompt, source=source))
    assert workflow is expected


@pytest.mark.parametrize("priority", [-1, 101])
def test_intent_refuses_priority_outside_doctrine_range(priority: int) -> None:
    with pytest.raises(ValidationError):
        Intent(session_id="s", prompt="hi", priority=priority)


def test_builtin_registry_has_the_exact_ordered_boot_inventory() -> None:
    registry = builtin_workflow_registry()
    assert [(workflow.manifest.key, workflow.manifest.revision) for workflow in registry.all()] == [
        ("bridge_chat", "1"),
        ("bridge_chat", "2"),
        ("bridge_chat", "3"),
        ("bridge_chat", "4"),
        ("bridge_chat", "5"),
        ("bridge_chat", "1-naming1"),
        ("bridge_chat", "2-naming1"),
        ("bridge_chat", "3-naming1"),
        ("bridge_chat", "4-naming1"),
        ("bridge_chat", "5-naming1"),
        ("delegated_rite", "1"),
        ("delegated_rite", "2"),
        ("scavenger.observe_market", "2"),
    ]
    for revision in ("1-naming1", "2-naming1", "3-naming1", "4-naming1", "5-naming1"):
        assert registry.is_active("bridge_chat", revision) is False
        assert registry.is_default("bridge_chat", revision) is False
        assert registry.route_rank("bridge_chat", revision) is None
    assert registry.get(OBSERVE_MARKET.name) is None
    assert registry.get_revision(OBSERVE_MARKET.name, "2") is OBSERVE_MARKET
    assert registry.is_active(OBSERVE_MARKET.name, "2") is False


def test_registry_keeps_old_revision_while_new_admissions_use_active_revision() -> None:
    registry = BuiltinWorkflowRegistry(
        workflows=(BRIDGE_CHAT, BRIDGE_CHAT_BOUND, DELEGATED_RITE),
        active_revisions=((BRIDGE_CHAT.name, "2"), (DELEGATED_RITE.name, "1")),
        route_precedence=(DELEGATED_RITE.name,),
        default_name=BRIDGE_CHAT.name,
    )

    admitted = registry.route(Intent(session_id="s", run_id="new", prompt="hi", source="bridge"))

    assert admitted is BRIDGE_CHAT_BOUND
    assert registry.get(BRIDGE_CHAT.name) is BRIDGE_CHAT_BOUND
    assert registry.get_revision(BRIDGE_CHAT.name, "1") is BRIDGE_CHAT
    assert registry.get_revision(BRIDGE_CHAT.name, "2") is BRIDGE_CHAT_BOUND


@pytest.mark.parametrize(
    ("workflows", "message"),
    [
        ((BRIDGE_CHAT, BRIDGE_CHAT_BOUND), "multiple revisions requires explicit active revisions"),
        ((BRIDGE_CHAT, DELEGATED_RITE), "multiple workflow names requires explicit route precedence"),
        ((BRIDGE_CHAT, BRIDGE_CHAT), "duplicate Pattern revisions"),
    ],
    ids=["active-revision", "route-precedence", "duplicate-revision"],
)
def test_registry_rejects_ambiguous_inventory_and_routing(workflows: tuple[Workflow, ...], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        BuiltinWorkflowRegistry(workflows=workflows)


def test_registry_retains_retired_workflow_for_pinned_execution_only() -> None:
    registry = BuiltinWorkflowRegistry(
        workflows=(BRIDGE_CHAT, DELEGATED_RITE),
        active_revisions=((BRIDGE_CHAT.name, BRIDGE_CHAT.manifest.revision),),
        default_name=BRIDGE_CHAT.name,
    )

    routed = registry.route(Intent(session_id="s", run_id="new", prompt="/delegate work", source="bridge"))

    assert routed is BRIDGE_CHAT
    assert registry.get(DELEGATED_RITE.name) is None
    assert registry.get_revision(DELEGATED_RITE.name, DELEGATED_RITE.manifest.revision) is DELEGATED_RITE
    assert registry.is_active(DELEGATED_RITE.name, DELEGATED_RITE.manifest.revision) is False
    assert registry.is_default(BRIDGE_CHAT.name, BRIDGE_CHAT.manifest.revision) is True


def test_pinned_workflow_resolution_requires_exact_owned_snapshot() -> None:
    registry = builtin_workflow_registry()
    snapshot = BRIDGE_CHAT.manifest.snapshot()
    drifted = replace(BRIDGE_CHAT.manifest, implementation_revision="py.drifted").snapshot()

    assert resolve_pinned_workflow(registry, workflow_name=BRIDGE_CHAT.name, snapshot=snapshot) is BRIDGE_CHAT
    assert resolve_pinned_workflow(registry, workflow_name="another_owner", snapshot=snapshot) is None
    assert resolve_pinned_workflow(registry, workflow_name=BRIDGE_CHAT.name, snapshot=drifted) is None


def test_intent_is_an_immutable_closed_admission_value() -> None:
    intent = Intent(session_id="s", prompt="bounded request")

    with pytest.raises(ValidationError, match="frozen"):
        intent.prompt = "changed after routing"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Intent.model_validate({"session_id": "s", "prompt": "p", "unknown": True})


@pytest.fixture
def local_workflow() -> Workflow:
    class LocalNode(BaseNode[BridgeChatState, None, None]):
        async def run(self, ctx: GraphRunContext[BridgeChatState, None]) -> End[None]:  # noqa: ARG002
            return End(None)

    return Workflow(
        name="local",
        title="Local",
        description="Disposable binding fixture",
        trigger=Trigger(hint="/local", match=lambda intent: intent.prompt == "/local"),
        graph=build_serial_graph(
            nodes=(LocalNode,), state_type=BridgeChatState, deps_type=type(None), output_type=type(None)
        ),
        start_node=LocalNode,
        make_state=lambda _intent: BridgeChatState(session_id="s", run_id="r", prompt="p"),
        manifest=PatternManifest(
            key="local",
            revision="1",
            implementation_revision="py.local.1",
            checkpoint_schema="local-v1",
            entry_node="local",
            nodes=(
                PatternNode(key="local", label="Local", implementation=LocalNode),
                PatternNode(key="end", label="End", kind="terminal"),
            ),
            edges=(PatternEdge(key="local-to-end", source="local", target="end"),),
        ),
    )


@pytest.mark.parametrize("attribute", ["__module__", "__qualname__"])
def test_exact_lookup_refuses_changed_local_binding(local_workflow: Workflow, attribute: str) -> None:
    registry = BuiltinWorkflowRegistry(workflows=(local_workflow,))
    snapshot = local_workflow.manifest.snapshot()
    assert registry.get_revision("local", "1") is local_workflow

    previous = getattr(local_workflow.start_node, attribute)
    try:
        setattr(local_workflow.start_node, attribute, "changed_binding")
        assert local_workflow.manifest.snapshot() == snapshot
        assert registry.get_revision("local", "1") is None
        assert resolve_pinned_workflow(registry, workflow_name="local", snapshot=snapshot) is None
        assert tuple(workflow.manifest.snapshot() for workflow in registry.all()) == (snapshot,)
        with pytest.raises(RuntimeError, match=r"binding.*unavailable"):
            registry.route(Intent(session_id="s", prompt="/local"))
    finally:
        setattr(local_workflow.start_node, attribute, previous)

    assert registry.get_revision("local", "1") is local_workflow


def test_unavailable_active_binding_cannot_fall_through_to_default(
    local_workflow: Workflow, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = BuiltinWorkflowRegistry(
        workflows=(local_workflow, BRIDGE_CHAT),
        route_precedence=("local",),
        default_name=BRIDGE_CHAT.name,
    )
    intent = Intent(session_id="s", prompt="/local")
    assert registry.route(intent) is local_workflow
    monkeypatch.setattr(local_workflow.start_node, "__module__", "changed_local_module")

    with pytest.raises(RuntimeError, match=r"binding.*unavailable"):
        registry.route(intent)
