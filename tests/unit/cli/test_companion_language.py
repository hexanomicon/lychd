"""Select only future speech locales after existing occurrence ownership retires."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any, cast

import httpx
import pytest
from scripts import companion_lab
from scripts.voice_probe import PrivateWorkspace

from lychd.cli.companion_view import Language, format_companion_event
from lychd.domain.speech_probe import SpeechProfile
from lychd.system.services.companion_session import CompanionSession, SessionResult
from lychd.system.services.speech_probe import SpeechProbe
from tests.unit.cli.test_companion_lab import ConsolePipe, ConsoleSession, speech, wav
from tests.unit.cli.test_companion_lab import (
    console_pipe as console_pipe,  # noqa: PLC0414 - expose the existing pytest fixture
)
from tests.unit.cli.test_companion_lab import (
    files as files,  # noqa: PLC0414 - preserve private workspace fixture ownership
)
from tests.unit.domain.test_speech_probe import profile_v2


def select(console: companion_lab.CompanionConsole, text: str) -> None:
    console._handle_line(text, console._capture_line())  # pyright: ignore[reportPrivateUsage]


def configured(files: PrivateWorkspace, **kwargs: Any) -> companion_lab.CompanionConsole:
    return companion_lab.CompanionConsole(files, cast("CompanionSession", ConsoleSession()), speech=speech(), **kwargs)


@pytest.mark.parametrize(
    ("initial_reply", "command", "expected"),
    [
        (None, ":language cs", ("cs", None)),
        ("en", ":language sk", ("sk", "en")),
        (None, ":language cs cs", ("cs", "cs")),
        ("sk", ":language en cs", ("en", "cs")),
    ],
)
def test_explicit_selection_preserves_omitted_reply_and_playback_choice(
    files: PrivateWorkspace,
    initial_reply: str | None,
    command: str,
    expected: tuple[str, str | None],
) -> None:
    console = configured(files, language="en", reply_language=initial_reply)
    select(console, command)
    assert (console.language, console.reply_language) == expected
    assert console.play_replies is False
    assert not cast("ConsoleSession", console.session).enqueued
    assert console.voice_task is None
    assert not console.replies


@pytest.mark.parametrize(
    "text",
    [
        ":language sk off",
        ":language auto",
        ":language de",
        ":language SK",
        ":language cs de",
        ":language cs cs extra",
        ":languagefoo cs",
    ],
)
def test_invalid_selection_is_atomic_and_never_enters_native_queue(files: PrivateWorkspace, text: str) -> None:
    console = configured(files, language="en", reply_language="en")
    with pytest.raises(ValueError, match=r"Language selection|Use :language"):
        select(console, text)
    assert (console.language, console.reply_language) == ("en", "en")
    assert not cast("ConsoleSession", console.session).enqueued


@pytest.mark.parametrize("operation", ["transcriber", "synthesizer"])
def test_selected_profile_must_declare_both_requested_locales_before_mutation(
    files: PrivateWorkspace, operation: str
) -> None:
    profile = speech().profile
    assert isinstance(profile, SpeechProfile)
    model = getattr(profile, operation).model_copy(update={"languages": ("en",)})
    selected = SpeechProbe(profile.model_copy(update={operation: model}))
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", ConsoleSession()), speech=selected, language="en", reply_language="en"
    )
    with pytest.raises(ValueError, match="not declared"):
        select(console, ":language cs cs")
    assert (console.language, console.reply_language) == ("en", "en")


def test_query_without_speech_is_observational_but_selection_requires_profile(
    files: PrivateWorkspace, capsys: pytest.CaptureFixture[str]
) -> None:
    console = companion_lab.CompanionConsole(files, cast("CompanionSession", ConsoleSession()))
    select(console, ":language")
    assert '"kind": "language"' in capsys.readouterr().out
    with pytest.raises(ValueError, match="profile"):
        select(console, ":language sk")
    assert console.language is console.reply_language is None
    assert not cast("ConsoleSession", console.session).enqueued


@pytest.mark.parametrize("fence", ["stale", "expired", "ineligible", "stopping"])
def test_reader_fences_apply_to_language_controls(files: PrivateWorkspace, fence: str) -> None:
    console = configured(files, language="en", reply_language="en")
    item = console._capture_line()  # pyright: ignore[reportPrivateUsage]
    if fence == "stale":
        cast("ConsoleSession", console.session).generation += 1
    elif fence == "expired":
        item = replace(item, expires_at_ms=1)
    elif fence == "ineligible":
        item = replace(item, eligible=False)
    else:
        console._stopping = 1  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(ValueError, match=r"predates stop|expired"):
        console._handle_line(":language cs cs", item)  # pyright: ignore[reportPrivateUsage]
    assert (console.language, console.reply_language) == ("en", "en")


@pytest.mark.parametrize("stage", ["capture_wait", "transcription", "synthesis"])
@pytest.mark.asyncio
async def test_busy_voice_and_reply_keep_original_locales_until_retirement(  # noqa: PLR0915 - keep one owned busy-to-retired scenario together
    files: PrivateWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    entered, release = asyncio.Event(), asyncio.Event()
    client = speech(
        httpx.MockTransport(
            lambda request: (
                httpx.Response(200, json={"text": "state"})
                if request.url.path.endswith("/transcriptions")
                else httpx.Response(200, content=wav(), headers={"content-type": "audio/wav"})
            )
        )
    )
    transcribe, synthesize = client.transcribe, client.synthesize
    observed: list[tuple[str, str | None]] = []

    async def recognition(*args: Any, **kwargs: Any) -> Any:
        observed.append(("transcription", kwargs.get("language")))
        if stage == "transcription":
            entered.set()
            await release.wait()
        return await transcribe(*args, **kwargs)

    async def generation(*args: Any, **kwargs: Any) -> Any:
        observed.append(("synthesis", kwargs.get("language")))
        if stage == "synthesis":
            entered.set()
            await release.wait()
        return await synthesize(*args, **kwargs)

    monkeypatch.setattr(client, "transcribe", recognition)
    monkeypatch.setattr(client, "synthesize", generation)
    state = ConsoleSession()
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", state), speech=client, language="en", reply_language="en"
    )
    events: list[dict[str, Any]] = []
    monkeypatch.setattr(console, "present", events.append)
    path = files.root / "input.wav"
    files.write_new(path, wav())
    if stage == "capture_wait":
        await console._capture_lock.acquire()  # pyright: ignore[reportPrivateUsage]
    voice = console.begin_voice(path)
    if stage == "capture_wait":
        await asyncio.sleep(0)
    else:
        await entered.wait()
    select(console, ":language cs cs")
    assert events[-1]["kind"] == "language_busy"
    assert (console.language, console.reply_language) == ("en", "en")
    select(console, ":language")
    assert events[-1]["language"] == events[-1]["reply_language"] == "en"
    assert "feedback" not in events[-1]
    assert "evidence" not in events[-1]
    release.set()
    if stage == "capture_wait":
        console._capture_lock.release()  # pyright: ignore[reportPrivateUsage]
    await voice
    await asyncio.gather(*console.replies)
    await asyncio.sleep(0)
    assert observed == [("transcription", "en"), ("synthesis", "en")]
    original = state.enqueued[0]
    original_document = original.model_dump_json()
    select(console, ":language cs cs")
    assert (console.language, console.reply_language) == ("cs", "cs")
    assert state.enqueued == [original]
    assert original.generation == 0
    assert original.source == "transcript"
    await console.begin_voice(path)
    await asyncio.gather(*console.replies)
    await asyncio.sleep(0)
    assert observed[-2:] == [("transcription", "cs"), ("synthesis", "cs")]
    assert state.enqueued[0].model_dump_json() == original_document
    assert state.enqueued[1].request_id != original.request_id


@pytest.mark.asyncio
async def test_pending_native_and_cancelled_caller_still_block_locale_mutation(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Pending(ConsoleSession):
        def enqueue(self, request: Any, **kwargs: Any) -> asyncio.Future[SessionResult]:
            completed = super().enqueue(request, **kwargs)
            self.value = completed.result()
            self.native: asyncio.Future[SessionResult] = asyncio.get_running_loop().create_future()
            return self.native

    state = Pending()
    console = companion_lab.CompanionConsole(files, cast("CompanionSession", state), speech=speech(), language="en")
    events: list[dict[str, Any]] = []
    monkeypatch.setattr(console, "present", events.append)
    caller = console.submit("state")
    caller.cancel()
    select(console, ":language cs")
    assert events[-1]["kind"] == "language_busy"
    assert not state.native.done()
    assert console.language == "en"
    state.native.set_result(state.value)
    await asyncio.gather(*console.replies)
    await asyncio.sleep(0)
    select(console, ":language cs")
    assert console.language == "cs"
    assert caller.cancelled()


@pytest.mark.asyncio
async def test_same_reader_batch_applies_configuration_before_fresh_record_and_refuses_later_switch(
    files: PrivateWorkspace,
    console_pipe: ConsolePipe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    language_selected, busy = asyncio.Event(), asyncio.Event()
    events: list[dict[str, Any]] = []

    def message(event: dict[str, Any]) -> None:
        events.append(event)
        if event.get("kind") == "language":
            language_selected.set()
        if event.get("kind") == "language_busy":
            busy.set()

    async def capture(**kwargs: Any) -> bytes:
        del kwargs
        return wav()

    monkeypatch.setattr(companion_lab, "_message", message)
    monkeypatch.setattr(companion_lab, "capture_utterance", capture)
    client = speech(
        httpx.MockTransport(
            lambda request: (
                httpx.Response(200, json={"text": "state"})
                if request.url.path.endswith("/transcriptions")
                else httpx.Response(200, content=wav(), headers={"content-type": "audio/wav"})
            )
        )
    )
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", ConsoleSession()), speech=client, language="en", reply_language="en"
    )
    task = asyncio.create_task(console.run())
    try:
        await asyncio.sleep(0)
        console_pipe.send(b":language cs cs\n:record 1\n:language en en\n")
        await asyncio.wait_for(language_selected.wait(), 2)
        await asyncio.wait_for(busy.wait(), 2)
        assert (console.language, console.reply_language) == ("cs", "cs")
        console_pipe.eof()
        await asyncio.wait_for(task, 2)
        assert next(e for e in events if e.get("kind") == "language")["language"] == "cs"
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize(
    ("language", "selected", "busy"),
    [
        ("sk", "Vybrané jazyky", "Jazyk sa nezmenil"),
        ("cs", "Vybrané jazyky", "Jazyk se nezměnil"),
        ("en", "Selected languages", "Language unchanged"),
    ],
)
def test_language_projection_is_closed_localized_and_content_free(language: Language, selected: str, busy: str) -> None:
    line = format_companion_event(
        {"kind": "language", "request_id": "r", "language": "cs", "reply_language": None, "PRIVATE": "secret"},
        language=language,
    )
    assert line is not None
    assert selected in line
    assert "cs" in line
    assert "secret" not in line
    assert busy in (format_companion_event({"kind": "language_busy", "request_id": "r"}, language=language) or "")
    assert "secret" not in (format_companion_event({"kind": "language", "language": "secret"}, language=language) or "")


@pytest.mark.parametrize("playback", [False, True])
def test_selection_preserves_existing_playback_preference(files: PrivateWorkspace, *, playback: bool) -> None:
    console = configured(files, language="en", reply_language="en", play_replies=playback)
    select(console, ":language sk cs")
    assert console.play_replies is playback


def test_selection_does_not_reopen_unknown_audio_or_change_target_authority(files: PrivateWorkspace) -> None:
    console = configured(files, language="en", reply_language="en")
    console._audio_blocked = True  # pyright: ignore[reportPrivateUsage]
    before = console._capture_line()  # pyright: ignore[reportPrivateUsage]
    select(console, ":language cs cs")
    assert console._audio_blocked is True  # pyright: ignore[reportPrivateUsage]
    assert console.target_id is None
    assert console.session.capture_generation() == before.generation
    with pytest.raises(ValueError, match="settle"):
        console.begin_voice()


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
def test_independent_whisper_and_synthesis_bindings_preserve_profile(files: PrivateWorkspace, language: str) -> None:
    profile = profile_v2()
    client = SpeechProbe(profile)
    console = companion_lab.CompanionConsole(
        files, cast("CompanionSession", ConsoleSession()), speech=client, language="en", reply_language="en"
    )
    select(console, f":language {language} sk")
    assert console.language == language
    assert console.reply_language == "sk"
    assert client.profile.digest == profile.digest
    assert client.profile.transcriber_binding == profile.transcriber_binding
    assert client.profile.synthesizer_binding == profile.synthesizer_binding
