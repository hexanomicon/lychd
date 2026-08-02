"""Process-local Creation evidence state machine with no physical effects."""

from __future__ import annotations

from dataclasses import dataclass, field

from lychd.domain.creation.contracts import (
    CandidateArtifact,
    CreationPhase,
    CreationSnapshot,
    CustodyOutcome,
    CustodyReceipt,
    EvidenceManifest,
    ExactSourceRevision,
    HumanReview,
    PromotionRequest,
    RecordBinding,
    ReviewDecision,
    Sha256Digest,
    VerificationOutcome,
    VerificationReceipt,
    VerificationRequirement,
    WorkPacket,
    path_is_within_roots,
    promotion_request_id,
)

__all__ = [
    "CreationConflictError",
    "CreationEligibilityError",
    "CreationInvariantError",
    "InMemoryCreationStateMachine",
    "UnknownCreationCandidateError",
]


class CreationInvariantError(ValueError):
    """Raised when a record contradicts its packet or candidate identity."""


class CreationEligibilityError(RuntimeError):
    """Raised when evidence cannot support review or a promotion request."""


class CreationConflictError(RuntimeError):
    """Raised when an immutable identity is replayed with different content."""


class UnknownCreationCandidateError(LookupError):
    """Raised when an operation names no admitted WorkPacket candidate."""


@dataclass
class _CreationRow:
    packet: WorkPacket
    candidate: CandidateArtifact | None = None
    custody: CustodyReceipt | None = None
    verification: dict[str, VerificationReceipt] = field(default_factory=dict)
    review: HumanReview | None = None
    promotion_request: PromotionRequest | None = None


