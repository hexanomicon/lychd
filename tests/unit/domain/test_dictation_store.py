"""Synthetic private custody tests; no model, network or PostgreSQL is exercised."""

import asyncio
import struct
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from lychd.domain.dictation import (
    DictationAttemptIdentity,
    DictationCorrectionRequest,
    DictationError,
    DictationProfile,
    DictationResult,
)
from lychd.domain.dictation_store import MemoryDictationStore
from lychd.domain.speech_probe import LocalSpeechBinding, WhisperModel, content_digest

NOW = datetime(2026, 11, 3, 12, tzinfo=UTC)


def profile(**changes: object) -> DictationProfile:
    original = DictationProfile(
        transcriber_binding=LocalSpeechBinding(
            runtime="whisper.cpp",
            dialect="whisper.cpp-batch-v1",
            endpoint="http://127.0.0.1:8081",
            runtime_revision="a" * 40,
            backend="cpu",
            device="host",
            model=WhisperModel(
                model="small-test",
                family="whisper-small",
                digest="sha256:" + "b" * 64,
                languages=("en", "sk"),
                license="synthetic-test-only",
            ),
        )
    )
    return DictationProfile.model_validate({**original.model_dump(), **changes})


def wav(sample: bytes = b"\x00\x00") -> bytes:
    return (
        struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            38,
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
            2,
        )
        + sample
    )


def identity(
    p: DictationProfile, owner: str = "alice", nonce: int = 1, now: datetime = NOW
) -> DictationAttemptIdentity:
    uid = UUID(int=(int(now.timestamp() * 1000) << 80) | (7 << 76) | (2 << 62) | nonce)
    return DictationAttemptIdentity(
        owner=owner,
        attempt_id=uid,
        source_digest=content_digest(wav()),
        profile_digest=p.digest,
        language="en",
    )


def result(i: DictationAttemptIdentity, text: str = "original") -> DictationResult:
    return DictationResult(
        attempt_id=i.attempt_id,
        status="transcribed",
        source_digest=i.source_digest,
        profile_digest=i.profile_digest,
        language=i.language,
        original_text=text,
    )


@pytest.mark.asyncio
async def test_concurrent_exact_claims_mint_one_dispatch_and_replay_unknown() -> None:
    store, p = MemoryDictationStore(), profile()
    i = identity(p)
    claims = await asyncio.gather(*(store.claim(i, wav(), NOW, p) for _ in range(10)))
    assert sum(c.dispatch for c in claims) == 1
    assert all(c.record.result is not None and c.record.result.status == "unknown" for c in claims)
    assert "raw_audio" not in repr(claims)
    assert store._entries["alice"][i.attempt_id].raw_audio == wav()  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
    await store.settle(i, result(i), NOW)
    assert (await store.claim(i, wav(), NOW, p)).record.result == result(i)


@pytest.mark.asyncio
async def test_settlement_is_once_and_original_cannot_be_rewritten_by_correction() -> None:
    store, p = MemoryDictationStore(), profile()
    i = identity(p)
    await store.claim(i, wav(), NOW, p)
    await store.settle(i, result(i), NOW)
    assert await store.settle(i, result(i, "late replacement"), NOW) == result(i)
    first = await store.correct("alice", DictationCorrectionRequest(attempt_id=i.attempt_id, final_text="edit"), NOW)
    latest = await store.correct(
        "alice",
        DictationCorrectionRequest(attempt_id=i.attempt_id, final_text="new edit"),
        NOW + timedelta(seconds=1),
    )
    assert latest.created_at == first.created_at
    assert latest.expires_at == first.expires_at
    assert latest.original_text == "original"
    assert await store.get_result("alice", i.attempt_id, NOW) == result(i)
    assert await store.list_corrections("alice", NOW) == (latest,)
    assert await store.list_corrections("bob", NOW) == ()
    assert await store.get_result("bob", i.attempt_id, NOW) is None
    assert not await store.delete("bob", i.attempt_id, NOW)
    with pytest.raises(DictationError, match="expired"):
        await store.correct("bob", DictationCorrectionRequest(attempt_id=i.attempt_id, final_text="steal"), NOW)


@pytest.mark.asyncio
async def test_raw_expiry_is_independent_and_does_not_remove_digest_or_transcript() -> None:
    store, p = MemoryDictationStore(), profile(raw_audio_retention_seconds=1)
    i = identity(p)
    await store.claim(i, wav(), NOW, p)
    await store.settle(i, result(i), NOW)
    later = NOW + timedelta(seconds=1)
    assert await store.get_result("alice", i.attempt_id, later) == result(i)
    entry = store._entries["alice"][i.attempt_id]  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
    assert entry.raw_audio is None
    assert not entry.raw_present
    replay = await store.claim(i, wav(), later, p)
    assert not replay.dispatch
    assert not replay.record.audio_available
    assert replay.record.result is not None
    assert replay.record.result.source_digest == i.source_digest


