"""Typed contracts for long-lived work delegated to an isolated agent runtime."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Annotated, Literal, cast
from uuid import uuid4

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
    field_validator,
    model_validator,
)

from lychd.domain.artifacts import ArtifactRef
from lychd.domain.delegation.cli_values import (
    CliLimits,
    CliRuntimeKind,
    CliWorkspace,
    reviewed_cli_version,
    validate_cli_model,
    validate_cli_path,
)

__all__ = [
    "LEGAL_DELEGATED_AGENT_TRANSITIONS",
    "MAX_DELEGATED_ERROR_LENGTH",
    "TERMINAL_DELEGATED_AGENT_STATUSES",
    "DelegatedAgentEvent",
    "DelegatedAgentEventKind",
    "DelegatedAgentJob",
    "DelegatedAgentJobRef",
    "DelegatedAgentJobStatus",
    "DelegatedAgentProfile",
    "DelegatedAgentRequest",
    "DelegatedAgentResult",
    "DelegatedCliIntentV1",
    "DelegatedCliRequestV2",
    "DelegatedRequest",
    "OperatorCampaignBinding",
    "OperatorCampaignReference",
    "bound_result_text",
    "cli_intent_digest",
    "decode_delegated_request",
    "delegated_request_digest",
    "encode_delegated_request",
]

_MAX_IDENTIFIER_LENGTH = 128
_MAX_PROMPT_LENGTH = 1_048_576
_MAX_RESULT_TEXT_LENGTH = 1_048_576
MAX_DELEGATED_ERROR_LENGTH = 16_384
_MAX_ARTIFACT_REFS = 256


def _retained_model_fields(value: BaseModel) -> dict[str, object]:
    """Preserve stored fields and forbidden additions before explicit revalidation."""
    fields: dict[str, object] = dict(value.__dict__)
    if value.__pydantic_extra__:
        fields.update(value.__pydantic_extra__)
    return fields


def bound_result_text(text: str, *, result_field: Literal["output", "error"]) -> str:
    """Bound locally projected result text while leaving runtime validation strict."""
    limit = _MAX_RESULT_TEXT_LENGTH if result_field == "output" else MAX_DELEGATED_ERROR_LENGTH
    if len(text) <= limit:
        return text
    suffix = "\n...[truncated]"
    return text[: limit - len(suffix)] + suffix


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
    # LOST is terminal for result adoption and polling, but it is not proof that
    # the external process stopped. Explicit containment may still settle it.
    DelegatedAgentJobStatus.LOST: frozenset({DelegatedAgentJobStatus.CANCELLED}),
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


SafeDelegatedIdentifier = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")]
Sha256Digest = Annotated[str, StringConstraints(strict=True, pattern=r"^sha256:[0-9a-f]{64}$")]


class OperatorCampaignReference(BaseModel):
    """Opaque immutable owner-qualified identity; the runtime never resolves paths."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")

    owner_namespace: Literal["operator-campaign@1"]
    record_id: SafeDelegatedIdentifier
    revision: SafeDelegatedIdentifier
    digest: Sha256Digest

    @field_validator("revision")
    @classmethod
    def _immutable_revision(cls, value: str) -> str:
        if value.casefold() == "latest":
            msg = "An immutable owner revision is required."
            raise ValueError(msg)
        return value


class OperatorCampaignBinding(BaseModel):
    """Four exact external contracts and their independent verifier identity."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")

    task: OperatorCampaignReference
    projection: OperatorCampaignReference
    custody: OperatorCampaignReference
    verification: OperatorCampaignReference
    verifier_id: SafeDelegatedIdentifier


class DelegatedCliIntentV1(BaseModel):
    """Complete retained input to the fixed official-one-shot@1 compiler."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")

    compiler_revision: Literal["official-one-shot@1"]
    cli_version: str
    executable: str
    model: str
    workspace: CliWorkspace
    limits: CliLimits

    @field_validator("workspace", mode="before")
    @classmethod
    def _workspace(cls, value: object) -> CliWorkspace:
        fields = {"job_root", "workspace", "scratch", "artifacts"}
        raw: object = asdict(value) if type(value) is CliWorkspace else value
        if type(raw) is not dict or set(cast("dict[str, object]", raw)) != fields:
            msg = "All exact CLI workspace roots are required."
            raise ValueError(msg)
        values = cast("dict[str, object]", raw)
        if any(type(item) is not str for item in values.values()):
            msg = "CLI workspace roots must be strings."
            raise ValueError(msg)
        return CliWorkspace(**cast("dict[str, str]", values))

    @field_validator("limits", mode="before")
    @classmethod
    def _limits(cls, value: object) -> CliLimits:
        fields = {"max_stdout_bytes", "max_stderr_bytes", "max_record_bytes", "wall_seconds"}
        raw: object = asdict(value) if type(value) is CliLimits else value
        if type(raw) is not dict or set(cast("dict[str, object]", raw)) != fields:
            msg = "All four exact CLI limits are required."
            raise ValueError(msg)
        values = cast("dict[str, object]", raw)
        if any(type(item) is not int for item in values.values()):
            msg = "CLI limits must be strict integers."
            raise ValueError(msg)
        return CliLimits(**cast("dict[str, int]", values))

    @model_validator(mode="after")
    def _mechanics(self) -> DelegatedCliIntentV1:
        validate_cli_path(self.executable)
        validate_cli_model(self.model)
        return self


