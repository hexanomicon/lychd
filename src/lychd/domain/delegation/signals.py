"""Control-flow signals that park a graph on delegated-agent completion."""

from __future__ import annotations

from dataclasses import dataclass

from lychd.domain.delegation.models import DelegatedAgentJobRef

__all__ = ["DelegatedAgentParked", "DelegatedAgentPending"]


class DelegatedAgentPending(Exception):  # noqa: N818 - suspension signal, not an error
    """A graph node has submitted a durable delegated job and must suspend."""

    def __init__(self, job: DelegatedAgentJobRef) -> None:
        """Carry the already-submitted job reference across the graph boundary."""
        self.job = job
        super().__init__(f"run {job.run_id} parked on delegated-agent job {job.job_id}")


@dataclass(frozen=True, kw_only=True)
class DelegatedAgentParked:
    """Graph-to-runner sentinel for one committed delegated-agent wait."""

    job: DelegatedAgentJobRef
