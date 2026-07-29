"""Ports that isolate the LychD delegation core from concrete agent runtimes."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lychd.domain.delegation.models import (
    DelegatedAgentEvent,
    DelegatedAgentJob,
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentRequest,
    DelegatedAgentResult,
)

__all__ = [
    "DelegatedAgentCoordinatorPort",
    "DelegatedAgentJobStore",
    "DelegatedAgentRuntime",
]


@runtime_checkable
class DelegatedAgentRuntime(Protocol):
    """Adapter contract for Codex-, Claude-, OpenCode-, or later agent runtimes."""

    name: str

    async def start(self, request: DelegatedAgentRequest, job: DelegatedAgentJobRef) -> None:
        """Start one isolated job under the caller-owned job reference."""
        ...

    async def poll(self, job: DelegatedAgentJobRef) -> DelegatedAgentResult | None:
        """Return a terminal result, or ``None`` while the external job is active."""
        ...

    async def cancel(self, job: DelegatedAgentJobRef) -> None:
        """Request cancellation of one active external job."""
        ...


class DelegatedAgentJobStore(Protocol):
    """Persistence port for replay-safe delegated job state."""

    async def create(
        self,
        request: DelegatedAgentRequest,
        ref: DelegatedAgentJobRef,
    ) -> tuple[DelegatedAgentJob, bool]:
        """Create once by request id; return ``(job, created)``."""
        ...

    async def get(self, job_id: str) -> DelegatedAgentJob | None: ...

    async def get_by_request(self, request_id: str) -> DelegatedAgentJob | None: ...

    async def jobs_for_run(self, run_id: str) -> tuple[DelegatedAgentJob, ...]: ...

    async def transition(
        self,
        job_id: str,
        status: DelegatedAgentJobStatus,
    ) -> tuple[DelegatedAgentJob, bool]:
        """Advance one legal nonterminal lifecycle edge."""
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

    async def submit(self, request: DelegatedAgentRequest) -> DelegatedAgentJobRef: ...

    async def get(self, job_id: str) -> DelegatedAgentJob | None: ...

    async def jobs_for_run(self, run_id: str) -> tuple[DelegatedAgentJob, ...]: ...

    async def refresh(self, job_id: str) -> DelegatedAgentJob: ...

    async def adopt(self, job_id: str, result: DelegatedAgentResult) -> bool: ...

    async def cancel(self, job_id: str) -> bool: ...

    async def events(self, job_id: str, *, after_seq: int = -1) -> tuple[DelegatedAgentEvent, ...]: ...
