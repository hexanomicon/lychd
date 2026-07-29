"""Deterministic, no-network delegated runtime used by the reference Composition."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from lychd.domain.delegation.models import (
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentRequest,
    DelegatedAgentResult,
)


@dataclass(frozen=True, slots=True)
class _ReferenceJob:
    request: DelegatedAgentRequest
    ref: DelegatedAgentJobRef
    result: DelegatedAgentResult


class ReferenceDelegatedAgentRuntime:
    """Process-local adapter that deterministically settles on the first poll."""

    name = "reference"

    def __init__(self) -> None:
        """Create an empty process-local reference runtime."""
        self._jobs: dict[str, _ReferenceJob] = {}
        self._lock = asyncio.Lock()

    async def start(self, request: DelegatedAgentRequest, job: DelegatedAgentJobRef) -> None:
        """Record one correlated request without filesystem, process, or network effects."""
        self._validate_identity(request, job)
        result = DelegatedAgentResult(
            job_id=job.job_id,
            status=DelegatedAgentJobStatus.SUCCEEDED,
            output=f"Reference delegate completed: {request.prompt}",
        )
        async with self._lock:
            existing = self._jobs.get(job.job_id)
            if existing is not None:
                if existing.request != request or existing.ref != job:
                    msg = f"Reference delegated job id {job.job_id!r} was reused with different content."
                    raise ValueError(msg)
                return
            self._jobs[job.job_id] = _ReferenceJob(request=request, ref=job, result=result)

    async def poll(self, job: DelegatedAgentJobRef) -> DelegatedAgentResult | None:
        """Return the deterministic terminal result for a started job."""
        async with self._lock:
            return self._require(job).result

    async def cancel(self, job: DelegatedAgentJobRef) -> None:
        """Replace a not-yet-adopted reference result with cancellation."""
        async with self._lock:
            existing = self._require(job)
            self._jobs[job.job_id] = _ReferenceJob(
                request=existing.request,
                ref=existing.ref,
                result=DelegatedAgentResult(
                    job_id=job.job_id,
                    status=DelegatedAgentJobStatus.CANCELLED,
                ),
            )

    def _require(self, job: DelegatedAgentJobRef) -> _ReferenceJob:
        try:
            existing = self._jobs[job.job_id]
        except KeyError as exc:
            msg = f"Unknown reference delegated job {job.job_id!r}."
            raise LookupError(msg) from exc
        if existing.ref != job:
            msg = f"Reference delegated job {job.job_id!r} does not match its tracked identity."
            raise ValueError(msg)
        return existing

    def _validate_identity(
        self,
        request: DelegatedAgentRequest,
        job: DelegatedAgentJobRef,
    ) -> None:
        if request.runtime != self.name or job.runtime != self.name:
            msg = "Reference delegated runtime accepts only the 'reference' runtime id."
            raise ValueError(msg)
        expected = (request.request_id, request.run_id, request.profile)
        observed = (job.request_id, job.run_id, job.profile)
        if observed != expected:
            msg = "Reference delegated job identity does not match its request."
            raise ValueError(msg)


__all__ = ("ReferenceDelegatedAgentRuntime",)
