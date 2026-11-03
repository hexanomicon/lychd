"""Native continuation judgment precedes document selection and remains silent on doubt."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Literal
from uuid import uuid4

import pytest
from pydantic_ai.models import override_allow_model_requests
from scripts.reach_worker import build_runtime

from lychd.compositions.reach.operator_model_wire import canonical_json, validate_generation_payload
from lychd.compositions.reach.operator_trace import ReachTraceEvent, trace_bytes
from lychd.compositions.reach.operator_wire import ReachHistoryEntry, ReachWorkerRequest
from lychd.compositions.reach.schemas import ReachPolicy
from tests.unit.compositions.test_reach_conversation import completion, policy, profile
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_request


def continuation(kind: Literal["reply", "followup"]) -> ReachWorkerRequest:
    anchor = ReachHistoryEntry(
        subject_id="bot:one",
        event_id="prior:bot",
        conversation_id="channel:one",
        occurred_at=NOW - timedelta(seconds=3),
        text="First point: observe. Second point: continue.",
    )
    return make_request(
        action="converse",
        trigger=kind,
        mention_subject_ids=(),
        question="Explain the second point, please.",
        related_event_id=anchor.event_id,
        related_subject_id=anchor.subject_id,
        related_occurred_at=anchor.occurred_at,
    ).model_copy(
        update={
            "request_id": str(uuid4()),
            "reply_to_event_id": anchor.event_id if kind == "reply" else None,
            "reply_anchor": anchor if kind == "reply" else None,
            "continuation_anchor": anchor if kind == "followup" else None,
        }
    )


def continuation_policy() -> ReachPolicy:
    return policy().model_copy(
        update={
            "allowed_reply_conversation_ids": ("channel:one",),
            "allowed_adjacent_followup_conversation_ids": ("channel:one",),
        }
    )


@pytest.mark.parametrize("kind", ["reply", "followup"])
@pytest.mark.parametrize("judgment", ["ignore", "malformed", "foreign", "timeout"])
@pytest.mark.asyncio
async def test_ignored_or_invalid_candidate_never_selects_documents(
    kind: Literal["reply", "followup"],
    judgment: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_selection(*_args: object, **_kwargs: object) -> str:
        msg = "Unaddressed candidate reached source selection"
        raise AssertionError(msg)

    monkeypatch.setattr("lychd.compositions.reach.conversation_workflow.conversation_prompt", forbidden_selection)
    binding = profile().model_copy(update={"adaptive_context": True})
    calls: list[dict[str, object]] = []
    events: list[ReachTraceEvent] = []

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        prompt = json.loads(validate_generation_payload(binding, payload)["messages"][-1]["content"])
        calls.append(prompt)
        assert prompt["conversation_phase"] == "addressing"
        if judgment == "timeout":
            raise TimeoutError
        value = {"kind": "ignore", "request_id": prompt["request_id"], "anchor_event_id": prompt["anchor"]["event_id"]}
        if judgment == "foreign":
            value["anchor_event_id"] = "foreign:answer"
        return completion("{}" if judgment == "malformed" else canonical_json(value))

    runtime = build_runtime(
        continuation_policy(),
        make_corpus(),
        profile=binding,
        model_relay=relay,
        started_at=STARTED,
        clock=lambda: NOW,
        trace=events.append,
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - exact isolated model relay
            result = await runtime.process(continuation(kind))
        assert (result.status, result.text, result.reaction, result.gif_id) == ("ignore", "", None, None)
        assert len(calls) == 1
        assert runtime.substrate.leases.active() == []
        verdicts = [event for event in events if event.name == "addressing" and event.status != "started"]
        assert len(verdicts) == 1
        assert verdicts[0].verdict == "ignore"
        assert not any(event.name in {"source_read", "research_plan", "checkback"} for event in events)
        assert "Explain the second point" not in b"".join(trace_bytes(event) for event in events).decode()
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_only_addressed_candidate_can_continue_to_context_and_answer() -> None:
    binding = profile().model_copy(update={"adaptive_context": True})
    phases: list[str] = []

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        prompt = json.loads(validate_generation_payload(binding, payload)["messages"][-1]["content"])
        phase = prompt.get("conversation_phase", "answer")
        phases.append(phase)
        if phase == "addressing":
            return completion(
                canonical_json(
                    {
                        "kind": "addressed",
                        "request_id": prompt["request_id"],
                        "anchor_event_id": prompt["anchor"]["event_id"],
                    }
                )
            )
        return completion('{"kind":"answer","text":"The second point is to continue."}')

    runtime = build_runtime(
        continuation_policy(), make_corpus(), profile=binding, model_relay=relay, started_at=STARTED, clock=lambda: NOW
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - exact isolated model relay
            result = await runtime.process(continuation("reply"))
        assert result.status == "conversation"
        assert result.text == "The second point is to continue."
        assert phases == ["addressing", "answer"]
    finally:
        await runtime.aclose()


@pytest.mark.parametrize(("adaptive", "round_number"), [(False, 0), (True, 1)])
@pytest.mark.asyncio
async def test_native_candidates_cannot_bypass_adaptive_or_context_admission(
    *, adaptive: bool, round_number: int
) -> None:
    calls: list[str] = []

    async def relay(operation: str, _payload: str) -> str:
        calls.append(operation)
        msg = "Refused candidate requested a capability"
        raise AssertionError(msg)

    request = continuation("followup").model_copy(update={"context_round": round_number})
    runtime = build_runtime(
        continuation_policy(),
        make_corpus(),
        profile=profile().model_copy(update={"adaptive_context": adaptive}),
        model_relay=relay,
        started_at=STARTED,
        clock=lambda: NOW,
    )
    try:
        result = await runtime.process(request)
        assert result.status == "refused"
        assert result.run_id is None
        assert calls == []
        assert result.reason == ("context_round" if round_number else "conversation_addressing_unavailable")
    finally:
        await runtime.aclose()
