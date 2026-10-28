"""Offline refusal/order/query controls; these do not establish PostgreSQL durability."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, Self, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lychd.db.models.ward import WardAudit, WardCredential, WardPermission, WardPrincipal, WardSession
from lychd.db.ward import PROTOCOL, DbWardStore
from lychd.domain.ward.service import AUDIENCE, Action, Attribution, Operation, Secret, WardRefusedError, WardService

NOW = datetime(2026, 10, 20, tzinfo=UTC)
ENGINE = create_async_engine("postgresql+asyncpg://")  # no connection or network operation


class TransactionDouble:
    def __init__(self, owner: SessionDouble) -> None:
        self.owner = owner
        self.before = list(owner.records)
        self.states = [(row, row.outcome, row.permitted) for row in owner.records]

    async def __aenter__(self) -> Self:
        self.owner.transactions += 1
        return self

    async def __aexit__(self, error_type: object, *args: object) -> None:
        owner = self.owner
        if error_type is not None or (owner.transactions == owner.fail_at and not owner.ack_lost):
            owner.records[:] = self.before
            for row, outcome, permitted in self.states:
                row.outcome, row.permitted = outcome, permitted
        else:
            owner.durable = list(owner.records)
            if owner.after_commit is not None:
                owner.after_commit()
        if error_type is not None and owner.cleanup_failure is not None:
            raise owner.cleanup_failure
        if error_type is None and owner.transactions == owner.fail_at:
            raise owner.failure


class SessionDouble:
    def __init__(self, values: list[Any]) -> None:
        self.values = iter(values)
        self.statements: list[Any] = []
        self.records: list[Any] = []
        self.durable: list[Any] = []
        self.bind = ENGINE
        self.autocommit = False
        self.transactional = True
        self.routed = False
        self.isolation: object = "read committed"
        self.transactions = 0
        self.fail_at = 0
        self.ack_lost = False
        self.failure = RuntimeError("commit acknowledgement lost")
        self.cleanup_failure: RuntimeError | None = None
        self.after_commit: Callable[[], None] | None = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    def begin(self) -> TransactionDouble:
        return TransactionDouble(self)

    async def execute(self, statement: object) -> None:
        self.statements.append(statement)
        if getattr(statement, "is_update", False):
            parameters = cast("Any", statement).compile().params
            for row in self.records:
                if row.id == parameters["id_1"]:
                    row.outcome, row.permitted = parameters["outcome"], parameters["permitted"]

    def get_bind(self, *, mapper: object) -> object:
        del mapper
        return object() if self.routed else self.bind.sync_engine

    async def connection(self) -> Any:
        pooled = SimpleNamespace(
            dbapi_connection=SimpleNamespace(autocommit=self.autocommit),
            driver_connection=SimpleNamespace(is_in_transaction=lambda: self.transactional),
        )
        return SimpleNamespace(sync_connection=SimpleNamespace(connection=pooled))

    async def scalar(self, statement: object) -> Any:
        self.statements.append(statement)
        if str(statement) == "SHOW transaction_isolation":
            return self.isolation
        return next(self.values)

    def add(self, row: Any) -> None:
        self.records.append(row)

    async def flush(self) -> None:
        pass

    @property
    def audits(self) -> list[WardAudit]:
        return [row for row in self.records if isinstance(row, WardAudit)]


def fixture_rows() -> tuple[UUID, WardPrincipal, WardSession, WardCredential, WardPermission, datetime]:
    principal_id, credential_id = uuid4(), uuid4()
    principal = WardPrincipal(id=principal_id, generation=1, policy_generation=2, kind="human", revoked_at=None)
    authentication = WardSession(
        id=uuid4(),
        principal_id=principal_id,
        credential_id=credential_id,
        generation=1,
        principal_generation=1,
        credential_generation=1,
        audience=AUDIENCE,
        expires_at=NOW + timedelta(hours=1),
        revoked_at=None,
    )
    credential = WardCredential(
        id=credential_id,
        principal_id=principal_id,
        issuer_id=ISSUER,
        protocol=PROTOCOL,
        audience=AUDIENCE,
        generation=1,
        expires_at=NOW + timedelta(hours=2),
        revoked_at=None,
        exchanged_at=None,
    )
    permission = WardPermission(expires_at=NOW + timedelta(hours=1))
    return principal_id, principal, authentication, credential, permission, NOW


ISSUER = uuid4()
OPERATION = Operation(Action.READ, uuid4(), "inspect-candidate")


def adapter(session: SessionDouble) -> DbWardStore:
    factory = cast("async_sessionmaker[AsyncSession]", lambda: session)
    return DbWardStore(factory, issuer_id=ISSUER)


def test_secret_shape_digest_and_repr_are_closed() -> None:
    first, second = Secret.generate(), Secret.generate()
    assert first != second
    assert len(first.value) == 43
    assert len(first.digest()) == 64
    assert first.value not in repr(first)
    assert first.value not in str(first)
    with pytest.raises(ValueError, match="invalid shape"):
        Secret("caller-claimed-principal")
    with pytest.raises(ValueError, match="outside"):
        Operation(Action.READ, uuid4(), "inspect", audience="remote")
    with pytest.raises(ValueError, match="outside"):
        Operation(Action.READ, uuid4(), "*")


@pytest.mark.asyncio
async def test_publication_uses_exact_query_and_no_reusable_grant() -> None:
    session = SessionDouble(list(fixture_rows()) * 2)
    received: list[Attribution] = []
    result = await adapter(session).publish(
        Secret.generate(),
        OPERATION,
        "projection",
        lambda _value, context: received.append(context),
        expected_policy_generation=2,
    )
    assert result is None
    assert len(received) == 1
    assert received[0].publication_attempt_id == session.durable[0].id
    lock_sql = str(session.statements[4].compile(dialect=postgresql.dialect()))
    policy_sql = str(session.statements[-2].compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in lock_sql
    for field in ("principal_id", "action", "object_id", "audience", "purpose", "allowed"):
        assert f"ward_permission.{field}" in policy_sql
    assert session.audits[0].permitted
    assert session.audits[0].object_id == OPERATION.object_id
    assert session.audits[0].purpose == OPERATION.purpose


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "refusal", ["principal", "credential", "session", "expiry", "audience", "issuer", "policy", "assignment"]
)
async def test_current_refusal_prevents_publication_and_audits(refusal: str) -> None:
    rows: list[Any] = list(fixture_rows())
    principal, authentication, credential = rows[1:4]
    if refusal == "principal":
        principal.revoked_at = NOW
    elif refusal == "credential":
        credential.generation = 2
    elif refusal == "session":
        authentication.revoked_at = NOW
    elif refusal == "expiry":
        authentication.expires_at = NOW
    elif refusal == "audience":
        authentication.audience = "other"
    elif refusal == "issuer":
        credential.issuer_id = uuid4()
    elif refusal == "policy":
        principal.policy_generation = 3
    else:
        rows[4] = None
    session = SessionDouble(rows)
    called: list[object] = []
    with pytest.raises(WardRefusedError):
        await adapter(session).publish(
            Secret.generate(),
            OPERATION,
            "projection",
            lambda value, _context: called.append(value),
            expected_policy_generation=2,
        )
    assert not called
    assert not session.audits[0].permitted


@pytest.mark.asyncio
async def test_revocation_during_awaited_preparation_is_resolved_afterwards() -> None:
    rows: list[Any] = list(fixture_rows())
    session = SessionDouble(rows)
    service = WardService(adapter(session))
    ready, release = asyncio.Event(), asyncio.Event()
    disclosed: list[object] = []

    async def prepare() -> str:
        ready.set()
        await release.wait()
        return "protected-projection"

    task = asyncio.create_task(
        service.publish(
            Secret.generate(),
            OPERATION,
            prepare=prepare,
            publication=lambda value, _context: disclosed.append(value),
            expected_policy_generation=2,
        )
    )
    await ready.wait()
    assert not session.statements
    rows[2].revoked_at = NOW
    release.set()
    with pytest.raises(WardRefusedError):
        await task
    assert not disclosed


@pytest.mark.asyncio
async def test_async_publication_refuses_before_preparation() -> None:
    session = SessionDouble([])
    called: list[object] = []

    async def prepare() -> str:
        called.append("prepare")
        return "projection"

    async def publish(value: str, context: Attribution) -> None:
        called.append(value)

    with pytest.raises(TypeError, match="synchronous"):
        await WardService(adapter(session)).publish(
            Secret.generate(),
            OPERATION,
            prepare=prepare,
            publication=cast("Callable[[str, Attribution], None]", publish),
            expected_policy_generation=2,
        )
    assert not called


@pytest.mark.asyncio
@pytest.mark.parametrize("refusal", ["none", "unknown", "audience", "issuer", "expired", "exchanged", "revoked"])
async def test_credential_exchange_refuses_current_invalid_evidence(refusal: str) -> None:
    principal_id, principal, _authentication, credential, _permission, now = fixture_rows()
    credential.exchanged_at = None
    audience = AUDIENCE
    if refusal == "audience":
        audience = "foreign"
    elif refusal == "issuer":
        credential.issuer_id = uuid4()
    elif refusal == "expired":
        credential.expires_at = now
    elif refusal == "exchanged":
        credential.exchanged_at = now
    elif refusal == "revoked":
        credential.revoked_at = now
    if refusal == "unknown":
        session = SessionDouble([None, None, now])
    else:
        session = SessionDouble([principal_id, principal, credential, now])
    secret = Secret.generate()
    if refusal == "none":
        authentication = await adapter(session).open_session(
            secret, audience=audience, expires_at=now + timedelta(minutes=1)
        )
        assert authentication.principal_id == principal_id
        assert authentication.secret != secret
        assert secret.value not in repr(authentication)
        assert credential.exchanged_at == now
    else:
        with pytest.raises(WardRefusedError):
            await adapter(session).open_session(secret, audience=audience, expires_at=now + timedelta(minutes=1))
    assert secret.value not in repr(session.audits)
    assert session.audits[0].permitted is (refusal == "none")


def test_generated_migration_has_one_head_and_retention_guard() -> None:
    from io import StringIO

    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(Config("src/lychd/db/migrations/alembic.ini"))
    revision = scripts.get_revision("0020")
    assert revision is not None
    assert revision.down_revision == "0019"
    heads = scripts.get_heads()
    assert len(heads) == 1
    assert revision.revision in {item.revision for item in scripts.walk_revisions(head=heads[0])}
    output = StringIO()
    context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})
    with Operations.context(context):
        revision.module.upgrade()
        revision.module.downgrade()
    sql = output.getvalue()
    assert "Retained Ward identity or audit prevents downgrade" in sql
    assert "FOREIGN KEY(credential_id, principal_id)" in sql
    assert "FOREIGN KEY(principal_id, principal_kind)" in sql
    assert "IN ACCESS EXCLUSIVE MODE" in sql
    for name in ("principal", "credential", "session", "permission", "user", "audit"):
        assert f"CREATE TABLE ward_{name}" in sql
        assert f"ward_{name} LIMIT 1)" in sql


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["before-handoff", "after-handoff", "commit", "ack"])
async def test_durable_unknown_attempt_survives_callback_or_commit_failure(failure: str) -> None:
    session = SessionDouble(list(fixture_rows()) * 2)
    original = RuntimeError("publication failure")
    disclosed: list[str] = []
    if failure in {"commit", "ack"}:
        session.fail_at, session.ack_lost = 2, failure == "ack"
        original = session.failure

    def publication(value: str, _context: Attribution) -> None:
        assert len(session.durable) == 1
        assert session.durable[0].outcome == "unknown"
        if failure != "before-handoff":
            disclosed.append(value)
        if failure in {"before-handoff", "after-handoff"}:
            raise original

    with pytest.raises(RuntimeError) as raised:
        await adapter(session).publish(
            Secret.generate(), OPERATION, "projection", publication, expected_policy_generation=2
        )
    assert raised.value is original
    assert session.durable[0].outcome == "unknown"
    assert session.durable[0].event == "publication-attempt"
    assert str(session.durable[0].id) in " ".join(original.__notes__)
    assert disclosed == ([] if failure == "before-handoff" else ["projection"])


@pytest.mark.asyncio
async def test_attempt_commit_ambiguity_prevents_handoff_and_restart_never_reuses_attempt() -> None:
    session = SessionDouble(list(fixture_rows()))
    session.fail_at, session.ack_lost = 1, True
    disclosed: list[str] = []
    with pytest.raises(RuntimeError):
        await adapter(session).publish(
            Secret.generate(),
            OPERATION,
            "projection",
            lambda value, _context: disclosed.append(value),
            expected_policy_generation=2,
        )
    retained_id = session.durable[0].id
    assert not disclosed
    rows: list[Any] = list(fixture_rows())
    rows[1].revoked_at = NOW
    session.values = iter(rows)
    session.fail_at = 0
    with pytest.raises(WardRefusedError):
        await adapter(session).publish(
            Secret.generate(),
            OPERATION,
            "projection",
            lambda value, _context: disclosed.append(value),
            expected_policy_generation=2,
        )
    assert session.durable[0].id == retained_id
    assert session.durable[0].outcome == "unknown"
    assert session.durable[1].id != retained_id
    assert session.durable[1].outcome == "refused"
    assert not disclosed


@pytest.mark.asyncio
async def test_revocation_between_attempt_commit_and_final_check_retains_refused() -> None:
    rows: list[Any] = list(fixture_rows())
    session = SessionDouble(rows * 2)
    session.after_commit = lambda: setattr(rows[2], "revoked_at", NOW)
    disclosed: list[str] = []
    with pytest.raises(WardRefusedError):
        await adapter(session).publish(
            Secret.generate(),
            OPERATION,
            "projection",
            lambda value, _context: disclosed.append(value),
            expected_policy_generation=2,
        )
    assert session.durable[0].outcome == "refused"
    assert not disclosed


@pytest.mark.asyncio
@pytest.mark.parametrize("shape", ["async-function", "async-callable", "async-generator", "coroutine", "task", "value"])
@pytest.mark.parametrize("through_service", [True, False])
async def test_detectable_async_or_non_none_publication_never_escapes(shape: str, *, through_service: bool) -> None:
    session = SessionDouble(list(fixture_rows()) * 2)
    disclosed: list[str] = []
    returned: list[Any] = []

    async def asynchronous(*args: object) -> None:
        disclosed.append("escaped")

    class AsyncCallable:
        async def __call__(self, *_args: object) -> None:
            disclosed.append("escaped")

    async def generator(*args: object) -> AsyncIterator[str]:
        yield "escaped"

    def wrapper(*args: object) -> object:
        result = (
            asyncio.create_task(asynchronous())
            if shape == "task"
            else asynchronous()
            if shape == "coroutine"
            else "value"
        )
        returned.append(result)
        return result

    callback = (
        asynchronous
        if shape == "async-function"
        else AsyncCallable()
        if shape == "async-callable"
        else generator
        if shape == "async-generator"
        else wrapper
    )
    publication = cast("Callable[[str, Attribution], None]", callback)
    occurrence = (
        WardService(adapter(session)).publish(
            Secret.generate(),
            OPERATION,
            prepare=lambda: asyncio.sleep(0, result="projection"),
            publication=publication,
            expected_policy_generation=2,
        )
        if through_service
        else adapter(session).publish(
            Secret.generate(),
            OPERATION,
            "projection",
            publication,
            expected_policy_generation=2,
        )
    )
    with pytest.raises(TypeError):
        await occurrence
    await asyncio.sleep(0)
    assert not disclosed
    if shape in {"async-function", "async-callable", "async-generator"}:
        assert not session.statements
    else:
        assert session.durable[0].outcome == "unknown"
        if shape == "task":
            assert returned[0].cancelled()
        elif shape == "coroutine":
            assert returned[0].cr_frame is None


@pytest.mark.asyncio
async def test_callback_error_remains_original_when_rollback_also_fails() -> None:
    session = SessionDouble(list(fixture_rows()) * 2)
    session.cleanup_failure = RuntimeError("rollback failed")
    original = RuntimeError("handoff then failed")

    def publication(_value: str, _context: Attribution) -> None:
        raise original

    with pytest.raises(RuntimeError) as raised:
        await adapter(session).publish(
            Secret.generate(), OPERATION, "projection", publication, expected_policy_generation=2
        )
    assert raised.value is original
    assert raised.value.__cause__ is session.cleanup_failure
    assert session.durable[0].outcome == "unknown"


@pytest.mark.asyncio
@pytest.mark.parametrize("isolation", [None, "repeatable read", "serializable", "read uncommitted", "READ COMMITTED"])
async def test_unsupported_actual_isolation_refuses_before_any_data_read(isolation: object) -> None:
    session = SessionDouble([])
    session.isolation = isolation
    with pytest.raises(WardRefusedError, match="actual READ COMMITTED"):
        await adapter(session).publish(
            Secret.generate(),
            OPERATION,
            "projection",
            lambda _value, _context: pytest.fail("handoff"),
            expected_policy_generation=2,
        )
    assert [str(statement) for statement in session.statements] == ["SHOW transaction_isolation"]
    assert not session.records
    assert session.isolation == isolation


@pytest.mark.asyncio
async def test_second_transaction_rechecks_actual_isolation_before_discovery() -> None:
    session = SessionDouble(list(fixture_rows()))
    session.after_commit = lambda: setattr(session, "isolation", "repeatable read")
    with pytest.raises(WardRefusedError, match="actual READ COMMITTED"):
        await adapter(session).publish(
            Secret.generate(),
            OPERATION,
            "projection",
            lambda _value, _context: pytest.fail("handoff"),
            expected_policy_generation=2,
        )
    assert session.durable[0].outcome == "unknown"
    assert str(session.statements[-1]) == "SHOW transaction_isolation"
    assert session.isolation == "repeatable read"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["autocommit", "no-server-transaction", "routed-bind", "prebound-connection"])
async def test_nontransactional_or_unsupported_bind_refuses_before_data(mode: str) -> None:
    session = SessionDouble([])
    if mode == "autocommit":
        session.autocommit = True
    elif mode == "no-server-transaction":
        session.transactional = False
    elif mode == "routed-bind":
        session.routed = True
    else:
        session.bind = cast("Any", object())
    with pytest.raises(WardRefusedError, match="actual READ COMMITTED"):
        await adapter(session).publish(
            Secret.generate(),
            OPERATION,
            "projection",
            lambda _value, _context: pytest.fail("handoff"),
            expected_policy_generation=2,
        )
    assert [str(statement) for statement in session.statements] == (
        ["SHOW transaction_isolation"] if mode == "no-server-transaction" else []
    )
    assert not session.records
