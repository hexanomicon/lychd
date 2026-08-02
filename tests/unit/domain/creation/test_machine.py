from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lychd.domain.creation import (
    CandidateArtifact,
    CandidateArtifactRef,
    CandidateBudget,
    CreationConflictError,
    CreationEligibilityError,
    CreationInvariantError,
    CreationPhase,
    CustodyOutcome,
    CustodyReceipt,
    ExactSourceRevision,
    HumanReview,
    InMemoryCreationStateMachine,
    NetworkConstraint,
    ProvisionalSourceBounds,
    ReviewDecision,
    RevisionAlgorithm,
    ToolPin,
    VerificationOutcome,
    VerificationReceipt,
    VerificationRequirement,
    WorkPacket,
)

NOW = datetime(2026, 1, 2, 3, 4, tzinfo=UTC)


def _digest(character: str) -> str:
    return f"sha256:{character * 64}"


def _base(character: str = "a") -> ExactSourceRevision:
    return ExactSourceRevision(
        source_id="repo",
        algorithm=RevisionAlgorithm.GIT_SHA1,
        revision=character * 40,
    )


def _tool() -> ToolPin:
    return ToolPin(name="ruff", version="0.14.14", distribution_digest=_digest("b"))


def _requirement(check_id: str, command: tuple[str, ...]) -> VerificationRequirement:
    return VerificationRequirement(
        check_id=check_id,
        command=command,
        tool=_tool(),
        environment_digest=_digest("c"),
        timeout_seconds=30,
        expected_exit_code=0,
    )


def _packet(
    *,
    budget: CandidateBudget | None = None,
    allowed_path_roots: tuple[str, ...] = ("src/lychd",),
) -> WorkPacket:
    checks = (
        _requirement("lint", ("ruff", "check", "src/lychd/example.py")),
        _requirement("test", ("pytest", "tests/unit/example")),
    )
    return WorkPacket(
        packet_id="packet-1",
        creation_request_id="request-1",
        candidate_id="candidate-1",
        principal_id="principal-1",
        source=ProvisionalSourceBounds(
            exact_base=_base(),
            source_tree_digest=_digest("d"),
            allowed_path_roots=allowed_path_roots,
        ),
        input_digests=(_digest("e"),),
        policy_digest=_digest("f"),
        tools=(_tool(),),
        declared_effects=("source.patch",),
        network=NetworkConstraint(),
        budget=budget
        or CandidateBudget(
            max_changed_paths=2,
            max_artifact_bytes=1_024,
            max_verification_checks=2,
        ),
        required_checks=checks,
        retention_days=30,
        promotion_owner="source-owner",
        authorization_class="source-promotion",
        recovery_plan_digest=_digest("1"),
        compatibility_evidence_digests=(_digest("2"),),
        assembled_at=NOW,
    )


def test_work_packet_digest_canonicalizes_set_like_fields() -> None:
    packet = _packet()
    second_tool = ToolPin(name="pytest", version="9.0.2", distribution_digest=_digest("8"))
    payload = packet.model_dump(mode="python")
    forward = WorkPacket.model_validate(
        {
            **payload,
            "input_digests": (_digest("7"), _digest("6")),
            "tools": (packet.tools[0], second_tool),
            "declared_effects": ("source.write", "source.patch"),
            "required_checks": packet.required_checks,
            "compatibility_evidence_digests": (_digest("5"), _digest("4")),
        }
    )
    reversed_order = WorkPacket.model_validate(
        {
            **payload,
            "input_digests": tuple(reversed(forward.input_digests)),
            "tools": tuple(reversed(forward.tools)),
            "declared_effects": tuple(reversed(forward.declared_effects)),
            "required_checks": tuple(reversed(forward.required_checks)),
            "compatibility_evidence_digests": tuple(reversed(forward.compatibility_evidence_digests)),
        }
    )

    assert reversed_order == forward
    assert reversed_order.digest == forward.digest


def _candidate(
    packet: WorkPacket,
    *,
    base: ExactSourceRevision | None = None,
    source_tree_digest: str | None = None,
    paths: tuple[str, ...] = ("src/lychd/example.py",),
    size: int = 256,
    recorded_at: datetime = NOW,
) -> CandidateArtifact:
    return CandidateArtifact(
        candidate_id=packet.candidate_id,
        creation_request_id=packet.creation_request_id,
        packet_id=packet.packet_id,
        packet_digest=packet.digest,
        exact_base=base or packet.source.exact_base,
        source_tree_digest=source_tree_digest or packet.source.source_tree_digest,
        artifact=CandidateArtifactRef(
            artifact_id="artifact-1",
            digest=_digest("3"),
            media_type="text/x-diff",
            size=size,
            classification="private",
        ),
        changed_paths=paths,
        declared_effects=packet.declared_effects,
        recorded_at=recorded_at,
    )


