"""Migrated mechanical host custody; no owner, executor or physical receipt.

An explicitly disposable URL may be supplied by the qualification operator. Each
case owns a fresh schema; public bootstrap installs the normal migration extension.
No model, provider, runtime launcher or affirmative admission fixture is used.
"""

# pyright: reportPrivateUsage=false
from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from advanced_alchemy.alembic.commands import AlembicCommandConfig
from alembic import command, op
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from lychd.agents.router import Intent
from lychd.config.constants import DB_MIGRATION_VERSION_TABLE, PATH_MIGRATION_CONFIG
from lychd.db.delegated_host import DbDelegatedHostDispositionStore
from lychd.db.delegation import DbDelegatedAgentJobStore
from lychd.db.models import DelegatedAgentJobRecord, DelegatedHostDispositionRecord, Run
from lychd.domain.artifacts import ArtifactRef
from lychd.domain.cortex.ledger import DbRunLedger
from lychd.domain.delegation.host_disposition import (
    DelegatedHostDispositionSnapshot,
    DelegatedHostPolicyIdentity,
    FreshHostPreparation,
    HostDispositionCommitUnknownError,
    HostDispositionConflictError,
    HostDispositionNotEligibleError,
    HostIntakeClosedError,
    HostPreparationNotFreshError,
)
from lychd.domain.delegation.models import (
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedCliRequestV2,
    decode_delegated_request,
)
from tests.support.delegated_cli import cli_request

pytestmark = [pytest.mark.integration, pytest.mark.container]
_VERSION_TABLE = "lychd_host_disposition_test_version"


def _engine(url: str, schema: str | None = None, *, migration: bool = False) -> AsyncEngine:
    # DDL needs the public vector type; workers must never fall back to public tables
    # after a qualification-schema drop. A missing owned table must remain missing.
    search_path = f"{schema},public" if migration else schema
    return create_async_engine(
        url,
        poolclass=NullPool,
        connect_args={} if schema is None else {"server_settings": {"search_path": search_path}},
    )


def _config(url: str, schema: str | None = None) -> AlembicCommandConfig:
    return AlembicCommandConfig(
        engine=_engine(url, schema, migration=True),
        version_table_name=DB_MIGRATION_VERSION_TABLE if schema is None else _VERSION_TABLE,
        file_=PATH_MIGRATION_CONFIG,
        render_as_batch=False,
    )


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    """Use only an explicitly disposable qualification database or a fresh container."""
    configured = os.environ.get("LYCHD_DELEGATED_HOST_TEST_DATABASE_URL")
    if configured:
        command.upgrade(_config(configured), "head")
        yield configured
        return
    pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL qualification")
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer(
        "pgvector/pgvector:pg18-trixie", driver="asyncpg", mem_limit="512m", nano_cpus=1_000_000_000
    ) as postgres:
        url = postgres.get_connection_url()
        command.upgrade(_config(url), "head")
        yield url


@dataclass
class _Case:
    url: str
    schema: str
    engine: AsyncEngine
    factory: async_sessionmaker[AsyncSession]

    def config(self) -> AlembicCommandConfig:
        return _config(self.url, self.schema)


@pytest_asyncio.fixture
async def case(pg_url: str) -> AsyncIterator[_Case]:
    schema = "host_disposition_" + uuid4().hex
    admin = _engine(pg_url)
    try:
        async with admin.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await asyncio.to_thread(command.upgrade, _config(pg_url, schema), "head")
        engine = _engine(pg_url, schema)
        try:
            yield _Case(pg_url, schema, engine, async_sessionmaker(engine, expire_on_commit=False))
        finally:
            await engine.dispose()
    finally:
        # Only this randomly named qualification schema belongs to this fixture.
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await admin.dispose()


def _policy() -> DelegatedHostPolicyIdentity:
    return DelegatedHostPolicyIdentity(policy_id="unqualified-policy", revision="1", digest="sha256:" + "a" * 64)


