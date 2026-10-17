"""Comparison completion preserves retirement boundaries without claiming truth."""

from __future__ import annotations

import hashlib
import io
import json
import sys
from typing import TYPE_CHECKING, Literal

import pytest
from pydantic import ValidationError
from scripts import compare_evolution

from lychd.domain.artifacts import ArtifactRef
from lychd.domain.evolution import (
    MAX_INPUT_BYTES,
    ComparisonAdmission,
    ComparisonPacket,
    ComparisonProposal,
    DispositionProposal,
    EvidenceSummary,
    HistoricalObligation,
    admission_digest,
    compare_history,
    decode_packet,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def reference(name: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=name,
        digest="sha256:" + hashlib.sha256(name.encode()).hexdigest(),
        media_type="application/json",
        size=1,
    )


def evidence(
    admission: ComparisonAdmission,
    obligation: HistoricalObligation,
    contract: ArtifactRef,
    purpose: Literal["candidate_contract", "inherited_contract", "owner_retirement", "transition_recovery"],
    result: Literal["pass", "fail", "unknown"] = "pass",
) -> EvidenceSummary:
    return EvidenceSummary(
        obligation_id=obligation.obligation_id,
        admission_digest=admission_digest(admission),
        base=admission.base,
        candidate=admission.candidate,
        policy=admission.policy,
        selected_contract=contract,
        purpose=purpose,
        kind="owner_decision" if purpose == "owner_retirement" else "verification_receipt",
        producer=obligation.owner if purpose == "owner_retirement" else "independent-verifier",
        reported_result=result,
        receipt=reference(f"{obligation.obligation_id}-{purpose}-{result}"),
    )


@pytest.fixture
def packet() -> ComparisonPacket:
    old = HistoricalObligation(obligation_id="protocol", owner="protocol-owner", inherited_contract=reference("v1"))
    extension = HistoricalObligation(obligation_id="extension-C", owner="C-owner", inherited_contract=reference("C"))
    admission = ComparisonAdmission(
        base=reference("installed-body"),
        candidate=reference("combined-v2-with-C"),
        policy=reference("predeclared-policy"),
        history=reference("selected-history-with-omissions"),
        obligations=(old, extension),
    )
    successor = reference("v2-no-credential-leak")
    replacement = DispositionProposal(
        obligation_id=old.obligation_id,
        owner=old.owner,
        disposition="replace",
        reason="End insecure v1; declare consumer transition and unresolved-work refusal.",
        selected_contract=successor,
        evidence=tuple(
            evidence(admission, old, successor, purpose)
            for purpose in ("candidate_contract", "owner_retirement", "transition_recovery")
        ),
    )
    retained = DispositionProposal(
        obligation_id=extension.obligation_id,
        owner=extension.owner,
        disposition="retain",
        reason="Preserve C under the combined body.",
        selected_contract=extension.inherited_contract,
        evidence=(evidence(admission, extension, extension.inherited_contract, "candidate_contract"),),
    )
    proposal = ComparisonProposal(admission_digest=admission_digest(admission), dispositions=(replacement, retained))
    return ComparisonPacket(profile="evolution-comparison@1", admission=admission, proposal=proposal)


def with_first(packet: ComparisonPacket, first: DispositionProposal) -> ComparisonProposal:
    return packet.proposal.model_copy(update={"dispositions": (first, packet.proposal.dispositions[1])})


def test_retirement_requires_owner_and_transition_while_unrelated_extension_survives(packet: ComparisonPacket) -> None:
    replacement, _ = packet.proposal.dispositions
    before = with_first(packet, replacement.model_copy(update={"evidence": replacement.evidence[:1]}))
    blocked = compare_history(packet.admission, before)
    assert blocked.outcome == "blocked"
    assert blocked.dispositions[0].blockers == ("missing_evidence",)
    after = compare_history(packet.admission, packet.proposal)
    assert after.outcome == "comparison_complete"
    assert [(item.disposition, item.blockers) for item in after.dispositions] == [("replace", ()), ("retain", ())]
    assert after.authority == "comparison-only"
    assert "promotion" not in after.model_dump_json()
    assert compare_history(packet.admission, before) == blocked
    assert after.input_digest != blocked.input_digest


@pytest.mark.parametrize("result", ["fail", "unknown"])
def test_passing_receipt_cannot_hide_conflicting_or_unknown_evidence(
    packet: ComparisonPacket, result: Literal["fail", "unknown"]
) -> None:
    row = packet.proposal.dispositions[0]
    adverse = row.evidence[0].model_copy(update={"reported_result": result, "receipt": reference("adverse")})
    proposal = with_first(packet, row.model_copy(update={"evidence": (*row.evidence, adverse)}))
    report = compare_history(packet.admission, proposal)
    assert report.outcome == "blocked"
    assert {"conflicting_evidence", "evidence_not_pass"} <= set(report.dispositions[0].blockers)


@pytest.mark.parametrize("field", ["base", "candidate", "policy", "selected_contract"])
def test_receipts_must_bind_exact_combined_candidate_and_criteria(packet: ComparisonPacket, field: str) -> None:
    row = packet.proposal.dispositions[0]
    stale = row.evidence[0].model_copy(update={field: reference("other-branch-or-policy")})
    proposal = with_first(packet, row.model_copy(update={"evidence": (stale, *row.evidence[1:])}))
    report = compare_history(packet.admission, proposal)
    assert report.outcome == "blocked"
    assert "evidence_binding_mismatch" in report.dispositions[0].blockers


def test_history_and_owner_cannot_be_substituted(packet: ComparisonPacket) -> None:
    admission = packet.admission.model_copy(update={"history": reference("different-selected-history")})
    report = compare_history(admission, packet.proposal)
    assert report.outcome == "blocked"
    assert report.blockers == ("admission_binding_mismatch",)
    row = packet.proposal.dispositions[0]
    forged = row.evidence[1].model_copy(update={"producer": "candidate-author"})
    proposal = with_first(packet, row.model_copy(update={"evidence": (row.evidence[0], forged, row.evidence[2])}))
    assert "retirement_owner_mismatch" in compare_history(packet.admission, proposal).dispositions[0].blockers


def test_reconciliation_cannot_discard_inherited_criterion(packet: ComparisonPacket) -> None:
    row = packet.proposal.dispositions[0]
    reconciled = row.model_copy(update={"disposition": "reconcile", "evidence": row.evidence[:1]})
    before = compare_history(packet.admission, with_first(packet, reconciled))
    assert before.outcome == "blocked"
    inherited = evidence(packet.admission, packet.admission.obligations[0], reference("v1"), "inherited_contract")
    reconciled = reconciled.model_copy(update={"evidence": (*reconciled.evidence, inherited)})
    assert compare_history(packet.admission, with_first(packet, reconciled)).outcome == "comparison_complete"


def test_rejection_records_refusal_without_candidate_acceptance(packet: ComparisonPacket) -> None:
    rows = tuple(
        row.model_copy(update={"disposition": "reject", "evidence": ()}) for row in packet.proposal.dispositions
    )
    report = compare_history(packet.admission, packet.proposal.model_copy(update={"dispositions": rows}))
    assert report.outcome == "rejection_recorded"
    assert report.authority == "comparison-only"


def test_reason_requires_non_whitespace_and_preserves_exact_text(packet: ComparisonPacket) -> None:
    first = packet.proposal.dispositions[0]
    for blank in ("", " \t\r\n"):
        with pytest.raises(ValidationError):
            compare_history(packet.admission, with_first(packet, first.model_copy(update={"reason": blank})))
    reason = " \t Retire insecure v1 with declared transition evidence. \n"
    proposal = with_first(packet, first.model_copy(update={"reason": reason}))
    admitted = packet.model_copy(update={"proposal": proposal})
    assert decode_packet(admitted.model_dump_json().encode()).proposal.dispositions[0].reason == reason
    assert compare_history(packet.admission, proposal).outcome == "comparison_complete"


def test_omissions_extras_duplicates_and_disguised_retention(packet: ComparisonPacket) -> None:
    first, second = packet.proposal.dispositions
    omitted = packet.proposal.model_copy(update={"dispositions": (first,)})
    assert compare_history(packet.admission, omitted).dispositions[1].blockers == ("missing_disposition",)
    extra = second.model_copy(update={"obligation_id": "unadmitted"})
    proposal = packet.proposal.model_copy(update={"dispositions": (first, second, extra)})
    assert compare_history(packet.admission, proposal).blockers == ("unexpected_obligation",)
    with pytest.raises(ValidationError):
        compare_history(packet.admission, packet.proposal.model_copy(update={"dispositions": (first, first)}))
    changed = first.model_copy(update={"disposition": "retain"})
    assert (
        "retained_contract_changed"
        in compare_history(packet.admission, with_first(packet, changed)).dispositions[0].blockers
    )


def test_exact_replay_and_deeply_immutable_bounded_values(packet: ComparisonPacket) -> None:
    encoded = packet.model_dump_json().encode()
    decoded = decode_packet(encoded)
    assert compare_history(decoded.admission, decoded.proposal) == compare_history(packet.admission, packet.proposal)
    reordered = decode_packet(json.dumps(json.loads(encoded), sort_keys=True).encode())
    assert (
        compare_history(reordered.admission, reordered.proposal).input_digest
        == compare_history(packet.admission, packet.proposal).input_digest
    )
    with pytest.raises(ValidationError):
        packet.admission.candidate.size = 2
    with pytest.raises(ValidationError):
        packet.proposal.dispositions[0].reason = "changed"
    bad = packet.admission.candidate.model_copy(update={"size": True})
    with pytest.raises(ValidationError):
        compare_history(packet.admission.model_copy(update={"candidate": bad}), packet.proposal)
    with pytest.raises(ValidationError):
        ComparisonAdmission.model_validate_json(packet.admission.model_dump_json().replace("installed-body", "x" * 257))


@pytest.mark.parametrize("size", ["1", True, 1.0])
def test_nested_artifact_references_do_not_coerce_json_scalars(packet: ComparisonPacket, size: object) -> None:
    payload = json.loads(packet.model_dump_json())
    payload["admission"]["base"]["size"] = size
    with pytest.raises(ValidationError):
        decode_packet(json.dumps(payload).encode())


def test_collection_limits_and_duplicate_admitted_obligations(packet: ComparisonPacket) -> None:
    row = packet.proposal.dispositions[0]
    excessive = row.model_copy(update={"evidence": (row.evidence[0],) * 17})
    with pytest.raises(ValidationError):
        compare_history(packet.admission, with_first(packet, excessive))
    repeated = packet.admission.model_copy(update={"obligations": (packet.admission.obligations[0],) * 2})
    with pytest.raises(ValidationError):
        compare_history(repeated, packet.proposal)


@pytest.mark.parametrize(
    "payload",
    [
        b'{"profile":1,"profile":2}',
        b'{"nested":{"secret":1,"secret":2}}',
        b'{"secret":NaN}',
        b'{"secret":Infinity}',
        b'{"secret":1e999}',
        b"\xff",
        b"[" * 1100,
        b" " * (MAX_INPUT_BYTES + 1),
    ],
)
def test_strict_bounded_decoder_refuses_invalid_json(payload: bytes) -> None:
    with pytest.raises((ValueError, RecursionError)):
        decode_packet(payload)


@pytest.fixture
def script(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> Callable[[bytes], tuple[int, str, str]]:
    def invoke(payload: bytes) -> tuple[int, str, str]:
        monkeypatch.setattr(sys, "argv", ["compare_evolution.py"])
        monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8"))
        code = compare_evolution.main()
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return invoke


def test_script_is_a_real_consumer_with_fixed_refusals(
    packet: ComparisonPacket, script: Callable[[bytes], tuple[int, str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    code, output, error = script(packet.model_dump_json().encode())
    assert code == 0
    assert not error
    assert json.loads(output)["outcome"] == "comparison_complete"
    first = packet.proposal.dispositions[0].model_copy(update={"evidence": ()})
    blocked = packet.model_copy(update={"proposal": with_first(packet, first)})
    assert script(blocked.model_dump_json().encode())[0] == 1
    assert script(b'{"private-secret":NaN}') == (2, "", "comparison input refused\n")
    assert script(b" " * (MAX_INPUT_BYTES + 1)) == (2, "", "comparison input refused\n")
    monkeypatch.setattr(compare_evolution, "MAX_OUTPUT_BYTES", 1)
    assert script(packet.model_dump_json().encode()) == (2, "", "comparison input refused\n")
