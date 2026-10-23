"""Held capture ownership and completion without launching a recorder or microphone."""

from __future__ import annotations

import asyncio
import signal
import struct
from typing import Any
from unittest.mock import AsyncMock

import pytest

from lychd.system.services import voice_capture


class Pipe(asyncio.StreamReader):
    def __init__(self) -> None:
        super().__init__()
        self.read_started = asyncio.Event()

    async def read(self, n: int = -1) -> bytes:
        self.read_started.set()
        return await super().read(n)


class Recorder:
    pid = 876543

    def __init__(self, pcm: bytes = b"\0" * 8000, *, status: int = 1) -> None:
        self.stdout = Pipe()
        self.stdout.feed_data(pcm)
        self.returncode: int | None = None
        self.status = status
        self.alive = True
        self.ignore_int = False
        self.signals: list[int] = []
        self.exited = asyncio.Event()

    def finish(self) -> None:
        self.returncode = self.status
        self.alive = False
        self.stdout.feed_eof()
        self.exited.set()

    def signal(self, _pid: int, sig: int) -> None:
        self.signals.append(sig)
        if sig != signal.SIGINT or not self.ignore_int:
            self.finish()

    async def wait(self) -> int:
        await self.exited.wait()
        assert self.returncode is not None
        return self.returncode


def install(monkeypatch: pytest.MonkeyPatch, recorder: Recorder) -> AsyncMock:
    launch = AsyncMock(return_value=recorder)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)

    def group_exists(_pid: int) -> bool:
        return recorder.alive

    monkeypatch.setattr(voice_capture, "_group_exists", group_exists)
    monkeypatch.setattr(voice_capture.os, "killpg", recorder.signal)
    return launch


async def begin(recorder: Recorder, released: asyncio.Event, **kwargs: Any) -> asyncio.Task[bytes]:
    task = asyncio.create_task(voice_capture.capture_held_utterance(released=released, max_seconds=1, **kwargs))
    await asyncio.wait_for(recorder.stdout.read_started.wait(), 1)
    return task


@pytest.mark.asyncio
async def test_release_returns_exact_partial_wave_after_sigint_and_group_retirement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder, released = Recorder(), asyncio.Event()
    launch = install(monkeypatch, recorder)
    notices: list[str] = []
    task = await begin(
        recorder,
        released,
        device="pulse",
        on_started=lambda: notices.append("started"),
        on_finishing=lambda: notices.append("finishing"),
    )
    recorder.stdout.feed_data(b"\1\0" * 1000)
    released.set()
    content = await asyncio.wait_for(task, 1)
    assert content[44:] == b"\0" * 8000 + b"\1\0" * 1000
    assert struct.unpack_from("<I", content, 40)[0] == 10_000
    assert content[:4] == b"RIFF"
    assert content[8:12] == b"WAVE"
    assert notices == ["started", "finishing"]
    assert recorder.signals == [signal.SIGINT]
    assert not recorder.alive
    assert launch.call_args.args[-2:] == ("--device", "pulse")
    assert launch.call_args.args[launch.call_args.args.index("--samples") + 1] == "16000"
    assert launch.call_args.kwargs["start_new_session"] is True


