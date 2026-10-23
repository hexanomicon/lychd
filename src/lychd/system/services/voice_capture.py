"""Explicit finite Linux microphone capture for the engineering speech probe."""

from __future__ import annotations

import asyncio
import os
import signal
import struct
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Literal

from lychd.lib.asyncio import complete_under_cancellation

SAMPLE_RATE = 16_000
MAX_CAPTURE_SECONDS = 15
MIN_HELD_FRAMES = 4000


@dataclass(frozen=True)
class _Retirement:
    signal_sent: bool
    forced: bool


class VoiceCaptureError(RuntimeError):
    """Capture failed after the owned recorder group retired; a new gesture may retry."""


class VoiceCaptureUnsettled(VoiceCaptureError):  # noqa: N818 - caller contract names unsettled ownership
    """Recorder retirement is unproven; further audio must remain closed."""


def _group_exists(pid: int) -> bool:
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    return True


async def _join_group(process: asyncio.subprocess.Process) -> None:
    await process.wait()
    while _group_exists(process.pid):  # noqa: ASYNC110 - process groups have no asyncio exit notification
        await asyncio.sleep(0.02)


async def _retire(
    process: asyncio.subprocess.Process, *, initial_signal: signal.Signals = signal.SIGTERM
) -> _Retirement:
    # Leader exit alone does not prove that its process group has retired.
    signal_sent = forced = False
    if _group_exists(process.pid):
        try:
            os.killpg(process.pid, initial_signal)
        except ProcessLookupError:
            pass
        else:
            signal_sent = True
    try:
        async with asyncio.timeout(2):
            await _join_group(process)
    except TimeoutError:
        forced = True
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        async with asyncio.timeout(2):
            await _join_group(process)
    return _Retirement(signal_sent, forced)


async def _settle_retirement(
    process: asyncio.subprocess.Process, *, initial_signal: signal.Signals = signal.SIGTERM
) -> _Retirement:
    closing = asyncio.create_task(
        _retire(process) if initial_signal == signal.SIGTERM else _retire(process, initial_signal=initial_signal)
    )
    try:
        try:
            return await asyncio.shield(closing)
        except asyncio.CancelledError:
            try:
                await complete_under_cancellation(closing)
            except asyncio.CancelledError:
                msg = "Recorder retirement cancelled without settlement; further audio must remain closed."
                raise VoiceCaptureUnsettled(msg) from None
            raise
    except VoiceCaptureUnsettled:
        raise
    except (OSError, RuntimeError, TimeoutError):
        msg = "Recorder retirement unconfirmed; further audio must remain closed."
        raise VoiceCaptureUnsettled(msg) from None


async def _launch_recorder(*, frames: int, device: Literal["default", "pulse"]) -> asyncio.subprocess.Process:
    launching = asyncio.create_task(
        asyncio.create_subprocess_exec(
            "arecord",
            "--quiet",
            "--file-type",
            "raw",
            "--format",
            "S16_LE",
            "--rate",
            str(SAMPLE_RATE),
            "--channels",
            "1",
            "--samples",
            str(frames),
            "--device",
            device,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
    )
    try:
        process = await asyncio.shield(launching)
    except asyncio.CancelledError:
        try:
            process = await complete_under_cancellation(launching)
        except asyncio.CancelledError:
            msg = "Recorder launch cancelled without an adopted process; ownership is unconfirmed."
            raise VoiceCaptureUnsettled(msg) from None
        await _settle_retirement(process)
        raise
    return process


def _wave(pcm: bytes) -> bytes:
    size = len(pcm)
    return (
        struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            size + 36,
            b"WAVE",
            b"fmt ",
            16,
            1,
            1,
            SAMPLE_RATE,
            SAMPLE_RATE * 2,
            2,
            16,
            b"data",
            size,
        )
        + pcm
    )


async def capture_utterance(*, seconds: int, device: Literal["default", "pulse"] = "default") -> bytes:
    """Capture an exact finite sample budget; unadopted launch errors prove no retirement.

    The caller owns visible indication, consent and private retention. The system
    ALSA default preserves routing; explicit Pulse never falls back. Only a
    VoiceCaptureError without VoiceCaptureUnsettled proves failed capture retired.
    """
    if (
        type(seconds) is not int
        or not 1 <= seconds <= MAX_CAPTURE_SECONDS
        or type(device) is not str
        or device not in {"default", "pulse"}
    ):
        msg = "Capture requires 1-15 whole seconds and an explicit supported local device."
        raise ValueError(msg)
    expected = seconds * SAMPLE_RATE * 2
    process = await _launch_recorder(frames=seconds * SAMPLE_RATE, device=device)
    try:
        async with asyncio.timeout(seconds + 5):
            if process.stdout is None:
                msg = "Recorder has no bounded output channel."
                raise VoiceCaptureError(msg)
            pcm = bytearray()
            while chunk := await process.stdout.read(min(65_536, expected + 1 - len(pcm))):
                pcm.extend(chunk)
                if len(pcm) > expected:
                    msg = "Recorder exceeded the exact sample budget."
                    raise VoiceCaptureError(msg)
            status = await process.wait()
            if status != 0 or len(pcm) != expected:
                msg = "Recorder failed or returned an incomplete utterance."
                raise VoiceCaptureError(msg)
        return _wave(bytes(pcm))
    except (OSError, RuntimeError, TimeoutError) as error:
        if isinstance(error, VoiceCaptureError):
            raise
        msg = "Recorder failed before completing the bounded utterance."
        raise VoiceCaptureError(msg) from None
    finally:
        await _settle_retirement(process)


