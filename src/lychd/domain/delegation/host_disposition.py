"""Mechanical delegated-host custody; none of these values permits guest release.

Preparation binds retained compiler inputs, not owner authority or physical facts.
Fresh handles are deliberately process-local and never enter a checkpoint or codec.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal, Never
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lychd.domain.delegation.cli_protocol import compile_cli_request
from lychd.domain.delegation.models import (
    DelegatedAgentJobRef,
    DelegatedCliRequestV2,
    SafeDelegatedIdentifier,
    Sha256Digest,
    cli_intent_digest,
    decode_delegated_request,
    delegated_request_digest,
)

MAX_HOST_PREPARATION_BYTES = 2 * 1024 * 1024


class HostDispositionError(RuntimeError):
    """A bounded mechanical operation cannot establish its promised disposition."""


class HostDispositionConflictError(HostDispositionError):
    """The supplied or retained exact identity differs or cannot be decoded."""


class HostIntakeClosedError(HostDispositionError):
    """Logical intake is irreversibly closed for this AgentJob."""


class HostDispositionNotEligibleError(HostDispositionError):
    """Current AgentJob state cannot receive a fresh mechanical handoff."""


class HostPreparationNotFreshError(HostDispositionError):
    """The exact issuing instance no longer holds this once-only preparation."""


class HostDispositionCommitUnknownError(HostDispositionError):
    """Commit acknowledgement was lost; no new handle or result was issued."""


def _fields(value: object) -> object:
    if isinstance(value, BaseModel):
        fields: dict[str, object] = dict(value.__dict__)
        if value.__pydantic_extra__:
            fields.update(value.__pydantic_extra__)
        return fields
    return value


def revalidate_host_job(job: DelegatedAgentJobRef) -> DelegatedAgentJobRef:
    """Reject copied-model bypasses instead of trusting a frozen instance."""
    return DelegatedAgentJobRef.model_validate(_fields(job))


class DelegatedHostPolicyIdentity(BaseModel):
    """Proposed immutable policy identity; shape does not establish admission."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")

    policy_id: SafeDelegatedIdentifier
    revision: SafeDelegatedIdentifier
    digest: Sha256Digest = Field(repr=False)

    @field_validator("revision")
    @classmethod
    def _immutable_revision(cls, value: str) -> str:
        if value.casefold() == "latest":
            msg = "An immutable host policy revision is required."
            raise ValueError(msg)
        return value


