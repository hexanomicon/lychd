"""Opt-in actual PostgreSQL custody; no peer or network transport is simulated.

LYCHD_INTERCOM_TEST_DATABASE_URL must name an operator-owned disposable database.
Each test executes the complete migration lineage in its own schema, then drops only that
owned schema. No container, service, database or transport starts implicitly.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.runtime.migration import MigrationStep
from alembic.script import ScriptDirectory
from sqlalchemy import delete, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from lychd.config.constants import DB_MIGRATION_VERSION_TABLE, PATH_MIGRATION_DIR
from lychd.db.intercom import NETWORK_ALLOWANCE, IntercomStore, IntercomStoreError
from lychd.db.models.intercom import (
    IntercomCapacity,
    IntercomDeclaration,
    IntercomPeer,
    IntercomTask,
    IntercomTransmission,
)

pytestmark = [pytest.mark.integration, pytest.mark.container, pytest.mark.asyncio]
_PUBLIC_KEY = "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEArwaj4ykXFOTzVsGcmxXNGVHsbmZiqne+B1R/KJODNB0=\n-----END PUBLIC KEY-----\n"


@pytest.fixture(scope="module")
def pg_url() -> str:
    value = os.environ.get("LYCHD_INTERCOM_TEST_DATABASE_URL")
    if not value:
        pytest.skip("Set LYCHD_INTERCOM_TEST_DATABASE_URL to an explicit disposable PostgreSQL database.")
    return value


def _revision(connection: Connection, schema: str) -> None:
    scripts = ScriptDirectory(str(PATH_MIGRATION_DIR))

    def upgrades(heads: tuple[str, ...], context: MigrationContext) -> Iterator[MigrationStep]:
        assert not heads, "The owned fixture schema must start without migration history."
        for revision in reversed(list(scripts.walk_revisions(head="head"))):
            yield MigrationStep.upgrade_from_script(scripts.revision_map, revision)

    context = MigrationContext.configure(
        connection,
        opts={
            "version_table": DB_MIGRATION_VERSION_TABLE,
            "version_table_schema": schema,
            "fn": upgrades,
        },
    )
    with context.begin_transaction(), Operations.context(context):
        context.run_migrations()
        assert context.get_current_heads() == ("0017",)


@pytest_asyncio.fixture
async def factory(pg_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    schema = "intercom_proof_" + uuid4().hex
    engine = create_async_engine(
        pg_url,
        pool_size=5,
        max_overflow=0,
        connect_args={"server_settings": {"search_path": f"{schema},public", "application_name": schema}},
        execution_options={"schema_translate_map": {None: schema}},
    )
    created = False
    try:
        async with engine.connect() as connection:
            await connection.execute(CreateSchema(schema))
            await connection.commit()
            created = True
            await connection.run_sync(_revision, schema)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        try:
            if created:
                async with engine.begin() as connection:
                    await connection.execute(DropSchema(schema, cascade=True))
        finally:
            await engine.dispose()


@dataclass
class Rig:
    store: IntercomStore
    factory: async_sessionmaker[AsyncSession]
    peer_id: UUID
    task_id: UUID
    declaration_id: UUID


def limits(uses: int = 10) -> dict[str, Any]:
    return {
        scope: {"uses": uses, "application_bytes": 65536 * uses, "network_bytes": NETWORK_ALLOWANCE * uses}
        for scope in ("host", "purpose", "peer", "task")
    }


def claim(method: str = "SendMessage") -> dict[str, Any]:
    return {
        "method": method,
        "application_bytes": 256,
        "network_bytes": NETWORK_ALLOWANCE,
        "wire_digest": "a" * 64,
        "policy_generation": 1,
        "key_version": 1,
        "revocation_generation": 0,
        "request_nonce": uuid4().hex,
    }


def received(*, nonce: str | None = None, terminal: bool = False, result: str = "public-result") -> dict[str, Any]:
    return {
        "status": "received",
        "accepted_network_bytes": 128,
        "response_nonce": nonce or uuid4().hex,
        "foreign_task_id": "foreign-task",
        "context_id": "foreign-context",
        "foreign_status": "completed" if terminal else "working",
        "terminal": terminal,
        "result": {"text": result},
    }


async def seed(factory: async_sessionmaker[AsyncSession], *, peer_id: UUID | None = None) -> Rig:
    peer_id, task_id, declaration_id, operation_id = peer_id or uuid4(), uuid4(), uuid4(), uuid4()
    store = IntercomStore(factory)
    await store.enroll(
        peer_id,
        {
            "key": {
                "key_id": "fixture-key",
                "public_key_pem": _PUBLIC_KEY,
                "issuer": "fixture-enrollment",
                "protocol": "rfc9421-ed25519",
                "audience": "fixture-workload",
                "valid_from": "2026-01-01T00:00:00+00:00",
                "expires_at": "2030-01-01T00:00:00+00:00",
            },
            "policy": {"generation": 1},
            "task_schema": "fixture.public-text@1",
            "purpose": "public-task",
        },
    )
    await store.declare(
        declaration_id,
        {
            "peer_id": str(peer_id),
            "operation_id": str(operation_id),
            "policy_generation": 1,
            "subject": "synthetic-operator",
            "authentication_generation": str(uuid4()),
            "purpose": "public-task",
            "task_schema": "fixture.public-text@1",
            "text": "synthetic-public-text",
            "source_manifest": [{"source": "operator-authored", "classification": "public"}],
        },
    )
    await store.create_task(
        task_id,
        {
            "peer_id": str(peer_id),
            "declaration_id": str(declaration_id),
            "operation_id": str(operation_id),
            "purpose": "public-task",
            "task_schema": "fixture.public-text@1",
            "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            "body": '{"public":"text"}',
            "policy_generation": 1,
            "key_version": 1,
            "revocation_generation": 0,
        },
    )
    return Rig(store, factory, peer_id, task_id, declaration_id)


async def capacities(factory: async_sessionmaker[AsyncSession]) -> list[IntercomCapacity]:
    async with factory() as session:
        return list((await session.scalars(select(IntercomCapacity))).all())


async def test_concurrent_new_tasks_share_one_permanent_host_charge(factory: async_sessionmaker[AsyncSession]) -> None:
    first = await seed(factory)
    second = await seed(factory, peer_id=first.peer_id)
    outcomes = await asyncio.gather(
        *(rig.store.claim(rig.task_id, uuid4(), claim(), limits(1)) for rig in (first, second)), return_exceptions=True
    )
    assert sum(isinstance(value, dict) for value in outcomes) == 1
    assert sum(isinstance(value, IntercomStoreError) for value in outcomes) == 1
    rows = await capacities(factory)
    assert len(rows) == 4
    assert all(
        (row.uses_charged, row.application_charged, row.network_charged) == (1, 256, NETWORK_ALLOWANCE) for row in rows
    )


async def test_concurrent_submit_claims_have_exactly_one_winner(factory: async_sessionmaker[AsyncSession]) -> None:
    rig = await seed(factory)
    outcomes = await asyncio.gather(
        *(rig.store.claim(rig.task_id, uuid4(), claim(), limits()) for _ in range(2)), return_exceptions=True
    )
    assert sum(isinstance(value, dict) for value in outcomes) == 1
    assert sum(isinstance(value, IntercomStoreError) for value in outcomes) == 1
    assert all(row.uses_charged == 1 for row in await capacities(factory))
    async with factory() as session:
        assert len((await session.scalars(select(IntercomTransmission))).all()) == 1


class LostAcknowledgementSession(AsyncSession):
    async def commit(self) -> None:
        await super().commit()
        message = "Injected acknowledgement loss after actual PostgreSQL commit."
        raise RuntimeError(message)


async def test_actual_committed_lost_ack_restart_never_reissues_or_refunds(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    rig = await seed(factory)
    engine = cast("AsyncEngine", factory.kw["bind"])
    uncertain = IntercomStore(async_sessionmaker(engine, class_=LostAcknowledgementSession, expire_on_commit=False))
    attempt_id, record = uuid4(), claim()
    with pytest.raises(IntercomStoreError, match="commit-unknown"):
        await uncertain.claim(rig.task_id, attempt_id, record, limits())
    restarted = IntercomStore(factory)
    assert (await restarted.task(rig.task_id))["submit_claimed"] is True
    assert not hasattr(restarted, "activate")
    for identity, evidence in ((attempt_id, record), (uuid4(), claim())):
        with pytest.raises(IntercomStoreError, match="claimed"):
            await restarted.claim(rig.task_id, identity, evidence, limits())
    assert all((row.uses_charged, row.network_charged) == (1, NETWORK_ALLOWANCE) for row in await capacities(factory))


async def test_unknown_charge_survives_new_task_operation_and_policy_labels(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    rig = await seed(factory)
    attempt_id = uuid4()
    await rig.store.claim(rig.task_id, attempt_id, claim(), limits(1))
    await rig.store.settle(rig.task_id, attempt_id, {"status": "unknown", "accepted_network_bytes": 0})
    next_task = await seed(factory, peer_id=rig.peer_id)
    await rig.store.set_policy(rig.peer_id, {"generation": 2, "configuration_label": "new"}, expected_generation=1)
    with pytest.raises(IntercomStoreError, match="capacity"):
        await next_task.store.claim(next_task.task_id, uuid4(), {**claim(), "policy_generation": 2}, limits(1))
    assert all(row.uses_charged == 1 for row in await capacities(factory))


async def test_terminal_nonce_replay_and_local_cancel_remain_distinct(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    rig = await seed(factory)
    submit = uuid4()
    await rig.store.claim(rig.task_id, submit, claim(), limits())
    await rig.store.settle(rig.task_id, submit, received(nonce="submit-response"))
    poll = uuid4()
    await rig.store.claim(rig.task_id, poll, claim("GetTask"), limits())
    with pytest.raises(IntercomStoreError, match="replay"):
        await rig.store.settle(rig.task_id, poll, received(nonce="submit-response", terminal=True))
    later = uuid4()
    await rig.store.claim(rig.task_id, later, claim("GetTask"), limits())
    terminal = received(nonce="terminal-response", terminal=True, result="first")
    assert (await rig.store.settle(rig.task_id, poll, terminal))["result"] == {"text": "first"}
    assert (await rig.store.settle(rig.task_id, poll, terminal))["result"] == {"text": "first"}
    assert (await rig.store.settle(rig.task_id, later, received(terminal=True, result="late")))["result"] == {
        "text": "first"
    }
    other = await seed(factory, peer_id=rig.peer_id)
    other_attempt = uuid4()
    await other.store.claim(other.task_id, other_attempt, claim(), limits())
    with pytest.raises(IntercomStoreError, match="replay"):
        await other.store.settle(other.task_id, other_attempt, received(nonce="submit-response"))
    await other.store.settle(other.task_id, other_attempt, received())
    assert (await other.store.close_task(other.task_id, peer_id=rig.peer_id))["status"] == "cancelled"
    cancel = uuid4()
    await other.store.claim(other.task_id, cancel, claim("CancelTask"), limits())
    observation = await other.store.settle(other.task_id, cancel, received(terminal=True, result="late"))
    assert observation["status"] == "cancelled"
    assert observation["result"] is None
    assert observation["cancellation_observation"]["foreign_status"] == "completed"


async def test_current_callback_runs_after_real_waited_peer_lock_before_adoption(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    rig = await seed(factory)
    attempt = uuid4()
    await rig.store.claim(rig.task_id, attempt, claim(), limits())
    allowed = True
    called = False

    def current() -> None:
        nonlocal called
        called = True
        if not allowed:
            code = "policy"
            raise IntercomStoreError(code)

    async with factory() as blocker:
        await blocker.execute(select(IntercomPeer).where(IntercomPeer.id == rig.peer_id).with_for_update())
        pending = asyncio.create_task(rig.store.settle(rig.task_id, attempt, received(terminal=True), current=current))
        try:
            deadline = asyncio.get_running_loop().time() + 5
            while True:
                async with factory() as observer:
                    waiting = await observer.scalar(
                        text("""SELECT count(*) FROM pg_stat_activity