def _custody(
    candidate: CandidateArtifact,
    *,
    outcome: CustodyOutcome = CustodyOutcome.SEALED,
    expected_digest: str | None = None,
    recorded_at: datetime = NOW,
) -> CustodyReceipt:
    expected = expected_digest or candidate.artifact.digest
    if outcome is CustodyOutcome.SEALED:
        observed_digest = expected
        observed_size = candidate.artifact.size
    elif outcome is CustodyOutcome.MISSING:
        observed_digest = None
        observed_size = None
    else:
        observed_digest = _digest("9")
        observed_size = candidate.artifact.size
    return CustodyReceipt(
        receipt_id="custody-1",
        candidate_id=candidate.candidate_id,
        artifact_id=candidate.artifact.artifact_id,
        expected_digest=expected,
        expected_size=candidate.artifact.size,
        observed_digest=observed_digest,
        observed_size=observed_size,
        outcome=outcome,
        custodian_id="artifact-store",
        recorded_at=recorded_at,
    )


def _receipt(
    candidate: CandidateArtifact,
    requirement: VerificationRequirement,
    *,
    outcome: VerificationOutcome = VerificationOutcome.PASSED,
    command: tuple[str, ...] | None = None,
    tool: ToolPin | None = None,
    environment_digest: str | None = None,
    timeout_seconds: int | None = None,
    started_at: datetime = NOW,
    completed_at: datetime | None = None,
) -> VerificationReceipt:
    return VerificationReceipt(
        receipt_id=f"receipt-{requirement.check_id}",
        candidate_id=candidate.candidate_id,
        artifact_digest=candidate.artifact.digest,
        exact_base=candidate.exact_base,
        check_id=requirement.check_id,
        command=command or requirement.command,
        tool=tool or requirement.tool,
        environment_digest=environment_digest or requirement.environment_digest,
        timeout_seconds=timeout_seconds or requirement.timeout_seconds,
        outcome=outcome,
        exit_code=0 if outcome is VerificationOutcome.PASSED else 1,
        error_class=None,
        result_digest=_digest("4" if requirement.check_id == "lint" else "5"),
        started_at=started_at,
        completed_at=completed_at or started_at + timedelta(seconds=1),
    )


def _machine_with_candidate(
    *,
    packet: WorkPacket | None = None,
    candidate: CandidateArtifact | None = None,
) -> tuple[InMemoryCreationStateMachine, WorkPacket, CandidateArtifact]:
    selected_packet = packet or _packet()
    selected_candidate = candidate or _candidate(selected_packet)
    machine = InMemoryCreationStateMachine()
    machine.admit(selected_packet)
    machine.record_candidate(selected_candidate)
    return machine, selected_packet, selected_candidate


def _machine_with_evidence() -> tuple[InMemoryCreationStateMachine, WorkPacket, CandidateArtifact]:
    machine, packet, candidate = _machine_with_candidate()
    machine.record_custody(_custody(candidate))
    for requirement in packet.required_checks:
        machine.record_verification(_receipt(candidate, requirement))
    return machine, packet, candidate


def _review(
    machine: InMemoryCreationStateMachine,
    candidate: CandidateArtifact,
    *,
    decision: ReviewDecision = ReviewDecision.REQUEST_PROMOTION,
    manifest_digest: str | None = None,
    reviewed_at: datetime = NOW + timedelta(minutes=1),
) -> HumanReview:
    manifest = machine.evidence_manifest(candidate.candidate_id)
    return HumanReview(
        review_id="review-1",
        human_principal_id="magus",
        candidate_id=candidate.candidate_id,
        artifact_digest=candidate.artifact.digest,
        exact_base=candidate.exact_base,
        evidence_manifest_digest=manifest_digest or manifest.digest,
        decision=decision,
        reviewed_at=reviewed_at,
    )


def test_candidate_refuses_packet_base_drift() -> None:
    packet = _packet()
    machine = InMemoryCreationStateMachine()
    machine.admit(packet)

    with pytest.raises(CreationInvariantError, match="exact base"):
        machine.record_candidate(_candidate(packet, base=_base("b")))


def test_candidate_refuses_packet_source_tree_drift() -> None:
    packet = _packet()
    machine = InMemoryCreationStateMachine()
    machine.admit(packet)

    with pytest.raises(CreationInvariantError, match="source tree"):
        machine.record_candidate(_candidate(packet, source_tree_digest=_digest("8")))


def test_candidate_record_id_cannot_be_reused_by_evidence() -> None:
    machine, _packet_record, candidate = _machine_with_candidate()
    colliding = _custody(candidate).model_copy(update={"receipt_id": candidate.candidate_id})

    with pytest.raises(CreationConflictError, match="already bound to different content"):
        machine.record_custody(colliding)


