"""Restricted durable disclosure evidence; none of these values grants an effect.

The only supported consumer is the synthetic offline export recorder. Host and
purpose capacity survive new Cut, Run, attempt and configuration identities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Literal, Never, Protocol
from uuid import UUID

from pydantic import Field

from lychd.domain.privacy.contracts import Digest, PrivacyCut, canonical_bytes, digest
from lychd.domain.privacy.labels import PrivacyValue

type DisclosureStatus = Literal["prepared", "claimed", "recorded", "refused", "unknown"]
type DisclosureCode = Literal[
    "contract",
    "binding",
    "authority",
    "expiry",
    "capacity",
    "conflict",
    "claim",
    "fenced",
    "commit-unknown",
    "store",
    "record-unknown",
]
Count = Annotated[int, Field(strict=True, ge=0, le=2**63 - 1)]


class DisclosureError(ValueError):
    """Closed content-free boundary error; foreign errors are never chained."""

    def __init__(self, code: DisclosureCode) -> None:
        """Keep only a closed refusal code, never foreign error text."""
        self.code = code
        super().__init__(f"Disclosure refused: {code}.")


def refuse(code: DisclosureCode) -> Never:
    """Raise only the closed code, suppressing foreign exception display."""
    raise DisclosureError(code) from None


class DisclosureCapacity(PrivacyValue):
    uses: Count
    bytes: Count


class DisclosureLimits(PrivacyValue):
    host: DisclosureCapacity
    purpose: DisclosureCapacity


class DisclosureRunBinding(PrivacyValue):
    """Exact independently retained Run and claimed delivery generation."""

    run_id: UUID
    delivery_id: UUID
    enqueue_seq: Count
    priority: Annotated[int, Field(strict=True, ge=0, le=100)]
    queue_name: Annotated[str, Field(min_length=1, max_length=50)]
    workflow_name: Annotated[str, Field(min_length=1, max_length=100)]
    sigil_name: Annotated[str, Field(min_length=1, max_length=100)]
    intent_digest: Digest
    pattern_digest: Digest


class DisclosurePreparation(PrivacyValue):
    """Canonical restricted evidence, without source or candidate body."""

    profile: Literal["closed-diagnostic-recording@1"] = "closed-diagnostic-recording@1"
    transmission_id: UUID
    request_id: UUID
    host_id: UUID
    configuration_digest: Digest
    authority_generation: Count
    run: DisclosureRunBinding
    cut: PrivacyCut
    candidate_size: Annotated[int, Field(strict=True, ge=1, le=1_048_576)]

    @property
    def digest(self) -> str:
        return digest(self)

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self)


class DisclosureDecision(PrivacyValue):
    preparation_digest: Digest
    claim_id: UUID
    charged_uses: Literal[1] = 1
    charged_bytes: Count
    admitted_at: datetime


class DisclosureSnapshot(PrivacyValue):
    preparation: DisclosurePreparation
    status: DisclosureStatus
    claim_id: UUID | None = None
    decision_digest: Digest | None = None
    receipt_id: UUID | None = None


class DisclosureSettlement(PrivacyValue):
    """Closed retained evidence, checked against exact transmission and claim."""

    receipt_id: UUID
    transmission_id: UUID
    claim_id: UUID
    outcome: Literal["recorded", "refused", "unknown"]


@dataclass(frozen=True, slots=True, eq=False)
class FreshDisclosureClaim:
    """Process-local object identity issued only after acknowledged fresh commit."""

    preparation: DisclosurePreparation
    claim_id: UUID


@dataclass(frozen=True, slots=True, eq=False)
class RecordingCompletion:
    """Identity-owned completion, never reconstructed from retained evidence."""

    receipt_id: UUID
    transmission_id: UUID
    claim_id: UUID
    outcome: Literal["recorded", "refused", "unknown"]

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(
            DisclosureSettlement(
                receipt_id=self.receipt_id,
                transmission_id=self.transmission_id,
                claim_id=self.claim_id,
                outcome=self.outcome,
            )
        )


class DisclosureAuthority(Protocol):
    def authorize(self, preparation: DisclosurePreparation) -> None: ...


class DisclosureCompletionOwner(Protocol):
    def verify_completion(self, claim: FreshDisclosureClaim, completion: RecordingCompletion) -> None: ...
