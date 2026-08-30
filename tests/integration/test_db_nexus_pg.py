"""[LINUX] PostgreSQL Nexus request admission receipts."""

# pyright: reportMissingImports=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, cast

import pytest
import pytest_asyncio

pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

from sqlalchemy import Table
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from lychd.db.models import NexusSwapRequest
from lychd.db.nexus import DbSwapRequestLedger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.container]


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as pg:
        yield pg.get_connection_url()


@pytest_asyncio.fixture
async def pg_factory(pg_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine: AsyncEngine = create_async_engine(pg_url)
    tables = cast("list[Table]", [NexusSwapRequest.__table__])
    async with engine.begin() as connection:
        await connection.run_sync(NexusSwapRequest.metadata.drop_all, tables=tables)
        await connection.run_sync(NexusSwapRequest.metadata.create_all, tables=tables)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_request_admission_survives_ledger_reconstruction(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_process = DbSwapRequestLedger(pg_factory)
    second_process = DbSwapRequestLedger(pg_factory)

    claims = await asyncio.gather(
        first_process.claim(request_id="request-race", target="chat:first"),
        second_process.claim(request_id="request-race", target="chat:second"),
    )

    assert sum(claim.created for claim in claims) == 1
    winner = next(claim.target for claim in claims if claim.created)
    assert {claim.target for claim in claims} == {winner}

    reconstructed = DbSwapRequestLedger(pg_factory)
    replay = await reconstructed.claim(request_id="request-race", target="chat:third")
    assert replay.created is False
    assert replay.target == winner
