"""Candidate-only Archive contracts; retrieval and promotion remain separate."""

from lychd.domain.memory.in_memory import InMemoryCandidateArchive
from lychd.domain.memory.models import (
    CandidateArchiveRecord,
    CandidateAttribution,
    CandidateDerivative,
    CandidateProcessingState,
    RawCandidate,
)
from lychd.domain.memory.ports import (
    CandidateArchiveIdentityConflictError,
    CandidateArchivePort,
    CandidateLineageError,
    IllegalCandidateProcessingTransitionError,
    StaleCandidateProcessingAttemptError,
    UnknownCandidateError,
)

__all__ = [
    "CandidateArchiveIdentityConflictError",
    "CandidateArchivePort",
    "CandidateArchiveRecord",
    "CandidateAttribution",
    "CandidateDerivative",
    "CandidateLineageError",
    "CandidateProcessingState",
    "IllegalCandidateProcessingTransitionError",
    "InMemoryCandidateArchive",
    "RawCandidate",
    "StaleCandidateProcessingAttemptError",
    "UnknownCandidateError",
]
