"""Human console integration over native owners and controlled local speech transports."""

from __future__ import annotations

import asyncio
import io
import json
import time
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from rich.console import Console
from scripts import companion_lab
from scripts.voice_probe import PrivateWorkspace

from lychd.compositions.blockworld.companion import CompanionService
from lychd.system.services.companion_session import CompanionSession, LocalCompanionRunner
from lychd.system.services.voice_playback import VoicePlaybackUnsettled
from tests.integration.test_companion import FakeBridge, policy
from tests.unit.cli.test_companion_lab import ConsolePipe, ConsoleSession, speech, wav
from tests.unit.cli.test_companion_lab import (
    console_pipe as console_pipe,  # noqa: PLC0414 - re-export shared pytest fixture
)
from tests.unit.cli.test_companion_lab import files as files  # noqa: PLC0414 - re-export shared pytest fixture


def human_console(
    files: PrivateWorkspace, session: CompanionSession, **options: Any
) -> tuple[companion_lab.CompanionConsole, io.StringIO]:
    output = io.StringIO()
    console = companion_lab.CompanionConsole(files, session, output="human", language="en", **options)
    console._terminal = Console(file=output, width=240, color_system=None, force_terminal=False)  # pyright: ignore[reportPrivateUsage]
    return console, output


@pytest.mark.asyncio
async def test_human_applied_controller_uses_correlated_deadline_and_formatting_time(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeBridge()
    bridge = fake.bridge()
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)
    console, output = human_console(files, session)
    session.record = console.record
    rendered_at: list[int] = []
    feedback = companion_lab.feedback_text

    def observed(request: Any, result: Any, **kwargs: Any) -> str:
        rendered_at.append(kwargs["at_ms"])
        return feedback(request, result, **kwargs)

    monkeypatch.setattr(companion_lab, "feedback_text", observed)
    await session.open()
    try:
        before = int(time.time() * 1000)
        result = await console.submit("idle")
        await asyncio.gather(*console.replies)
        after = int(time.time() * 1000)
        assert result.result is not None
        assert result.result.controller_expires_at_ms == fake.requests[0]["expires_at_ms"]
        assert len(rendered_at) == 1
        assert before <= rendered_at[0] <= after
        assert "Control for at most" in output.getvalue()
        assert "Check current state with state." in output.getvalue()
        assert len(fake.requests) == 1
        assert len(session.runner.queue.jobs) == 1
        native = json.loads(next(files.root.glob("*-native.json")).read_bytes())
        assert native["result"]["controller_expires_at_ms"] == result.result.controller_expires_at_ms
    finally:
        await session.aclose()


@pytest.mark.asyncio
async def test_human_reader_joins_real_queue_status_result_and_priority_stop(
    files: PrivateWorkspace, console_pipe: ConsolePipe, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeBridge()
    fake.delay = True
    bridge = fake.bridge()
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)
    console, output = human_console(files, session)
    session.record = console.record
    status_seen, stopped = asyncio.Event(), asyncio.Event()
    events: list[dict[str, Any]] = []
    original = console.present

    def observed(event: dict[str, Any]) -> None:
        events.append(event)
        original(event)
        if event.get("kind") == "status":
            status_seen.set()
        if event.get("control") == "stop" and event.get("kind") == "applied":
            stopped.set()

    monkeypatch.setattr(console, "present", observed)
    await session.open()
    running = asyncio.create_task(console.run())
    try:
        console_pipe.send(b"say [bold]first[/]\n")
        await asyncio.wait_for(fake.action_started.wait(), 2)
        console_pipe.send(b"say second\n:status\n")
        before = fake.reads, len(fake.requests), len(session.runner.queue.jobs)
        await asyncio.wait_for(status_seen.wait(), 2)
        assert before == (fake.reads, len(fake.requests), len(session.runner.queue.jobs))
        status = next(event for event in events if event.get("kind") == "status")
        assert len(status["session"]["pending"]) == 1
        assert status["session"]["current"]["request_id"] == fake.requests[0]["action_id"]
        assert "Pending inputs: 1/8." in output.getvalue()
        console_pipe.send(b"stop\n")
        await asyncio.wait_for(stopped.wait(), 2)
        assert len(fake.requests) == 1
        assert not console.replies
        console_pipe.send(b":quit\n")
        await asyncio.wait_for(running, 2)
        text = output.getvalue()
        assert "Stop requested; acknowledgement pending." in text
        assert "Server acknowledged stop." in text
        assert "Result (cancelled)" in text
        assert "[bold]first[/]" not in text  # private command body is not echoed by queue/status
        assert all(
            result.run_id is None
            for result in session.outcomes.values()
            if result.reason == "cancelled_before_execution"
        )
    finally:
        fake.release_action.set()
        if not running.done():
            running.cancel()
        await asyncio.gather(running, return_exceptions=True)
        await session.aclose()


