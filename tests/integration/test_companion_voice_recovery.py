"""Voice recovery across the real local control socket and native fixture Graph.

Speech, microphone and game transports remain fixture owned. These regressions
assert host boundary facts and bounded recovery advice, never provider diagnoses.
"""

from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path
from typing import Any, Literal

import httpx
import pytest
from rich.console import Console
from scripts import companion_lab
from scripts.voice_probe import PrivateWorkspace

from tests.integration.test_companion_control import connected, gesture, known
from tests.unit.cli.test_companion_lab import files as files  # noqa: PLC0414 - shared private fixture
from tests.unit.cli.test_companion_lab import wav

_PRIVATE = "PRIVATE_DIAGNOSTIC_7f2ab /private/player/source.wav [bold]"
_WORDS = "unsupported PRIVATE_TRANSCRIPT_9ae1"


def _events(console: companion_lab.CompanionConsole, monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    original = console._observe_control  # pyright: ignore[reportPrivateUsage]

    def observe(event: dict[str, Any]) -> None:
        events.append(dict(event))
        original(event)

    monkeypatch.setattr(console, "_observe_control", observe)
    return events


def _feedback(value: dict[str, Any], *, language: str, identity: str) -> str:
    feedback = value["feedback"]
    assert set(feedback) == {"language", "text"}
    assert feedback["language"] == language
    text = feedback["text"]
    assert isinstance(text, str)
    assert 0 < len(text) <= 200
    assert text.isprintable()
    for private in (_PRIVATE, "PRIVATE_DIAGNOSTIC", _WORDS, "PRIVATE_TRANSCRIPT", identity, "/private/", "source.wav"):
        assert private not in text
    return text


async def _post(client: httpx.AsyncClient, raw: bytes) -> httpx.Response:
    return await client.post("/v1/record", content=raw, headers={"Content-Type": "application/json"})


async def _settle_voice(console: companion_lab.CompanionConsole) -> None:
    assert console.voice_task is not None
    await asyncio.wait_for(console.voice_task, 2)
    # Let the task's existing done callbacks retire the observable voice phase.
    await asyncio.sleep(0)


@pytest.mark.parametrize(
    ("stage", "stt_calls"),
    [
        ("capture_failed", 0),
        ("audio_unsettled", 0),
        ("audio_read_failed", 0),
        ("source_retention_failed", 0),
        ("transcription_failed", 1),
        ("transcript_retention_failed", 1),
        ("instruction_refused", 1),
    ],
)
@pytest.mark.asyncio
async def test_failed_host_boundary_has_fixed_feedback_without_native_run(  # noqa: C901, PLR0915 - each injected boundary proves the same no-admission invariant
    files: PrivateWorkspace,
    unused_tcp_port: int,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    stt_calls: int,
) -> None:
    transcriptions: list[str] = []

    def transcribe(request: httpx.Request) -> httpx.Response:
        transcriptions.append(request.url.path)
        if stage == "transcription_failed":
            return httpx.Response(503, json={"detail": _PRIVATE})
        return httpx.Response(200, json={"text": _WORDS if stage == "instruction_refused" else "state"})

    async with connected(files, unused_tcp_port, monkeypatch, transcribe) as (control, console, fake, client, captures):
        events = _events(console, monkeypatch)
        original_write, original_read = files.write_new, files.read
        source = files.root / "supplied.wav"
        if stage == "audio_read_failed":
            original_write(source, wav())

        def write(path: Path, content: bytes) -> None:
            if (stage == "source_retention_failed" and path.name.endswith("-source.wav")) or (
                stage == "transcript_retention_failed" and path.name.endswith("-transcript.json")
            ):
                raise OSError(_PRIVATE)
            original_write(path, content)

        def read(path: Path, limit: int) -> bytes:
            if stage == "audio_read_failed" and path == source:
                raise OSError(_PRIVATE)
            return original_read(path, limit)

        async def failed_capture(*, seconds: int) -> bytes:
            captures.append(seconds)
            if stage == "capture_failed":
                raise companion_lab.VoiceCaptureError(_PRIVATE)
            raise companion_lab.VoiceCaptureUnsettled(_PRIVATE)

        monkeypatch.setattr(files, "write_new", write)
        monkeypatch.setattr(files, "read", read)
        if stage in {"capture_failed", "audio_unsettled"}:
            monkeypatch.setattr(companion_lab, "capture_utterance", failed_capture)
        raw = b""
        reads_before = fake.reads
        if stage == "audio_read_failed":
            # Supplied files use the existing foreground entry, with the same producer.
            await console.begin_voice(source)
            await asyncio.sleep(0)
            terminal = next(event for event in events if "voice_failure" in event)
            identity = terminal["request_id"]
            operation = None
        else:
            identity, raw = gesture(control)
            assert (await _post(client, raw)).status_code == 202
            await _settle_voice(console)
            operation = await known(client, identity)
            assert operation["status"] == "refused"
            assert operation["game_kind"] is None
            assert operation["server_stop_id"] is None
        (terminal,) = [event for event in events if "voice_failure" in event]
        assert terminal["request_id"] == identity
        assert terminal["kind"] == "refused"
        assert terminal["voice_failure"] == stage
        text = _feedback(terminal, language="en", identity=identity)
        if operation is not None:
            assert operation["feedback"] == terminal["feedback"]
            assert operation["native_evidence_status"] is None
        hints = {
            "capture_failed": (("record", "captur"),),
            "audio_unsettled": (("unconfirm", "unknown"), ("audio", "record"), ("text", "typed")),
            "audio_read_failed": (("read", "wav", "file"),),
            "source_retention_failed": (("audio", "source"), ("save", "retain", "stor")),
            "transcription_failed": (("transcri", "recogni", "speech"),),
            "transcript_retention_failed": (("transcript",), ("save", "retain", "stor")),
            "instruction_refused": (("command", "instruction"), ("exact", "strict", "support")),
        }
        assert all(any(fragment in text.lower() for fragment in alternatives) for alternatives in hints[stage])
        private = json.loads((files.root / f"{identity}-voice.json").read_bytes())
        assert private["request_id"] == identity
        assert private["kind"] == "refused"
        assert private["generation"] == console.session.capture_generation()
        assert type(private["expires_at_ms"]) is int
        if stage != "audio_read_failed":
            assert private["expires_at_ms"] == json.loads(raw)["expires_at_ms"]
        assert private["native_echo_admission"] is False
        assert "run_id" not in private
        assert len(transcriptions) == stt_calls
        assert not fake.requests
        assert fake.reads == reads_before
        assert not console.session.run_ids
        assert not list(files.root.glob("*-native.json"))
        assert not any(event.get("kind") == "queued" or event.get("run_id") for event in events)
        assert control.state()["audio_blocked"] is (stage == "audio_unsettled")


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize("output_mode", ["json", "human"])
@pytest.mark.asyncio
async def test_socket_stt_refusal_is_localized_deduplicated_and_fresh_gesture_reaches_native_graph(  # noqa: PLR0915 - one occurrence lineage includes dedupe, new admission and late-event precedence
    files: PrivateWorkspace,
    unused_tcp_port: int,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    language: str,
    output_mode: Literal["json", "human"],
) -> None:
    calls: list[str] = []

    def transcribe(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if len(calls) == 1:
            return httpx.Response(503, json={"detail": _PRIVATE})
        return httpx.Response(200, json={"text": "state" if language == "en" else "stav"})

    async with connected(files, unused_tcp_port, monkeypatch, transcribe) as (control, console, fake, client, captures):
        console.language = language
        console.output = output_mode
        stream = io.StringIO()
        console._terminal = Console(  # pyright: ignore[reportPrivateUsage]
            file=stream, width=500, color_system=None, force_terminal=False
        )
        events = _events(console, monkeypatch)
        failed_id, failed_raw = gesture(control)
        before = fake.reads
        assert (await _post(client, failed_raw)).status_code == 202
        await _settle_voice(console)
        failure = await known(client, failed_id)
        assert failure["request_id"] == failed_id
        assert failure["status"] == "refused"
        assert failure["game_kind"] is None
        assert failure["native_evidence_status"] is None
        assert failure["server_stop_id"] is None
        (terminal,) = [event for event in events if event.get("voice_failure") == "transcription_failed"]
        assert terminal["kind"] == ("voice_refused" if output_mode == "human" else "refused")
        assert terminal["request_id"] == failed_id
        text = _feedback(terminal, language=language, identity=failed_id)
        assert failure["feedback"] == terminal["feedback"]
        markers = {"sk": ("rozpozn", "prepis"), "cs": ("rozpozn", "přepis"), "en": ("recogni", "transcri")}
        assert any(marker in text.lower() for marker in markers[language])
        assert captures == [3]
        assert len(calls) == 1
        assert fake.reads == before
        assert not fake.requests
        assert not console.session.run_ids
        assert not list(files.root.glob("*-native.json"))
        assert control.state()["can_record"]
        if output_mode == "human":
            assert text in stream.getvalue()
            assert capsys.readouterr().out == ""
        else:
            messages = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
            assert terminal in messages
            assert all("transcript" not in item and "text" not in item for item in messages)
        duplicate = await _post(client, failed_raw)
        assert duplicate.status_code == 200
        assert duplicate.json() == failure
        assert captures == [3]
        assert len(calls) == 1
        assert not fake.requests
        recovered_id, recovered_raw = gesture(control)
        assert recovered_id != failed_id
        assert (await _post(client, recovered_raw)).status_code == 202
        await _settle_voice(console)
        await asyncio.wait_for(asyncio.gather(*console.replies), 2)
        recovered = await known(client, recovered_id)
        assert recovered["game_kind"] == "applied"
        assert recovered["status"] == "known"
        assert recovered["native_evidence_status"] == "recorded"
        assert recovered["feedback"]["language"] == language
        assert captures == [3, 3]
        assert len(calls) == 2
        assert len(fake.requests) == len(console.session.run_ids) == len(console.session.runner.queue.jobs) == 1
        assert recovered_id in console.session.run_ids
        assert failed_id not in console.session.run_ids
        (native_path,) = files.root.glob("*-native.json")
        native = json.loads(native_path.read_bytes())
        assert native["request_id"] == recovered_id
        assert native["run_id"] == fake.requests[0]["run_id"]
        assert native["events"]
        assert (await known(client, failed_id)) == failure
        # Reordered producer failure cannot regress an actual retained native result.
        control.observe({**terminal, "request_id": recovered_id})
        assert (await client.get("/v1/operations/" + recovered_id)).json() == recovered
        assert (await _post(client, failed_raw)).status_code == 200
        assert captures == [3, 3]
        assert len(calls) == 2
        assert len(fake.requests) == 1


@pytest.mark.asyncio
async def test_unknown_recorder_retirement_latches_audio_but_typed_state_keeps_native_ownership(
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    stt: list[str] = []

    def transcribe(request: httpx.Request) -> httpx.Response:
        stt.append(request.url.path)
        return httpx.Response(200, json={"text": "state"})

    async with connected(files, unused_tcp_port, monkeypatch, transcribe) as (control, console, fake, client, captures):

        async def capture(*, seconds: int) -> bytes:
            captures.append(seconds)
            raise companion_lab.VoiceCaptureUnsettled(_PRIVATE)

        monkeypatch.setattr(companion_lab, "capture_utterance", capture)
        identity, raw = gesture(control)
        assert (await _post(client, raw)).status_code == 202
        await _settle_voice(console)
        failure = await known(client, identity)
        assert failure["status"] == "refused"
        assert failure["game_kind"] is None
        _feedback(failure, language="en", identity=identity)
        state = (await client.get("/v1/state")).json()
        assert state["audio_blocked"]
        assert not state["can_record"]
        fresh_id, fresh_raw = gesture(control)
        assert (await _post(client, fresh_raw)).status_code == 409
        assert (await known(client, fresh_id))["game_kind"] is None
        with pytest.raises(ValueError, match="settle"):
            console.begin_voice()
        assert not fake.requests
        assert not console.session.run_ids
        result = await asyncio.wait_for(console.submit("state"), 2)
        await asyncio.wait_for(asyncio.gather(*console.replies), 2)
        assert result.kind == "applied"
        assert result.run_id is not None
        assert len(fake.requests) == len(console.session.run_ids) == 1
        assert result.request_id in console.session.run_ids
        assert identity not in console.session.run_ids
        assert control.state()["audio_blocked"]
        assert not control.state()["can_record"]
        assert captures == [3]
        assert not stt
        assert (await _post(client, raw)).status_code == 200
        assert captures == [3]
        assert not stt


@pytest.mark.parametrize("audio_unsettled", [False, True])
@pytest.mark.asyncio
async def test_post_enqueue_value_error_is_unknown_until_one_later_native_result(  # noqa: PLR0915 - one native occurrence proves unknown-to-known precedence without replay
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch, *, audio_unsettled: bool
) -> None:
    calls: list[str] = []

    def transcribe(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"text": "state"})

    async with connected(files, unused_tcp_port, monkeypatch, transcribe) as (control, console, fake, client, captures):
        fake.delay = True
        events = _events(console, monkeypatch)
        identity, raw = gesture(control)
        notices: list[str] = []

        def failed_notice(request_id: str) -> None:
            notices.append(request_id)
            if audio_unsettled:
                console._audio_blocked = True  # pyright: ignore[reportPrivateUsage] - concurrent audio-owner observation
            raise ValueError(_PRIVATE)

        monkeypatch.setattr(console, "_queued_notice", failed_notice)
        try:
            assert (await _post(client, raw)).status_code == 202
            await _settle_voice(console)
            await asyncio.wait_for(fake.action_started.wait(), 2)
            unknown = await known(client, identity)
            assert unknown["status"] == "unknown"
            assert unknown["game_kind"] is None
            (terminal,) = [event for event in events if "voice_failure" in event]
            assert terminal["kind"] == "unknown"
            assert terminal["voice_failure"] == ("audio_unsettled" if audio_unsettled else "admission_unknown")
            _feedback(terminal, language="en", identity=identity)
            assert unknown["feedback"] == terminal["feedback"]
            private = json.loads((files.root / f"{identity}-voice.json").read_bytes())
            assert private["kind"] == "unknown"
            assert "run_id" not in private
            assert notices == [identity]
            assert (await _post(client, raw)).status_code == 200
            assert captures == [3]
            assert len(calls) == 1
            assert len(fake.requests) == 1
            fake.release_action.set()
            await asyncio.wait_for(asyncio.gather(*console.replies), 2)
            applied = (await client.get("/v1/operations/" + identity)).json()
            assert applied["status"] == "known"
            assert applied["game_kind"] == "applied"
            assert applied["native_evidence_status"] == "recorded"
            (native_path,) = files.root.glob("*-native.json")
            native = json.loads(native_path.read_bytes())
            assert native["request_id"] == identity
            assert native["run_id"] == fake.requests[0]["run_id"]
            assert native["events"]
            assert len(console.session.run_ids) == len(console.session.runner.queue.jobs) == 1
            control.observe(terminal)
            assert (await client.get("/v1/operations/" + identity)).json() == applied
            assert (await _post(client, raw)).status_code == 200
            assert notices == [identity]
            assert captures == [3]
            assert len(calls) == 1
            assert len(fake.requests) == 1
        finally:
            fake.release_action.set()


@pytest.mark.parametrize("output_mode", ["json", "human"])
@pytest.mark.asyncio
async def test_failed_spoken_stop_is_correlated_unknown_without_server_identity_or_repost(
    files: PrivateWorkspace,
    unused_tcp_port: int,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    output_mode: Literal["json", "human"],
) -> None:
    async with connected(
        files, unused_tcp_port, monkeypatch, lambda _: httpx.Response(200, json={"text": " Stop\n"})
    ) as (control, console, fake, client, captures):
        console.output = output_mode
        stream = io.StringIO()
        console._terminal = Console(  # pyright: ignore[reportPrivateUsage]
            file=stream, width=500, color_system=None, force_terminal=False
        )
        events = _events(console, monkeypatch)
        attempts: list[None] = []

        async def failed_stop() -> Any:
            attempts.append(None)
            raise RuntimeError(_PRIVATE)

        # Restore the normal stop owner before the connected fixture retires.
        with monkeypatch.context() as failure:
            failure.setattr(console, "stop", failed_stop)
            identity, raw = gesture(control)
            assert (await _post(client, raw)).status_code == 202
            await _settle_voice(console)
            operation = await known(client, identity)
            assert operation["status"] == "unknown"
            assert operation["game_kind"] == "unknown"
            assert operation["server_stop_id"] is None
            (terminal,) = [event for event in events if event.get("kind") == "voice_stop_result"]
            assert terminal["request_id"] == identity
            assert terminal["game_kind"] == "unknown"
            assert terminal.get("server_stop_id") is None
            text = _feedback(terminal, language="en", identity=identity)
            assert operation["feedback"] == terminal["feedback"]
            assert "stop" in text.lower()
            if output_mode == "human":
                assert text in stream.getvalue()
                assert capsys.readouterr().out == ""
            else:
                messages = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
                assert terminal in messages
                assert all("transcript" not in item and "text" not in item for item in messages)
                assert _PRIVATE not in json.dumps(messages)
                assert " Stop\\n" not in json.dumps(messages)
            private = json.loads((files.root / f"{identity}-voice.json").read_bytes())
            assert private["request_id"] == identity
            assert private["kind"] == "unknown"
            assert private.get("stop_request_id") is None
            assert "run_id" not in private
            assert not any("voice_failure" in event for event in events)
            assert not fake.requests
            assert not fake.stop_ids
            assert not console.session.run_ids
            assert (await _post(client, raw)).status_code == 200
            assert attempts == [None]
            assert captures == [3]
            assert not fake.requests
            assert not fake.stop_ids


@pytest.mark.asyncio
async def test_expired_voice_waiting_for_audio_reports_input_unavailable_without_capture(
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    stt: list[str] = []

    def transcribe(request: httpx.Request) -> httpx.Response:
        stt.append(request.url.path)
        return httpx.Response(200, json={"text": "state"})

    async with connected(files, unused_tcp_port, monkeypatch, transcribe) as (control, console, fake, client, captures):
        events = _events(console, monkeypatch)
        lock = console._capture_lock  # pyright: ignore[reportPrivateUsage]
        await lock.acquire()
        try:
            identity, raw = gesture(control)
            expiry = json.loads(raw)["expires_at_ms"]
            assert (await _post(client, raw)).status_code == 202
            assert not captures
            assert not stt
            # The original captured deadline elapses while audio ownership is held.
            with monkeypatch.context() as expired:
                expired.setattr(companion_lab.time, "time", lambda: (expiry + 1) / 1000)
                lock.release()
                await _settle_voice(console)
            outcome = await known(client, identity)
            assert outcome["status"] == "refused"
            assert outcome["game_kind"] is None
            (terminal,) = [event for event in events if "voice_failure" in event]
            assert terminal["voice_failure"] == "input_unavailable"
            assert terminal["request_id"] == identity
            assert terminal["kind"] == "refused"
            _feedback(terminal, language="en", identity=identity)
            assert outcome["feedback"] == terminal["feedback"]
            private = json.loads((files.root / f"{identity}-voice.json").read_bytes())
            assert private["expires_at_ms"] == expiry
            assert private["kind"] == "refused"
            assert "run_id" not in private
            assert not captures
            assert not stt
            assert not fake.requests
            assert not console.session.run_ids
            assert not list(files.root.glob("*-native.json"))
        finally:
            if lock.locked():
                lock.release()