class DelegatedHostPreparation(BaseModel):
    """Exact bounded compiler inputs, independently checked on every reconstruction."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")

    preparation_schema: Literal["lychd-delegated-host-preparation@1"]
    job: DelegatedAgentJobRef = Field(repr=False)
    request: DelegatedCliRequestV2 = Field(repr=False)
    policy: DelegatedHostPolicyIdentity = Field(repr=False)
    executor_id: SafeDelegatedIdentifier
    executor_generation: int = Field(strict=True, ge=0, le=2**63 - 1)
    request_digest: Sha256Digest = Field(repr=False)
    intent_digest: Sha256Digest = Field(repr=False)
    launch_digest: Sha256Digest = Field(repr=False)

    @field_validator("job", "policy", mode="before")
    @classmethod
    def _retained_fields(cls, value: object) -> object:
        return _fields(value)

    @field_validator("request", mode="before")
    @classmethod
    def _v2_request(cls, value: object) -> DelegatedCliRequestV2:
        request = decode_delegated_request(value)
        if not isinstance(request, DelegatedCliRequestV2):
            msg = "Host preparation requires a retained V2 CLI request."
            raise TypeError(msg)
        return request

    @model_validator(mode="after")
    def _compiled_binding(self) -> DelegatedHostPreparation:
        spec = compile_cli_request(self.request, self.job)
        if (
            self.request_digest != delegated_request_digest(self.request)
            or self.intent_digest != cli_intent_digest(self.request)
            or self.launch_digest != "sha256:" + spec.digest
        ):
            msg = "Host preparation differs from its retained compiler inputs."
            raise ValueError(msg)
        return self

    def canonical_bytes(self) -> bytes:
        """Revalidate even copied instances before retaining restricted canonical bytes."""
        admitted = DelegatedHostPreparation.model_validate(_fields(self))
        encoded = json.dumps(
            admitted.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
        if len(encoded) > MAX_HOST_PREPARATION_BYTES:
            msg = "Host preparation exceeds the mechanical profile byte ceiling."
            raise ValueError(msg)
        return encoded

    @property
    def digest(self) -> Sha256Digest:
        """Bind internal custody without making the digest public evidence."""
        return "sha256:" + sha256(self.canonical_bytes()).hexdigest()


def build_host_preparation(
    job: DelegatedAgentJobRef,
    request: DelegatedCliRequestV2,
    *,
    policy: DelegatedHostPolicyIdentity,
    executor_id: str,
    executor_generation: int,
) -> DelegatedHostPreparation:
    """Compute mechanical digests without accepting them from the calling host."""
    retained_job = revalidate_host_job(job)
    retained_request = decode_delegated_request(request)
    if not isinstance(retained_request, DelegatedCliRequestV2):
        msg = "Host preparation requires a retained V2 CLI request."
        raise TypeError(msg)
    spec = compile_cli_request(retained_request, retained_job)
    preparation = DelegatedHostPreparation(
        preparation_schema="lychd-delegated-host-preparation@1",
        job=retained_job,
        request=retained_request,
        policy=policy,
        executor_id=executor_id,
        executor_generation=executor_generation,
        request_digest=delegated_request_digest(retained_request),
        intent_digest=cli_intent_digest(retained_request),
        launch_digest="sha256:" + spec.digest,
    )
    preparation.canonical_bytes()
    return preparation


def decode_host_preparation(encoded: bytes) -> DelegatedHostPreparation:
    """Refuse noncanonical, unknown or no-longer-reconstructable retained intent."""
    if not 0 < len(encoded) <= MAX_HOST_PREPARATION_BYTES:
        msg = "Host preparation is outside the mechanical profile byte ceiling."
        raise ValueError(msg)
    preparation = DelegatedHostPreparation.model_validate_json(encoded)
    if preparation.canonical_bytes() != encoded:
        msg = "Host preparation bytes are not canonical."
        raise ValueError(msg)
    return preparation


@dataclass(frozen=True, slots=True)
class DelegatedHostDispositionSnapshot:
    """Detached history only; a PREPARED snapshot cannot recreate a fresh handle."""

    job: DelegatedAgentJobRef = field(repr=False)
    preparation: DelegatedHostPreparation | None = field(repr=False)
    prepared_at: datetime | None
    dispatch_id: UUID | None
    dispatch_consumed_at: datetime | None
    intake_closed_at: datetime | None

    def __post_init__(self) -> None:
        """Keep public snapshots closed and detached even when directly constructed."""
        object.__setattr__(self, "job", revalidate_host_job(self.job))
        if self.preparation is not None:
            if type(self.preparation) is not DelegatedHostPreparation:
                msg = "Host snapshot requires the closed preparation type."
                raise TypeError(msg)
            preparation = decode_host_preparation(self.preparation.canonical_bytes())
            if preparation.job != self.job:
                msg = "Host snapshot preparation belongs to another job."
                raise ValueError(msg)
            object.__setattr__(self, "preparation", preparation)
        for name in ("prepared_at", "dispatch_consumed_at", "intake_closed_at"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _aware_instant(value))
        _dispatch_identity(self.dispatch_id)
        if (
            (self.preparation is None) != (self.prepared_at is None)
            or (self.dispatch_id is None) != (self.dispatch_consumed_at is None)
            or (self.dispatch_id is not None and self.preparation is None)
            or (self.preparation is None and self.intake_closed_at is None)
        ):
            msg = "Host snapshot disposition fields are incomplete."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True, eq=False, weakref_slot=True)
class FreshHostPreparation:
    """Issuer-local identity for one mechanical consumption, never a launch permit."""

    preparation: DelegatedHostPreparation = field(repr=False)

    def __reduce__(self) -> Never:
        """Keep ephemeral issuance out of persistence and process handoff."""
        msg = "Fresh host preparation cannot be serialized."
        raise TypeError(msg)


@dataclass(frozen=True, slots=True)
class DelegatedHostIntakeClosure:
    """Acknowledged logical intake closure; no physical containment is asserted."""

    job: DelegatedAgentJobRef = field(repr=False)
    closed_at: datetime

    def __post_init__(self) -> None:
        """Require an exact detached job and aware logical-closure instant."""
        object.__setattr__(self, "job", revalidate_host_job(self.job))
        object.__setattr__(self, "closed_at", _aware_instant(self.closed_at))


def _dispatch_identity(value: object) -> UUID | None:
    if value is None or isinstance(value, UUID):
        return value
    msg = "Host snapshot dispatch identity must be a UUID."
    raise TypeError(msg)


def _aware_instant(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        msg = "Host disposition instants must be aware datetimes."
        raise ValueError(msg)
    return value.astimezone(UTC)
