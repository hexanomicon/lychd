"""In-memory delegation store and runtime coordinator for the first core slice."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from uuid import uuid4

from lychd.domain.delegation.models import (
    LEGAL_DELEGATED_AGENT_TRANSITIONS,
    TERMINAL_DELEGATED_AGENT_STATUSES,
    DelegatedAgentEvent,
    DelegatedAgentEventKind,
    DelegatedAgentJob,
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentRequest,
    DelegatedAgentResult,
)
from lychd.domain.delegation.ports import DelegatedAgentJobStore, DelegatedAgentRuntime

__all__ = [
    "DelegatedAgentCoordinator",
    "DelegatedAgentIdempotencyConflictError",
    "IllegalDelegatedAgentTransitionError",
    "InMemoryDelegatedAgentJobStore",
    "UnknownDelegatedAgentJobError",
    "UnknownDelegatedAgentRuntimeError",
]


class UnknownDelegatedAgentRuntimeError(LookupError):
    """Raised when a request names no registered delegated-agent adapter."""


class UnknownDelegatedAgentJobError(LookupError):
    """Raised when a coordinator operation targets no tracked job."""


class DelegatedAgentIdempotencyConflictError(RuntimeError):
    """Raised when one idempotency id is replayed with different request content."""


class IllegalDelegatedAgentTransitionError(RuntimeError):
    """Raised when a job attempts to leave the declared lifecycle."""


@dataclass
class _JobRow:
    request: DelegatedAgentRequest
    ref: DelegatedAgentJobRef
    status: DelegatedAgentJobStatus = DelegatedAgentJobStatus.QUEUED
    result: DelegatedAgentResult | None = None
    events: list[DelegatedAgentEvent] = field(default_factory=list)

    def view(self) -> DelegatedAgentJob:
        return DelegatedAgentJob(
            request=self.request,
            ref=self.ref,
            status=self.status,
            result=self.result,
            events=tuple(self.events),
        )

    def append(self, kind: DelegatedAgentEventKind) -> None:
        self.events.append(
            DelegatedAgentEvent(
                job_id=self.ref.job_id,
                request_id=self.request.request_id,
                seq=len(self.events),
                kind=kind,
                status=self.status,
            )
        )


class InMemoryDelegatedAgentJobStore:
    """Loop-local, DB-free job store with atomic idempotency and terminal adoption."""

    def __init__(self) -> None:
        """Create an empty process-local delegation ledger."""
        self._rows: dict[str, _JobRow] = {}
        self._request_jobs: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        request: DelegatedAgentRequest,
        ref: DelegatedAgentJobRef,
    ) -> tuple[DelegatedAgentJob, bool]:
        """Create exactly once by request id and reject semantic id reuse."""
        async with self._lock:
            existing_id = self._request_jobs.get(request.request_id)
            if existing_id is not None:
                row = self._rows[existing_id]
                if row.request != request:
                    msg = f"Delegated request id {request.request_id!r} was reused with different content."
                    raise DelegatedAgentIdempotencyConflictError(msg)
                return row.view(), False
            if ref.job_id in self._rows:
                msg = f"Delegated runtime job id {ref.job_id!r} is already tracked."
                raise DelegatedAgentIdempotencyConflictError(msg)
            _validate_ref(request, ref)
            row = _JobRow(request=request, ref=ref)
            row.append(DelegatedAgentEventKind.STATUS_CHANGED)
            self._rows[ref.job_id] = row
            self._request_jobs[request.request_id] = ref.job_id
            return row.view(), True

    async def get(self, job_id: str) -> DelegatedAgentJob | None:
        async with self._lock:
            row = self._rows.get(job_id)
            return row.view() if row is not None else None

    async def get_by_request(self, request_id: str) -> DelegatedAgentJob | None:
        async with self._lock:
            job_id = self._request_jobs.get(request_id)
            row = self._rows.get(job_id) if job_id is not None else None
            return row.view() if row is not None else None

    async def jobs_for_run(self, run_id: str) -> tuple[DelegatedAgentJob, ...]:
        """Return jobs correlated to one canonical LychD run in creation order."""
        async with self._lock:
            return tuple(row.view() for row in self._rows.values() if row.request.run_id == run_id)

    async def transition(
        self,
        job_id: str,
        status: DelegatedAgentJobStatus,
    ) -> tuple[DelegatedAgentJob, bool]:
        """Advance one legal lifecycle edge and retain its semantic event."""
        if status in TERMINAL_DELEGATED_AGENT_STATUSES:
            msg = f"Terminal delegated-agent status {status.value!r} requires adopt() or cancel() evidence."
            raise IllegalDelegatedAgentTransitionError(msg)
        async with self._lock:
            row = self._require(job_id)
            if row.status is status:
                return row.view(), False
            if status not in LEGAL_DELEGATED_AGENT_TRANSITIONS[row.status]:
                msg = f"Illegal delegated-agent transition for {job_id}: {row.status} → {status}"
                raise IllegalDelegatedAgentTransitionError(msg)
            row.status = status
            row.append(DelegatedAgentEventKind.STATUS_CHANGED)
            return row.view(), True

    async def adopt(self, job_id: str, result: DelegatedAgentResult) -> tuple[DelegatedAgentJob, bool]:
        """Adopt the first terminal result; duplicate or late results are inert."""
        async with self._lock:
            row = self._require(job_id)
            if result.job_id != job_id:
                msg = f"Result for job {result.job_id!r} cannot settle tracked job {job_id!r}."
                raise ValueError(msg)
            if row.status in TERMINAL_DELEGATED_AGENT_STATUSES:
                return row.view(), False
            if result.status not in LEGAL_DELEGATED_AGENT_TRANSITIONS[row.status]:
                msg = f"Illegal delegated-agent transition for {job_id}: {row.status} → {result.status}"
                raise IllegalDelegatedAgentTransitionError(msg)
            row.result = result
            row.status = result.status
            row.append(DelegatedAgentEventKind.RESULT_ADOPTED)
            return row.view(), True

    async def cancel(self, job_id: str) -> tuple[DelegatedAgentJob, bool]:
        """Record terminal cancellation once."""
        async with self._lock:
            row = self._require(job_id)
            if row.status in TERMINAL_DELEGATED_AGENT_STATUSES and row.status is not DelegatedAgentJobStatus.LOST:
                return row.view(), False
            if DelegatedAgentJobStatus.CANCELLED not in LEGAL_DELEGATED_AGENT_TRANSITIONS[row.status]:
                msg = f"Illegal delegated-agent transition for {job_id}: {row.status} → cancelled"
                raise IllegalDelegatedAgentTransitionError(msg)
            row.status = DelegatedAgentJobStatus.CANCELLED
            row.result = DelegatedAgentResult(
                job_id=job_id,
                status=DelegatedAgentJobStatus.CANCELLED,
            )
            row.append(DelegatedAgentEventKind.STATUS_CHANGED)
            return row.view(), True

    async def events(self, job_id: str, *, after_seq: int = -1) -> tuple[DelegatedAgentEvent, ...]:
        async with self._lock:
            return tuple(event for event in self._require(job_id).events if event.seq > after_seq)

    def _require(self, job_id: str) -> _JobRow:
        try:
            return self._rows[job_id]
        except KeyError as exc:
            msg = f"Unknown delegated-agent job: {job_id}"
            raise UnknownDelegatedAgentJobError(msg) from exc


class DelegatedAgentCoordinator:
    """Idempotent facade over named delegated runtimes and one job store."""

    def __init__(
        self,
        *,
        runtimes: Mapping[str, DelegatedAgentRuntime],
        store: DelegatedAgentJobStore,
    ) -> None:
        """Bind named runtime adapters to one authoritative job store."""
        self._runtimes = dict(runtimes)
        self._store = store
        self._locks: dict[str, asyncio.Lock] = {}

    async def submit(self, request: DelegatedAgentRequest) -> DelegatedAgentJobRef:
        """Start at most one external job for one stable request id."""
        async with self._lock_for(f"request:{request.request_id}"):
            existing = await self._store.get_by_request(request.request_id)
            if existing is not None:
                if existing.request != request:
                    msg = f"Delegated request id {request.request_id!r} was reused with different content."
                    raise DelegatedAgentIdempotencyConflictError(msg)
                return existing.ref
            ref = DelegatedAgentJobRef(
                job_id=str(uuid4()),
                request_id=request.request_id,
                run_id=request.run_id,
                runtime=request.runtime,
                profile=request.profile,
            )
            job, created = await self._store.create(request, ref)
            if not created:
                return job.ref
            ref = job.ref
            try:
                runtime = self._runtime(request.runtime)
                await self._store.transition(ref.job_id, DelegatedAgentJobStatus.ADMITTED)
                await self._store.transition(ref.job_id, DelegatedAgentJobStatus.PREPARING)
                await runtime.start(request, ref)
            except asyncio.CancelledError:
                await self._store.adopt(
                    ref.job_id,
                    DelegatedAgentResult(
                        job_id=ref.job_id,
                        status=DelegatedAgentJobStatus.LOST,
                        error="submission was cancelled with an indeterminate runtime outcome",
                    ),
                )
                raise
            except Exception as exc:
                await self._store.adopt(
                    ref.job_id,
                    DelegatedAgentResult(
                        job_id=ref.job_id,
                        status=DelegatedAgentJobStatus.FAILED,
                        error=str(exc) or type(exc).__name__,
                    ),
                )
                raise
            await self._store.transition(ref.job_id, DelegatedAgentJobStatus.RUNNING)
            return job.ref

    async def get(self, job_id: str) -> DelegatedAgentJob | None:
        return await self._store.get(job_id)

    async def jobs_for_run(self, run_id: str) -> tuple[DelegatedAgentJob, ...]:
        """Return every delegated job correlated to one LychD run."""
        return await self._store.jobs_for_run(run_id)

    async def refresh(self, job_id: str) -> DelegatedAgentJob:
        """Poll an active job and adopt its result at most once."""
        async with self._lock_for(f"job:{job_id}"):
            job = await self._require(job_id)
            if job.status in TERMINAL_DELEGATED_AGENT_STATUSES:
                return job
            result = await self._runtime(job.ref.runtime).poll(job.ref)
            if result is None:
                return job
            settled, _adopted = await self._store.adopt(job_id, result)
            return settled

    async def adopt(self, job_id: str, result: DelegatedAgentResult) -> bool:
        """Adopt one externally delivered terminal result exactly once."""
        async with self._lock_for(f"job:{job_id}"):
            await self._require(job_id)
            _job, adopted = await self._store.adopt(job_id, result)
            return adopted

    async def cancel(self, job_id: str) -> bool:
        """Contain a possibly live runtime job and record terminal cancellation."""
        async with self._lock_for(f"job:{job_id}"):
            job = await self._require(job_id)
            if job.status in TERMINAL_DELEGATED_AGENT_STATUSES and job.status is not DelegatedAgentJobStatus.LOST:
                return False
            await self._runtime(job.ref.runtime).cancel(job.ref)
            _job, changed = await self._store.cancel(job_id)
            return changed

    async def events(self, job_id: str, *, after_seq: int = -1) -> tuple[DelegatedAgentEvent, ...]:
        return await self._store.events(job_id, after_seq=after_seq)

    async def _require(self, job_id: str) -> DelegatedAgentJob:
        job = await self._store.get(job_id)
        if job is None:
            msg = f"Unknown delegated-agent job: {job_id}"
            raise UnknownDelegatedAgentJobError(msg)
        return job

    def _runtime(self, name: str) -> DelegatedAgentRuntime:
        try:
            return self._runtimes[name]
        except KeyError as exc:
            msg = f"Unknown delegated-agent runtime {name!r}."
            raise UnknownDelegatedAgentRuntimeError(msg) from exc

    def _lock_for(self, key: str) -> asyncio.Lock:
        """Return a loop-local lock without serializing unrelated delegated jobs."""
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock


def _validate_ref(request: DelegatedAgentRequest, ref: DelegatedAgentJobRef) -> None:
    expected = (request.request_id, request.run_id, request.runtime, request.profile)
    observed = (ref.request_id, ref.run_id, ref.runtime, ref.profile)
    if observed != expected:
        msg = "Delegated runtime returned a job reference that does not match its request identity."
        raise ValueError(msg)
