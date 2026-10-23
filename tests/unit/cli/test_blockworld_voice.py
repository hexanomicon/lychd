from __future__ import annotations

import asyncio
import base64
import json
import os
import struct
import tempfile
from argparse import Namespace
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, TextIO, cast

import httpx
import pytest
import pytest_asyncio
from scripts import blockworld_voice
from scripts.voice_probe import PrivateWorkspace

from lychd.compositions.blockworld.horizon_assist import AssistRequest, HorizonAssistService
from lychd.compositions.blockworld.horizon_assist_runtime import LocalAssistRunner
from lychd.compositions.blockworld.horizon_behaviors import HorizonBehaviorService
from lychd.domain.speech_probe import SpeechModel, SpeechProfile
from lychd.system.services import horizon_control
from lychd.system.services.horizon_control import HorizonBinding, HorizonControlSession
from lychd.system.services.horizon_observer import HorizonTargetObserver
from lychd.system.services.speech_probe import SpeechProbe
from lychd.system.services.voice_capture import VoiceCaptureError, VoiceCaptureUnsettled
from tests.integration.test_horizon_assist import FakeGame, policy
from tests.unit.domain.test_speech_probe import profile_v2

type Host = tuple[PrivateWorkspace, FakeGame, LocalAssistRunner, HorizonControlSession]
_CHECKOUT = Path(__file__).resolve().parents[3]


def wav() -> bytes:
    return (
        struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 52, b"WAVE", b"fmt ", 16, 1, 1, 16000, 32000, 2, 16, b"data", 16)
        + b"\x00" * 16
    )


def speech(handler: httpx.MockTransport) -> SpeechProbe:
    pinned = SpeechProfile(
        endpoint="http://127.0.0.1:8080",
        runtime_revision="a" * 40,
        backend="cpu",
        device="cpu",
        transcriber=SpeechModel(
            model="parakeet-test",
            family="parakeet-tdt-0.6b-v3",
            digest="sha256:" + "b" * 64,
            languages=("sk", "en"),
            license="test-only",
        ),
        synthesizer=SpeechModel(
            model="supertonic-test",
            family="supertonic-3",
            digest="sha256:" + "c" * 64,
            languages=("sk", "en"),
            license="test-only",
        ),
        transport_timeout_seconds=1.0,
        total_timeout_seconds=2.0,
        max_response_bytes=65536,
        max_text_chars=200,
    )
    return SpeechProbe(pinned, transport=handler)


@pytest_asyncio.fixture
async def host() -> AsyncIterator[Host]:
    with tempfile.TemporaryDirectory(prefix="lychd-voice-test-") as directory:
        root = Path(directory)
        game = FakeGame(root / "game.sock")
        server = await asyncio.start_unix_server(game.handle, path=game.endpoint)
        control = HorizonControlSession(game.binding())
        assist = HorizonAssistService(policy(), control)
        runner = LocalAssistRunner(assist, control, behaviors=HorizonBehaviorService(assist))
        await control.open()
        await runner.open()
        try:
            yield PrivateWorkspace(root, (_CHECKOUT,)), game, runner, control
        finally:
            await runner.aclose()
            server.close()
            await server.wait_closed()
            for task in tuple(game.connections):
                task.cancel()
            await asyncio.gather(*game.connections, return_exceptions=True)


