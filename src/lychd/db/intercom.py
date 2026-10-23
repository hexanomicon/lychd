"""Acknowledged PostgreSQL custody for outbound public-text peer operations.

Lock order is permanent host/purpose/peer/task-family capacity, enrolled peer and
current credential, task/outbox, then transmission. No lock spans a network call.
Native preparation and closure acquire the real Run first; task owners never
acquire a Run after holding a task lock.
Reads return evidence only. A fresh claim commit is necessary but never sufficient
for activation: the single-loop service independently issues its local gate.
"""

from __future__ import annotations

import base64
import binascii
import contextlib
import json
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, NoReturn, cast
from uuid import UUID, uuid4

from http_message_signatures.algorithms import ED25519  # pyright: ignore[reportPrivateImportUsage]
from http_message_signatures.exceptions import HTTPMessageSignaturesException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.agents.workflows.base import pattern_snapshot_is_valid
from lychd.db.models.intercom import (
    IntercomCapacity,
    IntercomCredential,
    IntercomDeclaration,
    IntercomOutbox,
    IntercomPeer,
    IntercomTask,
    IntercomTransmission,
)
from lychd.db.models.run import Run
from lychd.db.models.run_delivery import RunDelivery
from lychd.domain.intercom.native import PeerRunBinding, PeerTaskRef

NETWORK_ALLOWANCE = 512 * 1024
APPLICATION_LIMIT = 64 * 1024
_MAX_INT = 2**63 - 1
_DIGEST_LENGTH = 64
_MAX_NATIVE_REAUTHORIZATIONS = 64
_MIN_VISIBLE = 33
_MAX_VISIBLE = 126
_CLOSED = frozenset({"expired", "revoked", "cancelled", "refused", "terminal"})
_SECRET_KEYS = frozenset({"private_key", "private_key_pem", "password", "secret", "access_token", "run_id"})
_NATIVE_FIELDS = (
    "native_run_id",
    "native_station",
    "native_request_id",
    "native_binding_digest",
    "native_pattern_digest",
    "native_enqueue_seq",
    "native_step_id",
    "native_occurrence_id",
)
_RECORD_AUTHORITY_KEYS = frozenset((*_NATIVE_FIELDS, "adoption_closed", "closure_reason", "native_reauthorizations"))


class IntercomStoreError(ValueError):
    """Closed error codes exclude retained text, keys and driver diagnostics."""

    def __init__(self, code: str) -> None:
        """Retain one safe refusal code."""
        self.code = code
        super().__init__(code)


def _refuse(code: str) -> NoReturn:
    raise IntercomStoreError(code) from None


def _canonical(record: dict[str, Any]) -> bytes:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def _record(value: dict[str, Any]) -> dict[str, Any]:
    """Detach JSON evidence and reject accidental private credential owners."""

    def check(item: object) -> None:
        if isinstance(item, dict):
            for key, nested in cast("dict[object, Any]", item).items():
                if not isinstance(key, str) or key.lower() in _SECRET_KEYS | _RECORD_AUTHORITY_KEYS:
                    _refuse("record")
                check(nested)
        elif isinstance(item, list):
            for nested in cast("list[Any]", item):
                check(nested)

    try:
        check(value)
        return cast("dict[str, Any]", json.loads(_canonical(value)))
    except (TypeError, ValueError, OverflowError):
        _refuse("record")


