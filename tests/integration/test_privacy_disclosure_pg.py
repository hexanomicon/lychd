"""Opt-in PostgreSQL disclosure custody with an explicitly synthetic recorder.

LYCHD_PRIVACY_TEST_DATABASE_URL selects an operator-provided disposable database.
Otherwise the explicit container test profile supplies a bounded PostgreSQL
container. No transport or application is started. Tables are ORM-derived in a
fresh owned schema; migration lineage is qualified by the separate test module.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import Table, delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from lychd.db.models import Consent, Run, RunDelivery, Session
from lychd.db.models.privacy import DisclosureCapacityRecord, DisclosureTransmission
from lychd.domain.cortex.cancellation import RunEffectFence
from lychd.domain.privacy.contracts import CutBinding, PreparationPolicy, PreparedCut, WholeProjection, digest
from lychd.domain.privacy.disclosure import (
    DisclosureCapacity,
    DisclosureError,
    DisclosureLimits,
    DisclosureRunBinding,
    DisclosureSnapshot,
    FreshDisclosureClaim,
)
from lychd.domain.privacy.fixtures import diagnostic_fixture, fixture_binding
from lychd.domain.privacy.preparation import CutAuthority, make_plan, prepare_cut
from lychd.system.services.privacy_disclosure import (
    PrivacyDisclosureService,
    RecordingSink,
    SyntheticExportAuthority,
)
from tests.postgres_model_tables import with_referenced_tables

pytestmark = [pytest.mark.integration, pytest.mark.container, pytest.mark.asyncio]
_HOST_ID = UUID(int=301)
_PURPOSE_ID = UUID(int=206)


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    configured = os.environ.get("LYCHD_PRIVACY_TEST_DATABASE_URL")
    if configured:
        yield configured
        return
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer(
        "pgvector/pgvector:pg18-trixie",
        driver="asyncpg",
        mem_limit="512m",
        nano_cpus=1_000_000_000,
        pids_limit=128,
    ) as postgres:
        yield postgres.get_connection_url()


@pytest_asyncio.fixture
async def factory(pg_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    schema = f"disclosure_proof_{uuid4().hex}"
    engine = create_async_engine(
        pg_url,
        pool_size=2,
        max_overflow=0,
        execution_options={"schema_translate_map": {None: schema}},
    )
    tables = cast(
        "list[Table]",
        [
            Session.__table__,
            Run.__table__,
            Consent.__table__,
            RunDelivery.__table__,
            DisclosureCapacityRecord.__table__,
            DisclosureTransmission.__table__,
        ],
    )
    tables = with_referenced_tables(tables)
    created = False
    try:
        async with engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
            created = True
            await connection.run_sync(Run.metadata.create_all, tables=tables)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        try:
            if created:
                async with engine.begin() as connection:
                    await connection.execute(DropSchema(schema, cascade=True))
        finally:
            await engine.dispose()


@dataclass
class _Fixture:
    source: WholeProjection
    host_id: UUID
    configuration: str
    binding: CutBinding
    policy: PreparationPolicy
    run_binding: DisclosureRunBinding
    run: Run
    delivery: RunDelivery
    cuts: CutAuthority
    prepared: PreparedCut

    def authority(self) -> SyntheticExportAuthority:
        return SyntheticExportAuthority(
            host_id=self.host_id,
            binding=self.binding,
            run=self.run_binding,
            policy=self.policy,
            configuration_digest=self.configuration,
        )


def _fixture(
    *,
    host_id: UUID = _HOST_ID,
    purpose_id: UUID = _PURPOSE_ID,
    configuration: str | None = None,
) -> _Fixture:
    # Choose expected host and retained execution facts before constructing the Cut.
    run_id, delivery_id = uuid4(), uuid4()
    intent = {"operation": "synthetic-offline-diagnostic-export"}
    pattern = {"revision": "synthetic-recording-pattern@1"}
    binding = fixture_binding().model_copy(
        update={"run_id": run_id, "occurrence_id": uuid4(), "attempt_id": uuid4(), "purpose_id": purpose_id}
    )
    run_binding = DisclosureRunBinding(
        run_id=run_id,
        delivery_id=delivery_id,
        enqueue_seq=0,
        priority=50,
        queue_name="runs",
        workflow_name="synthetic-disclosure",
        sigil_name="synthetic-disclosure",
        intent_digest=digest(intent),
        pattern_digest=digest(pattern),
    )
    run = Run(
        id=run_id,
        workflow_name=run_binding.workflow_name,
        pattern_manifest=pattern,
        source="cli",
        status="running",
        priority=run_binding.priority,
        sigil_name=run_binding.sigil_name,
        intent=intent,
        queue_name=run_binding.queue_name,
        enqueue_seq=run_binding.enqueue_seq,
    )
    delivery = RunDelivery(
        id=delivery_id,
        run_id=run_id,
        enqueue_seq=run_binding.enqueue_seq,
        queue_name=run_binding.queue_name,
        priority=run_binding.priority,
        state="claimed",
        claimed_at=datetime.now(UTC),
    )
    source, policy, cuts = diagnostic_fixture(), PreparationPolicy(), CutAuthority()
    configuration = configuration or digest("synthetic-disclosure-configuration@1")
    # This exact authority is independently pinned, never derived from cut.plan.binding.
    authority = SyntheticExportAuthority(
        host_id=host_id,
        binding=binding,
        run=run_binding,
        policy=policy,
        configuration_digest=configuration,
    )
    now = int(time.time())
    plan = make_plan(source, authority.binding, policy, expires_at=now + 300)
    prepared = prepare_cut(source, plan, policy, cuts, now=now)
    return _Fixture(source, host_id, configuration, binding, policy, run_binding, run, delivery, cuts, prepared)


def _limits(size: int, *, host_uses: int = 16, purpose_uses: int = 16) -> DisclosureLimits:
    return DisclosureLimits(
        host=DisclosureCapacity(uses=host_uses, bytes=16 * size),
        purpose=DisclosureCapacity(uses=purpose_uses, bytes=16 * size),
    )


def _service(
    factory: async_sessionmaker[AsyncSession],
    fixture: _Fixture,
    limits: DisclosureLimits,
    *,
    cuts: CutAuthority | None = None,
) -> tuple[PrivacyDisclosureService, RecordingSink, SyntheticExportAuthority]:
    sink, authority = RecordingSink(), fixture.authority()
    service = PrivacyDisclosureService(
        factory,
        authority=authority,
        cut_authority=cuts or fixture.cuts,
        limits=limits,
        fence=RunEffectFence(),
        sink=sink,
    )
    return service, sink, authority


@dataclass
class _Rig:
    fixture: _Fixture
    limits: DisclosureLimits
    service: PrivacyDisclosureService
    sink: RecordingSink
    authority: SyntheticExportAuthority
    snapshot: DisclosureSnapshot


async def _seed(
    factory: async_sessionmaker[AsyncSession],
    fixture: _Fixture | None = None,
    limits: DisclosureLimits | None = None,
) -> _Rig:
    fixture = fixture or _fixture()
    limits = limits or _limits(len(fixture.prepared.candidate))
    async with factory() as session:
        session.add(fixture.run)
        await session.flush()
        session.add(fixture.delivery)
        await session.commit()
    service, sink, authority = _service(factory, fixture, limits)
    snapshot = await service.prepare(fixture.prepared, request_id=uuid4(), transmission_id=uuid4())
    return _Rig(fixture, limits, service, sink, authority, snapshot)


async def _capacities(factory: async_sessionmaker[AsyncSession]) -> list[DisclosureCapacityRecord]:
    async with factory() as session:
        return list(
            (await session.scalars(select(DisclosureCapacityRecord).order_by(DisclosureCapacityRecord.scope))).all()
        )


async def _assert_charged(factory: async_sessionmaker[AsyncSession], size: int, uses: int = 1) -> None:
    capacities = await _capacities(factory)
    assert {row.scope for row in capacities} == {"host", "purpose", "cut"}
    assert all(row.uses_charged == uses and row.bytes_charged == uses * size for row in capacities)


async def _fresh(rig: _Rig) -> FreshDisclosureClaim:
    claim = await rig.service.claim(rig.snapshot.preparation)
    assert isinstance(claim, FreshDisclosureClaim)
    return claim


async def test_concurrent_duplicate_has_one_fresh_claim_and_one_exact_record(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    rig = await _seed(factory)
    repeats = await asyncio.gather(
        *(
            rig.service.prepare(
                rig.fixture.prepared,
                request_id=rig.snapshot.preparation.request_id,
                transmission_id=rig.snapshot.preparation.transmission_id,
            )
            for _ in range(3)
        )
    )
    assert all(item == rig.snapshot for item in repeats)
    results = await asyncio.gather(*(rig.service.claim(rig.snapshot.preparation) for _ in range(3)))
    claims = [item for item in results if isinstance(item, FreshDisclosureClaim)]
    assert len(claims) == 1
    assert sum(isinstance(item, DisclosureSnapshot) for item in results) == 2
    claim = claims[0]
    completion = await rig.service.record(claim)
    assert completion.outcome == "recorded"
    settled = await rig.service.settle(claim, completion)
    assert settled.status == "recorded"
    assert await rig.service.settle(claim, completion) == settled
    assert rig.sink.records == (rig.fixture.prepared.candidate,)
    with pytest.raises(DisclosureError, match="claim"):
        await rig.service.record(claim)
    await _assert_charged(factory, len(rig.fixture.prepared.candidate))
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(DisclosureTransmission)) == 1
        row = await session.get(DisclosureTransmission, settled.preparation.transmission_id)
        assert row is not None
        evidence = row.preparation_bytes + (row.decision_bytes or b"") + (row.settlement_bytes or b"")
    for forbidden in (b"SYNTHETIC-PERSON-017", b"sensitive_spans", b"source_id", rig.fixture.prepared.candidate):
        assert forbidden not in evidence
    for material in rig.fixture.source.materials():
        assert str(material.source_id).encode() not in evidence
        assert all(str(subject).encode() not in evidence for subject in material.label.subjects)


@pytest.mark.parametrize("scope", ["host", "purpose"])
@pytest.mark.parametrize("dimension", ["uses", "bytes"])
async def test_competing_fresh_runs_and_cuts_cannot_overspend_or_refund(
    factory: async_sessionmaker[AsyncSession], scope: str, dimension: str
) -> None:
    size = len(_fixture().prepared.candidate)
    wide = DisclosureCapacity(uses=16, bytes=16 * size)
    narrow = DisclosureCapacity(
        uses=1 if dimension == "uses" else 16, bytes=size if dimension == "bytes" else 16 * size
    )
    limits = DisclosureLimits(host=narrow if scope == "host" else wide, purpose=narrow if scope == "purpose" else wide)
    rigs = [await _seed(factory, limits=limits) for _ in range(3)]
    results = await asyncio.gather(
        *(rig.service.claim(rig.snapshot.preparation) for rig in rigs), return_exceptions=True
    )
    assert sum(isinstance(item, FreshDisclosureClaim) for item in results) == 1
    failures = [item for item in results if isinstance(item, DisclosureError)]
    assert len(failures) == 2
    assert all(item.code == "capacity" for item in failures)
    winner = next(index for index, item in enumerate(results) if isinstance(item, FreshDisclosureClaim))
    claim = cast("FreshDisclosureClaim", results[winner])
    completion = await rigs[winner].service.record(claim)
    assert (await rigs[winner].service.settle(claim, completion)).status == "recorded"
    fresh = await _seed(factory, limits=limits)
    with pytest.raises(DisclosureError, match="capacity"):
        await fresh.service.claim(fresh.snapshot.preparation)
    capacities = await _capacities(factory)
    assert all(row.uses_charged == 1 and row.bytes_charged == size for row in capacities if row.scope != "cut")
    cuts = [row for row in capacities if row.scope == "cut"]
    assert sum(row.uses_charged for row in cuts) == 1
    assert sum(row.bytes_charged for row in cuts) == size
    assert sum(len(rig.sink.records) for rig in [*rigs, fresh]) == 1


@pytest.mark.parametrize("changed", ["ids", "configuration", "limits", "host"])
async def test_cut_and_stable_host_capacity_cannot_be_reset_by_new_identity_or_configuration(
    factory: async_sessionmaker[AsyncSession], changed: str
) -> None:
    fixture = _fixture()
    limits = _limits(len(fixture.prepared.candidate), host_uses=1)
    rig = await _seed(factory, fixture, limits)
    claim = await _fresh(rig)
    await rig.service.store.recover(claim.preparation.transmission_id)
    if changed == "ids":
        with pytest.raises(DisclosureError, match="conflict"):
            await rig.service.prepare(fixture.prepared, request_id=uuid4(), transmission_id=uuid4())
    else:
        changed_fixture = _fixture(
            host_id=uuid4() if changed == "host" else fixture.host_id,
            configuration=digest("replacement-configuration") if changed == "configuration" else fixture.configuration,
        )
        changed_limits = _limits(len(fixture.prepared.candidate), host_uses=16) if changed == "limits" else limits
        with pytest.raises(DisclosureError, match="conflict"):
            await _seed(factory, changed_fixture, changed_limits)
    await _assert_charged(factory, len(fixture.prepared.candidate))
    assert rig.sink.records == ()
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(DisclosureTransmission)) == 1


_RUN_CHANGES: dict[str, Any] = {
    "status": "cancelled",
    "enqueue_seq": 1,
    "priority": 49,
    "queue_name": "changed",
    "workflow_name": "changed",
    "sigil_name": "changed",
    "intent": {"operation": "different"},
    "pattern_manifest": {"revision": "different"},
}
_DELIVERY_CHANGES: dict[str, Any] = {
    "state": "settled",
    "claimed_at": None,
    "enqueue_seq": 1,
    "priority": 49,
    "queue_name": "changed",
}


@pytest.mark.parametrize("phase", ["claim", "record"])
@pytest.mark.parametrize(
    ("owner", "field"),
    [("run", field) for field in _RUN_CHANGES] + [("delivery", field) for field in _DELIVERY_CHANGES],
)
async def test_actual_retained_run_and_exact_delivery_are_rechecked(
    factory: async_sessionmaker[AsyncSession], phase: str, owner: str, field: str
) -> None:
    rig = await _seed(factory)
    claim = await _fresh(rig) if phase == "record" else None
    model = Run if owner == "run" else RunDelivery
    row_id = rig.fixture.run_binding.run_id if owner == "run" else rig.fixture.run_binding.delivery_id
    changes = _RUN_CHANGES if owner == "run" else _DELIVERY_CHANGES
    async with factory() as session:
        await session.execute(update(model).where(model.id == row_id).values({field: changes[field]}))
        await session.commit()
    if claim is None:
        with pytest.raises(DisclosureError, match="binding"):
            await rig.service.claim(rig.snapshot.preparation)
        retained = await rig.service.store.read(rig.snapshot.preparation.transmission_id)
        assert retained is not None
        assert retained.status == "prepared"
        await _assert_charged(factory, len(rig.fixture.prepared.candidate), uses=0)
    else:
        completion = await rig.service.record(claim)
        assert completion.outcome == "refused"
        assert (await rig.service.settle(claim, completion)).status == "refused"
        await _assert_charged(factory, len(rig.fixture.prepared.candidate))
    assert rig.sink.records == ()


async def test_actual_commit_lost_acknowledgement_reconstruction_never_reissues(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = await _seed(factory, limits=_limits(len(_fixture().prepared.candidate), host_uses=1))
    original = AsyncSession.commit

    async def lost_ack(session: AsyncSession) -> None:
        await original(session)
        message = "Synthetic acknowledgement lost after actual PostgreSQL commit."
        raise RuntimeError(message)

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", lost_ack)
        with pytest.raises(DisclosureError, match="commit-unknown"):
            await rig.service.claim(rig.snapshot.preparation)
    retained = await rig.service.store.read(rig.snapshot.preparation.transmission_id)
    assert retained is not None
    assert retained.status == "claimed"
    assert retained.claim_id is not None
    reconstructed, sink, authority = _service(factory, rig.fixture, rig.limits, cuts=CutAuthority())
    assert authority is not rig.authority
    assert await reconstructed.claim(retained.preparation) == retained
    fabricated = FreshDisclosureClaim(retained.preparation, retained.claim_id)
    for service in (rig.service, reconstructed):
        with pytest.raises(DisclosureError, match="claim"):
            await service.record(fabricated)
    with pytest.raises(DisclosureError, match="binding"):
        await reconstructed.prepare(
            rig.fixture.prepared,
            request_id=retained.preparation.request_id,
            transmission_id=retained.preparation.transmission_id,
        )
    unknown = await reconstructed.store.recover(retained.preparation.transmission_id)
    assert unknown.status == "unknown"
    assert await reconstructed.store.recover(retained.preparation.transmission_id) == unknown
    assert await reconstructed.claim(retained.preparation) == unknown
    fresh = await _seed(factory, limits=rig.limits)
    with pytest.raises(DisclosureError, match="capacity"):
        await fresh.service.claim(fresh.snapshot.preparation)
    assert rig.sink.records == sink.records == fresh.sink.records == ()
    capacities = await _capacities(factory)
    assert all(row.uses_charged == 1 for row in capacities if row.scope != "cut")
    assert sum(row.uses_charged for row in capacities if row.scope == "cut") == 1


async def test_failure_before_commit_returns_no_claim_and_rolls_back_charges(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = await _seed(factory)

    async def before_commit(session: AsyncSession) -> None:
        message = "Synthetic failure before database commit."
        raise RuntimeError(message)

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", before_commit)
        with pytest.raises(DisclosureError, match="commit-unknown"):
            await rig.service.claim(rig.snapshot.preparation)
    assert await rig.service.store.read(rig.snapshot.preparation.transmission_id) == rig.snapshot
    await _assert_charged(factory, len(rig.fixture.prepared.candidate), uses=0)
    assert rig.sink.records == ()


@pytest.mark.parametrize("phase", ["claim", "record"])
async def test_current_authority_revocation_after_real_commit_prevents_activation(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    rig = await _seed(factory)
    claim = await _fresh(rig) if phase == "record" else None
    original = AsyncSession.commit

    async def revoke_after_commit(session: AsyncSession) -> None:
        await original(session)
        rig.authority.revoked = True

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", revoke_after_commit)
        if claim is None:
            with pytest.raises(DisclosureError, match="authority"):
                await rig.service.claim(rig.snapshot.preparation)
        else:
            completion = await rig.service.record(claim)
            assert completion.outcome == "refused"
    assert rig.sink.records == ()
    await _assert_charged(factory, len(rig.fixture.prepared.candidate))
    retained = await rig.service.store.recover(rig.snapshot.preparation.transmission_id)
    assert retained.status == "unknown"


@pytest.mark.parametrize("recorded", [False, True])
async def test_reconstructed_owner_and_unknown_are_absorbing_without_refund(
    factory: async_sessionmaker[AsyncSession], *, recorded: bool
) -> None:
    rig = await _seed(factory)
    claim = await _fresh(rig)
    with pytest.raises(DisclosureError, match="claim"):
        await rig.service.record(replace(claim))
    completion = await rig.service.record(claim) if recorded else None
    reconstructed, sink, _ = _service(factory, rig.fixture, rig.limits, cuts=CutAuthority())
    with pytest.raises(DisclosureError, match="claim"):
        await reconstructed.record(claim)
    unknown = await reconstructed.store.recover(claim.preparation.transmission_id)
    assert unknown.status == "unknown"
    assert await reconstructed.claim(claim.preparation) == unknown
    if completion is None:
        completion = await rig.service.record(claim)
        assert completion.outcome == "refused"
    assert await rig.service.settle(claim, completion) == unknown
    assert await reconstructed.store.recover(claim.preparation.transmission_id) == unknown
    assert rig.sink.records == ((rig.fixture.prepared.candidate,) if recorded else ())
    assert sink.records == ()
    await _assert_charged(factory, len(rig.fixture.prepared.candidate))


async def test_only_original_completion_identity_can_settle_retained_claim(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    rig = await _seed(factory)
    claim = await _fresh(rig)
    completion = await rig.service.record(claim)
    with pytest.raises(DisclosureError, match="claim"):
        await rig.service.settle(claim, replace(completion))
    with pytest.raises(DisclosureError, match="claim"):
        await rig.service.settle(replace(claim), completion)
    retained = await rig.service.store.read(claim.preparation.transmission_id)
    assert retained is not None
    assert retained.status == "claimed"
    assert (await rig.service.settle(claim, completion)).status == "recorded"
    assert rig.sink.records == (rig.fixture.prepared.candidate,)
    await _assert_charged(factory, len(rig.fixture.prepared.candidate))


@pytest.mark.parametrize("owner", ["run", "delivery"])
async def test_retained_disclosure_restricts_run_and_delivery_deletion(
    factory: async_sessionmaker[AsyncSession], owner: str
) -> None:
    rig = await _seed(factory)
    model = Run if owner == "run" else RunDelivery
    row_id = rig.fixture.run_binding.run_id if owner == "run" else rig.fixture.run_binding.delivery_id
    async with factory() as session:
        with pytest.raises(IntegrityError):
            await session.execute(delete(model).where(model.id == row_id))
        await session.rollback()
        assert await session.get(model, row_id) is not None
    assert await rig.service.store.read(rig.snapshot.preparation.transmission_id) == rig.snapshot
    await _assert_charged(factory, len(rig.fixture.prepared.candidate), uses=0)
