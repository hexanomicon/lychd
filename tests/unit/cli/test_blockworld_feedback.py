from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from scripts import blockworld_voice

from lychd.compositions.blockworld.horizon_behaviors import BehaviorDirective
from lychd.compositions.blockworld.horizon_feedback import MAX_FEEDBACK_CHARS, REPLY_LANGUAGES, feedback_text
from lychd.domain.cortex.runs import RunStatus
from tests.unit.cli.test_blockworld_voice import Host, speech, wav
from tests.unit.cli.test_blockworld_voice import host as native_host

host = native_host


@pytest.mark.parametrize(
    ("language", "refused", "reported", "unknown", "error", "waiting", "following", "building", "no_repeat"),
    [
        (
            "sk",
            "odmietnutý",
            "klient oznámil",
            "neznámy",
            "chybu",
            "Čakanie",
            "Nasledovanie",
            "stavebný plán",
            "neopakuj",
        ),
        ("cs", "odmítnut", "klient oznámil", "neznámý", "chybu", "Čekání", "Následování", "stavební plán", "neopakuj"),
        ("en", "refused", "client reported", "unknown", "error", "Waiting", "Following", "build plan", "do not repeat"),
    ],
)
def test_fixed_feedback_distinguishes_actual_results_without_releasing_private_detail(
    language: str,
    refused: str,
    reported: str,
    unknown: str,
    error: str,
    waiting: str,
    following: str,
    building: str,
    no_repeat: str,
) -> None:
    cases = [
        ({"kind": "refused"}, refused),
        ({"kind": "client_observed"}, reported),
        ({"kind": "outcome_unknown"}, unknown),
        ({"kind": "client_error"}, error),
        ({"kind": "behavior_started", "behavior": "idle"}, waiting),
        ({"kind": "behavior_started", "behavior": "follow"}, following),
        ({"kind": "build_started"}, building),
    ]
    rendered: set[str] = set()
    for result, expected in cases:
        text = feedback_text({**result, "detail": "PRIVATE provider exception says completed"}, language)
        assert expected in text
        assert "PRIVATE" not in text
        assert "provider" not in text
        assert 0 < len(text) <= MAX_FEEDBACK_CHARS
        rendered.add(text)
    assert len(rendered) == len(cases)
    for result in ({"kind": "outcome_unknown"}, {"kind": "future"}, {"kind": "behavior_started", "behavior": "future"}):
        assert no_repeat in feedback_text(result, language).casefold()
    assert feedback_text({"kind": "future"}, language) == feedback_text({}, language)
    # Starting a task is distinct from an observed result; no diagnostic prose
    # can turn that notice into a completion claim.
    for result in ({"kind": "behavior_started", "behavior": "follow"}, {"kind": "build_started"}):
        assert feedback_text({**result, "detail": "Completed successfully"}, language) == feedback_text(
            result, language
        )
        assert "Completed successfully" not in feedback_text(result, language)


def test_reply_languages_are_closed() -> None:
    assert REPLY_LANGUAGES == ("sk", "cs", "en")
    with pytest.raises(ValueError, match="sk, cs or en"):
        feedback_text({"kind": "client_observed"}, "de")


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["http", "invalid_wav"])
async def test_failed_optional_tts_preserves_one_effect_native_result_and_events(
    host: Host,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    files, game, runner, control = host
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("transcriptions"):
            return httpx.Response(200, json={"text": "say hello"})
        body = json.loads(request.content)
        assert body["input"] == feedback_text({"kind": "client_observed"}, "sk")
        return httpx.Response(
            503 if failure == "http" else 200,
            content=b"PRIVATE provider details",
            headers={"Content-Type": "audio/wav"},
        )

    session = blockworld_voice.VoiceSession(
        files, speech(httpx.MockTransport(handler)), runner, control, reply_language="sk"
    )
    try:
        task = session.begin(wav())
        result = await task
        assert result["kind"] == "client_observed"
        assert result["reply_status"] == "failed"
        assert result["reply_failure"] == "synthesis_failed"
        assert result["feedback_language"] == "sk"
        assert result["feedback"] == feedback_text(result, "sk")
        assert "reply_audio" not in result
        assert calls == ["/v1/audio/transcriptions", "/v1/audio/speech"]
        assert game.commands.count("chat hello") == 1
        assert len(runner.queue.jobs) == 1
        assert runner.services is not None
        native = await runner.services.ledger.get(result["run_id"])
        assert native is not None
        assert native.status is RunStatus.DONE
        assert runner.assist.run_results[result["run_id"]].kind == "client_observed"
        assert files.root.joinpath(result["events"]).read_text()
        receipt = json.loads(next(files.root.glob("*-voice.json")).read_bytes())
        assert receipt["result"] == result
        assert receipt["disposition"] == "client_observed"
        assert set(receipt["stage_seconds"]) == {"capture", "stt", "graph", "tts"}
        output = capsys.readouterr().out
        assert result["feedback"] in output
        assert "neopakuj" in output
        assert "PRIVATE" not in output
        assert "provider" not in output
    finally:
        await session.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["bug", "evidence"])
