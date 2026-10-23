"""Real local held-control HTTP through the existing console and native Graph, with inert audio."""

from __future__ import annotations

import asyncio
import io
import json
import time
import wave
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx
import pytest
from scripts import companion_lab
from scripts.voice_probe import PrivateWorkspace

from tests.integration.test_companion_control import connected, gesture, known
from tests.unit.cli.test_companion_lab import files as files  # noqa: PLC0414 - existing private fixture


def waveform() -> bytes:
    content = io.BytesIO()
    with wave.open(content, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16_000)
        writer.writeframes(b"\x01\x00" * 16_000)
    return content.getvalue()


@dataclass
class Recorder:
    entered: asyncio.Event = field(default_factory=asyncio.Event)
    calls: int = 0
    cancelled: bool = False
    before_return: Callable[[], None] | None = None

    async def capture(
        self,
        *,
        released: asyncio.Event,
        max_seconds: int,
        on_started: Callable[[], None],
        on_finishing: Callable[[], None],
    ) -> bytes:
        assert max_seconds == 15
        self.calls += 1
        on_started()
        self.entered.set()
        try:
            await released.wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        on_finishing()
        if self.before_return is not None:
            self.before_return()
        return waveform()


def released(raw: bytes) -> bytes:
    original = json.loads(raw)
    now = int(time.time() * 1000)
    return json.dumps(
        {
            **original,
            "released_at_ms": now,
            "release_before_ms": min(now + 3000, original["expires_at_ms"]),
        }
    ).encode()


async def post(client: httpx.AsyncClient, path: str, raw: bytes) -> httpx.Response:
    return await client.post(path, content=raw, headers={"Content-Type": "application/json"})


@pytest.mark.asyncio
async def test_held_release_crosses_once_into_same_native_run_after_transcription(
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    stt: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        stt.append(request)
        return httpx.Response(200, json={"text": "Čakaj."})

    async with connected(files, unused_tcp_port, monkeypatch, handler, hold_seconds=15) as (
        control,
        console,
        fake,
        client,
        fixed_captures,
    ):
        recorder = Recorder()
        monkeypatch.setattr(companion_lab, "capture_held_utterance", recorder.capture)
        identity, raw = gesture(control)
        assert (await post(client, "/v1/hold", raw)).status_code == 202
        await asyncio.wait_for(recorder.entered.wait(), 1)
        assert not stt
        assert not fake.requests
        operation = (await client.get("/v1/operations/" + identity)).json()
        assert operation["phase"] == "recording"
        finish = released(raw)
        assert (await post(client, "/v1/release", finish)).status_code == 202
        await asyncio.wait_for(fake.action_started.wait(), 2)
        await asyncio.gather(*console.replies)
        operation = await known(client, identity)
        assert operation["game_kind"] == "applied"
        assert len(stt) == recorder.calls == 1
        assert len(fake.requests) == 1
        assert not fixed_captures
        assert fake.requests[0]["action_id"] == identity
        voice = json.loads((files.root / f"{identity}-voice.json").read_bytes())
        assert voice["expires_at_ms"] == json.loads(raw)["expires_at_ms"]
        assert (files.root / f"{identity}-source.wav").read_bytes() == waveform()
        assert (await post(client, "/v1/release", finish)).status_code == 200
        assert (await post(client, "/v1/hold", raw)).status_code == 200
        assert len(stt) == recorder.calls == 1
        assert len(fake.requests) == 1


@pytest.mark.asyncio
async def test_release_before_start_keeps_later_http_start_inert(
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    stt: list[httpx.Request] = []

    def unexpected_stt(request: httpx.Request) -> httpx.Response:
        stt.append(request)
        return httpx.Response(500)

    async with connected(files, unused_tcp_port, monkeypatch, unexpected_stt, hold_seconds=15) as (
        control,
        console,
        fake,
        client,
        _fixed,
    ):
        recorder = Recorder()
        monkeypatch.setattr(companion_lab, "capture_held_utterance", recorder.capture)
        identity, raw = gesture(control)
        assert (await post(client, "/v1/release", released(raw))).status_code == 200
        assert (await post(client, "/v1/hold", raw)).status_code == 409
        assert (await known(client, identity))["status"] == "refused"
        assert recorder.calls == 0
        assert not stt
        assert not fake.requests
        assert not console.session.run_ids


@pytest.mark.asyncio
async def test_release_while_waiting_for_audio_never_launches_later(
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    stt: list[httpx.Request] = []

    def unexpected_stt(request: httpx.Request) -> httpx.Response:
        stt.append(request)
        return httpx.Response(500)

    async with connected(files, unused_tcp_port, monkeypatch, unexpected_stt, hold_seconds=15) as (
        control,
        console,
        fake,
        client,
        _fixed,
    ):
        recorder = Recorder()
        monkeypatch.setattr(companion_lab, "capture_held_utterance", recorder.capture)
        await console._capture_lock.acquire()  # pyright: ignore[reportPrivateUsage]
        try:
            identity, raw = gesture(control)
            assert (await post(client, "/v1/hold", raw)).status_code == 202
            assert (await post(client, "/v1/release", released(raw))).status_code == 202
        finally:
            console._capture_lock.release()  # pyright: ignore[reportPrivateUsage]
        assert console.voice_task is not None
        await console.voice_task
        assert (await known(client, identity))["status"] == "refused"
        assert recorder.calls == 0
        assert not stt
        assert not fake.requests


@pytest.mark.parametrize("case", ["stop", "expired"])
@pytest.mark.asyncio
async def test_hold_stop_or_original_deadline_blocks_transcription(
    files: PrivateWorkspace, unused_tcp_port: int, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    stt: list[httpx.Request] = []

    def unexpected_stt(request: httpx.Request) -> httpx.Response:
        stt.append(request)
        return httpx.Response(500)

    async with connected(files, unused_tcp_port, monkeypatch, unexpected_stt, hold_seconds=15) as (
        control,
        console,
        fake,
        client,
        _fixed,
    ):
        recorder = Recorder()
        monkeypatch.setattr(companion_lab, "capture_held_utterance", recorder.capture)
        _identity, raw = gesture(control)
        assert (await post(client, "/v1/hold", raw)).status_code == 202
        await asyncio.wait_for(recorder.entered.wait(), 1)
        if case == "stop":
            _stop_id, stop_raw = gesture(control, "stop")
            assert (await post(client, "/v1/stop", stop_raw)).status_code == 202
            assert console.voice_task is not None
            await asyncio.gather(console.voice_task, return_exceptions=True)
            assert recorder.cancelled
            assert (await post(client, "/v1/release", released(raw))).status_code == 409
        else:
            original_time = time.time
            recorder.before_return = lambda: monkeypatch.setattr(
                companion_lab.time, "time", lambda: original_time() + 31
            )
            assert (await post(client, "/v1/release", released(raw))).status_code == 202
            assert console.voice_task is not None
            await console.voice_task
        assert not stt
        assert not fake.requests
        assert not console.session.run_ids
