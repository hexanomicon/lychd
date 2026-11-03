"""Durable private dictation claims; no connection construction or automatic retries.

Every owner operation holds a domain-separated PostgreSQL advisory transaction
lock, including reads that purge expired content. Only acknowledged commit plus
session cleanup can return a fresh dispatch claim. Driver diagnostics are private.
"""

from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import and_, or_, select, text

from lychd.db.models.dictation import BridgeDictationAttempt
from lychd.domain.dictation import MAX_AUDIO_BYTES, DictationError
from lychd.domain.dictation_store import (
    DictationEntry,
    DictationStoreOperations,
    StoredDictationContent,
    validate_store_time,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_MAX_ROWS = 1000
_UUID_VERSION = 7
_MIN_AUDIO_BYTES = 46
_MAX_CONTENT_BYTES = 131_072


def _utc_now() -> datetime:
    return datetime.now(UTC)


class DictationStoreError(RuntimeError):
    """Content-free storage error. Unknown commit requires lookup, never retry dispatch."""


def _lock_id(owner: str) -> int:
    digest = hashlib.sha256(b"lychd:bridge-dictation:v1\0" + owner.encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def _decode(row: BridgeDictationAttempt, owner: str) -> DictationEntry:
    """Revalidate retained metadata without hydrating deferred raw bytes."""
    content = None if row.content_json is None else StoredDictationContent.model_validate_json(row.content_json)
    for moment in (row.created_at, row.expires_at, row.audio_expires_at, row.tombstone_until):
        validate_store_time(moment)
    if (
        row.attempt_id.version != _UUID_VERSION
        or row.tombstone_until
        != datetime.fromtimestamp((row.attempt_id.int >> 80) / 1000, UTC) + timedelta(seconds=300)
        or row.owner != owner
        or not timedelta(0) < row.expires_at - row.created_at <= timedelta(days=30)
        or not timedelta(0) <= row.audio_expires_at - row.created_at <= timedelta(hours=1)
        or not (row.raw_size == 0 or _MIN_AUDIO_BYTES <= row.raw_size <= MAX_AUDIO_BYTES)
        or (content is None and row.raw_size != 0)
    ):
        msg = "dictation_integrity"
        raise DictationStoreError(msg)
    if content is not None:
        identity, result = content.identity, content.result
        if (
            (not content.settled and (result.status != "unknown" or content.correction is not None))
            or identity.owner != owner
            or identity.attempt_id != row.attempt_id
            or result.attempt_id != row.attempt_id
            or result.language != identity.language
            or result.source_digest != identity.source_digest
            or result.profile_digest != identity.profile_digest
        ):
            msg = "dictation_integrity"
            raise DictationStoreError(msg)
        correction = content.correction
        if correction is not None and (
            correction.attempt_id != row.attempt_id
            or correction.original_text != result.original_text
            or correction.source_digest != identity.source_digest
            or correction.profile_digest != identity.profile_digest
            or correction.language != identity.language
            or correction.expires_at != row.expires_at
        ):
            msg = "dictation_integrity"
            raise DictationStoreError(msg)
    return DictationEntry(
        attempt_id=row.attempt_id,
        created_at=row.created_at,
        expires_at=row.expires_at,
        audio_expires_at=row.audio_expires_at,
        tombstone_until=row.tombstone_until,
        content=content,
        raw_present=row.raw_size > 0,
    )


class DbDictationStore(DictationStoreOperations):
    """Fresh-session PostgreSQL adapter; runtime never applies its own migration."""

    def __init__(self, factory: async_sessionmaker[AsyncSession], *, now: Callable[[], datetime] = _utc_now) -> None:
        """Initialize the explicit private-custody dependencies and bounds."""
        self._factory = factory
        self._now = now

    def _current_time(self, supplied: datetime) -> datetime:
        """Sample after pool/owner-lock waits; a caller timestamp is not admission."""
        validate_store_time(supplied)
        return self._now()

    @asynccontextmanager
    async def _transaction(self, owner: str | None) -> AsyncGenerator[AsyncSession]:
        commit_started = False
        try:
            async with self._factory() as session:
                if session.get_bind().dialect.name != "postgresql":
                    msg = "dictation_postgresql_required"
                    raise DictationStoreError(msg)  # noqa: TRY301
                if getattr(session.get_bind(), "hide_parameters", None) is not True:
                    msg = "dictation_private_parameters_required"
                    raise DictationStoreError(msg)  # noqa: TRY301
                async with session.begin():
                    await session.execute(text("SET LOCAL statement_timeout = '5s'"))
                    await session.execute(text("SET LOCAL lock_timeout = '2s'"))
                    await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                    if owner is not None:
                        await session.execute(
                            text("SELECT pg_advisory_xact_lock(CAST(:lock_id AS BIGINT))"),
                            {"lock_id": _lock_id(owner)},
                        )
                    yield session
                    commit_started = owner is not None
        except (DictationError, DictationStoreError):
            raise
        except Exception:  # noqa: BLE001 - never disclose private SQL parameters or driver messages
            msg = "dictation_commit_unknown" if commit_started else "dictation_storage_failure"
            raise DictationStoreError(msg) from None

    @asynccontextmanager
    async def _records(self, owner: str) -> AsyncGenerator[dict[UUID, DictationEntry]]:
        async with self._transaction(owner) as session:
            rows = (
                await session.scalars(
                    select(BridgeDictationAttempt).where(BridgeDictationAttempt.owner == owner).limit(_MAX_ROWS + 1),
                )
            ).all()
            if len(rows) > _MAX_ROWS:
                msg = "dictation_integrity"
                raise DictationStoreError(msg)
            mapped = {row.attempt_id: row for row in rows}
            entries = {row.attempt_id: _decode(row, owner) for row in rows}
            before = entries.copy()
            yield entries
            for attempt_id, row in mapped.items():
                if attempt_id not in entries:
                    await session.delete(row)
            for attempt_id, entry in entries.items():
                if before.get(attempt_id) == entry:
                    continue
                payload = None if entry.content is None else entry.content.model_dump_json()
                if payload is not None and len(payload.encode()) > _MAX_CONTENT_BYTES:
                    msg = "dictation_integrity"
                    raise DictationStoreError(msg)
                row = mapped.get(attempt_id)
                if row is None:
                    session.add(
                        BridgeDictationAttempt(
                            owner=owner,
                            attempt_id=attempt_id,
                            created_at=entry.created_at,
                            expires_at=entry.expires_at,
                            audio_expires_at=entry.audio_expires_at,
                            tombstone_until=entry.tombstone_until,
                            content_json=payload,
                            raw_audio=entry.raw_audio,
                            raw_size=len(entry.raw_audio or b""),
                        )
                    )
                else:
                    row.content_json = payload
                    if not entry.raw_present:
                        row.raw_audio = None
                        row.raw_size = 0
            await session.flush()

    async def purge(self, now: datetime) -> None:
        """Clear due owners in finite batches, acquiring the ordinary owner locks."""
        validate_store_time(now)
        while True:
            async with self._transaction(None) as session:
                owners = (
                    await session.scalars(
                        select(BridgeDictationAttempt.owner)
                        .where(
                            or_(
                                and_(
                                    BridgeDictationAttempt.content_json.is_not(None),
                                    BridgeDictationAttempt.expires_at <= now,
                                ),
                                and_(
                                    BridgeDictationAttempt.raw_size > 0, BridgeDictationAttempt.audio_expires_at <= now
                                ),
                                and_(
                                    BridgeDictationAttempt.content_json.is_(None),
                                    BridgeDictationAttempt.tombstone_until < now,
                                ),
                            )
                        )
                        .distinct()
                        .limit(100),
                    )
                ).all()
            if not owners:
                return
            for owner in owners:
                async with self._working(owner, now):
                    pass
