"""Synthetic subprocess/group checks; no speaker or recording is accessed."""

from __future__ import annotations

import asyncio
import signal
import struct
from collections.abc import Awaitable
from typing import Any, Literal
from unittest.mock import AsyncMock

import pytest

from lychd.system.services import voice_playback


def wav(*, frames: int = 80) -> bytes:
    size = frames * 2
    return (
        struct.pack(
            "<4sI4s4sIHHIIHH4sI", b"RIFF", size + 36, b"WAVE", b"fmt ", 16, 1, 1, 8000, 16000, 2, 16, b"data", size
        )
        + b"\0" * size
    )


class Pipe:
    def __init__(self) -> None:
        self.content = b""
        self.closed = False
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.release.set()
        self.broken = False

    def write(self, content: bytes) -> None:
        self.content += content

    async def drain(self) -> None:
        self.started.set()
        if self.broken:
            msg = "private-player-diagnostic"
            raise BrokenPipeError(msg)
        await self.release.wait()

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        pass


class Player:
    pid = 876543

    def __init__(self) -> None:
        self.stdin = Pipe()
        self.status = 0
        self.returncode: int | None = None
        self.exited = asyncio.Event()
        self.exited.set()
        self.waiting = asyncio.Event()

    async def wait(self) -> int:
        self.waiting.set()
        await self.exited.wait()
        self.returncode = self.status
        return self.status


class Host:
    def __init__(self) -> None:
        self.player = Player()
        self.alive = True
        self.ignore_term = False
        self.ignore_kill = False
        self.signals: list[int] = []
        self.terminated = asyncio.Event()

    def killpg(self, pid: int, sig: int) -> None:
        assert pid == self.player.pid
        if not self.alive:
            raise ProcessLookupError
        if sig:
            self.signals.append(sig)
            self.terminated.set()
            if (sig == signal.SIGKILL and self.ignore_kill) or (sig == signal.SIGTERM and self.ignore_term):
                return
            self.alive = False
            self.player.exited.set()


@pytest.fixture
def host(monkeypatch: pytest.MonkeyPatch) -> Host:
    value = Host()
    monkeypatch.setattr(voice_playback.os, "killpg", value.killpg)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=value.player))
    monkeypatch.setattr(voice_playback, "_RETIRE_SECONDS", 0.01)
    return value


@pytest.mark.parametrize("device", [None, "default", "pulse"])
@pytest.mark.asyncio
async def test_fixed_argv_and_exact_validated_stdin(
    host: Host, monkeypatch: pytest.MonkeyPatch, device: Literal["default", "pulse"] | None
) -> None:
    launch = AsyncMock(return_value=host.player)
    inspected: list[bytes] = []
    inspect = voice_playback.inspect_generated_wav

    def checked(content: bytes) -> Any:
        inspected.append(content)
        launch.assert_not_called()
        return inspect(content)

    monkeypatch.setattr(voice_playback, "inspect_generated_wav", checked)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    content = wav()
    result = (
        await voice_playback.play_reply(content)
        if device is None
        else await voice_playback.play_reply(content, device=device)
    )
    assert result == "player_exited"
    assert inspected == [content]
    assert host.player.stdin.content == content
    assert host.player.stdin.closed
    launch.assert_awaited_once_with(
        "aplay",
        "--quiet",
        "--device",
        "default" if device is None else device,
        "--file-type",
        "wav",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        start_new_session=True,
    )
    assert not host.alive


