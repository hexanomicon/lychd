"""Closed owner-admission observations and a denying trusted port.

This consumer seam supplies no owner-record producer, authority store, source-byte
closure, custody service or verifier reservation. Positive fixtures prove correlation
only; production owner truth must be implemented independently before effects.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from lychd.domain.delegation.models import (
    DelegatedAgentJobRef,
    DelegatedCliRequestV2,
    OperatorCampaignBinding,
    SafeDelegatedIdentifier,
    Sha256Digest,
)

_MAX_VALIDITY_SECONDS = 86_400


class OwnerAdmissionReason(StrEnum):
    """Bounded refusal vocabulary, never untrusted diagnostic text."""

    UNAVAILABLE = "unavailable"
    UNRESOLVED = "unresolved"
    STALE = "stale"
    REVOKED = "revoked"
    CONFLICT = "conflict"
    UNSUPPORTED = "unsupported"


class OwnerAdmissionDenied(BaseModel):
    """No current complete owner admission is established."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal["denied"]
    reason: OwnerAdmissionReason


class OwnerAdmissionGranted(BaseModel):
    """Trusted observation bound to one exact request occurrence and owner contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    decision: Literal["admitted"]
    job: DelegatedAgentJobRef
    request_digest: Sha256Digest
    intent_digest: Sha256Digest
    owner_binding: OperatorCampaignBinding
    admission_id: SafeDelegatedIdentifier
    issued_at: AwareDatetime
    expires_at: AwareDatetime
    generation: int = Field(strict=True, ge=0, le=2**63 - 1)

    @field_validator("job", mode="before")
    @classmethod
    def _retained_job_fields(cls, value: object) -> object:
        if isinstance(value, DelegatedAgentJobRef):
            fields: dict[str, object] = dict(value.__dict__)
            if value.__pydantic_extra__:
                fields.update(value.__pydantic_extra__)
            return fields
        return value

    @field_validator("issued_at", "expires_at", mode="before")
    @classmethod
    def _aware_instants(cls, value: object) -> datetime:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            msg = "Owner admission instants must be aware datetimes."
            raise ValueError(msg)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _bounded_validity(self) -> OwnerAdmissionGranted:
        issued = self._aware_instants(self.issued_at)
        expires = self._aware_instants(self.expires_at)
        seconds = (expires - issued).total_seconds()
        if not 0 < seconds <= _MAX_VALIDITY_SECONDS:
            msg = "Owner admission validity must be positive and no longer than one day."
            raise ValueError(msg)
        return self

    def is_current(self, now: datetime) -> bool:
        """Evaluate only time validity against the injected trusted clock."""
        try:
            issued = self._aware_instants(self.issued_at)
            expires = self._aware_instants(self.expires_at)
            current = self._aware_instants(now)
        except (TypeError, ValueError):
            return False
        return 0 < (expires - issued).total_seconds() <= _MAX_VALIDITY_SECONDS and issued <= current < expires


class OwnerAdmissionPort(Protocol):
    """Trusted injected owner check, unavailable to request/model selection.

    The producer owns source bytes, current authority, revocation and generation.
    Equality checks in the consumer cannot establish those facts.
    """

    async def admit(
        self, request: DelegatedCliRequestV2, job: DelegatedAgentJobRef
    ) -> OwnerAdmissionGranted | OwnerAdmissionDenied: ...


class DenyingOwnerAdmission:
    """Default contains no positive producer or implied authorization."""

    async def admit(self, request: DelegatedCliRequestV2, job: DelegatedAgentJobRef) -> OwnerAdmissionDenied:
        del request, job
        return OwnerAdmissionDenied(decision="denied", reason=OwnerAdmissionReason.UNAVAILABLE)
