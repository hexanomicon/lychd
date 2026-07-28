"""Full offline run of the bridge_chat graph (A5 §10).

Drives `BRIDGE_CHAT_GRAPH` end to end with a `TestModel`, asserting the node
path, the event sequence, turn settlement, and context release — with no model
request permitted (`ALLOW_MODEL_REQUESTS = False`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pytest
from pydantic_ai.models.test import TestModel
from pydantic_graph.persistence.in_mem import FullStatePersistence

from lychd.agents.outputs import BridgeReply
from lychd.agents.workflows.bridge_chat import BRIDGE_CHAT_GRAPH, BridgeChatState, WeaveContext
from tests.agents.conftest import make_services
from tests.agents.fakes import (
    FakeConsents,
    FakeDispatcher,
    FakeEvents,
    FakeOrchestrator,
    FakeTurns,
    approval_test_toolset,
)

if TYPE_CHECKING:
    from pydantic_ai import AgentRunResult

    from lychd.agents.factory import AgentForge


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
    # The graph no longer emits `done` — the ghoul (perform_run) owns the terminal DONE.
    assert "done" not in events.kinds()
    assert "token" not in events.kinds()  # TestModel emits structured output, not text deltas

    dispatcher = cast("FakeDispatcher", services.dispatcher)
    assert dispatcher.calls == ["chat"]
    assert dispatcher.requires_tools_calls == [True]
    assert turns.added
    assert turns.added[0][1].state == "settled"
    assert services.context.get("run_1") is None  # floor released after settle


@pytest.mark.asyncio
async def test_consent_parks_without_done() -> None:
    """A deferred (approval) turn parks: RunParked sentinel, no `done`, no in-graph `consent` (S4)."""
    from lychd.domain.cortex.graph_runner import GraphRunner
    from lychd.domain.cortex.runs import RunParked
    from lychd.domain.cortex.stasis import LiveStasisPhylactery

    events, turns, consents, orch = FakeEvents(), FakeTurns(), FakeConsents(), FakeOrchestrator()
    services = make_services(
        model=TestModel(),
        events=events,
        turns=turns,
        consents=consents,
        orchestrator=orch,
        toolsets=(approval_test_toolset(),),
    )
    state = BridgeChatState(session_id="sess_1", run_id="run_1", prompt="swap the coven")

    runner = GraphRunner[BridgeChatState](
        orchestrator=orch,  # pyright: ignore[reportArgumentType]
        persistence=LiveStasisPhylactery(job_id="run_1"),
        signal_priority=50,
    )
    result = await runner.run_graph(BRIDGE_CHAT_GRAPH, WeaveContext(), state, deps=services)

    assert isinstance(result, RunParked)
    assert result.tool_name == "request_coven_swap"
    assert consents.parked
    assert consents.parked[0]["tool_name"] == "request_coven_swap"
    # S4: the graph does NOT emit `consent` — that moves to perform_run (after status write).
    assert "consent" not in events.kinds()
    assert "done" not in events.kinds()  # parked runs must NOT close the stream
    # The tool body did not execute pre-approval, so no transition was requested.
    assert orch.calls == []


@pytest.mark.asyncio
async def test_converse_forwards_grant_model_settings() -> None:
    """Converse forwards grant settings and bounded completed Pydantic history."""
    from types import SimpleNamespace

    from pydantic_ai.messages import (
        ModelMessagesTypeAdapter,
        ModelRequest,
        ModelResponse,
        TextPart,
    )
    from pydantic_ai.run import AgentRunResultEvent

    from lychd.agents.services import WorkflowServices, default_sigil
    from lychd.domain.cortex.context import ContextOrchestrator
    from lychd.domain.web.fragments import build_fragment_registry
    from lychd.domain.web.schemas import BridgeTurn
    from tests.agents.fakes import FakeRegistry

    captured: dict[str, Any] = {}
    sentinel = {"temperature": 0.42, "max_tokens": 128}
    prior_messages = [
        ModelRequest(parts=ModelRequest.user_text_prompt("prior").parts, run_id="run-prior"),
        ModelResponse(parts=[TextPart("prior reply")], run_id="run-prior"),
    ]
    serialized_prior = list(ModelMessagesTypeAdapter.dump_python(prior_messages, mode="json"))
    expected_prior = list(serialized_prior)

    class _CaptureAgent:
        async def run_stream_events(self, _prompt: str, **kwargs: Any) -> Any:
            captured.update(kwargs)
            captured["prompt"] = _prompt
            captured["floor"] = kwargs["deps"].context.get("run_1").floor_text()
            new_messages = [
                ModelRequest(parts=ModelRequest.user_text_prompt(_prompt).parts, run_id="run_1"),
                ModelResponse(parts=[TextPart("ok")], run_id="run_1"),
            ]

            def _all_messages() -> list[Any]:
                return [*(kwargs["message_history"] or []), *new_messages]

            yield AgentRunResultEvent(
                result=cast(
                    "AgentRunResult[BridgeReply]",
                    SimpleNamespace(
                        output=BridgeReply(answer="ok", fragments=[]),
                        all_messages=_all_messages,
                        new_messages=lambda: new_messages,
                    ),
                )
            )

    class _CaptureForge:
        def agent_for(self, _spec: Any) -> _CaptureAgent:
            return _CaptureAgent()

    events, turns, consents, orch = FakeEvents(), FakeTurns(), FakeConsents(), FakeOrchestrator()
    turns.seed_session(
        "sess_1",
        turns=[BridgeTurn(role="user", content="hello", run_id="run_1")],
        message_history=serialized_prior,
    )
    services = WorkflowServices(
        dispatcher=FakeDispatcher(model=None, settings=sentinel),
        orchestrator=orch,
        context=ContextOrchestrator(registry=FakeRegistry()),
        fragments=build_fragment_registry(),
        turns=turns,
        consents=consents,
        events=events,
        forge=cast("AgentForge", _CaptureForge()),
        sigil_provider=default_sigil,
    )
    state = BridgeChatState(session_id="sess_1", run_id="run_1", prompt="hello")
    persistence: FullStatePersistence = FullStatePersistence()

    async with BRIDGE_CHAT_GRAPH.iter(WeaveContext(), state=state, deps=services, persistence=persistence) as run:
        async for _ in run:
            pass

    assert captured["model_settings"] == sentinel  # grant.model_settings() forwarded through
    assert captured["prompt"] == "hello"
    assert list(ModelMessagesTypeAdapter.dump_python(captured["message_history"], mode="json")) == expected_prior
    assert "hello" not in str(expected_prior)
    assert "active capability: chat:test" in captured["floor"]
    assert len(turns.sessions["sess_1"].message_history) == 4
