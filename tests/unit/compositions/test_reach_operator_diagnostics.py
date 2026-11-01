"""The disposable Core reports structure without copying private Run material."""

from __future__ import annotations

import asyncio
import fcntl
import os
import signal
from dataclasses import replace
from time import monotonic
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError
from scripts import reach_worker as worker

from lychd.compositions.reach.documents_workflow import DocumentsRefused, SearchDocuments
from lychd.compositions.reach.operator_diagnostics import (
    MAX_DIAGNOSTIC_BYTES,
    ReachRunDiagnostic,
    diagnostic_bytes,
    parse_diagnostic,
    write_diagnostic_line,
)
from lychd.domain.web.schemas import BridgeTurn
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_policy, make_request

CANARY = "private prompt /private/source provider-reply secret-token"


def test_full_unconsumed_diagnostic_pipe_cannot_block_and_restores_flags() -> None:
    read_fd, write_fd = os.pipe()
    original_flags = fcntl.fcntl(write_fd, fcntl.F_GETFL)
    previous_handler = signal.getsignal(signal.SIGALRM)

    def timed_out(_signum: int, _frame: Any) -> None:
        pytest.fail("Diagnostic sink blocked on a full pipe")

    try:
        os.set_blocking(write_fd, False)
        while True:
            try:
                os.write(write_fd, b"x" * 4096)
            except BlockingIOError:
                break
        fcntl.fcntl(write_fd, fcntl.F_SETFL, original_flags)
        signal.signal(signal.SIGALRM, timed_out)
        signal.setitimer(signal.ITIMER_REAL, 1)
        started = monotonic()
        write_diagnostic_line(diagnostic_bytes(diagnostic()), descriptor=write_fd)
        assert monotonic() - started < 1
        assert fcntl.fcntl(write_fd, fcntl.F_GETFL) == original_flags
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        os.close(read_fd)
        os.close(write_fd)


