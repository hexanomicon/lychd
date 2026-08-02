"""Immutable contracts for the narrow Archive candidate-admission seam."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

__all__ = [
    "CandidateArchiveRecord",
    "CandidateAttribution",
    "CandidateDerivative",
    "CandidateProcessingState",
    "RawCandidate",
]

_MAX_CONTENT_LENGTH = 1_048_576


def _reject_blank(value: str) -> str:
    if not value.strip():
        msg = "Candidate content cannot be blank."
        raise ValueError(msg)
    return value


type _Identifier = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$",
    ),
]
type _Kind = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$",
    ),
]
type _Reference = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2_048)]
type _Content = Annotated[
    str,
    StringConstraints(min_length=1, max_length=_MAX_CONTENT_LENGTH),
    AfterValidator(_reject_blank),
]


class CandidateProcessingState(StrEnum):
    """Finite processing state; it conveys no curation or recall eligibility."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class CandidateAttribution(BaseModel):
    """Identity that makes one candidate or derivative answerable to its source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    namespace_id: _Identifier
    subject_id: _Identifier
    producer_id: _Identifier
    producer_revision: _Identifier
    session_id: _Identifier | None = None
    run_id: _Identifier | None = None


class RawCandidate(BaseModel):
    """One explicitly admitted source unit before any derived processing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: _Identifier
    ingestion_key: _Identifier
    attribution: CandidateAttribution
    source_ref: _Reference
    source_revision: _Identifier
    kind: _Kind
    content: _Content = Field(repr=False)
    observed_at: AwareDatetime


class CandidateDerivative(BaseModel):
    """One separately identified output retaining direct raw-candidate lineage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    derivative_id: _Identifier
    derivation_key: _Identifier
    source_candidate_id: _Identifier
    processing_attempt: int = Field(ge=1)
    attribution: CandidateAttribution
    kind: _Kind
    content: _Content = Field(repr=False)
    derived_at: AwareDatetime


class CandidateArchiveRecord(BaseModel):
    """Immutable read model for raw admission and its processing state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate: RawCandidate
    state: CandidateProcessingState = CandidateProcessingState.PENDING
    processing_attempt: int = Field(default=0, ge=0)
    failure_code: _Identifier | None = None

    @model_validator(mode="after")
    def _validate_failure_shape(self) -> CandidateArchiveRecord:
        if self.state is CandidateProcessingState.PENDING and self.processing_attempt != 0:
            msg = "A pending candidate cannot claim a processing attempt."
            raise ValueError(msg)
        if self.state is not CandidateProcessingState.PENDING and self.processing_attempt == 0:
            msg = "A non-pending candidate must identify its processing attempt."
            raise ValueError(msg)
        if self.state is CandidateProcessingState.FAILED and self.failure_code is None:
            msg = "A failed candidate must carry a bounded failure code."
            raise ValueError(msg)
        if self.state is not CandidateProcessingState.FAILED and self.failure_code is not None:
            msg = "Only a failed candidate may carry a failure code."
            raise ValueError(msg)
        return self
