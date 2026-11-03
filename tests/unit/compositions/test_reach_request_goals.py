"""Request decomposition precedes planning and preserves each requested outcome."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError
from pydantic_ai.models import override_allow_model_requests
from scripts.reach_worker import build_runtime

from lychd.compositions.reach.conversation_workflow import make_conversation_intent, reach_conversation_workflow
from lychd.compositions.reach.documents_workflow import DocumentsRefused
from lychd.compositions.reach.operator_model_wire import (
    OperatorConversationProfile,
    canonical_json,
    validate_generation_payload,
)
from lychd.compositions.reach.operator_trace import ReachTraceEvent, trace_bytes
from lychd.compositions.reach.operator_wire import ReachHistoryEntry
from lychd.compositions.reach.request_goals import (
    parse_request_goals,
    request_goals_digest,
    request_goals_prompt,
)
from lychd.compositions.reach.research_wire import OperatorResearchRequest, OperatorResearchResponse
from tests.unit.compositions.test_reach_addressing import continuation, continuation_policy
from tests.unit.compositions.test_reach_conversation import completion, policy, profile
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_request
from tests.unit.compositions.test_reach_research import answer_json, relay_response, research_profile

GOALS = ("Describe the current supported behavior.", "Describe the future planned behavior.")
QUESTION = "What works today, and what is planned next?"
ANSWER = "Today supports bounded turns. Future work includes durable continuity."


def interpreted_profile() -> OperatorConversationProfile:
    return profile().model_copy(
        update={
            "adaptive_context": True,
            "checkback": True,
            "request_goals": True,
            "max_input_chars": 24_000,
        }
    )


@pytest.mark.parametrize(
    "output",
    [
        "{}",
        '{"goals":[]}',
        '{"goals":[" "]}',
        '{"goals":[1]}',
        '{"goals":["same"," same "]}',
        canonical_json({"goals": ["x" * 201]}),
        canonical_json({"goals": [str(index) for index in range(9)]}),
        '{"goals":["one"],"candidate":"forbidden"}',
    ],
)
def test_goals_are_strict_bounded_nonblank_and_unique(output: str) -> None:
    with pytest.raises(ValidationError):
        parse_request_goals(output)


def test_goals_profile_is_explicit_and_requires_checkback() -> None:
    assert not profile().request_goals
    value = profile().model_dump(mode="json") | {"request_goals": True, "adaptive_context": True}
    with pytest.raises(ValidationError):
        OperatorConversationProfile.model_validate_json(canonical_json(value))
    accepted = OperatorConversationProfile.model_validate_json(canonical_json(value | {"checkback": True}))
    assert accepted.request_goals
    assert parse_request_goals('{"goals":[" First outcome ","Second outcome"]}').goals == (
        "First outcome",
        "Second outcome",
    )


def test_interpretation_keeps_anchors_and_trims_only_oldest_history_to_budget() -> None:
    history = tuple(
        ReachHistoryEntry(
            subject_id="person:one",
            event_id=f"old:{index}",
            conversation_id="channel:one",
            occurred_at=NOW - timedelta(seconds=10 - index),
            text=f"Message {index} " + "h" * 1200,
        )
        for index in range(3)
    )
    anchor = history[-1].model_copy(update={"event_id": "anchor", "text": "The exact referenced answer."})
    request = make_request(action="converse", question=QUESTION).model_copy(
        update={
            "history": history,
            "reply_anchor": anchor,
        }
    )
    binding = interpreted_profile().model_copy(update={"max_input_chars": 4500})
    prompt = json.loads(request_goals_prompt(binding, request))
    assert set(prompt) == {
        "phase",
        "question",
        "reply_anchor",
        "continuation_anchor",
        "recent_messages",
        "omitted_recent_messages",
    }
    assert prompt["question"] == QUESTION
    assert prompt["reply_anchor"] == anchor.model_dump(mode="json")
    assert prompt["omitted_recent_messages"] > 0
    assert prompt["recent_messages"]
    assert prompt["recent_messages"] == [
        entry.model_dump(mode="json") for entry in history[prompt["omitted_recent_messages"] :]
    ]
    oversized = request.model_copy(update={"event": request.event.model_copy(update={"question": "q" * 8192})})
    with pytest.raises(DocumentsRefused, match="conversation_budget"):
        request_goals_prompt(binding, oversized)


def test_goal_checkpoint_rejects_disabled_or_missing_interpretation() -> None:
    binding, corpus = interpreted_profile(), make_corpus()
    request = make_request(action="converse")
    intent = make_conversation_intent(
        policy(),
        corpus,
        binding,
        request,
        session_id="session",
        started_at=STARTED,
        now=NOW,
    ).model_copy(update={"run_id": "run"})
    workflow = reach_conversation_workflow(policy(), corpus, binding, started_at=STARTED, clock=lambda: NOW)
    initial = workflow.make_state(intent)
    assert workflow.manifest.checkpoint_schema == "reach-operator-conversation-v6"
    assert workflow.validate_state is not None
    workflow.validate_state(intent, initial)
    with pytest.raises(DocumentsRefused, match="conversation_checkpoint"):
        workflow.validate_state(intent, initial.model_copy(update={"answer": ANSWER}))
    valid = initial.model_copy(update={"request_goals": GOALS, "answer": ANSWER})
    workflow.validate_state(intent, valid)
    with pytest.raises(DocumentsRefused, match="conversation_checkpoint"):
        workflow.validate_state(intent, valid.model_copy(update={"request_goals": (GOALS[0], GOALS[0])}))
    disabled = binding.model_copy(update={"request_goals": False})
    disabled_intent = make_conversation_intent(
        policy(),
        corpus,
        disabled,
        request,
        session_id="session",
        started_at=STARTED,
        now=NOW,
    ).model_copy(update={"run_id": "run"})
    disabled_workflow = reach_conversation_workflow(policy(), corpus, disabled, started_at=STARTED, clock=lambda: NOW)
    assert disabled_workflow.validate_state is not None
    disabled_state = disabled_workflow.make_state(disabled_intent).model_copy(update={"request_goals": GOALS})
    with pytest.raises(DocumentsRefused, match="conversation_checkpoint"):
        disabled_workflow.validate_state(disabled_intent, disabled_state)


def accepted_coverage(*, runtime_claims: bool = False) -> str:
    value: dict[str, Any] = {
        "verdict": "accept",
        "issues": [],
        "coverage": [
            {"goal": 0, "status": "complete", "answer_quote": "Today supports bounded turns."},
            {"goal": 1, "status": "complete", "answer_quote": "Future work includes durable continuity."},
        ],
    }
    if runtime_claims:
        value["current_runtime_claims"] = []
    return canonical_json(value)


@pytest.mark.parametrize("research", [False, True])
@pytest.mark.asyncio
async def test_native_goals_precede_planning_and_reach_the_same_frozen_review_context(*, research: bool) -> None:
    binding = (
        research_profile(request_goals=True, checkback=True, max_input_chars=24_000)
        if research
        else interpreted_profile()
    )
    corpus = make_corpus("# Graph\n" + ANSWER)
    prompts: list[dict[str, Any]] = []
    traces: list[ReachTraceEvent] = []
    acquisitions: list[OperatorResearchRequest] = []

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        body = validate_generation_payload(binding, payload)
        assert "tools" not in body
        prompt = json.loads(body["messages"][-1]["content"])
        prompts.append(prompt)
        if prompt.get("phase") == "interpretation":
            assert len(prompts) == 1
            assert "research_sources" not in prompt
            assert "available_research_sources" not in prompt
            assert "candidate" not in prompt
            return completion(canonical_json({"goals": GOALS}))
        context = prompt["context"] if prompt.get("phase") == "checkback" else prompt
        assert context["request_goals"] == list(GOALS)
        if prompt.get("phase") == "checkback":
            return completion(accepted_coverage(runtime_claims=research))
        if prompt.get("research_phase") == "planning":
            return completion(
                canonical_json(
                    {
                        "kind": "research",
                        "text": "I will read the public Graph source.",
                        "focus": "Graph",
                        "source_ids": ["doc:docs/graph.md"],
                    }
                )
            )
        return completion(
            answer_json(text=ANSWER, citations=("doc:docs/graph.md",))
            if research
            else canonical_json({"kind": "answer", "text": ANSWER})
        )

    async def acquire(request: OperatorResearchRequest) -> OperatorResearchResponse:
        acquisitions.append(request)
        return relay_response(request, sources=())

    runtime = build_runtime(
        policy(),
        corpus,
        profile=binding,
        model_relay=relay,
        research_relay=acquire if research else None,
        started_at=STARTED,
        clock=lambda: NOW,
        trace=traces.append,
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted model relay
            result = await runtime.process(
                make_request(action="converse", question=QUESTION).model_copy(update={"request_id": str(uuid4())})
            )
        assert result.status == "conversation"
        assert ANSWER in result.text
        assert len(prompts) == (4 if research else 3)
        assert len(acquisitions) == int(research)
        interpreted = [event for event in traces if event.name == "interpretation"]
        assert [event.status for event in interpreted] == ["started", "ok"]
        assert interpreted[-1].goal_count == len(GOALS)
        assert interpreted[-1].objective_digest == request_goals_digest(GOALS)
        assert GOALS[0] not in b"".join(trace_bytes(event) for event in traces).decode()
        assert runtime.substrate.leases.active() == []
    finally:
        await runtime.aclose()


@pytest.mark.parametrize("failure", ["malformed", "cancelled"])
@pytest.mark.asyncio
async def test_bad_interpretation_never_forms_or_adopts_an_answer(failure: str) -> None:
    binding = interpreted_profile()
    prompts: list[dict[str, Any]] = []

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        prompt = json.loads(validate_generation_payload(binding, payload)["messages"][-1]["content"])
        prompts.append(prompt)
        assert prompt["phase"] == "interpretation"
        if failure == "cancelled":
            raise asyncio.CancelledError
        return completion('{"goals":[]}')

    runtime = build_runtime(
        policy(), make_corpus(), profile=binding, model_relay=relay, started_at=STARTED, clock=lambda: NOW
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted model relay
            if failure == "cancelled":
                with pytest.raises(asyncio.CancelledError):
                    await runtime.process(make_request(action="converse"))
            else:
                result = await runtime.process(make_request(action="converse"))
                assert result.status == "error"
                assert result.text == ""
        assert len(prompts) == 1
        assert runtime.substrate.leases.active() == []
        for session in await runtime.sessions.list_sessions():
            assert session.message_history == []
            assert all(turn.state == "failed" for turn in session.turns)
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_native_ignore_bypasses_request_decomposition() -> None:
    binding = interpreted_profile()
    prompts: list[dict[str, Any]] = []

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        prompt = json.loads(validate_generation_payload(binding, payload)["messages"][-1]["content"])
        prompts.append(prompt)
        assert prompt["conversation_phase"] == "addressing"
        return completion(
            canonical_json(
                {"kind": "ignore", "request_id": prompt["request_id"], "anchor_event_id": prompt["anchor"]["event_id"]}
            )
        )

    runtime = build_runtime(
        continuation_policy(), make_corpus(), profile=binding, model_relay=relay, started_at=STARTED, clock=lambda: NOW
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - isolated admitted model relay
            result = await runtime.process(continuation("followup"))
        assert result.status == "ignore"
        assert result.text == ""
        assert len(prompts) == 1
        assert runtime.substrate.leases.active() == []
    finally:
        await runtime.aclose()