class InMemoryCreationStateMachine:
    """Retain immutable candidate evidence and emit only an inert request.

    The machine has no filesystem, process, network, database, workspace, VCS, or
    target-owner adapter. Its command tuples are compared as data and are never run.
    """

    def __init__(self) -> None:
        """Create an empty process-local evidence ledger."""
        self._rows: dict[str, _CreationRow] = {}
        self._packet_candidates: dict[str, str] = {}
        self._record_owners: dict[str, tuple[str, object]] = {}

    def admit(self, packet: WorkPacket) -> CreationSnapshot:
        """Admit one frozen packet identity idempotently."""
        existing = self._rows.get(packet.candidate_id)
        if existing is not None:
            if existing.packet != packet:
                msg = f"Candidate id {packet.candidate_id!r} is already bound to another WorkPacket."
                raise CreationConflictError(msg)
            return self._snapshot(existing)
        packet_owner = self._packet_candidates.get(packet.packet_id)
        if packet_owner is not None:
            msg = f"WorkPacket id {packet.packet_id!r} is already bound to candidate {packet_owner!r}."
            raise CreationConflictError(msg)
        row = _CreationRow(packet=packet)
        self._rows[packet.candidate_id] = row
        self._packet_candidates[packet.packet_id] = packet.candidate_id
        return self._snapshot(row)

    def record_candidate(self, candidate: CandidateArtifact) -> CreationSnapshot:
        """Bind one quarantined artifact reference after identity, path, and budget checks."""
        row = self._require(candidate.candidate_id)
        if row.candidate is not None:
            if row.candidate != candidate:
                msg = f"Candidate artifact {candidate.candidate_id!r} is already immutable."
                raise CreationConflictError(msg)
            return self._snapshot(row)
        packet = row.packet
        mismatches = {
            "creation request": candidate.creation_request_id != packet.creation_request_id,
            "packet id": candidate.packet_id != packet.packet_id,
            "packet digest": candidate.packet_digest != packet.digest,
            "exact base": candidate.exact_base != packet.source.exact_base,
            "source tree": candidate.source_tree_digest != packet.source.source_tree_digest,
            "declared effects": set(candidate.declared_effects) != set(packet.declared_effects),
        }
        invalid = [label for label, mismatch in mismatches.items() if mismatch]
        if invalid:
            msg = f"Candidate artifact does not match its WorkPacket: {', '.join(invalid)}."
            raise CreationInvariantError(msg)
        if candidate.recorded_at < packet.assembled_at:
            msg = "Candidate artifact cannot predate its WorkPacket assembly."
            raise CreationInvariantError(msg)
        outside = [
            path for path in candidate.changed_paths if not path_is_within_roots(path, packet.source.allowed_path_roots)
        ]
        if outside:
            msg = f"Candidate paths fall outside the admitted roots: {', '.join(outside)}."
            raise CreationInvariantError(msg)
        if len(candidate.changed_paths) > packet.budget.max_changed_paths:
            msg = "Candidate changed-path count exceeds its WorkPacket budget."
            raise CreationInvariantError(msg)
        if candidate.artifact.size > packet.budget.max_artifact_bytes:
            msg = "Candidate artifact size exceeds its WorkPacket budget."
            raise CreationInvariantError(msg)
        self._claim_record(candidate.candidate_id, candidate.candidate_id, candidate)
        row.candidate = candidate
        return self._snapshot(row)

    def record_custody(self, receipt: CustodyReceipt) -> CreationSnapshot:
        """Retain the first custody observation without treating model shape as truth."""
        row = self._require(receipt.candidate_id)
        candidate = self._require_candidate(row)
        if row.custody is not None:
            if row.custody != receipt:
                msg = f"Candidate {receipt.candidate_id!r} already has an immutable custody receipt."
                raise CreationConflictError(msg)
            return self._snapshot(row)
        self._require_evidence_open(row)
        expected = candidate.artifact
        if (
            receipt.artifact_id != expected.artifact_id
            or receipt.expected_digest != expected.digest
            or receipt.expected_size != expected.size
        ):
            msg = "Custody receipt does not bind the candidate artifact's exact identity, digest, and size."
            raise CreationInvariantError(msg)
        if receipt.recorded_at < candidate.recorded_at:
            msg = "Custody receipt cannot predate the candidate artifact."
            raise CreationInvariantError(msg)
        self._claim_record(receipt.receipt_id, receipt.candidate_id, receipt)
        row.custody = receipt
        return self._snapshot(row)

    def record_verification(self, receipt: VerificationReceipt) -> CreationSnapshot:
        """Retain one exact planned verifier observation; never execute its argv."""
        row = self._require(receipt.candidate_id)
        candidate = self._require_candidate(row)
        requirement = self._require_check(row.packet, receipt.check_id)
        self._validate_verification_receipt(row, candidate, requirement, receipt)
        if receipt.started_at < candidate.recorded_at:
            msg = "Verification receipt cannot predate the candidate artifact."
            raise CreationInvariantError(msg)
        existing = row.verification.get(receipt.check_id)
        if existing is not None:
            if existing != receipt:
                msg = f"Verification check {receipt.check_id!r} already has an immutable receipt."
                raise CreationConflictError(msg)
            return self._snapshot(row)
        self._require_evidence_open(row)
        self._claim_record(receipt.receipt_id, receipt.candidate_id, receipt)
        row.verification[receipt.check_id] = receipt
        return self._snapshot(row)

    def evidence_manifest(self, candidate_id: str) -> EvidenceManifest:
        """Build exact review evidence only when custody and every required check pass."""
        row = self._require(candidate_id)
        candidate = self._require_candidate(row)
        custody = row.custody
        if custody is None:
            msg = "Candidate has no custody receipt."
            raise CreationEligibilityError(msg)
        if custody.outcome is not CustodyOutcome.SEALED:
            msg = f"Candidate custody is {custody.outcome.value}, not sealed."
            raise CreationEligibilityError(msg)
        required = {check.check_id: check for check in row.packet.required_checks}
        missing = sorted(required.keys() - row.verification.keys())
        if missing:
            msg = f"Candidate is missing required verification receipts: {', '.join(missing)}."
            raise CreationEligibilityError(msg)
        failed = sorted(
            check_id
            for check_id, receipt in row.verification.items()
            if receipt.outcome is not VerificationOutcome.PASSED
            or receipt.exit_code != required[check_id].expected_exit_code
        )
        if failed:
            msg = f"Candidate has unsuccessful required checks: {', '.join(failed)}."
            raise CreationEligibilityError(msg)
        verification = tuple(
            RecordBinding(record_id=receipt.receipt_id, record_digest=receipt.digest)
            for check_id in sorted(required)
            for receipt in (row.verification[check_id],)
        )
        return EvidenceManifest(
            candidate_id=candidate.candidate_id,
            candidate=RecordBinding(record_id=candidate.candidate_id, record_digest=candidate.digest),
            packet_digest=row.packet.digest,
            exact_base=candidate.exact_base,
            artifact=candidate.artifact,
            custody=RecordBinding(record_id=custody.receipt_id, record_digest=custody.digest),
            verification=verification,
            declared_effects=tuple(sorted(candidate.declared_effects)),
            compatibility_evidence_digests=tuple(sorted(row.packet.compatibility_evidence_digests)),
        )

    def record_review(self, review: HumanReview) -> CreationSnapshot:
        """Retain the first explicit human verdict over the exact eligible evidence."""
        row = self._require(review.candidate_id)
        candidate = self._require_candidate(row)
        if row.review is not None:
            if row.review != review:
                msg = f"Candidate {review.candidate_id!r} already has an immutable human review."
                raise CreationConflictError(msg)
            return self._snapshot(row)
        manifest = self.evidence_manifest(review.candidate_id)
        mismatches = {
            "artifact digest": review.artifact_digest != candidate.artifact.digest,
            "exact base": review.exact_base != candidate.exact_base,
            "evidence manifest": review.evidence_manifest_digest != manifest.digest,
        }
        invalid = [label for label, mismatch in mismatches.items() if mismatch]
        if invalid:
            msg = f"Human review does not match the candidate's exact evidence: {', '.join(invalid)}."
            raise CreationInvariantError(msg)
        evidence_completed_at = max(
            row.custody.recorded_at if row.custody is not None else candidate.recorded_at,
            *(receipt.completed_at for receipt in row.verification.values()),
        )
        if review.reviewed_at < evidence_completed_at:
            msg = "Human review cannot predate the custody and verification evidence it judges."
            raise CreationInvariantError(msg)
        self._claim_record(review.review_id, review.candidate_id, review)
        row.review = review
        return self._snapshot(row)

    def request_promotion(
        self,
        candidate_id: str,
        *,
        current_base: ExactSourceRevision,
        current_source_tree_digest: Sha256Digest,
    ) -> PromotionRequest:
        """Emit an inert request after rechecking source, custody, checks, and review."""
        row = self._require(candidate_id)
        candidate = self._require_candidate(row)
        if current_base != candidate.exact_base:
            msg = "Current source base drifted from the candidate's exact base precondition."
            raise CreationEligibilityError(msg)
        if current_source_tree_digest != candidate.source_tree_digest:
            msg = "Current source tree drifted from the candidate's exact tree precondition."
            raise CreationEligibilityError(msg)
        review = row.review
        if review is None:
            msg = "Candidate has no explicit human review."
            raise CreationEligibilityError(msg)
        if review.decision is not ReviewDecision.REQUEST_PROMOTION:
            msg = "Human review did not request promotion."
            raise CreationEligibilityError(msg)
        manifest = self.evidence_manifest(candidate_id)
        if review.evidence_manifest_digest != manifest.digest:
            msg = "Human review no longer binds the exact eligible evidence manifest."
            raise CreationEligibilityError(msg)
        if row.promotion_request is not None:
            return row.promotion_request
        review_binding = RecordBinding(record_id=review.review_id, record_digest=review.digest)
        request = PromotionRequest(
            promotion_request_id=promotion_request_id(
                candidate_id=candidate_id,
                manifest_digest=manifest.digest,
                review_digest=review.digest,
            ),
            creation_request_id=row.packet.creation_request_id,
            candidate_id=candidate_id,
            candidate=manifest.candidate,
            packet_id=row.packet.packet_id,
            packet_digest=row.packet.digest,
            base_precondition=candidate.exact_base,
            source_tree_digest_precondition=candidate.source_tree_digest,
            artifact=candidate.artifact,
            custody=manifest.custody,
            verification=manifest.verification,
            evidence_manifest_digest=manifest.digest,
            review=review_binding,
            declared_effects=manifest.declared_effects,
            compatibility_evidence_digests=manifest.compatibility_evidence_digests,
            recovery_plan_digest=row.packet.recovery_plan_digest,
            promotion_owner=row.packet.promotion_owner,
            authorization_class=row.packet.authorization_class,
        )
        self._claim_record(request.promotion_request_id, request.candidate_id, request)
        row.promotion_request = request
        return request

    def get(self, candidate_id: str) -> CreationSnapshot:
        """Return an immutable projection of one admitted candidate."""
        return self._snapshot(self._require(candidate_id))

    def _snapshot(self, row: _CreationRow) -> CreationSnapshot:
        return CreationSnapshot(
            phase=self._phase(row),
            packet=row.packet,
            candidate=row.candidate,
            custody=row.custody,
            verification=tuple(row.verification[key] for key in sorted(row.verification)),
            review=row.review,
            promotion_request=row.promotion_request,
        )

    def _phase(self, row: _CreationRow) -> CreationPhase:
        if row.promotion_request is not None:
            phase = CreationPhase.PROMOTION_REQUESTED
        elif row.review is not None:
            phase = CreationPhase.REJECTED if row.review.decision is ReviewDecision.REJECT else CreationPhase.REVIEWED
        elif row.candidate is None:
            phase = CreationPhase.PACKET_ADMITTED
        elif row.custody is None and not row.verification:
            phase = CreationPhase.CANDIDATE_RECORDED
        elif self._is_eligible_for_review(row):
            phase = CreationPhase.ELIGIBLE_FOR_REVIEW
        else:
            phase = CreationPhase.EVIDENCE_RECORDED
        return phase

    def _is_eligible_for_review(self, row: _CreationRow) -> bool:
        try:
            self.evidence_manifest(row.packet.candidate_id)
        except CreationEligibilityError:
            return False
        return True

    def _require(self, candidate_id: str) -> _CreationRow:
        try:
            return self._rows[candidate_id]
        except KeyError as exc:
            msg = f"Unknown Creation candidate: {candidate_id}"
            raise UnknownCreationCandidateError(msg) from exc

    @staticmethod
    def _require_candidate(row: _CreationRow) -> CandidateArtifact:
        if row.candidate is None:
            msg = f"Candidate {row.packet.candidate_id!r} has no artifact record."
            raise CreationEligibilityError(msg)
        return row.candidate

    @staticmethod
    def _require_evidence_open(row: _CreationRow) -> None:
        if row.review is not None:
            msg = "Candidate evidence is frozen after human review."
            raise CreationConflictError(msg)

    @staticmethod
    def _require_check(packet: WorkPacket, check_id: str) -> VerificationRequirement:
        for requirement in packet.required_checks:
            if requirement.check_id == check_id:
                return requirement
        msg = f"Verification check {check_id!r} was not required by the WorkPacket."
        raise CreationInvariantError(msg)

    @staticmethod
    def _validate_verification_receipt(
        row: _CreationRow,
        candidate: CandidateArtifact,
        requirement: VerificationRequirement,
        receipt: VerificationReceipt,
    ) -> None:
        mismatches = {
            "artifact digest": receipt.artifact_digest != candidate.artifact.digest,
            "exact base": receipt.exact_base != candidate.exact_base,
            "command": receipt.command != requirement.command,
            "tool": receipt.tool != requirement.tool,
            "environment": receipt.environment_digest != requirement.environment_digest,
            "timeout": receipt.timeout_seconds != requirement.timeout_seconds,
            "packet candidate": receipt.candidate_id != row.packet.candidate_id,
        }
        invalid = [label for label, mismatch in mismatches.items() if mismatch]
        if invalid:
            msg = f"Verification receipt does not match its pinned requirement: {', '.join(invalid)}."
            raise CreationInvariantError(msg)

    def _claim_record(self, record_id: str, candidate_id: str, record: object) -> None:
        existing = self._record_owners.get(record_id)
        if existing is None:
            self._record_owners[record_id] = (candidate_id, record)
            return
        if existing != (candidate_id, record):
            msg = f"Evidence record id {record_id!r} is already bound to different content."
            raise CreationConflictError(msg)
