"""Observe existing local owners without giving clocks or receipts effect authority."""

from __future__ import annotations

import asyncio
import json
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from scripts import companion_lab
from scripts.voice_probe import PrivateWorkspace

from lychd.cli.companion_view import Language, format_companion_event
from lychd.system.services.companion_session import CompanionSession, SessionResult
from tests.unit.cli.test_companion_lab import ConsoleSession, speech, wav


@pytest.fixture
def files() -> Iterator[PrivateWorkspace]:
    with tempfile.TemporaryDirectory(prefix="lychd-timing-") as directory:
        yield PrivateWorkspace(Path(directory), (Path(__file__).resolve().parents[3],))


class Clock:
    def __init__(self) -> None:
        self.now = 10_000_000_000

    def __call__(self) -> int:
        return self.now

    def advance(self, milliseconds: int) -> None:
        self.now += milliseconds * 1_000_000


def timing(files: PrivateWorkspace) -> dict[str, Any]:
    paths = list(files.root.glob("*-timing.json"))
    assert len(paths) == 1
    assert paths[0].stat().st_size < 8192
    return cast("dict[str, Any]", json.loads(paths[0].read_bytes()))


async def settle(console: companion_lab.CompanionConsole) -> None:
    await asyncio.gather(*console.replies)
    await asyncio.sleep(0)


def console_for(
    files: PrivateWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    *,
    words: str = "state",
    reply: bool = True,
    state: ConsoleSession | None = None,
) -> tuple[companion_lab.CompanionConsole, Clock, Path]:
    clock = Clock()
    monkeypatch.setattr(companion_lab, "_host_tick", clock)

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/transcriptions"):
            clock.advance(23)
            return httpx.Response(200, json={"text": words})
        clock.advance(41)
        return httpx.Response(200, content=wav(), headers={"content-type": "audio/wav"})

    path = files.root / "input.wav"
    files.write_new(path, wav())
    console = companion_lab.CompanionConsole(
        files,
        cast("CompanionSession", state or ConsoleSession()),
        speech=speech(httpx.MockTransport(respond)),
        language="sk",
        reply_language="sk" if reply else None,
    )
    return console, clock, path