def test_candidate_and_evidence_chronology_must_be_possible() -> None:
    packet = _packet()
    machine = InMemoryCreationStateMachine()
    machine.admit(packet)
    with pytest.raises(CreationInvariantError, match="predate its WorkPacket"):
        machine.record_candidate(_candidate(packet, recorded_at=NOW - timedelta(seconds=1)))

    candidate = _candidate(packet, recorded_at=NOW + timedelta(seconds=2))
    machine.record_candidate(candidate)
    with pytest.raises(CreationInvariantError, match="Custody receipt cannot predate"):
        machine.record_custody(_custody(candidate, recorded_at=NOW + timedelta(seconds=1)))
    with pytest.raises(CreationInvariantError, match="Verification receipt cannot predate"):
        machine.record_verification(
            _receipt(candidate, packet.required_checks[0], started_at=NOW + timedelta(seconds=1))
        )


def test_candidate_refuses_path_sibling_and_traversal() -> None:
    packet = _packet()
    machine = InMemoryCreationStateMachine()
    machine.admit(packet)

    with pytest.raises(CreationInvariantError, match="outside the admitted roots"):
        machine.record_candidate(_candidate(packet, paths=("src/lychd-other/escape.py",)))
    with pytest.raises(ValidationError, match="without traversal"):
        _candidate(packet, paths=("src/lychd/../escape.py",))


@pytest.mark.parametrize(
    ("budget", "paths", "size", "message"),
    [
        (
            CandidateBudget(max_changed_paths=1, max_artifact_bytes=1_024, max_verification_checks=2),
            ("src/lychd/a.py", "src/lychd/b.py"),
            256,
            "changed-path count",
        ),
        (
            CandidateBudget(max_changed_paths=2, max_artifact_bytes=128, max_verification_checks=2),
            ("src/lychd/a.py",),
            256,
            "artifact size",
        ),
    ],
)
def test_candidate_refuses_path_and_artifact_budget_overrun(
    budget: CandidateBudget,
    paths: tuple[str, ...],
    size: int,
    message: str,
) -> None:
    packet = _packet(budget=budget)
    machine = InMemoryCreationStateMachine()
    machine.admit(packet)

    with pytest.raises(CreationInvariantError, match=message):
        machine.record_candidate(_candidate(packet, paths=paths, size=size))


def test_custody_must_bind_exact_candidate_artifact() -> None:
    machine, _packet_record, candidate = _machine_with_candidate()

    with pytest.raises(CreationEligibilityError, match="no custody receipt"):
        machine.evidence_manifest(candidate.candidate_id)
    with pytest.raises(CreationInvariantError, match="exact identity, digest, and size"):
        machine.record_custody(_custody(candidate, expected_digest=_digest("8")))


@pytest.mark.parametrize("outcome", [CustodyOutcome.MISSING, CustodyOutcome.CORRUPT])
def test_nonsealed_custody_can_never_make_candidate_eligible(outcome: CustodyOutcome) -> None:
    machine, _packet_record, candidate = _machine_with_candidate()
    machine.record_custody(_custody(candidate, outcome=outcome))

    with pytest.raises(CreationEligibilityError, match=f"custody is {outcome.value}"):
        machine.evidence_manifest(candidate.candidate_id)


def test_verification_receipt_must_match_pinned_deterministic_inputs() -> None:
    machine, packet, candidate = _machine_with_candidate()
    requirement = packet.required_checks[0]
    variants = (
        (_receipt(candidate, requirement, command=("ruff", "check", "src/lychd/other.py")), "command"),
        (_receipt(candidate, requirement, tool=ToolPin(name="ruff", version="future")), "tool"),
        (_receipt(candidate, requirement, environment_digest=_digest("8")), "environment"),
        (_receipt(candidate, requirement, timeout_seconds=31), "timeout"),
    )

    for receipt, mismatch in variants:
        with pytest.raises(CreationInvariantError, match=mismatch):
            machine.record_verification(receipt)


def test_missing_or_failed_required_check_blocks_review_and_cannot_be_overwritten() -> None:
    machine, packet, candidate = _machine_with_candidate()
    machine.record_custody(_custody(candidate))
    lint, test = packet.required_checks
    machine.record_verification(_receipt(candidate, lint))

    with pytest.raises(CreationEligibilityError, match="missing required verification"):
        machine.evidence_manifest(candidate.candidate_id)

    failed = _receipt(candidate, test, outcome=VerificationOutcome.FAILED)
    machine.record_verification(failed)
    with pytest.raises(CreationEligibilityError, match="unsuccessful required checks"):
        machine.evidence_manifest(candidate.candidate_id)
    with pytest.raises(CreationConflictError, match="immutable receipt"):
        machine.record_verification(_receipt(candidate, test))