@pytest.mark.asyncio
async def test_one_transcription_one_native_run_private_evidence_optional_generated_reply(host: Host) -> None:
    files, _game, runner, control = host
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("transcriptions"):
            assert b'filename="utterance.wav"' in request.content
            return httpx.Response(200, json={"text": "stav"})
        return httpx.Response(200, content=wav(), headers={"Content-Type": "audio/wav"})

    session = blockworld_voice.VoiceSession(
        files, speech(httpx.MockTransport(handler)), runner, control, language="sk", reply_language="sk"
    )
    result = await session.begin(wav())
    assert result["kind"] == "client_observed"
    assert len(runner.queue.jobs) == 1
    assert calls == ["/v1/audio/transcriptions", "/v1/audio/speech"]
    assert result["playback"] == "not_attempted"
    retained = list(files.root.glob("*-events.jsonl"))
    assert len(retained) == 1
    assert b"RIFF" not in retained[0].read_bytes()
    assert base64.b64encode(wav()) not in retained[0].read_bytes()
    receipt = json.loads(next(files.root.glob("*-voice.json")).read_bytes())
    assert set(receipt["stage_seconds"]) == {"capture", "stt", "graph", "tts"}
    assert receipt["native_echo_admission"] is False
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in files.root.glob("*.json*"))


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", [RuntimeError, TimeoutError, VoiceCaptureUnsettled])
async def test_unknown_recorder_retirement_fences_horizon_without_reporting_off(
    host: Host, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], error_type: type[Exception]
) -> None:
    files, _game, runner, control = host

    async def capture(**_: Any) -> bytes:
        msg = "private recorder details"
        raise error_type(msg)

    monkeypatch.setattr(blockworld_voice, "capture_utterance", capture)
    client = speech(httpx.MockTransport(lambda _: pytest.fail("Unknown capture cannot reach speech.")))
    session = blockworld_voice.VoiceSession(files, client, runner, control)
    try:
        with pytest.raises(error_type):
            await session.begin()
        assert session.stopped.is_set()
        with pytest.raises(ValueError, match="stopped"):
            session.begin()
        assert not runner.queue.jobs
        output = capsys.readouterr().out
        assert "CAPTURE RETIREMENT UNKNOWN" in output
        assert "CAPTURE OFF" not in output
        assert "private recorder details" not in output
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_settled_recorder_failure_leaves_horizon_available_for_new_gesture(
    host: Host, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    files, _game, runner, control = host
    attempts: list[int] = []

    async def capture(**_: Any) -> bytes:
        attempts.append(1)
        if len(attempts) == 1:
            msg = "Recorder failed after retirement."
            raise VoiceCaptureError(msg)
        return wav()

    monkeypatch.setattr(blockworld_voice, "capture_utterance", capture)
    client = speech(httpx.MockTransport(lambda _: httpx.Response(200, json={"text": "stav"})))
    session = blockworld_voice.VoiceSession(files, client, runner, control)
    try:
        with pytest.raises(VoiceCaptureError):
            await session.begin()
        await asyncio.sleep(0)
        assert len(attempts) == 1
        assert not session.stopped.is_set()
        assert not runner.queue.jobs
        assert (await session.begin())["kind"] == "client_observed"
        assert len(attempts) == 2
        assert len(runner.queue.jobs) == 1
        assert capsys.readouterr().out.count("CAPTURE OFF") == 2
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_ambiguous_transcript_has_no_run_or_world_command(host: Host) -> None:
    files, game, runner, control = host
    client = speech(httpx.MockTransport(lambda _request: httpx.Response(200, json={"text": "build a house"})))
    session = blockworld_voice.VoiceSession(files, client, runner, control)
    assert (await session.begin(wav()))["kind"] == "refused"
    assert not runner.queue.jobs
    assert set(game.commands) <= {"state", "status"}


@pytest.mark.asyncio
@pytest.mark.parametrize("phrase", ["postav schválený plán", "postav schvaleny plan", "build approved plan"])
async def test_build_phrase_does_not_invent_a_missing_plan(host: Host, phrase: str) -> None:
    files, game, runner, control = host
    client = speech(httpx.MockTransport(lambda _: httpx.Response(200, json={"text": phrase})))
    session = blockworld_voice.VoiceSession(files, client, runner, control)
    assert (await session.begin(wav()))["kind"] == "refused"
    assert not runner.queue.jobs
    assert set(game.commands) <= {"state", "status"}


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["capture", "stt"])
async def test_priority_stop_during_capture_or_stt_creates_no_run(
    host: Host, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    files, game, runner, control = host
    entered = asyncio.Event()

    async def capture(*, seconds: int) -> bytes:
        entered.set()
        await asyncio.Event().wait()
        return wav()

    async def handler(request: httpx.Request) -> httpx.Response:
        entered.set()
        await asyncio.Event().wait()
        return httpx.Response(200, json={"text": "goto 1 64 0"})

    monkeypatch.setattr(blockworld_voice, "capture_utterance", capture)
    session = blockworld_voice.VoiceSession(files, speech(httpx.MockTransport(handler)), runner, control)
    task = session.begin(None if stage == "capture" else wav())
    await entered.wait()
    await session.stop()
    assert task.cancelled()
    assert not runner.queue.jobs
    assert set(game.commands) <= {"state", "status"}
    with pytest.raises(ValueError, match="stopped"):
        session.begin(wav())


@pytest.mark.asyncio
async def test_priority_stop_drains_waiting_game_action(host: Host) -> None:
    files, game, runner, control = host
    client = speech(httpx.MockTransport(lambda _request: httpx.Response(200, json={"text": "goto 1 64 0"})))
    session = blockworld_voice.VoiceSession(files, client, runner, control)
    task = session.begin(wav())
    await game.issued.wait()
    await session.stop()
    assert task.cancelled()
    assert game.stops >= 1
    assert not game.active
    assert sum(command.startswith("goto ") for command in game.commands) == 1


@pytest.mark.asyncio
async def test_stop_fences_run_even_when_admission_has_not_returned_its_id(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    files, game, runner, control = host
    entered, release = asyncio.Event(), asyncio.Event()
    original = runner.submit

    async def delayed(request: AssistRequest) -> str:
        entered.set()
        await release.wait()
        return await original(request)

    monkeypatch.setattr(runner, "submit", delayed)
    client = speech(httpx.MockTransport(lambda _request: httpx.Response(200, json={"text": "goto 1 64 0"})))
    session = blockworld_voice.VoiceSession(files, client, runner, control)
    task = session.begin(wav())
    await entered.wait()
    stopping = asyncio.create_task(session.stop())
    await asyncio.sleep(0)
    release.set()
    await stopping
    assert task.cancelled()
    assert not any(command.startswith("goto ") for command in game.commands)


@pytest.mark.asyncio
async def test_console_stop_overtakes_queued_record_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    reader, writer = os.pipe()
    with os.fdopen(reader, "r") as stream:
        monkeypatch.setattr(blockworld_voice.sys, "stdin", cast("TextIO", stream))
        lines = blockworld_voice.console_lines()
        try:
            os.write(writer, b"record\n" * 12 + b"stop\nrecord\n")
            assert await anext(lines) == "stop"
        finally:
            await lines.aclose()
            os.close(writer)


@pytest.mark.asyncio
async def test_slovak_idle_runs_native_graph_and_next_capture_settles_it_first(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    files, game, runner, control = host
    words = iter(("Čakaj.", "Stav."))
    client = speech(httpx.MockTransport(lambda _request: httpx.Response(200, json={"text": next(words)})))
    session = blockworld_voice.VoiceSession(files, client, runner, control, behavior_seconds=5)
    recorded = asyncio.Event()
    original = session.supervisor.record

    async def evidence(record: dict[str, object]) -> None:
        assert original is not None
        await original(record)
        recorded.set()

    async def capture(*, seconds: int) -> bytes:
        assert runner.behaviors is not None
        assert runner.behaviors.directive is None
        assert all(job.task is not None and job.task.done() for job in runner.queue.jobs.values())
        return wav()

    session.supervisor.record = evidence
    monkeypatch.setattr(blockworld_voice, "capture_utterance", capture)
    try:
        assert (await session.begin(wav()))["kind"] == "behavior_started"
        await asyncio.wait_for(recorded.wait(), timeout=2)
        retained = json.loads(next(files.root.glob("*-behavior.json")).read_bytes())
        assert retained["model_calls"] == 0
        assert retained["action_attempts"] == 0
        assert await asyncio.to_thread(Path(retained["events"]).is_file)
        assert (await session.begin())["kind"] == "client_observed"
        assert not any(command.startswith("goto") for command in game.commands)
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_follow_transcript_without_exact_target_refuses(host: Host) -> None:
    files, game, runner, control = host
    client = speech(httpx.MockTransport(lambda _request: httpx.Response(200, json={"text": "Nasleduj ma."})))
    session = blockworld_voice.VoiceSession(files, client, runner, control)
    try:
        assert (await session.begin(wav()))["kind"] == "refused"
        assert not runner.queue.jobs
        assert set(game.commands) <= {"state", "status"}
    finally:
        await session.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw",
    [
        '{"binding":{},"binding":{}}',
        '{"binding":{"pid":NaN}}',
        '{"binding":{},"shell":"stop"}',
        '{"binding":{"endpoint":12}}',
        "[]",
    ],
)
async def test_target_profile_is_closed_private_query_binding(host: Host, raw: str) -> None:
    files, _game, _runner, _control = host
    path = files.root / "target.json"
    files.write_new(path, raw.encode())
    with pytest.raises(ValueError, match=r".+"):
        blockworld_voice.load_target_binding(files, path)


@pytest.mark.asyncio
async def test_operate_explicitly_opts_attached_target_into_finite_read_settlement(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    files, game, _runner, _control = host
    profile = files.root / "speech.json"
    client = speech(httpx.MockTransport(lambda _: httpx.Response(200)))
    files.write_new(profile, client.profile.model_dump_json().encode())
    binding = game.binding()

    def load_game(_path: Path) -> tuple[HorizonBinding, dict[str, Any], Path]:
        return binding, policy().model_dump(mode="json"), files.root

    def load_target(_files: PrivateWorkspace, _path: Path) -> HorizonBinding:
        return binding

    monkeypatch.setattr(horizon_control, "load_assist_profile", load_game)
    monkeypatch.setattr(blockworld_voice, "load_target_binding", load_target)

    class TargetConstructedError(Exception):
        pass

    def target(
        actual: HorizonBinding, *, bot_binding: HorizonBinding, settle_cancelled_reads: bool = False
    ) -> HorizonTargetObserver:
        assert actual is binding
        assert bot_binding is binding
        assert settle_cancelled_reads is True
        raise TargetConstructedError

    monkeypatch.setattr(blockworld_voice, "HorizonTargetObserver", target)
    options = Namespace(
        workspace=files.root,
        checkout_root=[_CHECKOUT],
        speech_profile=profile,
        game_profile=files.root / "game.json",
        target_profile=files.root / "target.json",
    )
    with pytest.raises(TargetConstructedError):
        await blockworld_voice.operate(options)


@pytest.mark.asyncio
async def test_version_two_loader_selects_speech_before_any_game_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    pinned = profile_v2()

    class BeforeGameAdmissionError(Exception):
        pass

    with tempfile.TemporaryDirectory(prefix="lychd-voice-v2-") as directory:
        root = Path(directory)
        profile_path = root / "speech.json"
        files = PrivateWorkspace(root, (_CHECKOUT,))
        files.write_new(profile_path, pinned.model_dump_json().encode())
        selected: list[SpeechProbe] = []

        def speech_probe(actual: Any) -> SpeechProbe:
            client = SpeechProbe(actual, transport=httpx.MockTransport(lambda _: pytest.fail("Unexpected speech HTTP")))
            selected.append(client)
            return client

        def load_game(_path: Path) -> Any:
            raise BeforeGameAdmissionError

        monkeypatch.setattr(blockworld_voice, "SpeechProbe", speech_probe)
        monkeypatch.setattr(horizon_control, "load_assist_profile", load_game)
        options = Namespace(
            workspace=root, checkout_root=[_CHECKOUT], speech_profile=profile_path, game_profile=root / "game.json"
        )
        with pytest.raises(BeforeGameAdmissionError):
            await blockworld_voice.operate(options)
        assert len(selected) == 1
        assert selected[0].profile.digest == pinned.digest
        assert selected[0].profile.transcriber_binding.runtime == "whisper.cpp"
        assert selected[0].profile.synthesizer_binding.runtime == "audio.cpp"
