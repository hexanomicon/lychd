from __future__ import annotations

import asyncio
import io
import json
import os
import struct
import sys
import tempfile
import time
from argparse import Namespace
from collections.abc import Coroutine, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from scripts import companion_lab
from scripts.voice_probe import PrivateWorkspace

from lychd.compositions.blockworld.companion import (
    BridgeState,
    CompanionReason,
    CompanionRequest,
    CompanionResult,
    CompanionService,
)
from lychd.compositions.blockworld.companion_intent import CompanionInstruction, CompanionIntentProfile
from lychd.domain.speech_probe import LocalSpeechProfile, SpeechModel, SpeechProbeError, SpeechProfile, content_digest
from lychd.system.services import voice_capture
from lychd.system.services.companion_session import CompanionSession, LocalCompanionRunner, SessionResult
from lychd.system.services.speech_probe import SpeechProbe
from lychd.system.services.voice_playback import VoicePlaybackUnsettled
from tests.integration.test_companion import FakeBridge, policy
from tests.unit.domain.test_speech_probe import profile_v2


def wav() -> bytes:
    return (
        struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 52, b"WAVE", b"fmt ", 16, 1, 1, 16000, 32000, 2, 16, b"data", 16)
        + b"\x00" * 16
    )


def speech(transport: httpx.MockTransport | None = None) -> SpeechProbe:
    return SpeechProbe(
        SpeechProfile(
            endpoint="http://127.0.0.1:18183",
            runtime_revision="a" * 40,
            backend="cpu",
            device="host",
            transcriber=SpeechModel(
                model="test-stt",
                family="parakeet-tdt-0.6b-v3",
                digest="sha256:" + "b" * 64,
                languages=("sk", "cs", "en"),
                license="test",
            ),
            synthesizer=SpeechModel(
                model="test-tts",
                family="supertonic-3",
                digest="sha256:" + "c" * 64,
                languages=("sk", "cs", "en"),
                license="test",
            ),
            transport_timeout_seconds=1.0,
            total_timeout_seconds=2.0,
            max_response_bytes=65536,
            max_text_chars=200,
        ),
        transport=transport,
    )


class ConsoleSession:
    def __init__(self) -> None:
        self.generation = 0
        self.stop_failed = False
        self.enqueued: list[Any] = []
        self.observation: BridgeState | None = None

    def capture_generation(self) -> int:
        return self.generation

    def enqueue(
        self, request: CompanionRequest | CompanionInstruction, *, captured_generation: int | None = None
    ) -> asyncio.Future[SessionResult]:
        del captured_generation
        self.enqueued.append(request)
        result: asyncio.Future[SessionResult] = asyncio.get_running_loop().create_future()
        applied = CompanionResult(
            request_id=request.request_id, kind="applied", detail="controller started", observation=self.observation
        )
        result.set_result(SessionResult(request.request_id, str(uuid4()), "applied", "controller started", applied))
        return result

    def stop(self) -> Any:
        self.generation += 1

        async def settle() -> CompanionResult:
            if self.stop_failed:
                msg = "stop unconfirmed"
                raise RuntimeError(msg)
            return CompanionResult(request_id=str(uuid4()), kind="applied", detail="stop barrier")

        return settle()


@pytest.fixture
def files() -> Iterator[PrivateWorkspace]:
    with tempfile.TemporaryDirectory(prefix="lychd-companion-cli-") as name:
        yield PrivateWorkspace(Path(name), (Path(__file__).resolve().parents[3],))


class ConsolePipe:
    def __init__(self, writer: int) -> None:
        self.writer: int | None = writer
        self.reads: asyncio.Queue[bytes] = asyncio.Queue()

    def send(self, value: bytes) -> None:
        assert self.writer is not None
        os.write(self.writer, value)

    def eof(self) -> None:
        if self.writer is not None:
            os.close(self.writer)
            self.writer = None

    async def read(self) -> bytes:
        return await asyncio.wait_for(self.reads.get(), 2)


@pytest.fixture
def console_pipe(monkeypatch: pytest.MonkeyPatch) -> Iterator[ConsolePipe]:
    reader, writer = os.pipe()
    pipe = ConsolePipe(writer)
    stream = io.TextIOWrapper(os.fdopen(reader, "rb", buffering=0), encoding="utf-8")
    original_read = os.read

    def observed_read(fd: int, size: int) -> bytes:
        value = original_read(fd, size)
        if fd == reader:
            pipe.reads.put_nowait(value)
        return value

    monkeypatch.setattr(sys, "stdin", stream)
    monkeypatch.setattr(os, "read", observed_read)
    try:
        yield pipe
    finally:
        pipe.eof()
        stream.close()


@pytest.mark.parametrize(
    "line", ["state", ":record 1", ":wav /tmp/unused.wav", ":target 00000000-0000-4000-8000-000000000000"]
)
@pytest.mark.asyncio
async def test_console_refuses_input_read_during_stop_and_accepts_fresh_input(
    files: PrivateWorkspace, console_pipe: ConsolePipe, monkeypatch: pytest.MonkeyPatch, line: str
) -> None:
    entered, release, refused, admitted = (asyncio.Event() for _ in range(4))

    class BlockedStop(ConsoleSession):
        def stop(self) -> Any:
            settlement = super().stop()

            async def settle() -> CompanionResult:
                entered.set()
                await release.wait()
                return await settlement

            return settle()

        def enqueue(self, request: Any, **kwargs: Any) -> asyncio.Future[SessionResult]:
            result = super().enqueue(request, **kwargs)
            admitted.set()
            return result

    notices: list[dict[str, Any]] = []

    def message(value: dict[str, Any]) -> None:
        notices.append(value)
        if value.get("kind") == "refused":
            refused.set()

    async def no_microphone(**_: Any) -> bytes:
        return wav()

    monkeypatch.setattr(companion_lab, "_message", message)
    monkeypatch.setattr(companion_lab, "capture_utterance", no_microphone)
    state = BlockedStop()
    console = companion_lab.CompanionConsole(
        files,
        cast("CompanionSession", state),
        speech=speech(httpx.MockTransport(lambda _: httpx.Response(200, json={"text": "state"}))),
    )
    task = asyncio.create_task(console.run())
    try:
        await asyncio.sleep(0)
        console_pipe.send(b"stop\n")
        await asyncio.wait_for(entered.wait(), 2)
        assert await console_pipe.read() == b"stop\n"
        console_pipe.send(line.encode() + b"\n")
        assert await console_pipe.read() == line.encode() + b"\n"
        release.set()
        await asyncio.wait_for(refused.wait(), 2)
        assert not state.enqueued
        assert console.voice_task is None
        assert console.target_id is None
        assert all("run_id" not in value for value in notices if value.get("kind") == "refused")
        console_pipe.send(b"state\n")
        await asyncio.wait_for(admitted.wait(), 2)
        assert len(state.enqueued) == 1
        assert state.enqueued[0].generation == 1
        console_pipe.eof()
        await asyncio.wait_for(task, 2)
    finally:
        release.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_same_read_stop_suffix_and_partial_pre_stop_line_keep_their_epoch(
    files: PrivateWorkspace, console_pipe: ConsolePipe
) -> None:
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(files, cast("CompanionSession", state))
    lines = companion_lab.console_lines(console._capture_line)  # pyright: ignore[reportPrivateUsage]
    pending = asyncio.create_task(anext(lines))
    try:
        await asyncio.sleep(0)
        console_pipe.send(b"stop\nstate\nsta")
        stop, _ = await asyncio.wait_for(pending, 2)
        assert stop == "stop"
        assert await console_pipe.read() == b"stop\nstate\nsta"
        await console.stop()
        same_read, original = await anext(lines)
        with pytest.raises(ValueError, match="predates stop"):
            console._handle_line(same_read, original)  # pyright: ignore[reportPrivateUsage]
        pending = asyncio.create_task(anext(lines))
        console_pipe.send(b"te\n")
        partial, original = await asyncio.wait_for(pending, 2)
        assert original.generation == 0
        with pytest.raises(ValueError, match="predates stop"):
            console._handle_line(partial, original)  # pyright: ignore[reportPrivateUsage]
        assert not state.enqueued
    finally:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await lines.aclose()


