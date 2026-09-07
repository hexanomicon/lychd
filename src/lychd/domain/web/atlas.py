"""Atlas contracts and versioned undertaking changes, independent of execution.

The memory adapter is loop-confined. Reference targets are admitted by the web
boundary; this module validates their relationships inside the Project only.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Literal, Protocol, runtime_checkable
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

MAX_CONCERNS = 200
MAX_ASSESSMENTS = 2_000
MAX_DECISIONS = 2_000
MAX_REFERENCES = 2_000
MAX_PAGE_SIZE = 100

AtlasLifecycle = Literal["active", "paused", "closed"]
AtlasJudgment = Literal["sufficient", "insufficient", "disputed"]
AtlasReferenceKind = Literal["session", "run"]
AtlasTitle = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=200, pattern=r"\S")]
AtlasStatement = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=4_000, pattern=r"\S")]
AtlasBrief = Annotated[str, StringConstraints(strict=True, max_length=20_000)]
AtlasCriteria = Annotated[str, StringConstraints(strict=True, max_length=8_000)]
AtlasRationale = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=8_000, pattern=r"\S")]
AtlasNextAction = Annotated[str, StringConstraints(strict=True, max_length=4_000)]
AtlasNote = Annotated[str, StringConstraints(strict=True, max_length=2_000)]
AtlasTargetId = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128)]
AtlasAuthor = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=100)]
AtlasRevision = Annotated[int, Field(strict=True, ge=1)]


class AtlasNotFoundError(LookupError):
    """An owned Project or one of its children is unavailable."""


class AtlasConflictError(ValueError):
    """A stale version or conflicting replay identity refused the change."""


class AtlasValidationError(ValueError):
    """A change violates an Atlas relationship or collection bound."""


class AtlasContract(BaseModel):
    """Closed input and response fields; server attribution is never client input."""

    model_config = ConfigDict(extra="forbid")


class AtlasConcern(AtlasContract):
    id: UUID
    statement: AtlasStatement
    criteria: AtlasCriteria
    revision: AtlasRevision


class AtlasAssessment(AtlasContract):
    """A judgment over a captured brief and concern, citing Atlas reference ids."""

    id: UUID
    concern_id: UUID
    concern_revision: AtlasRevision
    brief_revision: AtlasRevision
    statement: AtlasStatement
    criteria: AtlasCriteria
    brief: AtlasBrief
    judgment: AtlasJudgment
    rationale: AtlasRationale
    reference_ids: list[UUID] = Field(max_length=MAX_REFERENCES)
    author: AtlasAuthor
    created_at: datetime


class AtlasDecision(AtlasContract):
    id: UUID
    statement: AtlasStatement
    rationale: AtlasRationale
    supersedes_id: UUID | None
    author: AtlasAuthor
    created_at: datetime


class AtlasReference(AtlasContract):
    """A scoped activity link; an assessment cites this record's id separately."""

    id: UUID
    kind: AtlasReferenceKind
    target_id: AtlasTargetId
    concern_id: UUID | None
    note: AtlasNote
    author: AtlasAuthor
    created_at: datetime


class AtlasProject(AtlasContract):
    id: UUID
    title: AtlasTitle
    brief: AtlasBrief
    lifecycle: AtlasLifecycle
    next_action: AtlasNextAction
    version: AtlasRevision
    brief_revision: AtlasRevision
    created_at: datetime
    updated_at: datetime
    concerns: list[AtlasConcern] = Field(max_length=MAX_CONCERNS)
    assessments: list[AtlasAssessment] = Field(max_length=MAX_ASSESSMENTS)
    decisions: list[AtlasDecision] = Field(max_length=MAX_DECISIONS)
    references: list[AtlasReference] = Field(max_length=MAX_REFERENCES)


class AtlasSummary(AtlasContract):
    id: UUID
    title: AtlasTitle
    brief: AtlasBrief
    lifecycle: AtlasLifecycle
    next_action: AtlasNextAction
    version: AtlasRevision
    updated_at: datetime
    concern_count: int = Field(strict=True, ge=0)
    unassessed_count: int = Field(strict=True, ge=0)
    review_needed_count: int = Field(strict=True, ge=0)
    insufficient_count: int = Field(strict=True, ge=0)
    disputed_count: int = Field(strict=True, ge=0)


