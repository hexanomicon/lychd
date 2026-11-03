"""Private dictation retention port and effect-free, process-local test fixture.

Only the PostgreSQL implementation supplies durable custody. Audio is never part
of a returned record. Deletion clears content, keeping an owner/id fence only
until UUIDv7 admission closes. Neither a retained claim nor a read grants dispatch.
"""

from __future__ import annotations

import asyncio
import base64
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from lychd.domain.dictation import (
    MAX_AUDIO_BYTES,
    DictationAttemptIdentity,
    DictationAttemptSummary,
    DictationCorrection,
    DictationCorrectionRequest,
    DictationError,
    DictationModel,
    DictationProfile,
    DictationRequest,
    DictationResult,
    decode_audio,
    validate_new_attempt_time,
)
from lychd.domain.speech_probe import content_digest

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@dataclass(frozen=True)
class DictationRecord:
    """Internal metadata projection: digest survival is not audio availability."""

    identity: DictationAttemptIdentity | None
    result: DictationResult | None
    created_at: datetime
    expires_at: datetime
    audio_expires_at: datetime
    deleted: bool
    audio_available: bool


@dataclass(frozen=True)
class DictationClaim:
    """Dispatch is true only on an acknowledged fresh claim, never on replay."""

    dispatch: bool
    record: DictationRecord


_MAX_OWNER_CHARS = 256
_MAX_ATTEMPTS = 1000


def _valid_owner(owner: object) -> bool:
    return isinstance(owner, str) and 1 <= len(owner) <= _MAX_OWNER_CHARS


class DictationStore(Protocol):
    async def claim(
        self,
        identity: DictationAttemptIdentity,
        audio: bytes,
        now: datetime,
        profile: DictationProfile,
    ) -> DictationClaim: ...

    async def settle(
        self,
        identity: DictationAttemptIdentity,
        result: DictationResult,
        now: datetime,
    ) -> DictationResult | None: ...

    async def get_result(self, owner: str, attempt_id: UUID, now: datetime) -> DictationResult | None: ...

    async def correct(
        self,
        owner: str,
        request: DictationCorrectionRequest,
        now: datetime,
    ) -> DictationCorrection: ...

    async def list_corrections(self, owner: str, now: datetime) -> tuple[DictationCorrection, ...]: ...

    async def list_attempts(self, owner: str, now: datetime) -> tuple[DictationAttemptSummary, ...]: ...

    async def delete(self, owner: str, attempt_id: UUID, now: datetime) -> bool: ...

    async def purge(self, now: datetime) -> None: ...


class StoredDictationContent(DictationModel):
    """Closed private storage encoding; erased entirely for a tombstone."""

    identity: DictationAttemptIdentity
    result: DictationResult
    correction: DictationCorrection | None = None
    settled: bool = False


@dataclass(frozen=True)
class DictationEntry:
    """Adapter state; raw bytes are write-only for durable adapter reads."""

    attempt_id: UUID
    created_at: datetime
    expires_at: datetime
    audio_expires_at: datetime
    tombstone_until: datetime
    content: StoredDictationContent | None
    raw_present: bool = False
    raw_audio: bytes | None = field(default=None, repr=False, compare=False)

    def project(self, now: datetime) -> DictationRecord:
        return DictationRecord(
            identity=None if self.content is None else self.content.identity,
            result=None if self.content is None else self.content.result,
            created_at=self.created_at,
            expires_at=self.expires_at,
            audio_expires_at=self.audio_expires_at,
            deleted=self.content is None,
            audio_available=self.raw_present and now < self.audio_expires_at,
        )


def validate_store_time(now: datetime) -> None:
    if now.tzinfo is None or now.utcoffset() is None:
        msg = "Dictation custody requires aware server time."
        raise ValueError(msg)


def purge_entries(entries: dict[UUID, DictationEntry], now: datetime) -> None:
    """Pure bounded lifecycle transition shared by both store implementations."""
    validate_store_time(now)
    for attempt_id, retained in tuple(entries.items()):
        entry = retained
        if entry.content is not None and now >= entry.expires_at:
            entry = replace(entry, content=None, raw_present=False, raw_audio=None)
        if entry.raw_present and now >= entry.audio_expires_at:
            entry = replace(entry, raw_present=False, raw_audio=None)
        # UUID admission includes the exact upper bound, so keep its fence then.
        if entry.content is None and now > entry.tombstone_until:
            del entries[attempt_id]
        else:
            entries[attempt_id] = entry