@pytest.mark.parametrize("line", [b"state", b":record 1"])
@pytest.mark.asyncio
async def test_line_deadline_starts_at_first_observed_bytes_and_is_not_renewed(
    files: PrivateWorkspace, console_pipe: ConsolePipe, monkeypatch: pytest.MonkeyPatch, line: bytes
) -> None:
    now = [time.time()]
    monkeypatch.setattr(companion_lab, "time", SimpleNamespace(time=lambda: now[0], monotonic=time.monotonic))
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", state), speech=speech(), instruction_timeout_s=1
    )
    lines = companion_lab.console_lines(console._capture_line)  # pyright: ignore[reportPrivateUsage]
    pending = asyncio.create_task(anext(lines))
    try:
        await asyncio.sleep(0)
        console_pipe.send(line[:2])
        assert await console_pipe.read() == line[:2]
        original_deadline = int((now[0] + 1) * 1000)
        now[0] += 2
        console_pipe.send(line[2:] + b"\n")
        text, stamp = await asyncio.wait_for(pending, 2)
        assert stamp.expires_at_ms == original_deadline
        with pytest.raises(ValueError, match="expired"):
            console._handle_line(text, stamp)  # pyright: ignore[reportPrivateUsage]
        assert console.voice_task is None
        assert not state.enqueued
    finally:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await lines.aclose()


@pytest.mark.asyncio
async def test_reader_eof_preserves_full_queue_and_refuses_unterminated_input(
    console_pipe: ConsolePipe, capsys: pytest.CaptureFixture[str]
) -> None:
    lines = companion_lab.console_lines(lambda: 0)
    pending = asyncio.create_task(anext(lines))
    try:
        await asyncio.sleep(0)
        console_pipe.send(b"first\n")
        assert await asyncio.wait_for(pending, 2) == ("first", 0)
        assert await console_pipe.read() == b"first\n"
        # The generator now remains suspended at yield: EOF sees all eight
        # subsequent frames queued, with no pending consumer to remove one.
        console_pipe.send(b"state\n" * 8 + b"say incomplete")
        assert await console_pipe.read() == b"state\n" * 8 + b"say incomplete"
        console_pipe.eof()
        assert await console_pipe.read() == b""
        rest = [item async for item in lines]
        assert rest == [("state", 0)] * 8
        assert "Incomplete console line" in capsys.readouterr().out
    finally:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await lines.aclose()


@pytest.mark.asyncio
async def test_expired_recording_waiting_for_audio_never_arms_microphone(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = [time.time()]
    monkeypatch.setattr(companion_lab, "time", SimpleNamespace(time=lambda: now[0], monotonic=time.monotonic))
    captures: list[int] = []

    async def capture(**_: Any) -> bytes:
        captures.append(1)
        return wav()

    monkeypatch.setattr(companion_lab, "capture_utterance", capture)
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", state), speech=speech(), instruction_timeout_s=1
    )
    await console._capture_lock.acquire()  # pyright: ignore[reportPrivateUsage]
    recording = console.begin_voice()
    await asyncio.sleep(0)
    now[0] += 2
    console._capture_lock.release()  # pyright: ignore[reportPrivateUsage]
    await recording
    assert not captures
    assert not state.enqueued
    receipt = json.loads(next(files.root.glob("*-voice.json")).read_bytes())
    assert receipt["kind"] == "refused"


@pytest.mark.asyncio
async def test_target_controls_bind_in_order_inside_one_reader_callback(
    files: PrivateWorkspace, console_pipe: ConsolePipe
) -> None:
    state = ConsoleSession()
    first, second = str(uuid4()), str(uuid4())
    console = companion_lab.CompanionConsole(files, cast("CompanionSession", state), target_id=first)
    lines = companion_lab.console_lines(console._capture_line)  # pyright: ignore[reportPrivateUsage]
    pending = asyncio.create_task(anext(lines))
    try:
        await asyncio.sleep(0)
        console_pipe.send(f"follow me\n:target {second}\nfollow me\n".encode())
        for line, stamp in [await pending, await anext(lines), await anext(lines)]:
            console._handle_line(line, stamp)  # pyright: ignore[reportPrivateUsage]
        assert [request.action.target_id for request in state.enqueued] == [first, second]
        await asyncio.gather(*console.replies)
    finally:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await lines.aclose()


@pytest.mark.asyncio
async def test_overlapping_stops_keep_input_closed_until_both_console_settlements_finish(
    files: PrivateWorkspace,
) -> None:
    entered: asyncio.Queue[int] = asyncio.Queue()
    releases = [asyncio.Event(), asyncio.Event()]

    class OverlappingStop(ConsoleSession):
        def stop(self) -> Any:
            index = self.generation
            settlement = super().stop()

            async def settle() -> CompanionResult:
                entered.put_nowait(index)
                await releases[index].wait()
                return await settlement

            return settle()

    state = OverlappingStop()
    console = companion_lab.CompanionConsole(files, cast("CompanionSession", state), speech=speech())
    first = asyncio.create_task(console.stop())
    assert await asyncio.wait_for(entered.get(), 2) == 0
    second = asyncio.create_task(console.stop())
    assert await asyncio.wait_for(entered.get(), 2) == 1
    try:
        releases[0].set()
        await first
        old = console._capture_line()  # pyright: ignore[reportPrivateUsage]
        assert not old.eligible
        with pytest.raises(ValueError, match="settle"):
            console.begin_voice()
        releases[1].set()
        await second
        with pytest.raises(ValueError, match="unsettled"):
            console._handle_line("state", old)  # pyright: ignore[reportPrivateUsage]
        fresh = await console.submit("state")
        assert fresh.kind == "applied"
        await asyncio.gather(*console.replies)
    finally:
        for release in releases:
            release.set()
        await asyncio.gather(first, second, return_exceptions=True)


@pytest.mark.asyncio
async def test_settled_recorder_failure_waits_for_fresh_gesture_then_transcribes(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    recorders: list[SimpleNamespace] = []
    for pcm in (b"\0" * 100, b"\0" * 32_000):
        stream = asyncio.StreamReader()
        stream.feed_data(pcm)
        stream.feed_eof()
        recorders.append(SimpleNamespace(pid=876543, stdout=stream, wait=AsyncMock(return_value=0)))
    launch = AsyncMock(side_effect=recorders)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)

    def no_owned_group(_pid: int) -> bool:
        return False

    monkeypatch.setattr(voice_capture, "_group_exists", no_owned_group)
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"text": "stav"})

    state = ConsoleSession()
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", state), speech=speech(httpx.MockTransport(handler)), language="sk"
    )
    await console.begin_voice(seconds=1)
    await asyncio.sleep(0)
    assert launch.await_count == 1
    assert calls == []
    assert state.enqueued == []
    failed = json.loads(next(files.root.glob("*-voice.json")).read_bytes())
    assert failed["kind"] == "refused"
    assert not list(files.root.glob("*-source.wav"))
    await console.begin_voice(seconds=1)
    await asyncio.gather(*console.replies)
    assert launch.await_count == 2
    assert calls == ["/v1/audio/transcriptions"]
    assert len(state.enqueued) == 1
    assert state.enqueued[0].request_id != failed["request_id"]
    assert state.enqueued[0].action.kind == "state"
    output = capsys.readouterr().out
    assert output.count('"capture": "off"') == 2
    assert '"capture": "unknown"' not in output


