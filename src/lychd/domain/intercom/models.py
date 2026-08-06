"""Typed, bounded Intercom envelopes and peer-task lifecycle records."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, cast

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from lychd.domain.artifacts import ArtifactRef

__all__ = [
    "LEGAL_PEER_TASK_TRANSITIONS",
    "TERMINAL_PEER_TASK_STATUSES",
    "PeerAdmissionDecision",
    "PeerEnvelope",
    "PeerTaskPayload",
    "PeerTaskRecord",
    "PeerTaskResult",
    "PeerTaskStatus",
    "VerifiedPeerEnvelope",
]

_MAX_IDENTIFIER_LENGTH = 128
_MAX_VERSION_LENGTH = 64
_MAX_TASK_TYPE_LENGTH = 128
_MAX_CONTEXT_ID_LENGTH = 256
_MAX_REASON_LENGTH = 16_384
_MAX_PAYLOAD_BYTES = 1_048_576
_MAX_ARTIFACT_REFS = 256
_MAX_JSON_DEPTH = 32
_MAX_JSON_NODES = 100_000


class PeerTaskStatus(StrEnum):
    """Local durable-protocol vocabulary for one incoming peer task."""

    RECEIVED = "received"
    ADMITTED = "admitted"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    REFUSED = "refused"
    FAILED = "failed"
    EXPIRED = "expired"
    REVOKED = "revoked"
    CANCELLED = "cancelled"
    LOST = "lost"


TERMINAL_PEER_TASK_STATUSES: frozenset[PeerTaskStatus] = frozenset(
    {
        PeerTaskStatus.SUCCEEDED,
        PeerTaskStatus.REFUSED,
        PeerTaskStatus.FAILED,
        PeerTaskStatus.EXPIRED,
        PeerTaskStatus.REVOKED,
        PeerTaskStatus.CANCELLED,
        PeerTaskStatus.LOST,
    }
)

LEGAL_PEER_TASK_TRANSITIONS: dict[PeerTaskStatus, frozenset[PeerTaskStatus]] = {
    PeerTaskStatus.RECEIVED: frozenset(
        {
            PeerTaskStatus.ADMITTED,
            PeerTaskStatus.REFUSED,
            PeerTaskStatus.EXPIRED,
            PeerTaskStatus.REVOKED,
            PeerTaskStatus.FAILED,
        }
    ),
    PeerTaskStatus.ADMITTED: frozenset(
        {
            PeerTaskStatus.QUEUED,
            PeerTaskStatus.REFUSED,
            PeerTaskStatus.EXPIRED,
            PeerTaskStatus.REVOKED,
            PeerTaskStatus.CANCELLED,
            PeerTaskStatus.FAILED,
        }
    ),
    PeerTaskStatus.QUEUED: frozenset(
        {
            PeerTaskStatus.RUNNING,
            PeerTaskStatus.EXPIRED,
            PeerTaskStatus.REVOKED,
            PeerTaskStatus.CANCELLED,
            PeerTaskStatus.FAILED,
            PeerTaskStatus.LOST,
        }
    ),
    PeerTaskStatus.RUNNING: TERMINAL_PEER_TASK_STATUSES,
    PeerTaskStatus.SUCCEEDED: frozenset(),
    PeerTaskStatus.REFUSED: frozenset(),
    PeerTaskStatus.FAILED: frozenset(),
    PeerTaskStatus.EXPIRED: frozenset(),
    PeerTaskStatus.REVOKED: frozenset(),
    PeerTaskStatus.CANCELLED: frozenset(),
    PeerTaskStatus.LOST: frozenset(),
}


class PeerTaskPayload(BaseModel):
    """Bounded values and immutable artifact references crossing the sovereignty wall."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    values: dict[str, JsonValue] = Field(default_factory=dict)
    artifacts: tuple[ArtifactRef, ...] = Field(default=(), max_length=_MAX_ARTIFACT_REFS)

    @model_validator(mode="after")
    def _validate_encoded_size(self) -> PeerTaskPayload:
        _validate_json_shape(self.values)
        encoded = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > _MAX_PAYLOAD_BYTES:
            msg = f"Peer task payload exceeds the {_MAX_PAYLOAD_BYTES}-byte encoded limit."
            raise ValueError(msg)
        return self


def _validate_json_shape(values: dict[str, JsonValue]) -> None:
    stack: list[tuple[object, int]] = [(values, 0)]
    nodes = 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_JSON_NODES:
            msg = f"Peer task payload exceeds the {_MAX_JSON_NODES}-node structural limit."
            raise ValueError(msg)
        if depth > _MAX_JSON_DEPTH:
            msg = f"Peer task payload exceeds the {_MAX_JSON_DEPTH}-level nesting limit."
            raise ValueError(msg)
        if isinstance(value, dict):
            mapping = cast("dict[str, JsonValue]", value)
            stack.extend((child, depth + 1) for child in mapping.values())
        elif isinstance(value, list):
            sequence = cast("list[JsonValue]", value)
            stack.extend((child, depth + 1) for child in sequence)


