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
from unittest import mock

import pytest

pytest.importorskip("testcontainers", reason="[LINUX] PG runtime pass only")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from lychd.agents.router import Intent
from lychd.db.models import Run, Session, Step
from lychd.domain.cortex.events import InProcessEventBus, RunEvent, RunEventKind
from lychd.domain.cortex.ledger import DbRunLedger
from lychd.domain.cortex.runs import IllegalRunTransitionError, RunStatus
from lychd.domain.cortex.services import RunService
from lychd.domain.web.schemas import BridgeTurn
from lychd.domain.web.sessions import DbBridgeSessionStore

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
                await conn.run_sync(
                    Run.metadata.create_all,
                    tables=[Session.__table__, Run.__table__, Step.__table__],
                )

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
async def test_concurrent_run_claim_has_one_winner(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    """At-least-once broker delivery is fenced by one QUEUED→RUNNING CAS."""
    first = DbRunLedger(session_factory=pg_factory)
    second = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(first)

    results = await asyncio.gather(
        first.try_claim_run(run_id, enqueue_seq=0),
        second.try_claim_run(run_id, enqueue_seq=0),
    )

    assert sorted(results) == [False, True]
    row = await first.get(run_id)
    assert row is not None
    assert row.status is RunStatus.RUNNING


@pytest.mark.asyncio
async def test_claimed_failure_cannot_overwrite_new_resume_hop(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """The failure CAS is fenced by the enqueue sequence that this worker claimed."""
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    assert await ledger.bump_enqueue_seq(run_id) == 1
    assert await ledger.try_claim_run(run_id, enqueue_seq=1) is True

    await ledger.set_status(run_id, RunStatus.AWAITING_CONSENT)
    assert await ledger.try_admit_consent(run_id) == 2
    assert await ledger.try_claim_run(run_id, enqueue_seq=2) is True

    assert await ledger.try_fail_claimed(run_id, enqueue_seq=1, error="old hop failed") is False
    running = await ledger.get(run_id)
    assert running is not None
    assert running.status is RunStatus.RUNNING
    assert running.enqueue_seq == 2

    assert await ledger.try_fail_claimed(run_id, enqueue_seq=2, error="current hop failed") is True
    failed = await ledger.get(run_id)
    assert failed is not None
    assert failed.status is RunStatus.FAILED
    assert failed.error == "current hop failed"


@pytest.mark.asyncio
async def test_stale_consent_delivery_cannot_claim_retried_hop(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Postgres admission and hop allocation are one CAS; stale jobs cannot claim."""
    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    assert await ledger.try_claim_run(run_id, enqueue_seq=0) is True
    await ledger.set_status(run_id, RunStatus.AWAITING_CONSENT)

    assert await ledger.try_admit_consent(run_id) == 1
    assert await ledger.try_restore_consent_wait(run_id, enqueue_seq=1) is True
    assert await ledger.try_admit_consent(run_id) == 2

    assert await ledger.try_claim_run(run_id, enqueue_seq=1) is False
    assert await ledger.try_claim_run(run_id, enqueue_seq=2) is True


@pytest.mark.asyncio
async def test_cas_retries_lost_cancel_against_legal_fresh_edge(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """R3: a cancel losing a QUEUED→RUNNING claim retries against the fresh RUNNING and lands CANCELLED.

    We force the CAS window deterministically: a one-shot hook on the ledger's first
    row read commits a concurrent QUEUED→RUNNING claim, so the cancel's first CAS
    (`WHERE status='queued'`) matches 0 rows. The re-read sees RUNNING; RUNNING→CANCELLED
    is legal, so the bounded retry lands it instead of raising.
    """
    ledger = DbRunLedger(session_factory=pg_factory)
    claimant = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)

    original = RunService.get_one_or_none
    fired = {"done": False}

    async def racing_read(self: RunService, *args: object, **kwargs: object) -> object:
        row = await original(self, *args, **kwargs)  # reads the still-QUEUED row
        if not fired["done"]:
            fired["done"] = True
            await claimant.set_status(run_id, RunStatus.RUNNING)  # concurrent claim wins the window
        return row

    with mock.patch.object(RunService, "get_one_or_none", racing_read):
        await ledger.set_status(run_id, RunStatus.CANCELLED)  # must NOT raise — legal fresh edge

    row = await ledger.get(run_id)
    assert row is not None
    assert row.status is RunStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_losing_to_completion_is_benign(pg_factory: async_sessionmaker[AsyncSession]) -> None:
    """R7: engine.cancel losing to completion (fresh DONE, DONE→CANCELLED illegal) is a benign no-op, not a 500."""
    from lychd.domain.cortex.engine import QueueRouter
    from lychd.domain.cortex.engine import RunEngine as CortexRunEngine

    ledger = DbRunLedger(session_factory=pg_factory)
    completer = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    await ledger.set_status(run_id, RunStatus.RUNNING)

    class _Queue:
        async def enqueue(self, job_or_func: str, /, **kwargs: object) -> object:
            _ = (job_or_func, kwargs)
            return None

        async def job(self, job_key: str, /) -> object:
            _ = job_key
            return None

        async def abort(self, job: object, error: str, /, ttl: float = 5) -> None:
            _ = (job, error, ttl)

    engine = CortexRunEngine(
        ledger=ledger,
        bus=InProcessEventBus(ledger=ledger),
        workflows=None,
        queue_router=QueueRouter(),
        queues={"runs": _Queue()},
    )

    original = RunService.get_one_or_none
    fired = {"done": False}

    async def racing_read(self: RunService, *args: object, **kwargs: object) -> object:
        row = await original(self, *args, **kwargs)  # cancel's top read sees RUNNING
        if not fired["done"]:
            fired["done"] = True
            await completer.set_status(run_id, RunStatus.DONE)  # completion wins the race
        return row

    with mock.patch.object(RunService, "get_one_or_none", racing_read):
        await engine.cancel(run_id)  # must NOT raise — run already terminal → no-op

    row = await ledger.get(run_id)
    assert row is not None
    assert row.status is RunStatus.DONE  # completion won; cancel was a benign no-op


@pytest.mark.asyncio
async def test_reconcile_orphaned_running_lands_terminal_step(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """R1: a reconciled orphan (with a persisted Step) lands its terminal Step instead of colliding.

    Restart shape: the run reached RUNNING and persisted Step(seq=0); the process
    died; a FRESH bus restarts channel seqs at 0. Without seeding, reconcile's terminal
    emit would write Step(seq=0) → `uq_step_run_seq` violation → dropped. With the R1
    seed (`open(from_seq=next_seq)`), the terminal lands at seq 1.
    """
    from types import SimpleNamespace
    from uuid import UUID

    from sqlalchemy import select

    from lychd.ghouls.runs import reconcile_runs

    ledger = DbRunLedger(session_factory=pg_factory)
    run_id = await _seed(ledger)
    await ledger.set_status(run_id, RunStatus.RUNNING)
    await ledger.append_event(RunEvent(run_id=run_id, seq=0, kind=RunEventKind.STATUS, data="running"))

    # Fresh process: a brand-new bus (channel seqs restart at 0). reconcile only needs
    # the substrate's ledger + bus, so a namespace stand-in is sufficient here.
    bus = InProcessEventBus(ledger=ledger)
    substrate = SimpleNamespace(ledger=ledger, bus=bus)
    result = await reconcile_runs({"run_substrate": substrate})
    assert result["count"] >= 1

    for _ in range(50):  # drain the per-run ORDERED writer chain (the terminal persist)
        await asyncio.sleep(0)

    async with pg_factory() as session:
        rows = (await session.execute(select(Step.seq).where(Step.run_id == UUID(run_id)).order_by(Step.seq))).scalars()
        seqs = list(rows)
    assert seqs == [0, 1]  # pre-existing status + the reconciled terminal — no collision, nothing dropped


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


@pytest.mark.asyncio
async def test_concurrent_session_turn_appends_are_not_lost(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Concurrent writers serialize on the Session row and retain every JSONB turn."""
    store = DbBridgeSessionStore(pg_factory, sigil_name="magus")
    bridge_session = await store.create_session(title="concurrent")
    turns = [BridgeTurn(role="agent", content=f"turn-{index}") for index in range(16)]

    await asyncio.gather(*(store.add_turn(bridge_session.id, turn) for turn in turns))

    persisted = await store.get_session(bridge_session.id)
    assert persisted is not None
    assert {turn.content for turn in persisted.turns} == {turn.content for turn in turns}
    assert len(persisted.turns) == len(turns)