async def _seed(case: _Case, *, artifact: bool = False) -> tuple[DelegatedCliRequestV2, DelegatedAgentJobRef]:
    run = await DbRunLedger(session_factory=case.factory).create(
        Intent(session_id="mechanical-host", prompt="mechanical custody only", source="bridge"),
        workflow_name="bridge_chat",
        queue_name="runs",
        priority=50,
    )
    request = cli_request(run_id=run.run_id, request_id=str(uuid4()))
    if artifact:
        request = request.model_copy(
            update={
                "input_artifacts": (
                    ArtifactRef(artifact_id="one", digest="sha256:" + "a" * 64, media_type="text/plain", size=1),
                )
            }
        )
    job = DelegatedAgentJobRef(
        job_id=str(uuid4()),
        request_id=request.request_id,
        run_id=request.run_id,
        runtime=request.runtime,
        profile=request.profile,
    )
    jobs = DbDelegatedAgentJobStore(case.factory)
    await jobs.create(request, job)
    await jobs.transition(job.job_id, DelegatedAgentJobStatus.ADMITTED)
    await jobs.transition(job.job_id, DelegatedAgentJobStatus.PREPARING)
    return request, job


async def _prepare(
    store: DbDelegatedHostDispositionStore, job: DelegatedAgentJobRef, *, generation: int = 0
) -> FreshHostPreparation | DelegatedHostDispositionSnapshot:
    return await store.prepare(
        job, policy=_policy(), executor_id="unqualified-executor", executor_generation=generation
    )


@pytest.mark.asyncio
async def test_exact_replay_once_identity_and_retained_original(case: _Case) -> None:
    _request, job = await _seed(case)
    store = DbDelegatedHostDispositionStore(case.factory)
    assert await store.get(job) is None
    contenders = [DbDelegatedHostDispositionStore(case.factory) for _ in range(2)]
    outcomes = await asyncio.gather(*(_prepare(candidate, job) for candidate in contenders))
    assert sum(isinstance(result, FreshHostPreparation) for result in outcomes) == 1
    winner = next(index for index, result in enumerate(outcomes) if isinstance(result, FreshHostPreparation))
    store = contenders[winner]
    fresh = outcomes[winner]
    assert isinstance(fresh, FreshHostPreparation)
    before = await store.get(job)
    assert isinstance(await _prepare(store, job), DelegatedHostDispositionSnapshot)
    assert isinstance(
        await _prepare(DbDelegatedHostDispositionStore(case.factory), job), DelegatedHostDispositionSnapshot
    )
    with pytest.raises(HostPreparationNotFreshError):
        await store.consume_dispatch(FreshHostPreparation(fresh.preparation))
    with pytest.raises(HostPreparationNotFreshError):
        await contenders[1 - winner].consume_dispatch(fresh)
    with pytest.raises(HostDispositionConflictError):
        await _prepare(store, job, generation=1)
    assert await store.get(job) == before
    consumed = await store.consume_dispatch(fresh)
    assert consumed.dispatch_id is not None
    with pytest.raises(HostPreparationNotFreshError):
        await store.consume_dispatch(fresh)
    assert (await store.get(job)) == consumed


@pytest.mark.asyncio
async def test_close_wins_against_delayed_fresh_dispatch(case: _Case) -> None:
    _request, job = await _seed(case)
    store = DbDelegatedHostDispositionStore(case.factory)
    fresh = await _prepare(store, job)
    assert isinstance(fresh, FreshHostPreparation)
    other = DbDelegatedHostDispositionStore(case.factory)
    closure = await other.close_intake(job)
    assert await other.close_intake(job) == closure
    with pytest.raises(HostIntakeClosedError):
        await store.consume_dispatch(fresh)
    with pytest.raises(HostPreparationNotFreshError):
        await store.consume_dispatch(fresh)
    retained = await other.get(job)
    assert retained is not None
    assert retained.dispatch_id is None
    assert retained.intake_closed_at == closure.closed_at
    parent = await DbDelegatedAgentJobStore(case.factory).get(job.job_id)
    assert parent is not None
    assert parent.status is DelegatedAgentJobStatus.PREPARING
    assert parent.result is None


