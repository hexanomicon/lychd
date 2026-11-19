"""Actual migrated PostgreSQL evidence for authenticated paired receiver custody."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import os
import ssl
import time
from collections.abc import AsyncGenerator, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Table, func, select, text, update
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.compositions.atelier.brief import ShortVideoBrief
from lychd.db.intercom_inbox import InboxError, ReceiverInbox
from lychd.db.models.intercom_inbox import IntercomInboxAttempt, IntercomInboxTask
from lychd.domain.intercom.codec import send_params, task_params
from lychd.domain.intercom.transport import IntercomEndpoint, IntercomError, PreparedRequest, RawResponse, TaskMethod
from lychd.system.services.intercom_http import BoundedIntercomHTTP, prepare_request, verify_response
from lychd.system.services.intercom_receiver import RECEIVE_PATH, IntercomReceiver, PeerInvitation
from tests.integration import test_intercom_pg as custody
from tests.scout_network_fixture import certificate
from tests.unit.system.services import test_intercom_http as wire

pytestmark = [pytest.mark.integration, pytest.mark.container, pytest.mark.asyncio]
factory = custody.factory
keys = wire.keys
_RECEIVER = UUID(int=10)
_PEER = UUID(int=20)
_POLICY = "0" * 64


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    """Use a supplied disposable PostgreSQL instance or the manual container profile."""
    explicit = os.environ.get("LYCHD_INTERCOM_TEST_DATABASE_URL")
    if explicit:
        yield explicit
        return
    pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as pg:
        yield pg.get_connection_url()


def current() -> None:
    pass


def allow_start(_text: str, _now: datetime) -> None:
    pass


def inbox(factory: async_sessionmaker[AsyncSession], peer: UUID = _PEER, policy: str = _POLICY) -> ReceiverInbox:
    return ReceiverInbox(factory, receiver=_RECEIVER, peer=peer, task_schema="public.text@1", policy=policy)


def wrapper(**fields: object) -> dict[str, Any]:
    return {
        "method": "SendMessage",
        "local_id": "sender-id",
        "message_id": "message-id",
        "text": "public brief",
        "body_digest": hashlib.sha256(b"signed bytes").hexdigest(),
        "attempt": str(uuid4()),
        "nonce": uuid4().hex,
        "signature_expires": int(datetime.now(UTC).timestamp()) + 30,
        "authorize": current,
        **fields,
    }


def control(method: str, task_id: UUID, **fields: object) -> dict[str, Any]:
    return wrapper(method=method, text=None, message_id=None, task_id=str(task_id), **fields)


async def test_concurrent_intake_restart_replay_receipt_and_manual_result(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = inbox(factory)
    first, duplicate = await asyncio.gather(owner.receive(**wrapper()), inbox(factory).receive(**wrapper()))
    assert first == duplicate
    fresh = inbox(factory)
    assert await fresh.pending(authorize=current) == (first,)
    assert await fresh.review(task_id=first.task_id, authorize=current) == (first, "public brief")
    assert await fresh.find(local_id="sender-id", authorize=current) == first
    with pytest.raises(InboxError, match="transition"):
        await fresh.decide(task_id=first.task_id, state="TASK_STATE_COMPLETED", result="too early", authorize=current)
    with pytest.raises(InboxError, match="start-policy"):
        await fresh.decide(task_id=first.task_id, state="TASK_STATE_WORKING", authorize=current)
    working = await fresh.decide(
        task_id=first.task_id, state="TASK_STATE_WORKING", authorize=current, check_start=allow_start
    )
    assert working.state == "TASK_STATE_WORKING"
    assert await fresh.receive(**control("GetTask", first.task_id)) == working
    finished = await fresh.decide(
        task_id=first.task_id, state="TASK_STATE_COMPLETED", result="public reply", authorize=current
    )
    assert finished.result == "public reply"
    assert await inbox(factory).receive(**control("GetTask", first.task_id)) == finished
    assert await fresh.receive(**control("CancelTask", first.task_id)) == finished
    assert await fresh.receive(**wrapper()) == finished
    assert (
        await fresh.decide(task_id=first.task_id, state=finished.state, result=finished.result, authorize=current)
        == finished
    )
    with pytest.raises(InboxError, match="transition"):
        await fresh.decide(task_id=first.task_id, state=finished.state, result="changed", authorize=current)
    assert await fresh.pending(authorize=current) == ()


async def test_spent_wrappers_and_semantic_identity_survive_failure_and_restart(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    original = wrapper()
    owner = inbox(factory)
    receipt = await owner.receive(**original)
    restarted = inbox(factory)
    for change in ({"nonce": original["nonce"]}, {"attempt": original["attempt"]}):
        with pytest.raises(InboxError, match="replay"):
            await restarted.receive(**wrapper(**change))
    for change in ({"body_digest": "f" * 64}, {"message_id": "changed"}, {"local_id": "changed"}, {"text": "changed"}):
        rejected = wrapper(**change)
        with pytest.raises(InboxError, match="conflict"):
            await restarted.receive(**rejected)
        with pytest.raises(InboxError, match="replay"):
            await restarted.receive(**rejected)
    with pytest.raises(InboxError, match="unknown-task"):
        await restarted.receive(**control("CancelTask", receipt.task_id, local_id="other"))
    other = inbox(factory, peer=UUID(int=30))
    with pytest.raises(InboxError, match="unknown-task"):
        await other.receive(**control("GetTask", receipt.task_id))
    assert await other.pending(authorize=current) == ()
    with pytest.raises(InboxError, match="unknown-task"):
        await other.review(task_id=receipt.task_id, authorize=current)
    changed = inbox(factory, policy="f" * 64)
    with pytest.raises(InboxError, match="conflict"):
        await changed.receive(**wrapper())
    with pytest.raises(InboxError, match="unknown-task"):
        await changed.decide(task_id=receipt.task_id, state="TASK_STATE_REJECTED", authorize=current)
    assert (await other.receive(**wrapper())).task_id != receipt.task_id
    assert (await restarted.receive(**control("CancelTask", receipt.task_id))).state == "TASK_STATE_CANCELED"
    with pytest.raises(InboxError, match="transition"):
        await restarted.decide(task_id=receipt.task_id, state="TASK_STATE_WORKING", authorize=current)


async def test_close_intake_after_submit_and_new_capacity_cannot_reset(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = inbox(factory)
    monkeypatch.setattr("lychd.db.intercom_inbox.MAX_TASKS", 2)
    first = await owner.receive(**wrapper())

    def closed(_now: datetime, _expires_at: datetime) -> None:
        msg = "intake-closed"
        raise InboxError(msg)

    assert await owner.receive(**wrapper(admit_new=closed)) == first
    new = {"local_id": "second", "message_id": "second"}
    with pytest.raises(InboxError, match="intake-closed"):
        await owner.receive(**wrapper(**new, admit_new=closed))
    assert await owner.pending(authorize=current) == (first,)
    await owner.receive(**wrapper(**new))
    with pytest.raises(InboxError, match="capacity"):
        await inbox(factory, policy="f" * 64).receive(**wrapper(local_id="third", message_id="third"))
    assert await owner.receive(**wrapper()) == first
    assert await owner.receive(**control("GetTask", first.task_id, admit_new=closed)) == first


async def test_live_wrapper_bound_and_expired_fences(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = inbox(factory)
    monkeypatch.setattr("lychd.db.intercom_inbox.MAX_LIVE_ATTEMPTS", 1)
    await owner.receive(**wrapper())
    with pytest.raises(InboxError, match="attempt-capacity"):
        await owner.receive(**wrapper())
    async with factory.begin() as session:
        await session.execute(update(IntercomInboxAttempt).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    with pytest.raises(InboxError, match="signature-time"):
        await owner.receive(**wrapper(signature_expires=0))
    await owner.receive(**wrapper())
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(IntercomInboxAttempt)) == 1


async def test_original_expiry_bounds_work_but_retains_identity(factory: async_sessionmaker[AsyncSession]) -> None:
    owner = inbox(factory)
    first = await owner.receive(**wrapper())
    async with factory.begin() as session:
        past = datetime.now(UTC) - timedelta(seconds=2)
        await session.execute(update(IntercomInboxTask).values(admitted_at=past - timedelta(hours=1), expires_at=past))
    expired = await owner.receive(**control("GetTask", first.task_id))
    assert (expired.state, expired.disposition, expired.result) == ("TASK_STATE_FAILED", "expired", None)
    assert await owner.receive(**wrapper()) == expired
    with pytest.raises(InboxError, match="transition"):
        await owner.decide(task_id=first.task_id, state="TASK_STATE_WORKING", authorize=current)


async def test_operator_authority_rechecked_across_actual_receiver_lock(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = inbox(factory)
    allowed = True

    def live() -> None:
        if not allowed:
            msg = "revoked"
            raise InboxError(msg)

    async with factory() as blocker:
        await blocker.execute(select(func.pg_advisory_xact_lock(owner._lock)))  # pyright: ignore[reportPrivateUsage]
        pending = asyncio.create_task(owner.receive(**wrapper(authorize=live)))
        try:
            async with asyncio.timeout(2):
                while True:
                    async with factory() as observer:
                        waiting = await observer.scalar(
                            text("""
                            SELECT count(*) FROM pg_stat_activity WHERE application_name=current_setting('application_name')
                              AND wait_event_type='Lock' AND query LIKE '%pg_advisory_xact_lock%' AND pid<>pg_backend_pid()
                        """)
                        )
                    if waiting:
                        break
                    await asyncio.sleep(0.005)
            allowed = False
            await blocker.rollback()
            with pytest.raises(InboxError, match="revoked"):
                await pending
        finally:
            await blocker.rollback()
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
    assert await owner.pending(authorize=current) == ()
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(IntercomInboxAttempt)) == 0


async def test_downgrade_refuses_any_retained_receiver_history(factory: async_sessionmaker[AsyncSession]) -> None:
    def downgrade(connection: Connection) -> None:
        module = importlib.import_module("lychd.db.migrations.versions.0028_intercom_inbox")
        with Operations.context(MigrationContext.configure(connection)):
            module.downgrade()

    owner = inbox(factory)
    receipt = await owner.receive(**wrapper())
    async with factory() as session:
        connection = await session.connection()
        with pytest.raises(DBAPIError, match="Retained peer inbox"):
            await connection.run_sync(downgrade)
    assert await owner.find(local_id=receipt.local_id, authorize=current) == receipt


async def test_completed_custody_survives_deadline_without_late_wire_disclosure(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = inbox(factory)
    first = await owner.receive(**wrapper())
    await owner.decide(task_id=first.task_id, state="TASK_STATE_WORKING", authorize=current, check_start=allow_start)
    done = await owner.decide(
        task_id=first.task_id, state="TASK_STATE_COMPLETED", result="authorized reply", authorize=current
    )
    async with factory.begin() as session:
        past = datetime.now(UTC) - timedelta(seconds=2)
        await session.execute(update(IntercomInboxTask).values(admitted_at=past - timedelta(hours=1), expires_at=past))
    for request in (wrapper(), control("GetTask", done.task_id), control("CancelTask", done.task_id)):
        with pytest.raises(InboxError, match="expired"):
            await owner.receive(**request)
        with pytest.raises(InboxError, match="replay"):
            await owner.receive(**request)
    retained, _ = await owner.review(task_id=done.task_id, authorize=current)
    assert (retained.disposition, retained.result) == ("completed", "authorized reply")


async def test_actual_catalog_matches_both_registered_models(factory: async_sessionmaker[AsyncSession]) -> None:
    from sqlalchemy.schema import CreateSchema

    from tests.integration import test_privacy_disclosure_migrations_pg as migration

    expected_schema = "receiver_expected_" + uuid4().hex
    async with factory() as session:
        connection = await session.connection()
        migrated_schema = await connection.scalar(text("SELECT current_schema()"))
        assert isinstance(migrated_schema, str)
        await connection.execute(CreateSchema(expected_schema))
        await connection.execution_options(schema_translate_map={None: expected_schema})
        tables = [cast("Table", model.__table__) for model in (IntercomInboxTask, IntercomInboxAttempt)]
        await connection.run_sync(IntercomInboxTask.metadata.create_all, tables=tables)
        for table in tables:
            observed = await migration._catalog(connection, migrated_schema, table.name)  # pyright: ignore[reportPrivateUsage]
            expected = await migration._catalog(connection, expected_schema, table.name)  # pyright: ignore[reportPrivateUsage]
            assert observed == expected
        await session.rollback()


async def test_closing_intake_after_insert_rolls_back_before_acknowledgment(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = inbox(factory)
    checks = 0

    def closing(_now: datetime, _expires_at: datetime) -> None:
        nonlocal checks
        checks += 1
        if checks == 2:
            msg = "intake-closed"
            raise InboxError(msg)

    with pytest.raises(InboxError, match="intake-aborted"):
        await owner.receive(**wrapper(admit_new=closing))
    assert checks == 2
    assert await owner.pending(authorize=current) == ()
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(IntercomInboxAttempt)) == 0


async def test_lost_post_commit_ack_recovers_exact_task_without_second_intake(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    commit = AsyncSession.commit

    async def lost(session: AsyncSession) -> None:
        await commit(session)
        raise SQLAlchemyError

    request = wrapper()
    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", lost)
        with pytest.raises(InboxError, match="commit-unknown"):
            await inbox(factory).receive(**request)
    restarted = inbox(factory)
    received = await restarted.find(local_id="sender-id", authorize=current)
    with pytest.raises(InboxError, match="replay"):
        await restarted.receive(**request)
    assert await restarted.receive(**wrapper()) == received
    assert await restarted.pending(authorize=current) == (received,)


@pytest.mark.parametrize("cancel", [False, True])
async def test_terminal_write_crossing_row_lock_deadline_rolls_back(
    factory: async_sessionmaker[AsyncSession], *, cancel: bool
) -> None:
    owner = inbox(factory)
    first = await owner.receive(**wrapper())
    await owner.decide(task_id=first.task_id, state="TASK_STATE_WORKING", authorize=current, check_start=allow_start)
    async with factory.begin() as session:
        now = datetime.now(UTC)
        deadline = now + timedelta(seconds=1)
        await session.execute(
            update(IntercomInboxTask).values(admitted_at=now - timedelta(seconds=1), expires_at=deadline)
        )
    async with factory() as blocker:
        await blocker.execute(select(IntercomInboxTask).where(IntercomInboxTask.id == first.task_id).with_for_update())
        pending = asyncio.create_task(
            owner.receive(**control("CancelTask", first.task_id))
            if cancel
            else owner.decide(task_id=first.task_id, state="TASK_STATE_COMPLETED", result="too late", authorize=current)
        )
        try:
            async with asyncio.timeout(2):
                while True:
                    async with factory() as observer:
                        waiting = await observer.scalar(
                            text("""
                            SELECT count(*) FROM pg_stat_activity WHERE application_name=current_setting('application_name')
                              AND wait_event_type='Lock' AND query LIKE '%UPDATE%peer_inbox_task%' AND pid<>pg_backend_pid()
                        """)
                        )
                    if waiting:
                        break
                    await asyncio.sleep(0.005)
                await asyncio.sleep(max(0, (deadline - datetime.now(UTC)).total_seconds()) + 0.01)
            await blocker.rollback()
            with pytest.raises(InboxError, match="cancellation-aborted" if cancel else "expired"):
                await pending
        finally:
            await blocker.rollback()
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
    retained, _ = await owner.review(task_id=first.task_id, authorize=current)
    assert (retained.disposition, retained.result) == ("expired", None)


async def test_first_atelier_start_rechecks_retained_brief_and_idempotent_start_keeps_ownership(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = ReceiverInbox(
        factory, receiver=_RECEIVER, peer=_PEER, task_schema="atelier.short-video-brief@1", policy=_POLICY
    )
    brief = '{"recipe":"illustrated-story","script":"An evening walk.","duration_seconds":30}'
    received = await owner.receive(**wrapper(text=brief))
    with pytest.raises(InboxError, match="start-policy"):
        await owner.decide(task_id=received.task_id, state="TASK_STATE_WORKING", authorize=current)

    checks: list[datetime] = []

    def closes(text: str, now: datetime) -> None:
        assert text == brief
        assert ShortVideoBrief.from_wire(text).can_start(now)
        checks.append(now)
        if len(checks) == 2:
            msg = "start-window"
            raise InboxError(msg)

    with pytest.raises(InboxError, match="start-window"):
        await owner.decide(task_id=received.task_id, state="TASK_STATE_WORKING", authorize=current, check_start=closes)
    assert len(checks) == 2
    assert checks[1] >= checks[0]
    assert (await owner.pending(authorize=current)) == (received,)
    started = await owner.decide(
        task_id=received.task_id, state="TASK_STATE_WORKING", authorize=current, check_start=closes
    )

    def closed(_text: str, _now: datetime) -> None:
        pytest.fail("An exact working-state retry checked a new start window.")

    assert (
        await owner.decide(task_id=received.task_id, state="TASK_STATE_WORKING", authorize=current, check_start=closed)
        == started
    )


async def test_signed_tls_receiver_lost_ack_restart_and_exact_result(  # noqa: PLR0915 - One real TLS custody scenario.
    factory: async_sessionmaker[AsyncSession],
    keys: tuple[wire._Key, wire._Key],  # pyright: ignore[reportPrivateUsage]
    tmp_path: Path,
    unused_tcp_port: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Poll an acknowledged job after restart and recover a lost acknowledgement only on the receiver."""
    sender, receiver = keys
    hostname = "atelier-peer.test"
    cert, tls_key = await asyncio.to_thread(certificate, tmp_path, "atelier-peer", hostname, include_ip=False)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert, tls_key)
    tls.set_alpn_protocols(["http/1.1"])
    address = IPv4Address("127.0.0.1")
    pair = PeerInvitation(
        receiver_id=_RECEIVER,
        sender_id=_PEER,
        hostname=hostname,
        port=unused_tcp_port,
        listen_address=address,
        peer_address=address,
        task_schema="atelier.short-video-brief@1",
        sender_key_id="sender-key",
        sender_public_key_pem=sender.public.decode("ascii"),
        signing_key_id="receiver-key",
        receiver_public_key_pem=receiver.public.decode("ascii"),
        valid_until=datetime.now(UTC) + timedelta(minutes=5),
        tls_certificate=cert,
        tls_key=tls_key,
    )
    endpoint = IntercomEndpoint(str(address), hostname, pair.port, RECEIVE_PATH, cert)
    ready = asyncio.Event()
    bind = asyncio.start_server

    async def observe_bind(*args: Any, **kwargs: Any) -> asyncio.Server:
        server = await bind(*args, **kwargs)
        ready.set()
        return server

    monkeypatch.setattr(asyncio, "start_server", observe_bind)

    @asynccontextmanager
    async def listening() -> AsyncGenerator[tuple[IntercomReceiver, ReceiverInbox]]:
        owner = ReceiverInbox(factory, receiver=_RECEIVER, peer=_PEER, task_schema=pair.task_schema, policy=_POLICY)
        listener = IntercomReceiver(pair, owner, receiver.private, current)
        ready.clear()
        async with asyncio.TaskGroup() as group:
            task = group.create_task(listener.serve(tls))
            try:
                async with asyncio.timeout(5):
                    await ready.wait()
                yield listener, owner
            finally:
                task.cancel()

    def prepare(method: TaskMethod, local_id: str, params: dict[str, object]) -> PreparedRequest:
        return prepare_request(
            method=method,
            local_task_id=local_id,
            attempt_id=uuid4().hex,
            peer_id=str(_RECEIVER),
            workload_id=str(_PEER),
            task_schema=pair.task_schema,
            endpoint=pair.endpoint,
            params=params,
            signing_key=sender.private,
            key_id=pair.sender_key_id,
        )

    gate = wire._Gate()  # pyright: ignore[reportPrivateUsage]
    transport = BoundedIntercomHTTP()
    brief = ShortVideoBrief(recipe="captioned-excerpt", script="Public archive opening.", duration_seconds=10)
    brief_text = brief.model_dump_json(exclude_none=True)
    sent = prepare("SendMessage", "commission-1", send_params(brief_text, "message-1"))
    lost = prepare("SendMessage", "commission-2", send_params(brief_text, "message-2"))
    signed_ack_lost = asyncio.Event()
    async with listening() as (listener, _):
        response = await transport.exchange(endpoint, sent, gate=gate, deadline=time.monotonic() + 10)
        known = verify_response(
            sent, response.status, response.headers, response.body, receiver.public, pair.signing_key_id
        )
        assert known.state == "TASK_STATE_SUBMITTED"
        exchange = listener._exchange  # pyright: ignore[reportPrivateUsage]

        async def drop_ack(fields: list[tuple[str, str]], body: bytes) -> tuple[RawResponse, float]:
            ack, _ = await exchange(fields, body)
            observation = verify_response(lost, ack.status, ack.headers, ack.body, receiver.public, pair.signing_key_id)
            assert observation.state == "TASK_STATE_SUBMITTED"
            signed_ack_lost.set()
            # Custody committed and the response was signed. Lose it before the socket write.
            raise ConnectionResetError

        monkeypatch.setattr(listener, "_exchange", drop_ack)
        with pytest.raises(IntercomError):
            await transport.exchange(endpoint, lost, gate=gate, deadline=time.monotonic() + 10)
        assert signed_ack_lost.is_set()

    async with listening() as (_, reopened):
        recovered = await reopened.find(local_id=lost.local_task_id, authorize=current)
        assert recovered.state == "TASK_STATE_SUBMITTED"
        assert str(recovered.task_id) != known.foreign_task_id
        task_id = UUID(known.foreign_task_id)
        await reopened.decide(
            task_id=task_id, state="TASK_STATE_WORKING", authorize=current, check_start=pair.check_start
        )
        approved = "The public cut is ready for review."
        await reopened.decide(task_id=task_id, state="TASK_STATE_COMPLETED", result=approved, authorize=current)
        poll = prepare("GetTask", sent.local_task_id, task_params("GetTask", known.foreign_task_id))
        reply = await transport.exchange(endpoint, poll, gate=gate, deadline=time.monotonic() + 10)
        observed = verify_response(poll, reply.status, reply.headers, reply.body, receiver.public, pair.signing_key_id)
        assert observed.foreign_task_id == known.foreign_task_id
        assert (observed.state, observed.text) == ("TASK_STATE_COMPLETED", (approved,))
    assert sum(handoff.phase == "connect" for handoff in gate.handoffs) == 3
    assert {handoff.application_bytes for handoff in gate.handoffs if handoff.phase == "http"} == {
        sent.wire,
        lost.wire,
        poll.wire,
    }
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(IntercomInboxTask)) == 2
        assert await session.scalar(select(func.count()).select_from(IntercomInboxAttempt)) == 3
