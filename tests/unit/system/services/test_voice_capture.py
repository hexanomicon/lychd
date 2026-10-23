"""Bound capture acquisition and process ownership without opening a microphone."""

from __future__ import annotations

import asyncio
from typing import Any, Literal
from unittest.mock import AsyncMock

import pytest

from lychd.domain.artifacts import ArtifactRef
from lychd.extensions.builtin.echo.material import inspect_pcm_utterance
from lychd.system.services import voice_capture


class Recorder:
    pid = 876543

    def __init__(self, content: bytes | None, status: int = 0) -> None:
        self.stdout = asyncio.StreamReader()
        self.returncode: int | None = None
        self.status = status
        if content is not None:
            self.stdout.feed_data(content)
            self.stdout.feed_eof()

    async def wait(self) -> int:
        self.returncode = self.status
        return self.status


@pytest.fixture(autouse=True)
def no_host_process_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(_pid: int) -> bool:
        return False

    monkeypatch.setattr(voice_capture, "_group_exists", missing)


@pytest.mark.parametrize("device", [None, "default", "pulse"])
@pytest.mark.asyncio
async def test_exact_capture_passes_real_echo_inspector(
    device: Literal["default", "pulse"] | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib

    recorder = Recorder(b"\0" * 32_000)
    launch = AsyncMock(return_value=recorder)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    content = (
        await voice_capture.capture_utterance(seconds=1)
        if device is None
        else await voice_capture.capture_utterance(seconds=1, device=device)
    )
    source = ArtifactRef(
        artifact_id="capture",
        digest="sha256:" + hashlib.sha256(content).hexdigest(),
        media_type="audio/wav",
        size=len(content),
        classification="private",
    )
    assert inspect_pcm_utterance(source, content).frame_count == 16_000
    assert launch.call_args.args == (
        "arecord",
        "--quiet",
        "--file-type",
        "raw",
        "--format",
        "S16_LE",
        "--rate",
        "16000",
        "--channels",
        "1",
        "--samples",
        "16000",
        "--device",
        "default" if device is None else device,
    )
    assert launch.call_args.kwargs["start_new_session"] is True
    launch.assert_awaited_once()


@pytest.mark.parametrize("seconds", [0, 16, True, 1.5])
@pytest.mark.asyncio
async def test_invalid_capture_never_launches(seconds: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    launch = AsyncMock()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    with pytest.raises(ValueError, match="1-15 whole seconds"):
        await voice_capture.capture_utterance(seconds=seconds)
    launch.assert_not_called()


@pytest.mark.parametrize("device", [None, "", "pipewire", "hw:0", "--device=default", True, {}])
@pytest.mark.asyncio
async def test_unsupported_capture_device_never_launches(device: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    launch = AsyncMock()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    with pytest.raises(ValueError, match="explicit supported local device"):
        await voice_capture.capture_utterance(seconds=1, device=device)
    launch.assert_not_called()


@pytest.mark.parametrize("device", ["default", "pulse"])
@pytest.mark.asyncio
async def test_failed_explicit_device_does_not_try_another(
    device: Literal["default", "pulse"], monkeypatch: pytest.MonkeyPatch
) -> None:
    launch = AsyncMock(return_value=Recorder(b"", status=1))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    with pytest.raises(voice_capture.VoiceCaptureError, match="failed or returned an incomplete utterance") as failure:
        await voice_capture.capture_utterance(seconds=1, device=device)
    assert not isinstance(failure.value, voice_capture.VoiceCaptureUnsettled)
    launch.assert_awaited_once()
    assert launch.call_args.args[-2:] == ("--device", device)


@pytest.mark.asyncio
async def test_oversized_recorder_is_stopped_without_an_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = Recorder(b"\0" * 32_002)
    killed: list[int] = []

    def exists(_pid: int) -> bool:
        return not killed

    def terminate(pid: int, _sig: int) -> None:
        killed.append(pid)

    monkeypatch.setattr(voice_capture, "_group_exists", exists)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=recorder))
    monkeypatch.setattr(voice_capture.os, "killpg", terminate)
    with pytest.raises(voice_capture.VoiceCaptureError, match="sample budget") as failure:
        await voice_capture.capture_utterance(seconds=1)
    assert not isinstance(failure.value, voice_capture.VoiceCaptureUnsettled)
    assert killed == [recorder.pid]
    assert recorder.returncode is not None


@pytest.mark.asyncio
async def test_cancel_during_launch_retires_the_eventual_recorder(monkeypatch: pytest.MonkeyPatch) -> None:
    started = asyncio.Event()
    finish_launch = asyncio.Event()
    recorder = Recorder(None)
    killed: list[int] = []

    def exists(_pid: int) -> bool:
        return not killed

    def terminate(pid: int, _sig: int) -> None:
        killed.append(pid)

    monkeypatch.setattr(voice_capture, "_group_exists", exists)

    async def launch(*args: Any, **kwargs: Any) -> Recorder:
        started.set()
        await finish_launch.wait()
        return recorder

    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    monkeypatch.setattr(voice_capture.os, "killpg", terminate)
    task = asyncio.create_task(voice_capture.capture_utterance(seconds=1))
    await started.wait()
    task.cancel()
    finish_launch.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert killed == [recorder.pid]
    assert recorder.returncode is not None


@pytest.mark.asyncio
async def test_truncated_capture_does_not_become_valid_pcm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=Recorder(b"\0" * 100)))
    with pytest.raises(voice_capture.VoiceCaptureError, match="incomplete") as failure:
        await voice_capture.capture_utterance(seconds=1)
    assert not isinstance(failure.value, voice_capture.VoiceCaptureUnsettled)


