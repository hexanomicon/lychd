"""The exact local model wire rejects expanded payloads and mismatched replies."""

from __future__ import annotations

import asyncio
import json
import re
from hashlib import sha256
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import httpx2
import pytest
from pydantic import ValidationError
from pydantic_ai import Agent
from pydantic_ai.messages import ThinkingPart
from pydantic_ai.models import override_allow_model_requests
from pydantic_ai.profiles import DEFAULT_THINKING_TAGS
from scripts import generate_reach_decision_grammar as grammar_generator
from scripts.reach_worker import DocumentsRuntime, PipeModelRelay, build_runtime

from lychd.compositions.reach import checkback as checkback_module
from lychd.compositions.reach import decision_grammar_generated as generated_grammar
from lychd.compositions.reach import research as research_module
from lychd.compositions.reach.addressing import AddressingDecision
from lychd.compositions.reach.checkback import CheckbackJudgment
from lychd.compositions.reach.conversation_workflow import (
    ConversationDecision,
    _phase_settings,  # pyright: ignore[reportPrivateUsage] - focused private callsite binding test
)
from lychd.compositions.reach.decision_format import (
    DECISION_PHASES,
    DECISION_SCHEMA_BUNDLE_SHA256,
    DECISION_SCHEMA_INPUT_SHA256,
    DECISION_VARIANTS,
    DecisionPhase,
    DecisionVariant,
    decision_format_phase,
    decision_phase,
    decision_response_format,
    decision_schema,
    decision_schema_inputs,
)
from lychd.compositions.reach.documents_workflow import DocumentsRefused
from lychd.compositions.reach.operator_model import (
    OperatorModelConnector,
    _RelayTransport,  # pyright: ignore[reportPrivateUsage] - focused test of the private relay boundary
)
from lychd.compositions.reach.operator_model_wire import (
    MAX_MODEL_PAYLOAD_BYTES,
    OperatorConversationProfile,
    OperatorModelRequest,
    OperatorModelResponse,
    canonical_json,
    generation_format,
    generation_thinking,
    validate_generation_payload,
)
from lychd.compositions.reach.operator_trace import ReachTraceEvent, trace_bytes
from lychd.compositions.reach.operator_wire import MAX_WIRE_BYTES, strict_json
from lychd.compositions.reach.request_goals import TaskRequirements
from lychd.compositions.reach.research import (
    ResearchPlan,
    _ResearchDecision,  # pyright: ignore[reportPrivateUsage] - drift check against the raw research parser
)
from lychd.compositions.reach.schemas import Record
from lychd.domain.animation.capabilities import CapabilityGrant
from lychd.domain.cortex.stasis import InMemoryStasisStore
from tests.unit.compositions.test_reach_conversation import completion, policy
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_request
from tests.unit.compositions.test_reach_research import (
    assert_generation_cost,
    plan_json,
    relay_response,
    research_profile,
)


def profile() -> OperatorConversationProfile:
    return OperatorConversationProfile(persona_name="Example", persona_instructions="Be useful.")


def body() -> dict[str, Any]:
    binding = profile()
    return {
        "model": binding.model_id,
        "messages": [{"role": "system", "content": "Be useful."}, {"role": "user", "content": "Hello"}],
        "max_tokens": binding.max_tokens,
        "temperature": binding.temperature,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }


def test_closed_generation_payload_and_static_binding() -> None:
    binding = profile()
    assert validate_generation_payload(binding, canonical_json(body()))["model"] == binding.model_id
    assert binding.digest != binding.model_copy(update={"persona_name": "Changed"}).digest
    patches: tuple[dict[str, Any], ...] = (
        {"tools": []},
        {"model": "other"},
        {"max_tokens": 769},
        {"stream": True},
        {"chat_template_kwargs": {"enable_thinking": True}},
    )
    for patch in patches:
        with pytest.raises(ValueError, match=r"model_|validation"):
            validate_generation_payload(binding, canonical_json(body() | patch))
    with pytest.raises(ValueError, match="model_probe_payload"):
        OperatorModelRequest(
            call_id=str(uuid4()), binding_digest=binding.digest, operation="probe", payload_json='{"x":1}'
        )
    with pytest.raises(ValidationError):
        OperatorModelRequest.model_validate_json(
            canonical_json(
                {
                    "call_id": str(uuid4()),
                    "binding_digest": binding.digest,
                    "operation": "delete",
                    "payload_json": "{}",
                }
            )
        )


@pytest.mark.asyncio
async def test_pipe_rejects_mismatched_binding_without_repeating_request() -> None:
    binding = profile()
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    writes: list[bytes] = []

    def write(raw: bytes) -> None:
        writes.append(raw)
        frame = json.loads(raw)
        response = OperatorModelResponse(
            call_id=frame["call_id"],
            binding_digest="a" * 64,
            status="ok",
            payload_json=canonical_json({"healthy": True, "model_ids": [binding.model_id]}),
        )
        reader.feed_data(response.model_dump_json().encode() + b"\n")

    relay = PipeModelRelay(binding, reader, write)
    with pytest.raises(ValueError, match="model_response_binding"):
        await relay("probe", "{}")
    assert len(writes) == 1


@pytest.mark.asyncio
async def test_pipe_cancellation_does_not_retransmit() -> None:
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    writes: list[bytes] = []
    relay = PipeModelRelay(profile(), reader, writes.append)
    task = asyncio.create_task(relay("probe", "{}"))
    await asyncio.sleep(0)
    assert len(writes) == 1
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(writes) == 1
    assert not relay.lock.locked()


REASONING_CANARY = "SYNTHETIC_PRIVATE_THOUGHT_MUST_STAY_TRANSIENT"
LEGACY_PROFILE_DIGEST = "150082ac6f4444eb5e577d16215ffdf93ce24ead56887dedf42e90ecec016b15"
LEGACY_THINKING_PROFILE_DIGEST = "a07f4a9f1015e0473fc93811f662505dc18a0e795e598649e664c6a6a0454b61"
RESEARCH_SOURCE_SHAPE_COUNT = 23


def test_private_thinking_binding_preserves_the_known_legacy_digest_and_existing_defaults() -> None:
    omitted = profile()
    explicit_false = OperatorConversationProfile(
        persona_name="Example", persona_instructions="Be useful.", enable_thinking=False
    )
    thinking = OperatorConversationProfile(
        persona_name="Example", persona_instructions="Be useful.", enable_thinking=True
    )
    assert omitted.enable_thinking is False
    assert omitted.digest == explicit_false.digest == LEGACY_PROFILE_DIGEST
    assert thinking.digest != omitted.digest
    thinking_values = thinking.model_dump(
        mode="json",
        exclude={
            "json_object_output",
            "decision_schema_version",
            "thinking_phases",
            "context_projection_version",
            "checkback_invalid_retry",
        },
    )
    assert thinking.digest == sha256(canonical_json(thinking_values).encode()).hexdigest()
    legacy_values = omitted.model_dump(
        mode="json",
        exclude={
            "enable_thinking",
            "json_object_output",
            "decision_schema_version",
            "thinking_phases",
            "context_projection_version",
            "checkback_invalid_retry",
        },
    )
    assert legacy_values["max_tokens"] == 384
    assert legacy_values["research"] == {"enabled": False, "sources": []}
    assert sha256(canonical_json(legacy_values).encode()).hexdigest() == LEGACY_PROFILE_DIGEST


@pytest.mark.parametrize("value", [0, 1, "true", "false", None, [], {}])
def test_private_thinking_flag_is_an_original_boolean(value: object) -> None:
    with pytest.raises(ValidationError):
        OperatorConversationProfile.model_validate(
            {"persona_name": "Example", "persona_instructions": "Be useful.", "enable_thinking": value}
        )


@pytest.mark.parametrize("thinking", [False, True])
def test_json_object_binding_preserves_legacy_raw_profiles_and_hashes(*, thinking: bool) -> None:
    legacy = profile().model_copy(update={"enable_thinking": thinking})
    values = legacy.model_dump(
        mode="json",
        exclude={
            "json_object_output",
            "decision_schema_version",
            "thinking_phases",
            "context_projection_version",
            "checkback_invalid_retry",
        },
    )
    omitted = OperatorConversationProfile.model_validate_json(canonical_json(values))
    explicit = OperatorConversationProfile.model_validate_json(
        canonical_json(values | {"json_object_output": False, "decision_schema_version": 4})
    )
    expected = LEGACY_THINKING_PROFILE_DIGEST if thinking else LEGACY_PROFILE_DIGEST
    assert omitted.json_object_output is False
    assert omitted.digest == explicit.digest == expected
    assert generation_format(omitted, phase="conversation") == {}
    enabled = OperatorConversationProfile.model_validate_json(
        canonical_json(values | {"adaptive_context": True, "json_object_output": True, "decision_schema_version": 4})
    )
    enabled_values = enabled.model_dump(
        mode="json", exclude={"thinking_phases", "context_projection_version", "checkback_invalid_retry"}
    )
    enabled_values["decision_schema_bundle_sha256"] = DECISION_SCHEMA_BUNDLE_SHA256
    if not thinking:
        enabled_values.pop("enable_thinking")
    assert enabled.digest == sha256(canonical_json(enabled_values).encode()).hexdigest()
    assert enabled.digest != enabled.model_copy(update={"json_object_output": False}).digest
    assert enabled.decision_schema_version == 4
    assert generation_format(enabled, phase="conversation") == {
        "structured_outputs": decision_response_format("conversation")
    }


@pytest.mark.parametrize("value", [0, 1, "true", "false", None, [], {}])
def test_json_object_flag_requires_an_original_boolean(value: object) -> None:
    with pytest.raises(ValidationError):
        OperatorConversationProfile.model_validate(
            {
                "persona_name": "Example",
                "persona_instructions": "Be useful.",
                "adaptive_context": True,
                "json_object_output": value,
            }
        )


def test_json_object_output_requires_an_adaptive_decision_profile() -> None:
    with pytest.raises(ValidationError, match="json_object_output_requires_adaptive_context"):
        OperatorConversationProfile(persona_name="Example", persona_instructions="Be useful.", json_object_output=True)


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("value", [True, False, 3.0, "3", 4.0, "4", None, 0, 1, 2, 3])
def test_decision_schema_version_is_exact_original_integer_four(*, enabled: bool, value: object) -> None:
    with pytest.raises(ValidationError, match="decision_schema_version"):
        OperatorConversationProfile.model_validate(
            {
                "persona_name": "Example",
                "persona_instructions": "Be useful.",
                "adaptive_context": True,
                "json_object_output": enabled,
                "decision_schema_version": value,
            }
        )