class PeerEnvelope(BaseModel):
    """Versioned message shape after adapter decoding but before core verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol_version: str = Field(min_length=1, max_length=_MAX_VERSION_LENGTH)
    schema_version: str = Field(min_length=1, max_length=_MAX_VERSION_LENGTH)
    sender_peer_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    recipient_peer_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    message_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    task_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    idempotency_key: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    nonce: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    issued_at: AwareDatetime
    expires_at: AwareDatetime
    task_type: str = Field(min_length=1, max_length=_MAX_TASK_TYPE_LENGTH)
    payload: PeerTaskPayload
    context_id: str | None = Field(default=None, min_length=1, max_length=_MAX_CONTEXT_ID_LENGTH)

    @field_validator(
        "protocol_version",
        "schema_version",
        "sender_peer_id",
        "recipient_peer_id",
        "message_id",
        "task_id",
        "idempotency_key",
        "nonce",
        "task_type",
        "context_id",
    )
    @classmethod
    def _validate_canonical_text(cls, value: str | None) -> str | None:
        if value is not None and value != value.strip():
            msg = "Peer envelope identifiers and versions must be canonical non-whitespace values."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _validate_time_window(self) -> PeerEnvelope:
        if self.expires_at <= self.issued_at:
            msg = "Peer envelope expiry must be later than its issue time."
            raise ValueError(msg)
        return self


class VerifiedPeerEnvelope(BaseModel):
    """Adapter-authenticated envelope plus exact verification evidence.

    The canonical digest is produced by the pinned adapter and is used by core only
    for replay equality. It is not LychD's wire-signature format.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    envelope: PeerEnvelope
    canonical_envelope_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authenticated_peer_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    key_generation: int = Field(ge=0)
    revocation_generation: int = Field(ge=0)
    verified_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _bind_authenticated_sender(self) -> VerifiedPeerEnvelope:
        if self.authenticated_peer_id != self.envelope.sender_peer_id:
            msg = "Authenticated peer identity does not match the envelope sender."
            raise ValueError(msg)
        return self


class PeerAdmissionDecision(BaseModel):
    """Result of local peer/task/content policy without executing the task."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed: bool
    policy_revision: str = Field(min_length=1, max_length=_MAX_VERSION_LENGTH)
    reason: str | None = Field(default=None, max_length=_MAX_REASON_LENGTH)

    @field_validator("policy_revision")
    @classmethod
    def _validate_policy_revision(cls, value: str) -> str:
        if value != value.strip():
            msg = "Peer admission policy revision must be canonical."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _require_refusal_reason(self) -> PeerAdmissionDecision:
        if not self.allowed and (not self.reason or not self.reason.strip()):
            msg = "A refused peer admission must carry a reason."
            raise ValueError(msg)
        return self


class PeerTaskResult(BaseModel):
    """First terminal result retained for an exact local peer-task record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    status: Literal[
        PeerTaskStatus.SUCCEEDED,
        PeerTaskStatus.REFUSED,
        PeerTaskStatus.FAILED,
        PeerTaskStatus.EXPIRED,
        PeerTaskStatus.REVOKED,
        PeerTaskStatus.CANCELLED,
        PeerTaskStatus.LOST,
    ]
    payload: PeerTaskPayload | None = None
    reason: str | None = Field(default=None, max_length=_MAX_REASON_LENGTH)

    @field_validator("task_id")
    @classmethod
    def _validate_task_id(cls, value: str) -> str:
        if value != value.strip():
            msg = "Peer result task identity must be canonical."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _validate_terminal_shape(self) -> PeerTaskResult:
        if self.status is PeerTaskStatus.SUCCEEDED and self.reason is not None:
            msg = "A successful peer-task result cannot carry a failure reason."
            raise ValueError(msg)
        if self.status is not PeerTaskStatus.SUCCEEDED and (not self.reason or not self.reason.strip()):
            msg = f"A {self.status.value} peer-task result must carry a reason."
            raise ValueError(msg)
        if self.status is not PeerTaskStatus.SUCCEEDED and self.payload is not None:
            msg = f"A {self.status.value} peer-task result cannot carry a success payload."
            raise ValueError(msg)
        return self


class PeerTaskRecord(BaseModel):
    """Process-local read model for one authenticated peer task."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    verified: VerifiedPeerEnvelope
    admission: PeerAdmissionDecision | None = None
    status: PeerTaskStatus = PeerTaskStatus.RECEIVED
    result: PeerTaskResult | None = None
