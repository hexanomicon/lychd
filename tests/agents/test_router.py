"""Deterministic routing + the submit() service-assembly path (A5 §9, §3)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic_ai.models.test import TestModel

from lychd.agents.router import Intent, route, submit
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.web.fragments import build_fragment_registry
from lychd.domain.web.schemas import BridgeTurn
from lychd.domain.web.sessions import BridgeSessionStore
from tests.agents.fakes import FakeDispatcher, FakeOrchestrator, FakeRegistry


def test_route_bridge_source_selects_bridge_chat() -> None:
    """A bridge-source intent routes to the bridge_chat workflow."""
    workflow = route(Intent(session_id="s", run_id="r", prompt="hi", source="bridge"))
    assert workflow.name == "bridge_chat"


def test_route_unknown_source_falls_to_default() -> None:
    """An unmatched source falls back to the default (first-registered) workflow."""
    workflow = route(Intent(session_id="s", run_id="r", prompt="hi", source="somewhere-else"))
    assert workflow.name == "bridge_chat"


@pytest.mark.asyncio
async def test_submit_assembles_services_and_drives_run() -> None:
    """submit() builds WorkflowServices from app.state and drives the graph offline."""
    sessions = BridgeSessionStore()
    session = sessions.create_session(title="t")
    model = TestModel(custom_output_args={"answer": "ok", "fragments": []}, call_tools=[])
    state = SimpleNamespace(
        dispatcher=FakeDispatcher(model=model),
        orchestrator=FakeOrchestrator(),
        context_orchestrator=ContextOrchestrator(registry=FakeRegistry()),
        fragments=build_fragment_registry(),
        bridge_sessions=sessions,
    )
    intent = Intent(session_id=session.id, run_id="run_1", prompt="hello", source="bridge")

    handle = await submit(intent, state=state)
    assert handle.task is not None
    await handle.task

    run = sessions.get_run("run_1")
    assert run is not None
    assert run.workflow_name == "bridge_chat"
    assert run.status == "done"
    # The settled agent turn was written to the session.
    settled = [turn for turn in session.turns if isinstance(turn, BridgeTurn) and turn.state == "settled"]
    assert settled
    assert settled[0].content == "ok"
    # The forge was lazily seeded onto app.state (process-scoped cache, not a module global).
    assert getattr(state, "forge", None) is not None