@pytest.mark.parametrize(
    "changes",
    [
        {"max_seconds": True},
        {"max_seconds": 0},
        {"max_seconds": 16},
        {"device": "hw:0"},
        {"released": None},
        {"on_started": 1},
        {"on_finishing": 1},
    ],
)
@pytest.mark.asyncio
async def test_invalid_arguments_never_launch(changes: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    launch = AsyncMock()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    arguments: dict[str, Any] = {"released": asyncio.Event(), "max_seconds": 1, **changes}
    with pytest.raises(ValueError, match="Held capture requires"):
        await voice_capture.capture_held_utterance(**arguments)
    launch.assert_not_called()


@pytest.mark.asyncio
async def test_release_before_entry_never_launches(monkeypatch: pytest.MonkeyPatch) -> None:
    launch, released = AsyncMock(), asyncio.Event()
    released.set()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    with pytest.raises(voice_capture.VoiceCaptureError, match="before recorder launch"):
        await voice_capture.capture_held_utterance(released=released, max_seconds=1)
    launch.assert_not_called()


@pytest.mark.parametrize("cancel", [False, True])
@pytest.mark.asyncio
async def test_release_or_cancel_during_launch_adopts_retires_and_discards(
    monkeypatch: pytest.MonkeyPatch, *, cancel: bool
) -> None:
    recorder, released = Recorder(), asyncio.Event()
    install(monkeypatch, recorder)
    entered, finish_launch = asyncio.Event(), asyncio.Event()
    notices: list[str] = []

    async def launch(*_args: Any, **_kwargs: Any) -> Recorder:
        entered.set()
        await finish_launch.wait()
        return recorder

    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    task = asyncio.create_task(
        voice_capture.capture_held_utterance(
            released=released, max_seconds=1, on_started=lambda: notices.append("started")
        )
    )
    await entered.wait()
    if cancel:
        task.cancel()
    else:
        released.set()
    finish_launch.set()
    with pytest.raises(asyncio.CancelledError if cancel else voice_capture.VoiceCaptureError):
        await asyncio.wait_for(task, 1)
    assert recorder.signals == [signal.SIGTERM]
    assert not recorder.alive
    assert notices == []


@pytest.mark.parametrize("pcm", [b"", b"\0" * 7998, b"\0" * 8001, b"\0" * 32_001])
@pytest.mark.asyncio
async def test_empty_short_odd_or_overflow_capture_never_returns_wave(
    pcm: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder, released = Recorder(pcm), asyncio.Event()
    install(monkeypatch, recorder)
    task = await begin(recorder, released)
    released.set()
    with pytest.raises(voice_capture.VoiceCaptureError) as failure:
        await asyncio.wait_for(task, 1)
    assert not isinstance(failure.value, voice_capture.VoiceCaptureUnsettled)
    assert not recorder.alive


@pytest.mark.parametrize("status", [0, -signal.SIGINT, 2])
@pytest.mark.asyncio
async def test_unqualified_finish_exit_status_discards(status: int, monkeypatch: pytest.MonkeyPatch) -> None:
    recorder, released = Recorder(status=status), asyncio.Event()
    install(monkeypatch, recorder)
    task = await begin(recorder, released)
    released.set()
    with pytest.raises(voice_capture.VoiceCaptureError, match="unusable"):
        await asyncio.wait_for(task, 1)
    assert not recorder.alive


@pytest.mark.asyncio
async def test_spontaneous_status_one_before_release_is_not_graceful_finish(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder, released = Recorder(), asyncio.Event()
    install(monkeypatch, recorder)
    task = await begin(recorder, released)
    recorder.finish()
    with pytest.raises(voice_capture.VoiceCaptureError, match="before an intentional"):
        await asyncio.wait_for(task, 1)
    assert recorder.signals == []


@pytest.mark.parametrize("sample_limit", [False, True])
@pytest.mark.asyncio
async def test_wall_or_sample_limit_without_release_discards(
    monkeypatch: pytest.MonkeyPatch, *, sample_limit: bool
) -> None:
    recorder, released = Recorder(b"\0" * (32_000 if sample_limit else 8000)), asyncio.Event()
    install(monkeypatch, recorder)
    task = await begin(recorder, released)
    with pytest.raises(voice_capture.VoiceCaptureError):
        await asyncio.wait_for(task, 2)
    assert recorder.signals == [signal.SIGTERM]
    assert not recorder.alive


@pytest.mark.asyncio
async def test_forced_retirement_discards_released_audio(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder, released = Recorder(), asyncio.Event()
    recorder.ignore_int = True
    install(monkeypatch, recorder)
    join = voice_capture._join_group  # pyright: ignore[reportPrivateUsage] - force the real retirement fallback
    calls = 0

    async def first_deadline(process: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError
        await join(process)

    monkeypatch.setattr(voice_capture, "_join_group", first_deadline)
    task = await begin(recorder, released)
    released.set()
    with pytest.raises(voice_capture.VoiceCaptureError, match="unusable"):
        await asyncio.wait_for(task, 1)
    assert recorder.signals == [signal.SIGINT, signal.SIGKILL]
    assert not recorder.alive


@pytest.mark.parametrize("phase", ["capture", "retirement"])
@pytest.mark.asyncio
async def test_cancellation_never_returns_audio_and_joins_retirement(
    phase: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder, released = Recorder(), asyncio.Event()
    install(monkeypatch, recorder)
    entered, finish_join = asyncio.Event(), asyncio.Event()

    async def held_join(process: Any) -> None:
        entered.set()
        await finish_join.wait()
        await process.wait()

    monkeypatch.setattr(voice_capture, "_join_group", held_join)
    task = await begin(recorder, released)
    if phase == "retirement":
        released.set()
        await entered.wait()
    task.cancel()
    await entered.wait()
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    finish_join.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, 1)
    assert not recorder.alive


@pytest.mark.parametrize("callback_name", ["on_started", "on_finishing"])
@pytest.mark.asyncio
async def test_indication_failure_discards_and_retires(callback_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    recorder, released = Recorder(), asyncio.Event()
    install(monkeypatch, recorder)

    def failed() -> None:
        msg = "private presentation detail"
        raise ValueError(msg)

    task = await begin(recorder, released, **{callback_name: failed})
    released.set()
    with pytest.raises(voice_capture.VoiceCaptureError) as failure:
        await asyncio.wait_for(task, 1)
    assert "private" not in str(failure.value)
    assert not recorder.alive


@pytest.mark.asyncio
async def test_retirement_uncertainty_overrides_released_audio(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder, released = Recorder(), asyncio.Event()
    install(monkeypatch, recorder)
    monkeypatch.setattr(voice_capture, "_join_group", AsyncMock(side_effect=RuntimeError("private failure")))
    task = await begin(recorder, released)
    released.set()
    with pytest.raises(voice_capture.VoiceCaptureUnsettled) as failure:
        await asyncio.wait_for(task, 1)
    assert "private" not in str(failure.value)
