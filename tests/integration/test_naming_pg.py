"""Naming reconstruction, concurrent acceptance and rollback on disposable PostgreSQL."""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import AsyncIterator
from typing import cast

import pytest
import pytest_asyncio
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Table, func, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lychd.db.models.naming import NamingRecord
from lychd.db.naming import DbNamingStore
from lychd.domain.naming import NamingConflictError, NamingSnapshot
from tests.integration import test_db_migrations_pg as migration_fixtures
from tests.unit.domain.test_naming import names

pytestmark = [pytest.mark.integration, pytest.mark.container, pytest.mark.asyncio]
pg_url = migration_fixtures.pg_url
TABLES = [cast("Table", NamingRecord.__table__)]


def migrate(connection: Connection) -> None:
    with Operations.context(MigrationContext.configure(connection)):
        importlib.import_module("lychd.db.migrations.versions.0027_primus_naming").upgrade()


def downgrade(connection: Connection) -> None:
    with Operations.context(MigrationContext.configure(connection)):
        importlib.import_module("lychd.db.migrations.versions.0027_primus_naming").downgrade()


@pytest_asyncio.fixture(params=["models", "migration"])
async def factory(pg_url: str, request: pytest.FixtureRequest) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(pg_url, hide_parameters=True)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(NamingRecord.metadata.drop_all, tables=TABLES)
            if request.param == "migration":
                await connection.run_sync(migrate)
            else:
                await connection.run_sync(NamingRecord.metadata.create_all, tables=TABLES)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(NamingRecord.metadata.drop_all, tables=TABLES)
        await engine.dispose()


async def test_reconstruction_owner_isolation_and_retained_history(factory: async_sessionmaker[AsyncSession]) -> None:
    assert await DbNamingStore(factory).get("alice") is None
    first = await DbNamingStore(factory).accept("alice", names(), 0)
    assert await DbNamingStore(factory).get("alice") == first
    assert await DbNamingStore(factory).get("bob") is None
    second = await DbNamingStore(factory).accept("alice", names(primus_name="Aster Dawnkeeper"), 1)
    assert await DbNamingStore(factory).get("alice") == second
    assert first.primus_name == "Liora Shadowdancer"
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(NamingRecord)) == 2
    with pytest.raises(NamingConflictError):
        await DbNamingStore(factory).accept("alice", names(), 1)
    assert await DbNamingStore(factory).get("alice") == second


async def test_concurrent_first_acceptance_has_one_winner(factory: async_sessionmaker[AsyncSession]) -> None:
    outcomes = await asyncio.gather(
        DbNamingStore(factory).accept("alice", names(primus_name="Seren Silverleaf"), 0),
        DbNamingStore(factory).accept("alice", names(primus_name="Aster Dawnkeeper"), 0),
        return_exceptions=True,
    )
    assert sum(isinstance(result, NamingConflictError) for result in outcomes) == 1
    winners = [result for result in outcomes if isinstance(result, NamingSnapshot)]
    assert len(winners) == 1
    assert await DbNamingStore(factory).get("alice") == winners[0]


async def test_nonempty_downgrade_refuses_retained_names(factory: async_sessionmaker[AsyncSession]) -> None:
    first = await DbNamingStore(factory).accept("alice", names(), 0)
    async with factory() as session, session.begin():
        connection = await session.connection()
        with pytest.raises(DBAPIError, match="Retained naming revisions prevent downgrade"):
            await connection.run_sync(downgrade)
        await session.rollback()
    assert await DbNamingStore(factory).get("alice") == first


async def test_empty_downgrade_and_upgrade_round_trip(factory: async_sessionmaker[AsyncSession]) -> None:
    async with factory() as session, session.begin():
        connection = await session.connection()
        await connection.run_sync(downgrade)
        await connection.run_sync(migrate)
    assert await DbNamingStore(factory).get("alice") is None
    assert (await DbNamingStore(factory).accept("alice", names(), 0)).revision == 1
