"""PostgreSQL lexicon custody, with owner-serialized quota and protected parameters."""

from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select, text

from lychd.db.models.dictation_lexicon import BridgeDictationLexiconRule
from lychd.domain.dictation_lexicon import (
    DEFAULT_LEXICON_RETENTION_SECONDS,
    MAX_LEXICON_RULES,
    DictationLexiconError,
    DictationLexiconOperations,
    DictationLexiconRule,
    validate_lexicon_time,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _utc_now() -> datetime:
    return datetime.now(UTC)


class DictationLexiconStoreError(RuntimeError):
    """Fixed diagnostics only; no SQL or phrase content crosses this boundary."""


def _lock_id(owner: str) -> int:
    digest = hashlib.sha256(b"lychd:bridge-dictation-lexicon:v1\0" + owner.encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


class DbDictationLexiconStore(DictationLexiconOperations):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        *,
        retention_seconds: int = DEFAULT_LEXICON_RETENTION_SECONDS,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        """Initialize the explicit private-custody dependencies and bounds."""
        super().__init__(retention_seconds=retention_seconds)
        self._factory = factory
        self._now = now

    def _current_time(self, supplied: datetime) -> datetime:
        """Sample after pool and owner-lock acquisition; caller time cannot extend custody."""
        validate_lexicon_time(supplied)
        return self._now()

    @asynccontextmanager
    async def _transaction(self, owner: str | None) -> AsyncGenerator[AsyncSession]:
        commit_started = False
        try:
            async with self._factory() as session:
                if session.get_bind().dialect.name != "postgresql":
                    msg = "dictation_lexicon_postgresql_required"
                    raise DictationLexiconStoreError(msg)  # noqa: TRY301
                if getattr(session.get_bind(), "hide_parameters", None) is not True:
                    msg = "dictation_lexicon_private_parameters_required"
                    raise DictationLexiconStoreError(msg)  # noqa: TRY301
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
        except (DictationLexiconError, DictationLexiconStoreError):
            raise
        except Exception:  # noqa: BLE001 - private driver diagnostics are never public
            msg = "dictation_lexicon_commit_unknown" if commit_started else "dictation_lexicon_storage_failure"
            raise DictationLexiconStoreError(msg) from None

    @asynccontextmanager
    async def _records(self, owner: str) -> AsyncGenerator[dict[UUID, DictationLexiconRule]]:
        async with self._transaction(owner) as session:
            rows = (
                await session.scalars(
                    select(BridgeDictationLexiconRule)
                    .where(BridgeDictationLexiconRule.owner == owner)
                    .limit(MAX_LEXICON_RULES + 1),
                )
            ).all()
            if len(rows) > MAX_LEXICON_RULES:
                msg = "capacity"
                raise DictationLexiconError(msg)
            mapped = {row.id: row for row in rows}
            rules = {
                row.id: DictationLexiconRule(
                    id=row.id,
                    language=row.language,
                    heard=row.heard,
                    replacement=row.replacement,
                    created_at=row.created_at,
                    expires_at=row.expires_at,
                )
                for row in rows
            }
            yield rules
            for rule_id, row in mapped.items():
                if rule_id not in rules:
                    await session.delete(row)
            # Delete before insertion: an expired phrase can be approved again.
            await session.flush()
            for rule_id, rule in rules.items():
                if rule_id not in mapped:
                    session.add(BridgeDictationLexiconRule(owner=owner, **rule.model_dump()))
            await session.flush()

    async def purge(self, now: datetime) -> None:
        """Purge due owners in finite batches, using the same owner lock as admission."""
        validate_lexicon_time(now)
        while True:
            async with self._transaction(None) as session:
                owners = (
                    await session.scalars(
                        select(BridgeDictationLexiconRule.owner)
                        .where(BridgeDictationLexiconRule.expires_at <= now)
                        .distinct()
                        .limit(100),
                    )
                ).all()
            if not owners:
                return
            for owner in owners:
                async with self._working(owner, now):
                    pass
