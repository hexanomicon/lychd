"""PostgreSQL mechanical handoff custody, without owner or guest-release authority.

Every mutation locks the permanent AgentJob first, including close before prepare.
Only acknowledged new preparation issues an ephemeral once handle. No read, replay,
failed consumption or replacement adapter can recover that handle from history.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import TYPE_CHECKING, cast
from uuid import uuid4
from weakref import WeakSet

from sqlalchemy import func, select, text

from lychd.db.models.delegated_host import DelegatedHostDispositionRecord
from lychd.db.models.delegation import DelegatedAgentJobRecord
from lychd.domain.delegation.host_disposition import (
    DelegatedHostDispositionSnapshot,
    DelegatedHostIntakeClosure,
    DelegatedHostPolicyIdentity,
    FreshHostPreparation,
    HostDispositionCommitUnknownError,
    HostDispositionConflictError,
    HostDispositionNotEligibleError,
    HostIntakeClosedError,
    HostPreparationNotFreshError,
    build_host_preparation,
    decode_host_preparation,
    revalidate_host_job,
)
from lychd.domain.delegation.models import (
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentProfile,
    DelegatedCliRequestV2,
    decode_delegated_request,
    encode_delegated_request,
)
from lychd.domain.delegation.services import UnknownDelegatedAgentJobError
from lychd.lib.asyncio import complete_under_cancellation

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _conflict() -> HostDispositionConflictError:
    return HostDispositionConflictError("Delegated host retained binding differs.")


def _job_ref(row: DelegatedAgentJobRecord) -> DelegatedAgentJobRef:
    return DelegatedAgentJobRef(
        job_id=row.job_id,
        request_id=row.request_id,
        run_id=str(row.run_id),
        runtime=row.runtime,
        profile=DelegatedAgentProfile(row.profile),
    )


def _canonical_request(document: object) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )


def _current_v2(parent: DelegatedAgentJobRecord) -> tuple[DelegatedCliRequestV2, bytes]:
    """Admit the complete current stored shape without numeric aliases or defaults."""
    request = decode_delegated_request(parent.request)
    if not isinstance(request, DelegatedCliRequestV2):
        raise _conflict()
    encoded = _canonical_request(parent.request)
    if encoded != _canonical_request(encode_delegated_request(request)):
        raise _conflict()
    return request, encoded


def _snapshot(parent: DelegatedAgentJobRecord, row: DelegatedHostDispositionRecord) -> DelegatedHostDispositionSnapshot:
    try:
        job = _job_ref(parent)
        preparation = decode_host_preparation(row.preparation_bytes) if row.preparation_bytes is not None else None
        if preparation is not None:
            _request, current_bytes = _current_v2(parent)
            if (
                preparation.job != job
                or preparation.digest != row.preparation_digest
                or _canonical_request(encode_delegated_request(preparation.request)) != current_bytes
            ):
                raise _conflict()
        if (
            (preparation is None) != (row.preparation_digest is None)
            or (preparation is None) != (row.prepared_at is None)
            or (row.dispatch_id is None) != (row.dispatch_consumed_at is None)
            or (row.dispatch_id is not None and preparation is None)
            or (preparation is None and row.intake_closed_at is None)
        ):
            raise _conflict()
        return DelegatedHostDispositionSnapshot(
            job=job,
            preparation=preparation,
            prepared_at=row.prepared_at,
            dispatch_id=row.dispatch_id,
            dispatch_consumed_at=row.dispatch_consumed_at,
            intake_closed_at=row.intake_closed_at,
        )
    except (ValueError, TypeError, AttributeError) as error:
        raise _conflict() from error


async def _commit(session: AsyncSession) -> None:
    try:
        await session.commit()
    except asyncio.CancelledError:
        with contextlib.suppress(Exception):
            await complete_under_cancellation(session.rollback())
        raise
    except Exception as error:
        with contextlib.suppress(Exception):
            await session.rollback()
        msg = "Delegated host commit acknowledgement is unavailable."
        raise HostDispositionCommitUnknownError(msg) from error


class DbDelegatedHostDispositionStore:
    """One table and four mechanical operations; no runtime calls or release permits."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Keep once issuance local to this exact adapter instance."""
        self._factory = session_factory
        self._fresh: WeakSet[FreshHostPreparation] = WeakSet()

    @staticmethod
    async def _parent(session: AsyncSession, job: DelegatedAgentJobRef, *, lock: bool) -> DelegatedAgentJobRecord:
        try:
            expected = revalidate_host_job(job)
        except (ValueError, TypeError, AttributeError) as error:
            raise _conflict() from error
        statement = select(DelegatedAgentJobRecord).where(DelegatedAgentJobRecord.job_id == expected.job_id)
        if lock:
            statement = statement.with_for_update()
        row = await session.scalar(statement)
        if row is None:
            msg = "Delegated host AgentJob is unavailable."
            raise UnknownDelegatedAgentJobError(msg)
        try:
            if _job_ref(row) != expected:
                raise _conflict()
        except (ValueError, TypeError, AttributeError) as error:
            raise _conflict() from error
        return row

    @staticmethod
    async def _row(session: AsyncSession, parent: DelegatedAgentJobRecord) -> DelegatedHostDispositionRecord | None:
        return await session.scalar(
            select(DelegatedHostDispositionRecord).where(DelegatedHostDispositionRecord.job_record_id == parent.id)
        )

    async def prepare(
        self,
        job: DelegatedAgentJobRef,
        *,
        policy: DelegatedHostPolicyIdentity,
        executor_id: str,
        executor_generation: int,
    ) -> FreshHostPreparation | DelegatedHostDispositionSnapshot:
        """Retain actual V2 intent once; exact replay never reissues a once handle."""
        async with self._factory() as session:
            parent = await self._parent(session, job, lock=True)
            try:
                request, _current_bytes = _current_v2(parent)
                preparation = build_host_preparation(
                    _job_ref(parent),
                    request,
                    policy=policy,
                    executor_id=executor_id,
                    executor_generation=executor_generation,
                )
                encoded = preparation.canonical_bytes()
            except (ValueError, TypeError, AttributeError) as error:
                raise _conflict() from error
            row = await self._row(session, parent)
            if row is not None:
                snapshot = _snapshot(parent, row)
                if snapshot.preparation is None:
                    msg = "Delegated host intake was closed before preparation."
                    raise HostIntakeClosedError(msg)
                if row.preparation_bytes != encoded:
                    raise _conflict()
                return snapshot
            self._require_preparing(parent)
            now = cast("datetime", await session.scalar(select(func.clock_timestamp())))
            row = DelegatedHostDispositionRecord(
                job_record_id=parent.id,
                preparation_bytes=encoded,
                preparation_digest=preparation.digest,
                prepared_at=now,
            )
            session.add(row)
            await session.flush()
            await _commit(session)
            fresh = FreshHostPreparation(preparation)
            self._fresh.add(fresh)
            return fresh

    async def consume_dispatch(self, fresh: FreshHostPreparation) -> DelegatedHostDispositionSnapshot:
        """Retire local issuance before I/O, then consume the durable opportunity once."""
        if type(fresh) is not FreshHostPreparation or fresh not in self._fresh:
            msg = "Delegated host preparation is not freshly issued by this adapter."
            raise HostPreparationNotFreshError(msg)
        self._fresh.remove(fresh)
        try:
            encoded = fresh.preparation.canonical_bytes()
        except (ValueError, TypeError, AttributeError) as error:
            raise _conflict() from error
        async with self._factory() as session:
            parent = await self._parent(session, fresh.preparation.job, lock=True)
            row = await self._row(session, parent)
            if row is None:
                raise _conflict()
            snapshot = _snapshot(parent, row)
            if row.preparation_bytes != encoded:
                raise _conflict()
            if row.intake_closed_at is not None:
                msg = "Delegated host intake is logically closed."
                raise HostIntakeClosedError(msg)
            self._require_preparing(parent)
            if snapshot.dispatch_id is not None:
                raise _conflict()
            row.dispatch_id = uuid4()
            row.dispatch_consumed_at = cast("datetime", await session.scalar(select(func.clock_timestamp())))
            await session.flush()
            snapshot = _snapshot(parent, row)
            await _commit(session)
            return snapshot

    async def close_intake(self, job: DelegatedAgentJobRef) -> DelegatedHostIntakeClosure:
        """Persist logical closure even before preparation or with undecodable intent."""
        async with self._factory() as session:
            parent = await self._parent(session, job, lock=True)
            row = await self._row(session, parent)
            if row is None:
                row = DelegatedHostDispositionRecord(job_record_id=parent.id)
                session.add(row)
            if row.intake_closed_at is None:
                row.intake_closed_at = cast("datetime", await session.scalar(select(func.clock_timestamp())))
            closure = DelegatedHostIntakeClosure(_job_ref(parent), row.intake_closed_at)
            await session.flush()
            await _commit(session)
            return closure

    async def get(self, job: DelegatedAgentJobRef) -> DelegatedHostDispositionSnapshot | None:
        """Read one consistent detached snapshot; never recover a once handle."""
        async with self._factory() as session, session.begin():
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            parent = await self._parent(session, job, lock=False)
            row = await self._row(session, parent)
            return _snapshot(parent, row) if row is not None else None

    @staticmethod
    def _require_preparing(parent: DelegatedAgentJobRecord) -> None:
        if parent.status != DelegatedAgentJobStatus.PREPARING.value:
            msg = "Delegated host fresh handoff requires a PREPARING AgentJob."
            raise HostDispositionNotEligibleError(msg)
