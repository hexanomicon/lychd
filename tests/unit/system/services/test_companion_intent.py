"""Intent admission rejects hostile response envelopes before native Agent processing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ThinkingPart, ToolCallPart
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.toolsets import FunctionToolset
from pydantic_ai.usage import RequestUsage, UsageLimits

from lychd.agents.context_limits import limit_model_requests
from lychd.agents.deps import LychDDeps
from lychd.agents.factory import build_agent
from lychd.system.services.companion_intent import (
    CompanionIntentError,
    CompanionIntentModel,
    IntentDecision,
    companion_intent_spec,
    decode_intent_decision,
)

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage, ModelResponsePart
    from pydantic_ai.models.function import AgentInfo
    from pydantic_ai.settings import ModelSettings

_MODEL = "synthetic-intent"


def _response(**changes: Any) -> ModelResponse:
    params: dict[str, Any] = {
        "parts": [TextPart('{"decision":"state"}')],
        "model_name": _MODEL,
        "provider_details": {"finish_reason": "stop"},
        "finish_reason": "stop",
        **changes,
    }
    return ModelResponse(**params)


class _ResponseModel(Model):
    def __init__(self, response: ModelResponse) -> None:
        super().__init__()
        self.response = response

    @property
    def model_name(self) -> str:
        return _MODEL

    @property
    def system(self) -> str:
        return "synthetic"

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        _ = messages, model_settings, model_request_parameters
        return self.response


def _model(response: ModelResponse) -> Model:
    return _ResponseModel(response)


@pytest.mark.parametrize("decision", list(IntentDecision))
def test_decodes_only_closed_decisions(decision: IntentDecision) -> None:
    assert decode_intent_decision('{"decision":"' + decision + '"}') is decision


@pytest.mark.parametrize(
    "payload",
    [
        '{"decision":"state","decision":"idle"}',
        '{"decision":"state","extra":true}',
        '{"decision":"state","extra":{"same":1,"same":2}}',
        '{"decision":NaN}',
        '{"decision":Infinity}',
        '{"decision":-Infinity}',
        '{"decision":1}',
        '{"decision":null}',
        '{"decision":true}',
        '{"decision":["state"]}',
        '{"decision":{"decision":"state"}}',
        '{"decision":"STATE"}',
        '{"decision":"follow"}',
        "{}",
        "[]",
        '"state"',
        '{"decision":"state"} trailing',
        '```json\n{"decision":"state"}\n```',
        '{"decision":"state"}\n{"decision":"idle"}',
        '{"decision":"\ud800"}',
    ],
)
def test_refuses_malformed_duplicate_extra_and_nonfinite_json(payload: str) -> None:
    with pytest.raises(CompanionIntentError, match=r"^invalid_decision$"):
        decode_intent_decision(payload)


def test_byte_bound_applies_before_parsing_and_counts_utf8() -> None:
    with pytest.raises(CompanionIntentError, match=r"^output_limit$"):
        decode_intent_decision(" " * 513)
    with pytest.raises(CompanionIntentError, match=r"^output_limit$"):
        decode_intent_decision("é" * 257)
    payload = '{"decision":"state"}'
    assert decode_intent_decision(payload, max_response_bytes=len(payload)) is IntentDecision.STATE
    with pytest.raises(CompanionIntentError, match=r"^output_limit$"):
        decode_intent_decision(payload, max_response_bytes=len(payload) - 1)


@pytest.mark.parametrize("bound", [0, -1, 513, True])
def test_refuses_invalid_configuration(bound: int) -> None:
    with pytest.raises(CompanionIntentError, match=r"^invalid_configuration$"):
        decode_intent_decision("{}", max_response_bytes=bound)
    with pytest.raises(CompanionIntentError, match=r"^invalid_configuration$"):
        companion_intent_spec(max_tokens=bound)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"model_name": "other"}, "response_model_mismatch"),
        ({"model_name": None}, "response_model_mismatch"),
        ({"finish_reason": "length"}, "output_limit"),
        ({"provider_details": {"finish_reason": "length"}}, "output_limit"),
        ({"provider_details": None}, "incomplete_response"),
        ({"provider_details": {}}, "incomplete_response"),
        ({"provider_details": {"finish_reason": None}}, "incomplete_response"),
        ({"provider_details": {"finish_reason": "tool_calls"}}, "incomplete_response"),
        ({"provider_details": {"finish_reason": "stop "}}, "incomplete_response"),
        ({"finish_reason": None}, "incomplete_response"),
        ({"finish_reason": "tool_call"}, "incomplete_response"),
        ({"state": "suspended"}, "incomplete_response"),
        ({"state": "incomplete"}, "incomplete_response"),
        ({"parts": [TextPart('{"decision":"state","extra":1}')]}, "invalid_decision"),
        ({"parts": [TextPart(" " * 513)]}, "output_limit"),
        ({"parts": []}, "invalid_decision"),
        ({"parts": [ThinkingPart("foreign")]}, "invalid_decision"),
        ({"parts": [TextPart('{"decision":'), TextPart('"state"}')]}, "invalid_decision"),
    ],
)
async def test_guard_rejects_unadmitted_response(changes: dict[str, Any], code: str) -> None:
    model = CompanionIntentModel(_model(_response(**changes)), model_id=_MODEL)
    with pytest.raises(CompanionIntentError, match=r"^" + code + "$") as refused:
        await model.request([], None, ModelRequestParameters())
    assert refused.value.code == code


@pytest.mark.asyncio
@pytest.mark.parametrize("sibling_text", [False, True])
async def test_tool_rejected_before_registered_handler_runs(*, sibling_text: bool) -> None:
    effects: list[str] = []
    tools: FunctionToolset[LychDDeps] = FunctionToolset(id="negative-control")

    async def attempted_effect() -> str:
        effects.append("executed")
        return "unreachable"

    tools.add_function(attempted_effect)
    parts: list[ModelResponsePart] = [ToolCallPart("attempted_effect", {})]
    if sibling_text:
        parts.insert(0, TextPart('{"decision":"state"}'))
    model = CompanionIntentModel(_model(_response(parts=parts)), model_id=_MODEL)
    agent = build_agent(companion_intent_spec(), toolset_factories={})
    with pytest.raises(CompanionIntentError, match=r"^tool_call_refused$"):
        await agent.run("synthetic instruction", deps=cast("LychDDeps", object()), model=model, toolsets=[tools])
    assert effects == []


@pytest.mark.asyncio
async def test_real_agent_admits_one_text_decision_and_has_no_tools_or_repairs() -> None:
    requests = 0

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal requests
        requests += 1
        assert messages
        assert info.function_tools == []
        assert info.output_tools == []
        return _response()

    spec = companion_intent_spec()
    assert not spec.writes
    assert spec.retries == 0
    assert spec.toolset_names == ()
    model = CompanionIntentModel(FunctionModel(respond, model_name=_MODEL), model_id=_MODEL)
    agent = build_agent(spec, toolset_factories={})
    result = await agent.run(
        "synthetic instruction",
        deps=cast("LychDDeps", object()),
        model=model,
        usage_limits=UsageLimits(request_limit=1, tool_calls_limit=0),
    )
    assert decode_intent_decision(result.output) is IntentDecision.STATE
    assert requests == 1


@pytest.mark.asyncio
async def test_guard_retains_existing_context_wrapper() -> None:
    from pydantic_ai.exceptions import UsageLimitExceeded

    source = _model(_response(usage=RequestUsage(input_tokens=101)))
    bounded, limits = limit_model_requests(source, context_window=120, output_reserve=20)
    assert bounded is not None
    assert limits is not None
    model = CompanionIntentModel(bounded, model_id=_MODEL)
    with pytest.raises(UsageLimitExceeded, match="per-request input_tokens_limit"):
        await model.request([], None, ModelRequestParameters())


@pytest.mark.asyncio
async def test_streaming_cannot_bypass_guard() -> None:
    requests = 0

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal requests
        _ = messages, info
        requests += 1
        return _response()

    model = CompanionIntentModel(FunctionModel(respond, model_name=_MODEL), model_id=_MODEL)
    with pytest.raises(CompanionIntentError, match=r"^streaming_unsupported$"):
        async with model.request_stream([], None, ModelRequestParameters()):
            pytest.fail("unvalidated stream reached consumer")
    assert requests == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("reasoning", ["synthetic private reasoning", "é" * 4096])
async def test_guard_strips_one_bounded_thinking_part_before_agent_history(reasoning: str) -> None:
    source = _response(parts=[ThinkingPart(reasoning), TextPart('{"decision":"state"}')])
    model = CompanionIntentModel(_model(source), model_id=_MODEL)
    admitted = await model.request([], None, ModelRequestParameters())
    assert admitted.parts == [TextPart('{"decision":"state"}')]
    assert admitted.model_name == source.model_name
    assert admitted.provider_details == source.provider_details
    assert admitted.finish_reason == source.finish_reason
    assert len(source.parts) == 2
    agent = build_agent(companion_intent_spec(), toolset_factories={})
    result = await agent.run(
        "synthetic instruction",
        deps=cast("LychDDeps", object()),
        model=model,
        usage_limits=UsageLimits(request_limit=1, tool_calls_limit=0),
    )
    assert result.output == '{"decision":"state"}'
    assert all(not isinstance(part, ThinkingPart) for message in result.all_messages() for part in message.parts)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("parts", "code"),
    [
        ([ThinkingPart("é" * 4097), TextPart('{"decision":"state"}')], "output_limit"),
        ([ThinkingPart("one"), ThinkingPart("two"), TextPart('{"decision":"state"}')], "invalid_decision"),
        ([ThinkingPart("\ud800"), TextPart('{"decision":"state"}')], "invalid_decision"),
    ],
)
async def test_guard_refuses_oversize_multiple_or_invalid_reasoning(parts: list[ModelResponsePart], code: str) -> None:
    model = CompanionIntentModel(_model(_response(parts=parts)), model_id=_MODEL)
    with pytest.raises(CompanionIntentError, match=r"^" + code + "$"):
        await model.request([], None, ModelRequestParameters())