@pytest.mark.asyncio
async def test_exited_leader_does_not_hide_a_surviving_group(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = Recorder(None)
    recorder.returncode = 0
    group_alive = True
    killed: list[int] = []

    def terminate_group(pid: int, _sig: int) -> None:
        nonlocal group_alive
        killed.append(pid)
        group_alive = False

    def exists(_pid: int) -> bool:
        return group_alive

    monkeypatch.setattr(voice_capture, "_group_exists", exists)
    monkeypatch.setattr(voice_capture.os, "killpg", terminate_group)
    await voice_capture._retire(recorder)  # type: ignore[arg-type] - fixed substitute process, no host effects
    assert killed == [recorder.pid]
    assert group_alive is False


@pytest.mark.parametrize("outcome", ["complete", "incomplete", "cancelled"])
@pytest.mark.asyncio
async def test_retirement_failure_overrides_body_outcome(outcome: str, monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = Recorder(b"\0" * (32_000 if outcome == "complete" else 100))
    if outcome == "cancelled":
        monkeypatch.setattr(recorder, "wait", AsyncMock(side_effect=asyncio.CancelledError))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=recorder))
    monkeypatch.setattr(voice_capture, "_retire", AsyncMock(side_effect=TimeoutError("private retirement details")))
    with pytest.raises(voice_capture.VoiceCaptureUnsettled, match="retirement unconfirmed") as failure:
        await voice_capture.capture_utterance(seconds=1)
    assert "private" not in str(failure.value)


@pytest.mark.asyncio
async def test_repeated_cancellation_during_retirement_discards_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    entered, release = asyncio.Event(), asyncio.Event()
    recorder = Recorder(b"\0" * 32_000)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=recorder))

    async def retire(_: Any) -> None:
        entered.set()
        await release.wait()

    monkeypatch.setattr(voice_capture, "_retire", retire)
    task = asyncio.create_task(voice_capture.capture_utterance(seconds=1))
    try:
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, 1)


@pytest.mark.asyncio
async def test_launch_task_cancellation_is_unknown_ownership(monkeypatch: pytest.MonkeyPatch) -> None:
    launch = AsyncMock(side_effect=asyncio.CancelledError)
    retire = AsyncMock()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    monkeypatch.setattr(voice_capture, "_retire", retire)
    with pytest.raises(voice_capture.VoiceCaptureUnsettled, match="without an adopted process"):
        await voice_capture.capture_utterance(seconds=1)
    launch.assert_awaited_once()
    retire.assert_not_called()


@pytest.mark.asyncio
async def test_retirement_task_cancellation_is_unknown_ownership(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = Recorder(b"\0" * 32_000)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=recorder))
    monkeypatch.setattr(voice_capture, "_retire", AsyncMock(side_effect=asyncio.CancelledError))
    with pytest.raises(voice_capture.VoiceCaptureUnsettled, match="retirement cancelled without settlement"):
        await voice_capture.capture_utterance(seconds=1)


@pytest.mark.asyncio
async def test_unadopted_launch_failure_has_no_safe_retirement_proof(monkeypatch: pytest.MonkeyPatch) -> None:
    launch = AsyncMock(side_effect=OSError("private launch details"))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    with pytest.raises(OSError, match="private launch details"):
        await voice_capture.capture_utterance(seconds=1)
    launch.assert_awaited_once()


@pytest.mark.asyncio
async def test_read_deadline_failure_is_safe_only_after_retirement(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = Recorder(None)
    monkeypatch.setattr(recorder.stdout, "read", AsyncMock(side_effect=TimeoutError))
    retire = AsyncMock()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=recorder))
    monkeypatch.setattr(voice_capture, "_retire", retire)
    with pytest.raises(voice_capture.VoiceCaptureError) as failure:
        await voice_capture.capture_utterance(seconds=1)
    assert not isinstance(failure.value, voice_capture.VoiceCaptureUnsettled)
    retire.assert_awaited_once_with(recorder)
