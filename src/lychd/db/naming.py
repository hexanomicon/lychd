"""PostgreSQL naming custody with owner-serialized revision acceptance."""

from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy import select, text

from lychd.db.models.naming import NamingRecord
from lychd.domain.naming import (
    NamingAcceptance,
    NamingConflictError,
    NamingSnapshot,
    NamingStoreError,
    PersonalNames,
    validate_owner,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _snapshot(row: NamingRecord) -> NamingSnapshot:
    return NamingSnapshot.model_validate(
        {
            "revision": row.revision,
            "magus_name": row.magus_name,
            "primus_name": row.primus_name,
            "magus_origin": row.magus_origin,
            "primus_origin": row.primus_origin,
        }
    )


class DbNamingStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        """Use the Phylactery-owned private session factory."""
        self._factory = factory

    @asynccontextmanager
    async def _transaction(self, owner: str, *, mutation: bool) -> AsyncGenerator[AsyncSession]:
        validate_owner(owner)
        commit_started = False
        try:
            async with self._factory() as session:
                if session.get_bind().dialect.name != "postgresql":
                    msg = "naming_postgresql_required"
                    raise NamingStoreError(msg)  # noqa: TRY301
                if getattr(session.get_bind(), "hide_parameters", None) is not True:
                    msg = "naming_private_parameters_required"
                    raise NamingStoreError(msg)  # noqa: TRY301
                async with session.begin():
                    await session.execute(text("SET LOCAL statement_timeout = '5s'"))
                    await session.execute(text("SET LOCAL lock_timeout = '2s'"))
                    await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                    if mutation:
                        digest = hashlib.sha256(b"lychd:naming:v1\0" + owner.encode()).digest()
                        await session.execute(
                            text("SELECT pg_advisory_xact_lock(CAST(:lock_id AS BIGINT))"),
                            {"lock_id": int.from_bytes(digest[:8], "big", signed=True)},
                        )
                    yield session
                    commit_started = mutation
        except (NamingConflictError, NamingStoreError):
            raise
        except Exception:  # noqa: BLE001 - names and driver diagnostics stay private
            msg = "naming_commit_unknown" if commit_started else "naming_storage_failure"
            raise NamingStoreError(msg) from None

    async def get(self, owner: str) -> NamingSnapshot | None:
        async with self._transaction(owner, mutation=False) as session:
            row = await session.scalar(
                select(NamingRecord).where(NamingRecord.owner == owner).order_by(NamingRecord.revision.desc()).limit(1)
            )
            return None if row is None else _snapshot(row)

    async def accept(self, owner: str, names: PersonalNames, expected_revision: int) -> NamingSnapshot:
        accepted = NamingAcceptance(names=names, expected_revision=expected_revision)
        async with self._transaction(owner, mutation=True) as session:
            current = await session.scalar(
                select(NamingRecord.revision)
                .where(NamingRecord.owner == owner)
                .order_by(NamingRecord.revision.desc())
                .limit(1)
            )
            if (current or 0) != accepted.expected_revision:
                msg = "Names changed; reload before accepting another revision."
                raise NamingConflictError(msg)
            snapshot = NamingSnapshot(**accepted.names.model_dump(), revision=accepted.expected_revision + 1)
            session.add(NamingRecord(owner=owner, **snapshot.model_dump()))
            await session.flush()
        return snapshot
