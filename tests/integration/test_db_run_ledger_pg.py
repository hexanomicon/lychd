"""[LINUX] DbRunLedger durable-substrate suite (F4/H5): CAS matrix + seq fidelity.

WRITTEN HERE, DEFERRED to the Linux/PG runtime pass. The whole module is skipped
where `testcontainers` is absent (the Mac dev box). It validates the durable ledger's
concurrency story on a real Postgres:

- CAS: `set_status` is a compare-and-swap; a CANCELLED write can NOT land over a DONE
  that won the race (0 rows updated → re-read → `IllegalRunTransitionError`), and an
  idempotent same-target concurrent write is benign.
- Seq fidelity: `append_event` persists `RunEvent.seq` VERBATIM as `Step.seq`
  (no insert-time allocation), so Step order equals emit order (Wave-6 Scrying).
"""
# testcontainers is not installed on the Mac (Linux-only); SQLAlchemy Table vs
# FromClause noise on create_all. The whole module is importorskip'd at runtime.
# pyright: reportMissingImports=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportArgumentType=false

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

pytest.importorskip("testcontainers", reason="[LINUX] PG runtime pass only")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from lychd.agents.router import Intent
from lychd.db.models import Run, Step
from lychd.domain.cortex.events import RunEvent, RunEventKind
from lychd.domain.cortex.ledger import DbRunLedger
from lychd.domain.cortex.runs import IllegalRunTransitionError, RunStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def pg_factory() -> Iterator[async_sessionmaker[AsyncSession]]:
    """Spin a pgvector Postgres, create the run/step tables, yield a session factory."""
    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as pg:
        engine: AsyncEngine = create_async_engine(pg.get_connection_url())

        async def _init() -> None:
            async with engine.begin() as conn:
                await conn.run_sync(Run.metadata.create_all, tables=[Run.__table__, Step.__table__])

        asyncio.run(_init())
        yield async_sessionmaker(engine, expire_on_commit=False)
        asyncio.run(engine.dispose())


async def _seed(ledger: DbRunLedger, run_id_hint: str = "") -> str:
    intent = Intent(session_id="s", run_id=run_id_hint or None, prompt="p", source="bridge")
    run = await ledger.create(intent, workflow_name="bridge_chat", queue_name="runs", priority=70)
    return run.run_id


@pytest.mark.asyncio
async def test_cas_cancelled_cannot_land_over_done(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    """CAS: once DONE wins, a later CANCELLED write raises against the fresh truth."""
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    await ledger.set_status(run_id, RunStatus.RUNNING)
    await ledger.set_status(run_id, RunStatus.DONE)  # DONE wins

    with pytest.raises(IllegalRunTransitionError):
        await ledger.set_status(run_id, RunStatus.CANCELLED)  # illegal over terminal DONE

    row = await ledger.get(run_id)
    assert row is not None
    assert row.status is RunStatus.DONE


@pytest.mark.asyncio
async def test_cas_concurrent_same_target_is_benign(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    """CAS: two racing writers to the SAME terminal target both settle without error."""
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    await ledger.set_status(run_id, RunStatus.RUNNING)

    await asyncio.gather(
        ledger.set_status(run_id, RunStatus.DONE),
        ledger.set_status(run_id, RunStatus.DONE),
    )
    row = await ledger.get(run_id)
    assert row is not None
    assert row.status is RunStatus.DONE


@pytest.mark.asyncio
async def test_append_event_persists_seq_verbatim(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    """Seq fidelity: Step.seq equals the RunEvent.seq (no insert-time allocation)."""
    from sqlalchemy import select

    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    for seq, kind in ((0, RunEventKind.STATUS), (1, RunEventKind.NODE), (2, RunEventKind.DONE)):
        await ledger.append_event(RunEvent(run_id=run_id, seq=seq, kind=kind, data="x"))

    async with pg_factory() as session:
        from uuid import UUID

        rows = (await session.execute(select(Step.seq).where(Step.run_id == UUID(run_id)).order_by(Step.seq))).scalars()
        assert list(rows) == [0, 1, 2]  # verbatim, ordered
