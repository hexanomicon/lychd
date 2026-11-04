"""Core observations preserve exact structural identities while excluding private material."""

from __future__ import annotations

import asyncio
import json
from hashlib import sha256
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError
from scripts import reach_worker as worker

from lychd.compositions.reach.documents_workflow import DocumentsRefused
from lychd.compositions.reach.operator_model_wire import OperatorConversationProfile, OperatorModelResponse
from lychd.compositions.reach.operator_trace import ReachTraceEvent, TraceCorrelation, trace_bytes
from lychd.compositions.reach.research_wire import OperatorResearchRequest, OperatorResearchResponse, ResearchOptions
from lychd.domain.cortex.events import RunEventKind
from lychd.domain.cortex.execution_context import bind_occurrence, bind_step, reset_occurrence, reset_step
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_policy, make_request

CANARY = "private prompt /private/source provider-body secret-token"


def test_source_trace_retains_exact_read_range_and_digests_without_body() -> None:
    source = "opening material\n" + CANARY
    event = ReachTraceEvent(
        producer="core",
        name="source_read",
        status="ok",
        source_id="doc:docs/roadmap.md",
        chars=len(source),
        excerpt_start=17,
        excerpt_chars=len(CANARY),
        source_digest=sha256(source.encode()).hexdigest(),
        text_digest=sha256(CANARY.encode()).hexdigest(),
        truncated=True,
    )
    retained = ReachTraceEvent.model_validate_json(trace_bytes(event))
    assert retained.excerpt_start == 17
    assert retained.excerpt_chars == len(CANARY)
    assert retained.text_digest == sha256(CANARY.encode()).hexdigest()
    assert CANARY.encode() not in trace_bytes(event)
    with pytest.raises(ValidationError):
        ReachTraceEvent(producer="core", name="source_read", text_digest=CANARY)
    with pytest.raises(ValidationError):
        ReachTraceEvent(producer="core", name="source_read", excerpt_chars=16_001)


@pytest.mark.asyncio
async def test_core_trace_projects_actual_native_identity_and_never_result_or_log_bodies() -> None:
    records: list[ReachTraceEvent] = []
    runtime = worker.build_runtime(
        make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW, trace=records.append
    )
    request = make_request().model_copy(update={"request_id": str(uuid4())})
    try:
        result = await runtime.process(request)
        assert result.status == "docs"
        assert result.run_id is not None
        assert [event.trace_seq for event in records] == list(range(1, len(records) + 1))
        started = next(event for event in records if event.name == "run_started")
        finished = next(event for event in records if event.name == "run_finished")
        assert (started.request_id, started.run_id, started.generation) == (
            request.request_id,
            result.run_id,
            runtime.generation,
        )
        run = await runtime.substrate.ledger.get(result.run_id)
        assert run is not None
        assert (started.pattern_id, started.pattern_revision) == (
            run.pattern_manifest["key"],
            run.pattern_manifest["revision"],
        )
        assert (finished.request_id, finished.run_id, finished.status) == (request.request_id, result.run_id, "docs")
        entered = next(event for event in records if event.name == "native_node" and event.status == "entered")
        assert started.trace_seq < entered.trace_seq < finished.trace_seq
        retained = await runtime.substrate.ledger.list_events(result.run_id, limit=1000)
        expected = [
            event
            for event in retained
            if event.kind
            in {
                RunEventKind.STATUS,
                RunEventKind.NODE,
                RunEventKind.DISPATCH,
                RunEventKind.TRANSITION,
                RunEventKind.DONE,
            }
        ]
        native = [event for event in records if event.native_event_id is not None]
        assert [(event.native_event_id, event.native_seq, event.observed_at) for event in native] == [
            (event.event_id, event.seq, event.ts) for event in expected
        ]
        assert entered.occurrence_id is not None
        assert entered.request_id == request.request_id
        before = len(records)
        runtime.observe_native(retained[0].model_copy(update={"kind": RunEventKind.LOG, "data": CANARY}))
        runtime.observe_native(retained[0].model_copy(update={"kind": RunEventKind.TOKEN, "data": CANARY}))
        assert len(records) == before
        captured = b"".join(trace_bytes(event) for event in records).decode()
        assert CANARY not in captured
        assert result.text not in captured
        assert request.event.question not in captured
    finally:
        await runtime.aclose()


def _failure(kind: str) -> Exception:
    if kind == "validation_error":
        try:
            TraceCorrelation.model_validate({"private_input": CANARY})
        except ValidationError as error:
            return error
    if kind == "invalid_json":
        return json.JSONDecodeError("private diagnostic", CANARY, 0)
    return RuntimeError(CANARY)