def _integer(value: object, *, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= _MAX_INT:
        _refuse("record")
    return value


def _uuid(value: object) -> UUID:
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        _refuse("record")


def _time(value: object) -> datetime:
    try:
        result = datetime.fromisoformat(str(value))
        if result.tzinfo is None:
            _refuse("record")
        return result.astimezone(UTC)
    except (ValueError, TypeError):
        _refuse("record")


def _text(value: object, maximum: int) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        _refuse("record")
    return value


def _key(record: dict[str, Any]) -> tuple[bytes, str]:
    _text(record.get("key_id"), 200)
    try:
        pem = _text(record.get("public_key_pem"), 4096).encode("ascii")
        ED25519(public_key=pem)
        lines = pem.strip().splitlines()
        if lines[0] != b"-----BEGIN PUBLIC KEY-----" or lines[-1] != b"-----END PUBLIC KEY-----":
            _refuse("record")
        der = base64.b64decode(b"".join(b"".join(lines[1:-1]).split()), validate=True)
        # RFC 8410 Ed25519 SPKI has absent parameters and exactly 32 key octets.
        prefix = bytes.fromhex("302a300506032b6570032100")
        if len(der) != len(prefix) + 32 or not der.startswith(prefix):
            _refuse("record")
    except (ValueError, TypeError, IndexError, binascii.Error, HTTPMessageSignaturesException):
        _refuse("record")
    return pem, _digest(der)


def _same(record: dict[str, Any], retained: dict[str, Any], digest: str) -> None:
    if _digest(_canonical(retained)) != digest or _canonical(record) != _canonical(retained):
        _refuse("conflict")


def _current(peer: IntercomPeer, record: dict[str, Any]) -> None:
    if peer.revoked:
        _refuse("revoked")
    for field in ("policy_generation", "key_version", "revocation_generation"):
        if _integer(record.get(field)) != getattr(peer, field):
            _refuse("policy")


def task_snapshot(task: IntercomTask, outbox: IntercomOutbox) -> dict[str, Any]:
    """Validate sealed custody before exposing detached task and typed owner evidence."""
    _same(task.record, task.record, task.record_digest)
    if (
        outbox.task_id != task.id
        or outbox.body_digest != _digest(outbox.body)
        or outbox.body != task.record["body"].encode()
        or str(task.peer_id) != task.record["peer_id"]
        or str(task.declaration_id) != task.record["declaration_id"]
        or str(task.operation_id) != task.record["operation_id"]
        or task.purpose != task.record["purpose"]
        or task.task_schema != task.record["task_schema"]
        or task.expires_at != _time(task.record["expires_at"])
        or task.policy_generation != task.record["policy_generation"]
        or task.key_version != task.record["key_version"]
        or task.revocation_generation != task.record["revocation_generation"]
    ):
        _refuse("conflict")
    native = {field: getattr(task, field) for field in _NATIVE_FIELDS}
    if any(value is not None for value in native.values()) and any(value is None for value in native.values()):
        _refuse("conflict")
    terminal = _record(task.terminal_record) if task.terminal_record is not None else None
    return {
        **_record(task.record),
        "task_id": str(task.id),
        "body": outbox.body,
        "status": task.local_status,
        "local_status": task.local_status,
        "foreign_task_id": task.foreign_task_id,
        "foreign_status": task.foreign_status,
        "result": terminal.get("result") if task.local_status == "terminal" and terminal else None,
        "settlement": terminal,
        "context_id": terminal.get("context_id", task.record.get("context_id"))
        if terminal
        else task.record.get("context_id"),
        "submit_claimed": outbox.submit_claimed,
        **{field: str(value) if isinstance(value, UUID) else value for field, value in native.items()},
        "adoption_closed": bool(task.adoption_closed),
        "closure_reason": task.closure_reason,
        "native_reauthorizations": [_record(item) for item in (task.native_reauthorizations or [])],
        "cancellation_observation": {
            field: terminal.get(field)
            for field in ("foreign_task_id", "foreign_status", "context_id", "response_digest", "response_nonce")
        }
        if (task.local_status == "cancelled" or task.adoption_closed)
        and terminal
        and terminal.get("status") == "received"
        else None,
    }


def _native_binding(
    run: Run,
    delivery: RunDelivery | None,
    ref: PeerTaskRef,
    record: dict[str, Any],
    *,
    pattern_digest: str,
    enqueue_seq: int,
    step_id: str,
    occurrence_id: str,
) -> dict[str, Any]:
    """Validate native provenance only against the locked canonical running claim."""
    try:
        binding = PeerRunBinding.model_validate(run.intent.get("admitted_peer"))
    except ValueError:
        _refuse("native-binding")
    if (
        str(run.id) != ref.run_id
        or run.status != "running"
        or run.workflow_name != "native_public_peer"
        or run.enqueue_seq != _integer(enqueue_seq)
        or delivery is None
        or delivery.run_id != run.id
        or delivery.enqueue_seq != enqueue_seq
        or delivery.state != "claimed"
        or binding.request_id != ref.request_id
        or binding.digest != ref.binding_digest
        or not pattern_snapshot_is_valid(run.pattern_manifest)
        or run.pattern_manifest["digest"] != pattern_digest
        or not any(node["key"] == ref.station and node["kind"] == "peer" for node in run.pattern_manifest["nodes"])
    ):
        _refuse("native-binding")
    for field in (
        "peer_id",
        "declaration_id",
        "operation_id",
        "purpose",
        "task_schema",
        "endpoint",
        "category",
        "source_digest",
        "text_digest",
    ):
        if str(record.get(field)) != str(getattr(binding, field)):
            _refuse("native-binding")
    if _time(record.get("expires_at")) != binding.expires_at or binding.expires_at <= datetime.now(UTC):
        _refuse("native-binding")
    return {
        "native_run_id": run.id,
        "native_station": _text(ref.station, 100),
        "native_request_id": ref.request_id,
        "native_binding_digest": binding.digest,
        "native_pattern_digest": _text(pattern_digest, 64),
        "native_enqueue_seq": enqueue_seq,
        "native_step_id": _text(step_id, 128),
        "native_occurrence_id": _text(occurrence_id, 128),
    }


def _settlement(record: dict[str, Any]) -> tuple[str, int]:
    status = record.get("status")
    accepted = _integer(record.get("accepted_network_bytes", 0))
    if status not in {"received", "refused", "unknown"}:
        _refuse("record")
    if status == "received":
        nonce = _text(record.get("response_nonce"), 128)
        if any(not _MIN_VISIBLE <= ord(char) <= _MAX_VISIBLE for char in nonce):
            _refuse("record")
    return str(status), accepted


def transmission_snapshot(row: IntercomTransmission) -> dict[str, Any]:
    """Validate immutable physical-claim identity before exposing custody evidence."""
    _same(row.record, row.record, row.record_digest)
    if any(
        getattr(row, field) != row.record.get(field)
        for field in (
            "method",
            "policy_generation",
            "key_version",
            "revocation_generation",
            "application_bytes",
            "network_bytes",
        )
    ):
        _refuse("conflict")
    if row.settlement is None:
        if row.status != "claimed":
            _refuse("conflict")
    else:
        status, accepted = _settlement(row.settlement)
        if row.status != status or row.accepted_network_bytes != accepted:
            _refuse("conflict")
    return {
        "id": str(row.id),
        "task_id": str(row.task_id),
        "method": row.method,
        "status": row.status,
        "record": _record(row.record),
        "settlement": _record(row.settlement) if row.settlement is not None else None,
    }


async def _commit(session: AsyncSession) -> None:
    try:
        await session.commit()
    except BaseException:  # noqa: BLE001 - commit cancellation has an uncertain durable outcome
        with contextlib.suppress(BaseException):
            await session.rollback()
        _refuse("commit-unknown")


async def _peer_row(session: AsyncSession, peer_id: UUID, *, lock: bool = False) -> IntercomPeer:
    query = select(IntercomPeer).where(IntercomPeer.id == peer_id)
    row = await session.scalar(query.with_for_update().execution_options(populate_existing=True) if lock else query)
    if row is None:
        _refuse("missing")
    _same(row.enrollment, row.enrollment, row.enrollment_digest)
    return row


async def _credential_row(session: AsyncSession, peer: IntercomPeer) -> IntercomCredential:
    row = await session.scalar(
        select(IntercomCredential)
        .where(IntercomCredential.peer_id == peer.id, IntercomCredential.version == peer.key_version)
        .with_for_update()
    )
    if row is None:
        _refuse("conflict")
    _same(row.record, row.record, row.record_digest)
    pem, digest = _key(row.record)
    if pem != row.public_key_pem or digest != row.public_key_digest or row.record["key_id"] != row.key_id:
        _refuse("conflict")
    return row


async def lock_current_peer(session: AsyncSession, peer_id: UUID) -> IntercomPeer:
    """Lock enrolled peer then validate and lock its exact current credential.

    Native ownership callers acquire their Run first; no task lock is held when
    entering this shared R10 authority chain.
    """
    peer = await _peer_row(session, peer_id, lock=True)
    await _credential_row(session, peer)
    return peer


def require_current_peer(peer: IntercomPeer, record: dict[str, Any]) -> None:
    """Recheck durable revocation and all task authority generations without yielding."""
    _current(peer, record)


class IntercomStore:
    """Dedicated durable custody, with no deletion, refund or live-token API."""

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        """Use only the host-owned async PostgreSQL session factory."""
        self._factory = factory

    @asynccontextmanager
    async def _session(self, *, write: bool = False) -> AsyncGenerator[AsyncSession]:
        try:
            async with self._factory() as session:
                yield session
                if write:
                    await _commit(session)
        except IntercomStoreError:
            raise
        except Exception:  # noqa: BLE001 - project no driver or retained-text diagnostics
            _refuse("store")

    async def _peer(self, session: AsyncSession, peer_id: UUID, *, lock: bool = False) -> IntercomPeer:
        return await _peer_row(session, peer_id, lock=lock)

    async def _credential(self, session: AsyncSession, peer: IntercomPeer) -> IntercomCredential:
        return await _credential_row(session, peer)

    async def _peer_snapshot(self, session: AsyncSession, peer: IntercomPeer) -> dict[str, Any]:
        credential = await self._credential(session, peer)
        return {
            **_record(peer.enrollment),
            "peer_id": str(peer.id),
            "key": _record(credential.record),
            "current_key": _record(credential.record),
            "key_version": peer.key_version,
            "policy_generation": peer.policy_generation,
            "revocation_generation": peer.revocation_generation,
            "revoked": peer.revoked,
            "policy": _record(peer.policy),
        }

    async def enroll(self, peer_id: UUID, enrollment: dict[str, Any]) -> dict[str, Any]:
        record = _record(enrollment)
        key = record.get("key")
        if not isinstance(key, dict) or not isinstance(record.get("policy"), dict):
            _refuse("record")
        key = cast("dict[str, Any]", key)
        pem, key_digest = _key(key)
        generation = _integer(record["policy"].get("generation", 1), minimum=1)
        async with self._session(write=True) as session:
            inserted = await session.scalar(
                insert(IntercomPeer)
                .values(
                    id=peer_id,
                    enrollment=record,
                    enrollment_digest=_digest(_canonical(record)),
                    key_version=1,
                    policy_generation=generation,
                    revocation_generation=0,
                    revoked=False,
                    policy=record["policy"],
                )
                .on_conflict_do_nothing(index_elements=[IntercomPeer.id])
                .returning(IntercomPeer.id)
            )
            peer = await self._peer(session, peer_id, lock=True)
            _same(record, peer.enrollment, peer.enrollment_digest)
            if inserted is not None:
                session.add(
                    IntercomCredential(
                        id=uuid4(),
                        peer_id=peer_id,
                        version=1,
                        key_id=key["key_id"],
                        public_key_pem=pem,
                        public_key_digest=key_digest,
                        record=key,
                        record_digest=_digest(_canonical(key)),
                    )
                )
                await session.flush()
            return await self._peer_snapshot(session, peer)

    async def peer(self, peer_id: UUID) -> dict[str, Any]:
        async with self._session() as session:
            return await self._peer_snapshot(session, await self._peer(session, peer_id, lock=True))

    async def rotate(self, peer_id: UUID, key: dict[str, Any]) -> dict[str, Any]:
        record = _record(key)
        pem, digest = _key(record)
        async with self._session(write=True) as session:
            peer = await self._peer(session, peer_id, lock=True)
            if peer.revoked:
                _refuse("revoked")
            await self._credential(session, peer)
            old = await session.scalar(
                select(IntercomCredential).where(
                    IntercomCredential.peer_id == peer_id,
                    (IntercomCredential.key_id == record["key_id"]) | (IntercomCredential.public_key_digest == digest),
                )
            )
            if old is not None:
                _same(record, old.record, old.record_digest)
                if old.version != peer.key_version:
                    _refuse("revoked")
            else:
                peer.key_version += 1
                session.add(
                    IntercomCredential(
                        id=uuid4(),
                        peer_id=peer_id,
                        version=peer.key_version,
                        key_id=record["key_id"],
                        public_key_pem=pem,
                        public_key_digest=digest,
                        record=record,
                        record_digest=_digest(_canonical(record)),
                    )
                )
                await session.flush()
            return await self._peer_snapshot(session, peer)

    async def revoke(self, peer_id: UUID) -> dict[str, Any]:
        async with self._session(write=True) as session:
            peer = await self._peer(session, peer_id, lock=True)
            if not peer.revoked:
                peer.revoked = True
                peer.revocation_generation += 1
                peer.policy_generation += 1
            return await self._peer_snapshot(session, peer)

    async def set_policy(self, peer_id: UUID, policy: dict[str, Any], *, expected_generation: int) -> dict[str, Any]:
        record = _record(policy)
        async with self._session(write=True) as session:
            peer = await self._peer(session, peer_id, lock=True)
            if peer.revoked:
                _refuse("revoked")
            if peer.policy_generation != _integer(expected_generation, minimum=1):
                _refuse("policy")
            if _canonical(peer.policy) != _canonical(record):
                generation = _integer(record.get("generation", peer.policy_generation + 1), minimum=1)
                if generation <= peer.policy_generation:
                    _refuse("policy")
                peer.policy = record
                peer.policy_generation = generation
            return await self._peer_snapshot(session, peer)

    async def declare(self, declaration_id: UUID, record: dict[str, Any]) -> None:
        record = _record(record)
        peer_id, operation_id = _uuid(record.get("peer_id")), _uuid(record.get("operation_id"))
        generation = _integer(record.get("policy_generation"), minimum=1)
        async with self._session(write=True) as session:
            peer = await self._peer(session, peer_id, lock=True)
            if peer.revoked or peer.policy_generation != generation:
                _refuse("policy")
            await session.execute(
                insert(IntercomDeclaration)
                .values(
                    id=declaration_id,
                    peer_id=peer_id,
                    operation_id=operation_id,
                    policy_generation=generation,
                    record=record,
                    record_digest=_digest(_canonical(record)),
                )
                .on_conflict_do_nothing(index_elements=[IntercomDeclaration.id])
            )
            row = await session.get(IntercomDeclaration, declaration_id)
            if row is None:
                _refuse("missing")
            _same(record, row.record, row.record_digest)

    async def declaration(self, declaration_id: UUID) -> dict[str, Any]:
        """Read the exact original public-source assertion as nonbearer evidence."""
        async with self._session() as session:
            row = await session.get(IntercomDeclaration, declaration_id)
            if row is None:
                _refuse("missing")
            _same(row.record, row.record, row.record_digest)
            if (
                str(row.peer_id) != row.record.get("peer_id")
                or str(row.operation_id) != row.record.get("operation_id")
                or row.policy_generation != row.record.get("policy_generation")
            ):
                _refuse("conflict")
            return {**_record(row.record), "declaration_id": str(row.id)}

    async def _task(
        self, session: AsyncSession, task_id: UUID, *, lock: bool = False, peer_id: UUID | None = None
    ) -> IntercomTask:
        query = select(IntercomTask).where(IntercomTask.id == task_id)
        if peer_id is not None:
            query = query.where(IntercomTask.peer_id == peer_id)
        row = await session.scalar(query.with_for_update().execution_options(populate_existing=True) if lock else query)
        if row is None:
            _refuse("missing")
        return row

    async def _outbox(self, session: AsyncSession, task_id: UUID, *, lock: bool = False) -> IntercomOutbox:
        query = select(IntercomOutbox).where(IntercomOutbox.task_id == task_id)
        row = await session.scalar(query.with_for_update().execution_options(populate_existing=True) if lock else query)
        if row is None:
            _refuse("conflict")
        return row

    async def create_task(self, task_id: UUID, record: dict[str, Any]) -> dict[str, Any]:
        """Prepare a standalone operator operation without a fabricated Run owner."""
        record = _record(record)
        async with self._session(write=True) as session:
            return await self._create_task(session, task_id, record)

    async def create_native_task(
        self,
        task_id: UUID,
        record: dict[str, Any],
        *,
        ref: PeerTaskRef,
        pattern_digest: str,
        enqueue_seq: int,
        step_id: str,
        occurrence_id: str,
    ) -> dict[str, Any]:
        """Prepare one typed same-Run occurrence under Run-first claim ownership."""
        record = _record(record)
        if ref.task_id != task_id:
            _refuse("native-binding")
        async with self._session(write=True) as session:
            run = await session.scalar(
                select(Run)
                .where(Run.id == _uuid(ref.run_id))
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if run is None:
                _refuse("native-binding")
            delivery = await session.scalar(
                select(RunDelivery)
                .where(RunDelivery.run_id == run.id, RunDelivery.enqueue_seq == enqueue_seq)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            native = _native_binding(
                run,
                delivery,
                ref,
                record,
                pattern_digest=pattern_digest,
                enqueue_seq=enqueue_seq,
                step_id=step_id,
                occurrence_id=occurrence_id,
            )
            existing = await session.scalar(
                select(IntercomTask)
                .where(
                    IntercomTask.native_run_id == run.id,
                    IntercomTask.native_station == ref.station,
                    IntercomTask.native_request_id == ref.request_id,
                )
                .execution_options(populate_existing=True)
            )
            if existing is not None and existing.id != task_id:
                _refuse("conflict")
            return await self._create_task(session, task_id, record, native=native)

    async def _create_task(
        self,
        session: AsyncSession,
        task_id: UUID,
        record: dict[str, Any],
        *,
        native: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = _record(record)
        peer_id, declaration_id = _uuid(record.get("peer_id")), _uuid(record.get("declaration_id"))
        operation_id = _uuid(record.get("operation_id"))
        purpose, schema = _text(record.get("purpose"), 200), _text(record.get("task_schema"), 300)
        body = _text(record.get("body"), 48 * 1024).encode()
        expires = _time(record.get("expires_at"))
        if len(body) > 48 * 1024 or expires <= datetime.now(UTC):
            _refuse("expiry")
        native = native or {}
        peer = await self._peer(session, peer_id, lock=True)
        _current(peer, record)
        await self._credential(session, peer)
        declaration = await session.get(IntercomDeclaration, declaration_id)
        if (
            declaration is None
            or declaration.peer_id != peer_id
            or declaration.operation_id != operation_id
            or declaration.policy_generation != peer.policy_generation
        ):
            _refuse("conflict")
        _same(declaration.record, declaration.record, declaration.record_digest)
        if native and any(
            record.get(field) != declaration.record.get(field)
            for field in ("source_digest", "text_digest", "purpose", "task_schema", "endpoint", "category")
        ):
            _refuse("native-binding")
        inserted = await session.scalar(
            insert(IntercomTask)
            .values(
                id=task_id,
                peer_id=peer_id,
                declaration_id=declaration_id,
                operation_id=operation_id,
                purpose=purpose,
                task_schema=schema,
                expires_at=expires,
                policy_generation=peer.policy_generation,
                key_version=peer.key_version,
                revocation_generation=peer.revocation_generation,
                record=record,
                record_digest=_digest(_canonical(record)),
                local_status="prepared",
                adoption_closed=False,
                native_reauthorizations=[],
                **native,
            )
            .on_conflict_do_nothing(index_elements=[IntercomTask.id])
            .returning(IntercomTask.id)
        )
        task = await self._task(session, task_id, lock=True)
        _same(record, task.record, task.record_digest)
        if any(getattr(task, field) != native.get(field) for field in _NATIVE_FIELDS):
            _refuse("conflict")
        if inserted is not None:
            session.add(
                IntercomOutbox(id=uuid4(), task_id=task_id, body=body, body_digest=_digest(body), submit_claimed=False)
            )
            await session.flush()
        return task_snapshot(task, await self._outbox(session, task_id))

    async def task(self, task_id: UUID, *, peer_id: UUID | None = None) -> dict[str, Any]:
        async with self._session() as session:
            task = await self._task(session, task_id, peer_id=peer_id)
            return task_snapshot(task, await self._outbox(session, task_id))

    async def native_task(self, run_id: str, station: str, request_id: UUID) -> dict[str, Any] | None:
        """Read a semantic native occurrence without creating another task."""
        async with self._session() as session:
            task = await session.scalar(
                select(IntercomTask).where(
                    IntercomTask.native_run_id == _uuid(run_id),
                    IntercomTask.native_station == station,
                    IntercomTask.native_request_id == request_id,
                )
            )
            return task_snapshot(task, await self._outbox(session, task.id)) if task is not None else None

    async def native_tasks(self, run_id: str) -> list[dict[str, Any]]:
        """Retain every native occurrence, independently of the current wait owner."""
        async with self._session() as session:
            tasks = await session.scalars(
                select(IntercomTask).where(IntercomTask.native_run_id == _uuid(run_id)).order_by(IntercomTask.id)
            )
            return [task_snapshot(task, await self._outbox(session, task.id)) for task in tasks.all()]

    async def close_native_run(self, run_id: str, reason: str = "cancelled") -> list[dict[str, Any]]:
        """Close adoption for all same-Run tasks, including terminal and pre-park rows."""
        if reason not in {"cancelled", "expired", "revoked", "refused"}:
            _refuse("record")
        async with self._session(write=True) as session:
            run = await session.scalar(select(Run).where(Run.id == _uuid(run_id)).with_for_update())
            if run is None:
                _refuse("missing")
            rows = await session.scalars(
                select(IntercomTask)
                .where(IntercomTask.native_run_id == run.id)
                .order_by(IntercomTask.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            snapshots: list[dict[str, Any]] = []
            for task in rows.all():
                outbox = await self._outbox(session, task.id, lock=True)
                task.adoption_closed = True
                task.closure_reason = task.closure_reason or reason
                if task.local_status not in _CLOSED:
                    task.local_status = reason
                snapshots.append(task_snapshot(task, outbox))
            await session.flush()
            return snapshots

    async def record_native_authorization(
        self,
        run_id: str,
        task_id: UUID,
        record: dict[str, Any],
        *,
        current: Callable[[], None],
    ) -> None:
        """Append attribution evidence; it never restores a process-owned permit."""
        record = _record(record)
        if set(record) != {
            "subject",
            "authentication_generation",
            "actions",
            "reaffirm_public_source",
            "authorized_at",
            "binding_digest",
        }:
            _refuse("record")
        _text(record["subject"], 200)
        _uuid(record["authentication_generation"])
        _time(record["authorized_at"])
        if (
            not isinstance(record["actions"], list)
            or not record["actions"]
            or any(
                not isinstance(action, str) or action not in {"submit", "poll", "read", "cancel", "adopt", "resume"}
                for action in cast("list[object]", record["actions"])
            )
            or type(record["reaffirm_public_source"]) is not bool
        ):
            _refuse("record")
        async with self._session(write=True) as session:
            run = await session.scalar(select(Run).where(Run.id == _uuid(run_id)).with_for_update())
            if run is None:
                _refuse("missing")
            task = await self._task(session, task_id, lock=True)
            try:
                binding = PeerRunBinding.model_validate(run.intent.get("admitted_peer"))
            except ValueError:
                _refuse("native-binding")
            if (
                task.native_run_id != run.id
                or task.adoption_closed
                or task.local_status in {"cancelled", "expired", "revoked", "refused"}
                or task.native_binding_digest != record["binding_digest"]
                or task.native_binding_digest != binding.digest
                or task.native_request_id != binding.request_id
                or task.native_pattern_digest != run.pattern_manifest.get("digest")
                or task.expires_at <= datetime.now(UTC)
                or run.status in {"cancelling", "cancelled", "failed", "done"}
            ):
                _refuse("closed")
            if len(task.native_reauthorizations or []) >= _MAX_NATIVE_REAUTHORIZATIONS:
                _refuse("authorization-capacity")
            current()
            task.native_reauthorizations = [*(task.native_reauthorizations or []), record]
            await session.flush()
            current()

    async def terminal_transmission(self, task_id: UUID) -> dict[str, Any] | None:
        """Return actual same-task authenticated terminal custody for native CAS."""
        async with self._session() as session:
            task = await self._task(session, task_id)
            task_snapshot(task, await self._outbox(session, task_id))
            terminal = task.terminal_record
            if task.local_status != "terminal" or terminal is None or terminal.get("terminal") is not True:
                return None
            row = await session.scalar(
                select(IntercomTransmission)
                .where(
                    IntercomTransmission.task_id == task_id,
                    IntercomTransmission.status == "received",
                    IntercomTransmission.settlement == terminal,
                )
                .order_by(IntercomTransmission.id)
                .limit(1)
            )
            if row is None:
                return None
            if row.settlement != terminal or terminal.get("status") != "received":
                _refuse("conflict")
            return transmission_snapshot(row)

    async def native_transmission(self, task_id: UUID) -> dict[str, Any] | None:
        """Read the permanently claimed semantic submit for an honest local disposition."""
        async with self._session() as session:
            task = await self._task(session, task_id)
            if task.native_run_id is None:
                _refuse("native-binding")
            outbox = await self._outbox(session, task_id)
            task_snapshot(task, outbox)
            if not outbox.submit_claimed:
                return None
            row = await session.scalar(
                select(IntercomTransmission)
                .where(
                    IntercomTransmission.task_id == task_id,
                    IntercomTransmission.method == "SendMessage",
                )
                .order_by(IntercomTransmission.id)
                .limit(1)
            )
            if row is None:
                _refuse("conflict")
            return transmission_snapshot(row)

    async def close_task(self, task_id: UUID, *, peer_id: UUID, reason: str = "cancelled") -> dict[str, Any]:
        """Commit a local disposition; Run retirement separately closes native adoption."""
        if reason not in {"cancelled", "expired", "revoked", "refused"}:
            _refuse("record")
        async with self._session(write=True) as session:
            initial = await self._task(session, task_id, peer_id=peer_id)
            await self._peer(session, initial.peer_id, lock=True)
            task = await self._task(session, task_id, lock=True, peer_id=peer_id)
            outbox = await self._outbox(session, task_id, lock=True)
            if task.local_status not in _CLOSED:
                task.local_status = reason
                await session.flush()
            return task_snapshot(task, outbox)

    async def _capacities(
        self, session: AsyncSession, task: IntercomTask, limits: dict[str, Any]
    ) -> list[IntercomCapacity]:
        """Task family is sha256(peer UUID + newline + exact schema), never task UUID."""
        identities = (
            ("host", "host"),
            ("purpose", task.purpose),
            ("peer", str(task.peer_id)),
            ("task", _digest(f"{task.peer_id}\n{task.task_schema}".encode())),
        )
        rows: list[IntercomCapacity] = []
        for scope, identity in identities:
            limit = limits.get(scope)
            if not isinstance(limit, dict):
                _refuse("capacity")
            limit = cast("dict[str, Any]", limit)
            uses = _integer(limit.get("uses"))
            application = _integer(limit.get("application_bytes"))
            network = _integer(limit.get("network_bytes"))
            await session.execute(
                insert(IntercomCapacity)
                .values(
                    id=uuid4(),
                    scope=scope,
                    scope_id=identity,
                    uses_limit=uses,
                    application_limit=application,
                    network_limit=network,
                    uses_charged=0,
                    application_charged=0,
                    network_charged=0,
                )
                .on_conflict_do_nothing(index_elements=[IntercomCapacity.scope, IntercomCapacity.scope_id])
            )
            row = await session.scalar(
                select(IntercomCapacity)
                .where(IntercomCapacity.scope == scope, IntercomCapacity.scope_id == identity)
                .with_for_update()
            )
            if row is None or (row.uses_limit, row.application_limit, row.network_limit) != (
                uses,
                application,
                network,
            ):
                _refuse("capacity")
            rows.append(row)
        return rows

    async def claim(  # noqa: C901 - keep the charge and permanent-submit fence in one transaction
        self, task_id: UUID, attempt_id: UUID, record: dict[str, Any], limits: dict[str, Any]
    ) -> dict[str, Any]:
        record, limits = _record(record), _record(limits)
        method = record.get("method")
        application = _integer(record.get("application_bytes"), minimum=1)
        network = _integer(record.get("network_bytes"), minimum=1)
        if (
            method not in {"SendMessage", "GetTask", "CancelTask"}
            or application > APPLICATION_LIMIT
            or network != NETWORK_ALLOWANCE
        ):
            _refuse("record")
        digest = _text(record.get("wire_digest"), 64)
        if len(digest) != _DIGEST_LENGTH or any(char not in "0123456789abcdef" for char in digest):
            _refuse("record")
        async with self._session(write=True) as session:
            initial = await self._task(session, task_id)
            capacities = await self._capacities(session, initial, limits)
            peer = await self._peer(session, initial.peer_id, lock=True)
            _current(peer, record)
            await self._credential(session, peer)
            task = await self._task(session, task_id, lock=True)
            outbox = await self._outbox(session, task_id, lock=True)
            task_snapshot(task, outbox)
            previous = await session.get(IntercomTransmission, attempt_id, with_for_update=True)
            if previous is not None:
                _same(record, previous.record, previous.record_digest)
                _refuse("claimed")
            if task.expires_at <= datetime.now(UTC):
                _refuse("expiry")
            if task.local_status in _CLOSED and not (
                task.local_status == "cancelled" and method in {"GetTask", "CancelTask"}
            ):
                _refuse("closed")
            if method == "SendMessage":
                if task.adoption_closed:
                    _refuse("closed")
                if outbox.submit_claimed or task.foreign_task_id is not None:
                    _refuse("claimed")
                if application < len(outbox.body):
                    _refuse("capacity")
                outbox.submit_claimed = True
            elif task.foreign_task_id is None:
                _refuse("missing-foreign-task")
            for row in capacities:
                if (
                    row.uses_charged + 1 > row.uses_limit
                    or row.application_charged + application > row.application_limit
                    or row.network_charged + network > row.network_limit
                ):
                    _refuse("capacity")
                row.uses_charged += 1
                row.application_charged += application
                row.network_charged += network
            session.add(
                IntercomTransmission(
                    id=attempt_id,
                    task_id=task_id,
                    method=method,
                    policy_generation=peer.policy_generation,
                    key_version=peer.key_version,
                    revocation_generation=peer.revocation_generation,
                    application_bytes=application,
                    network_bytes=network,
                    accepted_network_bytes=0,
                    record=record,
                    record_digest=_digest(_canonical(record)),
                    status="claimed",
                )
            )
            task.local_status = "submitting" if method == "SendMessage" else task.local_status
            await session.flush()
            return {**record, "attempt_id": str(attempt_id), "task": task_snapshot(task, outbox)}

    async def settle(  # noqa: C901 - preserve ordered custody and closed-adoption fences together
        self, task_id: UUID, attempt_id: UUID, record: dict[str, Any], *, current: Callable[[], None] | None = None
    ) -> dict[str, Any]:
        record = _record(record)
        status, accepted = _settlement(record)
        async with self._session(write=True) as session:
            initial = await self._task(session, task_id)
            peer = await self._peer(session, initial.peer_id, lock=True)
            task = await self._task(session, task_id, lock=True)
            outbox = await self._outbox(session, task_id, lock=True)
            transmission = await session.get(IntercomTransmission, attempt_id, with_for_update=True)
            if transmission is None or transmission.task_id != task_id or accepted > transmission.network_bytes:
                _refuse("conflict")
            _same(transmission.record, transmission.record, transmission.record_digest)
            if transmission.settlement is not None:
                if _canonical(record) != _canonical(transmission.settlement):
                    _refuse("conflict")
                if current is not None:
                    current()
            else:
                if status == "received":
                    _current(peer, transmission.record)
                    await self._response_nonce(session, task.peer_id, attempt_id, record)
                if current is not None:
                    current()
                transmission.status, transmission.settlement = str(status), record
                transmission.accepted_network_bytes = accepted
                if task.expires_at <= datetime.now(UTC) and task.local_status not in _CLOSED:
                    task.local_status = "expired"
                if task.adoption_closed and status == "received":
                    self._observe_closed(task, record)
                elif task.local_status not in _CLOSED:
                    self._adopt(task, record)
                elif task.local_status == "cancelled" and status == "received":
                    self._observe_closed(task, record)
                await session.flush()
                if current is not None:
                    current()
            return task_snapshot(task, outbox)

    @staticmethod
    async def _response_nonce(session: AsyncSession, peer_id: UUID, attempt_id: UUID, record: dict[str, Any]) -> None:
        """Peer lock serializes this retained nonce check and its settlement write."""
        nonce = record.get("response_nonce")
        nonce = _text(nonce, 128)
        duplicate = await session.scalar(
            select(IntercomTransmission.id)
            .join(IntercomTask, IntercomTransmission.task_id == IntercomTask.id)
            .where(
                IntercomTask.peer_id == peer_id,
                IntercomTransmission.id != attempt_id,
                IntercomTransmission.status == "received",
                IntercomTransmission.settlement["response_nonce"].astext == nonce,
            )
            .limit(1)
        )
        if duplicate is not None:
            _refuse("replay")

    @staticmethod
    def _observe_closed(task: IntercomTask, record: dict[str, Any]) -> None:
        foreign = record.get("foreign_task_id")
        if foreign is not None and task.foreign_task_id not in {None, foreign}:
            _refuse("conflict")
        if foreign is not None:
            task.foreign_task_id = _text(foreign, 128)
        previous = task.terminal_record.get("context_id") if task.terminal_record else task.record.get("context_id")
        if record.get("context_id") is not None and previous not in {None, record["context_id"]}:
            _refuse("conflict")
        if record.get("foreign_status") is not None:
            task.foreign_status = _text(record["foreign_status"], 32)
        if task.local_status != "terminal":
            task.terminal_record = {**record, "context_id": record.get("context_id") or previous}

    @staticmethod
    def _adopt(task: IntercomTask, record: dict[str, Any]) -> None:  # noqa: C901 - ordered admission fences
        if record.get("status") != "received":
            if any(
                record.get(field) is not None for field in ("foreign_task_id", "foreign_status", "context_id", "result")
            ):
                _refuse("record")
            task.local_status = "unknown" if record["status"] == "unknown" else "refused"
            return
        foreign = record.get("foreign_task_id")
        if foreign is not None:
            foreign = _text(foreign, 128)
            if any(
                char
                not in "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
                for char in foreign
            ):
                _refuse("record")
            if task.foreign_task_id is not None and foreign != task.foreign_task_id:
                _refuse("conflict")
            task.foreign_task_id = foreign
        context = record.get("context_id")
        retained_context = (
            task.terminal_record.get("context_id") if task.terminal_record else task.record.get("context_id")
        )
        if context is not None and retained_context not in {None, context}:
            _refuse("conflict")
        if record.get("foreign_status") is not None:
            task.foreign_status = _text(record["foreign_status"], 32)
        task.terminal_record = {**record, "context_id": context or retained_context}
        if record.get("terminal") is True:
            if record.get("status") != "received":
                _refuse("record")
            task.local_status = "terminal"
        elif record.get("local_status") is not None:
            task.local_status = _text(record["local_status"], 24)
        elif record.get("status") == "unknown":
            task.local_status = "unknown"
        elif task.foreign_task_id is not None:
            task.local_status = "pending"