@pytest.mark.parametrize("error_type", [TimeoutError, RuntimeError, voice_capture.VoiceCaptureUnsettled])
@pytest.mark.asyncio
async def test_unsettled_capture_latches_audio_and_does_not_report_off(
    files: PrivateWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error_type: type[Exception],
) -> None:
    async def failed_capture(**_: Any) -> bytes:
        msg = "owned recorder retirement unconfirmed"
        raise error_type(msg)

    monkeypatch.setattr(companion_lab, "capture_utterance", failed_capture)
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(files, cast("CompanionSession", state), speech=speech(), language="sk")
    await console.begin_voice()
    output = capsys.readouterr().out
    assert '"capture": "unknown"' in output
    assert '"capture": "off"' not in output
    with pytest.raises(ValueError, match=r"profile|settle"):
        console.begin_voice()
    assert not state.enqueued


@pytest.mark.asyncio
async def test_waiting_reply_is_blocked_after_unsettled_capture(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered, release = asyncio.Event(), asyncio.Event()

    async def capture(**_: Any) -> bytes:
        entered.set()
        await release.wait()
        msg = "private recorder details"
        raise voice_capture.VoiceCaptureUnsettled(msg)

    monkeypatch.setattr(companion_lab, "capture_utterance", capture)
    client = speech(httpx.MockTransport(lambda _: pytest.fail("Unsettled capture cannot reach synthesis.")))
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", ConsoleSession()), speech=client, reply_language="sk", play_replies=True
    )
    recording = console.begin_voice()
    try:
        await asyncio.wait_for(entered.wait(), 1)
        outcome = await console.submit("stav")
        replies = tuple(console.replies)
        await asyncio.sleep(0)
    finally:
        release.set()
    await recording
    await asyncio.gather(*replies)
    assert outcome.kind == "applied"
    receipt = json.loads((files.root / f"{outcome.request_id}-reply-evidence.json").read_bytes())
    assert receipt["reply_status"] == "not_attempted"
    assert receipt["playback"] == "not_attempted"
    assert not list(files.root.glob("*-reply.wav"))