@pytest.mark.parametrize("output_mode", ["human", "json"])
@pytest.mark.asyncio
async def test_voice_original_words_are_private_opt_in_before_strict_refusal(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], output_mode: str
) -> None:
    words = "[bold]unsupported[/]\n\u202e"
    client = speech(httpx.MockTransport(lambda _: httpx.Response(200, json={"text": words})))
    state = ConsoleSession()
    stream = io.StringIO()
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", state), speech=client, language="en", output=cast("Any", output_mode)
    )
    console._terminal = Console(file=stream, width=240, color_system=None, force_terminal=False)  # pyright: ignore[reportPrivateUsage]
    events: list[dict[str, Any]] = []
    original = console.present

    def observed(event: dict[str, Any]) -> None:
        events.append(event)
        original(event)

    monkeypatch.setattr(console, "present", observed)
    source = files.root / "input.wav"
    files.write_new(source, wav())
    await console.begin_voice(source)
    (voice_file,) = files.root.glob("*-voice.json")
    voice = json.loads(voice_file.read_bytes())
    (transcript_file,) = files.root.glob("*-transcript.json")
    assert json.loads(transcript_file.read_bytes())["text"] == voice["transcript"] == words
    assert not state.enqueued
    assert console._voice_operation is None  # pyright: ignore[reportPrivateUsage]
    if output_mode == "human":
        heard = next(event for event in events if event.get("kind") == "heard")
        refused = next(event for event in events if event.get("kind") == "voice_refused")
        assert heard["request_id"] == refused["request_id"] == voice["request_id"]
        assert events.index(heard) < events.index(refused)
        text = stream.getvalue()
        assert "[bold]unsupported[/]\\u000a\\u202e" in text
        assert "\u202e" not in text
        assert text.index("Recognized") < text.index("Audio input refused")
        assert capsys.readouterr().out == ""
    else:
        assert not any(event.get("kind") == "heard" for event in events)
        messages = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
        assert all("text" not in event and "transcript" not in event for event in messages)
        assert not stream.getvalue()


@pytest.mark.parametrize("before_start", [False, True])
@pytest.mark.asyncio
async def test_stop_clears_waiting_or_held_transcription_without_fake_microphone_state(
    files: PrivateWorkspace, *, before_start: bool
) -> None:
    entered = asyncio.Event()

    async def handler(_request: httpx.Request) -> httpx.Response:
        entered.set()
        await asyncio.Event().wait()
        raise AssertionError

    state = ConsoleSession()
    console, output = human_console(files, cast("CompanionSession", state), speech=speech(httpx.MockTransport(handler)))
    source = files.root / "input.wav"
    files.write_new(source, wav())
    task = console.begin_voice(source)
    initial = console._voice_operation  # pyright: ignore[reportPrivateUsage]
    assert initial is not None
    assert initial.phase == "waiting_audio"
    if not before_start:
        await asyncio.wait_for(entered.wait(), 2)
        assert console._voice_operation is not None  # pyright: ignore[reportPrivateUsage]
        assert console._voice_operation.phase == "transcribing"  # pyright: ignore[reportPrivateUsage]
    await console.stop()
    assert task.done()
    assert console._voice_operation is None  # pyright: ignore[reportPrivateUsage]
    assert not state.enqueued
    assert entered.is_set() is not before_start
    assert "requested microphone" not in output.getvalue()


@pytest.mark.asyncio
async def test_presentation_and_voice_retention_failure_preserve_one_known_native_outcome(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeBridge()
    bridge = fake.bridge()
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)
    client = speech(httpx.MockTransport(lambda _: httpx.Response(200, json={"text": "state"})))
    console, _output = human_console(files, session, speech=client)
    session.record = console.record
    source = files.root / "input.wav"
    files.write_new(source, wav())
    original_write = files.write_new
    events: list[dict[str, Any]] = []
    original_present = console.present

    def write(path: Path, content: bytes) -> None:
        if path.name.endswith("-voice.json"):
            msg = "private disk failure"
            raise OSError(msg)
        original_write(path, content)

    def broken_print(*_args: Any, **_kwargs: Any) -> None:
        msg = "private output failure"
        raise OSError(msg)

    def observed(event: dict[str, Any]) -> None:
        events.append(event)
        original_present(event)

    assert console._terminal is not None  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(console._terminal, "print", broken_print)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(console, "present", observed)
    monkeypatch.setattr(files, "write_new", write)
    await session.open()
    try:
        await console.begin_voice(source)
        await asyncio.gather(*console.replies)
        assert len(fake.requests) == 1
        (result,) = session.outcomes.values()
        assert result.kind == "applied"
        assert result.evidence_status == "recorded"
        assert result.run_id == fake.requests[0]["run_id"]
        (failure,) = [event for event in events if event.get("kind") == "voice_evidence_failed"]
        assert failure["request_id"] == result.request_id
        assert console.status()["presentation_failed"] is True
        assert not console.replies
        await console.stop()
        assert fake.stop_ids
    finally:
        await session.aclose()
    assert not session.snapshot().opened


