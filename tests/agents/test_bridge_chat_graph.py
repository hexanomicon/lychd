"""Full offline run of the bridge_chat graph (A5 §10).

Drives `BRIDGE_CHAT_GRAPH` end to end with a `TestModel`, asserting the node
path, the event sequence, turn settlement, and context release — with no model
request permitted (`ALLOW_MODEL_REQUESTS = False`).
"""

from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel
from pydantic_graph.persistence.in_mem import FullStatePersistence

from lychd.agents.outputs import BridgeReply
from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT_GRAPH, BridgeChatState, WeaveContext
from tests.agents.conftest import make_services
from tests.agents.fakes import FakeConsents, FakeEvents, FakeOrchestrator, FakeTurns


@pytest.mark.asyncio
async def test_happy_path_settles_turn() -> None:
    """WeaveContext -> Converse -> ProjectReply -> End, turn settled, floor released."""
    events, turns, consents, orch = FakeEvents(), FakeTurns(), FakeConsents(), FakeOrchestrator()
    model = TestModel(custom_output_args={"answer": "greetings", "fragments": []}, call_tools=[])
    services = make_services(model=model, events=events, turns=turns, consents=consents, orchestrator=orch)
    state = BridgeChatState(session_id="sess_1", run_id="run_1", prompt="hello")
    persistence: FullStatePersistence = FullStatePersistence()

    async with BRIDGE_CHAT_GRAPH.iter(WeaveContext(), state=state, deps=services, persistence=persistence) as run:
        node_path: list[str] = [type(node).__name__ async for node in run]

    assert node_path == ["WeaveContext", "Converse", "ProjectReply", "End"]
    assert run.result is not None
    assert isinstance(run.result.output, BridgeReply)

    status_payloads = [payload for _, kind, payload in events.events if kind == "status"]
    assert status_payloads == ["weaving", "thinking", "settling"]
    assert events.kinds()[-1] == "done"
    assert "token" not in events.kinds()  # TestModel emits structured output, not text deltas

    assert services.dispatcher.calls == ["chat"]  # type: ignore[attr-defined]
    assert turns.statuses["run_1"] == "done"
    assert turns.added
    assert turns.added[0][1].state == "settled"
    assert services.context.get("run_1") is None  # floor released after settle


@pytest.mark.asyncio
async def test_consent_parks_without_done() -> None:
    """A deferred (approval) turn parks: consent event, awaiting_consent, no `done`."""
    events, turns, consents, orch = FakeEvents(), FakeTurns(), FakeConsents(), FakeOrchestrator()
    services = make_services(model=TestModel(), events=events, turns=turns, consents=consents, orchestrator=orch)
    state = BridgeChatState(session_id="sess_1", run_id="run_1", prompt="swap the coven")
    persistence: FullStatePersistence = FullStatePersistence()

    async with BRIDGE_CHAT_GRAPH.iter(WeaveContext(), state=state, deps=services, persistence=persistence) as run:
        async for _ in run:
            pass

    assert consents.parked
    assert consents.parked[0]["tool_name"] == "request_coven_swap"
    assert "consent" in events.kinds()
    assert "done" not in events.kinds()  # parked runs must NOT close the stream
    assert turns.statuses["run_1"] == "awaiting_consent"
    # The tool body did not execute pre-approval, so no transition was requested.
    assert orch.calls == []
