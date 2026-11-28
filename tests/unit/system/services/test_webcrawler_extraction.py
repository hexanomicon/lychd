"""Protocol and supervision substitutes; these tests do not qualify containment."""

# pyright: reportPrivateUsage=false
from __future__ import annotations

import asyncio
import io
import json
import signal
from hashlib import sha256
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest

from lychd.domain.scout.extraction import ExtractionCode, ExtractionError, ExtractionMedia
from lychd.system import scout_worker
from lychd.system.services import scout_extraction as extraction


def test_maintained_qualification_matches_current_source() -> None:
    """A historical host pass cannot silently qualify changed implementation bytes."""
    root = Path(__file__).resolve().parents[4]
    receipt = json.loads((root / "tests/fixtures/scout/linux-extraction-runtime.json").read_text())
    assert receipt["status"] == "passed"
    assert receipt["profile"] == "scout-static-extract@1"
    assert set(receipt["source_sha256"]) == {
        "src/lychd/system/scout_worker.py",
        "src/lychd/system/services/scout_extraction.py",
        "src/lychd/domain/scout/extraction.py",
        "tests/integration/test_scout_extraction_runtime.py",
    }
    for path, digest in receipt["source_sha256"].items():
        assert sha256((root / path).read_bytes()).hexdigest() == digest, path


@pytest.fixture
def runtime(tmp_path: Path) -> extraction.ScoutExtractionRuntime:
    bwrap = tmp_path / "bwrap"
    bwrap.touch()
    root = tmp_path / "python"
    (root / "bin").mkdir(parents=True)
    (root / "bin/python3").touch()
    (root / "lib").mkdir()
    libraries = tuple(tmp_path / name for name in sorted(extraction._LIBRARY_NAMES))
    for library in libraries:
        library.touch()
    return extraction.ScoutExtractionRuntime(bwrap, root, libraries)


def _record(body: bytes = b"ordinary text", media_type: str = "text/plain") -> tuple[bytes, int]:
    header = json.dumps({"media_type": media_type, "body_bytes": len(body)}).encode() + b"\n"
    output = io.BytesIO()
    code = scout_worker.run(io.BytesIO(header + body), output)
    return output.getvalue(), code


def _process(record: bytes, exit_code: int = 0, stderr: bytes = b"") -> Mock:
    stdout_reader, stderr_reader = asyncio.StreamReader(), asyncio.StreamReader()
    stdout_reader.feed_data(record)
    stdout_reader.feed_eof()
    stderr_reader.feed_data(stderr)
    stderr_reader.feed_eof()
    writer = Mock(spec=asyncio.StreamWriter)
    writer.drain = AsyncMock()
    process = Mock(spec=asyncio.subprocess.Process)
    process.pid = 987654
    process.returncode = exit_code
    process.stdin, process.stdout, process.stderr = writer, stdout_reader, stderr_reader
    process.wait = AsyncMock(return_value=exit_code)
    return process


def test_command_has_mandatory_boundaries_and_only_reviewed_readonly_roots(
    runtime: extraction.ScoutExtractionRuntime,
) -> None:
    command = extraction._command(runtime)
    for flag in (
        "--unshare-user",
        "--unshare-pid",
        "--unshare-net",
        "--unshare-ipc",
        "--unshare-uts",
        "--disable-userns",
        "--assert-userns-disabled",
        "--clearenv",
        "--die-with-parent",
        "--new-session",
    ):
        assert flag in command
    assert command[-10:] == (
        "--chdir",
        "/",
        "--remount-ro",
        "/",
        "--",
        "/runtime/bin/python3",
        "-I",
        "-S",
        "-B",
        "/worker.py",
    )
    assert command.count("--ro-bind") == 10
    assert not {"--bind", "--proc", "--dev", "--tmpfs", "--share-net", "--as-pid-1"} & set(command)
    assert not any("-try" in argument for argument in command)


def test_missing_containment_refuses_without_launch(runtime: extraction.ScoutExtractionRuntime) -> None:
    runtime.bwrap.unlink()
    with pytest.raises(ExtractionError) as error:
        extraction._command(runtime)
    assert error.value.code is ExtractionCode.CONTAINMENT