WHERE application_name=current_setting('application_name') AND wait_event_type='Lock'
AND query LIKE '%intercom_peer%' AND pid<>pg_backend_pid()""")
                    )
                if waiting:
                    break
                assert asyncio.get_running_loop().time() < deadline, "Expected actual PostgreSQL peer-lock waiter."
                await asyncio.sleep(0.01)
            assert not called
            allowed = False
            await blocker.rollback()
            with pytest.raises(IntercomStoreError, match="policy"):
                await pending
        finally:
            await blocker.rollback()
            if not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
    assert called
    assert (await rig.store.task(rig.task_id))["status"] == "submitting"
    async with factory() as session:
        transmission = await session.get(IntercomTransmission, attempt)
        assert transmission is not None
        assert transmission.settlement is None


@pytest.mark.parametrize("model", [IntercomPeer, IntercomTask, IntercomDeclaration])
async def test_retained_foreign_keys_restrict_history_deletion(
    factory: async_sessionmaker[AsyncSession], model: Any
) -> None:
    rig = await seed(factory)
    attempt = uuid4()
    await rig.store.claim(rig.task_id, attempt, claim(), limits())
    identity = {IntercomPeer: rig.peer_id, IntercomTask: rig.task_id, IntercomDeclaration: rig.declaration_id}[model]
    async with factory() as session:
        with pytest.raises(IntegrityError):
            await session.execute(delete(model).where(model.id == identity))
        await session.rollback()
    assert (await rig.store.task(rig.task_id))["task_id"] == str(rig.task_id)