class AtlasCatalogue(AtlasContract):
    projects: list[AtlasSummary] = Field(max_length=MAX_PAGE_SIZE)
    total: int = Field(strict=True, ge=0)
    limit: int = Field(strict=True, ge=1, le=MAX_PAGE_SIZE)
    offset: int = Field(strict=True, ge=0)


class AtlasCreate(AtlasContract):
    id: UUID
    title: AtlasTitle
    brief: AtlasBrief = ""
    next_action: AtlasNextAction = ""


class AtlasProjectUpdate(AtlasContract):
    kind: Literal["project.update"]
    title: AtlasTitle
    brief: AtlasBrief
    lifecycle: AtlasLifecycle
    next_action: AtlasNextAction


class AtlasConcernSave(AtlasContract):
    kind: Literal["concern.save"]
    concern_id: UUID | None
    statement: AtlasStatement
    criteria: AtlasCriteria


class AtlasConcernAssess(AtlasContract):
    kind: Literal["concern.assess"]
    concern_id: UUID
    judgment: AtlasJudgment
    rationale: AtlasRationale
    reference_ids: list[UUID] = Field(max_length=MAX_REFERENCES)

    @field_validator("reference_ids")
    @classmethod
    def unique_references(cls, value: list[UUID]) -> list[UUID]:
        """Require each retained reference to appear at most once."""
        if len(value) != len(set(value)):
            message = "Assessment reference identities must be unique."
            raise ValueError(message)
        return value


class AtlasDecisionRecord(AtlasContract):
    kind: Literal["decision.record"]
    statement: AtlasStatement
    rationale: AtlasRationale
    supersedes_id: UUID | None


class AtlasReferenceAdd(AtlasContract):
    kind: Literal["reference.add"]
    reference_kind: AtlasReferenceKind
    target_id: AtlasTargetId
    concern_id: UUID | None
    note: AtlasNote


AtlasChange = Annotated[
    AtlasProjectUpdate | AtlasConcernSave | AtlasConcernAssess | AtlasDecisionRecord | AtlasReferenceAdd,
    Field(discriminator="kind"),
]


class AtlasMutation(AtlasContract):
    request_id: UUID
    expected_version: AtlasRevision
    change: AtlasChange


