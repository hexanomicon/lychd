"""Immutable public input, attributed output, and exact byte citation contracts."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Any, Literal, NoReturn
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

COMPOSITION = "creation.investigation"
PATTERN = "creation.investigate"
PROFILE = "public-source-qwen@2"
OUTPUT_BYTES = 1536
PACKET_BYTES = 12288
RESPONSE_BYTES = 65536
SOURCE_BYTES = 4096
SOURCE_NAME_BYTES = 128
REQUEST_BYTES = 16384
INPUT_TOKENS = 3584
OUTPUT_TOKENS = 512
FEEDBACK_BYTES = 16384
FEEDBACK_LIMIT = 16


class CreationRefused(ValueError):  # noqa: N818 - domain refusal, not a runtime defect
    """A request cannot cross the application's admitted boundary."""


def refuse(code: str) -> NoReturn:
    raise CreationRefused(code)


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def canonical(value: Any) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            refuse("duplicate_key")
        result[key] = value
    return result


def decode(value: bytes) -> Any:
    """Reject ambiguous JSON before Pydantic can discard duplicate keys."""
    try:
        return json.loads(value.decode("utf-8", errors="strict"), object_pairs_hook=_pairs)
    except (UnicodeError, ValueError) as exc:
        code = "invalid_json"
        raise CreationRefused(code) from exc


def bounded(value: str, limit: int) -> str:
    if not value.strip() or len(value.encode("utf-8", errors="strict")) > limit:
        refuse("text_bounds")
    return value


class Source(Record):
    name: str
    text: str

    @field_validator("name")
    @classmethod
    def relative_name(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            len(value.encode("utf-8")) > SOURCE_NAME_BYTES
            or not value
            or path.is_absolute()
            or any(part in {"", ".", ".."} for part in value.split("/"))
            or any(char in value for char in ("\\", ":", "\x00"))
        ):
            refuse("source_name")
        return value


class Criterion(Record):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    predicate: str

    @field_validator("predicate")
    @classmethod
    def predicate_bytes(cls, value: str) -> str:
        return bounded(value, 192)


class InvestigationRequest(Record):
    request_id: UUID
    public_material: Literal[True]
    repository: str = Field(min_length=1, max_length=256)
    base_revision: str = Field(min_length=1, max_length=128)
    tree_or_patch_digest: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    question: str
    non_goals: tuple[str, ...] = Field(max_length=4)
    omissions: tuple[str, ...] = Field(max_length=4)
    sources: tuple[Source, ...] = Field(min_length=1, max_length=8)
    criteria: tuple[Criterion, ...] = Field(min_length=1, max_length=4)

    @field_validator("public_material", mode="before")
    @classmethod
    def public_declaration(cls, value: Any) -> Any:
        if value is not True:
            refuse("public_declaration")
        return value

    @field_validator("question")
    @classmethod
    def question_bytes(cls, value: str) -> str:
        return bounded(value, 512)

    @model_validator(mode="after")
    def source_closure(self) -> InvestigationRequest:
        if len({source.name for source in self.sources}) != len(self.sources):
            refuse("duplicate_source")
        if len({criterion.id for criterion in self.criteria}) != len(self.criteria):
            refuse("duplicate_criterion")
        if sum(len(source.text.encode("utf-8", errors="strict")) for source in self.sources) > SOURCE_BYTES:
            refuse("source_bytes")
        for value in (*self.non_goals, *self.omissions):
            bounded(value, 192)
        canonical(self)
        return self


class Citation(Record):
    source: str
    first_line: int = Field(ge=1)
    last_line: int = Field(ge=1)


class Finding(Record):
    criterion: str
    claim: str = Field(min_length=1, max_length=512)
    citations: tuple[Citation, ...] = Field(max_length=4)
    unknown: str = Field(max_length=192)


class Candidate(Record):
    summary: str = Field(min_length=1, max_length=512)
    findings: tuple[Finding, ...] = Field(min_length=1, max_length=4)


class Verdict(Record):
    disposition: Literal["accepted", "rejected", "partial", "incomplete"]
    findings: tuple[Finding, ...] = Field(min_length=1, max_length=4)
    contradictions: tuple[str, ...] = Field(max_length=4)


class ContinueRequest(Record):
    admission_id: UUID
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class CreationState(Record):
    """Only references cross Graph checkpoints; application records own truth."""

    model_config = ConfigDict(extra="forbid")
    run_id: str
    session_id: str
    admission_id: UUID


class CaseView(Record):
    case_id: UUID
    request_digest: str
    profile_digest: str
    status: str
    deadline: str
    slot_encumbered: bool
    request: InvestigationRequest
    profile: dict[str, Any]
    admissions: tuple[dict[str, Any], ...]
    attempts: tuple[dict[str, Any], ...]
    candidate: dict[str, Any] | None
    candidate_digest: str | None
    verdict: dict[str, Any] | None
    reason: str | None