@pytest.mark.asyncio
async def test_waiting_capture_is_blocked_after_unsettled_playback(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered, release = asyncio.Event(), asyncio.Event()
    captures: list[int] = []

    async def handler(_: httpx.Request) -> httpx.Response:
        entered.set()
        await release.wait()
        return httpx.Response(200, content=wav(), headers={"content-type": "audio/wav"})

    async def unsettled(_: bytes) -> None:
        msg = "owned playback unconfirmed"
        raise VoicePlaybackUnsettled(msg)

    async def capture(**_: Any) -> bytes:
        captures.append(1)
        return wav()

    monkeypatch.setattr(companion_lab, "play_reply", unsettled)
    monkeypatch.setattr(companion_lab, "capture_utterance", capture)
    console = companion_lab.CompanionConsole(
        files,
        cast("CompanionSession", ConsoleSession()),
        speech=speech(httpx.MockTransport(handler)),
        language="sk",
        reply_language="sk",
        play_replies=True,
    )
    outcome = await console.submit("stav")
    await entered.wait()
    reply = next(iter(console.replies))
    recording = console.begin_voice()
    release.set()
    await reply
    await recording
    assert captures == []
    receipt = json.loads((files.root / f"{outcome.request_id}-reply-evidence.json").read_bytes())
    assert receipt["request_id"] == outcome.request_id
    assert receipt["run_id"] == outcome.run_id
    assert receipt["playback"] == "settlement_unknown"
    assert receipt["reply_failure"] == "playback_unsettled"
    assert receipt["human_hearing"] == "unconfirmed"
    with pytest.raises(ValueError, match=r"profile|settle"):
        console.begin_voice()


@pytest.mark.asyncio
async def test_stop_joins_owned_audio_even_when_game_stop_fails(files: PrivateWorkspace) -> None:
    retired = asyncio.Event()

    async def owned_audio() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            retired.set()

    state = ConsoleSession()
    state.stop_failed = True
    console = companion_lab.CompanionConsole(files, cast("CompanionSession", state))
    console.voice_task = asyncio.create_task(owned_audio())
    await asyncio.sleep(0)
    with pytest.raises(RuntimeError, match="unconfirmed"):
        await console.stop()
    assert state.generation == 1
    assert retired.is_set()


@pytest.mark.asyncio
async def test_oversized_line_suffix_cannot_become_a_new_instruction(monkeypatch: pytest.MonkeyPatch) -> None:
    read_fd, write_fd = os.pipe()
    original_read = os.read
    received = asyncio.Event()
    stream = io.TextIOWrapper(os.fdopen(read_fd, "rb", buffering=0), encoding="utf-8")

    def observed_read(fd: int, size: int) -> bytes:
        value = original_read(fd, size)
        if fd == read_fd:
            received.set()
        return value

    monkeypatch.setattr(sys, "stdin", stream)
    monkeypatch.setattr(os, "read", observed_read)
    lines = companion_lab.console_lines(lambda: 0)
    pending = asyncio.create_task(anext(lines))
    try:
        await asyncio.sleep(0)
        os.write(write_fd, b"x" * (companion_lab.MAX_CONSOLE_BYTES + 1))
        await asyncio.wait_for(received.wait(), 2)
        os.write(write_fd, b"say suffix\nstate\n")
        assert await asyncio.wait_for(pending, 2) == ("state", 0)
    finally:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await lines.aclose()
        os.close(write_fd)
        stream.close()


@pytest.mark.asyncio
async def test_punctuated_stop_bypasses_full_console_input(monkeypatch: pytest.MonkeyPatch) -> None:
    read_fd, write_fd = os.pipe()
    stream = io.TextIOWrapper(os.fdopen(read_fd, "rb", buffering=0), encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", stream)
    lines = companion_lab.console_lines(lambda: 0)
    pending = asyncio.create_task(anext(lines))
    try:
        await asyncio.sleep(0)
        os.write(write_fd, b"say queued\n" * 8 + b"stop!\n")
        assert await asyncio.wait_for(pending, 2) == ("stop!", 0)
    finally:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await lines.aclose()
        os.close(write_fd)
        stream.close()


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_cancelled_action_reply_preserves_uncertainty(language: str) -> None:
    assert companion_lab.reply_text("cancelled", language) == companion_lab.reply_text("unknown", language)


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize("reason", ["cancelled_before_execution", None])
@pytest.mark.asyncio
async def test_console_speaks_correlated_pre_run_cause_and_keeps_active_cancellation_uncertain(
    files: PrivateWorkspace,
    capsys: pytest.CaptureFixture[str],
    language: str,
    reason: CompanionReason | None,
) -> None:
    sent: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(200, content=wav(), headers={"content-type": "audio/wav"})

    class CancelledSession(ConsoleSession):
        def enqueue(
            self, request: CompanionRequest | CompanionInstruction, *, captured_generation: int | None = None
        ) -> asyncio.Future[SessionResult]:
            del captured_generation
            self.enqueued.append(request)
            outcome = SessionResult(
                request.request_id,
                None if reason is not None else str(uuid4()),
                "cancelled",
                "private foreign diagnostic",
                reason=reason,
            )
            future: asyncio.Future[SessionResult] = asyncio.get_running_loop().create_future()
            future.set_result(outcome)
            return future

    state = CancelledSession()
    console = companion_lab.CompanionConsole(
        files,
        cast("CompanionSession", state),
        speech=speech(httpx.MockTransport(handler)),
        language=language,
        reply_language=language,
    )
    outcome = await console.submit("state")
    await asyncio.gather(*console.replies)
    report = next(json.loads(line) for line in capsys.readouterr().out.splitlines() if '"feedback"' in line)
    assert report["request_id"] == outcome.request_id
    assert report["run_id"] == outcome.run_id
    assert report["result"] is None
    assert report["reason"] == reason
    assert len(sent) == 1
    spoken = sent[0]["input"]
    assert spoken == report["feedback"]["text"]
    assert "private" not in spoken
    assert (spoken == companion_lab.reply_text("unknown", language)) is (reason is None)


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize("fail_synthesis", [False, True])
@pytest.mark.asyncio
async def test_state_feedback_is_the_synthesized_answer_and_speech_failure_never_retries_game(
    files: PrivateWorkspace,
    capsys: pytest.CaptureFixture[str],
    language: str,
    *,
    fail_synthesis: bool,
) -> None:
    sent: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        if fail_synthesis:
            msg = "unconfirmed speech response"
            raise httpx.ReadError(msg, request=request)
        return httpx.Response(200, content=wav(), headers={"content-type": "audio/wav"})

    state = ConsoleSession()
    state.observation = BridgeState.model_validate(
        {
            "protocol": 1,
            "boot_id": str(uuid4()),
            "generation": 0,
            "actor_id": str(uuid4()),
            "mode": "idle",
            "position": [3.0, 64.0, -1.0],
            "yaw": 0.0,
            "pitch": 0.0,
            "queue_depth": 0,
            "active_action_id": None,
            "players": [],
            "timestamp_ms": int(time.time() * 1000),
        }
    )
    console = companion_lab.CompanionConsole(
        files,
        cast("CompanionSession", state),
        speech=speech(httpx.MockTransport(handler)),
        language=language,
        reply_language=language,
    )
    result = await console.submit("state")
    await asyncio.gather(*console.replies)
    documents = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    report = next(document for document in documents if "feedback" in document)
    assert report["request_id"] == result.request_id
    assert len(state.enqueued) == 1
    assert result.kind == "applied"
    assert len(sent) == 1
    assert sent[0]["input"] == report["feedback"]["text"]
    assert "X 3.0" in sent[0]["input"]
    assert sent[0]["language"] == language
    assert len(list(files.root.glob("*-reply.wav"))) == (0 if fail_synthesis else 1)
    assert any(document.get("kind") == "speech_failed" for document in documents) is fail_synthesis
    receipt = json.loads((files.root / f"{result.request_id}-reply-evidence.json").read_bytes())
    assert receipt["request_id"] == result.request_id
    assert receipt["run_id"] == result.run_id
    assert receipt["game_status"] == "known"
    assert receipt["kind"] == result.kind == "applied"
    assert receipt["reply_status"] == ("failed" if fail_synthesis else "generated")
    assert receipt.get("reply_failure") == ("synthesis_failed" if fail_synthesis else None)
    assert receipt["playback"] == "not_attempted"


def _lab_options(files: PrivateWorkspace, pinned: LocalSpeechProfile) -> Namespace:
    bridge_path, speech_path = files.root / "bridge.json", files.root / "speech.json"
    files.write_new(
        bridge_path,
        json.dumps({"endpoint": "http://127.0.0.1:18184", "token": "a" * 64, "actor_id": str(uuid4())}).encode(),
    )
    files.write_new(speech_path, pinned.model_dump_json().encode())
    return companion_lab.parser().parse_args(
        [
            "--workspace",
            str(files.root),
            "--checkout-root",
            str(Path(__file__).resolve().parents[3]),
            "--bridge-profile",
            str(bridge_path),
            "--speech-profile",
            str(speech_path),
            "--language",
            "sk",
            "--bounds",
            "-24",
            "-64",
            "-24",
            "24",
            "320",
            "24",
        ]
    )


@pytest.mark.parametrize("version", ["v1", "v2"])
@pytest.mark.asyncio
async def test_versioned_loader_checks_cpu_host_before_opening_game(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    pinned = speech().profile if version == "v1" else profile_v2()
    options = _lab_options(files, pinned)

    class SelectedProfileError(Exception):
        pass

    def selected(actual: LocalSpeechProfile) -> SpeechProbe:
        assert actual.digest == pinned.digest
        assert (actual.transcriber_binding.backend, actual.transcriber_binding.device) == ("cpu", "host")
        assert (actual.synthesizer_binding.backend, actual.synthesizer_binding.device) == ("cpu", "host")
        raise SelectedProfileError

    monkeypatch.setattr(companion_lab, "SpeechProbe", selected)
    with pytest.raises(SelectedProfileError):
        await companion_lab.run(options)


@pytest.mark.parametrize("role", ["transcriber_binding", "synthesizer_binding"])
@pytest.mark.parametrize(("field", "value"), [("backend", "cuda"), ("device", "cuda:0")])
@pytest.mark.asyncio
async def test_cpu_host_guard_refuses_each_accelerated_operation_before_probe_construction(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch, role: str, field: str, value: str
) -> None:
    pinned = profile_v2()
    options = _lab_options(
        files, pinned.model_copy(update={role: getattr(pinned, role).model_copy(update={field: value})})
    )

    def forbidden(_actual: LocalSpeechProfile) -> SpeechProbe:
        pytest.fail("An accelerated operation passed the companion CPU/host guard")

    monkeypatch.setattr(companion_lab, "SpeechProbe", forbidden)
    with pytest.raises(ValueError, match="CPU/host"):
        await companion_lab.run(options)


def test_whisper_console_requires_language_before_capture_or_game_control(files: PrivateWorkspace) -> None:
    client = SpeechProbe(profile_v2(), transport=httpx.MockTransport(lambda _: pytest.fail("Unexpected HTTP")))
    state = ConsoleSession()
    with pytest.raises(SpeechProbeError, match="explicit"):
        companion_lab.CompanionConsole(files, cast("CompanionSession", state), speech=client)
    assert state.enqueued == []


@pytest.mark.parametrize(("language", "words", "kind"), [("sk", " Čakaj!\n", "idle"), ("en", " State\r\n", "state")])
@pytest.mark.asyncio
async def test_whisper_voice_framing_preserves_original_observation_and_command_transcript(
    files: PrivateWorkspace, language: str, words: str, kind: str
) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"text": words})

    client = SpeechProbe(profile_v2(), transport=httpx.MockTransport(handler))
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(files, cast("CompanionSession", state), speech=client, language=language)
    source = files.root / "source.wav"
    files.write_new(source, wav())
    await console.begin_voice(source)
    await asyncio.gather(*console.replies)
    assert len(calls) == 1
    assert len(state.enqueued) == 1
    assert state.enqueued[0].action.kind == kind
    assert state.enqueued[0].source == "transcript"
    assert state.enqueued[0].transcript == words
    observations = list(files.root.glob("*-transcript.json"))
    assert len(observations) == 1
    assert json.loads(observations[0].read_bytes())["text"] == words


@pytest.mark.parametrize(
    "words",
    [
        "stav\nsay hi",
        "state\tthen idle",
        "\x00state\n",
        "state\u0085",
        " Poved zahoj.\n",
        " Řekňa hoj.\n",
        "(Zvuk výstavl)",
    ],
)
def test_transcript_framing_never_repairs_embedded_controls_or_unsupported_words(
    files: PrivateWorkspace, words: str
) -> None:
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(files, cast("CompanionSession", state))
    with pytest.raises(ValueError, match=r"Instruction|Unsupported"):
        console.submit(words, source="transcript")
    assert state.enqueued == []


@pytest.mark.parametrize("words", [" State\n", "stav\r\n", "state\t"])
def test_text_source_keeps_strict_control_character_refusal(files: PrivateWorkspace, words: str) -> None:
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(files, cast("CompanionSession", state))
    with pytest.raises(ValueError, match="Instruction"):
        console.submit(words)
    assert state.enqueued == []


@pytest.mark.parametrize("phase", ["before_task", "capture", "transcription"])
@pytest.mark.parametrize("initial_target", ["bound", "absent"])
@pytest.mark.asyncio
async def test_voice_target_and_request_identity_are_bound_before_async_work(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch, phase: str, initial_target: str
) -> None:
    target_a, target_b = str(uuid4()), str(uuid4())
    entered, release = asyncio.Event(), asyncio.Event()
    words = " Follow me\n"

    async def capture(**_: Any) -> bytes:
        if phase == "capture":
            entered.set()
            await release.wait()
        return wav()

    async def handler(_: httpx.Request) -> httpx.Response:
        if phase == "transcription":
            entered.set()
            await release.wait()
        return httpx.Response(200, json={"text": words})

    monkeypatch.setattr(companion_lab, "capture_utterance", capture)
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(
        files,
        cast("CompanionSession", state),
        speech=speech(httpx.MockTransport(handler)),
        language="en",
        target_id=target_a if initial_target == "bound" else None,
    )
    utterance = console.begin_voice()
    if phase != "before_task":
        await asyncio.wait_for(entered.wait(), 2)
    console.target_id = target_b
    release.set()
    await utterance
    await asyncio.gather(*console.replies)
    if initial_target == "bound":
        assert len(state.enqueued) == 1
        assert state.enqueued[0].action.target_id == target_a
    else:
        assert state.enqueued == []
    records = list(files.root.glob("*-voice.json"))
    assert len(records) == 1
    record = json.loads(records[0].read_bytes())
    identity = record["request_id"]
    assert records[0].name == f"{identity}-voice.json"
    assert (files.root / f"{identity}-source.wav").read_bytes() == wav()
    transcript = json.loads((files.root / f"{identity}-transcript.json").read_bytes())
    assert transcript["source"]["artifact_id"] == identity
    assert transcript["text"] == words
    assert record["transcript"] == words
    assert "run_id" not in record
    if initial_target == "bound":
        assert state.enqueued[0].request_id == identity
        assert state.enqueued[0].transcript == words
    await console.begin_voice()
    await asyncio.gather(*console.replies)
    assert state.enqueued[-1].action.target_id == target_b
    assert state.enqueued[-1].request_id != identity


@pytest.mark.asyncio
async def test_voice_allocates_identity_synchronously_and_text_captures_current_target(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    allocated: list[str] = []

    def allocate() -> Any:
        identity = uuid4()
        allocated.append(str(identity))
        return identity

    monkeypatch.setattr(companion_lab, "uuid4", allocate)
    target_a, target_b = str(uuid4()), str(uuid4())
    state = ConsoleSession()
    client = speech(httpx.MockTransport(lambda _: httpx.Response(200, json={"text": "state"})))
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", state), speech=client, language="en", target_id=target_a
    )
    source = files.root / "supplied.wav"
    files.write_new(source, wav())
    task = console.begin_voice(source)
    assert len(allocated) == 1
    captured_id = allocated[0]
    console.target_id = target_b
    typed_b = await console.submit("follow")
    console.target_id = target_a
    typed_a = await console.submit("follow")
    await task
    await asyncio.gather(*console.replies)
    assert state.enqueued[0].action.target_id == target_b
    assert state.enqueued[1].action.target_id == target_a
    assert len({captured_id, typed_b.request_id, typed_a.request_id}) == 3
    voice_request = next(request for request in state.enqueued if request.source == "transcript")
    assert voice_request.request_id == captured_id


@pytest.mark.asyncio
async def test_cancelled_transcription_keeps_captured_identity_without_native_run(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered = asyncio.Event()

    async def handler(_: httpx.Request) -> httpx.Response:
        entered.set()
        await asyncio.Event().wait()
        raise AssertionError

    async def capture(**_: Any) -> bytes:
        return wav()

    monkeypatch.setattr(companion_lab, "capture_utterance", capture)
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(
        files,
        cast("CompanionSession", state),
        speech=speech(httpx.MockTransport(handler)),
        language="en",
        target_id=str(uuid4()),
    )
    task = console.begin_voice()
    await asyncio.wait_for(entered.wait(), 2)
    await console.stop()
    assert task.cancelled()
    assert state.generation == 1
    assert state.enqueued == []
    records = list(files.root.glob("*-voice.json"))
    assert len(records) == 1
    record = json.loads(records[0].read_bytes())
    assert records[0].name == f"{record['request_id']}-voice.json"
    assert (files.root / f"{record['request_id']}-source.wav").exists()
    assert record["kind"] == "cancelled_server_inference_unknown"
    assert record["generation"] == 0
    assert "run_id" not in record


@pytest.mark.asyncio
async def test_spoken_stop_records_separate_stop_identity_and_original_voice_identity(files: PrivateWorkspace) -> None:
    state = ConsoleSession()
    client = speech(httpx.MockTransport(lambda _: httpx.Response(200, json={"text": " Stop\n"})))
    console = companion_lab.CompanionConsole(files, cast("CompanionSession", state), speech=client, language="en")
    source = files.root / "supplied.wav"
    files.write_new(source, wav())
    await console.begin_voice(source)
    record = json.loads(next(files.root.glob("*-voice.json")).read_bytes())
    assert record["request_id"] != record["stop_request_id"]
    assert record["transcript"] == " Stop\n"
    assert record["kind"] == "applied"
    assert "run_id" not in record
    assert state.enqueued == []


def intent_profile() -> CompanionIntentProfile:
    return CompanionIntentProfile(base_url="http://127.0.0.1:12345/v1", model_id="fixture-model")


def test_free_form_instructions_require_an_explicit_profile(files: PrivateWorkspace) -> None:
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(files, cast("CompanionSession", state))
    with pytest.raises(ValueError, match="Unsupported"):
        console.submit("Could you wait here please")
    assert state.enqueued == []


@pytest.mark.asyncio
async def test_profile_keeps_exact_commands_on_the_strict_path(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(_text: str) -> str:
        pytest.fail("A strict instruction reached optional interpretation admission")

    monkeypatch.setattr(companion_lab, "validate_raw_instruction", forbidden)
    monkeypatch.setattr(companion_lab.time, "time", lambda: 1_700_000_000.0)
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", state), intent_profile=intent_profile(), instruction_timeout_s=7.25
    )
    await console.submit("state")
    await asyncio.gather(*console.replies)
    request = state.enqueued[0]
    assert isinstance(request, CompanionRequest)
    assert request.action.kind == "state"
    assert request.expires_at_ms == 1_700_000_007_250


@pytest.mark.parametrize("language", [None, "sk", "cs", "en"])
@pytest.mark.asyncio
async def test_profile_admits_original_free_form_input_as_an_envelope(
    files: PrivateWorkspace, language: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(companion_lab.time, "time", lambda: 1_700_000_000.0)
    selected, target = intent_profile(), str(uuid4())
    state = ConsoleSession()
    state.generation = 4
    console = companion_lab.CompanionConsole(
        files,
        cast("CompanionSession", state),
        intent_profile=selected,
        language=language,
        target_id=target,
        instruction_timeout_s=9,
    )
    words = "Could you wait here please"
    result = await console.submit(words)
    await asyncio.gather(*console.replies)
    request = state.enqueued[0]
    assert isinstance(request, CompanionInstruction)
    assert request.request_id == result.request_id
    assert request.original_text == words
    assert request.source == "text"
    assert request.language == (language or "en")
    assert request.profile_digest == selected.digest
    assert request.generation == 4
    assert request.target_id == target
    assert request.expires_at_ms == 1_700_000_009_000
    assert request.source_artifacts == ()


@pytest.mark.parametrize(
    "words",
    [
        "goto 1 2",
        "look nowhere",
        "say",
        "follow",
        "follow somebody",
        "state extra",
        "idle then follow",
        "/help",
        ":target nobody",
        "hi\tthere",
        "x" * 1001,
    ],
)
def test_profile_does_not_reinterpret_malformed_strict_commands_or_unsafe_framing(
    files: PrivateWorkspace, words: str
) -> None:
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(files, cast("CompanionSession", state), intent_profile=intent_profile())
    with pytest.raises(ValueError, match="Instruction"):
        console.submit(words)
    assert state.enqueued == []


@pytest.mark.parametrize("raw", [False, True])
@pytest.mark.parametrize("bound_target", [False, True])
@pytest.mark.asyncio
async def test_voice_expiry_and_material_references_survive_transcription_waiting(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch, *, raw: bool, bound_target: bool
) -> None:
    clock = [1_700_000_000.0]
    monkeypatch.setattr(companion_lab.time, "time", lambda: clock[0])
    entered, release = asyncio.Event(), asyncio.Event()
    words = " Could you wait here please\n" if raw else " State\n"

    async def handler(_: httpx.Request) -> httpx.Response:
        entered.set()
        await release.wait()
        return httpx.Response(200, json={"text": words})

    state = ConsoleSession()
    target = str(uuid4()) if bound_target else None
    console = companion_lab.CompanionConsole(
        files,
        cast("CompanionSession", state),
        speech=speech(httpx.MockTransport(handler)),
        language="en",
        target_id=target,
        intent_profile=intent_profile() if raw else None,
        instruction_timeout_s=9,
    )
    source = files.root / "supplied.wav"
    files.write_new(source, wav())
    task = console.begin_voice(source)
    console.target_id = str(uuid4())
    await asyncio.wait_for(entered.wait(), 2)
    clock[0] += 40
    state.generation = 1
    release.set()
    await task
    await asyncio.gather(*console.replies)
    request = state.enqueued[0]
    assert isinstance(request, CompanionInstruction | CompanionRequest)
    assert request.expires_at_ms == 1_700_000_009_000
    assert request.generation == 0
    if raw:
        assert isinstance(request, CompanionInstruction)
        assert request.target_id == target
        assert request.original_text == words
    else:
        assert isinstance(request, CompanionRequest)
        assert request.transcript == words
    audio, transcript = request.source_artifacts
    assert audio.artifact_id == request.request_id
    assert audio.media_type == "audio/wav"
    assert audio.digest == content_digest(wav())
    transcript_raw = (files.root / f"{request.request_id}-transcript.json").read_bytes()
    assert transcript.media_type == "application/json"
    assert transcript.size == len(transcript_raw)
    assert transcript.digest == content_digest(transcript_raw)
    assert audio.classification == transcript.classification == "private"
    voice = json.loads((files.root / f"{request.request_id}-voice.json").read_bytes())
    assert voice["expires_at_ms"] == request.expires_at_ms


@pytest.mark.parametrize("seconds", [0, 0.99, 60.01, float("nan"), float("inf")])
def test_console_requires_a_finite_instruction_timeout(files: PrivateWorkspace, seconds: float) -> None:
    with pytest.raises(ValueError, match="1-60"):
        companion_lab.CompanionConsole(files, cast("CompanionSession", ConsoleSession()), instruction_timeout_s=seconds)


@pytest.mark.asyncio
async def test_cli_loads_the_opted_in_profile_before_opening_game(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    options = _lab_options(files, speech().profile)
    selected = intent_profile()
    path = files.root / "intent.json"
    files.write_new(path, selected.model_dump_json().encode())
    options.intent_profile = path
    options.instruction_timeout = 11.5

    class SelectedProfileError(Exception):
        pass

    def runner(*_args: Any, intent_profile: CompanionIntentProfile | None) -> None:
        assert intent_profile == selected
        raise SelectedProfileError

    monkeypatch.setattr(companion_lab, "LocalCompanionRunner", runner)
    with pytest.raises(SelectedProfileError):
        await companion_lab.run(options)


def test_console_revalidates_a_copied_intent_profile(files: PrivateWorkspace) -> None:
    poisoned = intent_profile().model_copy(
        update={"base_url": "http://example.invalid:12345/v1", "max_requests": 1000000}
    )
    with pytest.raises(ValueError, match="validation"):
        companion_lab.CompanionConsole(files, cast("CompanionSession", ConsoleSession()), intent_profile=poisoned)


@pytest.mark.parametrize("playback", ["not_attempted", "player_exited", "failed", "settlement_unknown"])
@pytest.mark.asyncio
async def test_reply_receipt_correlates_generation_retained_bytes_and_player_settlement(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], playback: str
) -> None:
    client = speech(
        httpx.MockTransport(lambda _: httpx.Response(200, content=wav(), headers={"content-type": "audio/wav"}))
    )
    synthesize = client.synthesize
    observations: list[bytes] = []

    async def observed(text: str, **kwargs: Any) -> Any:
        observation, content = await synthesize(text, **kwargs)
        observations.append(observation.model_dump_json().encode())
        return observation, content

    async def play(content: bytes) -> str:
        assert content == wav()
        if playback == "failed":
            msg = "private player diagnostic"
            raise companion_lab.VoicePlaybackError(msg)
        if playback == "settlement_unknown":
            msg = "private retirement diagnostic"
            raise VoicePlaybackUnsettled(msg)
        assert playback == "player_exited"
        return playback

    monkeypatch.setattr(client, "synthesize", observed)
    monkeypatch.setattr(companion_lab, "play_reply", play)
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(
        files,
        cast("CompanionSession", state),
        speech=client,
        language="en",
        reply_language="en",
        play_replies=playback != "not_attempted",
    )
    outcome = await console.submit("state")
    await asyncio.gather(*console.replies)
    evidence = json.loads((files.root / f"{outcome.request_id}-reply-evidence.json").read_bytes())
    assert evidence["request_id"] == outcome.request_id
    assert evidence["run_id"] == outcome.run_id
    assert evidence["run_identity"] == "known"
    assert evidence["game_status"] == "known"
    assert evidence["kind"] == outcome.kind == "applied"
    assert evidence["reason"] is None
    assert evidence["reply_status"] == "generated"
    assert evidence["playback"] == playback
    assert evidence["human_hearing"] == "unconfirmed"
    assert files.read(Path(evidence["reply_audio"]), 65536) == wav()
    assert files.read(Path(evidence["synthesis_observation"]), 65536) == observations[0]
    assert Path(evidence["reply_audio"]).name == f"{outcome.request_id}-reply.wav"
    assert Path(evidence["synthesis_observation"]).name == f"{outcome.request_id}-reply.json"
    if playback == "settlement_unknown":
        with pytest.raises(ValueError, match=r"profile|settle"):
            console.begin_voice()
    assert len(state.enqueued) == 1
    messages = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert all("private" not in json.dumps(message) for message in messages)
    assert messages[-1]["request_id"] == outcome.request_id
    assert messages[-1]["run_id"] == outcome.run_id
    assert messages[-1]["evidence_status"] == "recorded"


@pytest.mark.parametrize("native", ["pre_run", "no_action"])
@pytest.mark.asyncio
async def test_reply_receipt_retains_absent_pre_run_and_actual_interpreter_run(
    files: PrivateWorkspace, native: str
) -> None:
    class SelectedSession(ConsoleSession):
        def enqueue(
            self, request: CompanionRequest | CompanionInstruction, *, captured_generation: int | None = None
        ) -> asyncio.Future[SessionResult]:
            del captured_generation
            self.enqueued.append(request)
            future: asyncio.Future[SessionResult] = asyncio.get_running_loop().create_future()
            future.set_result(
                SessionResult(
                    request.request_id,
                    None if native == "pre_run" else str(uuid4()),
                    "cancelled" if native == "pre_run" else "no_action",
                    "private native detail",
                    reason="cancelled_before_execution" if native == "pre_run" else None,
                )
            )
            return future

    state = SelectedSession()
    client = speech(
        httpx.MockTransport(lambda _: httpx.Response(200, content=wav(), headers={"content-type": "audio/wav"}))
    )
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", state), speech=client, language="en", reply_language="en"
    )
    outcome = await console.submit("state")
    await asyncio.gather(*console.replies)
    evidence = json.loads((files.root / f"{outcome.request_id}-reply-evidence.json").read_bytes())
    assert evidence["run_id"] == outcome.run_id
    assert evidence["run_identity"] == ("absent" if native == "pre_run" else "known")
    assert evidence["game_status"] == "known"
    assert evidence["kind"] == outcome.kind
    assert evidence["reason"] == outcome.reason
    assert len(state.enqueued) == 1


@pytest.mark.parametrize("stage", ["before_watcher", "synthesis"])
@pytest.mark.asyncio
async def test_stop_joins_reply_before_entry_or_during_synthesis_without_game_replay(
    files: PrivateWorkspace, stage: str
) -> None:
    entered = asyncio.Event()

    async def handler(_: httpx.Request) -> httpx.Response:
        entered.set()
        await asyncio.Event().wait()
        raise AssertionError

    state = ConsoleSession()
    console = companion_lab.CompanionConsole(
        files,
        cast("CompanionSession", state),
        speech=speech(httpx.MockTransport(handler)),
        language="en",
        reply_language="en",
        play_replies=True,
    )
    outcome = await console.submit("state")
    if stage == "synthesis":
        await asyncio.wait_for(entered.wait(), 2)
    await console.stop()
    evidence = json.loads((files.root / f"{outcome.request_id}-reply-evidence.json").read_bytes())
    assert evidence["reply_status"] == (
        "not_attempted" if stage == "before_watcher" else "cancelled_server_work_unknown"
    )
    assert evidence["run_id"] == outcome.run_id
    assert evidence["kind"] == outcome.kind == "applied"
    assert evidence["game_status"] == "known"
    assert evidence["reply_audio"] is None
    assert evidence["playback"] == "not_attempted"
    assert not console.replies
    assert len(state.enqueued) == 1
    assert entered.is_set() is (stage == "synthesis")


@pytest.mark.parametrize("stop_failed", [False, True])
@pytest.mark.parametrize("retirement", ["interrupted", "settlement_unknown"])
@pytest.mark.asyncio
async def test_stop_joins_player_despite_repeated_caller_cancellation_and_native_stop_failure(  # noqa: PLR0915 - one retirement scenario includes safe diagnostics and reopened admission
    files: PrivateWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    retirement: str,
    *,
    stop_failed: bool,
) -> None:
    loop = asyncio.get_running_loop()
    contexts: list[dict[str, Any]] = []
    previous = loop.get_exception_handler()
    loop.set_exception_handler(lambda _loop, context: contexts.append(context))
    request.addfinalizer(lambda: loop.set_exception_handler(previous))
    playing, retiring, release = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def play(_: bytes) -> str:
        playing.set()
        try:
            await asyncio.Event().wait()
        finally:
            retiring.set()
            await release.wait()
            if retirement == "settlement_unknown":
                msg = "private retirement diagnostic"
                raise VoicePlaybackUnsettled(msg)
        raise AssertionError

    monkeypatch.setattr(companion_lab, "play_reply", play)
    state = ConsoleSession()
    state.stop_failed = stop_failed
    client = speech(
        httpx.MockTransport(lambda _: httpx.Response(200, content=wav(), headers={"content-type": "audio/wav"}))
    )
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", state), speech=client, language="en", reply_language="en", play_replies=True
    )
    outcome = await console.submit("state")
    await asyncio.wait_for(playing.wait(), 2)
    stopping = asyncio.create_task(console.stop())
    await asyncio.wait_for(retiring.wait(), 2)
    stopping.cancel()
    await asyncio.sleep(0)
    stopping.cancel()
    assert not stopping.done()
    release.set()
    if stop_failed:
        with pytest.raises(RuntimeError, match="unconfirmed"):
            await stopping
    else:
        assert (await stopping).kind == "applied"
    evidence = json.loads((files.root / f"{outcome.request_id}-reply-evidence.json").read_bytes())
    assert evidence["playback"] == retirement
    assert evidence["human_hearing"] == "unconfirmed"
    assert evidence["kind"] == outcome.kind == "applied"
    assert evidence["run_id"] == outcome.run_id
    assert not console.replies
    if retirement == "settlement_unknown":
        with pytest.raises(ValueError, match=r"profile|settle"):
            console.begin_voice()
    assert len(state.enqueued) == 1
    if retirement == "interrupted":
        console.play_replies = False
        fresh = await console.submit("state")
        await asyncio.gather(*console.replies)
        assert fresh.request_id != outcome.request_id
    await asyncio.sleep(0)
    assert contexts == []


@pytest.mark.parametrize("known_run", [False, True])
@pytest.mark.asyncio
async def test_failed_native_stop_terminalizes_unavailable_reply_without_inventing_native_outcome(
    files: PrivateWorkspace, *, known_run: bool
) -> None:
    class UnavailableSession(ConsoleSession):
        def __init__(self) -> None:
            super().__init__()
            self.run_ids: dict[str, str] = {}
            self.stop_failed = True

        def enqueue(
            self, request: CompanionRequest | CompanionInstruction, *, captured_generation: int | None = None
        ) -> asyncio.Future[SessionResult]:
            del captured_generation
            self.enqueued.append(request)
            if known_run:
                self.run_ids[request.request_id] = str(uuid4())
            return asyncio.get_running_loop().create_future()

    state = UnavailableSession()
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", state), speech=speech(), language="en", reply_language="en"
    )
    native = console.submit("state")
    identity = state.enqueued[0].request_id
    with pytest.raises(RuntimeError, match="unconfirmed"):
        await console.stop()
    evidence = json.loads((files.root / f"{identity}-reply-evidence.json").read_bytes())
    assert evidence["game_status"] == "unavailable"
    assert evidence["kind"] is None
    assert evidence["run_identity"] == ("known" if known_run else "unknown")
    assert evidence["run_id"] == state.run_ids.get(identity)
    assert evidence["reply_status"] == evidence["playback"] == "not_attempted"
    assert not console.replies
    assert not native.done()
    native.cancel()
    assert len(state.enqueued) == 1