async def _drain_held(
    reader: asyncio.StreamReader,
    *,
    expected: int,
    released: asyncio.Event,
    invalid: asyncio.Future[str],
    on_started: Callable[[], None] | None,
) -> bytes:
    """Continue draining invalid output until owned retirement closes its pipe."""
    pcm = bytearray()
    first = True
    while chunk := await reader.read(65_536):
        if first:
            first = False
            if on_started is not None:
                try:
                    on_started()
                except Exception:  # noqa: BLE001 - failed indication still requires pipe drainage and retirement
                    invalid.set_result("Recorder capture indication failed.")
        if invalid.done():
            continue
        if len(pcm) + len(chunk) > expected:
            invalid.set_result("Recorder exceeded the held sample budget.")
        else:
            pcm.extend(chunk)
            if len(pcm) == expected and not released.is_set():
                invalid.set_result("Held capture reached its sample limit without release.")
    return bytes(pcm)


def _validate_held(released: object, maximum: object, device: object, started: object, finishing: object) -> None:
    if (
        type(released) is not asyncio.Event
        or type(maximum) is not int
        or not 1 <= maximum <= MAX_CAPTURE_SECONDS
        or type(device) is not str
        or device not in {"default", "pulse"}
        or (started is not None and not callable(started))
        or (finishing is not None and not callable(finishing))
    ):
        msg = "Held capture requires a release event, 1-15 whole seconds and a supported local device."
        raise ValueError(msg)


async def _finish_held(
    process: asyncio.subprocess.Process,
    reading: asyncio.Task[bytes],
    invalid: asyncio.Future[str],
    on_finishing: Callable[[], None] | None,
) -> bytes:
    retirement_started = False
    try:
        if on_finishing is not None:
            try:
                on_finishing()
            except Exception:  # noqa: BLE001 - indication cannot bypass owned retirement
                msg = "Recorder finish indication failed."
                raise VoiceCaptureError(msg) from None
        retirement_started = True
        retirement = await _settle_retirement(process, initial_signal=signal.SIGINT)
        async with asyncio.timeout(2):
            pcm = await reading
        status = await process.wait()
        if invalid.done():
            raise VoiceCaptureError(invalid.result())
        if (
            not retirement.signal_sent
            or retirement.forced
            or status != 1
            or len(pcm) < MIN_HELD_FRAMES * 2
            or len(pcm) % 2
        ):
            msg = "Recorder failed or returned an unusable held utterance."
            raise VoiceCaptureError(msg)
        return _wave(pcm)
    finally:
        if not retirement_started:
            await _settle_retirement(process)


async def capture_held_utterance(
    *,
    released: asyncio.Event,
    max_seconds: int,
    device: Literal["default", "pulse"] = "default",
    on_started: Callable[[], None] | None = None,
    on_finishing: Callable[[], None] | None = None,
) -> bytes:
    """Return released, bounded PCM only after the recorder group is proved retired.

    SIGINT exit status 1 is the pinned arecord 1.2.16 early-finish observation;
    that status is accepted only after an intentional delivered signal. Neither
    a duration/sample guard nor cancellation constitutes a valid release.
    """
    _validate_held(released, max_seconds, device, on_started, on_finishing)
    if released.is_set():
        msg = "Hold released before recorder launch."
        raise VoiceCaptureError(msg)
    process = await _launch_recorder(frames=max_seconds * SAMPLE_RATE, device=device)
    reading: asyncio.Task[bytes] | None = None
    release_wait: asyncio.Task[bool] | None = None
    retirement_started = False
    try:
        if process.stdout is None:
            msg = "Recorder has no bounded output channel."
            raise VoiceCaptureError(msg)
        released_during_launch = released.is_set()
        invalid: asyncio.Future[str] = asyncio.get_running_loop().create_future()
        reading = asyncio.create_task(
            _drain_held(
                process.stdout,
                expected=max_seconds * SAMPLE_RATE * 2,
                released=released,
                invalid=invalid,
                on_started=None if released_during_launch else on_started,
            )
        )
        if released_during_launch:
            msg = "Hold released during recorder launch; capture discarded."
            raise VoiceCaptureError(msg)
        release_wait = asyncio.create_task(released.wait())
        async with asyncio.timeout(max_seconds):
            done, _ = await asyncio.wait((reading, release_wait, invalid), return_when=asyncio.FIRST_COMPLETED)
            if invalid in done:
                raise VoiceCaptureError(invalid.result())
            if reading in done or process.returncode is not None:
                msg = "Recorder ended before an intentional held finish."
                raise VoiceCaptureError(msg)
        retirement_started = True
        return await _finish_held(process, reading, invalid, on_finishing)
    except (OSError, RuntimeError, TimeoutError) as error:
        if isinstance(error, VoiceCaptureError):
            raise
        msg = "Recorder failed before completing the held utterance."
        raise VoiceCaptureError(msg) from None
    finally:
        try:
            if not retirement_started:
                await _settle_retirement(process)
        finally:
            pending = tuple(task for task in (reading, release_wait) if task is not None)
            for task in pending:
                task.cancel()
            joined: list[Awaitable[object]] = list(pending)
            await complete_under_cancellation(asyncio.gather(*joined, return_exceptions=True))