@pytest.mark.parametrize("device", [None, "", "pipewire", "hw:0", "--device=default", True, {}])
@pytest.mark.asyncio
async def test_unsupported_playback_device_never_launches(
    device: Any, host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    launch = AsyncMock()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    with pytest.raises(voice_playback.VoicePlaybackError, match="hearing is unconfirmed"):
        await voice_playback.play_reply(wav(), device=device)
    launch.assert_not_called()
    assert host.player.stdin.content == b""


@pytest.mark.parametrize("device", ["default", "pulse"])
@pytest.mark.asyncio
async def test_failed_selected_output_never_tries_another_device(
    device: Literal["default", "pulse"], host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    host.player.status = 1
    launch = AsyncMock(return_value=host.player)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    with pytest.raises(voice_playback.VoicePlaybackError, match="hearing is unconfirmed") as failure:
        await voice_playback.play_reply(wav(), device=device)
    assert type(failure.value) is voice_playback.VoicePlaybackError
    launch.assert_awaited_once()
    assert launch.call_args.args[2:4] == ("--device", device)
    assert not host.alive


@pytest.mark.asyncio
async def test_independently_cancelled_retirement_keeps_ownership_unknown(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(voice_playback, "_retire", AsyncMock(side_effect=asyncio.CancelledError))
    with pytest.raises(voice_playback.VoicePlaybackUnsettled, match="ownership is unsettled"):
        await voice_playback.play_reply(wav())
    assert host.alive


@pytest.mark.parametrize(
    "content",
    [b"not-wave", bytearray(wav()), memoryview(wav()), "wav", wav(frames=960001)],
    ids=["invalid", "bytearray", "memoryview", "text", "over-duration"],
)
@pytest.mark.asyncio
async def test_invalid_or_nonstrict_bytes_never_launch(
    content: Any, host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    launch = AsyncMock()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    with pytest.raises(voice_playback.VoicePlaybackError, match="hearing is unconfirmed"):
        await voice_playback.play_reply(content)
    launch.assert_not_called()


@pytest.mark.parametrize("failure", ["nonzero", "broken-pipe", "missing-binary"])
@pytest.mark.asyncio
async def test_failures_are_content_free_and_settled(failure: str, host: Host, monkeypatch: pytest.MonkeyPatch) -> None:
    if failure == "nonzero":
        host.player.status = 2
    elif failure == "broken-pipe":
        host.player.stdin.broken = True
    else:
        monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(side_effect=FileNotFoundError("private-path")))
    with pytest.raises(voice_playback.VoicePlaybackError) as error:
        await voice_playback.play_reply(wav())
    assert type(error.value) is voice_playback.VoicePlaybackError
    assert str(error.value) == "Voice playback failed; human hearing is unconfirmed."
    assert error.value.__suppress_context__
    if failure != "missing-binary":
        assert not host.alive
        assert host.player.returncode is not None


@pytest.mark.asyncio
async def test_launch_cancel_adopts_player_despite_repeated_cancel(host: Host, monkeypatch: pytest.MonkeyPatch) -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def launch(*args: Any, **kwargs: Any) -> Player:
        started.set()
        await release.wait()
        return host.player

    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    task = asyncio.create_task(voice_playback.play_reply(wav()))
    await started.wait()
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert host.player.stdin.content == b""
    assert not host.alive
    assert host.player.returncode is not None


@pytest.mark.asyncio
async def test_playback_cancel_joins_group_and_repeated_cancel(host: Host) -> None:
    host.player.stdin.release.clear()
    host.ignore_term = True
    task = asyncio.create_task(voice_playback.play_reply(wav()))
    await host.player.stdin.started.wait()
    task.cancel()
    await host.terminated.wait()
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert host.signals == [signal.SIGTERM, signal.SIGKILL]
    assert not host.alive
    assert host.player.returncode is not None


@pytest.mark.asyncio
async def test_cancel_during_final_retirement_propagates(host: Host) -> None:
    host.ignore_term = True
    task = asyncio.create_task(voice_playback.play_reply(wav()))
    await host.terminated.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert host.signals == [signal.SIGTERM, signal.SIGKILL]
    assert not host.alive


@pytest.mark.asyncio
async def test_exited_leader_does_not_hide_surviving_descendant(host: Host) -> None:
    host.player.returncode = 0
    host.ignore_term = True
    assert await voice_playback.play_reply(wav()) == "player_exited"
    assert host.signals == [signal.SIGTERM, signal.SIGKILL]
    assert not host.alive


@pytest.mark.parametrize("stage", ["write", "wait"])
@pytest.mark.asyncio
async def test_duration_bounds_whole_write_and_wait(stage: str, host: Host, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voice_playback, "_PLAYBACK_SLACK_SECONDS", 0)
    if stage == "write":
        host.player.stdin.release.clear()
    else:
        host.player.exited.clear()
    with pytest.raises(voice_playback.VoicePlaybackError, match="hearing is unconfirmed"):
        await voice_playback.play_reply(wav())
    assert host.signals == [signal.SIGTERM]
    assert not host.alive
    assert host.player.returncode is not None


@pytest.mark.parametrize("cancel", [False, True])
@pytest.mark.asyncio
async def test_launch_deadline_adopts_late_child_before_returning(
    host: Host, monkeypatch: pytest.MonkeyPatch, *, cancel: bool
) -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    settling = asyncio.Event()
    cancelled = asyncio.Event()
    complete = voice_playback.complete_under_cancellation

    async def join(operation: Awaitable[Any]) -> Any:
        settling.set()
        return await complete(operation)

    async def launch(*args: Any, **kwargs: Any) -> Player:
        started.set()
        try:
            await release.wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise
        return host.player

    monkeypatch.setattr(voice_playback, "_LAUNCH_SECONDS", 0.01)
    monkeypatch.setattr(voice_playback, "complete_under_cancellation", join)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    task = asyncio.create_task(voice_playback.play_reply(wav()))
    await started.wait()
    async with asyncio.timeout(1):
        await settling.wait()  # The work deadline expired before OS launch returned.
    assert not task.done()
    assert not cancelled.is_set()
    if cancel:
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError if cancel else voice_playback.VoicePlaybackError):
        await task
    assert not cancelled.is_set()
    assert host.player.stdin.content == b""
    assert host.signals == [signal.SIGTERM]
    assert not host.alive
    assert host.player.returncode is not None


@pytest.mark.asyncio
async def test_surviving_group_after_both_retirement_deadlines_is_unsettled(host: Host) -> None:
    host.ignore_term = True
    host.ignore_kill = True
    with pytest.raises(voice_playback.VoicePlaybackUnsettled) as error:
        await voice_playback.play_reply(wav())
    assert str(error.value) == "Voice playback ownership is unsettled; human hearing is unconfirmed."
    assert error.value.__suppress_context__
    assert host.signals == [signal.SIGTERM, signal.SIGKILL]
    assert host.alive


@pytest.mark.asyncio
async def test_launch_failure_without_adopted_handle_is_unsettled(host: Host, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(side_effect=RuntimeError("private-launch-detail")))
    with pytest.raises(voice_playback.VoicePlaybackUnsettled, match="ownership is unsettled"):
        await voice_playback.play_reply(wav())
    assert host.player.stdin.content == b""


@pytest.mark.asyncio
async def test_cancellation_with_unretired_group_is_unsettled(host: Host) -> None:
    host.player.stdin.release.clear()
    host.ignore_term = True
    host.ignore_kill = True
    task = asyncio.create_task(voice_playback.play_reply(wav()))
    await host.player.stdin.started.wait()
    task.cancel()
    await host.terminated.wait()
    task.cancel()
    with pytest.raises(voice_playback.VoicePlaybackUnsettled, match="ownership is unsettled"):
        await task
    assert host.signals == [signal.SIGTERM, signal.SIGKILL]
    assert host.alive
