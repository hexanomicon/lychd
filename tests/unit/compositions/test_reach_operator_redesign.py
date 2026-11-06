"""Operator ownership regressions through native execution and neutral context driving."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from pydantic_ai.models import override_allow_model_requests
from scripts.reach_worker import build_runtime

from lychd.compositions.reach import conversation_workflow
from lychd.compositions.reach.checkback import InputBudget, checkback_spec, model_input_cost, validate_checkback_budget
from lychd.compositions.reach.conversation_session import drive_context_turn
from lychd.compositions.reach.documents_workflow import DocumentsRefused
from lychd.compositions.reach.operator_limits import TurnDeadline
from lychd.compositions.reach.operator_model_wire import (
    MAX_MODEL_PAYLOAD_BYTES,
    OperatorConversationProfile,
    OperatorModelRequest,
    canonical_json,
    validate_generation_payload,
)
from lychd.compositions.reach.operator_wire import MAX_WIRE_BYTES, ReachWorkerResult, protocol_bytes, strict_json
from lychd.compositions.reach.research_wire import OperatorResearchRequest
from lychd.domain.cortex.runs import RunStatus
from tests.unit.compositions.test_reach_checkback import verdict
from tests.unit.compositions.test_reach_conversation import completion, policy, profile
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_request
from tests.unit.compositions.test_reach_portability import Pager, event, history
from tests.unit.compositions.test_reach_research import (
    UNVERIFIED_WEB_NOTICE,
    admitted_source,
    answer_json,
    plan_json,
    relay_response,
    research_profile,
    unavailable_source,
)


@pytest.mark.parametrize("research", [False, True])
@pytest.mark.parametrize("stage", ["checkback", "correction"])
@pytest.mark.asyncio
async def test_late_admission_failure_preserves_budget_through_native_settlement(
    monkeypatch: pytest.MonkeyPatch, stage: str, *, research: bool
) -> None:
    binding = (
        research_profile(checkback=True, max_input_chars=24_000)
        if research
        else profile().model_copy(update={"adaptive_context": True, "checkback": True, "max_input_chars": 24_000})
    )
    validate = conversation_workflow.validate_checkback_budget
    generated: list[dict[str, Any]] = []

    def admit(selected: Any, spec: Any, prompt: str, *, phase: Any) -> None:
        validate(selected, spec, prompt, phase=phase)
        if json.loads(prompt).get("phase") == stage:
            msg = "conversation_budget"
            raise DocumentsRefused(msg)

    monkeypatch.setattr(conversation_workflow, "validate_checkback_budget", admit)

    async def relay(operation: str, payload: str) -> str:
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        prompt = json.loads(validate_generation_payload(binding, payload)["messages"][-1]["content"])
        generated.append(prompt)
        if prompt.get("phase") == "checkback":
            return completion(verdict("revise", claims=() if research else None))
        if prompt.get("research_phase") == "planning":
            return completion(plan_json())
        return completion(answer_json() if research else canonical_json({"kind": "answer", "text": "Original answer."}))

    async def acquire(request: OperatorResearchRequest) -> Any:
        return relay_response(request, sources=(admitted_source(),))

    runtime = build_runtime(
        policy(),
        make_corpus(),
        profile=binding,
        model_relay=relay,
        research_relay=acquire if research else None,
        started_at=STARTED,
        clock=lambda: NOW,
    )
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - explicit third-party model permission
            result = await runtime.process(
                make_request(action="converse").model_copy(update={"request_id": str(uuid4())})
            )
        assert (result.status, result.reason, result.text) == ("error", "budget", "")
        assert len(generated) == (2 if research else 1) + (stage == "correction")
        assert runtime.substrate.leases.active() == []
        assert result.run_id is not None
        failed = await runtime.sessions.settled_turn_for_run(result.run_id)
        assert failed is not None
        assert failed.state == "failed"
        assert "Original answer." not in failed.content
    finally:
        await runtime.aclose()


@pytest.mark.parametrize("local", [False, True])
@pytest.mark.asyncio
async def test_all_web_failed_settles_host_notice_without_synthesis_or_review(*, local: bool) -> None:
    binding = research_profile(checkback=True, max_input_chars=24_000)
    generated = acquisitions = 0

    async def relay(operation: str, payload: str) -> str:
        nonlocal generated
        if operation == "probe":
            return canonical_json({"healthy": True, "model_ids": [binding.model_id]})
        generated += 1
        assert generated == 1, "Host abstention must not depend on another model generation"
        validate_generation_payload(binding, payload)
        return completion(plan_json(("web:blocked", "doc:docs/graph.md") if local else ("web:blocked",)))

    async def acquire(request: OperatorResearchRequest) -> Any:
        nonlocal acquisitions
        acquisitions += 1
        return relay_response(request, sources=(unavailable_source(),))

    runtime = build_runtime(
        policy(),
        make_corpus(),
        profile=binding,
        model_relay=relay,
        research_relay=acquire,
        started_at=STARTED,
        clock=lambda: NOW,
    )
    request = make_request(action="converse").model_copy(update={"request_id": str(uuid4())})
    try:
        with override_allow_model_requests(True):  # noqa: FBT003 - explicit third-party model permission
            result = await runtime.process(request)
            duplicate = await runtime.process(request)
        assert result.status == "clarify"
        assert result.text == UNVERIFIED_WEB_NOTICE + "\n\nUnavailable source: Unavailable reference (fetch_protocol)."
        assert (generated, acquisitions) == (1, 1)
        assert duplicate.reason == "duplicate"
        assert runtime.substrate.leases.active() == []
        assert result.run_id is not None
        run = await runtime.substrate.ledger.get(result.run_id)
        assert run is not None
        assert run.status is RunStatus.DONE
        assert await runtime.sessions.settled_turn_for_run(result.run_id) is not None
    finally:
        await runtime.aclose()


def native_result(status: str) -> ReachWorkerResult:
    return ReachWorkerResult.model_validate(
        {
            "request_id": "request",
            "run_id": "run",
            "status": status,
            "text": "Which repository revision should I compare?",
            "policy_digest": "a" * 64,
            "corpus_digest": "b" * 64,
        }
    )


@pytest.mark.parametrize("deferred", [False, True])
@pytest.mark.asyncio
async def test_later_history_denial_keeps_native_result_and_typed_cause(*, deferred: bool) -> None:
    observed = event()
    if deferred:
        observed = observed.model_copy(update={"trigger": "reply", "related_event_id": "anchor"})
    recent = history("recent", 3)
    pages = [((), "permission_denied")] if deferred else [((recent,), "more"), ((recent,), "permission_denied")]
    pager = Pager(cast("Any", pages))
    native = native_result("need_context")
    worker = Mock(request=AsyncMock(return_value=native))
    outcome = await drive_context_turn(worker, observed, pager)
    assert outcome.result is native
    assert outcome.stop == "permission_denied"
    assert native.status == "need_context"
    worker.request.assert_awaited_once()
    assert pager.reads == (1 if deferred else 2)


@pytest.mark.asyncio
async def test_unrelated_native_clarification_survives_first_page_denial() -> None:
    native = native_result("clarify")
    outcome = await drive_context_turn(
        Mock(request=AsyncMock(return_value=native)), event(), Pager([((), "permission_denied")])
    )
    assert outcome.result is native
    assert outcome.stop is None
    assert outcome.result.text == "Which repository revision should I compare?"


def test_captured_deadline_cannot_be_extended_by_a_wall_clock_change() -> None:
    clock = [100.0]
    deadline = TurnDeadline.start(NOW, 10, 960, now=NOW + timedelta(seconds=2), clock=lambda: clock[0])
    assert deadline.remaining() == 8
    clock[0] += 3
    assert deadline.remaining(900) == 5
    clock[0] += 5
    with pytest.raises(TimeoutError):
        deadline.check()


def test_actual_wire_limits_bound_canonical_model_payload_and_escaped_frame() -> None:
    empty = canonical_json({"body": ""})
    payload = canonical_json({"body": "x" * (MAX_MODEL_PAYLOAD_BYTES - len(empty.encode()))})
    fields = {"call_id": str(uuid4()), "binding_digest": "a" * 64, "operation": "generate"}
    request = OperatorModelRequest.model_validate({**fields, "payload_json": payload})
    assert len(request.payload_json.encode()) == MAX_MODEL_PAYLOAD_BYTES
    with pytest.raises(ValidationError, match="model_payload"):
        OperatorModelRequest.model_validate({**fields, "payload_json": payload[:-2] + 'x"}'})
    escaped = canonical_json({"body": "\\" * ((MAX_MODEL_PAYLOAD_BYTES - len(empty.encode())) // 2)})
    request = OperatorModelRequest.model_validate({**fields, "payload_json": escaped})
    with pytest.raises(ValueError, match="output_limit"):
        protocol_bytes(cast("Any", request))
    raw = canonical_json({"body": "x" * (MAX_WIRE_BYTES - len(empty.encode()))}).encode()
    assert strict_json(raw)["body"]
    with pytest.raises(ValueError, match="input_limit"):
        strict_json(raw + b" ")


def test_largest_admitted_profile_still_checks_actual_encoded_budget() -> None:
    binding = OperatorConversationProfile.model_validate(
        {
            **profile().model_dump(),
            "max_context": 262_144,
            "max_input_chars": 210_000,
            "adaptive_context": True,
            "checkback": True,
        }
    )
    spec = checkback_spec(binding)
    for unit in ("漢", "𐍈", "\\"):
        prompt = unit * 190_000
        assert (
            max(model_input_cost(binding, spec.instructions, prompt, phase="checkback").excess(binding, InputBudget()))
            <= 0
        )
        validate_checkback_budget(binding, spec, prompt, phase="checkback")
    prompt = "\x00" * 180_000
    cost = model_input_cost(binding, spec.instructions, prompt, phase="checkback")
    assert cost.input_chars < binding.max_input_chars
    assert cost.payload_bytes > MAX_MODEL_PAYLOAD_BYTES
    with pytest.raises(DocumentsRefused, match="conversation_budget"):
        validate_checkback_budget(binding, spec, prompt, phase="checkback")