@pytest.mark.asyncio
async def test_preflight_refusal_records_no_child(
    runtime: extraction.ScoutExtractionRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime.bwrap.unlink()
    launch = AsyncMock()
    monkeypatch.setattr(extraction.asyncio, "create_subprocess_exec", launch)
    lifecycle = extraction.ExtractionLifecycle()
    with pytest.raises(ExtractionError) as error:
        await extraction.extract_static_text(b"", media_type="text/plain", runtime=runtime, lifecycle=lifecycle)
    assert error.value.code is ExtractionCode.CONTAINMENT
    assert lifecycle.child == "not_started"
    launch.assert_not_called()


@pytest.mark.parametrize("media_type", ["text/plain", "text/html"])
def test_real_worker_record_becomes_attributed_data(media_type: ExtractionMedia) -> None:
    body = b"<p>source text</p>" if media_type == "text/html" else b"source text"
    record, exit_code = _record(body, media_type)
    result = extraction._result(record, body, media_type, exit_code)
    assert result.text == "source text"
    assert result.source_digest == sha256(body).hexdigest()
    assert result.record_digest == sha256(record).hexdigest()
    assert result.text_digest == sha256(result.text.encode()).hexdigest()
    assert result.text not in repr(result)
    assert result.source_digest not in repr(result)


def test_worker_refusal_is_closed_and_keeps_no_foreign_message() -> None:
    record, exit_code = _record(b"secret\0payload")
    with pytest.raises(ExtractionError) as error:
        extraction._result(record, b"secret\0payload", "text/plain", exit_code)
    assert error.value.code is ExtractionCode.WORKER
    assert error.value.worker_code == "control"
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    "record",
    [
        b"{}",
        b"{}\n{}\n",
        b"[]\n",
        b'{"status":"ok","status":"ok"}\n',
        b'{"status":"refused","code":"foreign secret"}\n',
        b'{"status":NaN}\n',
        b'{"status":"ok","text":"\\ud800","strategy":"plain-text@1","transformations":["utf8-bom-removed-if-present","newlines-lf"]}\n',
    ],
)
def test_untrusted_records_refuse_generically(record: bytes) -> None:
    with pytest.raises(ExtractionError) as error:
        extraction._result(record, b"", "text/plain", 0)
    assert error.value.code is ExtractionCode.PROTOCOL
    assert "foreign secret" not in str(error.value)


@pytest.mark.parametrize("exit_code", [2, -9, 1])
def test_success_record_cannot_override_child_failure(exit_code: int) -> None:
    record, _ = _record()
    with pytest.raises(ExtractionError) as error:
        extraction._result(record, b"", "text/plain", exit_code)
    assert error.value.code is ExtractionCode.PROTOCOL


