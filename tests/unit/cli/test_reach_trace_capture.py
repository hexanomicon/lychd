"""Explicit cross-process relations survive capture and never depend on prompt parsing."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

import httpx
import pytest
from scripts import reach_operator as operator
from scripts.reach_model_broker import OperatorModelBroker
from scripts.reach_trace_archive import TraceArchive, query_archive
from scripts.reach_trace_capture import TraceCapture

from lychd.compositions.reach.operator_model_wire import OperatorConversationProfile, OperatorModelRequest
from lychd.compositions.reach.operator_trace import ReachTraceEvent, TraceCorrelation, trace_bytes
from lychd.compositions.reach.operator_wire import ReachWorkerReady, ReachWorkerResult
from tests.unit.compositions.test_reach_documents import make_corpus, make_policy, make_request

CANARY = "private question /private/source secret-token provider body"


@pytest.mark.asyncio
async def test_exact_run_query_joins_model_http_and_delivery_after_restart(tmp_path: Path) -> None:
    generation, run_id, request_id, other_request = (str(uuid4()) for _ in range(4))
    event_id, other_event = "1566390031717761145", "1566390031717761146"
    policy, corpus = make_policy(), make_corpus()
    profile = OperatorConversationProfile(persona_name="Fixture", persona_instructions="Be concise.")
    archive = TraceArchive(tmp_path / "trace")
    capture = TraceCapture(archive.emit)
    capture.ready(
        ReachWorkerReady(
            generation=generation,
            started_at=make_request().event.occurred_at,
            policy_digest=policy.digest,
            corpus_digest=corpus.digest,
        )
    )
    request = make_request(event_id=event_id, question=CANARY).model_copy(update={"request_id": request_id})
    queued = make_request(event_id=other_event, question=CANARY).model_copy(update={"request_id": other_request})
    capture.request(request)
    capture.request(queued)
    archive.emit(
        ReachTraceEvent(
            producer="core",
            name="run_started",
            generation=generation,
            request_id=request_id,
            run_id=run_id,
            trace_seq=1,
        )
    )

    def fail(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text=CANARY, headers={"x-private": CANARY})

    broker = OperatorModelBroker(profile, transport=httpx.MockTransport(fail), trace=capture.host)
    call = OperatorModelRequest(
        call_id=str(uuid4()),
        binding_digest=profile.digest,
        operation="probe",
        payload_json="{}",
        correlation=TraceCorrelation(generation=generation, request_id=request_id, run_id=run_id),
    )
    result = await broker.handle(call)
    assert result.reason == "model_unavailable"
    capture.result(
        ReachWorkerResult(
            request_id=request_id,
            run_id=run_id,
            status="error",
            reason="run_failed",
            policy_digest=policy.digest,
            corpus_digest=corpus.digest,
        )
    )
    archive.emit(
        ReachTraceEvent(
            producer="edge",
            name="delivery",
            generation=generation,
            platform_event_id=event_id,
            status="unknown",
            part=0,
            parts=2,
            trace_seq=1,
        )
    )
    assert archive.close()
    page = query_archive(tmp_path / "trace", run_id=run_id)
    records = [row["event"] for row in page["records"]]
    assert any(row["name"] == "model_http" and row.get("http_status") == 403 for row in records)
    assert any(row["name"] == "delivery" and row["status"] == "unknown" for row in records)
    assert any(row.get("request_id") == request_id and row.get("platform_event_id") == event_id for row in records)
    assert not any(row.get("request_id") == other_request for row in records)
    assert CANARY not in json.dumps(page)
    assert page["capture"] == "durable_best_effort"


@pytest.mark.parametrize("role", ["core", "edge"])
@pytest.mark.asyncio
async def test_role_custody_rejects_forged_trace_producer(tmp_path: Path, role: Literal["core", "edge"]) -> None:
    archive = TraceArchive(tmp_path / "trace")
    capture = TraceCapture(archive.emit)
    reader = asyncio.StreamReader()
    admitted = ReachTraceEvent(producer=role, name="delivery", status="unknown")
    forged = ReachTraceEvent(producer="host", name="session_finished", status="ok")
    reader.feed_data(trace_bytes(admitted) + trace_bytes(forged))
    reader.feed_eof()
    await operator.diagnostics(reader, role=role, capture=capture)
    assert archive.close()
    page = query_archive(tmp_path / "trace")
    assert [row["event"]["event_id"] for row in page["records"] if row["event"]["producer"] == role] == [
        admitted.event_id
    ]
    assert forged.event_id not in {row["event"]["event_id"] for row in page["records"]}


def test_observer_cancellation_cannot_cancel_model_or_edge_work() -> None:
    from lychd.compositions.reach.operator_trace import TraceEmitter

    def cancelled(_event: ReachTraceEvent) -> None:
        raise asyncio.CancelledError

    emitter = TraceEmitter("host", cancelled)
    emitter.record("model_call", status="started")
    emitter.record("model_call", status="ok")
    assert emitter.sequence == 2


def test_trace_source_is_catalogue_identifier_and_current_member(tmp_path: Path) -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ReachTraceEvent(producer="core", name="source_read", source_id="https://private.example/secret")
    archive = TraceArchive(tmp_path / "trace")
    capture = TraceCapture(archive.emit, source_ids=frozenset({"web:approved"}))
    capture.child(ReachTraceEvent(producer="core", name="source_read", source_id="web:unapproved"), "core")
    capture.child(ReachTraceEvent(producer="core", name="source_read", source_id="web:approved"), "core")
    assert archive.close()
    result = query_archive(tmp_path / "trace")
    assert [row["event"].get("source_id") for row in result["records"] if row["event"]["name"] == "source_read"] == [
        "web:approved"
    ]
