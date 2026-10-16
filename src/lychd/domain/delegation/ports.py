"""Ports that isolate the LychD delegation core from concrete agent runtimes."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lychd.domain.delegation.models import (
    DelegatedAgentEvent,
    DelegatedAgentJob,
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentResult,
    DelegatedRequest,
)

__all__ = [
    "DelegatedAgentCoordinatorPort",
    "DelegatedAgentJobStore",
    "DelegatedAgentRuntime",
]


@runtime_checkable
class DelegatedAgentRuntime(Protocol):
    """Adapter contract for Codex-, Claude-, OpenCode-, or later agent runtimes."""

    @property
    def name(self) -> str:
        """Return the adapter identity used by the coordinator."""
        ...

    async def start(self, request: DelegatedRequest, job: DelegatedAgentJobRef) -> None:
        """Start one isolated job under the caller-owned job reference."""
        ...

    async def poll(self, job: DelegatedAgentJobRef, *, request: DelegatedRequest) -> DelegatedAgentResult | None:
        """Correlate the outcome to the store-retained request; return ``None`` while active."""
        ...

    async def cancel(self, job: DelegatedAgentJobRef, *, request: DelegatedRequest) -> None:
        """Contain this exact job, correlated to its store-retained request.

        Successful return authorizes durable ``CANCELLED`` settlement. An
        acknowledged cancellation request alone is insufficient; raise while
        termination or external effects remain uncontained or indeterminate.
        """
        ...


class DelegatedAgentJobStore(Protocol):
    """Persistence port for replay-safe delegated job state."""

    async def create(
        self,
        request: DelegatedRequest,
        ref: DelegatedAgentJobRef,
    ) -> tuple[DelegatedAgentJob, bool]:
        """Create once by request id; return ``(job, created)``."""
        ...

    async def get(self, job_id: str) -> DelegatedAgentJob | None: ...

    async def get_by_request(self, request_id: str) -> DelegatedAgentJob | None: ...

    async def jobs_for_run(
        self,
        run_id: str,
        *,
        limit: int | None = None,
        event_limit: int | None = None,
    ) -> tuple[DelegatedAgentJob, ...]:
        """Return newest bounded jobs and event suffixes in creation order."""
        ...

    async def transition(
        self,
        job_id: str,
        status: DelegatedAgentJobStatus,
    ) -> tuple[DelegatedAgentJob, bool]:
        """Advance one legal nonterminal lifecycle edge."""
        ...

    async def settle_acceptance_failure(
        self,
        job_id: str,
        result: DelegatedAgentResult,
    ) -> tuple[DelegatedAgentJob, bool]:
        """Under the job lock, adopt LOST only while still PREPARING.

        Require a matching, shape-valid LOST result. Preserve RUNNING and every
        terminal row unchanged; reject any other state. Return ``(job, adopted)``
        with one result-adoption event only when this operation settles LOST.
        """
        ...

    async def adopt(self, job_id: str, result: DelegatedAgentResult) -> tuple[DelegatedAgentJob, bool]:
        """Adopt one terminal result once; return ``(job, adopted)``."""
        ...

    async def cancel(self, job_id: str) -> tuple[DelegatedAgentJob, bool]:
        """Record cancellation once; return ``(job, changed)``."""
        ...

    async def events(self, job_id: str, *, after_seq: int = -1) -> tuple[DelegatedAgentEvent, ...]: ...


class DelegatedAgentCoordinatorPort(Protocol):
    """The graph-facing delegated-agent service surface."""

    async def submit(self, request: DelegatedRequest) -> DelegatedAgentJobRef: ...

    async def get(self, job_id: str) -> DelegatedAgentJob | None: ...

    async def jobs_for_run(
        self,
        run_id: str,
        *,
        limit: int | None = None,
        event_limit: int | None = None,
    ) -> tuple[DelegatedAgentJob, ...]:
        """Return newest bounded jobs and event suffixes in creation order."""
        ...

    async def refresh(self, job_id: str) -> DelegatedAgentJob: ...

    async def adopt(self, job_id: str, result: DelegatedAgentResult) -> bool: ...

    async def cancel(self, job_id: str) -> bool: ...

    async def events(self, job_id: str, *, after_seq: int = -1) -> tuple[DelegatedAgentEvent, ...]: ...
