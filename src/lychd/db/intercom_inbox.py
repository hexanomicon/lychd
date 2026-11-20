"""Receiver-owned PostgreSQL intake for one explicitly enrolled public-text pair."""

from __future__ import annotations

import hashlib
import re
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import delete, func, or_, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from lychd.db.models.intercom_inbox import IntercomInboxAttempt, IntercomInboxTask
from lychd.domain.intercom.transport import MAX_OPERATION_SECONDS, TaskMethod

MAX_TASKS = 64
MAX_LIVE_ATTEMPTS = 128
MAX_TEXT_BYTES = 8192
MAX_RESULT_BYTES = 4096
MAX_LIFETIME_SECONDS = 86400
_DIGEST = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[!-~]{1,128}")
_OPEN = ("submitted", "working")
_WIRE = {
    "submitted": "TASK_STATE_SUBMITTED",
    "working": "TASK_STATE_WORKING",
    "completed": "TASK_STATE_COMPLETED",
    "rejected": "TASK_STATE_REJECTED",
    "canceled": "TASK_STATE_CANCELED",
    "expired": "TASK_STATE_FAILED",
}
_DECISIONS = {_WIRE[name]: name for name in ("working", "completed", "rejected")}


class InboxError(ValueError):
    """Content-free receiver outcome."""

    def __init__(self, code: str) -> None:
        """Project only a local finite reason."""
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class Receipt:
    """Receiver facts, with any explicit operator-authored public reply held as data."""

    task_id: UUID
    local_id: str
    state: str
    disposition: str
    result: str | None = field(repr=False)
    expires_at: datetime

    @classmethod
    def from_row(cls, row: IntercomInboxTask) -> Receipt:
        return cls(row.id, row.local_id, _WIRE[row.state], row.state, row.result, row.expires_at)


def _identifier(value: str | None) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        msg = "input"
        raise InboxError(msg)
    return value


def _uuid(value: UUID | str | None) -> UUID:
    try:
        return value if isinstance(value, UUID) else UUID(_identifier(value))
    except ValueError:
        msg = "unknown-task"
        raise InboxError(msg) from None


def _text(value: str | None, limit: int) -> str:
    if not isinstance(value, str) or not 0 < len(value) <= limit or "\x00" in value:
        msg = "text"
        raise InboxError(msg)
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        msg = "text"
        raise InboxError(msg) from None
    if len(encoded) > limit:
        msg = "text"
        raise InboxError(msg)
    return value


def _digest(value: object) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        msg = "input"
        raise InboxError(msg)
    return value


