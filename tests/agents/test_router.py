"""Deterministic routing via the WorkflowRegistry (A5 §9 / A5-U7).

The old `submit()` (asyncio.create_task) is gone — the run path is now
`RunEngine.submit` → SAQ → `perform_run` (see tests/unit/domain/cortex and
tests/unit/ghouls). Routing stays a pure, first-match `Trigger` decision.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from pydantic import ValidationError

from lychd.agents.router import Intent
from lychd.agents.workflows import (
    BRIDGE_CHAT,
    DELEGATED_RITE,
    BuiltinWorkflowRegistry,
    builtin_workflow_registry,
    resolve_pinned_workflow,
)


def test_route_delegate_command_selects_delegated_rite_before_default() -> None:
    workflow = builtin_workflow_registry().route(
        Intent(session_id="s", run_id="r", prompt="/delegate inspect this", source="bridge")
    )
    assert workflow.name == "delegated_rite"


@pytest.mark.parametrize(
    "prompt",
    [
        "/delegated ordinary request",
        "/delegatex ordinary request",
        "/delegate/ordinary-request",
    ],
)
def test_route_delegate_command_requires_a_token_boundary(prompt: str) -> None:
    workflow = builtin_workflow_registry().route(Intent(session_id="s", run_id="r", prompt=prompt, source="bridge"))

    assert workflow.name == "bridge_chat"


def test_route_unknown_source_falls_to_default() -> None:
    """An unmatched source falls back to the default (first-registered) workflow."""
    workflow = builtin_workflow_registry().route(
        Intent(session_id="s", run_id="r", prompt="hi", source="somewhere-else")
    )
    assert workflow.name == "bridge_chat"


@pytest.mark.parametrize("priority", [-1, 101])
def test_intent_refuses_priority_outside_doctrine_range(priority: int) -> None:
    with pytest.raises(ValidationError):
        Intent(session_id="s", prompt="hi", priority=priority)


def test_builtin_registry_has_the_exact_ordered_boot_inventory() -> None:
    registry = builtin_workflow_registry()
    assert [(workflow.manifest.key, workflow.manifest.revision) for workflow in registry.all()] == [
        ("bridge_chat", "1"),
        ("delegated_rite", "1"),
    ]


def test_registry_keeps_old_revision_while_new_admissions_use_active_revision() -> None:
    bridge_v2 = replace(
        BRIDGE_CHAT,
        manifest=replace(BRIDGE_CHAT.manifest, revision="2"),
    )
    registry = BuiltinWorkflowRegistry(
        workflows=(BRIDGE_CHAT, bridge_v2, DELEGATED_RITE),
        active_revisions=((BRIDGE_CHAT.name, "2"), (DELEGATED_RITE.name, "1")),
        route_precedence=(DELEGATED_RITE.name,),
        default_name=BRIDGE_CHAT.name,
    )

    admitted = registry.route(Intent(session_id="s", run_id="new", prompt="hi", source="bridge"))

    assert admitted is bridge_v2
    assert registry.get(BRIDGE_CHAT.name) is bridge_v2
    assert registry.get_revision(BRIDGE_CHAT.name, "1") is BRIDGE_CHAT
    assert registry.get_revision(BRIDGE_CHAT.name, "2") is bridge_v2


def test_registry_rejects_ambiguous_inventory_and_routing() -> None:
    bridge_v2 = replace(BRIDGE_CHAT, manifest=replace(BRIDGE_CHAT.manifest, revision="2"))

    with pytest.raises(ValueError, match="multiple revisions requires explicit active revisions"):
        BuiltinWorkflowRegistry(workflows=(BRIDGE_CHAT, bridge_v2))

    with pytest.raises(ValueError, match="multiple workflow names requires explicit route precedence"):
        BuiltinWorkflowRegistry(workflows=(BRIDGE_CHAT, DELEGATED_RITE))

    with pytest.raises(ValueError, match="duplicate Pattern revisions"):
        BuiltinWorkflowRegistry(workflows=(BRIDGE_CHAT, BRIDGE_CHAT))


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
    assert (
        resolve_pinned_workflow(
            registry,
            workflow_name=BRIDGE_CHAT.name,
            snapshot=drifted,
        )
        is None
    )


def test_intent_is_an_immutable_closed_admission_value() -> None:
    intent = Intent(session_id="s", prompt="bounded request")

    with pytest.raises(ValidationError, match="frozen"):
        intent.prompt = "changed after routing"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Intent.model_validate({"session_id": "s", "prompt": "p", "unknown": True})
