"""PostgreSQL implementation of the delegated-agent job-store port."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from lychd.domain.delegation.models import (
    LEGAL_DELEGATED_AGENT_TRANSITIONS,
    TERMINAL_DELEGATED_AGENT_STATUSES,
    DelegatedAgentEvent,
    DelegatedAgentEventKind,
    DelegatedAgentJob,
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentProfile,
    DelegatedAgentRequest,
    DelegatedAgentResult,
)
from lychd.domain.delegation.services import (
    DelegatedAgentIdempotencyConflictError,
    IllegalDelegatedAgentTransitionError,
    UnknownDelegatedAgentJobError,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from lychd.db.models.delegation import DelegatedAgentJobRecord

__all__ = ["DbDelegatedAgentJobStore"]


class DbDelegatedAgentJobStore:
    """Durable, transaction-safe delegated job state and semantic events."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Bind the store to the process database session factory."""
        self._session_factory = session_factory

    async def create(
        self,
        request: DelegatedAgentRequest,
        ref: DelegatedAgentJobRef,
    ) -> tuple[DelegatedAgentJob, bool]:
        """Insert once by request id, preserving the first LychD-owned job identity."""
        from lychd.db.models import DelegatedAgentJobRecord

        _validate_ref(request, ref)
        values = {
            "job_id": ref.job_id,
            "request_id": request.request_id,
            "run_id": UUID(request.run_id),
            "runtime": request.runtime,
            "profile": request.profile,
            "status": DelegatedAgentJobStatus.QUEUED.value,
            "request": request.model_dump(mode="json"),
            "result": None,
        }
        async with self._session_factory() as session, session.begin():
            row_id = await session.scalar(
                insert(DelegatedAgentJobRecord)
                .values(**values)
                .on_conflict_do_nothing(index_elements=[DelegatedAgentJobRecord.request_id])
                .returning(DelegatedAgentJobRecord.id)
            )
            created = row_id is not None
            row = await session.scalar(
                select(DelegatedAgentJobRecord)
                .where(DelegatedAgentJobRecord.request_id == request.request_id)
                .with_for_update()
            )
            if row is None:  # pragma: no cover - insert/read are one transaction
                msg = "Delegated job insert completed without a readable row."
                raise RuntimeError(msg)
            existing_request = DelegatedAgentRequest.model_validate(row.request)
            if existing_request != request:
                msg = f"Delegated request id {request.request_id!r} was reused with different content."
                raise DelegatedAgentIdempotencyConflictError(msg)
            if created:
                await self._append(
                    session,
                    row,
                    DelegatedAgentEventKind.STATUS_CHANGED,
                    DelegatedAgentJobStatus.QUEUED,
                )
            return await self._view(session, row), created

    async def get(self, job_id: str) -> DelegatedAgentJob | None:
        from lychd.db.models import DelegatedAgentJobRecord

        async with self._session_factory() as session:
            row = await session.scalar(select(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.job_id == job_id))
            return await self._view(session, row) if row is not None else None

    async def get_by_request(self, request_id: str) -> DelegatedAgentJob | None:
        from lychd.db.models import DelegatedAgentJobRecord

        async with self._session_factory() as session:
            row = await session.scalar(
                select(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.request_id == request_id)
            )
            return await self._view(session, row) if row is not None else None

    async def jobs_for_run(
        self,
        run_id: str,
        *,
        limit: int | None = None,
        event_limit: int | None = None,
    ) -> tuple[DelegatedAgentJob, ...]:
        """Return newest bounded jobs and event suffixes in creation order."""
        from lychd.db.models import DelegatedAgentJobRecord

        if limit is not None and limit < 0:
            msg = "Delegated job limit must be non-negative."
            raise ValueError(msg)
        if event_limit is not None and event_limit < 0:
            msg = "Delegated event limit must be non-negative."
            raise ValueError(msg)
        statement = select(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.run_id == UUID(run_id))
        reverse_rows = limit is not None
        if reverse_rows:
            statement = statement.order_by(
                DelegatedAgentJobRecord.created_at.desc(),
                DelegatedAgentJobRecord.id.desc(),
            ).limit(limit)
        else:
            statement = statement.order_by(
                DelegatedAgentJobRecord.created_at,
                DelegatedAgentJobRecord.id,
            )
        async with self._session_factory() as session:
            rows = list((await session.scalars(statement)).all())
            if reverse_rows:
                rows.reverse()
            return tuple([await self._view(session, row, event_limit=event_limit) for row in rows])

    async def transition(
        self,
        job_id: str,
        status: DelegatedAgentJobStatus,
    ) -> tuple[DelegatedAgentJob, bool]:
        if status in TERMINAL_DELEGATED_AGENT_STATUSES:
            msg = f"Terminal delegated-agent status {status.value!r} requires adopt() or cancel() evidence."
            raise IllegalDelegatedAgentTransitionError(msg)
        async with self._session_factory() as session, session.begin():
            row = await self._require_locked(session, job_id)
            current = DelegatedAgentJobStatus(row.status)
            if current is status:
                return await self._view(session, row), False
            if status not in LEGAL_DELEGATED_AGENT_TRANSITIONS[current]:
                msg = f"Illegal delegated-agent transition for {job_id}: {current} → {status}"
                raise IllegalDelegatedAgentTransitionError(msg)
            row.status = status.value
            await self._append(session, row, DelegatedAgentEventKind.STATUS_CHANGED, status)
            return await self._view(session, row), True

    async def adopt(
        self,
        job_id: str,
        result: DelegatedAgentResult,
    ) -> tuple[DelegatedAgentJob, bool]:
        async with self._session_factory() as session, session.begin():
            row = await self._require_locked(session, job_id)
            current = DelegatedAgentJobStatus(row.status)
            if result.job_id != job_id:
                msg = f"Result for job {result.job_id!r} cannot settle tracked job {job_id!r}."
                raise ValueError(msg)
            if current in TERMINAL_DELEGATED_AGENT_STATUSES:
                return await self._view(session, row), False
            if result.status not in LEGAL_DELEGATED_AGENT_TRANSITIONS[current]:
                msg = f"Illegal delegated-agent transition for {job_id}: {current} → {result.status}"
                raise IllegalDelegatedAgentTransitionError(msg)
            row.status = result.status.value
            row.result = result.model_dump(mode="json")
            await self._append(session, row, DelegatedAgentEventKind.RESULT_ADOPTED, result.status)
            return await self._view(session, row), True

    async def cancel(self, job_id: str) -> tuple[DelegatedAgentJob, bool]:
        """Settle cancellation, including a LOST job with uncertain liveness."""
        async with self._session_factory() as session, session.begin():
            row = await self._require_locked(session, job_id)
            current = DelegatedAgentJobStatus(row.status)
            if current in TERMINAL_DELEGATED_AGENT_STATUSES and current is not DelegatedAgentJobStatus.LOST:
                return await self._view(session, row), False
            if DelegatedAgentJobStatus.CANCELLED not in LEGAL_DELEGATED_AGENT_TRANSITIONS[current]:
                msg = f"Illegal delegated-agent transition for {job_id}: {current} → cancelled"
                raise IllegalDelegatedAgentTransitionError(msg)
            result = DelegatedAgentResult(job_id=job_id, status=DelegatedAgentJobStatus.CANCELLED)
            row.status = result.status.value
            row.result = result.model_dump(mode="json")
            await self._append(
                session,
                row,
                DelegatedAgentEventKind.STATUS_CHANGED,
                result.status,
            )
            return await self._view(session, row), True

    async def events(self, job_id: str, *, after_seq: int = -1) -> tuple[DelegatedAgentEvent, ...]:
        from lychd.db.models import DelegatedAgentEventRecord, DelegatedAgentJobRecord

        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(DelegatedAgentEventRecord)
                    .join(DelegatedAgentJobRecord)
                    .where(
                        DelegatedAgentJobRecord.job_id == job_id,
                        DelegatedAgentEventRecord.seq > after_seq,
                    )
                    .order_by(DelegatedAgentEventRecord.seq)
                )
            ).all()
            if not rows and not await session.scalar(
                select(DelegatedAgentJobRecord.id).where(DelegatedAgentJobRecord.job_id == job_id)
            ):
                msg = f"Unknown delegated-agent job: {job_id}"
                raise UnknownDelegatedAgentJobError(msg)
            return tuple(DelegatedAgentEvent.model_validate(row.payload) for row in rows)

    async def _require_locked(self, session: AsyncSession, job_id: str) -> DelegatedAgentJobRecord:
        from lychd.db.models import DelegatedAgentJobRecord

        row = await session.scalar(
            select(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.job_id == job_id).with_for_update()
        )
        if row is None:
            msg = f"Unknown delegated-agent job: {job_id}"
            raise UnknownDelegatedAgentJobError(msg)
        return row

    @staticmethod
    async def _append(
        session: AsyncSession,
        row: DelegatedAgentJobRecord,
        kind: DelegatedAgentEventKind,
        status: DelegatedAgentJobStatus,
    ) -> None:
        from lychd.db.models import DelegatedAgentEventRecord

        next_seq = await session.scalar(
            select(func.coalesce(func.max(DelegatedAgentEventRecord.seq), -1) + 1).where(
                DelegatedAgentEventRecord.job_record_id == row.id
            )
        )
        event = DelegatedAgentEvent(
            job_id=row.job_id,
            request_id=row.request_id,
            seq=int(next_seq or 0),
            kind=kind,
            status=status,
        )
        session.add(
            DelegatedAgentEventRecord(
                job_record_id=row.id,
                event_id=event.event_id,
                seq=event.seq,
                kind=event.kind.value,
                status=event.status.value,
                payload=event.model_dump(mode="json"),
            )
        )
        await session.flush()

    @staticmethod
    async def _view(
        session: AsyncSession,
        row: DelegatedAgentJobRecord,
        *,
        event_limit: int | None = None,
    ) -> DelegatedAgentJob:
        from lychd.db.models import DelegatedAgentEventRecord

        events: list[DelegatedAgentEventRecord]
        if event_limit == 0:
            events = []
        else:
            statement = select(DelegatedAgentEventRecord).where(DelegatedAgentEventRecord.job_record_id == row.id)
            reverse_events = event_limit is not None
            if reverse_events:
                statement = statement.order_by(DelegatedAgentEventRecord.seq.desc()).limit(event_limit)
            else:
                statement = statement.order_by(DelegatedAgentEventRecord.seq)
            events = list((await session.scalars(statement)).all())
            if reverse_events:
                events.reverse()
        request = DelegatedAgentRequest.model_validate(row.request)
        ref = DelegatedAgentJobRef(
            job_id=row.job_id,
            request_id=row.request_id,
            run_id=str(row.run_id),
            runtime=row.runtime,
            profile=DelegatedAgentProfile(row.profile),
        )
        result = DelegatedAgentResult.model_validate(row.result) if row.result is not None else None
        return DelegatedAgentJob(
            request=request,
            ref=ref,
            status=DelegatedAgentJobStatus(row.status),
            result=result,
            events=tuple(DelegatedAgentEvent.model_validate(event.payload) for event in events),
        )


def _validate_ref(request: DelegatedAgentRequest, ref: DelegatedAgentJobRef) -> None:
    expected = (request.request_id, request.run_id, request.runtime, request.profile)
    observed = (ref.request_id, ref.run_id, ref.runtime, ref.profile)
    if observed != expected:
        msg = "Delegated runtime returned a job reference that does not match its request identity."
        raise ValueError(msg)