class _LockWitness:
    """Real PostgreSQL lock barriers, never a replacement for database locking."""

    def __init__(self) -> None:
        self.acquired, self.resume, self.waiting = asyncio.Event(), asyncio.Event(), asyncio.Event()
        self.waiter_pid: int | None = None

    def sessions(self, *, holder: bool) -> type[AsyncSession]:
        witness = self

        class WitnessSession(AsyncSession):
            async def scalar(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
                parent_lock = "FROM delegated_agent_job" in str(statement) and "FOR UPDATE" in str(statement)
                if parent_lock and not holder:
                    witness.waiter_pid = cast("int", await super().scalar(select(func.pg_backend_pid())))
                    witness.waiting.set()
                result = await super().scalar(statement, *args, **kwargs)
                if parent_lock and holder:
                    witness.acquired.set()
                    await witness.resume.wait()
                return result

        return WitnessSession


async def _blocked(case: _Case, witness: _LockWitness) -> None:
    await asyncio.wait_for(witness.waiting.wait(), timeout=5)
    assert witness.waiter_pid is not None
    await _blocked_pid(case, witness.waiter_pid)


async def _blocked_pid(case: _Case, pid: int) -> None:
    async with asyncio.timeout(5), case.factory() as observer:
        while not await observer.scalar(select(func.cardinality(func.pg_blocking_pids(pid)))):  # noqa: ASYNC110 - observes a real database lock, not a local event
            await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_close_before_first_prepare_has_a_permanent_parent_anchor(case: _Case) -> None:
    _request, job = await _seed(case)
    witness = _LockWitness()
    closer = DbDelegatedHostDispositionStore(
        async_sessionmaker(case.engine, class_=witness.sessions(holder=True), expire_on_commit=False)
    )
    preparer = DbDelegatedHostDispositionStore(
        async_sessionmaker(case.engine, class_=witness.sessions(holder=False), expire_on_commit=False)
    )
    close = asyncio.create_task(closer.close_intake(job))
    prepare: asyncio.Task[FreshHostPreparation | DelegatedHostDispositionSnapshot] | None = None
    try:
        await asyncio.wait_for(witness.acquired.wait(), timeout=5)
        prepare = asyncio.create_task(_prepare(preparer, job))
        await _blocked(case, witness)
    finally:
        witness.resume.set()
    closure = await close
    assert prepare is not None
    with pytest.raises(HostIntakeClosedError):
        await prepare
    retained = await closer.get(job)
    assert retained is not None
    assert retained.preparation is None
    assert retained.dispatch_id is None
    assert retained.intake_closed_at == closure.closed_at


@pytest.mark.asyncio
async def test_consumption_then_close_retains_potentially_in_flight_truth(case: _Case) -> None:
    _request, job = await _seed(case)
    store = DbDelegatedHostDispositionStore(case.factory)
    fresh = await _prepare(store, job)
    assert isinstance(fresh, FreshHostPreparation)
    outcomes = await asyncio.gather(
        store.consume_dispatch(fresh), store.consume_dispatch(fresh), return_exceptions=True
    )
    consumed = next(result for result in outcomes if isinstance(result, DelegatedHostDispositionSnapshot))
    assert sum(isinstance(result, HostPreparationNotFreshError) for result in outcomes) == 1
    closure = await DbDelegatedHostDispositionStore(case.factory).close_intake(job)
    retained = await store.get(job)
    assert retained is not None
    assert retained.dispatch_id == consumed.dispatch_id
    assert retained.intake_closed_at == closure.closed_at


@pytest.mark.asyncio
@pytest.mark.parametrize("after_commit", [False, True], ids=["before-real-commit", "after-real-commit"])
async def test_uncertain_consumption_never_reissues_even_after_rollback(
    case: _Case, monkeypatch: pytest.MonkeyPatch, *, after_commit: bool
) -> None:
    _request, job = await _seed(case)
    store = DbDelegatedHostDispositionStore(case.factory)
    fresh = await _prepare(store, job)
    assert isinstance(fresh, FreshHostPreparation)

    class LostReplySession(AsyncSession):
        async def commit(self) -> None:
            if after_commit:
                await super().commit()
            msg = "injected commit acknowledgement loss"
            raise OSError(msg)

    monkeypatch.setattr(store, "_factory", async_sessionmaker(case.engine, class_=LostReplySession))
    with pytest.raises(HostDispositionCommitUnknownError, match="acknowledgement"):
        await store.consume_dispatch(fresh)
    with pytest.raises(HostPreparationNotFreshError):
        await store.consume_dispatch(fresh)
    replacement = DbDelegatedHostDispositionStore(case.factory)
    replay = await _prepare(replacement, job)
    assert isinstance(replay, DelegatedHostDispositionSnapshot)
    assert (replay.dispatch_id is not None) is after_commit
    assert await replacement.get(job) == replay


@pytest.mark.asyncio
@pytest.mark.parametrize("after_commit", [False, True])
async def test_uncertain_preparation_yields_no_handle(case: _Case, *, after_commit: bool) -> None:
    _request, job = await _seed(case)

    class LostReplySession(AsyncSession):
        async def commit(self) -> None:
            if after_commit:
                await super().commit()
            msg = "injected preparation acknowledgement loss"
            raise OSError(msg)

    store = DbDelegatedHostDispositionStore(async_sessionmaker(case.engine, class_=LostReplySession))
    with pytest.raises(HostDispositionCommitUnknownError):
        await _prepare(store, job)
    replacement = DbDelegatedHostDispositionStore(case.factory)
    snapshot = await replacement.get(job)
    assert (snapshot is not None) is after_commit
    if after_commit:
        assert isinstance(await _prepare(replacement, job), DelegatedHostDispositionSnapshot)


@pytest.mark.asyncio
async def test_cancellation_during_committed_dispatch_is_observable_and_retires_handle(
    case: _Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    _request, job = await _seed(case)
    store = DbDelegatedHostDispositionStore(case.factory)
    fresh = await _prepare(store, job)
    assert isinstance(fresh, FreshHostPreparation)
    committed, pending = asyncio.Event(), asyncio.Event()

    class PausedReplySession(AsyncSession):
        async def commit(self) -> None:
            await super().commit()
            committed.set()
            await pending.wait()

    monkeypatch.setattr(store, "_factory", async_sessionmaker(case.engine, class_=PausedReplySession))
    task = asyncio.create_task(store.consume_dispatch(fresh))
    await asyncio.wait_for(committed.wait(), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    with pytest.raises(HostPreparationNotFreshError):
        await store.consume_dispatch(fresh)
    replacement = DbDelegatedHostDispositionStore(case.factory)
    retained = await replacement.get(job)
    assert retained is not None
    assert retained.dispatch_id is not None
    assert isinstance(await _prepare(replacement, job), DelegatedHostDispositionSnapshot)


@pytest.mark.asyncio
async def test_cancelled_lock_wait_cannot_retry_its_unconsumed_preparation(
    case: _Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    _request, job = await _seed(case)
    store = DbDelegatedHostDispositionStore(case.factory)
    fresh = await _prepare(store, job)
    assert isinstance(fresh, FreshHostPreparation)
    witness = _LockWitness()
    monkeypatch.setattr(
        store,
        "_factory",
        async_sessionmaker(case.engine, class_=witness.sessions(holder=False), expire_on_commit=False),
    )
    async with case.factory() as holder, holder.begin():
        await holder.scalar(
            select(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.job_id == job.job_id).with_for_update()
        )
        pending = asyncio.create_task(store.consume_dispatch(fresh))
        try:
            await _blocked(case, witness)
        finally:
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
    with pytest.raises(HostPreparationNotFreshError):
        await store.consume_dispatch(fresh)
    engine = _engine(case.url, case.schema)
    try:
        replacement = DbDelegatedHostDispositionStore(async_sessionmaker(engine, expire_on_commit=False))
        replay = await _prepare(replacement, job)
        assert isinstance(replay, DelegatedHostDispositionSnapshot)
        assert replay.dispatch_id is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_fresh_preparation_requires_current_preparing_parent(case: _Case) -> None:
    _request, job = await _seed(case)
    async with case.factory() as session, session.begin():
        await session.execute(
            update(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.job_id == job.job_id).values(status="running")
        )
    store = DbDelegatedHostDispositionStore(case.factory)
    with pytest.raises(HostDispositionNotEligibleError):
        await _prepare(store, job)
    assert await store.get(job) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["state", "request", "scalar", "unknown", "corrupt_preparation"])
async def test_current_parent_and_retained_intent_rechecked_but_close_remains_available(
    case: _Case, change: str
) -> None:
    request, job = await _seed(case)
    store = DbDelegatedHostDispositionStore(case.factory)
    fresh = await _prepare(store, job)
    assert isinstance(fresh, FreshHostPreparation)
    close_job = job
    async with case.factory() as session, session.begin():
        if change == "state":
            await session.execute(
                update(DelegatedAgentJobRecord)
                .where(DelegatedAgentJobRecord.job_id == job.job_id)
                .values(status="running")
            )
        elif change == "scalar":
            await session.execute(
                update(DelegatedAgentJobRecord)
                .where(DelegatedAgentJobRecord.job_id == job.job_id)
                .values(request_id="changed-request-id")
            )
            close_job = job.model_copy(update={"request_id": "changed-request-id"})
        elif change == "corrupt_preparation":
            await session.execute(update(DelegatedHostDispositionRecord).values(preparation_bytes=b"{}"))
        else:
            raw = request.model_dump(mode="json")
            raw["prompt" if change == "request" else "request_schema"] = (
                "changed" if change == "request" else "unknown@99"
            )
            await session.execute(
                update(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.job_id == job.job_id).values(request=raw)
            )
    expected = HostDispositionNotEligibleError if change == "state" else HostDispositionConflictError
    with pytest.raises(expected):
        await store.consume_dispatch(fresh)
    await DbDelegatedHostDispositionStore(case.factory).close_intake(close_job)


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["float-limit", "bool-artifact", "valid-changed"])
async def test_current_numeric_aliases_and_valid_change_refuse_without_history_loss(case: _Case, change: str) -> None:
    request, job = await _seed(case, artifact=True)
    store = DbDelegatedHostDispositionStore(case.factory)
    fresh = await _prepare(store, job)
    assert isinstance(fresh, FreshHostPreparation)
    raw = request.model_dump(mode="json")
    if change == "float-limit":
        raw["cli_intent"]["limits"]["max_stdout_bytes"] = float(raw["cli_intent"]["limits"]["max_stdout_bytes"])
    elif change == "bool-artifact":
        raw["input_artifacts"][0]["size"] = True
    else:
        raw["prompt"] += " valid changed control"
    original = fresh.preparation.canonical_bytes()
    async with case.factory() as session, session.begin():
        await session.execute(
            update(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.job_id == job.job_id).values(request=raw)
        )
    with pytest.raises(HostDispositionConflictError):
        await store.get(job)
    with pytest.raises(HostDispositionConflictError):
        await store.consume_dispatch(fresh)
    with pytest.raises(HostPreparationNotFreshError):
        await store.consume_dispatch(fresh)
    await store.close_intake(job)
    async with case.factory() as session:
        row = await session.scalar(select(DelegatedHostDispositionRecord))
        assert row is not None
        assert row.preparation_bytes == original
        assert row.preparation_digest == fresh.preparation.digest
        assert row.dispatch_id is None
        assert row.intake_closed_at is not None


@pytest.mark.asyncio
async def test_new_preparation_refuses_default_omitted_current_shape_without_rewriting(case: _Case) -> None:
    request, job = await _seed(case, artifact=True)
    raw = request.model_dump(mode="json")
    del raw["input_artifacts"][0]["classification"]
    assert decode_delegated_request(raw) == request
    async with case.factory() as session, session.begin():
        await session.execute(
            update(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.job_id == job.job_id).values(request=raw)
        )
    store = DbDelegatedHostDispositionStore(case.factory)
    with pytest.raises(HostDispositionConflictError):
        await _prepare(store, job)
    assert await store.get(job) is None
    await store.close_intake(job)
    async with case.factory() as session:
        retained = await session.scalar(select(DelegatedAgentJobRecord.request))
        assert retained is not None
        assert "classification" not in retained["input_artifacts"][0]


@pytest.mark.asyncio
@pytest.mark.parametrize("values", [{}, {"preparation_bytes": b"{}"}, {"dispatch_id": uuid4()}])
async def test_database_rejects_partial_dispositions(case: _Case, values: dict[str, Any]) -> None:
    _request, job = await _seed(case)
    async with case.factory() as session:
        parent = await session.scalar(
            select(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.job_id == job.job_id)
        )
        assert parent is not None
        session.add(DelegatedHostDispositionRecord(job_record_id=parent.id, **values))
        with pytest.raises(IntegrityError, match="check constraint"):
            await session.flush()


@pytest.mark.asyncio
@pytest.mark.parametrize("disposition", ["closed-only", "prepared", "consumed"])
async def test_retained_history_blocks_deletion_and_downgrade(case: _Case, disposition: str) -> None:
    _request, job = await _seed(case)
    store = DbDelegatedHostDispositionStore(case.factory)
    if disposition == "closed-only":
        await store.close_intake(job)
    else:
        fresh = await _prepare(store, job)
        assert isinstance(fresh, FreshHostPreparation)
        if disposition == "consumed":
            await store.consume_dispatch(fresh)
    retained = await store.get(job)
    for statement in (
        delete(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.job_id == job.job_id),
        delete(Run).where(Run.id == UUID(job.run_id)),
    ):
        async with case.factory() as session:
            with pytest.raises(IntegrityError, match="foreign key constraint"):
                await session.execute(statement)
    with pytest.raises(DBAPIError, match="Retained delegated host disposition"):
        await asyncio.to_thread(command.downgrade, case.config(), "0014")
    assert await store.get(job) == retained
    async with case.factory() as session:
        assert await session.scalar(text("SELECT version_num FROM lychd_host_disposition_test_version")) == "0016"


@pytest.mark.asyncio
async def test_empty_schema_round_trip(case: _Case) -> None:
    await asyncio.to_thread(command.downgrade, case.config(), "0014")
    await asyncio.to_thread(command.upgrade, case.config(), "head")
    async with case.factory() as session:
        assert await session.scalar(select(func.count()).select_from(DelegatedHostDispositionRecord)) == 0
        rows = await session.execute(
            text(
                "SELECT column_name,is_nullable FROM information_schema.columns "
                "WHERE table_schema=:schema AND table_name='delegated_host_disposition'"
            ),
            {"schema": case.schema},
        )
        assert {str(row[0]): str(row[1]) for row in rows} == {
            column.name: "YES" if column.nullable else "NO"
            for column in DelegatedHostDispositionRecord.__table__.columns
        }


@pytest.mark.asyncio
async def test_locked_downgrade_does_not_erase_a_late_successful_writer(
    case: _Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    _request, job = await _seed(case)
    locked, resume = threading.Event(), threading.Event()
    original = op.execute

    def pause_after_lock(statement: Any, *args: Any, **kwargs: Any) -> Any:
        result = original(statement, *args, **kwargs)
        if str(statement) == "LOCK TABLE delegated_host_disposition IN ACCESS EXCLUSIVE MODE":
            locked.set()
            if not resume.wait(timeout=5):
                msg = "qualification downgrade barrier expired"
                raise RuntimeError(msg)
        return result

    witness = _LockWitness()
    store = DbDelegatedHostDispositionStore(
        async_sessionmaker(case.engine, class_=witness.sessions(holder=False), expire_on_commit=False)
    )
    monkeypatch.setattr(op, "execute", pause_after_lock)
    downgrade = asyncio.create_task(asyncio.to_thread(command.downgrade, case.config(), "0014"))
    writer: asyncio.Task[FreshHostPreparation | DelegatedHostDispositionSnapshot] | None = None
    try:
        assert await asyncio.to_thread(locked.wait, 5)
        writer = asyncio.create_task(_prepare(store, job))
        await _blocked(case, witness)
    finally:
        resume.set()
        downgrade_outcome = (await asyncio.gather(downgrade, return_exceptions=True))[0]
        writer_outcome = None if writer is None else (await asyncio.gather(writer, return_exceptions=True))[0]
    assert downgrade_outcome is None
    assert writer is not None
    assert isinstance(writer_outcome, DBAPIError)
    assert getattr(writer_outcome.orig, "sqlstate", None) == "42P01"
    await asyncio.to_thread(command.upgrade, case.config(), "head")
    assert await store.get(job) is None


@pytest.mark.asyncio
async def test_writer_parent_lock_precedes_downgrade_and_retains_committed_history(
    case: _Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    _request, job = await _seed(case)
    witness = _LockWitness()
    store = DbDelegatedHostDispositionStore(
        async_sessionmaker(case.engine, class_=witness.sessions(holder=True), expire_on_commit=False)
    )
    attempted = threading.Event()
    migration_pid: list[int] = []
    original = op.execute

    def observe_parent_lock(statement: Any, *args: Any, **kwargs: Any) -> Any:
        if str(statement) == "LOCK TABLE delegated_agent_job IN ACCESS EXCLUSIVE MODE":
            migration_pid.append(cast("int", op.get_bind().scalar(text("SELECT pg_backend_pid()"))))
            attempted.set()
        return original(statement, *args, **kwargs)

    monkeypatch.setattr(op, "execute", observe_parent_lock)
    writer = asyncio.create_task(_prepare(store, job))
    downgrade: asyncio.Task[None] | None = None
    try:
        await asyncio.wait_for(witness.acquired.wait(), timeout=5)
        downgrade = asyncio.create_task(asyncio.to_thread(command.downgrade, case.config(), "0014"))
        assert await asyncio.to_thread(attempted.wait, 5)
        await _blocked_pid(case, migration_pid[0])
    finally:
        witness.resume.set()
        writer_outcome = (await asyncio.gather(writer, return_exceptions=True))[0]
        downgrade_outcome = None if downgrade is None else (await asyncio.gather(downgrade, return_exceptions=True))[0]
    assert isinstance(writer_outcome, FreshHostPreparation)
    assert downgrade is not None
    assert isinstance(downgrade_outcome, DBAPIError)
    assert getattr(downgrade_outcome.orig, "sqlstate", None) == "P0001"
    assert "Retained delegated host disposition" in str(downgrade_outcome)
    retained = await store.get(job)
    assert retained is not None
    assert retained.preparation == writer_outcome.preparation
    async with case.factory() as session:
        assert await session.scalar(text("SELECT version_num FROM lychd_host_disposition_test_version")) == "0016"
