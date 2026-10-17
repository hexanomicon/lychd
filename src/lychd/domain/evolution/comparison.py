"""Offline checks of caller-admitted continuity claims, never promotion authority.

References and reported results are attributed declarations. This module neither
authenticates their issuers nor reads artifacts, runs tests, or observes live state.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, model_validator

from lychd.domain.artifacts import ArtifactRef

MAX_INPUT_BYTES = 1_048_576
MAX_OUTPUT_BYTES = 65_536
_MAX_ARTIFACT_ID = 256
_MAX_MEDIA_TYPE = 128
Label = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")]
Reason = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=2048, pattern=r"\S")]
Digest = Annotated[str, StringConstraints(strict=True, pattern=r"^sha256:[0-9a-f]{64}$")]
DispositionKind = Literal["retain", "reconcile", "replace", "reject"]


def _bounded_reference(value: object) -> ArtifactRef:
    reference = ArtifactRef.model_validate(value.model_dump() if isinstance(value, ArtifactRef) else value, strict=True)
    if (
        len(reference.artifact_id) > _MAX_ARTIFACT_ID
        or len(reference.media_type) > _MAX_MEDIA_TYPE
        or reference.size > 2**63 - 1
    ):
        msg = "Artifact reference exceeds comparison limits."
        raise ValueError(msg)
    return reference


Reference = Annotated[ArtifactRef, BeforeValidator(_bounded_reference)]


class ComparisonValue(BaseModel):
    """Frozen scalar/reference/tuple records admit no mutable nested containers."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")


class HistoricalObligation(ComparisonValue):
    obligation_id: Label
    owner: Label
    inherited_contract: Reference


class ComparisonAdmission(ComparisonValue):
    """Trusted caller's declared boundary; validation does not authenticate it."""

    base: Reference
    candidate: Reference
    policy: Reference
    history: Reference
    obligations: tuple[HistoricalObligation, ...] = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def unique_obligations(self) -> ComparisonAdmission:
        if len({item.obligation_id for item in self.obligations}) != len(self.obligations):
            msg = "Historical obligation identities must be unique."
            raise ValueError(msg)
        return self


class EvidenceSummary(ComparisonValue):
    """Caller-admitted attribution and result, not an authenticated test receipt."""

    obligation_id: Label
    admission_digest: Digest
    base: Reference
    candidate: Reference
    policy: Reference
    selected_contract: Reference
    purpose: Literal["candidate_contract", "inherited_contract", "owner_retirement", "transition_recovery"]
    kind: Literal["verification_receipt", "owner_decision"]
    producer: Label
    reported_result: Literal["pass", "fail", "unknown"]
    receipt: Reference


class DispositionProposal(ComparisonValue):
    obligation_id: Label
    owner: Label
    disposition: DispositionKind
    reason: Reason
    selected_contract: Reference
    evidence: tuple[EvidenceSummary, ...] = Field(default=(), max_length=16)


class ComparisonProposal(ComparisonValue):
    admission_digest: Digest
    dispositions: tuple[DispositionProposal, ...] = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def unique_dispositions(self) -> ComparisonProposal:
        if len({item.obligation_id for item in self.dispositions}) != len(self.dispositions):
            msg = "Disposition identities must be unique."
            raise ValueError(msg)
        return self


class ComparisonPacket(ComparisonValue):
    profile: Literal["evolution-comparison@1"]
    admission: ComparisonAdmission
    proposal: ComparisonProposal


class DispositionResult(ComparisonValue):
    obligation_id: Label
    disposition: DispositionKind | None
    blockers: tuple[Label, ...] = Field(max_length=16)


class ComparisonReport(ComparisonValue):
    """Completion is mechanical sufficiency, never candidate acceptance."""

    input_digest: Digest
    outcome: Literal["blocked", "rejection_recorded", "comparison_complete"]
    authority: Literal["comparison-only"] = "comparison-only"
    blockers: tuple[Label, ...] = Field(max_length=8)
    dispositions: tuple[DispositionResult, ...] = Field(min_length=1, max_length=128)


def admission_digest(admission: ComparisonAdmission) -> str:
    """Bind a proposal to the exact declared historical boundary and policy."""
    admitted = ComparisonAdmission.model_validate_json(admission.model_dump_json())
    return _digest(admitted)


