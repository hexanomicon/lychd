"""Explicit export loading and content-free operator JSON-line framing failures."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from scripts.reach_worker import build_runtime, load_corpus, load_policy, main, serve

from lychd.compositions.reach.operator_wire import MAX_WIRE_BYTES
from tests.unit.compositions.test_reach_documents import NOW, STARTED, make_corpus, make_policy, make_request


def export_corpus(directory: Path) -> None:
    corpus = make_corpus()
    directory.mkdir()
    (directory / "manifest.json").write_text(corpus.manifest.model_dump_json())
    (directory / "000.md").write_text(corpus.texts[0])


def test_export_loader_verifies_regular_files_and_content(tmp_path: Path) -> None:
    export = tmp_path / "public"
    export_corpus(export)
    corpus = load_corpus(export)
    assert corpus.digest == make_corpus().digest
    (export / "000.md").write_text("Changed bytes")
    with pytest.raises(ValueError, match="corpus_content"):
        load_corpus(export)


def test_export_loader_refuses_symlinks_and_duplicate_manifest_keys(tmp_path: Path) -> None:
    export = tmp_path / "public"
    export_corpus(export)
    (export / "000.md").unlink()
    (tmp_path / "private.md").write_text("Never admitted")
    (export / "000.md").symlink_to(tmp_path / "private.md")
    with pytest.raises(OSError, match="Too many levels of symbolic links"):
        load_corpus(export)
    (export / "manifest.json").write_text('{"source_revision":"a","source_revision":"b"}')
    with pytest.raises(ValueError, match="duplicate_key"):
        load_corpus(export)


def test_explicit_policy_json_does_not_accept_extra_credentials(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"
    path.write_text(make_policy().model_dump_json())
    assert load_policy(path) == make_policy()
    path.write_text('{"token":"synthetic-secret"}')
    with pytest.raises(ValidationError):
        load_policy(path)


def test_startup_error_is_fixed_and_stdout_is_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--policy", str(tmp_path / "missing"), "--corpus-dir", str(tmp_path / "missing")]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "reach_worker_startup_refused\n"


@pytest.mark.asyncio
async def test_protocol_ready_result_and_duplicate_do_not_repeat_terminal_text() -> None:
    runtime = build_runtime(make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW)
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    request = make_request().model_dump_json().encode() + b"\n"
    reader.feed_data(request + request)
    reader.feed_eof()
    written: list[bytes] = []
    try:
        await serve(runtime, reader, written.append)
        ready, answer, duplicate = [json.loads(item) for item in written]
        assert ready["kind"] == "ready"
        assert ready["started_at"]
        assert answer["status"] == "docs"
        assert answer["run_id"]
        assert duplicate["reason"] == "duplicate"
        assert duplicate["text"] == ""
    finally:
        await runtime.aclose()


@pytest.mark.parametrize(
    "raw",
    [b'{"secret":"never-echo","secret":"other"}\n', b"x" * (MAX_WIRE_BYTES + 1) + b"\n", b"truncated-sensitive-input"],
    ids=["duplicate", "oversized", "truncated"],
)
@pytest.mark.asyncio
async def test_invalid_frames_return_only_fixed_codes(raw: bytes) -> None:
    runtime = build_runtime(make_policy(), make_corpus(), started_at=STARTED, clock=lambda: NOW)
    reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
    reader.feed_data(raw)
    reader.feed_eof()
    written: list[bytes] = []
    try:
        await serve(runtime, reader, written.append)
        assert len(written) == 2
        error = json.loads(written[1])
        assert error["status"] == "error"
        assert error["run_id"] is None
        assert error["text"] == ""
        assert b"sensitive" not in written[1]
        assert b"never-echo" not in written[1]
        assert await runtime.sessions.list_sessions() == []
    finally:
        await runtime.aclose()
