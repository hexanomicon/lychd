"""Full offline run of the bridge_chat graph (A5 §10).

Drives `BRIDGE_CHAT_GRAPH` end to end with a `TestModel`, asserting the node
path, the event sequence, turn settlement, and context release — with no model
request permitted (`ALLOW_MODEL_REQUESTS = False`).
"""

# pyright: reportPrivateUsage=false
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
    FakeGrant,
    FakeOrchestrator,
    FakeTurns,
)

if TYPE_CHECKING:
    from pydantic_ai import AgentRunResult
    from pydantic_ai.messages import ModelMessage
    from pydantic_ai.models import ModelRequestParameters
    from pydantic_ai.settings import ModelSettings


@pytest.mark.asyncio
async def test_happy_path_settles_turn() -> None:
    """WeaveContext -> Converse -> ProjectReply -> End, turn settled, floor released."""
    events, turns, consents, orch = FakeEvents(), FakeTurns(), FakeConsents(), FakeOrchestrator()
    model = TestModel(custom_output_args={"answer": "greetings", "fragments": []}, call_tools=[])
    services = make_services(model=model, events=events, turns=turns, consents=consents, orchestrator=orch)
    state = BridgeChatState(session_id="sess_1", run_id="run_1", prompt="hello")
    persistence: FullStatePersistence = FullStatePersistence()

    async with BRIDGE_CHAT_GRAPH.iter(WeaveContext(), state=state, deps=services, persistence=persistence) as run:
        async for _ in run:
            pass

    assert run.result is not None
    assert isinstance(run.result.output, BridgeReply)

    status_payloads = [payload for _, kind, payload in events.events if kind == "status"]
    assert status_payloads == ["weaving", "thinking", "settling"]
    # The graph no longer emits `done` — the ghoul (perform_run) owns the terminal DONE.
    assert "done" not in events.kinds()

    dispatcher = cast("FakeDispatcher", services.dispatcher)
    assert dispatcher.calls == ["chat"]
    assert dispatcher.requires_tools_calls == [True]
    assert turns.added
    assert turns.added[0][1].state == "settled"
    assert services.context.get("run_1") is not None  # worker owns release after terminal Run settlement


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

            yield AgentRunResultEvent(
                result=cast(
                    "AgentRunResult[BridgeReply]",
                    SimpleNamespace(
                        output=BridgeReply(answer="ok", fragments=[]),
                        new_messages=lambda: new_messages,
                    ),
                )
            )

    class _CaptureForge:
        def agent_for(self, _spec: object) -> _CaptureAgent:
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
        forge=cast("Any", _CaptureForge()),
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


def test_usage_limits_reserve_output_without_fake_precount() -> None:
    from pydantic_ai.models.test import TestModel

    from lychd.agents.workflows.bridge_chat import _usage_limits

    limits = _usage_limits(8192, FakeGrant(model=TestModel()))

    assert limits is not None
    assert limits.input_tokens_limit == 7680
    assert limits.count_tokens_before_request is False


def test_usage_limits_enable_precount_only_for_model_override() -> None:
    from pydantic_ai.models.test import TestModel
    from pydantic_ai.usage import RequestUsage

    from lychd.agents.workflows.bridge_chat import _usage_limits

    class _CountingModel(TestModel):
        async def count_tokens(
            self,
            messages: list[ModelMessage],
            model_settings: ModelSettings | None,
            model_request_parameters: ModelRequestParameters,
        ) -> RequestUsage:
            _ = (messages, model_settings, model_request_parameters)
            return RequestUsage()

    limits = _usage_limits(8192, FakeGrant(model=_CountingModel()))

    assert limits is not None
    assert limits.count_tokens_before_request is True


def test_usage_limits_reject_output_reserve_that_consumes_window() -> None:
    from types import SimpleNamespace

    from pydantic_ai.models.test import TestModel

    from lychd.agents.workflows.bridge_chat import _usage_limits
    from lychd.domain.cortex.context import ContextBudgetExceededError

    grant = FakeGrant(model=TestModel())
    grant.spec.generation_profile = SimpleNamespace(max_context=4096, max_tokens=4096)

    with pytest.raises(ContextBudgetExceededError, match="leaves no input budget"):
        _usage_limits(4096, grant)
