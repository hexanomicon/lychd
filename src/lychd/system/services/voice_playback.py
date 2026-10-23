"""Explicit finite playback of validated reply bytes, with owned process settlement."""

from __future__ import annotations

import asyncio
import os
import signal
from contextlib import suppress
from typing import Literal

from lychd.domain.speech_probe import SpeechProbeError
from lychd.lib.asyncio import complete_under_cancellation
from lychd.system.services.speech_probe import inspect_generated_wav

_LAUNCH_SECONDS = 5
_RETIRE_SECONDS = 2
_PLAYBACK_SLACK_SECONDS = 5
_FAILURE = "Voice playback failed; human hearing is unconfirmed."
_UNSETTLED = "Voice playback ownership is unsettled; human hearing is unconfirmed."


class VoicePlaybackError(RuntimeError):
    """Playback refused or failed without exposing audio or player diagnostics."""


class VoicePlaybackUnsettled(VoicePlaybackError):  # noqa: N818 - caller contract names unsettled ownership
    """Owned player retirement is unproven; capture must remain closed."""


def _cancellations() -> int:
    owner = asyncio.current_task()
    return owner.cancelling() if owner is not None else 0


def _group_exists(pid: int) -> bool:
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    return True


async def _join_group(process: asyncio.subprocess.Process) -> None:
    await process.wait()
    while _group_exists(process.pid):  # noqa: ASYNC110 - groups have no asyncio exit notification
        await asyncio.sleep(0.02)


async def _retire(process: asyncio.subprocess.Process) -> None:
    if process.stdin is not None:
        process.stdin.close()
    # An exited leader does not establish that its descendants have retired.
    if _group_exists(process.pid):
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
    try:
        async with asyncio.timeout(_RETIRE_SECONDS):
            await _join_group(process)
    except TimeoutError:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        async with asyncio.timeout(_RETIRE_SECONDS):
            await _join_group(process)


async def _settle_retirement(process: asyncio.subprocess.Process) -> None:
    closing = asyncio.create_task(_retire(process))
    try:
        try:
            await asyncio.shield(closing)
        except asyncio.CancelledError:
            try:
                await complete_under_cancellation(closing)
            except asyncio.CancelledError:
                raise VoicePlaybackUnsettled(_UNSETTLED) from None
            raise
    except VoicePlaybackUnsettled:
        raise
    except (OSError, RuntimeError, TimeoutError):
        raise VoicePlaybackUnsettled(_UNSETTLED) from None


async def _launch(device: Literal["default", "pulse"]) -> asyncio.subprocess.Process:
    if type(device) is not str or device not in {"default", "pulse"}:
        raise VoicePlaybackError(_FAILURE)
    try:
        return await asyncio.create_subprocess_exec(
            "aplay",
            "--quiet",
            "--device",
            device,
            "--file-type",
            "wav",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError:
        raise
    except (OSError, RuntimeError, asyncio.CancelledError):
        # No process handle was adopted; partial launch settlement is unproven.
        raise VoicePlaybackUnsettled(_UNSETTLED) from None


async def play_reply(content: bytes, *, device: Literal["default", "pulse"] = "default") -> Literal["player_exited"]:
    """Play one bounded canonical PCM WAV; player exit does not prove hearing.

    The caller explicitly selects playback and closes capture before entry.
    The system ALSA default preserves host routing; explicit Pulse never falls back.
    Unsupported device values refuse before any player is launched.
    Cancellation adopts an in-flight launch and joins the owned process group.
    The launch work deadline may be exceeded by required ownership settlement
    while waiting for the OS to return a process handle; late launches receive
    no audio and are retired before this call returns.
    """
    try:
        facts = inspect_generated_wav(content)
    except SpeechProbeError:
        raise VoicePlaybackError(_FAILURE) from None
    launching = asyncio.create_task(_launch(device))
    process: asyncio.subprocess.Process | None = None
    try:
        try:
            async with asyncio.timeout(_LAUNCH_SECONDS):
                process = await asyncio.shield(launching)
        except (asyncio.CancelledError, TimeoutError):
            # Cancelling subprocess creation can kill only the leader and lose
            # its group handle. Adopt the shielded launch, even after expiry.
            cancellations = _cancellations()
            with suppress(FileNotFoundError):
                process = await complete_under_cancellation(launching)
            if _cancellations() > cancellations:
                raise asyncio.CancelledError from None
            raise
        async with asyncio.timeout(facts.frame_count / facts.sample_rate_hz + _PLAYBACK_SLACK_SECONDS):
            if process is None or process.stdin is None:
                raise VoicePlaybackError(_FAILURE)
            process.stdin.write(content)
            await process.stdin.drain()
            process.stdin.close()
            await process.stdin.wait_closed()
            if await process.wait() != 0:
                raise VoicePlaybackError(_FAILURE)
    except VoicePlaybackUnsettled:
        raise
    except (OSError, RuntimeError, TimeoutError):
        raise VoicePlaybackError(_FAILURE) from None
    else:
        return "player_exited"
    finally:
        if process is not None:
            await _settle_retirement(process)