async def test_programming_and_reply_evidence_failures_still_fail(
    host: Host,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    files, game, runner, control = host

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("transcriptions"):
            return httpx.Response(200, json={"text": "say hello"})
        if failure == "bug":
            msg = "programming defect"
            raise RuntimeError(msg)
        return httpx.Response(200, content=wav(), headers={"Content-Type": "audio/wav"})

    original_write = files.write_new

    def write(path: Path, content: bytes) -> None:
        if path.name.endswith("-reply.wav"):
            msg = "reply evidence unavailable"
            raise OSError(msg)
        original_write(path, content)

    if failure == "evidence":
        monkeypatch.setattr(files, "write_new", write)
    session = blockworld_voice.VoiceSession(
        files, speech(httpx.MockTransport(handler)), runner, control, reply_language="en"
    )
    try:
        with pytest.raises(RuntimeError if failure == "bug" else OSError):
            await session.begin(wav())
        assert game.commands.count("chat hello") == 1
        receipt = json.loads(next(files.root.glob("*-voice.json")).read_bytes())
        assert receipt["result"]["kind"] == "client_observed"
        assert "reply_failure" not in receipt["result"]
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_tts_cancellation_propagates_without_erasing_the_game_result(host: Host) -> None:
    files, game, runner, control = host
    entered = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("transcriptions"):
            return httpx.Response(200, json={"text": "say hello"})
        entered.set()
        await asyncio.Event().wait()
        return httpx.Response(200, content=wav(), headers={"Content-Type": "audio/wav"})

    session = blockworld_voice.VoiceSession(
        files, speech(httpx.MockTransport(handler)), runner, control, reply_language="en"
    )
    task = session.begin(wav())
    await asyncio.wait_for(entered.wait(), timeout=2)
    await session.stop()
    assert task.cancelled()
    receipt = json.loads(next(files.root.glob("*-voice.json")).read_bytes())
    assert receipt["disposition"] == "client_observed"
    assert receipt["result"]["reply_status"] == "cancelled_server_work_unknown"
    assert receipt["result"]["run_id"] in runner.assist.run_results
    assert game.commands.count("chat hello") == 1


@pytest.mark.asyncio
async def test_unchanged_idle_is_quiet_but_keeps_each_native_run_and_private_event_file(
    host: Host,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files, game, runner, control = host
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, content=wav(), headers={"Content-Type": "audio/wav"})

    session = blockworld_voice.VoiceSession(
        files, speech(httpx.MockTransport(handler)), runner, control, reply_language="en"
    )
    assert runner.behaviors is not None
    clock = [100.0]
    monkeypatch.setattr(runner.behaviors, "clock", lambda: clock[0])
    runner.behaviors.begin(
        BehaviorDirective(kind="idle", task_id="00000000-0000-0000-0000-000000000001", duration_s=5.0)
    )
    try:
        assert (await session.supervisor.tick_once()).kind == "changed"
        first = capsys.readouterr().out
        assert '"behavior": "idle"' in first
        clock[0] += 1.0
        assert (await session.supervisor.tick_once()).kind == "unchanged"
        assert '"behavior":' not in capsys.readouterr().out
        records = [json.loads(path.read_bytes()) for path in files.root.glob("*-behavior.json")]
        assert {record["kind"] for record in records} == {"changed", "unchanged"}
        assert len(runner.queue.jobs) == len(records) == 2
        assert len(list(files.root.glob("*-events.jsonl"))) == 2
        for record in records:
            assert files.root.joinpath(record["events"]).read_text()
            assert record["model_calls"] == record["action_attempts"] == 0
        assert not calls
        assert set(game.commands) <= {"state", "status"}
        # Suppression is specific to idle; another source still gets its notice.
        assert session.supervisor.record is not None
        await session.supervisor.record({"source": "follow", "kind": "unchanged", "run_id": None})
        assert '"behavior": "follow"' in capsys.readouterr().out
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_pre_capture_settlement_has_separate_timing_without_changing_four_stage_keys(
    host: Host,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files, _game, runner, control = host
    entered, release = asyncio.Event(), asyncio.Event()
    client = speech(httpx.MockTransport(lambda _: httpx.Response(200, json={"text": "say hello"})))
    session = blockworld_voice.VoiceSession(files, client, runner, control)
    original_pause = session.supervisor.pause

    async def pause() -> None:
        await original_pause()
        entered.set()
        await release.wait()

    async def capture(*, seconds: int) -> bytes:
        assert release.is_set()
        return wav()

    monkeypatch.setattr(session.supervisor, "pause", pause)
    monkeypatch.setattr(blockworld_voice, "capture_utterance", capture)
    try:
        task = session.begin()
        await asyncio.wait_for(entered.wait(), timeout=2)
        await asyncio.sleep(0.02)
        release.set()
        result = await task
        assert result["kind"] == "client_observed"
        receipt = json.loads(next(files.root.glob("*-voice.json")).read_bytes())
        assert receipt["settlement_seconds"] >= 0.015
        assert set(receipt["stage_seconds"]) == {"capture", "stt", "graph", "tts"}
        assert receipt["stage_seconds"]["capture"] < receipt["settlement_seconds"]
    finally:
        release.set()
        await session.stop()
