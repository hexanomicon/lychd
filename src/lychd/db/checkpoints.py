"""Postgres implementation of the Cortex durable-checkpoint store."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from lychd.db.models.checkpoint import RunCheckpoint

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker


class PostgresStasisStore:
    """Persist one complete JSONB graph snapshot document per run."""

    def __init__(self, session_factory: async_sessionmaker[Any]) -> None:
        """Bind the store to the application database session factory."""
        self._session_factory = session_factory

    async def load(self, run_id: str) -> list[Any] | None:
        async with self._session_factory() as session:
            checkpoint = await session.scalar(select(RunCheckpoint).where(RunCheckpoint.run_id == UUID(run_id)))
            return None if checkpoint is None else copy.deepcopy(checkpoint.snapshots)

    async def replace(self, run_id: str, snapshots: list[Any]) -> None:
        run_uuid = UUID(run_id)
        async with self._session_factory() as session:
            statement = (
                insert(RunCheckpoint)
                .values(run_id=run_uuid, snapshots=copy.deepcopy(snapshots))
                .on_conflict_do_update(
                    index_elements=[RunCheckpoint.run_id],
                    set_={"snapshots": copy.deepcopy(snapshots)},
                )
            )
            async with session.begin():
                await session.execute(statement)

    async def delete(self, run_id: str) -> None:
        async with self._session_factory() as session, session.begin():
            checkpoint = await session.scalar(select(RunCheckpoint).where(RunCheckpoint.run_id == UUID(run_id)))
            if checkpoint is not None:
                await session.delete(checkpoint)

    async def exists(self, run_id: str) -> bool:
        async with self._session_factory() as session:
            return (
                await session.scalar(select(RunCheckpoint.id).where(RunCheckpoint.run_id == UUID(run_id))) is not None
            )