def test_schema_fingerprint_is_computed_and_cannot_be_configured() -> None:
    inputs = tuple(
        (variant, json.dumps(decision_schema(variant), separators=(",", ":"), ensure_ascii=False))
        for variant in DECISION_VARIANTS
    )
    assert decision_schema_inputs() == inputs
    assert sha256(canonical_json(inputs).encode()).hexdigest() == DECISION_SCHEMA_INPUT_SHA256
    assert generated_grammar.SCHEMA_INPUT_SHA256 == DECISION_SCHEMA_INPUT_SHA256
    generator_sha256 = sha256(Path(grammar_generator.__file__).read_bytes()).hexdigest()
    assert generator_sha256 == generated_grammar.GENERATOR_SHA256
    converter = {
        "package": "xgrammar",
        "version": "0.2.3",
        "api": "Grammar.from_json_schema",
        "serialization": "str(Grammar)",
        "options": {"any_whitespace": False, "indent": None, "separators": [",", ":"]},
        "normalization": "nonempty-json-scalar-native-max-v2",
    }
    assert json.loads(generated_grammar.CONVERTER_METADATA_JSON) == converter
    bundle = {
        "converter": converter,
        "generator_sha256": generator_sha256,
        "schema_inputs": inputs,
        "carriers": [(variant, decision_response_format(variant)) for variant in DECISION_VARIANTS],
    }
    assert sha256(canonical_json(bundle).encode()).hexdigest() == DECISION_SCHEMA_BUNDLE_SHA256
    assert generated_grammar.BUNDLE_SHA256 == DECISION_SCHEMA_BUNDLE_SHA256
    assert grammar_generator.ARTIFACT.read_text() == grammar_generator.render_artifact(generated_grammar.GRAMMARS)
    with pytest.raises(ValidationError, match="decision_schema_bundle_sha256"):
        OperatorConversationProfile.model_validate(profile().model_dump() | {"decision_schema_bundle_sha256": "a" * 64})


@pytest.mark.parametrize("enabled", [False, True])
def test_generation_format_presence_is_bound_and_legacy_payload_stays_unchanged(*, enabled: bool) -> None:
    binding = profile().model_copy(update={"adaptive_context": True, "json_object_output": enabled})
    payload = body() | generation_format(binding, phase="conversation")
    assert validate_generation_payload(binding, canonical_json(payload)) == payload
    assert ("structured_outputs" in payload) is enabled
    wrong_presence = body() if enabled else body() | {"structured_outputs": decision_response_format("conversation")}
    with pytest.raises(ValueError, match="model_generation_binding"):
        validate_generation_payload(binding, canonical_json(wrong_presence))


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize(
    "format_value",
    [None, {}, "json_object", {"type": "text"}, {"type": "json_schema"}, {"type": "json_object", "extra": True}],
)
def test_generation_format_rejects_null_conflicting_and_expanded_values(*, enabled: bool, format_value: object) -> None:
    binding = profile().model_copy(update={"adaptive_context": True, "json_object_output": enabled})
    with pytest.raises(ValueError, match=r"model_generation_binding|validation error"):
        validate_generation_payload(binding, canonical_json(body() | {"structured_outputs": format_value}))


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize(
    "kwargs",
    [
        None,
        {},
        {"enable_thinking": 0},
        {"enable_thinking": 1},
        {"enable_thinking": "true"},
        {"enable_thinking": None},
        {"enable_thinking": False, "budget": 10},
        {"reasoning_effort": "high"},
    ],
)
def test_generation_thinking_kwargs_are_closed_and_strict(*, enabled: bool, kwargs: object) -> None:
    binding = profile().model_copy(update={"enable_thinking": enabled})
    payload = body()
    if kwargs is None:
        payload.pop("chat_template_kwargs")
    else:
        payload["chat_template_kwargs"] = kwargs
    with pytest.raises(ValidationError):
        validate_generation_payload(binding, canonical_json(payload))


@pytest.mark.parametrize("enabled", [False, True])
def test_generation_thinking_kwargs_must_match_the_selected_private_binding(*, enabled: bool) -> None:
    binding = profile().model_copy(update={"enable_thinking": enabled})
    payload = body() | {"chat_template_kwargs": {"enable_thinking": enabled}}
    assert validate_generation_payload(binding, canonical_json(payload))["chat_template_kwargs"] == {
        "enable_thinking": enabled
    }
    with pytest.raises(ValueError, match="model_generation_binding"):
        validate_generation_payload(
            binding, canonical_json(body() | {"chat_template_kwargs": {"enable_thinking": not enabled}})
        )


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("explicit_conflict", [False, True])
@pytest.mark.asyncio
async def test_native_relay_inserts_the_bound_default_and_never_overrides_explicit_sdk_conflict(
    *, enabled: bool, explicit_conflict: bool
) -> None:
    binding = profile().model_copy(update={"enable_thinking": enabled})
    calls: list[dict[str, Any]] = []

    async def relay(_operation: str, payload: str) -> str:
        calls.append(validate_generation_payload(binding, payload))
        return completion("Final answer.")

    payload = body()
    if explicit_conflict:
        payload["chat_template_kwargs"] = {"enable_thinking": not enabled}
    else:
        payload.pop("chat_template_kwargs")
    request = httpx2.Request(
        "POST", "http://reach-model.invalid/v1/chat/completions", content=canonical_json(payload).encode()
    )
    transport = _RelayTransport(binding, relay)
    if explicit_conflict:
        with pytest.raises(ValueError, match="model_generation_binding"):
            await transport.handle_async_request(request)
        assert calls == []
    else:
        result = await transport.handle_async_request(request)
        assert result.status_code == 200
        assert len(calls) == 1
        assert calls[0]["chat_template_kwargs"] == {"enable_thinking": enabled}


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.asyncio
async def test_native_json_format_default_and_explicit_presence_match_the_binding(
    *, enabled: bool, explicit: bool
) -> None:
    binding = profile().model_copy(update={"adaptive_context": True, "json_object_output": enabled})
    calls: list[dict[str, Any]] = []

    async def relay(_operation: str, payload: str) -> str:
        calls.append(validate_generation_payload(binding, payload))
        return completion('{"kind":"answer","text":"Final answer."}')

    payload = body()
    if explicit:
        payload["structured_outputs"] = decision_response_format("conversation")
    request = httpx2.Request(
        "POST", "http://reach-model.invalid/v1/chat/completions", content=canonical_json(payload).encode()
    )
    transport = _RelayTransport(binding, relay)
    if explicit != enabled:
        with pytest.raises(ValueError, match="model_generation_binding"):
            await transport.handle_async_request(request)
        assert calls == []
    else:
        assert (await transport.handle_async_request(request)).status_code == 200
        assert len(calls) == 1
        assert ("structured_outputs" in calls[0]) is enabled
        assert calls[0].get("structured_outputs") == generation_format(binding, phase="conversation").get(
            "structured_outputs"
        )


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("finish", ["stop", "length", None, "unknown"])
@pytest.mark.asyncio
async def test_native_completion_length_always_refuses_and_thinking_requires_natural_stop(
    *, enabled: bool, finish: str | None
) -> None:
    binding = profile().model_copy(update={"enable_thinking": enabled})
    calls = 0

    async def relay(_operation: str, _payload: str) -> str:
        nonlocal calls
        calls += 1
        value = json.loads(completion('{"kind":"answer","text":"Complete-looking JSON."}'))
        if finish is None:
            value["choices"][0].pop("finish_reason")
        else:
            value["choices"][0]["finish_reason"] = finish
        return canonical_json(value)

    request = httpx2.Request(
        "POST",
        "http://reach-model.invalid/v1/chat/completions",
        content=canonical_json(body() | {"chat_template_kwargs": {"enable_thinking": enabled}}).encode(),
    )
    transport = _RelayTransport(binding, relay)
    if finish == "length" or (enabled and finish != "stop"):
        with pytest.raises(ValueError, match="model_response"):
            await transport.handle_async_request(request)
    else:
        assert (await transport.handle_async_request(request)).status_code == 200
    assert calls == 1