class DelegatedCliRequestV2(BaseModel):
    """Strict sibling of the legacy request; owner observations are never request data."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    request_schema: Literal["lychd-delegated-cli-request@2"]
    request_id: SafeDelegatedIdentifier
    run_id: SafeDelegatedIdentifier
    step_id: SafeDelegatedIdentifier
    runtime: Literal["codex", "claude"]
    profile: DelegatedAgentProfile
    prompt: str = Field(min_length=1, max_length=_MAX_PROMPT_LENGTH, strict=True)
    input_artifacts: tuple[ArtifactRef, ...] = Field(max_length=_MAX_ARTIFACT_REFS)
    cli_intent: DelegatedCliIntentV1
    owner_binding: OperatorCampaignBinding

    @field_validator("input_artifacts", mode="before")
    @classmethod
    def _strict_artifacts(cls, value: object) -> object:
        if type(value) not in (tuple, list):
            msg = "CLI input artifacts must be an explicit sequence."
            raise ValueError(msg)
        artifacts: list[object] = []
        for item in cast("list[object] | tuple[object, ...]", value):
            raw: object = _retained_model_fields(item) if isinstance(item, ArtifactRef) else item
            if type(raw) is not dict or type(cast("dict[str, object]", raw).get("size")) is not int:
                msg = "CLI input artifact sizes must be strict integers."
                raise ValueError(msg)
            artifacts.append(cast("dict[str, object]", raw))
        return tuple(artifacts)

    @model_validator(mode="after")
    def _pinned_version(self) -> DelegatedCliRequestV2:
        if self.cli_intent.cli_version != reviewed_cli_version(CliRuntimeKind(self.runtime)):
            msg = "CLI intent requires the exact reviewed version."
            raise ValueError(msg)
        if len(self.prompt.encode("utf-8")) > _MAX_PROMPT_LENGTH:
            msg = "CLI prompt exceeds the UTF-8 byte ceiling."
            raise ValueError(msg)
        return self


type DelegatedRequest = DelegatedAgentRequest | DelegatedCliRequestV2


def decode_delegated_request(value: object) -> DelegatedRequest:
    """Dispatch by exact discriminator before validation; never try another version."""
    if type(value) in (DelegatedAgentRequest, DelegatedCliRequestV2):
        # Field-based serialization erases forbidden additions and may coerce primitives.
        value = _retained_model_fields(cast("DelegatedRequest", value))
    if type(value) is not dict:
        msg = "A delegated request must be an object."
        raise ValueError(msg)
    raw = dict(cast("dict[str, object]", value))
    artifacts = raw.get("input_artifacts")
    if isinstance(artifacts, (list, tuple)):
        raw["input_artifacts"] = tuple(
            _retained_model_fields(item) if isinstance(item, ArtifactRef) else item
            for item in cast("list[object] | tuple[object, ...]", artifacts)
        )
    if "request_schema" not in raw:
        return DelegatedAgentRequest.model_validate(raw)
    if type(raw["request_schema"]) is str and raw["request_schema"] == "lychd-delegated-cli-request@2":
        return DelegatedCliRequestV2.model_validate(raw)
    msg = "Unsupported delegated request schema."
    raise ValueError(msg)


def encode_delegated_request(request: DelegatedRequest) -> dict[str, object]:
    """Validate and retain the complete exact request shape at every storage boundary."""
    return decode_delegated_request(request).model_dump(mode="json")


def _versioned_digest(domain: str, payload: object) -> str:
    canonical = json.dumps(
        {"digest_domain": domain, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + sha256(canonical).hexdigest()


def delegated_request_digest(request: DelegatedCliRequestV2) -> str:
    """Bind the internal V2 request separately from launch and mechanical intent."""
    return _versioned_digest("lychd-delegated-cli-request@2", encode_delegated_request(request))


def cli_intent_digest(request: DelegatedCliRequestV2) -> str:
    """Bind only the closed compiler input under its own digest domain."""
    retained = decode_delegated_request(request)
    if not isinstance(retained, DelegatedCliRequestV2):
        msg = "A V2 CLI request is required."
        raise TypeError(msg)
    return _versioned_digest("lychd-delegated-cli-intent@1", retained.cli_intent.model_dump(mode="json"))


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
    error: str | None = Field(default=None, max_length=MAX_DELEGATED_ERROR_LENGTH)

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

    request: DelegatedRequest
    ref: DelegatedAgentJobRef
    status: DelegatedAgentJobStatus
    result: DelegatedAgentResult | None = None
    events: tuple[DelegatedAgentEvent, ...] = ()

    @field_validator("request", mode="before")
    @classmethod
    def _request_codec(cls, value: object) -> DelegatedRequest:
        return decode_delegated_request(value)

    @field_serializer("request", when_used="json")
    def _encode_request(self, value: DelegatedRequest) -> dict[str, object]:
        return encode_delegated_request(value)