class ReceiverInbox:
    """Each operation serializes on a stable pair, shared by replacement processes and policies."""

    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        *,
        receiver: object,
        peer: object,
        task_schema: str,
        policy: str,
        lifetime_seconds: int = MAX_LIFETIME_SECONDS,
    ) -> None:
        """Bind the authenticated pair and reviewed task class to independently supplied live authority."""
        if not isinstance(receiver, UUID) or not isinstance(peer, UUID) or receiver == peer:
            msg = "pair"
            raise InboxError(msg)
        if type(lifetime_seconds) is not int or not 1 <= lifetime_seconds <= MAX_LIFETIME_SECONDS:
            msg = "lifetime"
            raise InboxError(msg)
        self._factory = factory
        self._receiver = receiver
        self._peer = peer
        self._schema = _identifier(task_schema)
        self._policy = _digest(policy)
        self._lifetime = timedelta(seconds=lifetime_seconds)
        digest = hashlib.sha256(b"lychd:intercom:inbox:1" + receiver.bytes + peer.bytes).digest()
        self._lock = int.from_bytes(digest[:8], "big", signed=True)

    def _pair(self, model: type[IntercomInboxTask | IntercomInboxAttempt]) -> ColumnElement[bool]:
        return (model.receiver == self._receiver) & (model.peer == self._peer)

    def _owned(self) -> ColumnElement[bool]:
        return (
            self._pair(IntercomInboxTask)
            & (IntercomInboxTask.task_schema == self._schema)
            & (IntercomInboxTask.policy == self._policy)
        )

    @asynccontextmanager
    async def _transaction(
        self, authorize: Callable[[], None], *, before_commit: Callable[[datetime], None] | None = None
    ) -> AsyncGenerator[tuple[AsyncSession, datetime]]:
        authorize()
        async with self._factory() as session:
            try:
                await session.execute(text("SET LOCAL lock_timeout = '2s'"))
                await session.execute(text("SET LOCAL statement_timeout = '5s'"))
                await session.execute(select(func.pg_advisory_xact_lock(self._lock)))
                now = cast("datetime", await session.scalar(select(func.clock_timestamp())))
                authorize()
                await session.execute(
                    update(IntercomInboxTask)
                    .where(self._owned(), IntercomInboxTask.state.in_(_OPEN), IntercomInboxTask.expires_at <= now)
                    .values(state="expired")
                )
                yield session, now
                await session.flush()
                if before_commit is not None:
                    before_commit(cast("datetime", await session.scalar(select(func.clock_timestamp()))))
                authorize()
            except SQLAlchemyError:
                msg = "storage"
                raise InboxError(msg) from None
            try:
                await session.commit()
            except SQLAlchemyError:
                msg = "commit-unknown"
                raise InboxError(msg) from None
        authorize()

    async def _spend(
        self, session: AsyncSession, now: datetime, attempt: str, nonce: str, signature_expires: int
    ) -> None:
        if type(signature_expires) is not int or not (
            now.timestamp() < signature_expires <= now.timestamp() + MAX_OPERATION_SECONDS
        ):
            msg = "signature-time"
            raise InboxError(msg)
        pair = self._pair(IntercomInboxAttempt)
        await session.execute(delete(IntercomInboxAttempt).where(pair, IntercomInboxAttempt.expires_at <= now))
        duplicate = (IntercomInboxAttempt.attempt == attempt) | (IntercomInboxAttempt.nonce == nonce)
        if await session.scalar(select(IntercomInboxAttempt.id).where(pair, duplicate).limit(1)) is not None:
            msg = "replay"
            raise InboxError(msg)
        count = await session.scalar(select(func.count()).select_from(IntercomInboxAttempt).where(pair))
        if count is None or count >= MAX_LIVE_ATTEMPTS:
            msg = "attempt-capacity"
            raise InboxError(msg)
        session.add(
            IntercomInboxAttempt(
                receiver=self._receiver,
                peer=self._peer,
                attempt=attempt,
                nonce=nonce,
                expires_at=datetime.fromtimestamp(signature_expires, UTC),
            )
        )

    async def _submit(
        self,
        session: AsyncSession,
        now: datetime,
        local_id: str,
        message_id: str,
        body_digest: str,
        request_text: str,
        admit_new: Callable[[datetime, datetime], None] | None,
    ) -> tuple[IntercomInboxTask, bool]:
        pair = self._pair(IntercomInboxTask)
        existing = await session.scalars(
            select(IntercomInboxTask).where(
                pair, or_(IntercomInboxTask.local_id == local_id, IntercomInboxTask.message_id == message_id)
            )
        )
        matches = existing.all()
        if matches:
            row = matches[0]
            retained = (row.local_id, row.message_id, row.body_digest, row.request_text, row.task_schema, row.policy)
            incoming = (local_id, message_id, body_digest, request_text, self._schema, self._policy)
            if len(matches) != 1 or retained != incoming:
                msg = "conflict"
                raise InboxError(msg)
            return row, False
        count = await session.scalar(select(func.count()).select_from(IntercomInboxTask).where(pair))
        if count is None or count >= MAX_TASKS:
            msg = "capacity"
            raise InboxError(msg)
        expires_at = now + self._lifetime
        if admit_new is not None:
            admit_new(now, expires_at)
        row = IntercomInboxTask(
            id=uuid4(),
            receiver=self._receiver,
            peer=self._peer,
            policy=self._policy,
            task_schema=self._schema,
            local_id=local_id,
            message_id=message_id,
            body_digest=body_digest,
            request_text=request_text,
            admitted_at=now,
            expires_at=expires_at,
            state="submitted",
            result=None,
        )
        session.add(row)
        return row, True

    async def _load(self, session: AsyncSession, *criteria: ColumnElement[bool]) -> IntercomInboxTask:
        row = await session.scalar(select(IntercomInboxTask).where(self._owned(), *criteria))
        if row is None:
            msg = "unknown-task"
            raise InboxError(msg)
        return row

    async def _wire_operation(
        self,
        session: AsyncSession,
        now: datetime,
        *,
        method: TaskMethod,
        local_id: str,
        body_digest: str,
        message_id: str | None,
        text: str | None,
        task_id: UUID | str | None,
        admit_new: Callable[[datetime, datetime], None] | None,
    ) -> tuple[Receipt, bool, datetime | None]:
        if method == "SendMessage" and task_id is None:
            row, admitted = await self._submit(
                session, now, local_id, _identifier(message_id), body_digest, _text(text, MAX_TEXT_BYTES), admit_new
            )
            return Receipt.from_row(row), admitted, None
        if method not in {"GetTask", "CancelTask"} or message_id is not None or text is not None:
            msg = "method"
            raise InboxError(msg)
        row = await self._load(session, IntercomInboxTask.id == _uuid(task_id), IntercomInboxTask.local_id == local_id)
        if method == "CancelTask" and row.state in _OPEN:
            row.state = "canceled"
            return Receipt.from_row(row), False, row.expires_at
        return Receipt.from_row(row), False, None

    async def receive(  # noqa: C901 - Wire admission and commit-time fences settle as one transaction.
        self,
        *,
        method: TaskMethod,
        local_id: str,
        body_digest: str,
        attempt: str,
        nonce: str,
        signature_expires: int,
        authorize: Callable[[], None],
        message_id: str | None = None,
        text: str | None = None,
        task_id: UUID | str | None = None,
        admit_new: Callable[[datetime, datetime], None] | None = None,
    ) -> Receipt:
        """Admit verified leaves and the digest of their exact signed bytes under the caller's current wire check."""
        _identifier(local_id)
        _identifier(attempt)
        _identifier(nonce)
        _digest(body_digest)

        def wire_current() -> None:
            authorize()
            if type(signature_expires) is not int or datetime.now(UTC).timestamp() >= signature_expires:
                msg = "signature-time"
                raise InboxError(msg)

        refusal: InboxError | None = None
        receipt: Receipt | None = None
        admitted = False
        cancellation_deadline: datetime | None = None

        def check_reply_deadline(now: datetime) -> None:
            nonlocal refusal
            if receipt is not None and receipt.result is not None and now >= receipt.expires_at:
                refusal = InboxError("expired")

        def check_before_commit(now: datetime) -> None:
            check_reply_deadline(now)
            if cancellation_deadline is not None and now >= cancellation_deadline:
                # The cancellation and physical wrapper both roll back at the task's deadline.
                msg = "cancellation-aborted"
                raise InboxError(msg)
            if admitted:
                if receipt is None or receipt.expires_at <= now:
                    msg = "intake-aborted"
                    raise InboxError(msg)
                if admit_new is not None:
                    try:
                        admit_new(now, receipt.expires_at)
                    except InboxError:
                        # The uncommitted task and its replay fence roll back together. No signed refusal is valid.
                        msg = "intake-aborted"
                        raise InboxError(msg) from None

        async with self._transaction(wire_current, before_commit=check_before_commit) as (session, now):
            await self._spend(session, now, attempt, nonce, signature_expires)
            try:
                receipt, admitted, cancellation_deadline = await self._wire_operation(
                    session,
                    now,
                    method=method,
                    local_id=local_id,
                    body_digest=body_digest,
                    message_id=message_id,
                    text=text,
                    task_id=task_id,
                    admit_new=admit_new,
                )
            except InboxError as exc:
                # A freshly authenticated wrapper remains spent even when the semantic operation is refused.
                refusal = exc
        check_reply_deadline(datetime.now(UTC))
        if refusal is not None:
            raise refusal
        if receipt is None:
            msg = "storage"
            raise InboxError(msg)
        return receipt

    async def pending(self, *, authorize: Callable[[], None]) -> tuple[Receipt, ...]:
        """List only this pairing's reviewable work, without request or result text."""
        async with self._transaction(authorize) as (session, _):
            rows = await session.scalars(
                select(IntercomInboxTask)
                .where(self._owned(), IntercomInboxTask.state.in_(_OPEN))
                .order_by(IntercomInboxTask.admitted_at, IntercomInboxTask.id)
                .limit(MAX_TASKS)
            )
            return tuple(Receipt.from_row(row) for row in rows)

    async def find(self, *, local_id: str, authorize: Callable[[], None]) -> Receipt:
        """Look up a sender identity for local operator reconciliation after a lost acknowledgement."""
        async with self._transaction(authorize) as (session, _):
            row = await self._load(session, IntercomInboxTask.local_id == _identifier(local_id))
            return Receipt.from_row(row)

    async def review(self, *, task_id: UUID, authorize: Callable[[], None]) -> tuple[Receipt, str]:
        """Read the bounded foreign brief locally as inert text."""
        async with self._transaction(authorize) as (session, _):
            row = await self._load(session, IntercomInboxTask.id == task_id)
            return Receipt.from_row(row), row.request_text

    async def decide(
        self,
        *,
        task_id: UUID,
        state: str,
        authorize: Callable[[], None],
        result: str | None = None,
        check_start: Callable[[str, datetime], None] | None = None,
    ) -> Receipt:
        """Claim a submitted brief, refuse it, or seal the working task's manually approved public result."""
        decision = _DECISIONS.get(state)
        if not decision or (decision != "completed" and result is not None):
            msg = "decision"
            raise InboxError(msg)
        if decision == "completed":
            result = _text(result, MAX_RESULT_BYTES)
        deadline: datetime | None = None
        first_start: str | None = None

        def check_decision_deadline(now: datetime) -> None:
            if deadline is not None and now >= deadline:
                msg = "expired"
                raise InboxError(msg)
            if check_start is not None and first_start is not None:
                check_start(first_start, now)

        async with self._transaction(authorize, before_commit=check_decision_deadline) as (session, now):
            row = await self._load(session, IntercomInboxTask.id == task_id)
            if (row.state, row.result) != (decision, result):
                if row.state not in _OPEN or (decision == "completed" and row.state != "working"):
                    msg = "transition"
                    raise InboxError(msg)
                deadline = row.expires_at
                if decision == "working":
                    if check_start is None:
                        msg = "start-policy"
                        raise InboxError(msg)
                    first_start = row.request_text
                    check_decision_deadline(now)
                row.state = decision
                row.result = result
            return Receipt.from_row(row)
