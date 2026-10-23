"""Real PostgreSQL Scout custody; synthetic policy is not credential qualification."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import Table, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lychd.db.models import Consent, Run, RunDelivery, Session
from lychd.db.models.scout import ScoutAttempt, ScoutBudget
from lychd.db.scout import DbScoutAttemptStore
from lychd.domain.scout.attempts import (
    NewScoutClaim,
    ScoutAllowance,
    ScoutAttemptSnapshot,
    ScoutBudgetLimits,
    ScoutCommitUnknownError,
    ScoutConflictError,
    ScoutPreparation,
    ScoutSettlement,
    ScoutStoreError,
)
from lychd.domain.scout.authority import ScoutAction, ScoutAuthorizationDecision
from lychd.domain.scout.profile import ScoutBinding
from tests.postgres_model_tables import with_referenced_tables
from tests.unit.db.test_scout_attempts import prepared_fixture

pytestmark = [pytest.mark.integration, pytest.mark.container]


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    configured = os.environ.get("LYCHD_SCOUT_TEST_DATABASE_URL")
    if configured:
        yield configured
        return
    pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL acceptance")
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


@pytest_asyncio.fixture
async def factory(pg_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(pg_url)
    tables = cast(
        "list[Table]",
        [
            Session.__table__,
            Run.__table__,
            Consent.__table__,
            RunDelivery.__table__,
            ScoutBudget.__table__,
            ScoutAttempt.__table__,
        ],
    )
    tables = with_referenced_tables(tables)
    async with engine.begin() as connection:
        await connection.run_sync(Run.metadata.drop_all, tables=tables)
        await connection.run_sync(Run.metadata.create_all, tables=tables)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


class _Authority:
    """Inert component-test policy; no network and no authentication assertion."""

    allow = True

    def authorize(self, action: ScoutAction, preparation: ScoutPreparation) -> ScoutAuthorizationDecision:
        return ScoutAuthorizationDecision(action=action, preparation_digest=preparation.digest, allowed=self.allow)


class _Completions:
    """Accept only the exact object explicitly retained as owned test completion."""

    def __init__(self) -> None:
        self.owned: tuple[NewScoutClaim, ScoutSettlement] | None = None

    def verify(self, claim: NewScoutClaim, settlement: ScoutSettlement) -> None:
        if self.owned is None or self.owned[0] is not claim or self.owned[1] is not settlement:
            message = "No owned test completion."
            raise ScoutStoreError(message)


def _limits(preparation: ScoutPreparation) -> ScoutBudgetLimits:
    limit = preparation.allowance.add(preparation.allowance)
    return ScoutBudgetLimits(host=limit, binding=limit)


async def _seed(
    factory: async_sessionmaker[AsyncSession],
) -> tuple[DbScoutAttemptStore, ScoutAttemptSnapshot, _Authority, _Completions]:
    preparation, run, binding, review = prepared_fixture()
    async with factory() as session:
        session.add(run)
        await session.flush()
        session.add(
            RunDelivery(
                run_id=run.id,
                enqueue_seq=0,
                queue_name="runs",
                priority=50,
                state="claimed",
                claimed_at=datetime.now(UTC),
            )
        )
        await session.commit()
    authority, completions = _Authority(), _Completions()
    store = DbScoutAttemptStore(factory, authority, _limits(preparation), completions)
    snapshot = await store.prepare(preparation, binding, review)
    return store, snapshot, authority, completions


async def _grant(factory: async_sessionmaker[AsyncSession], snapshot: ScoutAttemptSnapshot) -> None:
    async with factory() as session:
        consent = await session.get(Consent, snapshot.consent_id)
        run = await session.get(Run, snapshot.preparation.run_id)
        delivery = await session.scalar(select(RunDelivery).where(RunDelivery.run_id == snapshot.preparation.run_id))
        assert consent is not None
        assert run is not None
        assert delivery is not None
        consent.status, consent.decided_by, consent.decided_at = "granted", "magus", datetime.now(UTC)
        delivery.state, delivery.settled_at = "settled", datetime.now(UTC)
        await session.flush()
        run.enqueue_seq = 1
        session.add(
            RunDelivery(
                run_id=run.id,
                enqueue_seq=1,
                queue_name="runs",
                priority=50,
                state="claimed",
                claimed_at=datetime.now(UTC),
            )
        )
        await session.commit()


async def _budgets(factory: async_sessionmaker[AsyncSession]) -> list[ScoutBudget]:
    async with factory() as session:
        return list((await session.scalars(select(ScoutBudget).order_by(ScoutBudget.scope))).all())


@pytest.mark.asyncio
async def test_atomic_preparation_duplicate_and_changed_binding(factory: async_sessionmaker[AsyncSession]) -> None:
    store, snapshot, _, _ = await _seed(factory)
    preparation = snapshot.preparation
    async with factory() as session:
        row = await session.get(ScoutAttempt, preparation.attempt_id)
        assert row is not None
        review = row.review_bytes
    repeats = await asyncio.gather(*(store.prepare(preparation, snapshot.native_binding, review) for _ in range(3)))
    assert all(item == snapshot for item in repeats)
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(Consent)) == 1
        assert await session.scalar(select(func.count()).select_from(ScoutAttempt)) == 1
    changed = preparation.model_copy(update={"attempt_id": uuid4()})
    with pytest.raises(ScoutConflictError):
        await store.prepare(changed, snapshot.native_binding, review)
    assert all(row.connects_reserved == 0 for row in await _budgets(factory))


@pytest.mark.asyncio
async def test_fresh_claim_reserves_both_scopes_and_concurrent_duplicate_never_reissues(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    store, snapshot, _, _ = await _seed(factory)
    with pytest.raises(ScoutStoreError):
        await store.claim(snapshot.preparation.attempt_id, snapshot.preparation.digest, 0)
    await _grant(factory, snapshot)
    results = await asyncio.gather(
        *(store.claim(snapshot.preparation.attempt_id, snapshot.preparation.digest, 1) for _ in range(3))
    )
    assert sum(isinstance(result, NewScoutClaim) for result in results) == 1
    assert sum(isinstance(result, ScoutAttemptSnapshot) for result in results) == 2
    assert all(row.connects_reserved == snapshot.preparation.allowance.connects for row in await _budgets(factory))


@pytest.mark.asyncio
async def test_failed_current_authority_rolls_back_reservation(factory: async_sessionmaker[AsyncSession]) -> None:
    store, snapshot, authority, _ = await _seed(factory)
    await _grant(factory, snapshot)
    authority.allow = False
    with pytest.raises(ScoutStoreError):
        await store.claim(snapshot.preparation.attempt_id, snapshot.preparation.digest, 1)
    assert (await store.read(snapshot.preparation.attempt_id)).status == "prepared"
    assert all(row.wire_bytes_reserved == 0 for row in await _budgets(factory))


@pytest.mark.asyncio
async def test_lost_commit_acknowledgement_never_returns_permit_or_refunds(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    store, snapshot, authority, completions = await _seed(factory)
    await _grant(factory, snapshot)
    original = AsyncSession.commit

    async def uncertain(session: AsyncSession) -> None:
        await original(session)
        message = "Synthetic lost acknowledgement after actual database commit."
        raise RuntimeError(message)

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", uncertain)
        with pytest.raises(ScoutCommitUnknownError):
            await store.claim(snapshot.preparation.attempt_id, snapshot.preparation.digest, 1)
    restarted = DbScoutAttemptStore(factory, authority, _limits(snapshot.preparation), completions)
    duplicate = await restarted.claim(snapshot.preparation.attempt_id, snapshot.preparation.digest, 1)
    assert isinstance(duplicate, ScoutAttemptSnapshot)
    assert duplicate.status == "claimed"
    assert await restarted.reconcile_before(datetime.now(UTC) + timedelta(seconds=1)) == 1
    assert (await restarted.read(snapshot.preparation.attempt_id)).status == "unknown_after_crash"
    assert all(row.wire_bytes_reserved == snapshot.preparation.allowance.wire_bytes for row in await _budgets(factory))


@pytest.mark.asyncio
async def test_only_owned_completion_settles_once_and_persists_measured_usage(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    store, snapshot, _, completions = await _seed(factory)
    await _grant(factory, snapshot)
    claim = await store.claim(snapshot.preparation.attempt_id, snapshot.preparation.digest, 1)
    assert isinstance(claim, NewScoutClaim)
    settlement = ScoutSettlement(
        receipt_id=uuid4(),
        outcome="succeeded",
        usage=ScoutAllowance(connects=2, transmissions=5, wire_bytes=1000),
        handoff_evidence=b"[]",
        sockets="closed",
        child="reaped",
    )
    with pytest.raises(ScoutStoreError):
        await store.settle(claim, settlement)
    assert all(row.wire_bytes_reserved == 10000 for row in await _budgets(factory))
    completions.owned = claim, settlement
    settled = await store.settle(claim, settlement)
    assert settled.status == "succeeded"
    assert settled.receipt_digest is not None
    assert await store.settle(claim, settlement) == settled
    assert all(row.wire_bytes_reserved == 0 and row.wire_bytes_used == 1000 for row in await _budgets(factory))


@pytest.mark.asyncio
async def test_unknown_keeps_full_reservation_and_changed_config_cannot_reset_it(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    store, snapshot, authority, completions = await _seed(factory)
    await _grant(factory, snapshot)
    claim = await store.claim(snapshot.preparation.attempt_id, snapshot.preparation.digest, 1)
    assert isinstance(claim, NewScoutClaim)
    unknown = await store.unknown(claim)
    assert unknown.status == "unknown_after_crash"
    assert isinstance(
        await store.claim(snapshot.preparation.attempt_id, snapshot.preparation.digest, 1), ScoutAttemptSnapshot
    )
    larger = snapshot.preparation.allowance.add(_limits(snapshot.preparation).host)
    changed = DbScoutAttemptStore(factory, authority, ScoutBudgetLimits(host=larger, binding=larger), completions)
    with pytest.raises(ScoutConflictError):
        await changed.claim(snapshot.preparation.attempt_id, snapshot.preparation.digest, 1)
    assert all(row.connects_reserved == 3 and row.connects_used == 0 for row in await _budgets(factory))
    another_store, another_snapshot, _, _ = await _seed(factory)
    await _grant(factory, another_snapshot)
    with pytest.raises(ScoutStoreError):
        await another_store.claim(another_snapshot.preparation.attempt_id, another_snapshot.preparation.digest, 1)
    binding_budget = next(row for row in await _budgets(factory) if row.scope == "binding")
    assert binding_budget.active_claims == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["delivery", "consent", "admission"])
async def test_claim_rechecks_actual_retained_owners(factory: async_sessionmaker[AsyncSession], changed: str) -> None:
    store, snapshot, _, _ = await _seed(factory)
    await _grant(factory, snapshot)
    async with factory() as session:
        if changed == "consent":
            consent = await session.get(Consent, snapshot.consent_id)
            assert consent is not None
            consent.native_binding = {**cast("dict[str, object]", consent.native_binding), "review_digest": "f" * 64}
        else:
            run = await session.get(Run, snapshot.preparation.run_id)
            assert run is not None
            if changed == "delivery":
                run.enqueue_seq = 2
            else:
                admitted = ScoutBinding.model_validate(run.intent["admitted_scout"])
                run.intent = {
                    "admitted_scout": admitted.model_copy(update={"question": "Changed question."}).model_dump(
                        mode="json"
                    )
                }
        await session.commit()
    with pytest.raises(ScoutStoreError):
        await store.claim(snapshot.preparation.attempt_id, snapshot.preparation.digest, 1)
    assert all(row.connects_reserved == 0 for row in await _budgets(factory))


@pytest.mark.asyncio
async def test_binding_slot_serializes_attempts_and_settlement_preserves_cumulative_ceiling(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    attempts = [await _seed(factory) for _ in range(3)]
    for _, snapshot, _, _ in attempts:
        await _grant(factory, snapshot)
    results = await asyncio.gather(
        *(
            store.claim(snapshot.preparation.attempt_id, snapshot.preparation.digest, 1)
            for store, snapshot, _, _ in attempts
        ),
        return_exceptions=True,
    )
    assert sum(isinstance(item, NewScoutClaim) for item in results) == 1
    assert sum(isinstance(item, ScoutStoreError) for item in results) == 2
    winner = next(index for index, item in enumerate(results) if isinstance(item, NewScoutClaim))
    claim = cast("NewScoutClaim", results[winner])
    store, _, _, completions = attempts[winner]
    settlement = ScoutSettlement(
        receipt_id=uuid4(),
        outcome="succeeded",
        usage=claim.preparation.allowance,
        handoff_evidence=b"[]",
        sockets="closed",
        child="reaped",
    )
    completions.owned = claim, settlement
    await store.settle(claim, settlement)
    waiting = [item for index, item in enumerate(attempts) if index != winner]
    next_store, next_snapshot, _, next_completions = waiting[0]
    next_claim = await next_store.claim(next_snapshot.preparation.attempt_id, next_snapshot.preparation.digest, 1)
    assert isinstance(next_claim, NewScoutClaim)
    next_settlement = settlement.model_copy(update={"receipt_id": uuid4()})
    next_completions.owned = next_claim, next_settlement
    await next_store.settle(next_claim, next_settlement)
    last_store, last_snapshot, _, _ = waiting[1]
    with pytest.raises(ScoutStoreError):
        await last_store.claim(last_snapshot.preparation.attempt_id, last_snapshot.preparation.digest, 1)
    budgets = await _budgets(factory)
    assert all(row.connects_reserved == 0 and row.connects_used == 6 for row in budgets)
    assert all(row.active_claims == 0 for row in budgets)


@pytest.mark.asyncio
async def test_preparation_commit_unknown_reuses_same_native_consent(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    preparation, run, binding, review = prepared_fixture()
    async with factory() as session:
        session.add(run)
        await session.flush()
        session.add(
            RunDelivery(
                run_id=run.id,
                enqueue_seq=0,
                queue_name="runs",
                priority=50,
                state="claimed",
                claimed_at=datetime.now(UTC),
            )
        )
        await session.commit()
    store = DbScoutAttemptStore(factory, _Authority(), _limits(preparation), _Completions())
    original = AsyncSession.commit

    async def uncertain(session: AsyncSession) -> None:
        await original(session)
        message = "Synthetic lost acknowledgement after committed preparation."
        raise RuntimeError(message)

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", uncertain)
        with pytest.raises(ScoutCommitUnknownError):
            await store.prepare(preparation, binding, review)
    retained = await store.read_request(preparation.request_id)
    assert retained is not None
    assert await store.prepare(preparation, binding, review) == retained
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(Consent)) == 1
    assert all(row.connects_reserved == 0 for row in await _budgets(factory))
