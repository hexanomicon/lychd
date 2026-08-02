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
    WORKFLOW_REGISTRY,
    BuiltinWorkflowRegistry,
)


def test_route_bridge_source_selects_bridge_chat() -> None:
    """A bridge-source intent routes to the bridge_chat workflow."""
    workflow = WORKFLOW_REGISTRY.route(Intent(session_id="s", run_id="r", prompt="hi", source="bridge"))
    assert workflow.name == "bridge_chat"


def test_route_delegate_command_selects_delegated_rite_before_default() -> None:
    workflow = WORKFLOW_REGISTRY.route(
        Intent(session_id="s", run_id="r", prompt="/delegate inspect this", source="bridge")
    )
    assert workflow.name == "delegated_rite"


def test_route_unknown_source_falls_to_default() -> None:
    """An unmatched source falls back to the default (first-registered) workflow."""
    workflow = WORKFLOW_REGISTRY.route(Intent(session_id="s", run_id="r", prompt="hi", source="somewhere-else"))
    assert workflow.name == "bridge_chat"


@pytest.mark.parametrize("priority", [-1, 101])
def test_intent_refuses_priority_outside_doctrine_range(priority: int) -> None:
    with pytest.raises(ValidationError):
        Intent(session_id="s", prompt="hi", priority=priority)


def test_registry_get_by_name_and_default() -> None:
    """The registry looks up by persisted name and exposes the route floor."""
    assert WORKFLOW_REGISTRY.get("bridge_chat") is WORKFLOW_REGISTRY.default
    assert WORKFLOW_REGISTRY.get("nonexistent") is None
    assert WORKFLOW_REGISTRY.default.name == "bridge_chat"


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


def test_registry_requires_explicit_activation_for_multiple_revisions() -> None:
    bridge_v2 = replace(BRIDGE_CHAT, manifest=replace(BRIDGE_CHAT.manifest, revision="2"))

    with pytest.raises(ValueError, match="multiple revisions requires explicit active revisions"):
        BuiltinWorkflowRegistry(workflows=(BRIDGE_CHAT, bridge_v2))


def test_registry_requires_explicit_route_precedence_for_multiple_names() -> None:
    with pytest.raises(ValueError, match="multiple workflow names requires explicit route precedence"):
        BuiltinWorkflowRegistry(workflows=(BRIDGE_CHAT, DELEGATED_RITE))


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
