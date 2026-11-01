"""Core observations preserve exact structural identities while excluding private material."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError
from scripts import reach_worker as worker

from lychd.compositions.reach.operator_model_wire import OperatorConversationProfile, OperatorModelResponse
from lychd.compositions.reach.operator_trace import ReachTraceEvent, TraceCorrelation, trace_bytes
from lychd.compositions.reach.research_wire import OperatorResearchRequest, OperatorResearchResponse, ResearchOptions
from lychd.domain.cortex.events import RunEventKind
from lychd.domain.cortex.execution_context import bind_occurrence, bind_step, reset_occurrence, reset_step
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_policy, make_request

CANARY = "private prompt /private/source provider-body secret-token"


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