@pytest.mark.asyncio
async def test_one_envelope_measures_wait_stt_native_and_tts_without_summing(
    files: PrivateWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console, clock, path = console_for(files, monkeypatch)
    await console._capture_lock.acquire()  # pyright: ignore[reportPrivateUsage]
    voice = console.begin_voice(path)
    clock.advance(17)
    console._capture_lock.release()  # pyright: ignore[reportPrivateUsage]
    await voice
    await settle(console)
    record = timing(files)
    request = cast("ConsoleSession", console.session).enqueued[0]
    assert record["request_id"] == request.request_id
    assert record["generation"] == request.generation
    assert record["expires_at_ms"] == request.expires_at_ms
    assert record["elapsed_ms"] == 81
    assert record["stages"]["audio_wait"]["duration_ms"] == 17
    assert record["stages"]["transcription"]["duration_ms"] == 23
    assert record["stages"]["synthesis"]["duration_ms"] == 41
    assert record["stages"]["capture"]["status"] == "not_attempted"
    assert record["stages"]["supplied_audio_read"]["status"] == "returned"
    assert record["native_end_basis"] == "native_result_observed"
    evidence = json.loads((files.root / f"{request.request_id}-reply-evidence.json").read_bytes())
    assert record["run_id"] == evidence["run_id"]
    assert evidence["kind"] == record["native_kind"] == "applied"
    assert record["human_hearing"] == evidence["human_hearing"] == "unconfirmed"
    assert "state" not in json.dumps(record)
    assert not any(stage["status"] == "pending" for stage in record["stages"].values())


@pytest.mark.asyncio
async def test_no_tts_preserves_optional_reply_custody(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    console, _, path = console_for(files, monkeypatch, reply=False)
    await console.begin_voice(path)
    await settle(console)
    record = timing(files)
    assert record["native_kind"] == "applied"
    assert record["stages"]["synthesis"]["status"] == "not_attempted"
    assert not list(files.root.glob("*-reply-evidence.json"))


@pytest.mark.asyncio
async def test_preentry_voice_cancel_retains_only_local_wait(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    console, clock, path = console_for(files, monkeypatch)
    voice = console.begin_voice(path)
    voice.cancel()
    clock.advance(9)
    await asyncio.gather(voice, return_exceptions=True)
    await asyncio.sleep(0)
    record = timing(files)
    assert record["elapsed_ms"] == 9
    assert record["stages"]["audio_wait"]["status"] == "local_retirement_unknown"
    assert record["stages"]["transcription"]["status"] == "not_attempted"
    assert record["native_end_basis"] == "not_attempted"
    assert not cast("ConsoleSession", console.session).enqueued


@pytest.mark.parametrize("words", ["stop", "not a supported instruction"])
@pytest.mark.asyncio
async def test_stop_and_refused_instruction_keep_original_voice_record(
    files: PrivateWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    words: str,
) -> None:
    console, _, path = console_for(files, monkeypatch, words=words)
    await console.begin_voice(path)
    await settle(console)
    record = timing(files)
    voice = json.loads((files.root / f"{record['request_id']}-voice.json").read_bytes())
    assert voice["request_id"] == record["request_id"]
    assert record["run_id"] is None
    assert record["stages"]["spoken_stop"]["status"] == ("returned" if words == "stop" else "not_attempted")
    assert not cast("ConsoleSession", console.session).enqueued


@pytest.mark.asyncio
async def test_local_outcome_retirement_does_not_wait_for_native_future(
    files: PrivateWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Pending(ConsoleSession):
        def enqueue(self, request: Any, **kwargs: Any) -> asyncio.Future[SessionResult]:
            del kwargs
            self.enqueued.append(request)
            self.native: asyncio.Future[SessionResult] = asyncio.get_running_loop().create_future()
            return self.native

    state = Pending()
    console, clock, path = console_for(files, monkeypatch, state=state, reply=False)
    await console.begin_voice(path)
    identity = state.enqueued[0].request_id
    native, outcome = console._reply_outcomes[identity]  # pyright: ignore[reportPrivateUsage]
    clock.advance(53)
    outcome.set_result(None)  # Existing stop retirement seam; native work remains pending.
    await settle(console)
    original = next(files.root.glob("*-timing.json")).read_bytes()
    record = timing(files)
    assert record["stages"]["native_wait"]["duration_ms"] == 53
    assert record["native_end_basis"] == "local_outcome_unavailable"
    assert record["run_identity"] == "unknown"
    assert not native.done()
    native.set_result(SessionResult(identity, None, "cancelled", "late", reason="cancelled_before_execution"))
    await asyncio.sleep(0)
    assert next(files.root.glob("*-timing.json")).read_bytes() == original


@pytest.mark.asyncio
async def test_interrupted_stt_closes_local_span_without_claiming_remote_stop(
    files: PrivateWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console, clock, path = console_for(files, monkeypatch)
    entered = asyncio.Event()

    async def blocked(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        entered.set()
        await asyncio.Event().wait()

    assert console.speech is not None
    monkeypatch.setattr(console.speech, "transcribe", blocked)
    voice = console.begin_voice(path)
    await entered.wait()
    clock.advance(37)
    voice.cancel()
    await asyncio.gather(voice, return_exceptions=True)
    await asyncio.sleep(0)
    record = timing(files)
    assert record["stages"]["transcription"] == {"start_ms": 0, "duration_ms": 37, "status": "cancelled_local"}
    assert record["native_end_basis"] == "not_attempted"
    assert not cast("ConsoleSession", console.session).enqueued


@pytest.mark.asyncio
async def test_timing_write_failure_does_not_erase_game_or_audio_evidence(
    files: PrivateWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console, _, path = console_for(files, monkeypatch)
    original = files.write_new
    attempts: list[Path] = []
    events: list[dict[str, Any]] = []
    monkeypatch.setattr(console, "present", events.append)

    def write(path: Path, content: bytes) -> None:
        if path.name.endswith("-timing.json"):
            attempts.append(path)
            message = "private diagnostic"
            raise OSError(message)
        original(path, content)

    monkeypatch.setattr(files, "write_new", write)
    await console.begin_voice(path)
    await settle(console)
    assert len(attempts) == 1
    assert list(files.root.glob("*-reply-evidence.json"))
    assert list(files.root.glob("*-voice.json"))
    failed = next(event for event in events if event.get("kind") == "timing_evidence_failed")
    assert failed["native_kind"] == "applied"
    assert "timing_evidence_path" not in failed
    assert "evidence" not in failed
    assert "private diagnostic" not in json.dumps(failed)


@pytest.mark.parametrize("bad", [None, -1, True, "bad"])
def test_bad_clock_samples_are_unavailable(monkeypatch: pytest.MonkeyPatch, bad: object) -> None:
    monkeypatch.setattr(companion_lab.time, "monotonic_ns", lambda: bad)
    assert companion_lab._host_tick() is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_clock_exception_cannot_prevent_command(files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch) -> None:
    console, _, path = console_for(files, monkeypatch)

    def unavailable() -> int:
        message = "private clock"
        raise RuntimeError(message)

    monkeypatch.undo()
    monkeypatch.setattr(companion_lab.time, "monotonic_ns", unavailable)
    await console.begin_voice(path)
    await settle(console)
    record = timing(files)
    assert record["elapsed_ms"] is None
    assert record["native_kind"] == "applied"
    assert record["stages"]["transcription"]["duration_ms"] is None


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_timing_view_is_bounded_and_does_not_dump_payload(language: Language) -> None:
    line = format_companion_event(
        {
            "kind": "voice_timing",
            "request_id": "r",
            "elapsed_ms": 123,
            "stages": {
                "transcription": {"duration_ms": 24, "status": "returned"},
                "synthesis": {"duration_ms": None, "status": "not_attempted"},
            },
            "PRIVATE": "secret" * 10000,
        },
        language=language,
    )
    assert line is not None
    assert "123 ms" in line
    assert "24 ms" in line
    assert "secret" not in line
    assert len(line) < 1200


@pytest.mark.parametrize("owner", ["companion-outcome-reply", "companion-reply-audio"])
@pytest.mark.asyncio
async def test_preentry_reply_cancellation_never_invents_synthesis(
    files: PrivateWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    owner: str,
) -> None:
    console, _, path = console_for(files, monkeypatch)
    original = asyncio.create_task

    def create(coro: Any, **kwargs: Any) -> Any:
        task = original(coro, **kwargs)
        if kwargs.get("name") == owner:
            task.cancel()
        return task

    monkeypatch.setattr(asyncio, "create_task", create)
    await console.begin_voice(path)
    await asyncio.gather(*console.replies, return_exceptions=True)
    await asyncio.sleep(0)
    record = timing(files)
    assert record["stages"]["synthesis"]["status"] == "not_attempted"
    if owner == "companion-outcome-reply":
        assert record["native_end_basis"] == "local_retirement_unknown"
        assert record["run_identity"] == "unknown"
    else:
        assert record["native_kind"] == "applied"
        assert record["stages"]["reply_audio_wait"]["status"] == "local_retirement_unknown"
        evidence = json.loads(next(files.root.glob("*-reply-evidence.json")).read_bytes())
        assert evidence["reply_status"] == "not_attempted"


@pytest.mark.parametrize(
    "boundary",
    [
        "supplied_audio_read",
        "source_retention",
        "transcription",
        "transcript_retention",
        "synthesis",
        "reply_artifact_retention",
        "voice_evidence_retention",
        "reply_evidence_retention",
    ],
)
@pytest.mark.asyncio
async def test_failed_boundaries_keep_timing_and_native_truth_separate(
    files: PrivateWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
) -> None:
    console, _, path = console_for(files, monkeypatch)
    original_write = files.write_new
    suffix = {
        "source_retention": "-source.wav",
        "transcript_retention": "-transcript.json",
        "reply_artifact_retention": "-reply.wav",
        "voice_evidence_retention": "-voice.json",
        "reply_evidence_retention": "-reply-evidence.json",
    }.get(boundary)

    def write(candidate: Path, content: bytes) -> None:
        if suffix is not None and candidate.name.endswith(suffix):
            message = "private failed write"
            raise OSError(message)
        original_write(candidate, content)

    async def failed(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        message = "private failed inference"
        raise RuntimeError(message)

    monkeypatch.setattr(files, "write_new", write)
    if boundary == "supplied_audio_read":
        path.unlink()
    assert console.speech is not None
    if boundary in {"transcription", "synthesis"}:
        monkeypatch.setattr(console.speech, "transcribe" if boundary == "transcription" else "synthesize", failed)
    await console.begin_voice(path)
    await settle(console)
    record = timing(files)
    assert record["stages"][boundary]["status"] == (
        "returned" if boundary == "reply_evidence_retention" else "raised_local"
    )
    if boundary in {"synthesis", "reply_artifact_retention", "voice_evidence_retention", "reply_evidence_retention"}:
        assert record["native_kind"] == "applied"
    else:
        assert record["native_end_basis"] == "not_attempted"
        assert not cast("ConsoleSession", console.session).enqueued
    assert "private failed" not in json.dumps(record)


@pytest.mark.asyncio
async def test_reversed_clock_is_unknown_not_negative(files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch) -> None:
    console, clock, path = console_for(files, monkeypatch, reply=False)
    voice = console.begin_voice(path)
    clock.advance(-1000)
    await voice
    await settle(console)
    record = timing(files)
    assert record["elapsed_ms"] is None
    assert record["native_kind"] == "applied"


@pytest.mark.asyncio
async def test_reply_contention_is_a_separate_measured_wait(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    console, clock, path = console_for(files, monkeypatch)
    await console._reply_lock.acquire()  # pyright: ignore[reportPrivateUsage]
    await console.begin_voice(path)
    await asyncio.sleep(0)
    clock.advance(29)
    console._reply_lock.release()  # pyright: ignore[reportPrivateUsage]
    await settle(console)
    record = timing(files)
    assert record["stages"]["audio_wait"]["duration_ms"] == 0
    assert record["stages"]["reply_audio_wait"]["duration_ms"] == 29


@pytest.mark.asyncio
async def test_priority_stop_during_tts_preserves_native_result_and_local_cancel(
    files: PrivateWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console, clock, path = console_for(files, monkeypatch)
    entered = asyncio.Event()

    async def blocked(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        entered.set()
        await asyncio.Event().wait()

    assert console.speech is not None
    monkeypatch.setattr(console.speech, "synthesize", blocked)
    await console.begin_voice(path)
    await entered.wait()
    clock.advance(13)
    stopped = await console.stop()
    assert stopped.kind == "applied"
    await settle(console)
    record = timing(files)
    assert record["native_kind"] == "applied"
    assert record["stages"]["synthesis"]["status"] == "cancelled_local"
    assert record["stages"]["synthesis"]["duration_ms"] == 13
    evidence = json.loads(next(files.root.glob("*-reply-evidence.json")).read_bytes())
    assert evidence["reply_status"] == "cancelled_server_work_unknown"
    assert evidence["kind"] == "applied"


@pytest.mark.parametrize(
    ("language", "cancelled", "unavailable"),
    [
        ("sk", "miestne zrušené", "výsledok nedostupný"),
        ("cs", "místně zrušeno", "výsledek nedostupný"),
        ("en", "locally cancelled", "result unavailable"),
    ],
)
def test_timing_view_retains_cancel_status_and_native_endpoint(
    language: Language,
    cancelled: str,
    unavailable: str,
) -> None:
    line = format_companion_event(
        {
            "kind": "voice_timing",
            "request_id": "r",
            "elapsed_ms": 15,
            "source": "supplied",
            "native_end_basis": "local_outcome_unavailable",
            "stages": {
                "transcription": {"duration_ms": 7, "status": "cancelled_local"},
                "native_wait": {"duration_ms": 8, "status": "returned"},
            },
        },
        language=language,
    )
    assert line is not None
    assert cancelled in line
    assert unavailable in line
    assert "WAV" in line