def malformed_completion(failure: str) -> str:
    value = json.loads(completion('{"kind":"answer","text":"Unadopted answer."}'))
    message = value["choices"][0]["message"]
    message["reasoning"] = REASONING_CANARY
    if failure in {"thinking_only", "empty"}:
        message["content"] = None if failure == "thinking_only" else ""
    elif failure == "malformed_decision":
        message["content"] = '{"kind":"answer","text":"„Partial" broken"}'
    elif failure == "length":
        value["choices"][0]["finish_reason"] = "length"
    elif failure == "oversized":
        message["reasoning"] = REASONING_CANARY + "x" * MAX_MODEL_PAYLOAD_BYTES
    elif failure == "inline_thinking":
        message["content"] = DEFAULT_THINKING_TAGS[0] + REASONING_CANARY + DEFAULT_THINKING_TAGS[1] + message["content"]
    elif failure == "inline_closing":
        message["content"] = DEFAULT_THINKING_TAGS[1] + message["content"]
    elif failure == "malformed_reasoning":
        message["reasoning"] = {"text": REASONING_CANARY}
    if failure == "malformed":
        return "{"
    return json.dumps(value) if failure == "noncanonical" else canonical_json(value)


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("json_output", [False, True])
@pytest.mark.parametrize(
    "failure",
    [
        "thinking_only",
        "empty",
        "length",
        "malformed",
        "malformed_decision",
        "oversized",
        "noncanonical",
        "inline_thinking",
        "inline_closing",
        "malformed_reasoning",
    ],
)
@pytest.mark.asyncio
async def test_bad_completion_settles_finitely_without_retry_or_adoption(
    *, enabled: bool, json_output: bool, failure: str
) -> None:
    binding = profile().model_copy(
        update={"adaptive_context": True, "enable_thinking": enabled, "json_object_output": json_output}
    )
    calls = 0
    events: list[ReachTraceEvent] = []

    async def relay(operation: str, _payload: str) -> str:
        nonlocal calls
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        calls += 1
        return malformed_completion(failure)

    runtime = build_runtime(
        policy(),
        make_corpus(),
        profile=binding,
        model_relay=relay,
        started_at=STARTED,
        clock=lambda: NOW,
        trace=events.append,
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated installed-SDK relay
            result = await runtime.process(
                make_request(action="converse").model_copy(update={"request_id": str(uuid4())})
            )
        assert result.status == "error"
        assert result.text == ""
        assert calls == 1
        assert runtime.substrate.leases.active() == []
        for session in await runtime.sessions.list_sessions():
            assert session.message_history == []
            assert all(REASONING_CANARY not in turn.content for turn in session.turns)
        assert REASONING_CANARY not in b"".join(trace_bytes(event) for event in events).decode()
    finally:
        await runtime.aclose()


@pytest.mark.parametrize("enabled", [False, True])
def test_both_exact_sizers_use_the_selected_private_thinking_value(
    monkeypatch: pytest.MonkeyPatch, *, enabled: bool
) -> None:
    binding = research_profile(checkback=True, max_input_chars=24_000, enable_thinking=enabled)
    observed: list[bool] = []

    def capture(value: Any) -> str:
        if isinstance(value, dict) and "chat_template_kwargs" in value:
            payload = cast("dict[str, Any]", value)
            observed.append(cast("bool", payload["chat_template_kwargs"]["enable_thinking"]))
        return canonical_json(value)

    monkeypatch.setattr(checkback_module, "canonical_json", capture)
    monkeypatch.setattr(research_module, "canonical_json", capture)
    checkback_module.validate_checkback_budget(
        binding, checkback_module.checkback_spec(binding), '{"candidate":{}}', phase="checkback"
    )
    plan = research_module.ResearchPlan(kind="research", text="Read the selected source.", source_ids=("web:official",))
    research_module.synthesis_prompt(
        binding,
        make_corpus(),
        make_request(action="converse"),
        plan,
        (
            research_module.SourceReadResult(
                id="web:official",
                title="Evidence",
                url="https://example.com/guide",
                status="unavailable",
                reason="source_unavailable",
            ),
        ),
        instructions="Trusted instructions.",
    )
    assert observed
    assert all(value is enabled for value in observed)


def assert_schema_transport_round_trip(
    binding: OperatorConversationProfile, payload: str, rebuilt: dict[str, Any]
) -> None:
    assert canonical_json(rebuilt) == payload
    assert "response_format" not in rebuilt
    frame = OperatorModelRequest(
        call_id=str(uuid4()), binding_digest=binding.digest, operation="generate", payload_json=canonical_json(rebuilt)
    ).model_dump_json()
    assert len(frame.encode()) <= MAX_WIRE_BYTES
    decoded = OperatorModelRequest.model_validate_json(frame)
    assert decoded.payload_json == payload
    encoded_body = json.loads(decoded.payload_json)
    assert encoded_body.get("structured_outputs") == generation_format(binding, phase="conversation").get(
        "structured_outputs"
    )
    if binding.json_object_output:
        ordered = encoded_body["structured_outputs"]["grammar"]
        assert isinstance(ordered, str)
        assert ordered == decision_response_format("conversation")["grammar"]


@pytest.mark.parametrize("field", ["reasoning", "reasoning_content"])
@pytest.mark.parametrize("json_output", [False, True])
@pytest.mark.asyncio
async def test_installed_sdk_keeps_provider_reasoning_separate_from_final_text_and_does_not_replay(
    field: str, *, json_output: bool
) -> None:
    binding = profile().model_copy(
        update={"adaptive_context": True, "enable_thinking": True, "json_object_output": json_output}
    )
    payloads: list[str] = []
    final = '{"kind":"answer","text":"Final public text."}'

    async def relay(_operation: str, payload: str) -> str:
        payloads.append(payload)
        assert REASONING_CANARY not in payload
        request = validate_generation_payload(binding, payload)
        assert_schema_transport_round_trip(binding, payload, request)
        assert request["chat_template_kwargs"] == {"enable_thinking": True}
        assert ("structured_outputs" in request) is json_output
        assert request.get("structured_outputs") == generation_format(binding, phase="conversation").get(
            "structured_outputs"
        )
        assert [message["role"] for message in request["messages"]] == ["system", "user"]
        response = json.loads(completion(final))
        response["choices"][0]["message"][field] = REASONING_CANARY
        return canonical_json(response)

    connector = OperatorModelConnector(binding, relay)
    agent: Agent[None, str] = Agent(
        connector.get_model(model_id=binding.model_id),
        instructions="Return final text.",
        output_type=str,
        deps_type=type(None),
        retries=0,
        model_settings={
            "max_tokens": binding.max_tokens,
            "temperature": binding.temperature,
            "extra_body": generation_format(binding, phase="conversation"),
        },
    )
    async with agent:
        with override_allow_model_requests(True):  # noqa: FBT003 - installed SDK with an in-memory relay
            first = await agent.run("First call.")
            second = await agent.run("Second call without supplied history.")
        assert first.output == second.output == final
        assert any(isinstance(part, ThinkingPart) and part.content == REASONING_CANARY for part in first.response.parts)
        assert any(
            isinstance(part, ThinkingPart) and part.content == REASONING_CANARY for part in second.response.parts
        )
    assert len(payloads) == 2


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("selective", [False, True])
@pytest.mark.asyncio
async def test_actual_sdk_explicit_thinking_conflict_is_refused_before_relay(*, enabled: bool, selective: bool) -> None:
    binding = profile().model_copy(
        update={
            "enable_thinking": enabled,
            "adaptive_context": selective,
            "json_object_output": selective,
            "thinking_phases": ("checkback",) if selective else (),
        }
    )
    calls = 0

    async def relay(_operation: str, _payload: str) -> str:
        nonlocal calls
        calls += 1
        return completion("Unadmitted")

    connector = OperatorModelConnector(binding, relay)
    agent: Agent[None, str] = Agent(
        connector.get_model(model_id=binding.model_id),
        instructions="Return final text.",
        output_type=str,
        deps_type=type(None),
        retries=0,
        model_settings={"max_tokens": binding.max_tokens, "temperature": binding.temperature},
    )
    async with agent:
        with (
            override_allow_model_requests(True),  # noqa: FBT003 - installed SDK with an in-memory relay
            pytest.raises(ValueError, match="model_generation_binding"),
        ):
            await agent.run(
                "Conflict",
                model_settings={
                    "extra_body": {
                        **generation_format(binding, phase="checkback"),
                        "chat_template_kwargs": {"enable_thinking": not (enabled or selective)},
                    }
                },
            )
    assert calls == 0


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("format_value", [None, {"type": "text"}, {"type": "json_object"}, {"type": "json_schema"}])
@pytest.mark.asyncio
async def test_actual_sdk_explicit_json_format_conflicts_are_refused_before_relay(
    *, enabled: bool, format_value: object
) -> None:
    binding = profile().model_copy(update={"adaptive_context": True, "json_object_output": enabled})
    calls = 0

    async def relay(_operation: str, _payload: str) -> str:
        nonlocal calls
        calls += 1
        return completion("Unadmitted")

    connector = OperatorModelConnector(binding, relay)
    agent: Agent[None, str] = Agent(
        connector.get_model(model_id=binding.model_id),
        instructions="Return a JSON object.",
        output_type=str,
        deps_type=type(None),
        retries=0,
        model_settings={"max_tokens": binding.max_tokens, "temperature": binding.temperature},
    )
    async with agent:
        with (
            override_allow_model_requests(True),  # noqa: FBT003 - installed SDK with an in-memory relay
            pytest.raises(ValueError, match=r"model_generation_binding|validation error"),
        ):
            await agent.run("Conflict", model_settings={"extra_body": {"response_format": format_value}})
    assert calls == 0


async def assert_native_reasoning_custody(
    runtime: DocumentsRuntime, run_id: str, events: list[ReachTraceEvent]
) -> None:
    session = await runtime.sessions.session_for_run(run_id)
    assert session is not None
    assert session.message_history == []
    assert all(REASONING_CANARY not in turn.content for turn in session.turns)
    retained = await runtime.substrate.ledger.list_events(run_id)
    assert REASONING_CANARY not in canonical_json([event.model_dump(mode="json") for event in retained])
    assert REASONING_CANARY not in b"".join(trace_bytes(event) for event in events).decode()
    assert runtime.substrate.leases.active() == []


RESEARCH_POSTURE_GRAMMARS: dict[str, DecisionVariant] = {
    "planning": "planning",
    "synthesis": "synthesis",
    "checkback": "checkback_public",
    "correction": "synthesis",
}


@pytest.mark.parametrize("field", ["reasoning", "reasoning_content"])
@pytest.mark.asyncio
async def test_native_sdk_reasoning_never_enters_review_repair_history_checkpoints_or_trace(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    binding = research_profile(
        checkback=True,
        max_input_chars=24_000,
        enable_thinking=False,
        json_object_output=True,
        thinking_phases=("checkback",),
    )
    phases: list[str] = []
    snapshots: list[str] = []
    events: list[ReachTraceEvent] = []
    original_replace = InMemoryStasisStore.replace
    reviews = iter(("revise", "accept"))
    acquisitions = 0

    async def snapshot(store: InMemoryStasisStore, run_id: str, documents: list[Any]) -> None:
        snapshots.append(canonical_json(documents))
        await original_replace(store, run_id, documents)

    monkeypatch.setattr(InMemoryStasisStore, "replace", snapshot)

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        assert REASONING_CANARY not in payload
        body = validate_generation_payload(binding, payload)
        assert [message["role"] for message in body["messages"]] == ["system", "user"]
        prompt = json.loads(body["messages"][-1]["content"])
        phase = prompt.get("phase", prompt.get("research_phase"))
        assert body["chat_template_kwargs"] == {"enable_thinking": phase == "checkback"}
        assert decision_format_phase(body["structured_outputs"]) == RESEARCH_POSTURE_GRAMMARS[phase]
        assert_generation_cost(binding, payload, phase=RESEARCH_POSTURE_GRAMMARS[phase])
        phases.append(phase)
        if phase == "planning":
            output = plan_json(("web:official",))
        elif phase == "checkback":
            verdict = next(reviews)
            output = canonical_json(
                {
                    "verdict": verdict,
                    "issues": [] if verdict == "accept" else ["missing_component"],
                    "current_runtime_claims": [],
                }
            )
        else:
            output = canonical_json(
                {
                    "kind": "answer",
                    "text": "Qualified final answer." if phase == "correction" else "Draft answer.",
                    "citations": ["web:official"],
                }
            )
        response = json.loads(completion(output))
        response["choices"][0]["message"][field] = REASONING_CANARY
        return canonical_json(response)

    async def acquire(request: Any) -> Any:
        nonlocal acquisitions
        acquisitions += 1
        return relay_response(request)

    runtime = build_runtime(
        policy(),
        make_corpus(),
        profile=binding,
        model_relay=relay,
        research_relay=acquire,
        started_at=STARTED,
        clock=lambda: NOW,
        trace=events.append,
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - installed SDK with an in-memory relay
            result = await runtime.process(
                make_request(action="converse", question="Compare doc:docs/graph.md with web:official.").model_copy(
                    update={"request_id": str(uuid4())}
                )
            )
        assert result.status == "conversation"
        assert "Qualified final answer." in result.text
        assert REASONING_CANARY not in result.text
        assert phases == ["planning", "synthesis", "checkback", "correction", "checkback"]
        assert acquisitions == 1
        assert snapshots
        assert all(REASONING_CANARY not in value for value in snapshots)
        assert result.run_id is not None
        await assert_native_reasoning_custody(runtime, result.run_id, events)
    finally:
        await runtime.aclose()


@pytest.mark.parametrize("enabled", [False, True])
def test_private_4096_completion_ceiling_requires_exact_profile_and_refuses_4097(*, enabled: bool) -> None:
    binding = OperatorConversationProfile(
        persona_name="Example", persona_instructions="Be useful.", max_tokens=4096, enable_thinking=enabled
    )
    payload = body() | {"max_tokens": 4096, "chat_template_kwargs": {"enable_thinking": enabled}}
    assert validate_generation_payload(binding, canonical_json(payload))["max_tokens"] == 4096
    with pytest.raises(ValueError, match="model_generation_binding"):
        validate_generation_payload(binding, canonical_json(payload | {"max_tokens": 2048}))
    with pytest.raises(ValidationError):
        validate_generation_payload(binding, canonical_json(payload | {"max_tokens": 4097}))
    with pytest.raises(ValidationError):
        OperatorConversationProfile(persona_name="Example", persona_instructions="Be useful.", max_tokens=4097)


def test_legacy_2048_profile_digest_and_default_false_binding_are_unchanged() -> None:
    omitted = OperatorConversationProfile(persona_name="Example", persona_instructions="Be useful.", max_tokens=2048)
    explicit = OperatorConversationProfile(
        persona_name="Example", persona_instructions="Be useful.", max_tokens=2048, enable_thinking=False
    )
    assert omitted.digest == explicit.digest == "02963aa403c0eed97abd99b4c7425e62d40e1f2aaa4377f38ce6f4475125a6d0"
    assert profile().max_tokens == 384
    assert profile().digest == LEGACY_PROFILE_DIGEST
    assert validate_generation_payload(omitted, canonical_json(body() | {"max_tokens": 2048}))["max_tokens"] == 2048
    with pytest.raises(ValueError, match="model_generation_binding"):
        validate_generation_payload(omitted, canonical_json(body() | {"max_tokens": 4096}))


def test_private_completion_allowance_must_leave_declared_context_for_input() -> None:
    with pytest.raises(ValidationError, match="model_completion_context"):
        OperatorConversationProfile(
            persona_name="Example", persona_instructions="Be useful.", max_tokens=4096, max_context=4096
        )
    binding = OperatorConversationProfile(
        persona_name="Example", persona_instructions="Be useful.", max_tokens=4096, max_context=16_384
    )
    assert binding.max_tokens == 4096
    assert binding.max_context == 16_384


def _schema_object(value: Any, schema: dict[str, Any]) -> bool:
    if not isinstance(value, dict):
        return False
    properties = cast("dict[str, Any]", schema.get("properties", {}))
    entries = cast("dict[str, Any]", value)
    return (
        set(schema.get("required", ())) <= entries.keys()
        and (schema.get("additionalProperties") is not False or entries.keys() <= properties.keys())
        and all(_schema_accepts(item, properties[key]) for key, item in entries.items() if key in properties)
    )


def _schema_array(value: Any, schema: dict[str, Any]) -> bool:
    if not isinstance(value, list):
        return False
    entries = cast("list[Any]", value)
    if not schema.get("minItems", 0) <= len(entries) <= schema["maxItems"]:
        return False
    if "prefixItems" in schema:
        prefixes = cast("list[dict[str, Any]]", schema["prefixItems"])
        return len(entries) == len(prefixes) and all(
            _schema_accepts(item, prefix) for item, prefix in zip(entries, prefixes, strict=True)
        )
    return all(_schema_accepts(item, schema["items"]) for item in entries)


def _schema_string(value: Any, schema: dict[str, Any]) -> bool:
    return (
        isinstance(value, str)
        and schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", len(value))
        and ("pattern" not in schema or re.search(schema["pattern"], value) is not None)
    )


def _schema_integer(value: Any, schema: dict[str, Any]) -> bool:
    return type(value) is int and schema.get("minimum", value) <= value <= schema.get("maximum", value)


def _schema_accepts(value: Any, schema: dict[str, Any]) -> bool:
    """Exercise only the finite JSON Schema vocabulary used by this projection."""
    if "anyOf" in schema and not any(_schema_accepts(value, item) for item in schema["anyOf"]):
        return False
    if "const" in schema and canonical_json(value) != canonical_json(schema["const"]):
        return False
    if "enum" in schema and not any(canonical_json(value) == canonical_json(item) for item in schema["enum"]):
        return False
    validators = {
        "object": _schema_object,
        "array": _schema_array,
        "string": _schema_string,
        "integer": _schema_integer,
    }
    if schema.get("type") == "null":
        return value is None
    validator = validators.get(schema.get("type", ""))
    return validator(value, schema) if validator is not None else True


RAW_DECISION_FIXTURES: tuple[tuple[type[Record], dict[str, Any]], ...] = (
    (
        ConversationDecision,
        {
            "kind": "read_more",
            "text": "Read the earlier message.",
            "reaction": None,
            "gif_id": None,
        },
    ),
    (
        ResearchPlan,
        {
            "kind": "research",
            "text": "Read the source.",
            "focus": "Explain the current request from the selected source.",
            "source_ids": ["web:official"],
        },
    ),
    (
        _ResearchDecision,
        {
            "kind": "answer",
            "text": "Supported answer.",
            "citations": [],
            "reaction": "✨",
            "gif_id": "confetti",
        },
    ),
    (
        AddressingDecision,
        {"kind": "addressed", "request_id": "request-1", "anchor_event_id": "anchor-1"},
    ),
    (
        CheckbackJudgment,
        {
            "verdict": "needs_evidence",
            "issues": ["missing_evidence"],
            "clarification": "Which passage should I quote?",
            "coverage": [{"goal": 0, "status": "missing", "answer_quote": None}],
            "current_runtime_claims": None,
        },
    ),
    (
        TaskRequirements,
        {
            "version": 1,
            "goals": ["Explain the first idea."],
            "constraints": [],
            "quotation_presentation": "none",
            "required_context": [],
        },
    ),
)


@pytest.mark.parametrize(("model", "raw"), RAW_DECISION_FIXTURES)
def test_fixed_grammar_admits_raw_parser_families_with_explicit_provider_focus_requirement(
    model: type[Record], raw: dict[str, Any]
) -> None:
    model.model_validate_json(canonical_json(raw))
    phase_by_model: dict[type[Record], DecisionPhase] = {
        ConversationDecision: "conversation",
        ResearchPlan: "planning",
        _ResearchDecision: "synthesis",
        AddressingDecision: "addressing",
        CheckbackJudgment: "checkback",
        TaskRequirements: "goals",
    }
    schema = decision_schema(phase_by_model[model])
    assert _schema_accepts(raw, schema)
    branches = schema.get("anyOf", [schema])
    branch = next(item for item in branches if set(item["properties"]) == set(model.model_fields))
    native_required = {name for name, field in model.model_fields.items() if field.is_required()}
    expected_required = native_required | {"focus"} if model is ResearchPlan else native_required
    assert set(branch["required"]) == expected_required
    assert branch["additionalProperties"] is False


@pytest.mark.parametrize(
    "raw",
    [
        {"phase": "correction", "allowed_issues": [], "context": {}, "candidate": {}},
        {"kind": "answer", "text": "Answer.", "candidate": {}},
        {"kind": "read_more", "text": None},
        {"kind": "answer", "text": "Answer.", "citations": None},
        {"verdict": "accept", "issues": [], "coverage": None},
        {"verdict": "accept", "issues": [], "request_digest": "a" * 64},
        {"status": "conversation", "text": "Settled host output."},
        {
            "kind": "research",
            "text": "Plan.",
            "focus": "Current request.",
            "source_ids": ["web:official"],
            "citations": [],
        },
        {"kind": "addressed", "request_id": "request-1", "anchor_event_id": "anchor-1", "text": "Foreign."},
    ],
)
def test_fixed_grammar_refuses_input_envelopes_host_receipts_and_mixed_foreign_keys(raw: dict[str, Any]) -> None:
    assert all(not _schema_accepts(raw, decision_schema(phase)) for phase in DECISION_VARIANTS)


@pytest.mark.parametrize("goal", [0, 7, "0", "7", "Explain the first idea."])
def test_coverage_projection_preserves_native_index_and_frozen_name_alias_forms(goal: object) -> None:
    raw = {"verdict": "revise", "issues": ["missing_component"], "coverage": [{"goal": goal, "status": "missing"}]}
    assert _schema_accepts(raw, decision_schema("checkback"))


def altered_decision_format(change: str) -> dict[str, Any]:
    value = decision_response_format("conversation")
    changed_schema = decision_schema("conversation")
    changed_schema["additionalProperties"] = True
    alterations: dict[str, dict[str, Any]] = {
        "schema": {"json": json.dumps(changed_schema, separators=(",", ":"), ensure_ascii=False)},
        "reordered": {"json": canonical_json(decision_schema("conversation"))},
        "whitespace": {"grammar": " " + value["grammar"]},
        "grammar": {"grammar": 'root ::= "arbitrary"\n'},
        "grammar_reordered": {"grammar": "\n".join(reversed(value["grammar"].splitlines())) + "\n"},
        "grammar_dictionary": {"grammar": decision_schema("conversation")},
        "grammar_boolean": {"grammar": True},
        "grammar_null": {"grammar": None},
        "json_source": {"json": dict(decision_schema_inputs())["conversation"]},
        "dictionary": {"json": decision_schema("conversation")},
        "boolean": {"json": True},
        "string_boolean": {"json": "true"},
        "null": {"json": None},
        "extra": value | {"regex": ".*"},
    }
    return alterations[change]


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize(
    "change",
    [
        "schema",
        "reordered",
        "whitespace",
        "dictionary",
        "boolean",
        "string_boolean",
        "null",
        "extra",
        "grammar",
        "grammar_reordered",
        "grammar_dictionary",
        "grammar_boolean",
        "grammar_null",
        "json_source",
    ],
)
@pytest.mark.asyncio
async def test_native_relay_refuses_altered_schema_dialect_without_forwarding(*, enabled: bool, change: str) -> None:
    binding = profile().model_copy(update={"adaptive_context": True, "json_object_output": enabled})
    calls = 0

    async def relay(_operation: str, _payload: str) -> str:
        nonlocal calls
        calls += 1
        return completion("Unadmitted")

    request = httpx2.Request(
        "POST",
        "http://reach-model.invalid/v1/chat/completions",
        content=canonical_json(body() | {"structured_outputs": altered_decision_format(change)}).encode(),
    )
    with pytest.raises(ValueError, match="model_generation_binding"):
        await _RelayTransport(binding, relay).handle_async_request(request)
    assert calls == 0


def test_nested_format_mutation_cannot_change_the_baseline_schema_or_binding() -> None:
    binding = profile().model_copy(update={"adaptive_context": True, "json_object_output": True})
    baseline = canonical_json(generation_format(binding, phase="conversation"))
    digest = binding.digest
    exposed = generation_format(binding, phase="conversation")
    mutable_schema = decision_schema("conversation")
    mutable_schema["properties"]["text"]["maxLength"] = 1
    exposed["structured_outputs"]["grammar"] = canonical_json(mutable_schema)
    assert canonical_json(generation_format(binding, phase="conversation")) == baseline
    assert binding.digest == digest
    assert decision_format_phase(decision_response_format("conversation")) == "conversation"
    with pytest.raises(ValueError, match="model_generation_binding"):
        validate_generation_payload(binding, canonical_json(body() | exposed))


def test_source_inputs_keep_declared_order_and_carriers_recognize_only_exact_grammar_bytes() -> None:
    planning = decision_schema("planning")
    assert [list(branch["properties"]) for branch in planning["anyOf"]] == [
        ["kind", "text", "reaction", "gif_id"],
        ["kind", "text", "focus", "source_ids"],
    ]
    expected = {
        "conversation": ["kind", "text", "reaction", "gif_id"],
        "terminal_correction": ["kind", "text", "reaction", "gif_id"],
        "synthesis": ["kind", "text", "citations", "reaction", "gif_id"],
        "addressing": ["kind", "request_id", "anchor_event_id"],
        "checkback": [
            "verdict",
            "issues",
            "coverage",
            "clarification",
            "current_runtime_claims",
        ],
        "checkback_goals": [
            "verdict",
            "issues",
            "coverage",
            "clarification",
            "current_runtime_claims",
        ],
        "checkback_public": [
            "verdict",
            "issues",
            "coverage",
            "clarification",
            "current_runtime_claims",
        ],
        "checkback_public_goals": [
            "verdict",
            "issues",
            "coverage",
            "clarification",
            "current_runtime_claims",
        ],
        "goals": [
            "version",
            "goals",
            "constraints",
            "quotation_presentation",
            "required_context",
        ],
    }
    for variant, ordered in decision_schema_inputs():
        assert json.loads(ordered) == decision_schema(variant)
        carrier = decision_response_format(variant)
        assert set(carrier) == {"grammar"}
        assert decision_format_phase(carrier) == variant
        assert decision_format_phase({"json": ordered}) is None
        if variant in {"checkback_goals", "checkback_public_goals"}:
            branches = json.loads(ordered)["anyOf"]
            assert [branch["properties"]["verdict"]["const"] for branch in branches] == [
                "accept",
                "revise",
                "needs_evidence",
            ]
            assert all(list(branch["properties"]) == expected[variant] for branch in branches)
        elif decision_phase(variant) != "planning":
            assert list(json.loads(ordered)["properties"]) == expected[variant]


def test_research_source_projection_has_all_exact_inline_tuple_shapes() -> None:
    branch = next(
        item for item in decision_schema("planning")["anyOf"] if item["properties"].get("kind") == {"const": "research"}
    )
    variants = branch["properties"]["source_ids"]["anyOf"]
    patterns = {r"^doc:[A-Za-z0-9_./-]{1,200}$", r"^web:[a-z][a-z0-9_]{0,31}$"}
    shapes = {tuple(item["pattern"] for item in variant["prefixItems"]) for variant in variants}
    assert len(variants) == len(shapes) == RESEARCH_SOURCE_SHAPE_COUNT
    for variant in variants:
        assert set(variant) == {"type", "prefixItems", "items", "minItems", "maxItems"}
        assert variant["type"] == "array"
        assert variant["items"] is False
        assert variant["minItems"] == variant["maxItems"] == len(variant["prefixItems"])
        for item in variant["prefixItems"]:
            assert set(item) == {"type", "pattern"}
            assert item["type"] == "string"
            assert item["pattern"] in patterns


@pytest.mark.parametrize("kinds", [kinds for size in range(6) for kinds in product(("doc", "web"), repeat=size)])
def test_source_kind_projection_matches_native_counts_for_every_order_through_length_five(
    kinds: tuple[str, ...],
) -> None:
    raw = {
        "kind": "research",
        "text": "Read the admitted sources.",
        "focus": "Explain the current request from the admitted sources.",
        "source_ids": [f"{kind}:source_{index}" for index, kind in enumerate(kinds)],
    }
    try:
        ResearchPlan.model_validate_json(canonical_json(raw))
    except ValidationError:
        native_accepts = False
    else:
        native_accepts = True
    assert _schema_accepts(raw, decision_schema("planning")) is native_accepts


@pytest.mark.parametrize("source_id", ["doc:", "doc:a b", "doc:" + "a" * 201, "web:A", "web:" + "a" * 33])
def test_source_kind_projection_keeps_the_exact_native_identifier_patterns(source_id: str) -> None:
    raw = {
        "kind": "research",
        "text": "Read the admitted source.",
        "focus": "Explain the current request.",
        "source_ids": [source_id],
    }
    assert not _schema_accepts(raw, decision_schema("planning"))
    with pytest.raises(ValidationError):
        ResearchPlan.model_validate_json(canonical_json(raw))


def test_source_membership_and_uniqueness_remain_native_admission_requirements() -> None:
    duplicate = {
        "kind": "research",
        "text": "Read the source.",
        "focus": "Explain the current request.",
        "source_ids": ["doc:a", "doc:a"],
    }
    assert _schema_accepts(duplicate, decision_schema("planning"))
    with pytest.raises(ValidationError, match="conversation_research_sources"):
        ResearchPlan.model_validate_json(canonical_json(duplicate))
    foreign = {
        "kind": "research",
        "text": "Read the source.",
        "focus": "Explain the current request.",
        "source_ids": ["doc:foreign"],
    }
    assert _schema_accepts(foreign, decision_schema("planning"))
    with pytest.raises(ValueError, match="conversation_research_sources"):
        research_module.parse_research_plan(canonical_json(foreign), ({"id": "doc:allowed"},))


@pytest.mark.parametrize("phase", DECISION_VARIANTS)
def test_wire_accepts_only_exact_source_fixed_phase_members(
    phase: DecisionVariant,
) -> None:
    binding = profile().model_copy(
        update={
            "adaptive_context": True,
            "json_object_output": True,
            "checkback": True,
            "request_goals": phase in {"checkback_goals", "checkback_public_goals"},
        }
    )
    payload = body() | generation_format(binding, phase=phase)
    rebuilt = validate_generation_payload(binding, canonical_json(payload))
    assert rebuilt == payload
    assert decision_format_phase(rebuilt["structured_outputs"]) == phase


@pytest.mark.parametrize("phase", DECISION_PHASES)
def test_phase_grammar_forbids_the_wrong_raw_output_family(
    phase: DecisionPhase,
) -> None:
    fixtures: dict[str, dict[str, Any]] = {
        "planning": {
            "kind": "research",
            "text": "Read this source.",
            "focus": "Explain the current request.",
            "source_ids": ["doc:a"],
        },
        "conversation": {"kind": "read_more", "text": "Read earlier context."},
        "terminal_correction": {"kind": "answer", "text": "Ordinary answer."},
        "synthesis": {"kind": "answer", "text": "Sourced answer.", "citations": []},
        "addressing": {
            "kind": "addressed",
            "request_id": "request",
            "anchor_event_id": "anchor",
        },
        "checkback": {"verdict": "accept", "issues": []},
        "goals": {
            "version": 1,
            "goals": ["Explain this idea."],
            "constraints": [],
            "quotation_presentation": "none",
            "required_context": [],
        },
    }
    allowed = {
        "planning": {"planning"},
        "conversation": {"planning", "conversation"},
        "terminal_correction": {
            "planning",
            "conversation",
            "terminal_correction",
            "synthesis",
        },
        "synthesis": {"synthesis"},
        "addressing": {"addressing"},
        "checkback": {"checkback"},
        "goals": {"goals"},
    }
    for family, raw in fixtures.items():
        assert _schema_accepts(raw, decision_schema(phase)) is (phase in allowed[family])


def test_valid_synthesis_json_remains_invalid_in_the_native_conversation_parser() -> None:
    raw: dict[str, Any] = {"kind": "answer", "text": "An answer from the wrong family.", "citations": []}
    assert _schema_accepts(raw, decision_schema("synthesis"))
    assert not _schema_accepts(raw, decision_schema("planning"))
    with pytest.raises(ValidationError, match="citations"):
        ConversationDecision.model_validate_json(canonical_json(raw))


def test_phase_settings_preserve_held_grant_kwargs_and_refuse_explicit_format_conflicts() -> None:
    binding = profile().model_copy(update={"adaptive_context": True, "json_object_output": True})
    original = {"max_tokens": binding.max_tokens, "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}}
    grant = cast("CapabilityGrant", SimpleNamespace(model_settings=lambda: original))
    selected = _phase_settings(binding, grant, "conversation")
    assert selected is not None
    assert selected.get("max_tokens") == binding.max_tokens
    assert selected.get("extra_body") == {
        "chat_template_kwargs": {"enable_thinking": False},
        **generation_format(binding, phase="conversation"),
    }
    assert original["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    conflict = {"extra_body": generation_format(binding, phase="synthesis")}
    foreign = cast("CapabilityGrant", SimpleNamespace(model_settings=lambda: conflict))
    with pytest.raises(DocumentsRefused, match="model_generation_binding"):
        _phase_settings(binding, foreign, "conversation")
    selective = binding.model_copy(update={"thinking_phases": ("checkback",)})
    with pytest.raises(DocumentsRefused, match="model_generation_binding"):
        _phase_settings(selective, grant, "checkback")


@pytest.mark.parametrize(
    "value",
    [
        None,
        "checkback",
        {},
        [True],
        [1],
        ["foreign"],
        ["Checkback"],
        ["planning_documents"],
        ["planning_web"],
        ["checkback", "checkback"],
        [*DECISION_PHASES, "checkback"],
    ],
)
def test_thinking_phase_selection_is_closed_unique_and_bounded(value: object) -> None:
    values = profile().model_dump(mode="json") | {
        "adaptive_context": True,
        "json_object_output": True,
        "thinking_phases": value,
    }
    with pytest.raises(ValidationError):
        OperatorConversationProfile.model_validate_json(canonical_json(values))


def test_nonempty_thinking_phases_require_the_known_json_carrier() -> None:
    with pytest.raises(ValidationError, match="model_thinking_phases"):
        OperatorConversationProfile(
            persona_name="Example", persona_instructions="Be useful.", thinking_phases=("checkback",)
        )


@pytest.mark.parametrize("thinking", [False, True])
@pytest.mark.parametrize("json_mode", [False, True])
def test_empty_thinking_tuple_preserves_existing_profile_digest(*, thinking: bool, json_mode: bool) -> None:
    binding = profile().model_copy(
        update={"adaptive_context": True, "enable_thinking": thinking, "json_object_output": json_mode}
    )
    old_values = binding.model_dump(
        mode="json", exclude={"thinking_phases", "context_projection_version", "checkback_invalid_retry"}
    )
    if not thinking:
        old_values.pop("enable_thinking")
    if json_mode:
        old_values["decision_schema_bundle_sha256"] = DECISION_SCHEMA_BUNDLE_SHA256
    else:
        old_values.pop("json_object_output")
        old_values.pop("decision_schema_version")
    assert binding.digest == sha256(canonical_json(old_values).encode()).hexdigest()
    explicit = OperatorConversationProfile.model_validate_json(
        canonical_json(binding.model_dump(mode="json") | {"thinking_phases": []})
    )
    assert explicit.digest == binding.digest


def test_nonempty_thinking_tuple_retains_its_authored_order_and_binds_each_selection() -> None:
    binding = profile().model_copy(update={"adaptive_context": True, "json_object_output": True})
    first = binding.model_copy(update={"thinking_phases": ("checkback", "synthesis")})
    second = binding.model_copy(update={"thinking_phases": ("synthesis", "checkback")})
    assert first.digest != second.digest
    assert first.digest != binding.digest
    assert first.model_dump(mode="json")["thinking_phases"] == ["checkback", "synthesis"]
    assert second.model_dump(mode="json")["thinking_phases"] == ["synthesis", "checkback"]
    assert all(
        generation_thinking(first, phase=phase) == generation_thinking(second, phase=phase) for phase in DECISION_PHASES
    )
    all_phases = OperatorConversationProfile.model_validate_json(
        canonical_json(binding.model_dump(mode="json") | {"thinking_phases": list(DECISION_PHASES)})
    )
    assert all(generation_thinking(all_phases, phase=phase) for phase in DECISION_PHASES)
    with pytest.raises(ValueError, match="model_generation_binding"):
        generation_thinking(first, phase=None)


@pytest.mark.parametrize("phase", DECISION_VARIANTS)
@pytest.mark.parametrize("selected", ["planning", "checkback"])
@pytest.mark.parametrize("globally_enabled", [False, True])
def test_request_mode_uses_global_flag_or_the_validated_carrier_phase(
    phase: DecisionVariant, selected: DecisionPhase, *, globally_enabled: bool
) -> None:
    binding = profile().model_copy(
        update={
            "adaptive_context": True,
            "json_object_output": True,
            "enable_thinking": globally_enabled,
            "thinking_phases": (selected,),
            "checkback": True,
            "request_goals": phase in {"checkback_goals", "checkback_public_goals"},
        }
    )
    expected = globally_enabled or decision_phase(phase) == selected
    payload = body() | generation_format(binding, phase=phase) | {"chat_template_kwargs": {"enable_thinking": expected}}
    assert generation_thinking(binding, phase=phase) is expected
    assert validate_generation_payload(binding, canonical_json(payload)) == payload
    with pytest.raises(ValueError, match="model_generation_binding"):
        validate_generation_payload(
            binding,
            canonical_json(payload | {"chat_template_kwargs": {"enable_thinking": not expected}}),
        )


@pytest.mark.parametrize("phase", ["conversation", "checkback", "planning_documents", "planning_web"])
@pytest.mark.parametrize("finish", ["stop", "length", None, "unknown"])
@pytest.mark.asyncio
async def test_selective_thinking_completion_gate_uses_the_actual_validated_mode(
    phase: DecisionVariant, finish: str | None
) -> None:
    binding = profile().model_copy(
        update={"adaptive_context": True, "json_object_output": True, "thinking_phases": ("planning", "checkback")}
    )
    calls = 0

    async def relay(_operation: str, _payload: str) -> str:
        nonlocal calls
        calls += 1
        value = json.loads(completion('{"verdict":"accept","issues":[]}'))
        if finish is None:
            value["choices"][0].pop("finish_reason")
        else:
            value["choices"][0]["finish_reason"] = finish
        return canonical_json(value)

    payload = body() | generation_format(binding, phase=phase)
    payload.pop("chat_template_kwargs")
    request = httpx2.Request(
        "POST", "http://reach-model.invalid/v1/chat/completions", content=canonical_json(payload).encode()
    )
    if finish == "length" or (decision_phase(phase) in {"planning", "checkback"} and finish != "stop"):
        with pytest.raises(ValueError, match="model_response"):
            await _RelayTransport(binding, relay).handle_async_request(request)
    else:
        assert (await _RelayTransport(binding, relay).handle_async_request(request)).status_code == 200
    assert calls == 1


@pytest.mark.parametrize("variant", DECISION_VARIANTS)
def test_variants_map_to_seven_semantic_phases(variant: DecisionVariant) -> None:
    expected = (
        "planning" if variant.startswith("planning") else "checkback" if variant.startswith("checkback") else variant
    )
    assert decision_phase(variant) == expected
    assert decision_phase(variant) in DECISION_PHASES
    assert len(DECISION_PHASES) == 7
    assert len(DECISION_VARIANTS) == 12


@pytest.mark.parametrize("kinds", [kinds for size in range(6) for kinds in product(("doc", "web"), repeat=size)])
@pytest.mark.parametrize(("variant", "kind", "limit"), [("planning_documents", "doc", 3), ("planning_web", "web", 2)])
def test_resource_planning_projection_is_homogeneous_and_preserves_native_limits(
    variant: DecisionVariant, kind: str, limit: int, kinds: tuple[str, ...]
) -> None:
    raw = {
        "kind": "research",
        "text": "Read the admitted sources.",
        "focus": "Explain the current request from the admitted sources.",
        "source_ids": [f"{source_kind}:source_{index}" for index, source_kind in enumerate(kinds)],
    }
    expected = 1 <= len(kinds) <= limit and set(kinds) == {kind}
    assert _schema_accepts(raw, decision_schema(variant)) is expected
    if expected:
        ResearchPlan.model_validate_json(canonical_json(raw))
    for answer_kind in ("answer", "read_more", "clarify"):
        assert _schema_accepts({"kind": answer_kind, "text": "Ordinary decision."}, decision_schema(variant))


@pytest.mark.parametrize(("variant", "source_id"), [("planning_documents", "doc:a"), ("planning_web", "web:a")])
def test_resource_grammars_do_not_admit_membership_or_uniqueness(variant: DecisionVariant, source_id: str) -> None:
    raw = {
        "kind": "research",
        "text": "Read the source.",
        "focus": "Explain the current request.",
        "source_ids": [source_id],
    }
    assert _schema_accepts(raw, decision_schema(variant))
    with pytest.raises(ValueError, match="conversation_research_sources"):
        research_module.parse_research_plan(canonical_json(raw), ())
    raw["source_ids"] = [source_id, source_id]
    assert _schema_accepts(raw, decision_schema(variant))
    with pytest.raises(ValidationError, match="conversation_research_sources"):
        ResearchPlan.model_validate_json(canonical_json(raw))


@pytest.mark.parametrize("field", ["SCHEMA_INPUT_SHA256", "CONVERTER_METADATA_JSON", "GRAMMARS", "BUNDLE_SHA256"])
def test_stale_artifact_refuses_runtime_without_blocking_pure_schema_generation(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    changes = {
        "SCHEMA_INPUT_SHA256": "a" * 64,
        "CONVERTER_METADATA_JSON": "{}",
        "GRAMMARS": tuple((name, grammar + "\n") for name, grammar in generated_grammar.GRAMMARS),
        "BUNDLE_SHA256": "b" * 64,
    }
    monkeypatch.setattr(generated_grammar, field, changes[field])
    assert len(decision_schema_inputs()) == len(DECISION_VARIANTS)
    assert decision_schema("planning_documents")["anyOf"][1]["properties"]["source_ids"]["maxItems"] == 3
    with pytest.raises(ValueError, match="decision_grammar_artifact"):
        decision_response_format("conversation")


@pytest.mark.parametrize("variant", DECISION_VARIANTS)
def test_compact_grammar_carriers_fit_existing_transport_limits(
    variant: DecisionVariant,
) -> None:
    binding = profile().model_copy(
        update={
            "adaptive_context": True,
            "json_object_output": True,
            "checkback": True,
            "request_goals": variant in {"checkback_goals", "checkback_public_goals"},
        }
    )
    payload = canonical_json(body() | generation_format(binding, phase=variant))
    assert MAX_MODEL_PAYLOAD_BYTES == 1_048_576
    assert MAX_WIRE_BYTES == 2_097_152
    assert binding.timeout_seconds == 60
    assert len(payload.encode()) < MAX_MODEL_PAYLOAD_BYTES
    frame = OperatorModelRequest(
        call_id=str(uuid4()),
        binding_digest=binding.digest,
        operation="generate",
        payload_json=payload,
    ).model_dump_json()
    assert len(frame.encode()) < MAX_WIRE_BYTES
    assert validate_generation_payload(binding, payload)["structured_outputs"] == decision_response_format(variant)


def test_converter_output_fingerprints_pin_all_twelve_effective_grammars() -> None:
    expected = {
        "planning": "75fb3d496a89fe4bbd0dd03bb5f6a56e35e5a007d5b2695e2d4f28675095cfae",
        "conversation": "e4ca476a27f5ad95416fc96eb3a9690fcd4da9c0ce9a944b3369097cc48f4575",
        "terminal_correction": "2942ed35e7f3d56e91df0bb7e2896fa36154abde4bcf282e2a19e99b72a88b94",
        "synthesis": "cf2214656ba92a34aeee91c3b9557a97d95c2b385095892e8cdb225ca405b4f2",
        "addressing": "c12dd303235a0491ad50c16ab1313fb913bf11d44149257fb6a70c214a2fa735",
        "checkback": "5a6967c45a7cb956b72840b36d62b76e76d03a70706fa229736dbdf67fec36f6",
        "goals": "4db70e632f09d12117f01e7be2ea68f0ba6ef4047de79c39a56720f772cbcac5",
        "planning_documents": "df5ccf01de8c78d4c6748b8efb0f046a6198d23254ba3d5a9e46e350f34d8ac2",
        "planning_web": "d4a7986eba34ad2c9b1c082e77d490a3a02a9b9ab622882813c65ca6025f3186",
        "checkback_goals": "1fdc7330a943c585da92f3c6afca7da363643d7a2f6e41f557d11a774dc46282",
        "checkback_public": "da8a54df6bee8b3bafd09dd55718bca6681942755351c8c0e4021d6eda575d75",
        "checkback_public_goals": "da27d866829d0743b0b1949c31c3badfc71a7789613dbd1feb46aeacee461b57",
    }
    assert tuple(expected) == DECISION_VARIANTS
    assert {
        variant: sha256(decision_response_format(variant)["grammar"].encode()).hexdigest()
        for variant in DECISION_VARIANTS
    } == expected


def test_bounded_string_normalization_preserves_nonempty_json_with_native_maximum() -> None:
    source = (
        r'root ::= (("\"" unit{1, 200} "\""))'
        "\n"
        r"unit ::= (([^\"\\\r\n]))"
        "\n"
        r'other ::= (("\"" unit_two{1, 200} "\""))'
        "\n"
        r"unit_two ::= (([^\"\\\r\n]))"
        "\n"
        r'third ::= (("\"" unit_three{1, 200} "\""))'
        "\n"
        r"unit_three ::= (([^\"\\\r\n]))"
        "\n"
    )
    normalized = grammar_generator.normalize_bounded_json_strings("goals", source)
    assert normalized.splitlines()[0] == r'root ::= (("\"" reach_json_scalar_v1 reach_json_string_tail_v2))'
    assert normalized.splitlines()[1] == "unit ::= ((reach_json_scalar_v1))"
    assert r"[^\0-\x1f\"\\]" in normalized
    assert r'"\\u" [dD] [89aAbB]' in normalized
    assert r'"\\u" [dD] [c-fC-F]' in normalized
    assert "{1, 200}" not in normalized
    assert "reach_json_string_tail_v2 ::=" in normalized
    assert r"(=([ \n\t]* [,}\]:]))" in normalized
    assert r"(([^\"\\\r\n]))" not in normalized
    with pytest.raises(ValueError, match="decision_grammar_string_normalization"):
        grammar_generator.normalize_bounded_json_strings("goals", normalized)


@pytest.mark.parametrize(
    "mutation",
    [
        "foreign_variant",
        "missing_leaf",
        "extra_leaf",
        "duplicate_rule",
        "helper_collision",
        "unbounded",
        "zero_minimum",
        "unexpected_minimum",
        "excess_maximum",
        "reversed_bounds",
        "foreign_reference",
        "unused_leaf",
        "unrecognized_leaf",
    ],
)
def test_bounded_string_normalization_refuses_unreviewed_converter_shapes(
    mutation: str,
) -> None:
    source = (
        r'root ::= (("\"" unit{1, 200} "\""))'
        "\n"
        r"unit ::= (([^\"\\\r\n]))"
        "\n"
        r'other ::= (("\"" unit_two{1, 200} "\""))'
        "\n"
        r"unit_two ::= (([^\"\\\r\n]))"
        "\n"
        r'third ::= (("\"" unit_three{1, 200} "\""))'
        "\n"
        r"unit_three ::= (([^\"\\\r\n]))"
        "\n"
    )
    variant = "goals"
    if mutation == "foreign_variant":
        variant = "foreign"
    elif mutation == "missing_leaf":
        source = "\n".join(line for index, line in enumerate(source.splitlines()) if index != 1) + "\n"
    elif mutation == "extra_leaf":
        source += r"extra_unit ::= (([^\"\\\r\n]))" + "\n"
    elif mutation == "duplicate_rule":
        source += source.splitlines()[1] + "\n"
    elif mutation == "helper_collision":
        source += 'reach_json_scalar_v1 ::= "A"\n'
    elif mutation == "foreign_reference":
        source += "foreign ::= unit\n"
    elif mutation == "unused_leaf":
        source = "\n".join(source.splitlines()[1:]) + "\n"
    elif mutation == "unrecognized_leaf":
        source = source.replace(r"[^\"\\\r\n]", r"[^\"\\]")
    else:
        bound = {
            "unbounded": "*",
            "zero_minimum": "{0, 200}",
            "unexpected_minimum": "{2, 200}",
            "excess_maximum": "{1, 8001}",
            "reversed_bounds": "{200, 1}",
        }[mutation]
        source = source.replace("{1, 200}", bound)
    with pytest.raises(ValueError, match="decision_grammar_string_normalization"):
        grammar_generator.normalize_bounded_json_strings(cast("DecisionVariant", variant), source)


@pytest.mark.parametrize("variant", DECISION_VARIANTS)
def test_generated_normalized_strings_use_recursive_tail_and_native_maximum(
    variant: DecisionVariant,
) -> None:
    grammar = decision_response_format(variant)["grammar"]
    assert isinstance(grammar, str)
    assert r"(([^\"\\\r\n]))" not in grammar
    assert grammar.count("reach_json_scalar_v1 ::=") == 1
    assert grammar.count("reach_json_hex_v1 ::=") == 1
    assert grammar.count("reach_json_escape_v2 ::=") == 1
    assert grammar.count("reach_json_string_tail_v2 ::=") == 1
    assert r"[^\0-\x1f\"\\]" in grammar
    expected_count = {
        "planning": 4,
        "conversation": 2,
        "terminal_correction": 2,
        "synthesis": 3,
        "addressing": 2,
        "checkback": 4,
        "goals": 3,
        "planning_documents": 4,
        "planning_web": 4,
        "checkback_goals": 14,
        "checkback_public": 4,
        "checkback_public_goals": 14,
    }[variant]
    rules = dict(line.split(" ::= ", 1) for line in grammar.splitlines())
    leaves = {name for name, body in rules.items() if body == "((reach_json_scalar_v1))"}
    assert len(leaves) == expected_count
    assert (
        sum(body == r'(("\"" reach_json_scalar_v1 reach_json_string_tail_v2))' for body in rules.values())
        == expected_count
    )
    assert not any(re.search(r"\b" + re.escape(leaf) + r"\{", grammar) for leaf in leaves)


@pytest.mark.parametrize(
    "text", ['First\n- "Exact quotation"\n- Path a\\b.', "Slovenský text 漢字 👀", "A" * 7998 + "\nA"]
)
def test_native_answer_parsers_keep_escaped_text_and_original_character_bound(text: str) -> None:
    raw = canonical_json({"kind": "answer", "text": text})
    assert ConversationDecision.model_validate_json(raw).text == text
    assert ConversationDecision.model_validate(strict_json(raw.encode())).text == text
    assert _ResearchDecision.model_validate_json(raw).text == text
    if len(text) == 8000:
        with pytest.raises(ValidationError, match="string_too_long"):
            _ResearchDecision.model_validate_json(canonical_json({"kind": "answer", "text": text + "A"}))
        with pytest.raises(ValidationError, match="string_too_long"):
            ConversationDecision.model_validate(
                strict_json(canonical_json({"kind": "answer", "text": text + "A"}).encode())
            )


@pytest.mark.parametrize(
    ("model", "base", "field", "limit"),
    [
        (ConversationDecision, {"kind": "answer"}, "text", 8000),
        (_ResearchDecision, {"kind": "answer"}, "text", 8000),
        (ResearchPlan, {"kind": "research", "focus": "Target", "source_ids": ["doc:a"]}, "text", 500),
        (ResearchPlan, {"kind": "research", "text": "Read source", "source_ids": ["doc:a"]}, "focus", 500),
        (AddressingDecision, {"kind": "addressed", "anchor_event_id": "anchor"}, "request_id", 128),
        (AddressingDecision, {"kind": "addressed", "request_id": "request"}, "anchor_event_id", 128),
        (CheckbackJudgment, {"verdict": "needs_evidence", "issues": ["missing_evidence"]}, "clarification", 500),
    ],
)
def test_native_scalar_maxima_remain_decisive_after_provider_projection(
    model: type[Record], base: dict[str, Any], field: str, limit: int
) -> None:
    admitted = base | {field: "A" * limit}
    assert model.model_validate_json(canonical_json(admitted)).model_dump()[field] == "A" * limit
    with pytest.raises(ValidationError, match="string_too_long"):
        model.model_validate_json(canonical_json(base | {field: "A" * (limit + 1)}))


@pytest.mark.parametrize("limit", [200, 240])
def test_native_array_string_maxima_remain_decisive_after_provider_projection(
    limit: int,
) -> None:
    def payload(size: int) -> dict[str, Any]:
        return (
            {
                "version": 1,
                "goals": ["A" * size],
                "constraints": [],
                "quotation_presentation": "none",
                "required_context": [],
            }
            if limit == 200
            else {
                "verdict": "accept",
                "issues": [],
                "current_runtime_claims": ["A" * size],
            }
        )

    model: type[Record] = TaskRequirements if limit == 200 else CheckbackJudgment
    model.model_validate_json(canonical_json(payload(limit)))
    with pytest.raises(ValidationError, match="string_too_long"):
        model.model_validate_json(canonical_json(payload(limit + 1)))


def test_native_coverage_quote_limit_remains_decisive_after_provider_projection() -> None:
    valid = {"goal": 0, "status": "complete", "answer_quote": "A" * 240}
    assert checkback_module.CheckbackCoverage.model_validate_json(canonical_json(valid)).answer_quote == "A" * 240
    with pytest.raises(ValidationError, match="string_too_long"):
        checkback_module.CheckbackCoverage.model_validate_json(canonical_json(valid | {"answer_quote": "A" * 241}))


@pytest.mark.parametrize("field", ["gif_id", "citations"])
def test_native_patterned_selection_limits_remain_decisive_after_provider_projection(field: str) -> None:
    valid = "a" * 32 if field == "gif_id" else "doc:" + "a" * 200
    for value, accepted in [(valid, True), (valid + "a", False)]:
        raw = canonical_json({"kind": "answer", "text": "Answer", field: value if field == "gif_id" else [value]})
        if accepted:
            _ResearchDecision.model_validate_json(raw)
        else:
            with pytest.raises(ValidationError, match="string_pattern_mismatch"):
                _ResearchDecision.model_validate_json(raw)


def test_native_read_more_reason_keeps_its_separate_maximum() -> None:
    assert (
        ConversationDecision.model_validate_json(canonical_json({"kind": "read_more", "text": "A" * 500})).text
        == "A" * 500
    )
    with pytest.raises(ValidationError, match="conversation_context_reason"):
        ConversationDecision.model_validate_json(canonical_json({"kind": "read_more", "text": "A" * 501}))


@pytest.mark.parametrize("variant", ["planning", "planning_documents", "planning_web"])
@pytest.mark.parametrize(
    "focus_patch",
    [{}, {"focus": None}, {"focus": ""}, {"focus": "x" * 501}, {"focus": 0}, {"focus": False}, {"focus": []}],
)
def test_provider_research_branch_requires_nonnull_bounded_focus(
    variant: DecisionVariant, focus_patch: dict[str, Any]
) -> None:
    raw = {
        "kind": "research",
        "text": "Read the selected source.",
        "source_ids": ["web:a" if variant == "planning_web" else "doc:a"],
    } | focus_patch
    assert not _schema_accepts(raw, decision_schema(variant))


@pytest.mark.parametrize("request_goals", [False, True])
@pytest.mark.parametrize("public", [False, True])
def test_goal_review_carrier_is_selected_and_bound_by_the_trusted_profile(*, request_goals: bool, public: bool) -> None:
    binding = profile().model_copy(
        update={
            "adaptive_context": True,
            "json_object_output": True,
            "checkback": True,
            "request_goals": request_goals,
            "thinking_phases": ("checkback",),
        }
    )
    selected: DecisionVariant = (
        "checkback_public_goals"
        if public and request_goals
        else "checkback_public"
        if public
        else "checkback_goals"
        if request_goals
        else "checkback"
    )
    foreign: DecisionVariant = (
        "checkback_public"
        if public and request_goals
        else "checkback_public_goals"
        if public
        else "checkback"
        if request_goals
        else "checkback_goals"
    )
    actual = generation_format(binding, phase="checkback_public" if public else "checkback")
    assert actual == {"structured_outputs": decision_response_format(selected)}
    payload = body() | actual | {"chat_template_kwargs": {"enable_thinking": True}}
    assert validate_generation_payload(binding, canonical_json(payload)) == payload
    assert generation_thinking(binding, phase=selected) is True
    with pytest.raises(ValueError, match="model_generation_binding"):
        validate_generation_payload(
            binding,
            canonical_json(payload | {"structured_outputs": decision_response_format(foreign)}),
        )
    if not request_goals:
        with pytest.raises(ValueError, match="model_generation_binding"):
            generation_format(binding, phase="checkback_public_goals" if public else "checkback_goals")


@pytest.mark.parametrize("request_goals", [False, True])
@pytest.mark.parametrize("foreign", [False, True])
@pytest.mark.asyncio
async def test_actual_sdk_goal_review_carrier_conflict_is_refused_before_relay(
    *, request_goals: bool, foreign: bool
) -> None:
    binding = profile().model_copy(
        update={"adaptive_context": True, "json_object_output": True, "checkback": True, "request_goals": request_goals}
    )
    selected: DecisionVariant = "checkback_goals" if request_goals != foreign else "checkback"
    calls = 0
    output = canonical_json(
        {
            "verdict": "accept",
            "issues": [],
            "coverage": [{"goal": 0, "status": "complete", "answer_quote": "Visible answer."}],
        }
    )

    async def relay(_operation: str, payload: str) -> str:
        nonlocal calls
        calls += 1
        rebuilt = validate_generation_payload(binding, payload)
        assert decision_format_phase(rebuilt["structured_outputs"]) == selected
        return completion(output)

    connector = OperatorModelConnector(binding, relay)
    agent: Agent[None, str] = Agent(
        connector.get_model(model_id=binding.model_id),
        instructions="Review the answer.",
        output_type=str,
        deps_type=type(None),
        retries=0,
        model_settings={"max_tokens": binding.max_tokens, "temperature": binding.temperature},
    )
    async with agent:
        with override_allow_model_requests(True):  # noqa: FBT003 - installed SDK with an in-memory relay
            if foreign:
                with pytest.raises(ValueError, match="model_generation_binding"):
                    await agent.run(
                        "Review",
                        model_settings={"extra_body": {"structured_outputs": decision_response_format(selected)}},
                    )
            else:
                result = await agent.run(
                    "Review", model_settings={"extra_body": {"structured_outputs": decision_response_format(selected)}}
                )
                assert result.output == output
    assert calls == (0 if foreign else 1)


@pytest.mark.parametrize(
    "coverage",
    [None, [], [{"goal": 0, "status": "complete"}], [{"goal": 0, "status": "complete", "answer_quote": None}]],
)
def test_goal_review_provider_shape_requires_coverage_and_complete_quotes(coverage: object) -> None:
    raw: dict[str, Any] = {"verdict": "accept", "issues": [], "current_runtime_claims": [","]}
    if coverage is not None:
        raw["coverage"] = coverage
    assert not _schema_accepts(raw, decision_schema("checkback_goals"))
    assert _schema_accepts(raw, decision_schema("checkback"))


@pytest.mark.parametrize("variant", ["checkback_public", "checkback_public_goals"])
@pytest.mark.parametrize("verdict", ["accept", "revise", "needs_evidence"])
@pytest.mark.parametrize("claims", [{}, {"current_runtime_claims": None}, {"current_runtime_claims": []}])
def test_public_review_requires_explicit_nonnull_runtime_claims_in_every_verdict(
    variant: DecisionVariant, verdict: str, claims: dict[str, Any]
) -> None:
    goals = ["Explain this idea."] if variant == "checkback_public_goals" else []
    context = {
        "research_phase": "synthesis",
        "research_sources": [{"id": "doc:a", "status": "ok", "text": "Visible answer."}],
        "evidence_scope": {
            "version": "public-text-v1",
            "source_authority": "public_reference_text",
            "successful_read_proves": "source_bytes_obtained",
            "operator_runtime_observation": "not_supplied",
        },
        "request_goals": goals,
    }
    envelope = checkback_module.CheckbackEnvelope.prepare(
        make_request(action="converse"), canonical_json(context), persona_name="Example"
    )
    candidate = canonical_json({"kind": "answer", "text": "Visible answer."})
    raw = {
        "verdict": verdict,
        "issues": [] if verdict == "accept" else ["missing_evidence"],
        **({"coverage": [{"goal": 0, "status": "complete", "answer_quote": "Visible answer."}]} if goals else {}),
        **({"clarification": "Which source?"} if verdict == "needs_evidence" else {}),
        **claims,
    }
    expected = claims.get("current_runtime_claims") == []
    assert _schema_accepts(raw, decision_schema(variant)) is expected
    if expected:
        assert envelope.parse(canonical_json(raw), candidate).current_runtime_claims == ()
    else:
        with pytest.raises(ValueError, match="conversation_checkback_runtime_claims"):
            envelope.parse(canonical_json(raw), candidate)


@pytest.mark.parametrize("status", ["missing", "unsupported"])
@pytest.mark.parametrize("quote", [{}, {"answer_quote": None}, {"answer_quote": "Visible answer."}])
def test_goal_review_provider_shape_preserves_noncomplete_quote_options(status: str, quote: dict[str, Any]) -> None:
    raw = {"verdict": "revise", "issues": ["missing_component"], "coverage": [{"goal": 0, "status": status, **quote}]}
    assert _schema_accepts(raw, decision_schema("checkback_goals"))
    CheckbackJudgment.model_validate_json(canonical_json(raw))


@pytest.mark.parametrize("status", ["missing", "unsupported"])
def test_goal_review_provider_refuses_accept_with_incomplete_coverage(status: str) -> None:
    envelope = checkback_module.CheckbackEnvelope.prepare(
        make_request(action="converse"),
        canonical_json({"request_goals": ["Give the requested answer"]}),
        persona_name="Example",
    )
    candidate = canonical_json({"kind": "clarify", "text": "The visible excerpt is incomplete."})
    raw = {
        "verdict": "accept",
        "issues": [],
        "coverage": [{"goal": 0, "status": status, "answer_quote": "The visible excerpt is incomplete."}],
        "current_runtime_claims": [],
    }
    assert not _schema_accepts(raw, decision_schema("checkback_goals"))
    assert _schema_accepts(raw, decision_schema("checkback"))
    with pytest.raises(ValueError, match="conversation_checkback_coverage"):
        envelope.parse(canonical_json(raw), candidate)


@pytest.mark.parametrize("verdict", ["accept", "revise", "needs_evidence"])
@pytest.mark.parametrize("issues", [[], ["missing_component"]])
@pytest.mark.parametrize("clarification", [{}, {"clarification": None}, {"clarification": "Which source?"}])
def test_goal_review_provider_projects_native_verdict_conditions(
    verdict: str, issues: list[str], clarification: dict[str, Any]
) -> None:
    raw = {
        "verdict": verdict,
        "issues": issues,
        "coverage": [{"goal": 0, "status": "complete", "answer_quote": "Visible answer."}],
        **clarification,
    }
    expected = (verdict == "accept") == (not issues) and (
        (verdict == "needs_evidence") == (clarification.get("clarification") is not None)
    )
    assert _schema_accepts(raw, decision_schema("checkback_goals")) is expected
    if expected:
        CheckbackJudgment.model_validate_json(canonical_json(raw))
    else:
        with pytest.raises(ValueError, match=r"conversation_checkback_(verdict|clarification)"):
            CheckbackJudgment.model_validate_json(canonical_json(raw))


@pytest.mark.parametrize("mutation", ["missing_goal", "duplicate_goal", "foreign_quote", "incomplete_accept"])
def test_goal_review_provider_projection_keeps_exact_coverage_and_evidence_native(mutation: str) -> None:
    envelope = checkback_module.CheckbackEnvelope.prepare(
        make_request(action="converse"),
        canonical_json({"request_goals": ["First outcome", "Second outcome"]}),
        persona_name="Example",
    )
    candidate = canonical_json({"kind": "answer", "text": "First result. Second result."})
    coverage: list[dict[str, Any]] = [
        {"goal": 0, "status": "complete", "answer_quote": "First result."},
        {"goal": 1, "status": "complete", "answer_quote": "Second result."},
    ]
    raw = {"verdict": "accept", "issues": [], "coverage": coverage}
    assert _schema_accepts(raw, decision_schema("checkback_goals"))
    assert envelope.parse(canonical_json(raw), candidate).verdict == "accept"
    if mutation == "missing_goal":
        coverage.pop()
    elif mutation == "duplicate_goal":
        coverage[1]["goal"] = 0
    elif mutation == "foreign_quote":
        coverage[1]["answer_quote"] = "Unstated result."
    else:
        coverage[1]["status"] = "missing"
    assert _schema_accepts(raw, decision_schema("checkback_goals")) is (mutation != "incomplete_accept")
    with pytest.raises(ValueError, match="conversation_checkback_coverage"):
        envelope.parse(canonical_json(raw), candidate)


@pytest.mark.parametrize("variant", ["planning", "planning_documents", "planning_web"])
@pytest.mark.parametrize("focus", ["x", "x" * 500])
def test_provider_research_focus_admits_both_native_text_boundaries(variant: DecisionVariant, focus: str) -> None:
    raw = {
        "kind": "research",
        "text": "Read the selected source.",
        "focus": focus,
        "source_ids": ["web:a" if variant == "planning_web" else "doc:a"],
    }
    assert _schema_accepts(raw, decision_schema(variant))
    assert ResearchPlan.model_validate_json(canonical_json(raw)).focus == focus


@pytest.mark.parametrize("variant", ["planning", "planning_documents", "planning_web"])
@pytest.mark.parametrize("focus_patch", [{}, {"focus": None}])
def test_native_legacy_research_parser_preserves_optional_focus(
    variant: DecisionVariant, focus_patch: dict[str, Any]
) -> None:
    source_id = "web:a" if variant == "planning_web" else "doc:a"
    raw = {"kind": "research", "text": "Read the selected source.", "source_ids": [source_id]} | focus_patch
    assert not _schema_accepts(raw, decision_schema(variant))
    assert not ResearchPlan.model_fields["focus"].is_required()
    plan = research_module.parse_research_plan(canonical_json(raw), ({"id": source_id},))
    assert plan is not None
    assert plan.focus is None
    assert plan.source_ids == (source_id,)


@pytest.mark.parametrize("opt_in", ["request_goals", "json_object_output"])
@pytest.mark.parametrize("version", [None, 3, 4], ids=["omitted", "old-v3", "explicit-v4"])
@pytest.mark.parametrize("input_mode", ["python", "json"])
def test_enabled_profiles_require_explicit_v4_without_silent_migration(
    opt_in: str, version: int | None, input_mode: str
) -> None:
    raw: dict[str, Any] = {
        "persona_name": "Example",
        "persona_instructions": "Be useful.",
        "adaptive_context": True,
        "checkback": True,
        opt_in: True,
    }
    if version is not None:
        raw["decision_schema_version"] = version

    def admit() -> OperatorConversationProfile:
        return (
            OperatorConversationProfile.model_validate_json(canonical_json(raw))
            if input_mode == "json"
            else OperatorConversationProfile.model_validate(raw)
        )

    if version == 4:
        accepted = admit()
        assert accepted.decision_schema_version == 4
        assert "decision_schema_version" in accepted.model_fields_set
    else:
        with pytest.raises(ValidationError, match="decision_schema_version"):
            admit()


def test_disabled_legacy_omitted_schema_version_keeps_its_binding() -> None:
    raw = {"persona_name": "Example", "persona_instructions": "Be useful."}
    accepted = OperatorConversationProfile.model_validate_json(canonical_json(raw))
    assert "decision_schema_version" not in accepted.model_fields_set
    assert accepted.digest == profile().digest == LEGACY_PROFILE_DIGEST


def test_explicit_210000_input_bound_preserves_default_and_physical_limits() -> None:
    legacy = profile()
    selected = OperatorConversationProfile.model_validate(legacy.model_dump() | {"max_input_chars": 210_000})
    assert legacy.max_input_chars == 20_000
    assert selected.digest != legacy.digest
    assert (selected.max_context, selected.max_tokens, selected.timeout_seconds) == (
        legacy.max_context,
        legacy.max_tokens,
        legacy.timeout_seconds,
    )
    assert (MAX_MODEL_PAYLOAD_BYTES, MAX_WIRE_BYTES) == (1_048_576, 2_097_152)
    payload = body() | {"messages": [{"role": "system", "content": "s"}, {"role": "user", "content": "x" * 209_999}]}
    assert validate_generation_payload(selected, canonical_json(payload))["messages"] == payload["messages"]
    with pytest.raises(ValueError, match="model_generation_binding"):
        validate_generation_payload(legacy, canonical_json(payload))
    payload["messages"][1]["content"] += "x"
    with pytest.raises(ValueError, match="model_generation_binding"):
        validate_generation_payload(selected, canonical_json(payload))
    payload["messages"] = [{"role": "system", "content": "x" * 210_001}]
    with pytest.raises(ValidationError, match="string_too_long"):
        validate_generation_payload(selected, canonical_json(payload))
    with pytest.raises(ValidationError):
        OperatorConversationProfile.model_validate(legacy.model_dump() | {"max_input_chars": 210_001})
    payload["messages"] = [{"role": "system", "content": "\x00" * 180_000}]
    with pytest.raises(ValueError, match="model_payload"):
        validate_generation_payload(selected, canonical_json(payload))


def test_model_binding_is_configurable_and_keeps_the_legacy_defaults() -> None:
    legacy = profile()
    assert (legacy.animator_id, legacy.model_id) == ("night-qwen38", "Qwen3.8-27B")
    assert legacy.digest == LEGACY_PROFILE_DIGEST
    routed = OperatorConversationProfile(
        persona_name="Example",
        persona_instructions="Be useful.",
        animator_id="gateway",
        model_id="vendor/small-model",
    )
    assert routed.capability_key == "gateway:chat:vendor/small-model"
    assert routed.digest != legacy.digest
    payload = canonical_json(body() | {"model": "vendor/small-model"})
    assert validate_generation_payload(routed, payload)["model"] == "vendor/small-model"
    with pytest.raises(ValueError, match="model_generation_binding"):
        validate_generation_payload(routed, canonical_json(body()))


@pytest.mark.parametrize(
    ("observed", "accepted"),
    [
        ("vendor/small-model", True),
        ("small-model", True),
        ("model", False),
        ("other/small-model", False),
        ("", False),
        (None, False),
        (7, False),
    ],
)
def test_served_model_accepts_only_the_exact_id_or_its_gateway_route_suffix(
    observed: object, *, accepted: bool
) -> None:
    routed = OperatorConversationProfile(
        persona_name="Example", persona_instructions="Be useful.", model_id="vendor/small-model"
    )
    assert routed.serves(observed) is accepted
    assert profile().serves("Qwen3.8-27B")
    assert not profile().serves("27B")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_id", ""),
        ("model_id", "has space"),
        ("model_id", "/leading"),
        ("animator_id", "Upper"),
        ("animator_id", ""),
    ],
)
def test_model_binding_identifiers_are_closed(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        OperatorConversationProfile.model_validate(
            {"persona_name": "Example", "persona_instructions": "Be useful.", field: value}
        )
