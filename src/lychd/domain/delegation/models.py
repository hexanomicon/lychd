"""Typed contracts for long-lived work delegated to an isolated agent runtime."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from lychd.domain.artifacts import ArtifactRef

__all__ = [
    "LEGAL_DELEGATED_AGENT_TRANSITIONS",
    "TERMINAL_DELEGATED_AGENT_STATUSES",
    "DelegatedAgentEvent",
    "DelegatedAgentEventKind",
    "DelegatedAgentJob",
    "DelegatedAgentJobRef",
    "DelegatedAgentJobStatus",
    "DelegatedAgentProfile",
    "DelegatedAgentRequest",
    "DelegatedAgentResult",
]

_MAX_IDENTIFIER_LENGTH = 128
_MAX_PROMPT_LENGTH = 1_048_576
_MAX_RESULT_TEXT_LENGTH = 1_048_576
_MAX_ERROR_LENGTH = 16_384
_MAX_ARTIFACT_REFS = 256


class DelegatedAgentProfile(StrEnum):
    """Canonical containment posture shared by requests and Coffin policy."""

    READ = "read"
    CANDIDATE = "candidate"
    VERIFY = "verify"


class DelegatedAgentJobStatus(StrEnum):
    """The local truth LychD retains for one delegated job."""

    QUEUED = "queued"
    ADMITTED = "admitted"
    PREPARING = "preparing"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    LOST = "lost"


TERMINAL_DELEGATED_AGENT_STATUSES: frozenset[DelegatedAgentJobStatus] = frozenset(
    {
        DelegatedAgentJobStatus.SUCCEEDED,
        DelegatedAgentJobStatus.FAILED,
        DelegatedAgentJobStatus.CANCELLED,
        DelegatedAgentJobStatus.TIMED_OUT,
        DelegatedAgentJobStatus.LOST,
    }
)

LEGAL_DELEGATED_AGENT_TRANSITIONS: dict[DelegatedAgentJobStatus, frozenset[DelegatedAgentJobStatus]] = {
    DelegatedAgentJobStatus.QUEUED: frozenset(
        {
            DelegatedAgentJobStatus.ADMITTED,
            DelegatedAgentJobStatus.FAILED,
            DelegatedAgentJobStatus.CANCELLED,
            DelegatedAgentJobStatus.TIMED_OUT,
            DelegatedAgentJobStatus.LOST,
        }
    ),
    DelegatedAgentJobStatus.ADMITTED: frozenset(
        {
            DelegatedAgentJobStatus.PREPARING,
            DelegatedAgentJobStatus.FAILED,
            DelegatedAgentJobStatus.CANCELLED,
            DelegatedAgentJobStatus.TIMED_OUT,
            DelegatedAgentJobStatus.LOST,
        }
    ),
    DelegatedAgentJobStatus.PREPARING: frozenset(
        {
            DelegatedAgentJobStatus.RUNNING,
            DelegatedAgentJobStatus.FAILED,
            DelegatedAgentJobStatus.CANCELLED,
            DelegatedAgentJobStatus.TIMED_OUT,
            DelegatedAgentJobStatus.LOST,
        }
    ),
    DelegatedAgentJobStatus.RUNNING: TERMINAL_DELEGATED_AGENT_STATUSES,
    DelegatedAgentJobStatus.SUCCEEDED: frozenset(),
    DelegatedAgentJobStatus.FAILED: frozenset(),
    DelegatedAgentJobStatus.CANCELLED: frozenset(),
    DelegatedAgentJobStatus.TIMED_OUT: frozenset(),
    DelegatedAgentJobStatus.LOST: frozenset(),
}


class DelegatedAgentEventKind(StrEnum):
    """Stable semantic events retained by the delegation job store."""

    STATUS_CHANGED = "status_changed"
    RESULT_ADOPTED = "result_adopted"


class DelegatedAgentRequest(BaseModel):
    """One replay-safe request handed to an isolated delegated-agent adapter.

    ``request_id`` is the idempotency key. Callers must persist this request in graph
    state before retrying submission; a retry with the same id may never start a
    second external job.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str = Field(
        default_factory=lambda: str(uuid4()),
        min_length=1,
        max_length=_MAX_IDENTIFIER_LENGTH,
    )
    run_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    step_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    runtime: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    profile: DelegatedAgentProfile = DelegatedAgentProfile.READ
    prompt: str = Field(min_length=1, max_length=_MAX_PROMPT_LENGTH)
    input_artifacts: tuple[ArtifactRef, ...] = Field(default=(), max_length=_MAX_ARTIFACT_REFS)


class DelegatedAgentJobRef(BaseModel):
    """LychD-owned job identity correlated to one request, run, and runtime adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    request_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    run_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    runtime: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    profile: DelegatedAgentProfile = DelegatedAgentProfile.READ


class DelegatedAgentResult(BaseModel):
    """Terminal result returned by a delegated runtime without embedding blob bytes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    status: Literal[
        DelegatedAgentJobStatus.SUCCEEDED,
        DelegatedAgentJobStatus.FAILED,
        DelegatedAgentJobStatus.CANCELLED,
        DelegatedAgentJobStatus.TIMED_OUT,
        DelegatedAgentJobStatus.LOST,
    ]
    output: str | None = Field(default=None, max_length=_MAX_RESULT_TEXT_LENGTH)
    artifacts: tuple[ArtifactRef, ...] = Field(default=(), max_length=_MAX_ARTIFACT_REFS)
    error: str | None = Field(default=None, max_length=_MAX_ERROR_LENGTH)

    @model_validator(mode="after")
    def _validate_terminal_shape(self) -> DelegatedAgentResult:
        if self.status is DelegatedAgentJobStatus.SUCCEEDED and self.error is not None:
            msg = "A successful delegated-agent result cannot carry an error."
            raise ValueError(msg)
        if (
            self.status
            in {
                DelegatedAgentJobStatus.FAILED,
                DelegatedAgentJobStatus.TIMED_OUT,
                DelegatedAgentJobStatus.LOST,
            }
            and not self.error
        ):
            msg = f"A {self.status.value} delegated-agent result must carry an error."
            raise ValueError(msg)
        return self


class DelegatedAgentEvent(BaseModel):
    """One immutable, JSON-round-trippable job lifecycle event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        min_length=1,
        max_length=_MAX_IDENTIFIER_LENGTH,
    )
    job_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    request_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    seq: int = Field(ge=0)
    kind: DelegatedAgentEventKind
    status: DelegatedAgentJobStatus
    ts: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))


class DelegatedAgentJob(BaseModel):
    """Read model for one locally tracked delegated job."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request: DelegatedAgentRequest
    ref: DelegatedAgentJobRef
    status: DelegatedAgentJobStatus
    result: DelegatedAgentResult | None = None
    events: tuple[DelegatedAgentEvent, ...] = ()
