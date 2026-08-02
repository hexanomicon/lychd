from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lychd.domain.creation import (
    CandidateArtifactRef,
    CandidateBudget,
    ExactSourceRevision,
    NetworkConstraint,
    NetworkMode,
    ProvisionalSourceBounds,
    RevisionAlgorithm,
    ToolPin,
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


def _requirement(check_id: str = "lint") -> VerificationRequirement:
    return VerificationRequirement(
        check_id=check_id,
        command=("ruff", "check", "src/lychd/example.py"),
        tool=_tool(),
        environment_digest=_digest("c"),
        timeout_seconds=30,
        expected_exit_code=0,
    )


def _packet(**changes: object) -> WorkPacket:
    values: dict[str, object] = {
        "packet_id": "packet-1",
        "creation_request_id": "request-1",
        "candidate_id": "candidate-1",
        "principal_id": "principal-1",
        "source": ProvisionalSourceBounds(
            exact_base=_base(),
            source_tree_digest=_digest("d"),
            allowed_path_roots=("src/lychd",),
        ),
        "input_digests": (_digest("e"),),
        "policy_digest": _digest("f"),
        "tools": (_tool(),),
        "declared_effects": ("source.patch",),
        "network": NetworkConstraint(),
        "budget": CandidateBudget(
            max_changed_paths=2,
            max_artifact_bytes=1_024,
            max_verification_checks=2,
        ),
        "required_checks": (_requirement(),),
        "retention_days": 30,
        "promotion_owner": "source-owner",
        "authorization_class": "source-promotion",
        "recovery_plan_digest": _digest("1"),
        "compatibility_evidence_digests": (_digest("2"),),
        "assembled_at": NOW,
    }
    values.update(changes)
    return WorkPacket.model_validate(values)


@pytest.mark.parametrize(
    "path",
    ["/src/lychd/file.py", "src/../secret", "src//file.py", "./src/file.py", "src\\file.py"],
)
def test_source_bounds_reject_absolute_traversing_or_noncanonical_paths(path: str) -> None:
    with pytest.raises(ValidationError, match="repository-relative|POSIX"):
        ProvisionalSourceBounds(
            exact_base=_base(),
            source_tree_digest=_digest("d"),
            allowed_path_roots=(path,),
        )


def test_exact_revision_rejects_moving_or_wrong_width_identity() -> None:
    with pytest.raises(ValidationError, match="hexadecimal|pattern"):
        ExactSourceRevision(
            source_id="repo",
            algorithm=RevisionAlgorithm.GIT_SHA1,
            revision="main",
        )
    with pytest.raises(ValidationError, match="exactly 64"):
        ExactSourceRevision(
            source_id="repo",
            algorithm=RevisionAlgorithm.GIT_SHA256,
            revision="a" * 40,
        )


def test_work_packet_is_frozen_and_has_a_stable_digest() -> None:
    packet = _packet()
    equivalent = _packet()

    assert packet.digest == equivalent.digest
    assert packet.network.mode is NetworkMode.DENIED
    with pytest.raises(ValidationError, match="frozen"):
        packet.principal_id = "another-principal"


def test_candidate_artifact_reference_is_finitely_bounded() -> None:
    with pytest.raises(ValidationError, match="at most 128 characters"):
        CandidateArtifactRef(
            artifact_id="a" * 129,
            digest=_digest("a"),
            media_type="text/x-diff",
            size=1,
        )
    with pytest.raises(ValidationError, match="less than or equal"):
        CandidateArtifactRef(
            artifact_id="artifact-1",
            digest=_digest("a"),
            media_type="text/x-diff",
            size=11 * 1_024 * 1_024 * 1_024,
        )


def test_work_packet_rejects_unpinned_check_tool_and_check_budget_overflow() -> None:
    other_tool = ToolPin(name="pytest", version="9.0.1", distribution_digest=_digest("9"))
    unpinned = VerificationRequirement(
        check_id="test",
        command=("pytest", "tests/unit"),
        tool=other_tool,
        environment_digest=_digest("c"),
        timeout_seconds=30,
        expected_exit_code=0,
    )
    with pytest.raises(ValidationError, match="absent from the packet tool pins"):
        _packet(required_checks=(unpinned,))

    with pytest.raises(ValidationError, match="exceeds the packet's check budget"):
        _packet(
            required_checks=(_requirement("lint"), _requirement("format")),
            budget=CandidateBudget(
                max_changed_paths=2,
                max_artifact_bytes=1_024,
                max_verification_checks=1,
            ),
        )


def test_admitted_network_declaration_requires_exact_policy_digest() -> None:
    with pytest.raises(ValidationError, match="must bind an exact policy digest"):
        NetworkConstraint(mode=NetworkMode.ADMITTED)

    admitted = NetworkConstraint(mode=NetworkMode.ADMITTED, policy_digest=_digest("a"))
    assert admitted.policy_digest == _digest("a")
