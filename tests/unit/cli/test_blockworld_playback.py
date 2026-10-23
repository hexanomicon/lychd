"""Optional speaker stage preserves native game outcomes; no real audio devices."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest
from scripts import blockworld_voice

from lychd.system.services.voice_playback import VoicePlaybackError, VoicePlaybackUnsettled
from tests.unit.cli.test_blockworld_voice import Host, speech, wav
from tests.unit.cli.test_blockworld_voice import host as native_host

host = native_host


def transport(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("transcriptions"):
        return httpx.Response(200, json={"text": "say hello"})
    return httpx.Response(200, content=wav(), headers={"Content-Type": "audio/wav"})


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_playback_is_separate_opt_in_with_separate_timing_and_receipt(
    host: Host, monkeypatch: pytest.MonkeyPatch, *, enabled: bool
) -> None:
    files, game, runner, control = host
    player = AsyncMock(return_value="player_exited")
    monkeypatch.setattr(blockworld_voice, "play_reply", player)
    session = blockworld_voice.VoiceSession(
        files, speech(httpx.MockTransport(transport)), runner, control, reply_language="en", play_replies=enabled
    )
    try:
        result = await session.begin(wav())
        assert result["kind"] == "client_observed"
        assert result["reply_status"] == "generated"
        assert game.commands.count("chat hello") == 1
        assert len(runner.queue.jobs) == 1
        receipt = json.loads(next(files.root.glob("*-voice.json")).read_bytes())
        assert receipt["result"] == result
        if enabled:
            player.assert_awaited_once_with(wav())
            assert result["playback"] == "player_exited"
            assert result["human_hearing"] == "unconfirmed"
            assert receipt["stage_seconds"]["playback"] >= 0
        else:
            player.assert_not_awaited()
            assert result["playback"] == "not_attempted"
            assert "playback" not in receipt["stage_seconds"]
    finally:
        await session.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize("unsettled", [False, True])
async def test_player_failure_keeps_game_result_and_unsettled_player_blocks_capture(
    host: Host, monkeypatch: pytest.MonkeyPatch, *, unsettled: bool
) -> None:
    files, game, runner, control = host
    error = VoicePlaybackUnsettled if unsettled else VoicePlaybackError
    player = AsyncMock(side_effect=error("synthetic player failure"))
    monkeypatch.setattr(blockworld_voice, "play_reply", player)
    session = blockworld_voice.VoiceSession(
        files, speech(httpx.MockTransport(transport)), runner, control, reply_language="sk", play_replies=True
    )
    try:
        result = await session.begin(wav())
        assert result["kind"] == "client_observed"
        assert result["playback"] == ("settlement_unknown" if unsettled else "failed")
        assert result["reply_status"] == "generated"
        assert game.commands.count("chat hello") == 1
        assert runner.assist.run_results[result["run_id"]].kind == "client_observed"
        assert session.stopped.is_set() is unsettled
        receipt = json.loads(next(files.root.glob("*-voice.json")).read_bytes())
        assert receipt["result"] == result
        assert receipt["disposition"] == "client_observed"
        if unsettled:
            with pytest.raises(ValueError, match="stopped"):
                session.begin(wav())
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_stop_during_playback_joins_owned_stage_without_erasing_game_outcome(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    files, game, runner, control = host
    entered, retired = asyncio.Event(), asyncio.Event()

    async def player(_: bytes) -> str:
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            retired.set()
        return "player_exited"

    monkeypatch.setattr(blockworld_voice, "play_reply", player)
    session = blockworld_voice.VoiceSession(
        files, speech(httpx.MockTransport(transport)), runner, control, reply_language="en", play_replies=True
    )
    task = session.begin(wav())
    await asyncio.wait_for(entered.wait(), timeout=2)
    await session.stop()
    assert retired.is_set()
    assert task.cancelled()
    assert game.commands.count("chat hello") == 1
    receipt = json.loads(next(files.root.glob("*-voice.json")).read_bytes())
    assert receipt["disposition"] == "client_observed"
    assert receipt["result"]["playback"] == "interrupted"
    assert receipt["result"]["run_id"] in runner.assist.run_results


@pytest.mark.asyncio
async def test_playback_requires_explicit_reply_language(host: Host) -> None:
    files, _game, runner, control = host
    with pytest.raises(ValueError, match="reply language"):
        blockworld_voice.VoiceSession(files, speech(httpx.MockTransport(transport)), runner, control, play_replies=True)
