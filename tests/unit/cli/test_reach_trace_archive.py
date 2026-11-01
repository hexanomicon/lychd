"""Diagnostic custody, bounded capture and exact retained-correlation queries."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from scripts import reach_trace
from scripts import reach_trace_archive as traces

from lychd.compositions.reach.operator_trace import MAX_TRACE_BYTES, ReachTraceEvent, trace_bytes


def observation(**values: Any) -> ReachTraceEvent:
    return ReachTraceEvent.model_validate({"producer": "host", "name": "request_received", **values})


def test_restart_exact_links_and_unknown_terminal_state(tmp_path: Path) -> None:
    root = tmp_path / "traces"
    generation, request, run, call, other_request, other_run = (str(uuid4()) for _ in range(6))
    with traces.TraceArchive(root) as archive:
        for event in (
            observation(producer="edge", name="admission", generation=generation, platform_event_id="123"),
            observation(generation=generation, request_id=request, platform_event_id="123"),
            observation(producer="core", name="run_started", generation=generation, request_id=request, run_id=run),
            observation(name="model_call", generation=generation, request_id=request, call_id=call),
            observation(name="model_http", generation=generation, call_id=call, http_status=503, status="unavailable"),
            observation(producer="edge", name="delivery", generation=generation, platform_event_id="123"),
            observation(generation=generation, request_id=other_request, run_id=other_run, platform_event_id="123"),
        ):
            archive.emit(event)
        assert archive.flush()
    result = traces.query_archive(root, run_id=run)
    assert result["capture"] == "durable_best_effort"
    assert result["completeness"] == "not_established"
    assert {item["event"]["name"] for item in result["records"]} == {
        "admission",
        "request_received",
        "run_started",
        "model_call",
        "model_http",
        "delivery",
    }
    assert all(item["event"].get("run_id") != other_run for item in result["records"])
    assert len(traces.query_archive(root, platform_event_id="123")["records"]) == 7
    assert traces.query_archive(root, request_id=request, failures=True)["records"][0]["event"]["http_status"] == 503
    assert traces.query_archive(root, latest=True)["selection"] == {"run_id": other_run}
    with traces.TraceArchive(root) as reopened:
        assert reopened.flush()
    assert len(traces.query_archive(root, run_id=run)["records"]) == 6
    assert root.stat().st_mode & 0o777 == 0o700
    assert (root / traces.DATABASE_NAME).stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("unsafe", ["checkout", "symlink", "public", "hardlink", "fifo"])
def test_unsafe_paths_refuse_without_touching_evidence(tmp_path: Path, unsafe: str) -> None:
    root = tmp_path / "traces"
    if unsafe == "checkout":
        root.mkdir(mode=0o700)
        (root / ".git").mkdir()
    elif unsafe == "symlink":
        target = tmp_path / "target"
        target.mkdir(mode=0o700)
        root.symlink_to(target, target_is_directory=True)
    elif unsafe == "public":
        root.mkdir(mode=0o755)
    else:
        root.mkdir(mode=0o700)
        path = root / traces.DATABASE_NAME
        if unsafe == "hardlink":
            path.write_bytes(b"evidence")
            path.chmod(0o600)
            (tmp_path / "alias").hardlink_to(path)
        else:
            import os

            os.mkfifo(path, 0o600)
    with pytest.raises(traces.TraceArchiveError, match="trace_archive_unsafe_path"):
        traces.TraceArchive(root)


def test_corrupt_unknown_schema_and_changed_schema_never_reset(tmp_path: Path) -> None:
    root = tmp_path / "traces"
    with traces.TraceArchive(root) as archive:
        archive.emit(observation())
        assert archive.flush()
    database = root / traces.DATABASE_NAME
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version=99")
    unknown = database.read_bytes()
    with pytest.raises(traces.TraceArchiveError):
        traces.TraceArchive(root)
    assert database.read_bytes() == unknown
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version=1")
        connection.execute("CREATE TABLE unexpected (value TEXT)")
    with pytest.raises(traces.TraceArchiveError):
        traces.query_archive(root)
    database.write_bytes(b"synthetic corrupt evidence")
    corrupt = database.read_bytes()
    with pytest.raises(traces.TraceArchiveError):
        traces.TraceArchive(root)
    assert database.read_bytes() == corrupt


def test_retention_uses_receipt_clock_and_reports_suffix_bounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "traces"
    clock = datetime(2026, 1, 1, tzinfo=UTC)
    monkeypatch.setattr(traces, "_now", lambda: clock)
    monkeypatch.setattr(traces, "MAX_EVENTS", 3)
    with traces.TraceArchive(root) as archive:
        for index in range(5):
            archive.emit(observation(count=index, observed_at=clock + timedelta(days=200)))
        assert archive.flush()
        result = traces.query_archive(root, limit=2)
        assert result["truncated"]
        assert result["pruned_total"] == 2
        assert [row["event"]["count"] for row in result["records"]] == [3, 4]
        assert result["retained_bounds"]["first_ingest_id"] == 3
    clock += timedelta(days=31)
    with traces.TraceArchive(root) as reopened:
        assert reopened.flush()
    result = traces.query_archive(root)
    assert result["records"] == []
    assert result["pruned_total"] == 5


def test_queue_overflow_is_bounded_and_resumption_records_loss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "traces"
    archive = traces.TraceArchive(root)
    entered, release = threading.Event(), threading.Event()
    # Fault injection deliberately pauses the writer's private transaction boundary.
    original = archive._commit  # pyright: ignore[reportPrivateUsage]

    def blocked(connection: sqlite3.Connection, events: list[Any], *, force: bool = False) -> bool:
        if events and not entered.is_set():
            entered.set()
            assert release.wait(5)
        return original(connection, events, force=force)

    monkeypatch.setattr(archive, "_commit", blocked)
    try:
        archive.emit(observation())
        assert entered.wait(2)
        for _ in range(traces.QUEUE_CAPACITY + 50):
            archive.emit(observation())
        health = archive.health()
        assert health["queued"] == traces.QUEUE_CAPACITY
        assert health["dropped_total"] == 50
        assert not archive.close(timeout=0.01)
        release.set()
        assert archive.close()
    finally:
        release.set()
        archive.close()
    result = traces.query_archive(root, limit=1000)
    assert result["dropped_total"] == 50
    assert any(row["event"]["name"] == "capture_gap" for row in result["records"])


def test_capture_io_failure_does_not_escape_sink_and_recovers_as_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "traces"
    with traces.TraceArchive(root) as archive:
        # Fail precisely the private storage-attestation boundary, then restore it.
        attest = archive._attest  # pyright: ignore[reportPrivateUsage]

        def unavailable() -> None:
            message = "synthetic private error must never be serialized"
            raise OSError(message)

        monkeypatch.setattr(archive, "_attest", unavailable)
        archive.emit(observation())
        assert not archive.flush()
        assert capfd.readouterr().err == "reach_trace_capture_unavailable\n"
        assert not archive.flush()
        assert capfd.readouterr().err == ""
        monkeypatch.setattr(archive, "_attest", attest)
        archive.emit(observation(name="request_finished", status="ok"))
        assert archive.flush()
        assert capfd.readouterr().err == "reach_trace_capture_recovered\n"
    result = traces.query_archive(root)
    assert result["write_failures"] >= 1
    assert result["dropped_total"] >= 1
    assert any(row["event"]["name"] == "capture_gap" for row in result["records"])
    assert b"synthetic private error" not in (root / traces.DATABASE_NAME).read_bytes()


def test_strict_allowlist_canary_and_structural_sequence_are_distinct(
    tmp_path: Path,
) -> None:
    root = tmp_path / "traces"
    generation = str(uuid4())
    canary = "https://synthetic-private-canary.invalid/message-body"
    with traces.TraceArchive(root) as archive:
        archive.emit(observation().model_copy(update={"source_id": canary}))
        archive.emit(observation(generation=generation, trace_seq=1, native_seq=1))
        archive.emit(observation(generation=generation, trace_seq=2, native_seq=30))
        archive.emit(observation(generation=generation, trace_seq=5, native_seq=31))
        assert archive.flush()
    result = traces.query_archive(root)
    assert result["dropped_total"] == 1
    assert result["producer_gaps"] == 2
    assert canary not in json.dumps(result)
    assert canary.encode() not in (root / traces.DATABASE_NAME).read_bytes()


def test_queries_are_read_only_and_cli_errors_remain_fixed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "traces"
    clock = datetime.now(UTC)
    run = str(uuid4())
    with traces.TraceArchive(root) as archive:
        archive.emit(observation(run_id=run))
        assert archive.flush()
        assert traces.query_archive(root, since=clock - timedelta(seconds=10))["records"]
    before = (root / traces.DATABASE_NAME).read_bytes()
    assert reach_trace.main(["show", "--archive-dir", str(root), "--run-id", run]) == 0
    assert json.loads(capsys.readouterr().out)["selection"] == {"run_id": run}
    assert (root / traces.DATABASE_NAME).read_bytes() == before
    invalid_queries: tuple[dict[str, Any], ...] = (
        {"limit": 1001},
        {"run_id": "' OR 1=1 --"},
        {"since": "2026-01-01"},
    )
    for options in invalid_queries:
        with pytest.raises(traces.TraceArchiveError, match="trace_query_invalid"):
            traces.query_archive(root, **options)
    assert reach_trace.main(["recent", "--archive-dir", str(root), "--limit", "1001"]) == 1
    assert capsys.readouterr().err == "reach_trace_refused\n"


def test_byte_pressure_retires_old_observations_and_keeps_accepting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "traces"
    byte_limit = 512 * 1024
    monkeypatch.setattr(traces, "MAX_DATABASE_BYTES", byte_limit)
    identity = str(uuid4())
    event = observation(
        generation=identity,
        request_id=identity,
        run_id=identity,
        call_id=identity,
        occurrence_id=identity,
        step_id=identity,
        native_event_id=identity,
        source_id="doc:" + "a" * 200,
        node="a" * 128,
        platform="discord",
        platform_event_id="18446744073709551615",
        conversation_id="18446744073709551615",
        remote_id="18446744073709551615",
        context_round=2,
        operation="fetch",
        duration_ms=123456,
        http_status=200,
        chars=10000,
        bytes_count=10000,
        part=100,
        parts=100,
    )
    assert MAX_TRACE_BYTES // 2 < len(trace_bytes(event)) <= MAX_TRACE_BYTES
    with traces.TraceArchive(root) as archive:
        for batch in range(12):
            for item in range(32):
                archive.emit(event.model_copy(update={"event_id": str(uuid4()), "count": batch * 32 + item}))
            assert archive.flush()
            assert traces.query_archive(root, limit=1)["records"][0]["event"]["count"] == batch * 32 + 31
        result = traces.query_archive(root, limit=1)
        assert result["pruned_total"] > 0
        assert result["dropped_total"] == 0
        assert result["write_failures"] == 0
        assert (root / traces.DATABASE_NAME).stat().st_size <= byte_limit


def test_offline_queries_hide_expired_rows_without_reopening_or_mutating(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "traces"
    clock = datetime(2026, 1, 1, tzinfo=UTC)
    monkeypatch.setattr(traces, "_now", lambda: clock)
    run = str(uuid4())
    with traces.TraceArchive(root) as archive:
        archive.emit(observation(run_id=run))
        assert archive.flush()
    before = (root / traces.DATABASE_NAME).read_bytes()
    clock += timedelta(days=31)
    selectors: tuple[dict[str, Any], ...] = ({}, {"run_id": run}, {"latest": True}, {"runs": True})
    for options in selectors:
        result = traces.query_archive(root, **options)
        assert result["records"] == []
        assert result.get("runs", []) == []
        assert result["retained_bounds"]["count"] == 0
        assert result["physical_bounds"]["count"] == 1
        assert result["expired_retained_count"] == 1
    assert (root / traces.DATABASE_NAME).read_bytes() == before


def test_identity_closure_depth_marks_unresolved_links(tmp_path: Path) -> None:
    root = tmp_path / "traces"
    first_run, request_one, call_one, second_run, request_two, call_two, third_run = (str(uuid4()) for _ in range(7))
    with traces.TraceArchive(root) as archive:
        for links in (
            {"run_id": first_run, "request_id": request_one},
            {"request_id": request_one, "call_id": call_one},
            {"call_id": call_one, "run_id": second_run},
            {"run_id": second_run, "request_id": request_two},
            {"request_id": request_two, "call_id": call_two},
            {"call_id": call_two, "run_id": third_run},
        ):
            archive.emit(observation(**links))
        assert archive.flush()
    result = traces.query_archive(root, run_id=first_run)
    assert result["links_truncated"]
    assert not result["truncated"]
    assert len(result["records"]) < 6
    assert all(row["event"].get("run_id") != third_run for row in result["records"])


def test_missing_first_structural_observation_counts_as_a_gap(tmp_path: Path) -> None:
    root = tmp_path / "traces"
    with traces.TraceArchive(root) as archive:
        archive.emit(observation(generation=str(uuid4()), trace_seq=2, native_seq=70))
        assert archive.flush()
    assert traces.query_archive(root)["producer_gaps"] == 1