def _digest(value: ComparisonValue) -> str:
    payload = json.dumps(value.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _evidence_blockers(
    admission: ComparisonAdmission, obligation: HistoricalObligation, proposed: DispositionProposal, boundary: str
) -> set[str]:
    blockers: set[str] = set()
    for evidence in proposed.evidence:
        contract = (
            obligation.inherited_contract if evidence.purpose == "inherited_contract" else proposed.selected_contract
        )
        if (
            evidence.admission_digest != boundary
            or evidence.base != admission.base
            or evidence.candidate != admission.candidate
            or evidence.policy != admission.policy
            or evidence.obligation_id != obligation.obligation_id
            or evidence.selected_contract != contract
        ):
            blockers.add("evidence_binding_mismatch")
        owner_decision = evidence.purpose == "owner_retirement"
        if evidence.kind != ("owner_decision" if owner_decision else "verification_receipt"):
            blockers.add("evidence_kind_mismatch")
        if owner_decision and evidence.producer != obligation.owner:
            blockers.add("retirement_owner_mismatch")
    if proposed.disposition == "reject":
        return blockers
    return blockers | _required_evidence_blockers(obligation, proposed)


def _required_evidence_blockers(obligation: HistoricalObligation, proposed: DispositionProposal) -> set[str]:
    blockers: set[str] = set()
    required = {"candidate_contract"}
    if proposed.disposition == "reconcile" and proposed.selected_contract != obligation.inherited_contract:
        required.add("inherited_contract")
    if proposed.disposition == "replace":
        required.update(("owner_retirement", "transition_recovery"))
    if required.difference(item.purpose for item in proposed.evidence):
        blockers.add("missing_evidence")
    if any(item.reported_result != "pass" for item in proposed.evidence):
        blockers.add("evidence_not_pass")
    for purpose in {item.purpose for item in proposed.evidence}:
        if len({item.reported_result for item in proposed.evidence if item.purpose == purpose}) > 1:
            blockers.add("conflicting_evidence")
    return blockers


def compare_history(admission: ComparisonAdmission, proposal: ComparisonProposal) -> ComparisonReport:
    """Check all declared obligations without fetching or authorizing anything.

    Every supplied summary participates: a passing receipt cannot hide a failing
    or unknown one. Reconciliation evidence binds the combined candidate itself.
    A rejection can complete this comparison but never accepts the candidate.
    """
    packet = ComparisonPacket.model_validate_json(
        ComparisonPacket(profile="evolution-comparison@1", admission=admission, proposal=proposal).model_dump_json()
    )
    admission, proposal = packet.admission, packet.proposal
    blockers: set[str] = set()
    boundary = admission_digest(admission)
    if proposal.admission_digest != boundary:
        blockers.add("admission_binding_mismatch")
    by_id = {item.obligation_id: item for item in proposal.dispositions}
    if by_id.keys() - {item.obligation_id for item in admission.obligations}:
        blockers.add("unexpected_obligation")
    results: list[DispositionResult] = []
    for obligation in admission.obligations:
        proposed = by_id.get(obligation.obligation_id)
        reasons: set[str] = set()
        if proposed is None:
            reasons.add("missing_disposition")
        else:
            if proposed.owner != obligation.owner:
                reasons.add("obligation_owner_mismatch")
            if proposed.disposition == "retain" and proposed.selected_contract != obligation.inherited_contract:
                reasons.add("retained_contract_changed")
            if proposed.disposition == "replace" and proposed.selected_contract == obligation.inherited_contract:
                reasons.add("retirement_contract_unchanged")
            reasons.update(_evidence_blockers(admission, obligation, proposed, boundary))
        results.append(
            DispositionResult(
                obligation_id=obligation.obligation_id,
                disposition=proposed.disposition if proposed else None,
                blockers=tuple(sorted(reasons)),
            )
        )
    outcome = "comparison_complete"
    if blockers or any(item.blockers for item in results):
        outcome = "blocked"
    elif any(item.disposition == "reject" for item in results):
        outcome = "rejection_recorded"
    return ComparisonReport(
        input_digest=_digest(packet),
        outcome=outcome,
        blockers=tuple(sorted(blockers)),
        dispositions=tuple(results),
    )


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = "Duplicate JSON key."
            raise ValueError(msg)
        result[key] = value
    return result


def _nonfinite_constant(_value: str) -> None:
    msg = "Nonfinite JSON number."
    raise ValueError(msg)


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        _nonfinite_constant(value)
    return number


def decode_packet(payload: bytes) -> ComparisonPacket:
    """Decode one bounded, duplicate-free, finite UTF-8 JSON packet."""
    if len(payload) > MAX_INPUT_BYTES:
        msg = "Comparison input exceeds byte limit."
        raise ValueError(msg)
    text = payload.decode("utf-8")
    json.loads(text, object_pairs_hook=_unique_object, parse_constant=_nonfinite_constant, parse_float=_finite_float)
    return ComparisonPacket.model_validate_json(text)