def payload_digest(data: AtlasCreate | AtlasMutation) -> str:
    """Fingerprint the complete validated payload, preserving ordered citations."""
    payload = json.dumps(data.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def new_project(data: AtlasCreate, *, now: datetime) -> AtlasProject:
    """Create an empty undertaking without admitting a conversation or Run."""
    return AtlasProject(
        id=data.id,
        title=data.title,
        brief=data.brief,
        lifecycle="active",
        next_action=data.next_action,
        version=1,
        brief_revision=1,
        created_at=now,
        updated_at=now,
        concerns=[],
        assessments=[],
        decisions=[],
        references=[],
    )


def validate_page(limit: int, offset: int) -> None:
    """Keep both adapters' pagination bounds identical."""
    if type(limit) is not int or type(offset) is not int or not 1 <= limit <= MAX_PAGE_SIZE or offset < 0:
        message = "Atlas pagination requires a limit from 1 to 100 and a nonnegative offset."
        raise AtlasValidationError(message)


def summarize_project(project: AtlasProject) -> AtlasSummary:
    """Count each concern from its latest assessment and current basis revisions.

    A stale basis counts only as review-needed, regardless of the recorded judgment.
    """
    latest = {assessment.concern_id: assessment for assessment in project.assessments}
    unassessed = 0
    review_needed = 0
    insufficient = 0
    disputed = 0
    for concern in project.concerns:
        assessment = latest.get(concern.id)
        if assessment is None:
            unassessed += 1
        elif assessment.concern_revision != concern.revision or assessment.brief_revision != project.brief_revision:
            review_needed += 1
        elif assessment.judgment == "insufficient":
            insufficient += 1
        elif assessment.judgment == "disputed":
            disputed += 1
    return AtlasSummary(
        id=project.id,
        title=project.title,
        brief=project.brief,
        lifecycle=project.lifecycle,
        next_action=project.next_action,
        version=project.version,
        updated_at=project.updated_at,
        concern_count=len(project.concerns),
        unassessed_count=unassessed,
        review_needed_count=review_needed,
        insufficient_count=insufficient,
        disputed_count=disputed,
    )


def _concern(project: AtlasProject, concern_id: UUID) -> AtlasConcern:
    for concern in project.concerns:
        if concern.id == concern_id:
            return concern
    message = "Atlas concern is unavailable in this Project."
    raise AtlasNotFoundError(message)


def _require_capacity(size: int, maximum: int, label: str) -> None:
    if size >= maximum:
        message = f"Atlas Project has reached its {label} limit ({maximum})."
        raise AtlasValidationError(message)


def _save_concern(project: AtlasProject, change: AtlasConcernSave, record_id: UUID) -> None:
    if change.concern_id is None:
        _require_capacity(len(project.concerns), MAX_CONCERNS, "concern")
        project.concerns.append(
            AtlasConcern(id=record_id, statement=change.statement, criteria=change.criteria, revision=1)
        )
        return
    concern = _concern(project, change.concern_id)
    if (concern.statement, concern.criteria) != (change.statement, change.criteria):
        concern.statement = change.statement
        concern.criteria = change.criteria
        concern.revision += 1


def _assess_concern(
    project: AtlasProject, change: AtlasConcernAssess, *, author: str, now: datetime, record_id: UUID
) -> None:
    concern = _concern(project, change.concern_id)
    references = {reference.id: reference for reference in project.references}
    for reference_id in change.reference_ids:
        reference = references.get(reference_id)
        if reference is None or reference.concern_id not in (None, concern.id):
            message = "Assessment references must belong to this Project and this concern or the whole Project."
            raise AtlasValidationError(message)
    _require_capacity(len(project.assessments), MAX_ASSESSMENTS, "assessment")
    project.assessments.append(
        AtlasAssessment(
            id=record_id,
            concern_id=concern.id,
            concern_revision=concern.revision,
            brief_revision=project.brief_revision,
            statement=concern.statement,
            criteria=concern.criteria,
            brief=project.brief,
            judgment=change.judgment,
            rationale=change.rationale,
            reference_ids=list(change.reference_ids),
            author=author,
            created_at=now,
        )
    )


def _record_decision(
    project: AtlasProject, change: AtlasDecisionRecord, *, author: str, now: datetime, record_id: UUID
) -> None:
    if change.supersedes_id is not None:
        if not any(decision.id == change.supersedes_id for decision in project.decisions):
            message = "Superseded Atlas decision is unavailable in this Project."
            raise AtlasNotFoundError(message)
        if any(decision.supersedes_id == change.supersedes_id for decision in project.decisions):
            message = "This Atlas decision has already been superseded."
            raise AtlasConflictError(message)
    _require_capacity(len(project.decisions), MAX_DECISIONS, "decision")
    project.decisions.append(
        AtlasDecision(
            id=record_id,
            statement=change.statement,
            rationale=change.rationale,
            supersedes_id=change.supersedes_id,
            author=author,
            created_at=now,
        )
    )


def _add_reference(
    project: AtlasProject, change: AtlasReferenceAdd, *, author: str, now: datetime, record_id: UUID
) -> None:
    if change.concern_id is not None:
        _concern(project, change.concern_id)
    identity = (change.reference_kind, change.target_id, change.concern_id)
    if any((reference.kind, reference.target_id, reference.concern_id) == identity for reference in project.references):
        message = "This activity is already linked to the selected Atlas concern or Project."
        raise AtlasConflictError(message)
    _require_capacity(len(project.references), MAX_REFERENCES, "reference")
    project.references.append(
        AtlasReference(
            id=record_id,
            kind=change.reference_kind,
            target_id=change.target_id,
            concern_id=change.concern_id,
            note=change.note,
            author=author,
            created_at=now,
        )
    )


def apply_change(
    project: AtlasProject, data: AtlasMutation, *, author: str, now: datetime, record_id: UUID
) -> AtlasProject:
    """Calculate a detached successor; adapters own atomic replay and commit."""
    if data.expected_version != project.version:
        message = "Atlas Project changed since this draft was loaded. Reload and reconcile the draft."
        raise AtlasConflictError(message)
    result = project.model_copy(deep=True)
    change = data.change
    if isinstance(change, AtlasProjectUpdate):
        if result.brief != change.brief:
            result.brief_revision += 1
        result.title = change.title
        result.brief = change.brief
        result.lifecycle = change.lifecycle
        result.next_action = change.next_action
    elif isinstance(change, AtlasConcernSave):
        _save_concern(result, change, record_id)
    elif isinstance(change, AtlasConcernAssess):
        _assess_concern(result, change, author=author, now=now, record_id=record_id)
    elif isinstance(change, AtlasDecisionRecord):
        _record_decision(result, change, author=author, now=now, record_id=record_id)
    else:
        _add_reference(result, change, author=author, now=now, record_id=record_id)
    result.version += 1
    result.updated_at = now
    return result


@runtime_checkable
class AtlasStorePort(Protocol):
    """Owner-scoped aggregate access; reference target validation belongs to admission."""

    async def list_projects(self, owner: str, limit: int = 50, offset: int = 0) -> AtlasCatalogue: ...

    async def get_project(self, owner: str, project_id: UUID) -> AtlasProject: ...

    async def create_project(self, owner: str, data: AtlasCreate) -> AtlasProject: ...

    async def change_project(self, owner: str, project_id: UUID, data: AtlasMutation) -> AtlasProject: ...

    async def replay_change(self, owner: str, project_id: UUID, data: AtlasMutation) -> AtlasProject | None: ...

    async def projects_for_reference(
        self, owner: str, kind: AtlasReferenceKind, target_id: str
    ) -> list[AtlasSummary]: ...


class InMemoryAtlasStore:
    """Loop-confined atomic aggregate changes with detached values and exact retries."""

    def __init__(self) -> None:
        """Create an empty process-local profile, with no persistence claim."""
        self._projects: dict[UUID, AtlasProject] = {}
        self._owners: dict[UUID, str] = {}
        self._creation_digests: dict[UUID, str] = {}
        self._requests: dict[UUID, tuple[UUID, str]] = {}

    def _owned_project(self, owner: str, project_id: UUID) -> AtlasProject:
        if self._owners.get(project_id) != owner:
            message = "Atlas Project is unavailable."
            raise AtlasNotFoundError(message)
        return self._projects[project_id]

    async def list_projects(self, owner: str, limit: int = 50, offset: int = 0) -> AtlasCatalogue:
        validate_page(limit, offset)
        projects = sorted(
            (project for project in self._projects.values() if self._owners[project.id] == owner),
            key=lambda project: (project.updated_at, project.id),
            reverse=True,
        )
        return AtlasCatalogue(
            projects=[summarize_project(project) for project in projects[offset : offset + limit]],
            total=len(projects),
            limit=limit,
            offset=offset,
        )

    async def get_project(self, owner: str, project_id: UUID) -> AtlasProject:
        return self._owned_project(owner, project_id).model_copy(deep=True)

    async def create_project(self, owner: str, data: AtlasCreate) -> AtlasProject:
        digest = payload_digest(data)
        if data.id in self._projects:
            existing = self._owned_project(owner, data.id)
            if self._creation_digests[data.id] != digest:
                message = "Atlas Project identity was already used for a different creation payload."
                raise AtlasConflictError(message)
            return existing.model_copy(deep=True)
        project = new_project(data, now=datetime.now(UTC))
        self._projects[data.id] = project
        self._owners[data.id] = owner
        self._creation_digests[data.id] = digest
        return project.model_copy(deep=True)

    async def change_project(self, owner: str, project_id: UUID, data: AtlasMutation) -> AtlasProject:
        project = self._owned_project(owner, project_id)
        digest = payload_digest(data)
        receipt = self._requests.get(data.request_id)
        if receipt is not None:
            if receipt != (project_id, digest):
                message = "Atlas request identity was already used for a different Project or payload."
                raise AtlasConflictError(message)
            return project.model_copy(deep=True)
        result = apply_change(project, data, author=owner, now=datetime.now(UTC), record_id=uuid4())
        self._projects[project_id] = result
        self._requests[data.request_id] = (project_id, digest)
        return result.model_copy(deep=True)

    async def replay_change(self, owner: str, project_id: UUID, data: AtlasMutation) -> AtlasProject | None:
        """Resolve retained retries before a controller revalidates activity targets."""
        project = self._owned_project(owner, project_id)
        receipt = self._requests.get(data.request_id)
        if receipt is None:
            return None
        if receipt != (project_id, payload_digest(data)):
            message = "Atlas request identity was already used for a different Project or payload."
            raise AtlasConflictError(message)
        return project.model_copy(deep=True)

    async def projects_for_reference(self, owner: str, kind: AtlasReferenceKind, target_id: str) -> list[AtlasSummary]:
        projects = sorted(
            (
                project
                for project in self._projects.values()
                if self._owners[project.id] == owner
                and any(reference.kind == kind and reference.target_id == target_id for reference in project.references)
            ),
            key=lambda project: (project.updated_at, project.id),
            reverse=True,
        )
        return [summarize_project(project) for project in projects]
