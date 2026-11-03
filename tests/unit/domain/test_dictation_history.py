"""Owned recovery metadata includes uncorrected and uncertain attempts, never content."""

from datetime import datetime, timedelta

import pytest

from lychd.domain.dictation import DictationCorrectionRequest, DictationError
from lychd.domain.dictation_store import MemoryDictationStore
from tests.unit.domain.test_dictation_service import setup
from tests.unit.domain.test_dictation_store import NOW, identity, profile, result, wav

SUMMARY_FIELDS = {
    "attempt_id",
    "status",
    "language",
    "created_at",
    "expires_at",
    "audio_expires_at",
    "audio_available",
    "has_correction",
}


@pytest.mark.asyncio
async def test_history_includes_unknown_success_and_correction_without_private_payload() -> None:
    store, pinned = MemoryDictationStore(), profile(raw_audio_retention_seconds=2)
    identities = [identity(pinned, nonce=number) for number in (1, 2, 3)]
    for attempt in identities:
        await store.claim(attempt, wav(), NOW, pinned)
    for attempt in identities[1:]:
        await store.settle(attempt, result(attempt, "Private original"), NOW)
    await store.correct(
        "alice", DictationCorrectionRequest(attempt_id=identities[2].attempt_id, final_text="Private edit"), NOW
    )
    history = await store.list_attempts("alice", NOW)
    assert [item.status for item in history] == ["unknown", "transcribed", "transcribed"]
    assert [item.has_correction for item in history] == [False, False, True]
    assert all(item.audio_available for item in history)
    assert all(set(item.model_dump()) == SUMMARY_FIELDS for item in history)
    assert all("Private" not in item.model_dump_json() for item in history)
    assert all(
        item.created_at == NOW and item.expires_at == NOW + timedelta(seconds=pinned.retention_seconds)
        for item in history
    )
    assert await store.list_attempts("foreign", NOW) == ()
    await store.delete("alice", identities[0].attempt_id, NOW)
    assert [item.attempt_id for item in await store.list_attempts("alice", NOW)] == [
        i.attempt_id for i in identities[1:]
    ]
    after_raw_expiry = await store.list_attempts("alice", NOW + timedelta(seconds=2))
    assert len(after_raw_expiry) == 2
    assert not any(item.audio_available for item in after_raw_expiry)
    assert await store.list_attempts("alice", NOW + timedelta(seconds=pinned.retention_seconds)) == ()


@pytest.mark.asyncio
@pytest.mark.parametrize(("elapsed", "expected_count"), [(1, 1), (2, 0)])
async def test_history_rechecks_record_and_audio_deadlines_after_commit(
    monkeypatch: pytest.MonkeyPatch,
    elapsed: int,
    expected_count: int,
) -> None:
    store, pinned = MemoryDictationStore(), profile(retention_seconds=2, raw_audio_retention_seconds=1)
    await store.claim(identity(pinned), wav(), NOW, pinned)
    clock = iter((NOW, NOW + timedelta(seconds=elapsed)))

    def current_time(_supplied: datetime) -> datetime:
        return next(clock)

    monkeypatch.setattr(store, "_current_time", current_time)
    history = await store.list_attempts("alice", NOW)
    assert len(history) == expected_count
    assert not any(item.audio_available for item in history)


@pytest.mark.asyncio
async def test_history_never_silently_truncates_an_impossible_over_capacity_owner() -> None:
    store, pinned = MemoryDictationStore(), profile()
    attempt = identity(pinned)
    await store.claim(attempt, wav(), NOW, pinned)
    entry = store._entries["alice"][attempt.attempt_id]  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
    # Corrupt fixture only: normal claim admission cannot exceed the profile bound.
    store._entries["alice"] = {identity(pinned, nonce=number).attempt_id: entry for number in range(1, 1002)}  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
    with pytest.raises(DictationError, match="capacity"):
        await store.list_attempts("alice", NOW)


def test_discovery_reports_exact_active_profile_retention_and_capacity() -> None:
    service, adapter = setup(retention_seconds=1234, max_records_per_owner=17, raw_audio_retention_seconds=2)
    discovery = service.discovery()
    assert discovery.retention_seconds == 1234
    assert discovery.max_records_per_owner == 17
    assert discovery.raw_audio_retention_seconds == 2
    assert adapter.calls == 0
    service.profile = None
    unavailable = service.discovery()
    assert unavailable.retention_seconds is None
    assert unavailable.max_records_per_owner is None


@pytest.mark.asyncio
async def test_service_history_remains_available_without_transcription_profile() -> None:
    service, adapter = setup()
    pinned = service.profile
    assert pinned is not None
    attempt = identity(pinned)
    await service.store.claim(attempt, wav(), NOW, pinned)
    service.profile = None
    # Service fixture uses its own fixed midnight clock; set this fixture's clock explicitly.
    service._now = lambda: NOW  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
    history = await service.list_attempts("alice")
    assert len(history) == 1
    assert history[0].status == "unknown"
    assert adapter.calls == 0