@pytest.mark.parametrize("code", ["validation_error", "invalid_json", "runtime_error"])
@pytest.mark.asyncio
async def test_run_failure_trace_classifies_types_without_rendering_errors(
    monkeypatch: pytest.MonkeyPatch, code: str
) -> None:
    records: list[ReachTraceEvent] = []

    async def fail(*_args: Any, **_kwargs: Any) -> None:
        raise _failure(code)

    monkeypatch.setattr(worker, "perform_run", fail)
    runtime = worker.build_runtime(
        make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW, trace=records.append
    )
    try:
        result = await runtime.process(make_request().model_copy(update={"request_id": str(uuid4())}))
        assert result.reason == "run_failed"
        terminal = next(event for event in records if event.name == "run_finished")
        assert terminal.code == code
        assert CANARY not in b"".join(trace_bytes(event) for event in records).decode()
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_failed_capture_consumes_sequence_without_changing_result() -> None:
    records: list[ReachTraceEvent] = []
    attempted = 0

    def capture(event: ReachTraceEvent) -> None:
        nonlocal attempted
        attempted += 1
        if attempted == 2:
            raise asyncio.CancelledError
        records.append(event)

    runtime = worker.build_runtime(make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW, trace=capture)
    try:
        result = await runtime.process(make_request().model_copy(update={"request_id": str(uuid4())}))
        assert result.status == "docs"
        assert [event.trace_seq for event in records][:2] == [1, 3]
        assert records[-1].name == "run_finished"
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_model_and_research_wire_inherit_exact_native_task_context_and_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding = OperatorConversationProfile(
        persona_name="Example",
        persona_instructions="Public evidence only.",
        adaptive_context=True,
        research=ResearchOptions(enabled=True),
    )
    reader = asyncio.StreamReader()
    frames: list[dict[str, Any]] = []
    request = make_request().model_copy(update={"request_id": str(uuid4())})
    occurrence_id, step_id = str(uuid4()), str(uuid4())

    def write(raw: bytes) -> None:
        frame: dict[str, Any] = json.loads(raw)
        frames.append(frame)
        response = (
            OperatorModelResponse(call_id=frame["call_id"], binding_digest=binding.digest, status="ok")
            if frame["kind"] == "model_request"
            else OperatorResearchResponse(
                call_id=frame["call_id"], request_id=frame["request_id"], binding_digest=binding.digest, status="ok"
            )
        )
        reader.feed_data(response.model_dump_json().encode() + b"\n")

    relay = worker.PipeModelRelay(binding, reader, write)

    async def execute(*_args: Any, **_kwargs: Any) -> None:
        occurrence_token, step_token = bind_occurrence(occurrence_id), bind_step(step_id)
        try:
            await relay("probe", "{}")
            await relay.research(
                OperatorResearchRequest(
                    call_id=str(uuid4()),
                    request_id=request.request_id,
                    binding_digest=binding.digest,
                    event=request.event,
                    plan="Read selected public evidence.",
                )
            )
        finally:
            reset_step(step_token)
            reset_occurrence(occurrence_token)

    monkeypatch.setattr(worker, "perform_run", execute)
    runtime = worker.build_runtime(make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW)
    try:
        result = await runtime.process(request)
        assert result.run_id is not None
        assert len(frames) == 2
        expected = TraceCorrelation(
            generation=runtime.generation,
            request_id=request.request_id,
            run_id=result.run_id,
            occurrence_id=occurrence_id,
            step_id=step_id,
        ).model_dump(mode="json")
        assert [frame["correlation"] for frame in frames] == [expected, expected]
        await relay("probe", "{}")
        assert frames[-1]["correlation"] is None
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_caller_cancellation_stays_cancelled_and_has_no_invented_run_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records: list[ReachTraceEvent] = []
    entered = asyncio.Event()

    async def wait(*_args: Any, **_kwargs: Any) -> None:
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(worker, "perform_run", wait)
    runtime = worker.build_runtime(
        make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW, trace=records.append
    )
    task = asyncio.create_task(runtime.process(make_request().model_copy(update={"request_id": str(uuid4())})))
    try:
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        terminal = records[-1]
        assert terminal.name == "run_finished"
        assert terminal.status == "cancelled"
        assert terminal.code is None
    finally:
        await runtime.aclose()


def test_adoption_control_and_reference_metadata_are_closed_and_do_not_contain_model_text() -> None:
    event = ReachTraceEvent(
        producer="core",
        name="checkback_control",
        status="ok",
        attempt=0,
        request_digest="a" * 64,
        evidence_digest="b" * 64,
        candidate_digest="c" * 64,
        guard_rule="unchanged_explanation",
        guard_version="unchanged-explanation-v1",
        guard_status="unchanged_requested_transformation",
        effective_verdict="revise",
    )
    observed = ReachTraceEvent.model_validate_json(trace_bytes(event))
    assert observed.verdict is None
    assert observed.issue_codes is None
    assert observed.goal_coverage is None
    assert observed.effective_verdict == "revise"
    with pytest.raises(ValidationError):
        ReachTraceEvent.model_validate({"producer": "core", "name": "checkback_control", "guard_status": CANARY})
    with pytest.raises(ValidationError):
        ReachTraceEvent.model_validate({"producer": "core", "name": "reference_hints", "reference_version": CANARY})
    with pytest.raises(ValidationError):
        ReachTraceEvent(producer="core", name="reference_hints", reference_count=4)