@pytest.mark.parametrize(
    "failed_artifact",
    ["native.json", "reply.wav", "reply.json", "reply-evidence.json", "reply-evidence-playback-unsettled"],
)
@pytest.mark.asyncio
async def test_human_output_distinguishes_applied_game_from_native_audio_and_reply_retention_failures(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch, failed_artifact: str
) -> None:
    fake = FakeBridge()
    bridge = fake.bridge()
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)
    client = speech(
        httpx.MockTransport(lambda _: httpx.Response(200, content=wav(), headers={"content-type": "audio/wav"}))
    )
    console, output = human_console(
        files,
        session,
        speech=client,
        reply_language="en",
        play_replies=failed_artifact in {"reply.wav", "reply.json", "reply-evidence-playback-unsettled"},
    )

    async def player(_content: bytes) -> str:
        assert failed_artifact == "reply-evidence-playback-unsettled"
        msg = "private player retirement failure"
        raise VoicePlaybackUnsettled(msg)

    monkeypatch.setattr(companion_lab, "play_reply", player)
    session.record = console.record
    original_write = files.write_new

    def write(path: Path, content: bytes) -> None:
        suffix = "reply-evidence.json" if failed_artifact == "reply-evidence-playback-unsettled" else failed_artifact
        if path.name.endswith("-" + suffix):
            msg = "private write failure"
            raise OSError(msg)
        original_write(path, content)

    monkeypatch.setattr(files, "write_new", write)
    await session.open()
    try:
        result = await console.submit("state")
        await asyncio.gather(*console.replies)
        assert result.kind == "applied"
        assert result.run_id == fake.requests[0]["run_id"]
        assert len(fake.requests) == 1
        assert "Result (applied)" in output.getvalue()
        expected = {
            "native.json": "Result retention failed.",
            "reply.wav": "audio retention failed; playback: not attempted; evidence: retained.",
            "reply.json": "audio retention failed; playback: not attempted; evidence: retained.",
            "reply-evidence-playback-unsettled": "playback: settlement unknown; evidence: failed.",
            "reply-evidence.json": "playback: not attempted; evidence: failed.",
        }
        assert expected[failed_artifact] in output.getvalue()
        assert "Result (unknown)" not in output.getvalue()
        assert "private write failure" not in output.getvalue()
        assert console.status()["audio_blocked"] is (failed_artifact == "reply-evidence-playback-unsettled")
        assert result.evidence_status == ("failed" if failed_artifact == "native.json" else "recorded")
    finally:
        await console.stop()
        await session.aclose()


@pytest.mark.asyncio
async def test_human_native_custody_failure_is_visible_after_early_queue_cancellation(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeBridge()
    fake.delay = True
    bridge = fake.bridge()
    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge)
    console, output = human_console(files, session)
    session.record = console.record
    original_write = files.write_new
    failed_identity: str | None = None

    def write(path: Path, content: bytes) -> None:
        if path.name.endswith("-native.json") and json.loads(content)["request_id"] == failed_identity:
            msg = "private queue custody failure"
            raise OSError(msg)
        original_write(path, content)

    monkeypatch.setattr(files, "write_new", write)
    await session.open()
    try:
        active = console.submit("say active")
        await asyncio.wait_for(fake.action_started.wait(), 2)
        queued = console.submit("say queued")
        failed_identity = session.snapshot().pending[0].request_id
        await console.stop()
        cancelled = await queued
        await active
        assert cancelled.run_id is None
        assert cancelled.reason == "cancelled_before_execution"
        assert session.outcomes[failed_identity].evidence_status == "failed"
        assert f"[{failed_identity}] Result retention failed." in output.getvalue()
        assert len(fake.requests) == 1
        assert not console.replies
    finally:
        fake.release_action.set()
        await session.aclose()
