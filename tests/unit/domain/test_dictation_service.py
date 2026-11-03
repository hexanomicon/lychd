"""Synthetic private-custody lifecycle; no actual speech or network qualification."""

from __future__ import annotations

import asyncio
import base64
import json
import struct
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest

from lychd.domain.artifacts import ArtifactRef
from lychd.domain.dictation import (
    DictationCorrectionRequest,
    DictationProfile,
    DictationRequest,
    DictationTranscriberError,
)
from lychd.domain.dictation_service import DictationService
from lychd.domain.dictation_store import MemoryDictationStore

NOW = datetime(2026, 11, 3, tzinfo=UTC)


def profile(**updates: Any) -> DictationProfile:
    return DictationProfile.model_validate_json(
        json.dumps(
            {
                "transcriber_binding": {
                    "runtime": "whisper.cpp",
                    "dialect": "whisper.cpp-batch-v1",
                    "endpoint": "http://127.0.0.1:8080",
                    "runtime_revision": "a" * 40,
                    "backend": "cpu",
                    "device": "host",
                    "model": {
                        "model": "synthetic",
                        "family": "whisper-small",
                        "digest": "sha256:" + "b" * 64,
                        "languages": ["en"],
                        "license": "MIT",
                    },
                },
                **updates,
            }
        )
    )


def request(*, number: int = 1) -> DictationRequest:
    pcm = b"\x00\x00" * 8
    content = (
        struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + len(pcm),
            b"WAVE",
            b"fmt ",
            16,
            1,
            1,
            16000,
            32000,
            2,
            16,
            b"data",
            len(pcm),
        )
        + pcm
    )
    identifier = UUID(int=(int(NOW.timestamp() * 1000) << 80) | (7 << 76) | (2 << 62) | number)
    return DictationRequest(attempt_id=identifier, audio_base64=base64.b64encode(content).decode(), language="en")


def authorize() -> None:
    pass


class Transcriber:
    def __init__(self, pinned: DictationProfile) -> None:
        self.profile = pinned
        self.calls = 0
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.block = False
        self.error: Exception | None = None

    async def transcribe(self, source: ArtifactRef, content: bytes, language: str) -> str:
        assert source.classification == "private"
        assert source.size == len(content)
        assert language == "en"
        self.calls += 1
        self.entered.set()
        if self.block:
            await self.release.wait()
        if self.error:
            raise self.error
        return "Original words"


def setup(**updates: Any) -> tuple[DictationService, Transcriber]:
    pinned = profile(**updates)
    adapter = Transcriber(pinned)
    service = DictationService(store=MemoryDictationStore(), profile=pinned, transcriber=adapter, now=lambda: NOW)
    return service, adapter


@pytest.mark.asyncio
async def test_replay_correction_owner_delete() -> None:
    service, adapter = setup()
    incoming = request()
    first = await service.transcribe("owner", incoming, authorize=authorize)
    assert first.status == "transcribed"
    assert await service.transcribe("owner", incoming, authorize=authorize) == first
    assert adapter.calls == 1
    correction = await service.correct(
        "owner", DictationCorrectionRequest(attempt_id=incoming.attempt_id, final_text="Edited")
    )
    assert correction.original_text == "Original words"
    assert await service.list_corrections("other") == ()
    assert await service.get_result("other", incoming.attempt_id) is None
    await service.delete("owner", incoming.attempt_id)
    assert await service.get_result("owner", incoming.attempt_id) is None
    assert (await service.transcribe("owner", incoming, authorize=authorize)).reason == "expired"
    assert adapter.calls == 1


@pytest.mark.asyncio
async def test_concurrent_duplicate_observes_unknown_and_late_delete_wins() -> None:
    service, adapter = setup()
    adapter.block = True
    incoming = request()
    pending = asyncio.create_task(service.transcribe("owner", incoming, authorize=authorize))
    await adapter.entered.wait()
    replay = await service.transcribe("owner", incoming, authorize=authorize)
    assert replay.status == "unknown"
    await service.delete("owner", incoming.attempt_id)
    adapter.release.set()
    assert (await pending).reason == "expired"
    assert adapter.calls == 1
    assert await service.get_result("owner", incoming.attempt_id) is None


