"""Immutable, effect-free contracts for Creation candidates and promotion requests."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from lychd.domain.artifacts import ArtifactRef

__all__ = [
    "CandidateArtifact",
    "CandidateArtifactRef",
    "CandidateBudget",
    "CreationPhase",
    "CreationSnapshot",
    "CustodyOutcome",
    "CustodyReceipt",
    "EvidenceManifest",
    "ExactSourceRevision",
    "HumanReview",
    "NetworkConstraint",
    "NetworkMode",
    "PromotionRequest",
    "ProvisionalSourceBounds",
    "RecordBinding",
    "ReviewDecision",
    "RevisionAlgorithm",
    "Sha256Digest",
    "ToolPin",
    "VerificationOutcome",
    "VerificationReceipt",
    "VerificationRequirement",
    "WorkPacket",
]

_MAX_IDENTIFIER_LENGTH = 128
_MAX_PATH_LENGTH = 1_024
_MAX_PATHS = 4_096
_MAX_INPUTS = 256
_MAX_TOOLS = 128
_MAX_EFFECTS = 128
_MAX_CHECKS = 256
_MAX_COMMAND_PARTS = 128
_MAX_COMMAND_PART_LENGTH = 4_096
_MAX_ARTIFACT_BYTES = 10 * 1_024 * 1_024 * 1_024
_MAX_TIMEOUT_SECONDS = 86_400
_MAX_RETENTION_DAYS = 3_650

Identifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=_MAX_IDENTIFIER_LENGTH),
]
Sha256Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
CommandPart = Annotated[str, Field(min_length=1, max_length=_MAX_COMMAND_PART_LENGTH)]
MediaType = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    def digest(self) -> str:
        """Return a stable digest of this immutable record's canonical JSON form."""
        payload = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        return f"sha256:{hashlib.sha256(payload).hexdigest()}"


class RevisionAlgorithm(StrEnum):
    """Content-addressed revision forms admitted by the narrow source projection."""

    GIT_SHA1 = "git-sha1"
    GIT_SHA256 = "git-sha256"


class NetworkMode(StrEnum):
    """Network declaration bound into a packet; it grants no network access."""

    DENIED = "denied"
    ADMITTED = "admitted"


class CustodyOutcome(StrEnum):
    """Observed custody state for candidate bytes."""

    SEALED = "sealed"
    MISSING = "missing"
    CORRUPT = "corrupt"


class VerificationOutcome(StrEnum):
    """Deterministic verifier result retained as evidence."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMED_OUT = "timed_out"


class ReviewDecision(StrEnum):
    """An explicit human judgment over one exact evidence manifest."""

    REQUEST_PROMOTION = "request_promotion"
    REJECT = "reject"


class CreationPhase(StrEnum):
    """Observable phase of one process-local Creation candidate."""

    PACKET_ADMITTED = "packet_admitted"
    CANDIDATE_RECORDED = "candidate_recorded"
    EVIDENCE_RECORDED = "evidence_recorded"
    ELIGIBLE_FOR_REVIEW = "eligible_for_review"
    REVIEWED = "reviewed"
    REJECTED = "rejected"
    PROMOTION_REQUESTED = "promotion_requested"


class ExactSourceRevision(_FrozenModel):
    """One repository identity at a full immutable Git object id, never a moving ref."""

    source_id: Identifier
    algorithm: RevisionAlgorithm
    revision: str = Field(pattern=r"^[0-9a-f]{40,64}$")

    @model_validator(mode="after")
    def _validate_revision_width(self) -> Self:
        expected = 40 if self.algorithm is RevisionAlgorithm.GIT_SHA1 else 64
        if len(self.revision) != expected:
            msg = f"{self.algorithm.value} revisions must contain exactly {expected} hexadecimal characters."
            raise ValueError(msg)
        return self


class ProvisionalSourceBounds(_FrozenModel):
    """Minimal source-candidate fields; not a generic Creation or Pattern ABI."""

    exact_base: ExactSourceRevision
    source_tree_digest: Sha256Digest
    allowed_path_roots: tuple[str, ...] = Field(min_length=1, max_length=_MAX_PATHS)

    @field_validator("allowed_path_roots")
    @classmethod
    def _validate_allowed_path_roots(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_validate_relative_path(value) for value in values)
        if len(set(normalized)) != len(normalized):
            msg = "Allowed path roots must be unique."
            raise ValueError(msg)
        return tuple(sorted(normalized))


class ToolPin(_FrozenModel):
    """A tool identity and immutable version input, never an executable adapter."""

    name: Identifier
    version: Identifier
    distribution_digest: Sha256Digest | None = None


class NetworkConstraint(_FrozenModel):
    """A denied or content-addressed admitted policy declaration."""

    mode: NetworkMode = NetworkMode.DENIED
    policy_digest: Sha256Digest | None = None

    @model_validator(mode="after")
    def _validate_policy_binding(self) -> Self:
        if self.mode is NetworkMode.DENIED and self.policy_digest is not None:
            msg = "Denied network declarations cannot carry an admission policy."
            raise ValueError(msg)
        if self.mode is NetworkMode.ADMITTED and self.policy_digest is None:
            msg = "Admitted network declarations must bind an exact policy digest."
            raise ValueError(msg)
        return self


class CandidateBudget(_FrozenModel):
    """Finite candidate and verification ceilings carried by one packet."""

    max_changed_paths: int = Field(ge=1, le=_MAX_PATHS)
    max_artifact_bytes: int = Field(ge=1, le=_MAX_ARTIFACT_BYTES)
    max_verification_checks: int = Field(ge=1, le=_MAX_CHECKS)


class CandidateArtifactRef(ArtifactRef):
    """The shared artifact reference narrowed to Creation's finite record limits."""

    artifact_id: Identifier
    media_type: MediaType
    size: int = Field(ge=0, le=_MAX_ARTIFACT_BYTES)