def diagnostic() -> ReachRunDiagnostic:
    return ReachRunDiagnostic(
        observed_at=NOW,
        generation=str(uuid4()),
        request_id=str(uuid4()),
        run_id=str(uuid4()),
        status="error",
        reason="run_failed",
        stage="execute",
        run_status="failed",
        evidence="flushed",
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"message": CANARY},
        {"failure_code": CANARY},
        {"failure_code": "model_unknown"},
        {"reason": "private_secret"},
        {"request_id": "/private/token-canary"},
        {"run_id": "not-a-uuid"},
        {"generation": "not-a-uuid"},
        {"stage": "private_stage"},
        {"capture": "durable"},
        {"schema_version": True},
    ],
)
def test_diagnostic_rejects_unadmitted_fields_and_identifiers(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        ReachRunDiagnostic.model_validate(diagnostic().model_dump() | changes)


@pytest.mark.parametrize("raw", [b'{"kind":1,"kind":2}', b'{"x":NaN}', b"\xff", b"x" * (MAX_DIAGNOSTIC_BYTES + 1)])
def test_diagnostic_parser_rejects_ambiguous_or_unbounded_input(raw: bytes) -> None:
    with pytest.raises((ValueError, UnicodeError)):
        parse_diagnostic(raw)


@pytest.mark.asyncio
async def test_success_is_observed_once_and_never_copies_result_content() -> None:
    records: list[ReachRunDiagnostic] = []
    runtime = worker.build_runtime(
        make_policy(),
        make_corpus(),
        started_at=STARTED,
        clock=lambda: NOW,
        diagnostic=records.append,
    )
    request = make_request().model_copy(update={"request_id": str(uuid4())})
    try:
        result = await runtime.process(request)
        assert result.status == "docs"
        assert len(records) == 1
        record = records[0]
        assert (record.generation, record.request_id, record.run_id) == (
            runtime.generation,
            request.request_id,
            result.run_id,
        )
        assert (record.status, record.run_status, record.stage, record.capture) == (
            "docs",
            "done",
            "result_validation",
            "process_local",
        )
        assert record.failed_node is None
        assert result.text not in diagnostic_bytes(record).decode()
        assert (await runtime.process(request)).reason == "duplicate"
        assert len(records) == 1
    finally:
        await runtime.aclose()


@pytest.mark.parametrize("safe", [False, True])
@pytest.mark.asyncio
async def test_real_graph_failure_reports_only_actual_failed_node_and_closed_code(
    monkeypatch: pytest.MonkeyPatch,
    *,
    safe: bool,
) -> None:
    async def fail(*_args: Any, **_kwargs: Any) -> None:
        if safe:
            message = "conversation_output"
            raise DocumentsRefused(message)
        raise ValueError(CANARY)

    records: list[ReachRunDiagnostic] = []
    runtime = worker.build_runtime(
        make_policy(),
        make_corpus(),
        started_at=STARTED,
        clock=lambda: NOW,
        diagnostic=records.append,
    )
    monkeypatch.setattr(SearchDocuments, "run", fail)
    try:
        result = await runtime.process(make_request())
        assert (result.status, result.reason, result.text) == ("error", "run_failed", "")
        assert len(records) == 1
        record = records[0]
        assert record.stage == "execute"
        assert record.run_status == "failed"
        assert record.failed_node is not None
        assert record.failed_node.node == "search"
        assert record.failure_code == ("conversation_output" if safe else None)
        raw = diagnostic_bytes(record).decode()
        assert CANARY not in raw
        assert make_request().event.question not in raw
        assert record.request_id is None
    finally:
        await runtime.aclose()


@pytest.mark.parametrize("failure", ["lookup", "validation", "binding", "missing"])
@pytest.mark.asyncio
async def test_later_result_failures_never_blame_the_last_settled_station(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    records: list[ReachRunDiagnostic] = []
    runtime = worker.build_runtime(
        make_policy(),
        make_corpus(),
        started_at=STARTED,
        clock=lambda: NOW,
        diagnostic=records.append,
    )
    original = runtime.sessions.settled_turn_for_run

    async def turn_for_run(run_id: str) -> BridgeTurn | None:
        turn = await original(run_id)
        assert turn is not None
        if failure == "missing":
            return None
        if failure == "lookup":
            raise ValueError(CANARY)
        if failure == "binding":
            result = worker.ReachWorkerResult.model_validate_json(turn.content)
            return replace(turn, content=result.model_copy(update={"request_id": "other"}).model_dump_json())
        return replace(turn, content=CANARY)

    monkeypatch.setattr(runtime.sessions, "settled_turn_for_run", turn_for_run)
    try:
        result = await runtime.process(make_request())
        assert result.reason == {"binding": "result_binding", "missing": "run_incomplete"}.get(failure, "run_failed")
        assert len(records) == 1
        record = records[0]
        assert record.stage == ("result_lookup" if failure in {"lookup", "missing"} else "result_validation")
        assert record.run_status == "done"
        assert record.failed_node is None
        assert CANARY not in diagnostic_bytes(record).decode()
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_timeout_remains_bounded_and_reports_execution_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    async def block(*_args: Any, **_kwargs: Any) -> None:
        await asyncio.Event().wait()

    records: list[ReachRunDiagnostic] = []
    runtime = worker.build_runtime(
        make_policy(),
        make_corpus(),
        started_at=STARTED,
        clock=lambda: NOW,
        diagnostic=records.append,
    )
    monkeypatch.setattr(SearchDocuments, "run", block)
    try:
        async with asyncio.timeout(1):
            result = await runtime.process(make_request(), timeout=0.01)
        assert result.reason == "run_timeout"
        assert len(records) == 1
        assert records[0].stage == "execute"
        assert records[0].failed_node is None
        assert runtime.queue.jobs == {}
    finally:
        await runtime.aclose()


@pytest.mark.parametrize("broken", ["flush", "projection", "sink"])
@pytest.mark.asyncio
async def test_diagnostic_failure_never_changes_settled_result(
    monkeypatch: pytest.MonkeyPatch,
    broken: str,
) -> None:
    records: list[ReachRunDiagnostic] = []
    runtime = worker.build_runtime(make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW)
    try:
        result = await runtime.process(make_request())
        assert result.run_id is not None
        runtime.diagnostic = records.append

        async def stalled(*_args: Any, **_kwargs: Any) -> Any:
            await asyncio.Event().wait()

        def fail(_record: ReachRunDiagnostic) -> None:
            raise ValueError(CANARY)

        monkeypatch.setattr(worker, "DIAGNOSTIC_TIMEOUT", 0.01)
        if broken == "flush":
            monkeypatch.setattr(runtime.substrate.bus, "wait_persisted", stalled)
        elif broken == "projection":
            monkeypatch.setattr(runtime.substrate.ledger, "latest_event", stalled)
        else:
            runtime.diagnostic = fail
        async with asyncio.timeout(1):
            await runtime.observe_result("/private/token", result.run_id, result, "result_validation", None)
        assert result.status == "docs"
        if broken in {"flush", "projection"}:
            assert len(records) == 1
            assert records[0].evidence == "unavailable"
            assert records[0].failed_node is None
        else:
            assert records == []
    finally:
        await runtime.aclose()
