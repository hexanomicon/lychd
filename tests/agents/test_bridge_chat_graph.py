"""Full offline run of the bridge_chat graph (A5 §10).

Drives `BRIDGE_CHAT_GRAPH` end to end with a `TestModel`, asserting the node
path, the event sequence, turn settlement, and context release — with no model
request permitted (`ALLOW_MODEL_REQUESTS = False`).
"""

# pyright: reportPrivateUsage=false
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, cast

import pytest
from pydantic_ai.models.test import TestModel

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
    from collections.abc import AsyncGenerator

    from pydantic_ai import AgentRunResult, RunContext
    from pydantic_ai.messages import ModelMessage, ModelResponse
    from pydantic_ai.models import ModelRequestParameters, StreamedResponse
    from pydantic_ai.settings import ModelSettings
    from pydantic_ai.usage import RequestUsage


@pytest.mark.asyncio
async def test_happy_path_settles_turn() -> None:
    """WeaveContext -> Converse -> ProjectReply -> End, turn settled, floor released."""
    events, turns, consents, orch = FakeEvents(), FakeTurns(), FakeConsents(), FakeOrchestrator()
    model = TestModel(custom_output_args={"answer": "greetings", "fragments": []}, call_tools=[])
    services = make_services(model=model, events=events, turns=turns, consents=consents, orchestrator=orch)
    state = BridgeChatState(session_id="sess_1", run_id="run_1", prompt="hello")
    async with BRIDGE_CHAT_GRAPH.iter(inputs=WeaveContext(), state=state, deps=services) as run:
        async for _ in run:
            pass

    assert isinstance(run.output, BridgeReply)

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
        @asynccontextmanager
        async def run_stream_events(self, _prompt: str, **kwargs: Any) -> AsyncGenerator[Any]:
            yield self._events(_prompt, **kwargs)

        async def _events(self, _prompt: str, **kwargs: Any) -> AsyncGenerator[Any]:
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
    async with BRIDGE_CHAT_GRAPH.iter(inputs=WeaveContext(), state=state, deps=services) as run:
        async for _ in run:
            pass

    assert captured["model_settings"] == sentinel  # grant.model_settings() forwarded through
    assert captured["prompt"] == "hello"
    assert list(ModelMessagesTypeAdapter.dump_python(captured["message_history"], mode="json")) == expected_prior
    assert "hello" not in str(expected_prior)
    assert "active capability: chat:test" in captured["floor"]
    assert len(turns.sessions["sess_1"].message_history) == 4


def test_usage_limits_reject_output_reserve_that_consumes_window() -> None:
    from types import SimpleNamespace

    from pydantic_ai.models.test import TestModel

    from lychd.agents.workflows.bridge_chat import _request_policy
    from lychd.domain.cortex.context import ContextBudgetExceededError

    grant = FakeGrant(model=TestModel())
    grant.spec.generation_profile = SimpleNamespace(max_context=4096, max_tokens=4096)

    with pytest.raises(ContextBudgetExceededError, match="leaves no input budget"):
        _request_policy(4096, grant)


class _ReportedUsageModel(TestModel):
    """Report exact request usage while retaining the real offline agent loop."""

    request_input_tokens = 4500
    requests = 0
    streams_closed = 0

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        self.requests += 1
        response = await super().request(messages, model_settings, model_request_parameters)
        response.usage.input_tokens = self.request_input_tokens
        return response

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: RunContext[Any] | None = None,
    ) -> AsyncGenerator[StreamedResponse]:
        self.requests += 1
        try:
            async with super().request_stream(
                messages, model_settings, model_request_parameters, run_context
            ) as response:
                response._usage.input_tokens = self.request_input_tokens
                yield response
        finally:
            self.streams_closed += 1


class _CountingUsageModel(_ReportedUsageModel):
    async def count_tokens(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> RequestUsage:
        from pydantic_ai.usage import RequestUsage

        _ = messages, model_settings, model_request_parameters
        return RequestUsage(input_tokens=self.request_input_tokens)


@pytest.mark.asyncio
@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("precount", [False, True])
async def test_context_window_allows_multiple_requests_that_each_fit(*, streaming: bool, precount: bool) -> None:
    from pydantic_ai import Agent
    from pydantic_ai.run import AgentRunResultEvent

    from lychd.agents.workflows.bridge_chat import _request_policy

    model_type = _CountingUsageModel if precount else _ReportedUsageModel
    model = model_type(custom_output_text="done")
    agent = Agent(model)
    calls: list[str] = []

    async def lookup() -> str:
        calls.append("lookup")
        return "found"

    agent.tool_plain(lookup)
    bounded_model, limits = _request_policy(8192, FakeGrant(model=model))
    if streaming:
        result = None
        async with agent.run_stream_events("hello", model=bounded_model, usage_limits=limits) as stream:
            async for event in stream:
                if isinstance(event, AgentRunResultEvent):
                    result = event.result
        assert result is not None
    else:
        result = await agent.run("hello", model=bounded_model, usage_limits=limits)
    assert result.output == "done"
    assert result.usage.input_tokens == 9000
    assert model.requests == 2
    assert calls == ["lookup"]


@pytest.mark.asyncio
@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("precount", [False, True])
async def test_context_window_rejects_oversized_request_before_tools(*, streaming: bool, precount: bool) -> None:
    from pydantic_ai import Agent
    from pydantic_ai.exceptions import UsageLimitExceeded

    from lychd.agents.workflows.bridge_chat import _request_policy

    model_type = _CountingUsageModel if precount else _ReportedUsageModel
    model = model_type(custom_output_text="done")
    model.request_input_tokens = 8000
    bounded_model, limits = _request_policy(8192, FakeGrant(model=model))
    agent = Agent(bounded_model)
    calls: list[str] = []

    async def lookup() -> str:
        calls.append("lookup")
        return "found"

    agent.tool_plain(lookup)

    async def run() -> None:
        if streaming:
            async with agent.run_stream_events("hello", usage_limits=limits) as stream:
                async for _ in stream:
                    pass
        else:
            await agent.run("hello", usage_limits=limits)

    with pytest.raises(UsageLimitExceeded, match="per-request input_tokens_limit of 7680"):
        await run()
    assert calls == []
    assert model.requests == (0 if precount else 1)
    assert model.streams_closed == int(streaming and not precount)