@pytest.mark.asyncio
@pytest.mark.parametrize("deletion", [True, False])
async def test_deleted_or_expired_content_cannot_be_resurrected_and_old_ids_never_dispatch(*, deletion: bool) -> None:
    store, p = MemoryDictationStore(), profile(retention_seconds=2)
    i = identity(p)
    await store.claim(i, wav(), NOW, p)
    await store.settle(i, result(i), NOW)
    await store.correct("alice", DictationCorrectionRequest(attempt_id=i.attempt_id, final_text="secret"), NOW)
    later = NOW + timedelta(seconds=2)
    if deletion:
        assert await store.delete("alice", i.attempt_id, NOW)
    assert await store.get_result("alice", i.attempt_id, later) is None
    assert await store.list_corrections("alice", later) == ()
    assert await store.settle(i, result(i, "late"), later) is None
    entry = store._entries["alice"][i.attempt_id]  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
    assert entry.content is None
    assert entry.raw_audio is None
    with pytest.raises(DictationError, match="expired"):
        await store.claim(i, wav(), later, p)
    await store.purge(NOW + timedelta(seconds=300))
    assert i.attempt_id in store._entries["alice"]  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
    await store.purge(NOW + timedelta(seconds=300, milliseconds=1))
    assert not store._entries  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
    with pytest.raises(DictationError, match="expired"):
        await store.claim(i, wav(), NOW + timedelta(seconds=301), p)


@pytest.mark.asyncio
async def test_quota_counts_tombstones_exact_replay_works_and_owner_isolation_holds() -> None:
    store, p = MemoryDictationStore(), profile(max_records_per_owner=1)
    i = identity(p)
    await store.claim(i, wav(), NOW, p)
    assert not (await store.claim(i, wav(), NOW, p)).dispatch
    await store.delete("alice", i.attempt_id, NOW)
    with pytest.raises(DictationError, match="capacity"):
        await store.claim(identity(p, nonce=2), wav(), NOW, p)
    assert (await store.claim(identity(p, owner="bob"), wav(), NOW, p)).dispatch


@pytest.mark.asyncio
async def test_unknown_settlement_stays_unknown_and_refuses_correction() -> None:
    store, p = MemoryDictationStore(), profile()
    i = identity(p)
    c = await store.claim(i, wav(), NOW, p)
    assert c.record.result is not None
    await store.settle(i, c.record.result, NOW)
    settled = await store.settle(i, result(i), NOW)
    assert settled is not None
    assert settled.status == "unknown"
    with pytest.raises(DictationError, match="expired"):
        await store.correct("alice", DictationCorrectionRequest(attempt_id=i.attempt_id, final_text="invented"), NOW)


@pytest.mark.asyncio
async def test_invalid_audio_provenance_identity_and_clock_are_refused() -> None:
    store, p = MemoryDictationStore(), profile()
    i = identity(p)
    with pytest.raises(DictationError, match="invalid_audio"):
        await store.claim(i, b"garbage", NOW, p)
    with pytest.raises(DictationError, match="replay_conflict"):
        await store.claim(i, wav(b"\x01\x00"), NOW, p)
    with pytest.raises(DictationError, match="expired"):
        await store.claim(i.model_copy(update={"attempt_id": uuid4()}), wav(), NOW, p)
    with pytest.raises(ValueError, match="aware"):
        await store.claim(i, wav(), NOW.replace(tzinfo=None), p)
    await store.claim(i, wav(), NOW, p)
    for changes in ({"language": "sk"}, {"source_digest": content_digest(wav(b"\x01\x00"))}):
        changed = i.model_copy(update=changes)
        audio = wav() if "language" in changes else wav(b"\x01\x00")
        with pytest.raises(DictationError, match="replay_conflict"):
            await store.claim(changed, audio, NOW, p)
    with pytest.raises(DictationError, match="replay_conflict"):
        await store.settle(i, result(i).model_copy(update={"source_digest": "sha256:" + "f" * 64}), NOW)


@pytest.mark.asyncio
async def test_zero_raw_retention_never_enters_quarantine_storage() -> None:
    store, p = MemoryDictationStore(), profile(raw_audio_retention_seconds=0)
    i = identity(p)
    c = await store.claim(i, wav(), NOW, p)
    assert not c.record.audio_available
    assert store._entries["alice"][i.attempt_id].raw_audio is None  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
    await store.purge(NOW)
    assert store._entries["alice"][i.attempt_id].raw_audio is None  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