def validate_output(request: InvestigationRequest, value: Candidate | Verdict) -> bytes:
    """Resolve citations to exact retained UTF-8 byte spans; never judge semantics."""
    if len(canonical(value)) > OUTPUT_BYTES:
        refuse("output_bytes")
    expected = {criterion.id for criterion in request.criteria}
    if {finding.criterion for finding in value.findings} != expected or len(value.findings) != len(expected):
        refuse("criterion_closure")
    sources = {source.name: source.text.encode("utf-8") for source in request.sources}
    spans: list[dict[str, Any]] = []
    for finding in value.findings:
        for citation in finding.citations:
            data = sources.get(citation.source)
            if data is None:
                refuse("citation_source")
            lines = data.splitlines(keepends=True)
            if not 1 <= citation.first_line <= citation.last_line <= len(lines):
                refuse("citation_span")
            start = sum(map(len, lines[: citation.first_line - 1]))
            stop = sum(map(len, lines[: citation.last_line]))
            spans.append(
                {
                    "criterion": finding.criterion,
                    "source": citation.source,
                    "source_digest": digest(data),
                    "start": start,
                    "stop": stop,
                    "digest": digest(data[start:stop]),
                }
            )
    return canonical({"schema_valid": True, "citations": spans, "semantic_correctness": "not_established"})


class FeedbackTarget(Record):
    """Exact retained evidence identities; source texts are hashed as literal UTF-8."""

    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    verdict_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    sources_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    criteria_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ExternalAssessment(Record):
    assessment_id: UUID
    target: FeedbackTarget
    reviewer_label: str
    reviewer_revision: str
    report: str
    disposition: Literal["accepted", "rejected", "partial", "incomplete", "not_assessed"]
    exposure: tuple[str, ...] = Field(max_length=4)
    limitations: tuple[str, ...] = Field(max_length=4)
    submitter_annotations: tuple[Finding, ...] = Field(default=(), max_length=4)

    @model_validator(mode="after")
    def byte_bounds(self) -> ExternalAssessment:
        bounded(self.reviewer_label, 128)
        bounded(self.reviewer_revision, 128)
        bounded(self.report, 8192)
        for value in (*self.exposure, *self.limitations):
            bounded(value, 192)
        if len(canonical(self)) > FEEDBACK_BYTES:
            refuse("feedback_body_bytes")
        return self


class OwnerDecision(Record):
    decision_id: UUID
    assessment_id: UUID
    assessment_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    target: FeedbackTarget
    action: Literal["hold", "reject"]
    reason: str
    distinguishing_observation: str | None = None

    @model_validator(mode="after")
    def byte_bounds(self) -> OwnerDecision:
        bounded(self.reason, 1024)
        if self.distinguishing_observation is not None:
            bounded(self.distinguishing_observation, 512)
        if len(canonical(self)) > FEEDBACK_BYTES:
            refuse("feedback_body_bytes")
        return self


class FeedbackEntry(Record):
    id: UUID
    sequence: int
    body_digest: str
    body: dict[str, Any]
    attribution: dict[str, Any]
    created_at: str
    report_digest: str | None
    criterion_coverage: dict[str, Literal["submitter_annotation", "not_assessed"]]


class FeedbackView(Record):
    case_id: UUID
    native_status: str
    native_verdict: dict[str, Any] | None
    target: FeedbackTarget | None
    status: Literal["unassessed", "review_required", "hold", "rejected"]
    current_assessment_id: UUID | None
    current_decision_id: UUID | None
    assessments: tuple[FeedbackEntry, ...]
    decisions: tuple[FeedbackEntry, ...]


def feedback_target(
    request_bytes: bytes, profile_bytes: bytes, candidate_bytes: bytes, verdict_bytes: bytes
) -> FeedbackTarget:
    """Hash request/profile/candidate literal bytes and the canonical decoded native verdict.

    sources_digest hashes a canonical list, in retained source order, of objects
    with exactly name and digest (SHA-256 of that source's literal UTF-8 text).
    criteria_digest hashes the canonical original criterion objects in retained order.
    """
    request = InvestigationRequest.model_validate(decode(request_bytes))
    return FeedbackTarget(
        request_digest=digest(request_bytes),
        profile_digest=digest(profile_bytes),
        candidate_digest=digest(candidate_bytes),
        verdict_digest=digest(canonical(decode(verdict_bytes))),
        sources_digest=digest(
            canonical([{"name": s.name, "digest": digest(s.text.encode("utf-8"))} for s in request.sources])
        ),
        criteria_digest=digest(canonical([c.model_dump(mode="json") for c in request.criteria])),
    )


def validate_annotations(request: InvestigationRequest, assessment: ExternalAssessment) -> None:
    """Check submitter mappings only; absence never fabricates an external judgment."""
    annotations = assessment.submitter_annotations
    expected = {criterion.id for criterion in request.criteria}
    if len({a.criterion for a in annotations}) != len(annotations) or any(
        a.criterion not in expected for a in annotations
    ):
        refuse("criterion_binding")
    sources = {source.name: source.text.encode("utf-8") for source in request.sources}
    for annotation in annotations:
        for citation in annotation.citations:
            data = sources.get(citation.source)
            if data is None:
                refuse("citation_source")
            if not 1 <= citation.first_line <= citation.last_line <= len(data.splitlines(keepends=True)):
                refuse("citation_span")