class DictationStoreOperations:
    """Common lifecycle algebra; adapters supply one atomic owner transaction."""

    @asynccontextmanager
    async def _records(self, _owner: str) -> AsyncGenerator[dict[UUID, DictationEntry]]:
        raise NotImplementedError
        yield {}  # pragma: no cover - async contextmanager protocol

    def _current_time(self, supplied: datetime) -> datetime:
        """Memory fixtures use supplied time; durable adapters own a fresh clock."""
        return supplied

    @asynccontextmanager
    async def _working(self, owner: str, now: datetime) -> AsyncGenerator[tuple[dict[UUID, DictationEntry], datetime]]:
        validate_store_time(now)
        if not _valid_owner(owner):
            msg = "Invalid dictation owner."
            raise ValueError(msg)
        async with self._records(owner) as entries:
            now = self._current_time(now)
            validate_store_time(now)
            purge_entries(entries, now)
            yield entries, now

    async def claim(
        self,
        identity: DictationAttemptIdentity,
        audio: bytes,
        now: datetime,
        profile: DictationProfile,
    ) -> DictationClaim:
        identity = DictationAttemptIdentity.model_validate(identity.model_dump())
        profile = DictationProfile.model_validate(profile.model_dump())
        if identity.language not in profile.transcriber_binding.model.languages:
            msg = "language_unavailable"
            raise DictationError(msg)
        if type(audio) is not bytes or len(audio) > MAX_AUDIO_BYTES:
            msg = "invalid_audio"
            raise DictationError(msg)
        decode_audio(
            DictationRequest(
                attempt_id=identity.attempt_id,
                audio_base64=base64.b64encode(audio).decode("ascii"),
                language=identity.language,
            )
        )
        if content_digest(audio) != identity.source_digest or profile.digest != identity.profile_digest:
            msg = "replay_conflict"
            raise DictationError(msg)
        async with self._working(identity.owner, now) as (entries, current_time):
            previous = entries.get(identity.attempt_id)
            if previous is not None:
                if previous.content is None:
                    msg = "expired"
                    raise DictationError(msg)
                if previous.content.identity != identity:
                    msg = "replay_conflict"
                    raise DictationError(msg)
                claim = DictationClaim(dispatch=False, record=previous.project(current_time))
            else:
                validate_new_attempt_time(identity.attempt_id, current_time)
                if len(entries) >= profile.max_records_per_owner:
                    msg = "capacity"
                    raise DictationError(msg)
                result = DictationResult(
                    attempt_id=identity.attempt_id,
                    status="unknown",
                    source_digest=identity.source_digest,
                    profile_digest=identity.profile_digest,
                    language=identity.language,
                    reason="outcome_unknown",
                )
                entry = DictationEntry(
                    attempt_id=identity.attempt_id,
                    created_at=current_time,
                    expires_at=current_time + timedelta(seconds=profile.retention_seconds),
                    audio_expires_at=current_time + timedelta(seconds=profile.raw_audio_retention_seconds),
                    tombstone_until=datetime.fromtimestamp((identity.attempt_id.int >> 80) / 1000, UTC)
                    + timedelta(seconds=300),
                    content=StoredDictationContent(identity=identity, result=result),
                    raw_present=profile.raw_audio_retention_seconds > 0,
                    raw_audio=audio if profile.raw_audio_retention_seconds > 0 else None,
                )
                entries[identity.attempt_id] = entry
                claim = DictationClaim(dispatch=True, record=entry.project(current_time))
        if self._current_time(current_time) >= claim.record.expires_at:
            msg = "expired"
            raise DictationError(msg)
        return claim

    async def settle(
        self,
        identity: DictationAttemptIdentity,
        result: DictationResult,
        now: datetime,
    ) -> DictationResult | None:
        identity = DictationAttemptIdentity.model_validate(identity.model_dump())
        result = DictationResult.model_validate(result.model_dump())
        if (
            result.attempt_id != identity.attempt_id
            or result.source_digest != identity.source_digest
            or result.profile_digest != identity.profile_digest
            or result.language != identity.language
        ):
            msg = "replay_conflict"
            raise DictationError(msg)
        async with self._working(identity.owner, now) as (entries, current_time):
            entry = entries.get(identity.attempt_id)
            if entry is None or entry.content is None:
                settled = None
            elif entry.content.identity != identity:
                msg = "replay_conflict"
                raise DictationError(msg)
            elif entry.content.settled:
                settled = entry.content.result
            else:
                entries[identity.attempt_id] = replace(
                    entry,
                    content=StoredDictationContent(identity=identity, result=result, settled=True),
                )
                settled = result
        if entry is not None and self._current_time(current_time) >= entry.expires_at:
            return None
        return settled

    async def get_result(self, owner: str, attempt_id: UUID, now: datetime) -> DictationResult | None:
        async with self._working(owner, now) as (entries, current_time):
            entry = entries.get(attempt_id)
            result = None if entry is None or entry.content is None else entry.content.result
        if entry is not None and self._current_time(current_time) >= entry.expires_at:
            return None
        return result

    async def correct(
        self,
        owner: str,
        request: DictationCorrectionRequest,
        now: datetime,
    ) -> DictationCorrection:
        request = DictationCorrectionRequest.model_validate(request.model_dump())
        async with self._working(owner, now) as (entries, current_time):
            entry = entries.get(request.attempt_id)
            if entry is None or entry.content is None or entry.content.result.status != "transcribed":
                msg = "expired"
                raise DictationError(msg)
            content = entry.content
            original = content.result.original_text
            if original is None:
                msg = "expired"
                raise DictationError(msg)
            correction = DictationCorrection(
                attempt_id=request.attempt_id,
                source_digest=content.identity.source_digest,
                profile_digest=content.identity.profile_digest,
                language=content.identity.language,
                original_text=original,
                final_text=request.final_text,
                created_at=current_time if content.correction is None else content.correction.created_at,
                expires_at=entry.expires_at,
            )
            entries[request.attempt_id] = replace(entry, content=content.model_copy(update={"correction": correction}))
        if self._current_time(current_time) >= correction.expires_at:
            msg = "expired"
            raise DictationError(msg)
        return correction

    async def list_corrections(self, owner: str, now: datetime) -> tuple[DictationCorrection, ...]:
        async with self._working(owner, now) as (entries, current_time):
            corrections = tuple(
                entry.content.correction
                for entry in sorted(entries.values(), key=lambda item: item.created_at)
                if entry.content is not None and entry.content.correction is not None
            )
        current = self._current_time(current_time)
        return tuple(correction for correction in corrections if current < correction.expires_at)

    async def list_attempts(self, owner: str, now: datetime) -> tuple[DictationAttemptSummary, ...]:
        """Expose bounded owned metadata, refreshing expiry after transaction cleanup."""
        async with self._working(owner, now) as (entries, current_time):
            if len(entries) > _MAX_ATTEMPTS:
                msg = "capacity"
                raise DictationError(msg)
            attempts = tuple(
                DictationAttemptSummary(
                    attempt_id=entry.attempt_id,
                    status=entry.content.result.status,
                    language=entry.content.identity.language,
                    created_at=entry.created_at,
                    expires_at=entry.expires_at,
                    audio_expires_at=entry.audio_expires_at,
                    audio_available=entry.raw_present and current_time < entry.audio_expires_at,
                    has_correction=entry.content.correction is not None,
                )
                for entry in sorted(entries.values(), key=lambda item: (item.created_at, item.attempt_id))
                if entry.content is not None
            )
        current = self._current_time(current_time)
        validate_store_time(current)
        return tuple(
            attempt.model_copy(
                update={"audio_available": attempt.audio_available and current < attempt.audio_expires_at}
            )
            for attempt in attempts
            if current < attempt.expires_at
        )

    async def delete(self, owner: str, attempt_id: UUID, now: datetime) -> bool:
        async with self._working(owner, now) as (entries, current_time):
            entry = entries.get(attempt_id)
            deleted = entry is not None and entry.content is not None
            if entry is not None and deleted:
                entries[attempt_id] = replace(entry, content=None, raw_present=False, raw_audio=None)
                purge_entries(entries, current_time)
        return deleted


class MemoryDictationStore(DictationStoreOperations):
    """Test-only memory equivalent; no restart or physical erasure claims."""

    def __init__(self) -> None:
        """Initialize the explicit private-custody dependencies and bounds."""
        self._entries: dict[str, dict[UUID, DictationEntry]] = {}
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def _records(self, owner: str) -> AsyncGenerator[dict[UUID, DictationEntry]]:
        async with self._lock:
            working = self._entries.get(owner, {}).copy()
            yield working
            if working:
                self._entries[owner] = working
            else:
                self._entries.pop(owner, None)

    async def purge(self, now: datetime) -> None:
        validate_store_time(now)
        async with self._lock:
            for owner, entries in tuple(self._entries.items()):
                purge_entries(entries, now)
                if not entries:
                    del self._entries[owner]