@pytest.mark.parametrize("failed_artifact", ["reply.wav", "reply.json", "reply-evidence.json"])
@pytest.mark.asyncio
async def test_reply_artifact_or_receipt_failure_keeps_known_game_and_honest_retention(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], failed_artifact: str
) -> None:
    original = files.write_new

    def write(path: Path, raw: bytes) -> None:
        if path.name.endswith(failed_artifact):
            msg = "private filesystem diagnostic"
            raise OSError(msg)
        original(path, raw)

    monkeypatch.setattr(files, "write_new", write)
    state = ConsoleSession()
    client = speech(
        httpx.MockTransport(lambda _: httpx.Response(200, content=wav(), headers={"content-type": "audio/wav"}))
    )
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", state), speech=client, language="en", reply_language="en", play_replies=False
    )
    outcome = await console.submit("state")
    await asyncio.gather(*console.replies)
    messages = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    report = messages[-1]
    assert "private" not in json.dumps(report)
    if failed_artifact == "reply-evidence.json":
        assert report["kind"] == "reply_evidence_failed"
        assert report["evidence_status"] == "failed"
        assert "evidence" not in report
        assert report["game_kind"] == "applied"
        assert not (files.root / f"{outcome.request_id}-reply-evidence.json").exists()
        evidence = report
    else:
        evidence = json.loads((files.root / f"{outcome.request_id}-reply-evidence.json").read_bytes())
        assert evidence["reply_failure"] == "artifact_write_failed"
        assert report["evidence_status"] == "recorded"
    assert evidence["request_id"] == outcome.request_id
    assert evidence["run_id"] == outcome.run_id
    assert evidence["game_status"] == "known"
    assert evidence["reply_status"] == "generated"
    assert evidence["playback"] == "not_attempted"
    assert bool(evidence["reply_audio"]) is (failed_artifact != "reply.wav")
    assert bool(evidence["synthesis_observation"]) is (failed_artifact == "reply-evidence.json")
    assert len(state.enqueued) == 1


