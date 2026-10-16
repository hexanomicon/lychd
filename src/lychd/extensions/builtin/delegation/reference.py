"""Deterministic, no-network runtime for the Core-owned ``delegated_rite`` Pattern."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from lychd.domain.delegation.models import (
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentRequest,
    DelegatedAgentResult,
    DelegatedRequest,
    bound_result_text,
)


@dataclass(frozen=True, slots=True)
class _ReferenceJob:
    request: DelegatedRequest
    ref: DelegatedAgentJobRef
    result: DelegatedAgentResult


class ReferenceDelegatedAgentRuntime:
    """No-effect adapter retaining projections only until durable settlement."""

    name = "reference"

    def __init__(self) -> None:
        """Create an empty process-local reference runtime."""
        self._jobs: dict[str, _ReferenceJob] = {}
        self._lock = asyncio.Lock()

    async def start(self, request: DelegatedRequest, job: DelegatedAgentJobRef) -> None:
        """Record one correlated request without filesystem, process, or network effects."""
        await self._remember(request, job)

    async def rehydrate_effect_free(
        self,
        request: DelegatedRequest,
        job: DelegatedAgentJobRef,
    ) -> None:
        """Rebuild one deterministic job solely from its persisted request."""
        await self._remember(request, job)

    async def _remember(
        self,
        request: DelegatedRequest,
        job: DelegatedAgentJobRef,
    ) -> None:
        """Retain a bounded pure projection, marking any omitted echo suffix."""
        self._validate_identity(request, job)
        result = DelegatedAgentResult(
            job_id=job.job_id,
            status=DelegatedAgentJobStatus.SUCCEEDED,
            output=bound_result_text(f"Reference delegate completed: {request.prompt}", result_field="output"),
        )
        async with self._lock:
            existing = self._jobs.get(job.job_id)
            if existing is not None:
                if existing.request != request or existing.ref != job:
                    msg = f"Reference delegated job id {job.job_id!r} was reused with different content."
                    raise ValueError(msg)
                return
            self._jobs[job.job_id] = _ReferenceJob(request=request, ref=job, result=result)

    async def poll(self, job: DelegatedAgentJobRef, *, request: DelegatedRequest) -> DelegatedAgentResult | None:
        """Return the pure result only for the retained request and job."""
        self._validate_identity(request, job)
        async with self._lock:
            return self._require(job, request=request).result

    async def cancel(self, job: DelegatedAgentJobRef, *, request: DelegatedRequest) -> None:
        """Cancel a not-yet-adopted result only for the retained request and job."""
        self._validate_identity(request, job)
        async with self._lock:
            existing = self._require(job, request=request)
            self._jobs[job.job_id] = _ReferenceJob(
                request=existing.request,
                ref=existing.ref,
                result=DelegatedAgentResult(
                    job_id=job.job_id,
                    status=DelegatedAgentJobStatus.CANCELLED,
                ),
            )

    async def retire_effect_free(self, job: DelegatedAgentJobRef) -> None:
        """Idempotently forget a projection acknowledged by the job store."""
        async with self._lock:
            existing = self._jobs.get(job.job_id)
            if existing is None:
                return
            if existing.ref != job:
                msg = f"Reference delegated job {job.job_id!r} does not match its tracked identity."
                raise ValueError(msg)
            self._jobs.pop(job.job_id)

    def _require(self, job: DelegatedAgentJobRef, *, request: DelegatedRequest) -> _ReferenceJob:
        try:
            existing = self._jobs[job.job_id]
        except KeyError as exc:
            msg = f"Unknown reference delegated job {job.job_id!r}."
            raise LookupError(msg) from exc
        if existing.ref != job:
            msg = f"Reference delegated job {job.job_id!r} does not match its tracked identity."
            raise ValueError(msg)
        if existing.request != request:
            msg = f"Reference delegated job {job.job_id!r} does not match its retained request."
            raise ValueError(msg)
        return existing

    def _validate_identity(
        self,
        request: DelegatedRequest,
        job: DelegatedAgentJobRef,
    ) -> None:
        if type(request) is not DelegatedAgentRequest:
            msg = "Reference delegated runtime refuses versioned CLI intent."
            raise ValueError(msg)
        if request.runtime != self.name or job.runtime != self.name:
            msg = "Reference delegated runtime accepts only the 'reference' runtime id."
            raise ValueError(msg)
        expected = (request.request_id, request.run_id, request.profile)
        observed = (job.request_id, job.run_id, job.profile)
        if observed != expected:
            msg = "Reference delegated job identity does not match its request."
            raise ValueError(msg)


__all__ = ("ReferenceDelegatedAgentRuntime",)
