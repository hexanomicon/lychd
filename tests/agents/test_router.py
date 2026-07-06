"""Deterministic routing via the WorkflowRegistry (A5 §9 / A5-U7).

The old `submit()` (asyncio.create_task) is gone — the run path is now
`RunEngine.submit` → SAQ → `perform_run` (see tests/unit/domain/cortex and
tests/unit/ghouls). Routing stays a pure, first-match `Trigger` decision.
"""

from __future__ import annotations

from lychd.agents.router import Intent, route
from lychd.agents.workflows import WORKFLOW_REGISTRY


def test_route_bridge_source_selects_bridge_chat() -> None:
    """A bridge-source intent routes to the bridge_chat workflow."""
    workflow = route(Intent(session_id="s", run_id="r", prompt="hi", source="bridge"))
    assert workflow.name == "bridge_chat"


def test_route_unknown_source_falls_to_default() -> None:
    """An unmatched source falls back to the default (first-registered) workflow."""
    workflow = route(Intent(session_id="s", run_id="r", prompt="hi", source="somewhere-else"))
    assert workflow.name == "bridge_chat"


def test_registry_get_by_name_and_default() -> None:
    """The registry looks up by persisted name and exposes the route floor."""
    assert WORKFLOW_REGISTRY.get("bridge_chat") is WORKFLOW_REGISTRY.default
    assert WORKFLOW_REGISTRY.get("nonexistent") is None
    assert WORKFLOW_REGISTRY.default.name == "bridge_chat"