@pytest.mark.asyncio
async def test_launch_uses_literal_command_empty_environment_closed_fds_and_exact_eof_request(
    runtime: extraction.ScoutExtractionRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record, code = _record()
    process = _process(record, code)
    launch = AsyncMock(return_value=process)
    monkeypatch.setattr(extraction.asyncio, "create_subprocess_exec", launch)
    lifecycle = extraction.ExtractionLifecycle()
    result = await extraction.extract_static_text(
        b"ordinary text", media_type="text/plain", runtime=runtime, lifecycle=lifecycle
    )
    assert result.text == "ordinary text"
    assert lifecycle.child == "reaped"
    assert launch.call_args.args == extraction._command(runtime)
    assert launch.call_args.kwargs == {
        "stdin": -1,
        "stdout": -1,
        "stderr": -1,
        "env": {},
        "cwd": "/",
        "close_fds": True,
        "start_new_session": True,
        "limit": 4096,
    }
    writes = b"".join(call.args[0] for call in process.stdin.write.call_args_list)
    header, body = writes.split(b"\n", 1)
    assert json.loads(header) == {"media_type": "text/plain", "body_bytes": 13}
    assert body == b"ordinary text"
    process.stdin.close.assert_called()


@pytest.mark.asyncio
async def test_launcher_failure_has_no_bare_subprocess_fallback(
    runtime: extraction.ScoutExtractionRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch = AsyncMock(side_effect=PermissionError("foreign diagnostics"))
    monkeypatch.setattr(extraction.asyncio, "create_subprocess_exec", launch)
    lifecycle = extraction.ExtractionLifecycle()
    with pytest.raises(ExtractionError) as error:
        await extraction.extract_static_text(b"", media_type="text/plain", runtime=runtime, lifecycle=lifecycle)
    assert error.value.code is ExtractionCode.CONTAINMENT
    assert lifecycle.child == "not_started"
    assert "foreign" not in str(error.value)
    launch.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_refusal_retains_observed_reaping(
    runtime: extraction.ScoutExtractionRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = b"source\0text"
    record, code = _record(body)
    process = _process(record, code)
    monkeypatch.setattr(extraction.asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    lifecycle = extraction.ExtractionLifecycle()
    with pytest.raises(ExtractionError) as error:
        await extraction.extract_static_text(body, media_type="text/plain", runtime=runtime, lifecycle=lifecycle)
    assert error.value.code is ExtractionCode.WORKER
    assert lifecycle.child == "reaped"
    process.wait.assert_awaited()


@pytest.mark.asyncio
async def test_lifecycle_cannot_be_reused_for_another_invocation(
    runtime: extraction.ScoutExtractionRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch = AsyncMock()
    monkeypatch.setattr(extraction.asyncio, "create_subprocess_exec", launch)
    lifecycle = extraction.ExtractionLifecycle()
    with pytest.raises(ExtractionError) as first:
        await extraction.extract_static_text(
            b"", media_type=cast("ExtractionMedia", "unknown"), runtime=runtime, lifecycle=lifecycle
        )
    assert first.value.code is ExtractionCode.MEDIA
    with pytest.raises(ExtractionError) as second:
        await extraction.extract_static_text(b"", media_type="text/plain", runtime=runtime, lifecycle=lifecycle)
    assert second.value.code is ExtractionCode.CONTAINMENT
    assert lifecycle.child == "not_started"
    launch.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", ["stdout", "stderr"])
async def test_pipe_overflow_refuses_without_returning_partial_success(
    runtime: extraction.ScoutExtractionRuntime,
    monkeypatch: pytest.MonkeyPatch,
    stream: str,
) -> None:
    record, code = _record()
    process = _process(record, code)
    reader = asyncio.StreamReader()
    reader.feed_data(b"x" * (scout_worker.MAX_OUTPUT_BYTES + 1))
    reader.feed_eof()
    setattr(process, stream, reader)
    monkeypatch.setattr(extraction.asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    with pytest.raises(ExtractionError) as error:
        await extraction.extract_static_text(b"", media_type="text/plain", runtime=runtime)
    assert error.value.code is ExtractionCode.OUTPUT


@pytest.mark.asyncio
async def test_cancellation_kills_outer_group_and_waits_before_propagating(
    runtime: extraction.ScoutExtractionRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _process(b"")
    process.returncode = None
    entered = asyncio.Event()

    async def exchange(*args: object) -> tuple[bytes, int]:
        entered.set()
        await asyncio.Event().wait()
        return b"", 0

    kill = Mock()
    monkeypatch.setattr(extraction.asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    monkeypatch.setattr(extraction, "_exchange", exchange)
    monkeypatch.setattr(extraction.os, "killpg", kill)
    task = asyncio.create_task(extraction.extract_static_text(b"", media_type="text/plain", runtime=runtime))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    kill.assert_called_once_with(process.pid, signal.SIGKILL)
    process.wait.assert_awaited_once()


@pytest.mark.asyncio
async def test_unproved_cleanup_is_refusal_not_success(monkeypatch: pytest.MonkeyPatch) -> None:
    process = _process(b"")
    process.returncode = None

    async def pending() -> int:
        await asyncio.Event().wait()
        return 0

    process.wait = pending
    monkeypatch.setattr(extraction.os, "killpg", Mock())
    monkeypatch.setattr(extraction, "_CLEANUP_SECONDS", 0.001)

    async def spawned() -> asyncio.subprocess.Process:
        return cast("asyncio.subprocess.Process", process)

    lifecycle = extraction.ExtractionLifecycle()
    with pytest.raises(ExtractionError) as error:
        await extraction._finish_cleanup(asyncio.create_task(spawned()), lifecycle)
    assert error.value.code is ExtractionCode.CLEANUP
    assert lifecycle.child is None


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["media", "type", "size"])
async def test_invalid_input_refuses_before_any_launch(
    runtime: extraction.ScoutExtractionRuntime,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    launch = AsyncMock()
    monkeypatch.setattr(extraction.asyncio, "create_subprocess_exec", launch)
    body = cast("bytes", "foreign text") if case == "type" else b"x" * (scout_worker.MAX_BODY_BYTES + 1)
    media_type = cast("ExtractionMedia", "application/xml") if case == "media" else "text/plain"
    if case == "media":
        body = b""
    lifecycle = extraction.ExtractionLifecycle()
    with pytest.raises(ExtractionError) as error:
        await extraction.extract_static_text(body, media_type=media_type, runtime=runtime, lifecycle=lifecycle)
    assert error.value.code is (ExtractionCode.MEDIA if case == "media" else ExtractionCode.INPUT)
    assert lifecycle.child == "not_started"
    launch.assert_not_called()


@pytest.mark.asyncio
async def test_wall_timeout_kills_and_reaps_before_refusal(
    runtime: extraction.ScoutExtractionRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _process(b"")
    process.returncode = None

    async def exchange(*args: object) -> tuple[bytes, int]:
        await asyncio.Event().wait()
        return b"", 0

    kill = Mock()
    monkeypatch.setattr(extraction.asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    monkeypatch.setattr(extraction, "_exchange", exchange)
    monkeypatch.setattr(extraction, "_WALL_SECONDS", 0.001)
    monkeypatch.setattr(extraction.os, "killpg", kill)
    with pytest.raises(ExtractionError) as error:
        await extraction.extract_static_text(b"", media_type="text/plain", runtime=runtime)
    assert error.value.code is ExtractionCode.TIMEOUT
    kill.assert_called_once_with(process.pid, signal.SIGKILL)
    process.wait.assert_awaited_once()


@pytest.mark.asyncio
async def test_repeated_cancellation_cannot_interrupt_owned_cleanup(
    runtime: extraction.ScoutExtractionRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _process(b"")
    process.returncode = None
    entered, cleanup_entered, release = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def exchange(*args: object) -> tuple[bytes, int]:
        entered.set()
        await asyncio.Event().wait()
        return b"", 0

    async def wait() -> int:
        cleanup_entered.set()
        await release.wait()
        return -9

    process.wait = wait
    kill = Mock()
    monkeypatch.setattr(extraction.asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    monkeypatch.setattr(extraction, "_exchange", exchange)
    monkeypatch.setattr(extraction.os, "killpg", kill)
    lifecycle = extraction.ExtractionLifecycle()
    task = asyncio.create_task(
        extraction.extract_static_text(b"", media_type="text/plain", runtime=runtime, lifecycle=lifecycle)
    )
    await entered.wait()
    task.cancel()
    await cleanup_entered.wait()
    assert lifecycle.child is None
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert lifecycle.child == "reaped"
    kill.assert_called_once_with(process.pid, signal.SIGKILL)


@pytest.mark.asyncio
async def test_cancellation_during_launch_waits_for_owned_process_then_cleans(
    runtime: extraction.ScoutExtractionRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _process(b"")
    process.returncode = None
    entered, release = asyncio.Event(), asyncio.Event()

    async def launch(*args: object, **kwargs: object) -> asyncio.subprocess.Process:
        entered.set()
        await release.wait()
        return cast("asyncio.subprocess.Process", process)

    kill = Mock()
    monkeypatch.setattr(extraction.asyncio, "create_subprocess_exec", launch)
    monkeypatch.setattr(extraction.os, "killpg", kill)
    task = asyncio.create_task(extraction.extract_static_text(b"", media_type="text/plain", runtime=runtime))
    await entered.wait()
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    kill.assert_called_once_with(process.pid, signal.SIGKILL)
    process.wait.assert_awaited_once()


@pytest.mark.asyncio
async def test_late_launch_after_cleanup_refusal_still_has_kill_and_reap_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _process(b"")
    process.returncode = None
    release, reaped = asyncio.Event(), asyncio.Event()

    async def spawned() -> asyncio.subprocess.Process:
        await release.wait()
        return cast("asyncio.subprocess.Process", process)

    async def wait() -> int:
        reaped.set()
        return -9

    process.wait = AsyncMock(side_effect=wait)
    kill = Mock()
    monkeypatch.setattr(extraction.os, "killpg", kill)
    monkeypatch.setattr(extraction, "_CLEANUP_SECONDS", 0.001)
    spawn = asyncio.create_task(spawned())
    lifecycle = extraction.ExtractionLifecycle()
    with pytest.raises(ExtractionError) as error:
        await extraction._finish_cleanup(spawn, lifecycle)
    assert error.value.code is ExtractionCode.CLEANUP
    assert lifecycle.child is None
    kill.assert_not_called()
    release.set()
    await asyncio.wait_for(reaped.wait(), timeout=1.0)
    kill.assert_called_once_with(process.pid, signal.SIGKILL)
    process.wait.assert_awaited_once()
    process.stdin.close.assert_called_once()
    assert lifecycle.child is None