@pytest.mark.parametrize("cancel_before_admission", [False, True])
@pytest.mark.asyncio
async def test_cancelled_console_caller_keeps_native_outcome_and_real_run_for_reply(
    files: PrivateWorkspace, *, cancel_before_admission: bool
) -> None:
    fake = FakeBridge()
    fake.delay = True
    bridge = fake.bridge()
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)
    speech_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        speech_requests.append(request)
        return httpx.Response(200, content=wav(), headers={"content-type": "audio/wav"})

    console = companion_lab.CompanionConsole(
        files, session, speech=speech(httpx.MockTransport(handler)), language="en", reply_language="en"
    )
    await session.open()
    try:
        caller = console.submit("say owned")
        if not cancel_before_admission:
            await asyncio.wait_for(fake.action_started.wait(), 2)
        assert caller.cancel()
        await asyncio.wait_for(fake.action_started.wait(), 2)
        assert caller.cancelled()
        assert console.replies
        assert speech_requests == []
        assert list(files.root.glob("*-reply-evidence.json")) == []
        fake.release_action.set()
        await asyncio.wait_for(asyncio.gather(*console.replies), 2)
        assert len(fake.requests) == 1
        identity = fake.requests[0]["action_id"]
        outcome = session.outcomes[identity]
        receipt = json.loads((files.root / f"{identity}-reply-evidence.json").read_bytes())
        assert outcome.kind == receipt["kind"] == "applied"
        assert receipt["game_status"] == "known"
        assert receipt["run_identity"] == "known"
        assert receipt["run_id"] == outcome.run_id == session.run_ids[identity]
        assert receipt["run_id"] is not None
        assert receipt["reply_status"] == "generated"
        assert len(speech_requests) == 1
        assert caller.cancelled()
    finally:
        await console.stop()
        await session.aclose()


