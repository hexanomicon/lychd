"""Offline console/voice admission tests; no microphone, providers or game services."""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

import pytest
from scripts.companion_lab import CompanionConsole
from scripts.voice_probe import PrivateWorkspace

from lychd.compositions.blockworld.companion import CompanionResult
from lychd.compositions.blockworld.companion_dialogue import CompanionDialogue
from lychd.compositions.blockworld.companion_memory import CommandRecipe, DialogueLanguage, SessionRecipeStore
from lychd.system.services.companion_session import CompanionSession, SessionResult
from tests.unit.cli.test_companion_lab import ConsoleSession, wav


@pytest.fixture
def files() -> Iterator[PrivateWorkspace]:
    with tempfile.TemporaryDirectory(prefix="lychd-dialogue-") as directory:
        yield PrivateWorkspace(Path(directory), (Path(__file__).resolve().parents[3],))


async def settle(console: CompanionConsole) -> None:
    async with asyncio.timeout(2):
        await asyncio.gather(*console.replies)
        # Python 3.15 may return an already-completed gather synchronously;
        # give the registered set-discard callbacks their turn as well.
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_console_confirmation_queues_original_once_and_review_saves_only_after_two_answers(
    files: PrivateWorkspace,
) -> None:
    session, store = ConsoleSession(), SessionRecipeStore()
    console = CompanionConsole(
        files, cast("CompanionSession", session), dialogue=CompanionDialogue(store), language="sk"
    )
    events: list[dict[str, Any]] = []
    console.present = Mock(side_effect=events.append)
    assert (await console.submit("čakaj")).kind == "clarification"
    assert session.enqueued == []
    assert (await console.submit("áno")).kind == "applied"
    await settle(console)
    assert len(session.enqueued) == 1
    original = session.enqueued[0]
    assert original.transcript == "čakaj"
    assert events[-1]["phase"] == "review"
    await console.submit("áno")
    assert await store.find("sk", "čakaj") is None
    await console.submit("áno bez potvrdenia")
    recipe = await store.find("sk", "čakaj")
    assert recipe is not None
    assert recipe.skip_confirmation
    await console.submit("čakaj")
    await settle(console)
    assert len(session.enqueued) == 2
    assert session.enqueued[1].request_id != original.request_id
    assert events[-1].get("phase") != "review"


@pytest.mark.asyncio
async def test_stop_cancels_pending_memory_read_and_keeps_ordinary_stop_independent(files: PrivateWorkspace) -> None:
    entered = asyncio.Event()

    class SlowMemory(SessionRecipeStore):
        async def find(self, language: DialogueLanguage, phrase: str) -> CommandRecipe | None:
            del language, phrase
            entered.set()
            await asyncio.Event().wait()

    session = ConsoleSession()
    console = CompanionConsole(files, cast("CompanionSession", session), dialogue=CompanionDialogue(SlowMemory()))
    future = console.submit("idle")
    await entered.wait()
    await console.stop()
    assert future.cancelled()
    assert session.enqueued == []
    assert (await console.submit("yes")).kind == "clarification"
    assert session.enqueued == []


@pytest.mark.asyncio
async def test_delayed_voice_yes_cannot_confirm_newer_typed_proposal(files: PrivateWorkspace) -> None:
    session = ConsoleSession()
    console = CompanionConsole(
        files, cast("CompanionSession", session), dialogue=CompanionDialogue(SessionRecipeStore(), allow_time=True)
    )
    console.present = Mock()
    await console.submit("idle")
    entered, release = asyncio.Event(), asyncio.Event()

    async def transcribe(*args: Any, **kwargs: Any) -> Any:
        entered.set()
        await release.wait()
        return SimpleNamespace(text="yes", model_dump_json=lambda: "{}")

    console.speech = cast("Any", SimpleNamespace(transcribe=transcribe))
    path = files.root / "answer.wav"
    files.write_new(path, wav())
    voice = console.begin_voice(path)
    await entered.wait()
    await console.submit("time night")
    release.set()
    await voice
    assert session.enqueued == []
    await console.submit("yes")
    await settle(console)
    assert len(session.enqueued) == 1
    assert session.enqueued[0].action.kind == "time"


@pytest.mark.asyncio
async def test_post_enqueue_failure_stays_unknown_without_replay(files: PrivateWorkspace) -> None:
    class LostAdmission(ConsoleSession):
        def enqueue(self, request: Any, **kwargs: Any) -> Any:
            super().enqueue(request, **kwargs)
            msg = "acknowledgement lost"
            raise RuntimeError(msg)

    session = LostAdmission()
    console = CompanionConsole(
        files,
        cast("CompanionSession", session),
        dialogue=CompanionDialogue(SessionRecipeStore(), confirmation="never"),
    )
    console.present = Mock()
    outcome = await console.submit("idle")
    assert outcome.kind == "unknown"
    assert len(session.enqueued) == 1
    await console.submit("yes")
    assert len(session.enqueued) == 1


@pytest.mark.asyncio
async def test_confirmation_outcome_survives_its_evidence_write_failure(
    files: PrivateWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = ConsoleSession()
    console = CompanionConsole(
        files, cast("CompanionSession", session), dialogue=CompanionDialogue(SessionRecipeStore())
    )
    events: list[dict[str, Any]] = []
    console.present = Mock(side_effect=events.append)
    original_write = files.write_new

    def write(path: Path, content: bytes) -> None:
        if path.name.endswith("-dialogue-outcome.json"):
            msg = "synthetic evidence failure"
            raise OSError(msg)
        original_write(path, content)

    monkeypatch.setattr(files, "write_new", write)
    await console.submit("idle")
    result = await console.submit("yes")
    await settle(console)
    assert result.kind == "applied"
    relays = [event for event in events if event.get("kind") == "dialogue_outcome"]
    assert len(relays) == 1
    assert relays[0]["game_kind"] == "applied"
    assert relays[0]["evidence_status"] == "failed"
    assert len(session.enqueued) == 1


@pytest.mark.asyncio
async def test_stop_keeps_confirmation_relay_owned_by_native_result(files: PrivateWorkspace) -> None:
    entered = asyncio.Event()

    class DelayedSession(ConsoleSession):
        def enqueue(self, request: Any, **kwargs: Any) -> asyncio.Future[SessionResult]:
            del kwargs
            self.enqueued.append(request)
            self.pending: asyncio.Future[SessionResult] = asyncio.get_running_loop().create_future()
            entered.set()
            return self.pending

        def stop(self) -> Any:
            barrier = super().stop()

            async def finish() -> CompanionResult:
                request = self.enqueued[0]
                applied = CompanionResult(request_id=request.request_id, kind="applied", detail="observed fake result")
                self.pending.set_result(
                    SessionResult(request.request_id, "00000000-0000-4000-8000-000000000001", "applied", "", applied)
                )
                return await barrier

            return finish()

    session = DelayedSession()
    console = CompanionConsole(
        files, cast("CompanionSession", session), dialogue=CompanionDialogue(SessionRecipeStore())
    )
    events: list[dict[str, Any]] = []
    console.present = Mock(side_effect=events.append)
    await console.submit("idle")
    confirmation = console.submit("yes")
    await entered.wait()
    await console.stop()
    assert confirmation.cancelled()
    relays = [event for event in events if event.get("kind") == "dialogue_outcome"]
    assert len(relays) == 1
    assert relays[0]["action_request_id"] == session.enqueued[0].request_id
    assert relays[0]["request_id"] != relays[0]["action_request_id"]
    assert relays[0]["game_kind"] == "applied"
