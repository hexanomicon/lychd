"""LychD-owned port for raw memory candidates and their derivatives."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lychd.domain.memory.models import (
    CandidateArchiveRecord,
    CandidateDerivative,
    CandidateProcessingState,
    RawCandidate,
)

__all__ = [
    "CandidateArchiveIdentityConflictError",
    "CandidateArchivePort",
    "CandidateLineageError",
    "IllegalCandidateProcessingTransitionError",
    "StaleCandidateProcessingAttemptError",
    "UnknownCandidateError",
]


class CandidateArchiveIdentityConflictError(RuntimeError):
    """Raised when a stable record or idempotency identity changes meaning."""


class UnknownCandidateError(LookupError):
    """Raised when an operation requires a raw candidate that was never admitted."""


class CandidateLineageError(RuntimeError):
    """Raised when a derivative cannot prove a valid admitted source lineage."""


class IllegalCandidateProcessingTransitionError(RuntimeError):
    """Raised when processing attempts an undeclared lifecycle edge."""


class StaleCandidateProcessingAttemptError(IllegalCandidateProcessingTransitionError):
    """Raised when an older processor tries to settle or publish into a retry."""


@runtime_checkable
class CandidateArchivePort(Protocol):
    """Archive boundary for explicit candidate admission, processing, and lineage."""

    async def admit_raw(self, candidate: RawCandidate) -> tuple[CandidateArchiveRecord, bool]:
        """Admit once by record id and ingestion key; return ``(record, created)``."""
        ...

    async def get_raw(self, candidate_id: str) -> CandidateArchiveRecord | None: ...

    async def get_raw_by_ingestion_key(self, ingestion_key: str) -> CandidateArchiveRecord | None: ...

    async def transition_processing(
        self,
        candidate_id: str,
        state: CandidateProcessingState,
        *,
        attempt: int | None = None,
        failure_code: str | None = None,
    ) -> tuple[CandidateArchiveRecord, bool]:
        """Advance one attempt-fenced processing edge; return ``(record, changed)``."""
        ...

    async def admit_derivative(self, derivative: CandidateDerivative) -> tuple[CandidateDerivative, bool]:
        """Admit one derivative by record id and derivation key."""
        ...

    async def get_derivative(self, derivative_id: str) -> CandidateDerivative | None: ...

    async def get_derivative_by_derivation_key(self, derivation_key: str) -> CandidateDerivative | None: ...
