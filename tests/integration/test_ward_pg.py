"""Opt-in real PostgreSQL Ward controls. Construction does not run this profile."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Iterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import psycopg
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from psycopg.sql import SQL, Identifier
from sqlalchemy import Table, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from lychd.config.constants import PATH_MIGRATION_CONFIG
from lychd.config.settings.root import Settings
from lychd.db.authority import RUNTIME_AUTHORITY_QUERY
from lychd.db.bootstrap import bootstrap_database
from lychd.db.factory import create_db_engine, database_saq_dsn, database_url
from lychd.db.models.ward import WardAudit, WardCredential, WardPermission, WardPrincipal, WardSession, WardUser
from lychd.db.ward import DbWardStore
from lychd.domain.ward.service import (
    AUDIENCE,
    Action,
    Authentication,
    Operation,
    PrincipalKind,
    Secret,
    WardRefusedError,
    WardService,
)
from tests.integration import test_archive_migrations_pg as migration
from tests.integration import test_database_authority_pg as authority

pytestmark = [pytest.mark.integration, pytest.mark.container]
database = authority.database
ISSUER = uuid4()
TABLES = cast(
    "list[Table]",
    [
        model.__table__
        for model in (
            WardPrincipal,
            WardUser,
            WardCredential,
            WardSession,
            WardPermission,
            WardAudit,
        )
    ],
)


def _migration_head() -> str:
    """Resolve the authoritative head while refusing divergent migration branches."""
    heads = ScriptDirectory.from_config(Config(PATH_MIGRATION_CONFIG)).get_heads()
    assert len(heads) == 1, f"Expected one migration head, found {heads!r}"
    return heads[0]


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


@pytest_asyncio.fixture
async def factory(pg_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(pg_url)
    async with engine.begin() as connection:
        await connection.run_sync(WardPrincipal.metadata.drop_all, tables=TABLES)
        await connection.run_sync(WardPrincipal.metadata.create_all, tables=TABLES)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def ward(factory: async_sessionmaker[AsyncSession], *, issuer: UUID = ISSUER) -> WardService:
    return WardService(DbWardStore(factory, issuer_id=issuer))


def future() -> datetime:
    return datetime.now(UTC) + timedelta(hours=1)


async def prepared() -> str:
    return "candidate-projection"


async def publish(service: WardService, authentication: Authentication, operation: Operation) -> list[str]:
    disclosed: list[str] = []
    await service.publish(
        authentication.secret,
        operation,
        prepare=prepared,
        publication=lambda value, _context: disclosed.append(value),
        expected_policy_generation=2,
    )
    return disclosed


@pytest.mark.asyncio
async def test_default_deny_exact_principal_object_action_and_purpose(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    service = ward(factory)
    alice = await service.enroll(PrincipalKind.HUMAN, expires_at=future())
    bob = await service.enroll(PrincipalKind.SERVICE, expires_at=future())
    assert alice.user_id is not None
    assert bob.user_id is None
    alice_session = await service.open_session(alice.credential, expires_at=future() - timedelta(minutes=1))
    bob_session = await service.open_session(bob.credential, expires_at=future() - timedelta(minutes=1))
    operation = Operation(Action.READ, uuid4(), "review-candidate")
    with pytest.raises(WardRefusedError):
        await publish(service, alice_session, operation)
    await service.assign(alice.principal_id, operation, expires_at=future())
    assert await publish(service, alice_session, operation) == ["candidate-projection"]
    for authentication, query in (
        (bob_session, operation),
        (alice_session, Operation(Action.READ, uuid4(), operation.purpose)),
        (alice_session, Operation(Action.DECIDE, operation.object_id, operation.purpose)),
        (alice_session, Operation(Action.READ, operation.object_id, "other-purpose")),
    ):
        with pytest.raises(WardRefusedError):
            await publish(service, authentication, query)
    with pytest.raises(WardRefusedError):
        await service.revoke(bob.principal_id, session_id=alice_session.session_id)
    assert await publish(service, alice_session, operation)


@pytest.mark.asyncio
async def test_exchange_is_once_under_concurrency_and_auth_refusals(factory: async_sessionmaker[AsyncSession]) -> None:
    service = ward(factory)
    enrolled = await service.enroll(PrincipalKind.HUMAN, expires_at=future())
    with pytest.raises(WardRefusedError):
        await service.open_session(enrolled.credential, audience="foreign", expires_at=future())
    with pytest.raises(WardRefusedError):
        await ward(factory, issuer=uuid4()).open_session(enrolled.credential, expires_at=future())
    with pytest.raises(WardRefusedError):
        await service.open_session(Secret.generate(), expires_at=future())
    outcomes = await asyncio.gather(
        service.open_session(enrolled.credential, expires_at=future() - timedelta(minutes=1)),
        service.open_session(enrolled.credential, expires_at=future() - timedelta(minutes=1)),
        return_exceptions=True,
    )
    assert sum(isinstance(result, Authentication) for result in outcomes) == 1
    assert sum(isinstance(result, WardRefusedError) for result in outcomes) == 1
    async with factory() as session, session.begin():
        row = await session.scalar(select(WardCredential).where(WardCredential.id == enrolled.credential_id))
        assert row is not None
        assert row.exchanged_at is not None
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(WardRefusedError):
        await service.open_session(enrolled.credential, expires_at=future())


@pytest.mark.asyncio
async def test_revocation_during_preparation_and_restart_remains_denied(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    service = ward(factory)
    enrolled = await service.enroll(PrincipalKind.HUMAN, expires_at=future())
    authentication = await service.open_session(enrolled.credential, expires_at=future() - timedelta(minutes=1))
    operation = Operation(Action.READ, uuid4(), "review-candidate")
    await service.assign(enrolled.principal_id, operation, expires_at=future())
    ready, release = asyncio.Event(), asyncio.Event()
    disclosed: list[str] = []

    async def delayed() -> str:
        ready.set()
        await release.wait()
        return "candidate-projection"

    pending = asyncio.create_task(
        service.publish(
            authentication.secret,
            operation,
            prepare=delayed,
            publication=lambda value, _context: disclosed.append(value),
            expected_policy_generation=2,
        )
    )
    await ready.wait()
    await asyncio.gather(
        service.revoke(enrolled.principal_id, session_id=authentication.session_id),
        service.revoke(enrolled.principal_id, session_id=authentication.session_id),
    )
    release.set()
    with pytest.raises(WardRefusedError):
        await pending
    assert not disclosed
    with pytest.raises(WardRefusedError):
        await publish(ward(factory), authentication, operation)
    async with factory() as session:
        row = await session.get(WardSession, authentication.session_id)
        assert row is not None
        assert row.generation == 2
        audits = list(await session.scalars(select(WardAudit)))
        assert any(audit.event == "publication-attempt" and audit.outcome == "refused" for audit in audits)
        stored_audits = (await session.execute(select(WardAudit.__table__))).mappings().all()
        audit_text = repr([dict(row) for row in stored_audits])
        assert enrolled.credential.value not in audit_text
        assert authentication.secret.value not in audit_text
        credential = await session.get(WardCredential, enrolled.credential_id)
        assert credential is not None
        assert credential.secret_digest == enrolled.credential.digest()


@pytest.mark.asyncio
async def test_policy_change_and_terminal_principal_revocation_fence_pending_work(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    service = ward(factory)
    enrolled = await service.enroll(PrincipalKind.NODE, expires_at=future())
    authentication = await service.open_session(enrolled.credential, expires_at=future() - timedelta(minutes=1))
    operation = Operation(Action.DECIDE, uuid4(), "adoption-judgment")
    generation = await service.assign(enrolled.principal_id, operation, expires_at=future())
    await service.assign(enrolled.principal_id, operation, expires_at=future(), allowed=False)
    await service.assign(enrolled.principal_id, operation, expires_at=future())
    disclosed: list[str] = []
    with pytest.raises(WardRefusedError):
        await service.publish(
            authentication.secret,
            operation,
            prepare=prepared,
            publication=lambda value, _context: disclosed.append(value),
            expected_policy_generation=generation,
        )
    outcomes = await asyncio.gather(
        service.revoke(enrolled.principal_id),
        service.assign(enrolled.principal_id, operation, expires_at=future()),
        return_exceptions=True,
    )
    assert outcomes[0] is None
    assert isinstance(outcomes[1], (int, WardRefusedError))
    with pytest.raises(WardRefusedError):
        await publish(ward(factory), authentication, operation)
    assert not disclosed


@pytest.mark.asyncio
@pytest.mark.parametrize("expiry", ["credential", "session", "permission"])
async def test_each_expiry_prevents_disclosure(factory: async_sessionmaker[AsyncSession], expiry: str) -> None:
    service = ward(factory)
    enrolled = await service.enroll(PrincipalKind.PEER, expires_at=future())
    authentication = await service.open_session(enrolled.credential, expires_at=future() - timedelta(minutes=1))
    operation = Operation(Action.INSPECT, uuid4(), "review-candidate")
    await service.assign(enrolled.principal_id, operation, expires_at=future())
    async with factory() as session, session.begin():
        if expiry == "credential":
            row = await session.get(WardCredential, enrolled.credential_id)
        elif expiry == "session":
            row = await session.get(WardSession, authentication.session_id)
        else:
            row = await session.scalar(
                select(WardPermission).where(WardPermission.principal_id == enrolled.principal_id)
            )
        assert row is not None
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(WardRefusedError):
        await publish(service, authentication, operation)


@pytest.mark.asyncio
async def test_schema_enforces_human_user_and_session_principal_binding(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    from sqlalchemy.exc import IntegrityError

    service = ward(factory)
    alice = await service.enroll(PrincipalKind.HUMAN, expires_at=future())
    robot = await service.enroll(PrincipalKind.SERVICE, expires_at=future())
    with pytest.raises(IntegrityError):
        async with factory() as session, session.begin():
            session.add(WardUser(principal_id=robot.principal_id))
    with pytest.raises(IntegrityError):
        async with factory() as session, session.begin():
            session.add(
                WardSession(
                    principal_id=robot.principal_id,
                    credential_id=alice.credential_id,
                    secret_digest=Secret.generate().digest(),
                    audience=AUDIENCE,
                    generation=1,
                    principal_generation=1,
                    credential_generation=1,
                    expires_at=future(),
                )
            )


def _ward_migration_state(url: str, version: str, *, present: bool) -> None:
    assert migration.run(url, "SELECT version_num FROM lychd_db_version") == [(version,)]
    names = {
        row[0]
        for row in migration.run(url, "SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    }
    expected = {table.name for table in TABLES}
    if present:
        assert expected <= names
    else:
        assert expected.isdisjoint(names)
    assert migration.run(url, "SELECT value FROM security_receipt_probe WHERE id=1") == [("preserved",)]


def _ward_row_counts(dsn: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    with psycopg.connect(dsn) as connection:
        for table in TABLES:
            row = connection.execute(SQL("SELECT count(*) FROM {}").format(Identifier("public", table.name))).fetchone()
            assert row is not None
            counts[table.name] = int(row[0])
    return counts


def _ward_runtime_roundtrip(database: Settings) -> UUID:
    async def exercise() -> UUID:
        engine = create_db_engine(database.server.database, runtime=True)
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)
            service = ward(factory)
            enrolled = await service.enroll(PrincipalKind.HUMAN, expires_at=future())
            authentication = await service.open_session(enrolled.credential, expires_at=future() - timedelta(minutes=1))
            operation = Operation(Action.READ, uuid4(), "review-candidate")
            generation = await service.assign(enrolled.principal_id, operation, expires_at=future())
            disclosed: list[str] = []
            await service.publish(
                authentication.secret,
                operation,
                prepare=prepared,
                publication=lambda value, _context: disclosed.append(value),
                expected_policy_generation=generation,
            )
            assert disclosed == ["candidate-projection"]
            await service.revoke(enrolled.principal_id, session_id=authentication.session_id)
            with pytest.raises(WardRefusedError):
                await publish(ward(factory), authentication, operation)
            return enrolled.principal_id
        finally:
            await engine.dispose()

    return asyncio.run(exercise())


def test_fullchain_0019_0020_cycle_runtime_roles_and_retained_refusal(database: Settings) -> None:
    """Use real bootstrap/HBA and Alembic environment, never direct module operations."""
    scripts = ScriptDirectory.from_config(Config(str(PATH_MIGRATION_CONFIG)))
    revision = scripts.get_revision("0020")
    assert revision is not None
    assert revision.down_revision == "0019"
    head = _migration_head()
    db = database.server.database
    admin_url = database_url(db)
    runtime_url = database_url(db, runtime=True)
    admin_dsn = database_saq_dsn(db)
    runtime_dsn = database_saq_dsn(db, runtime=True)
    # The reused fixture ran the real empty full-chain bootstrap first. Establish
    # the exact pre-Ward baseline through its migration owner before this cycle.
    _ward_migration_state(admin_url, head, present=True)
    command.downgrade(migration.config(admin_url), "0019")
    _ward_migration_state(admin_url, "0019", present=False)
    command.upgrade(migration.config(admin_url), "0020")
    _ward_migration_state(admin_url, "0020", present=True)
    for table in TABLES:
        columns = migration.run(
            admin_url,
            "SELECT column_name,is_nullable FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=:table",
            {"table": table.name},
        )
        assert dict(columns) == {column.name: "YES" if column.nullable else "NO" for column in table.columns}
    command.downgrade(migration.config(admin_url), "0019")
    _ward_migration_state(admin_url, "0019", present=False)
    command.upgrade(migration.config(admin_url), "0020")
    _ward_migration_state(admin_url, "0020", present=True)
    # Recreated tables have no old ACLs: only the explicit bootstrap grant admits DML.
    with (
        psycopg.connect(runtime_dsn, autocommit=True) as connection,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
    ):
        connection.execute("SELECT id FROM public.ward_principal LIMIT 0")
    bootstrap_database(database)
    with psycopg.connect(runtime_dsn) as connection:
        assert connection.execute(RUNTIME_AUTHORITY_QUERY).fetchone() == (False,)
        for table in TABLES:
            assert connection.execute(
                "SELECT has_table_privilege(current_user,%s,'SELECT'), "
                "has_table_privilege(current_user,%s,'INSERT'), "
                "has_table_privilege(current_user,%s,'UPDATE'), "
                "has_table_privilege(current_user,%s,'DELETE')",
                (table.name,) * 4,
            ).fetchone() == (True, True, True, True)
    for statement in (
        "ALTER TABLE public.ward_principal ADD COLUMN forbidden integer",
        "DROP TABLE public.ward_audit",
        "CREATE TABLE public.ward_forbidden(id integer)",
        "CREATE ROLE ward_forbidden SUPERUSER",
        "UPDATE public.lychd_db_version SET version_num='forbidden'",
        "UPDATE public.saq_versions SET version=0",
    ):
        with (
            psycopg.connect(runtime_dsn, autocommit=True) as connection,
            pytest.raises(psycopg.errors.InsufficientPrivilege),
        ):
            connection.execute(statement)
    # Empty guard passes, so an actual runtime migration must fail on schema ownership.
    with pytest.raises(DBAPIError) as denied:
        command.downgrade(migration.config(runtime_url), "0019")
    assert getattr(denied.value.orig, "sqlstate", None) == "42501"
    _ward_migration_state(admin_url, head, present=True)
    assert _ward_row_counts(admin_dsn) == {table.name: 0 for table in TABLES}
    principal_id = _ward_runtime_roundtrip(database)
    retained = _ward_row_counts(admin_dsn)
    assert all(count > 0 for count in retained.values())
    with pytest.raises(DBAPIError, match="Retained Ward identity or audit prevents downgrade") as retained_error:
        command.downgrade(migration.config(admin_url), "0019")
    assert getattr(retained_error.value.orig, "sqlstate", None) == "P0001"
    _ward_migration_state(admin_url, head, present=True)
    assert _ward_row_counts(admin_dsn) == retained
    assert migration.run(admin_url, "SELECT id FROM public.ward_principal WHERE id=:id", {"id": principal_id}) == [
        (principal_id,)
    ]


@pytest.mark.asyncio
async def test_credential_revocation_invalidates_existing_authentication(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    service = ward(factory)
    enrolled = await service.enroll(PrincipalKind.HUMAN, expires_at=future())
    authentication = await service.open_session(enrolled.credential, expires_at=future() - timedelta(minutes=1))
    operation = Operation(Action.READ, uuid4(), "review-candidate")
    await service.assign(enrolled.principal_id, operation, expires_at=future())
    await service.revoke(enrolled.principal_id, credential_id=enrolled.credential_id)
    with pytest.raises(WardRefusedError):
        await publish(ward(factory), authentication, operation)
    with pytest.raises(WardRefusedError):
        await service.open_session(enrolled.credential, expires_at=future() - timedelta(minutes=1))


def _fault_handoff(failure: str, error: RuntimeError, disclosed: list[str], value: str) -> None:
    if failure != "before-handoff":
        disclosed.append(value)
    if failure in {"before-handoff", "after-handoff"}:
        raise error


async def _change_after_attempt(
    service: WardService, principal_id: UUID, session_id: UUID, operation: Operation, failure: str
) -> None:
    if failure == "revocation":
        await service.revoke(principal_id, session_id=session_id)
    elif failure == "regrant":
        await service.assign(principal_id, operation, expires_at=future(), allowed=False)
        await service.assign(principal_id, operation, expires_at=future())


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["before-handoff", "after-handoff", "commit-ack", "revocation", "regrant"])
async def test_retained_publication_attempt_faults_and_current_recheck(
    factory: async_sessionmaker[AsyncSession],
    failure: str,
) -> None:
    service = ward(factory)
    enrolled = await service.enroll(PrincipalKind.HUMAN, expires_at=future())
    authentication = await service.open_session(enrolled.credential, expires_at=future() - timedelta(minutes=1))
    operation = Operation(Action.READ, uuid4(), "review-candidate")
    generation = await service.assign(enrolled.principal_id, operation, expires_at=future())
    original = RuntimeError("publication acknowledgement unavailable")
    transactions = 0

    @asynccontextmanager
    async def controlled_factory() -> AsyncGenerator[Any]:
        async with factory() as underlying:

            @asynccontextmanager
            async def transaction() -> AsyncGenerator[None]:
                nonlocal transactions
                async with underlying.begin():
                    yield
                transactions += 1
                if transactions == 1:
                    await _change_after_attempt(
                        service, enrolled.principal_id, authentication.session_id, operation, failure
                    )
                elif failure == "commit-ack":
                    raise original

            class Proxy:
                def begin(self) -> AbstractAsyncContextManager[None]:
                    return transaction()

                def __getattr__(self, name: str) -> Any:
                    return getattr(underlying, name)

            yield Proxy()

    store = DbWardStore(cast("async_sessionmaker[AsyncSession]", controlled_factory), issuer_id=ISSUER)
    disclosed: list[str] = []

    expected_error = WardRefusedError if failure in {"revocation", "regrant"} else RuntimeError
    with pytest.raises(expected_error) as raised:
        await store.publish(
            authentication.secret,
            operation,
            "projection",
            lambda value, _context: _fault_handoff(failure, original, disclosed, value),
            expected_policy_generation=generation,
        )
    if expected_error is RuntimeError:
        assert raised.value is original
    # Reopen through a fresh adapter/session; the retained attempt cannot restore authority.
    async with factory() as session:
        attempt = await session.scalar(select(WardAudit).where(WardAudit.event == "publication-attempt"))
        assert attempt is not None
        assert attempt.outcome == ("refused" if failure in {"revocation", "regrant"} else "unknown")
        assert attempt.expected_policy_generation == generation
        assert attempt.principal_id == enrolled.principal_id
        assert str(attempt.id) in " ".join(raised.value.__notes__)
    assert disclosed == (["projection"] if failure in {"after-handoff", "commit-ack"} else [])
    await service.revoke(enrolled.principal_id)
    with pytest.raises(WardRefusedError):
        await publish(ward(factory), authentication, operation)


@pytest.mark.asyncio
@pytest.mark.parametrize("isolation", ["REPEATABLE READ", "SERIALIZABLE", "AUTOCOMMIT"])
async def test_nondefault_isolation_refuses_and_preserves_caller_configuration(
    factory: async_sessionmaker[AsyncSession],
    pg_url: str,
    isolation: str,
) -> None:
    service = ward(factory)
    enrolled = await service.enroll(PrincipalKind.HUMAN, expires_at=future())
    authentication = await service.open_session(enrolled.credential, expires_at=future() - timedelta(minutes=1))
    operation = Operation(Action.READ, uuid4(), "review-candidate")
    await service.assign(enrolled.principal_id, operation, expires_at=future())
    engine = create_async_engine(pg_url, isolation_level=isolation)
    try:
        configured = async_sessionmaker(engine, expire_on_commit=False)
        with pytest.raises(WardRefusedError, match="actual READ COMMITTED"):
            await publish(ward(configured), authentication, operation)
        async with configured() as session:
            assert await session.scalar(text("SHOW transaction_isolation")) == (
                "read committed" if isolation == "AUTOCOMMIT" else isolation.lower()
            )
            assert await session.scalar(select(WardAudit).where(WardAudit.event == "publication-attempt")) is None
    finally:
        await engine.dispose()