@pytest.mark.parametrize("version", ["anchor-order-v1", "anchor-order-v2"])
def test_reference_trace_keeps_old_and_new_parser_dialects(version: str) -> None:
    event = ReachTraceEvent.model_validate(
        {"producer": "core", "name": "reference_hints", "reference_version": version}
    )
    assert ReachTraceEvent.model_validate_json(trace_bytes(event)).reference_version == version


def test_old_trace_claim_metadata_is_unrecorded_and_new_empty_observation_is_recorded() -> None:
    old = ReachTraceEvent(producer="core", name="checkback", status="ok", verdict="accept")
    assert old.runtime_claim_count is None
    assert old.runtime_claim_digest is None
    new = old.model_copy(update={"runtime_claim_count": 0, "runtime_claim_digest": "a" * 64})
    observed = ReachTraceEvent.model_validate_json(trace_bytes(new))
    assert observed.runtime_claim_count == 0
    assert observed.runtime_claim_digest == "a" * 64
    assert observed.verdict == "accept"
    with pytest.raises(ValidationError):
        ReachTraceEvent.model_validate({"producer": "core", "name": "checkback", "runtime_claim_count": 5})


@pytest.mark.parametrize(
    ("rule", "version", "status"),
    [
        ("unchanged_explanation", "unchanged-explanation-v1", "unchanged_requested_transformation"),
        ("runtime_evidence_authority", "runtime-evidence-authority-v1", "current_runtime_claim_without_observation"),
        ("misbound_reference_clarification", "misbound-reference-clarification-v1", "unrequested_target_clarification"),
    ],
)
def test_adoption_trace_reads_separate_guard_dialects_without_claim_clauses(
    rule: str, version: str, status: str
) -> None:
    event = ReachTraceEvent.model_validate(
        {
            "producer": "core",
            "name": "checkback_control",
            "status": "ok",
            "guard_rule": rule,
            "guard_version": version,
            "guard_status": status,
            "effective_verdict": "revise",
            "runtime_claim_count": 2,
            "runtime_claim_digest": "a" * 64,
        }
    )
    assert ReachTraceEvent.model_validate_json(trace_bytes(event)).guard_rule == rule
    assert event.verdict is None
    assert event.issue_codes is None
    assert "current_runtime_claims" not in event.model_dump()


class BudgetSubclass(DocumentsRefused):
    pass


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (DocumentsRefused("conversation_budget"), "budget"),
        (ValueError("conversation_budget"), "value_error"),
        (BudgetSubclass("conversation_budget"), "value_error"),
        (DocumentsRefused(CANARY), "value_error"),
        (DocumentsRefused("conversation_budget", CANARY), "value_error"),
        (DocumentsRefused(None), "value_error"),
    ],
)
def test_only_exact_core_budget_refusal_gets_budget_trace(error: Exception, expected: str) -> None:
    assert worker._trace_failure_code(error) == expected  # pyright: ignore[reportPrivateUsage] - closed Core diagnostic boundary


@pytest.mark.asyncio
async def test_trusted_budget_failure_records_no_exception_body(monkeypatch: pytest.MonkeyPatch) -> None:
    records: list[ReachTraceEvent] = []

    async def fail(*_args: Any, **_kwargs: Any) -> None:
        message = "conversation_budget"
        raise DocumentsRefused(message)

    monkeypatch.setattr(worker, "perform_run", fail)
    runtime = worker.build_runtime(
        make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW, trace=records.append
    )
    try:
        result = await runtime.process(make_request().model_copy(update={"request_id": str(uuid4())}))
        assert result.reason == "run_failed"
        terminal = next(event for event in records if event.name == "run_finished")
        assert terminal.code == "budget"
        assert "conversation_budget" not in b"".join(trace_bytes(event) for event in records).decode()
    finally:
        await runtime.aclose()


@pytest.mark.parametrize("field", ["research_plan_text_chars", "research_plan_focus_chars"])
def test_plan_validation_counts_are_optional_bounded_and_body_free(field: str) -> None:
    event = ReachTraceEvent.model_validate(
        {"producer": "core", "name": "research_plan", "status": "failed", "operation": "validation", field: 501}
    )
    assert getattr(ReachTraceEvent.model_validate_json(trace_bytes(event)), field) == 501
    assert len(trace_bytes(event)) <= 2048
    for invalid in (-1, 49_153, CANARY):
        with pytest.raises(ValidationError):
            ReachTraceEvent.model_validate({"producer": "core", "name": "research_plan", field: invalid})
    assert field not in ReachTraceEvent(producer="core", name="research_plan").model_dump(exclude_none=True)


def test_provider_observation_accepts_only_finite_categories() -> None:
    for field in ("completion_finish_reason", "content_state"):
        with pytest.raises(ValidationError):
            ReachTraceEvent.model_validate({"producer": "host", "name": "model_call", field: CANARY})