class VerificationRequirement(_FrozenModel):
    """One pinned deterministic check description; command argv remains inert data."""

    check_id: Identifier
    command: tuple[CommandPart, ...] = Field(min_length=1, max_length=_MAX_COMMAND_PARTS)
    tool: ToolPin
    environment_digest: Sha256Digest
    timeout_seconds: int = Field(ge=1, le=_MAX_TIMEOUT_SECONDS)
    expected_exit_code: int = Field(ge=0, le=255)


class WorkPacket(_FrozenModel):
    """A frozen just-in-time candidate input envelope with no execution authority."""

    schema_version: Literal[1] = 1
    packet_id: Identifier
    creation_request_id: Identifier
    candidate_id: Identifier
    principal_id: Identifier
    source: ProvisionalSourceBounds
    input_digests: tuple[Sha256Digest, ...] = Field(default=(), max_length=_MAX_INPUTS)
    policy_digest: Sha256Digest
    tools: tuple[ToolPin, ...] = Field(default=(), max_length=_MAX_TOOLS)
    declared_effects: tuple[Identifier, ...] = Field(default=(), max_length=_MAX_EFFECTS)
    network: NetworkConstraint = Field(default_factory=NetworkConstraint)
    budget: CandidateBudget
    required_checks: tuple[VerificationRequirement, ...] = Field(min_length=1, max_length=_MAX_CHECKS)
    retention_days: int = Field(ge=1, le=_MAX_RETENTION_DAYS)
    promotion_owner: Identifier
    authorization_class: Identifier
    recovery_plan_digest: Sha256Digest
    compatibility_evidence_digests: tuple[Sha256Digest, ...] = Field(default=(), max_length=_MAX_INPUTS)
    assembled_at: AwareDatetime

    @field_validator("input_digests", "declared_effects", "compatibility_evidence_digests")
    @classmethod
    def _canonicalize_scalar_sets(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """Give set-like packet fields one canonical digest order."""
        return tuple(sorted(values))

    @field_validator("tools")
    @classmethod
    def _canonicalize_tools(cls, values: tuple[ToolPin, ...]) -> tuple[ToolPin, ...]:
        return tuple(sorted(values, key=lambda tool: (tool.name, tool.version, tool.distribution_digest or "")))

    @field_validator("required_checks")
    @classmethod
    def _canonicalize_checks(
        cls,
        values: tuple[VerificationRequirement, ...],
    ) -> tuple[VerificationRequirement, ...]:
        return tuple(sorted(values, key=lambda check: check.check_id))

    @model_validator(mode="after")
    def _validate_packet_sets_and_budget(self) -> Self:
        _require_unique((tool.name for tool in self.tools), label="Tool names")
        _require_unique((check.check_id for check in self.required_checks), label="Verification check ids")
        _require_unique(self.input_digests, label="Input digests")
        _require_unique(self.declared_effects, label="Declared effects")
        _require_unique(self.compatibility_evidence_digests, label="Compatibility evidence digests")
        if len(self.required_checks) > self.budget.max_verification_checks:
            msg = "The verification plan exceeds the packet's check budget."
            raise ValueError(msg)
        pinned_tools = {(tool.name, tool.version, tool.distribution_digest) for tool in self.tools}
        for check in self.required_checks:
            check_tool = (check.tool.name, check.tool.version, check.tool.distribution_digest)
            if check_tool not in pinned_tools:
                msg = f"Verification check {check.check_id!r} uses a tool absent from the packet tool pins."
                raise ValueError(msg)
        return self


class CandidateArtifact(_FrozenModel):
    """An immutable candidate artifact reference outside the active source tree."""

    candidate_id: Identifier
    creation_request_id: Identifier
    packet_id: Identifier
    packet_digest: Sha256Digest
    exact_base: ExactSourceRevision
    source_tree_digest: Sha256Digest
    artifact: CandidateArtifactRef
    changed_paths: tuple[str, ...] = Field(min_length=1, max_length=_MAX_PATHS)
    declared_effects: tuple[Identifier, ...] = Field(default=(), max_length=_MAX_EFFECTS)
    recorded_at: AwareDatetime

    @field_validator("changed_paths")
    @classmethod
    def _validate_changed_paths(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_validate_relative_path(value) for value in values)
        if len(set(normalized)) != len(normalized):
            msg = "Changed paths must be unique."
            raise ValueError(msg)
        return tuple(sorted(normalized))

    @field_validator("declared_effects")
    @classmethod
    def _validate_declared_effects(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        _require_unique(values, label="Candidate declared effects")
        return tuple(sorted(values))


class CustodyReceipt(_FrozenModel):
    """A factual custody attestation; only a matching sealed receipt is eligible."""

    receipt_id: Identifier
    candidate_id: Identifier
    artifact_id: Identifier
    expected_digest: Sha256Digest
    expected_size: int = Field(ge=0, le=_MAX_ARTIFACT_BYTES)
    observed_digest: Sha256Digest | None = None
    observed_size: int | None = Field(default=None, ge=0, le=_MAX_ARTIFACT_BYTES)
    outcome: CustodyOutcome
    custodian_id: Identifier
    recorded_at: AwareDatetime

    @model_validator(mode="after")
    def _validate_outcome_shape(self) -> Self:
        observed = (self.observed_digest, self.observed_size)
        expected = (self.expected_digest, self.expected_size)
        if self.outcome is CustodyOutcome.SEALED and observed != expected:
            msg = "A sealed custody receipt must observe the exact expected digest and size."
            raise ValueError(msg)
        if self.outcome is CustodyOutcome.MISSING and observed != (None, None):
            msg = "A missing custody receipt cannot claim observed bytes."
            raise ValueError(msg)
        if self.outcome is CustodyOutcome.CORRUPT and (None in observed or observed == expected):
            msg = "A corrupt custody receipt must record a non-matching observed digest or size."
            raise ValueError(msg)
        return self


class VerificationReceipt(_FrozenModel):
    """One verifier observation bound to exact candidate, tool, environment, and argv."""

    receipt_id: Identifier
    candidate_id: Identifier
    artifact_digest: Sha256Digest
    exact_base: ExactSourceRevision
    check_id: Identifier
    command: tuple[CommandPart, ...] = Field(min_length=1, max_length=_MAX_COMMAND_PARTS)
    tool: ToolPin
    environment_digest: Sha256Digest
    timeout_seconds: int = Field(ge=1, le=_MAX_TIMEOUT_SECONDS)
    outcome: VerificationOutcome
    exit_code: int | None = Field(default=None, ge=0, le=255)
    error_class: str | None = Field(default=None, min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    result_digest: Sha256Digest
    output_truncated: bool = False
    started_at: AwareDatetime
    completed_at: AwareDatetime

    @model_validator(mode="after")
    def _validate_result_shape(self) -> Self:
        if self.completed_at < self.started_at:
            msg = "Verification completion cannot precede its start."
            raise ValueError(msg)
        if self.outcome is VerificationOutcome.PASSED and (self.exit_code is None or self.error_class is not None):
            msg = "A passed verification requires an exit code and no error class."
            raise ValueError(msg)
        if self.outcome is VerificationOutcome.FAILED and self.exit_code is None:
            msg = "A failed verification requires an observed exit code."
            raise ValueError(msg)
        if self.outcome in {VerificationOutcome.ERROR, VerificationOutcome.TIMED_OUT} and self.error_class is None:
            msg = "Verifier errors and timeouts must retain an error class."
            raise ValueError(msg)
        return self


class RecordBinding(_FrozenModel):
    """Content-addressed binding to one immutable evidence record."""

    record_id: Identifier
    record_digest: Sha256Digest


class EvidenceManifest(_FrozenModel):
    """Exact custody and verification evidence presented for human review."""

    candidate_id: Identifier
    candidate: RecordBinding
    packet_digest: Sha256Digest
    exact_base: ExactSourceRevision
    artifact: CandidateArtifactRef
    custody: RecordBinding
    verification: tuple[RecordBinding, ...] = Field(min_length=1, max_length=_MAX_CHECKS)
    declared_effects: tuple[Identifier, ...] = Field(default=(), max_length=_MAX_EFFECTS)
    compatibility_evidence_digests: tuple[Sha256Digest, ...] = Field(default=(), max_length=_MAX_INPUTS)


class HumanReview(_FrozenModel):
    """A human verdict over one exact manifest; it grants no target-owner authority."""

    review_id: Identifier
    human_principal_id: Identifier
    candidate_id: Identifier
    artifact_digest: Sha256Digest
    exact_base: ExactSourceRevision
    evidence_manifest_digest: Sha256Digest
    decision: ReviewDecision
    reviewed_at: AwareDatetime


class PromotionRequest(_FrozenModel):
    """An inert request for a target owner to revalidate and possibly perform an effect."""

    schema_version: Literal[1] = 1
    promotion_request_id: Identifier
    creation_request_id: Identifier
    candidate_id: Identifier
    candidate: RecordBinding
    packet_id: Identifier
    packet_digest: Sha256Digest
    base_precondition: ExactSourceRevision
    source_tree_digest_precondition: Sha256Digest
    artifact: CandidateArtifactRef
    custody: RecordBinding
    verification: tuple[RecordBinding, ...] = Field(min_length=1, max_length=_MAX_CHECKS)
    evidence_manifest_digest: Sha256Digest
    review: RecordBinding
    declared_effects: tuple[Identifier, ...] = Field(default=(), max_length=_MAX_EFFECTS)
    compatibility_evidence_digests: tuple[Sha256Digest, ...] = Field(default=(), max_length=_MAX_INPUTS)
    recovery_plan_digest: Sha256Digest
    promotion_owner: Identifier
    authorization_class: Identifier
    inert: Literal[True] = True


class CreationSnapshot(_FrozenModel):
    """Immutable projection of one row in the process-local state machine."""

    phase: CreationPhase
    packet: WorkPacket
    candidate: CandidateArtifact | None = None
    custody: CustodyReceipt | None = None
    verification: tuple[VerificationReceipt, ...] = ()
    review: HumanReview | None = None
    promotion_request: PromotionRequest | None = None


def _validate_relative_path(value: str) -> str:
    if not value or len(value) > _MAX_PATH_LENGTH:
        msg = f"Candidate paths must contain between 1 and {_MAX_PATH_LENGTH} characters."
        raise ValueError(msg)
    if "\\" in value or "\x00" in value:
        msg = "Candidate paths must use normalized POSIX syntax."
        raise ValueError(msg)
    parts = value.split("/")
    if value.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        msg = "Candidate paths must be normalized repository-relative paths without traversal."
        raise ValueError(msg)
    normalized = str(PurePosixPath(value))
    if normalized != value:
        msg = "Candidate paths must already be normalized."
        raise ValueError(msg)
    return normalized


def _require_unique(values: Iterable[str], *, label: str) -> None:
    materialized = tuple(values)
    if len(set(materialized)) != len(materialized):
        msg = f"{label} must be unique."
        raise ValueError(msg)


def promotion_request_id(*, candidate_id: str, manifest_digest: str, review_digest: str) -> str:
    """Derive an idempotent request identity from the exact reviewed evidence."""
    payload = f"{candidate_id}\0{manifest_digest}\0{review_digest}".encode()
    return f"promotion-{hashlib.sha256(payload).hexdigest()}"


def path_is_within_roots(path: str, roots: tuple[str, ...]) -> bool:
    """Compare canonical path parts so lexical siblings never match a root."""
    path_parts = PurePosixPath(path).parts
    for root in roots:
        root_parts = PurePosixPath(root).parts
        if path_parts[: len(root_parts)] == root_parts:
            return True
    return False