@pytest.mark.asyncio
async def test_distinct_attempts_do_not_queue_a_second_local_transcription() -> None:
    service, adapter = setup()
    adapter.block = True
    first = request()
    pending = asyncio.create_task(service.transcribe("owner", first, authorize=authorize))
    await adapter.entered.wait()
    second = request(number=2)
    refused = await service.transcribe("owner", second, authorize=authorize)
    assert refused.status == "refused"
    assert refused.reason == "capacity"
    assert adapter.calls == 1
    adapter.release.set()
    assert (await pending).status == "transcribed"
    assert await service.transcribe("owner", second, authorize=authorize) == refused
    assert adapter.calls == 1


@pytest.mark.asyncio
async def test_cancellation_leaves_recoverable_unknown_without_redispatch() -> None:
    service, adapter = setup()
    adapter.block = True
    incoming = request()
    pending = asyncio.create_task(service.transcribe("owner", incoming, authorize=authorize))
    await adapter.entered.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    recovered = await service.get_result("owner", incoming.attempt_id)
    assert recovered is not None
    assert recovered.status == "unknown"
    assert await service.transcribe("owner", incoming, authorize=authorize) == recovered
    assert adapter.calls == 1
    await service.aclose()


@pytest.mark.asyncio
async def test_timeout_and_typed_transport_error_remain_unknown() -> None:
    service, adapter = setup(transport_timeout_seconds=0.01, total_timeout_seconds=0.01)
    adapter.block = True
    assert (await service.transcribe("owner", request(), authorize=authorize)).status == "unknown"
    await service.aclose()
    service, adapter = setup()
    adapter.error = DictationTranscriberError("unknown", "outcome_unknown")
    assert (await service.transcribe("owner", request(), authorize=authorize)).status == "unknown"


@pytest.mark.asyncio
async def test_invalid_audio_never_claims_and_disabled_recovery_still_works() -> None:
    service, adapter = setup()
    incoming = request()
    invalid = incoming.model_copy(update={"audio_base64": "AA=="})
    assert (await service.transcribe("owner", invalid, authorize=authorize)).reason == "invalid_audio"
    assert await service.get_result("owner", incoming.attempt_id) is None
    first = await service.transcribe("owner", incoming, authorize=authorize)
    service.profile = None
    assert service.discovery().status == "unavailable"
    assert await service.get_result("owner", incoming.attempt_id) == first
    assert adapter.calls == 1


@pytest.mark.asyncio
async def test_authority_revoked_during_call_never_returns_or_settles_transcript() -> None:
    service, adapter = setup()
    adapter.block = True
    allowed = True

    def current() -> None:
        if not allowed:
            raise PermissionError

    incoming = request()
    pending = asyncio.create_task(service.transcribe("owner", incoming, authorize=current))
    await adapter.entered.wait()
    allowed = False
    adapter.release.set()
    with pytest.raises(PermissionError):
        await pending
    recovered = await service.get_result("owner", incoming.attempt_id)
    assert recovered is not None
    assert recovered.status == "unknown"


def test_profile_without_matching_adapter_fails_closed() -> None:
    service, adapter = setup()
    assert service.discovery().status == "available"
    adapter.profile = profile(raw_audio_retention_seconds=0)
    assert service.discovery().status == "unavailable"


@pytest.mark.asyncio
async def test_late_cancellation_suppressing_adapter_cannot_settle() -> None:
    service, adapter = setup(transport_timeout_seconds=0.01, total_timeout_seconds=0.01)
    release = asyncio.Event()

    class LateTranscriber(Transcriber):
        async def transcribe(self, source: ArtifactRef, content: bytes, language: str) -> str:
            assert source.classification == "private"
            assert source.size == len(content)
            assert language == "en"
            try:
                await release.wait()
            except asyncio.CancelledError:
                await release.wait()
            return "Late private words"

    late = LateTranscriber(adapter.profile)
    service.transcriber = late
    incoming = request()
    assert (await service.transcribe("owner", incoming, authorize=authorize)).status == "unknown"
    release.set()
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    recovered = await service.get_result("owner", incoming.attempt_id)
    assert recovered is not None
    assert recovered.status == "unknown"
    await service.aclose()