def test_review_must_bind_exact_eligible_manifest() -> None:
    machine, _packet_record, candidate = _machine_with_evidence()

    manifest = machine.evidence_manifest(candidate.candidate_id)
    assert manifest.candidate.record_id == candidate.candidate_id
    assert manifest.candidate.record_digest == candidate.digest

    with pytest.raises(CreationInvariantError, match="evidence manifest"):
        machine.record_review(_review(machine, candidate, manifest_digest=_digest("0")))


def test_review_cannot_predate_eligible_evidence() -> None:
    machine, _packet_record, candidate = _machine_with_evidence()

    with pytest.raises(CreationInvariantError, match="cannot predate"):
        machine.record_review(_review(machine, candidate, reviewed_at=NOW))


def test_promotion_requires_explicit_positive_human_review() -> None:
    machine, _packet_record, candidate = _machine_with_evidence()

    with pytest.raises(CreationEligibilityError, match="no explicit human review"):
        machine.request_promotion(
            candidate.candidate_id,
            current_base=candidate.exact_base,
            current_source_tree_digest=candidate.source_tree_digest,
        )

    machine.record_review(_review(machine, candidate, decision=ReviewDecision.REJECT))
    assert machine.get(candidate.candidate_id).phase is CreationPhase.REJECTED
    with pytest.raises(CreationEligibilityError, match="did not request promotion"):
        machine.request_promotion(
            candidate.candidate_id,
            current_base=candidate.exact_base,
            current_source_tree_digest=candidate.source_tree_digest,
        )


def test_promotion_refuses_current_base_drift_after_review() -> None:
    machine, _packet_record, candidate = _machine_with_evidence()
    machine.record_review(_review(machine, candidate))

    with pytest.raises(CreationEligibilityError, match="base drifted"):
        machine.request_promotion(
            candidate.candidate_id,
            current_base=_base("b"),
            current_source_tree_digest=candidate.source_tree_digest,
        )


def test_promotion_refuses_current_source_tree_drift_after_review() -> None:
    machine, _packet_record, candidate = _machine_with_evidence()
    machine.record_review(_review(machine, candidate))

    with pytest.raises(CreationEligibilityError, match="source tree drifted"):
        machine.request_promotion(
            candidate.candidate_id,
            current_base=candidate.exact_base,
            current_source_tree_digest=_digest("8"),
        )


def test_positive_path_emits_only_stable_inert_promotion_request() -> None:
    machine, packet, candidate = _machine_with_evidence()
    review = _review(machine, candidate)
    machine.record_review(review)

    first = machine.request_promotion(
        candidate.candidate_id,
        current_base=candidate.exact_base,
        current_source_tree_digest=candidate.source_tree_digest,
    )
    second = machine.request_promotion(
        candidate.candidate_id,
        current_base=candidate.exact_base,
        current_source_tree_digest=candidate.source_tree_digest,
    )

    assert first is second
    assert first.inert is True
    assert first.base_precondition == candidate.exact_base
    assert first.source_tree_digest_precondition == candidate.source_tree_digest
    assert first.candidate.record_digest == candidate.digest
    assert first.packet_digest == packet.digest
    assert first.review.record_id == review.review_id
    assert first.promotion_owner == packet.promotion_owner
    assert machine.get(candidate.candidate_id).phase is CreationPhase.PROMOTION_REQUESTED

    machine.record_custody(_custody(candidate))
    for requirement in packet.required_checks:
        machine.record_verification(_receipt(candidate, requirement))


def test_promotion_request_id_cannot_reuse_an_existing_candidate_record_id() -> None:
    preview, _preview_packet, preview_candidate = _machine_with_evidence()
    preview.record_review(_review(preview, preview_candidate))
    promotion_id = preview.request_promotion(
        preview_candidate.candidate_id,
        current_base=preview_candidate.exact_base,
        current_source_tree_digest=preview_candidate.source_tree_digest,
    ).promotion_request_id

    machine, _packet_record, candidate = _machine_with_evidence()
    machine.record_review(_review(machine, candidate))
    colliding_packet = _packet().model_copy(
        update={
            "packet_id": "packet-2",
            "creation_request_id": "request-2",
            "candidate_id": promotion_id,
        }
    )
    machine.admit(colliding_packet)
    machine.record_candidate(_candidate(colliding_packet))

    with pytest.raises(CreationConflictError, match="already bound to different content"):
        machine.request_promotion(
            candidate.candidate_id,
            current_base=candidate.exact_base,
            current_source_tree_digest=candidate.source_tree_digest,
        )
    assert machine.get(candidate.candidate_id).promotion_request is None