@pytest.mark.parametrize("during_stop_line", [b"say stale-during-stop\n", b":record 1\n"])
@pytest.mark.asyncio
async def test_console_input_read_during_full_stop_never_reaches_native_transport(  # noqa: PLR0915 - one native causal trace spans physical stop, held console settlement and fresh recovery
    files: PrivateWorkspace, console_pipe: ConsolePipe, monkeypatch: pytest.MonkeyPatch, during_stop_line: bytes
) -> None:
    physical_stop_settled, release, stop_returned, fresh_published = (asyncio.Event() for _ in range(4))
    captures: list[int] = []
    records: list[dict[str, Any]] = []

    async def forbidden_capture(**_: Any) -> bytes:
        captures.append(1)
        msg = "A stop-period recording trigger must not arm capture."
        raise ValueError(msg)

    def forbidden_speech(_: httpx.Request) -> httpx.Response:
        msg = "Unexpected controlled speech request."
        raise AssertionError(msg)

    monkeypatch.setattr(companion_lab, "capture_utterance", forbidden_capture)
    fake = FakeBridge()
    bridge = fake.bridge()
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)

    async def retain(document: dict[str, Any]) -> None:
        records.append(document)
        if document["input"].get("action", {}).get("text") == "fresh-after-stop":
            fresh_published.set()

    session.record = retain

    class HeldConsole(companion_lab.CompanionConsole):
        held_once = False

        async def _settle_stop(
            self,
            settlement: Coroutine[Any, Any, CompanionResult],
            audio: list[asyncio.Task[None]],
            replies: list[asyncio.Task[None]],
        ) -> CompanionResult | BaseException:
            result = await super()._settle_stop(settlement, audio, replies)
            if not self.held_once:
                self.held_once = True
                assert not isinstance(result, BaseException)
                assert result.kind == "applied"
                physical_stop_settled.set()
                await release.wait()
            return result

        async def stop(self) -> CompanionResult:
            result = await super().stop()
            stop_returned.set()
            return result

    console = HeldConsole(files, session, speech=speech(httpx.MockTransport(forbidden_speech)), language="en")
    await session.open()
    task = asyncio.create_task(console.run())
    try:
        await asyncio.sleep(0)
        console_pipe.send(b"stop\n")
        await asyncio.wait_for(physical_stop_settled.wait(), 2)
        assert await console_pipe.read() == b"stop\n"
        assert len(fake.stop_ids) == fake.generation == bridge.epoch == 1
        assert not bridge.paused
        assert not stop_returned.is_set()
        console_pipe.send(during_stop_line)
        assert await console_pipe.read() == during_stop_line
        assert not stop_returned.is_set()
        assert not fake.requests
        assert not captures
        assert not session.run_ids
        release.set()
        await asyncio.wait_for(stop_returned.wait(), 2)
        console_pipe.send(b"say fresh-after-stop\n")
        await asyncio.wait_for(fresh_published.wait(), 2)
        if console.voice_task is not None:
            await asyncio.wait_for(asyncio.gather(console.voice_task, return_exceptions=True), 2)
        assert not captures
        assert len(fake.requests) == len(records) == 1
        sent, outcome = fake.requests[0], records[0]
        assert sent["kind"] == "say"
        assert sent["args"] == {"text": "fresh-after-stop"}
        assert sent["generation"] == fake.generation == 1
        assert outcome["request_id"] == sent["action_id"]
        assert outcome["kind"] == "applied"
        assert outcome["run_id"] is not None
        assert session.run_ids[sent["action_id"]] == outcome["run_id"]
        assert [
            event["data"]
            for event in outcome["events"]
            if event["kind"] == "node" and event.get("meta", {}).get("phase") == "entered"
        ] == ["validate", "execute", "report"]
        console_pipe.eof()
        await asyncio.wait_for(task, 2)
    finally:
        release.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await session.aclose()
