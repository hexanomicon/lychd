"""Atlas ownership, retry identities, and requirement-based assessment history."""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from lychd.domain.web.atlas import (
    AtlasChange,
    AtlasConcernAssess,
    AtlasConcernSave,
    AtlasConflictError,
    AtlasCreate,
    AtlasDecisionRecord,
    AtlasJudgment,
    AtlasMutation,
    AtlasNotFoundError,
    AtlasProject,
    AtlasProjectUpdate,
    AtlasReferenceAdd,
    AtlasValidationError,
    InMemoryAtlasStore,
    payload_digest,
    summarize_project,
)

pytestmark = pytest.mark.asyncio


def mutation(project: AtlasProject, change: AtlasChange, request_id: UUID | None = None) -> AtlasMutation:
    return AtlasMutation(request_id=request_id or uuid4(), expected_version=project.version, change=change)


def add_concern(statement: str = "Can recovery be demonstrated?") -> AtlasConcernSave:
    return AtlasConcernSave(
        kind="concern.save", concern_id=None, statement=statement, criteria="Restore a retained backup"
    )


def update(project: AtlasProject, **changes: str) -> AtlasProjectUpdate:
    values = {
        "kind": "project.update",
        "title": project.title,
        "brief": project.brief,
        "lifecycle": project.lifecycle,
        "next_action": project.next_action,
    }
    values.update(changes)
    return AtlasProjectUpdate.model_validate(values)


async def test_creation_needs_no_execution_and_returns_detached_values() -> None:
    store = InMemoryAtlasStore()
    created = AtlasCreate(id=uuid4(), title="Ongoing stewardship", brief="Keep recovery understood")
    project = await store.create_project("magus", created)
    assert project.version == project.brief_revision == 1
    assert project.lifecycle == "active"
    assert project.concerns == project.assessments == project.decisions == project.references == []
    project.title = "Changed outside the store"
    assert (await store.get_project("magus", project.id)).title == created.title
    replay = await store.create_project("magus", created)
    assert replay.version == 1
    with pytest.raises(AtlasConflictError, match="creation payload"):
        await store.create_project("magus", created.model_copy(update={"title": "Different"}))


async def test_foreign_projects_and_children_are_unavailable() -> None:
    store = InMemoryAtlasStore()
    data = AtlasCreate(id=uuid4(), title="Private undertaking")
    project = await store.create_project("magus", data)
    command = mutation(project, add_concern())
    assert (await store.list_projects("other")).total == 0
    with pytest.raises(AtlasNotFoundError):
        await store.get_project("other", project.id)
    with pytest.raises(AtlasNotFoundError):
        await store.create_project("other", data)
    with pytest.raises(AtlasNotFoundError):
        await store.change_project("other", project.id, command)
    with pytest.raises(AtlasNotFoundError):
        await store.replay_change("other", project.id, command)
    missing = AtlasConcernSave(kind="concern.save", concern_id=uuid4(), statement="Missing", criteria="")
    with pytest.raises(AtlasNotFoundError):
        await store.change_project("magus", project.id, mutation(project, missing))


async def test_exact_mutation_and_creation_replay_return_latest_state_without_repeating_work() -> None:
    store = InMemoryAtlasStore()
    creation = AtlasCreate(id=uuid4(), title="Recovery")
    project = await store.create_project("magus", creation)
    command = mutation(project, add_concern())
    assert await store.replay_change("magus", project.id, command) is None
    project = await store.change_project("magus", project.id, command)
    project = await store.change_project(
        "magus", project.id, mutation(project, update(project, title="Recovery revised"))
    )
    replay = await store.change_project("magus", project.id, command)
    assert replay.version == 3
    assert replay.title == "Recovery revised"
    assert len(replay.concerns) == 1
    assert await store.replay_change("magus", project.id, command) == replay
    assert await store.create_project("magus", creation) == replay
    replay.concerns[0].statement = "External mutation"
    assert (await store.get_project("magus", project.id)).concerns[0].statement != "External mutation"


async def test_stale_or_changed_retry_and_cross_project_identity_reuse_are_refused() -> None:
    store = InMemoryAtlasStore()
    project = await store.create_project("magus", AtlasCreate(id=uuid4(), title="First"))
    command = mutation(project, add_concern())
    current = await store.change_project("magus", project.id, command)
    changed = mutation(project, add_concern("Altered retry"), command.request_id)
    with pytest.raises(AtlasConflictError, match="request identity"):
        await store.change_project("magus", project.id, changed)
    with pytest.raises(AtlasConflictError, match="request identity"):
        await store.replay_change("magus", project.id, changed)
    with pytest.raises(AtlasConflictError, match="changed since"):
        await store.change_project("magus", project.id, mutation(project, add_concern("Stale draft")))
    other = await store.create_project("magus", AtlasCreate(id=uuid4(), title="Second"))
    with pytest.raises(AtlasConflictError, match="different Project"):
        await store.change_project("magus", other.id, mutation(other, add_concern(), command.request_id))
    assert await store.get_project("magus", project.id) == current


async def test_same_version_race_accepts_one_edit_and_exact_race_replays_once() -> None:
    store = InMemoryAtlasStore()
    project = await store.create_project("magus", AtlasCreate(id=uuid4(), title="Concurrent"))
    results = await asyncio.gather(
        store.change_project("magus", project.id, mutation(project, add_concern("First draft"))),
        store.change_project("magus", project.id, mutation(project, add_concern("Second draft"))),
        return_exceptions=True,
    )
    assert sum(isinstance(result, AtlasProject) for result in results) == 1
    assert sum(isinstance(result, AtlasConflictError) for result in results) == 1
    project = await store.get_project("magus", project.id)
    command = mutation(project, add_concern("Same retry"))
    first, second = await asyncio.gather(
        store.change_project("magus", project.id, command),
        store.change_project("magus", project.id, command),
    )
    assert first == second
    assert first.version == 3
    assert len(first.concerns) == 2


async def test_assessments_retain_judged_basis_and_require_review_only_after_relevant_edits() -> None:
    store = InMemoryAtlasStore()
    project = await store.create_project("magus", AtlasCreate(id=uuid4(), title="Recovery", brief="Original brief"))
    project = await store.change_project("magus", project.id, mutation(project, add_concern()))
    concern = project.concerns[0]
    assert summarize_project(project).unassessed_count == 1
    assessment = AtlasConcernAssess(
        kind="concern.assess",
        concern_id=concern.id,
        judgment="sufficient",
        rationale="The operator reviewed the recovery record.",
        reference_ids=[],
    )
    project = await store.change_project("magus", project.id, mutation(project, assessment))
    original_assessment = project.assessments[0].model_copy(deep=True)
    assert original_assessment.author == "magus"
    assert summarize_project(project).unassessed_count == summarize_project(project).review_needed_count == 0
    project = await store.change_project("magus", project.id, mutation(project, update(project, lifecycle="paused")))
    assert project.brief_revision == 1
    assert summarize_project(project).review_needed_count == 0
    unchanged = AtlasConcernSave(
        kind="concern.save", concern_id=concern.id, statement=concern.statement, criteria=concern.criteria
    )
    project = await store.change_project("magus", project.id, mutation(project, unchanged))
    assert project.concerns[0].revision == 1
    project = await store.change_project("magus", project.id, mutation(project, update(project, brief="Revised brief")))
    assert project.brief_revision == 2
    assert summarize_project(project).review_needed_count == 1
    assert project.assessments[0] == original_assessment
    project = await store.change_project("magus", project.id, mutation(project, assessment))
    assert summarize_project(project).review_needed_count == 0
    revised = unchanged.model_copy(update={"criteria": "Restore under the new environment"})
    project = await store.change_project("magus", project.id, mutation(project, revised))
    assert project.concerns[0].revision == 2
    assert summarize_project(project).review_needed_count == 1
    assert project.assessments[-1].criteria == concern.criteria
    assert project.assessments[-1].brief == "Revised brief"
    assert project.assessments[-1].concern_revision == 1


async def test_invalid_assessment_does_not_change_project_or_claim_retry_identity() -> None:
    store = InMemoryAtlasStore()
    project = await store.create_project("magus", AtlasCreate(id=uuid4(), title="Evidence"))
    project = await store.change_project("magus", project.id, mutation(project, add_concern()))
    invalid = mutation(
        project,
        AtlasConcernAssess(
            kind="concern.assess",
            concern_id=project.concerns[0].id,
            judgment="insufficient",
            rationale="Unknown reference",
            reference_ids=[uuid4()],
        ),
    )
    with pytest.raises(AtlasValidationError, match="Assessment references"):
        await store.change_project("magus", project.id, invalid)
    assert await store.get_project("magus", project.id) == project
    assert await store.replay_change("magus", project.id, invalid) is None


async def test_reference_membership_and_citation_scope_are_explicit() -> None:
    store = InMemoryAtlasStore()
    project = await store.create_project("magus", AtlasCreate(id=uuid4(), title="References"))
    for statement in ("First concern", "Second concern"):
        project = await store.change_project("magus", project.id, mutation(project, add_concern(statement)))
    first, second = project.concerns
    for target_id, concern_id in (("run_finished", first.id), ("sess_original", None)):
        change = AtlasReferenceAdd(
            kind="reference.add",
            reference_kind="run" if concern_id else "session",
            target_id=target_id,
            concern_id=concern_id,
            note="Related activity; no automatic judgment",
        )
        project = await store.change_project("magus", project.id, mutation(project, change))
    assert summarize_project(project).unassessed_count == 2
    assert len(await store.projects_for_reference("magus", "session", "sess_original")) == 1
    assert await store.projects_for_reference("magus", "run", "sess_original") == []
    assert await store.projects_for_reference("other", "session", "sess_original") == []
    duplicate = AtlasReferenceAdd(
        kind="reference.add",
        reference_kind="session",
        target_id="sess_original",
        concern_id=None,
        note="Repeated link",
    )
    with pytest.raises(AtlasConflictError, match="already linked"):
        await store.change_project("magus", project.id, mutation(project, duplicate))
    wrong_scope = AtlasConcernAssess(
        kind="concern.assess",
        concern_id=second.id,
        judgment="disputed",
        rationale="This reference belongs to the other concern",
        reference_ids=[project.references[0].id],
    )
    with pytest.raises(AtlasValidationError):
        await store.change_project("magus", project.id, mutation(project, wrong_scope))
    allowed = wrong_scope.model_copy(update={"reference_ids": [project.references[1].id]})
    project = await store.change_project("magus", project.id, mutation(project, allowed))
    assert project.assessments[0].reference_ids == [project.references[1].id]
    assert project.assessments[0].judgment == "disputed"


async def test_decisions_append_and_only_current_decisions_can_be_superseded() -> None:
    store = InMemoryAtlasStore()
    project = await store.create_project("magus", AtlasCreate(id=uuid4(), title="Decisions"))
    first = AtlasDecisionRecord(
        kind="decision.record", statement="Use the first approach", rationale="Evidence", supersedes_id=None
    )
    project = await store.change_project("magus", project.id, mutation(project, first))
    original = project.decisions[0].model_copy(deep=True)
    replacement = AtlasDecisionRecord(
        kind="decision.record",
        statement="Use a revised approach",
        rationale="Changed assumptions",
        supersedes_id=original.id,
    )
    project = await store.change_project("magus", project.id, mutation(project, replacement))
    assert project.decisions[0] == original
    assert project.decisions[-1].supersedes_id == original.id
    with pytest.raises(AtlasConflictError, match="already been superseded"):
        await store.change_project("magus", project.id, mutation(project, replacement))
    with pytest.raises(AtlasNotFoundError):
        await store.change_project(
            "magus", project.id, mutation(project, replacement.model_copy(update={"supersedes_id": uuid4()}))
        )


async def test_close_and_reopen_preserve_records_and_execution_associations() -> None:
    store = InMemoryAtlasStore()
    project = await store.create_project("magus", AtlasCreate(id=uuid4(), title="Stewardship"))
    reference = AtlasReferenceAdd(
        kind="reference.add", reference_kind="run", target_id="run_active", concern_id=None, note="Still admitted"
    )
    project = await store.change_project("magus", project.id, mutation(project, reference))
    references = project.references.copy()
    for lifecycle in ("paused", "closed", "active"):
        project = await store.change_project(
            "magus", project.id, mutation(project, update(project, lifecycle=lifecycle))
        )
        assert project.references == references
        assert project.brief_revision == 1


async def test_catalogue_is_owner_scoped_and_paginated_without_conflating_empty_pages() -> None:
    store = InMemoryAtlasStore()
    for owner, title in (("magus", "First"), ("other", "Foreign"), ("magus", "Second")):
        await store.create_project(owner, AtlasCreate(id=uuid4(), title=title))
    first_page = await store.list_projects("magus", limit=1)
    assert first_page.total == 2
    assert first_page.projects[0].title == "Second"
    empty_page = await store.list_projects("magus", limit=1, offset=2)
    assert empty_page.total == 2
    assert empty_page.projects == []
    with pytest.raises(AtlasValidationError):
        await store.list_projects("magus", limit=0)
    with pytest.raises(AtlasValidationError):
        await store.list_projects("magus", offset=-1)


async def test_contracts_refuse_injected_authority_and_coerced_revisions() -> None:
    with pytest.raises(ValidationError):
        AtlasCreate.model_validate({"id": str(uuid4()), "title": "Project", "author": "other"})
    with pytest.raises(ValidationError):
        AtlasCreate(id=uuid4(), title="   ")
    with pytest.raises(ValidationError):
        AtlasMutation.model_validate(
            {"request_id": str(uuid4()), "expected_version": "1", "change": add_concern().model_dump()}
        )
    reference_id = uuid4()
    with pytest.raises(ValidationError):
        AtlasConcernAssess(
            kind="concern.assess",
            concern_id=uuid4(),
            judgment="sufficient",
            rationale="Review",
            reference_ids=[reference_id, reference_id],
        )
    project = AtlasCreate(id=uuid4(), title="Project")
    assert payload_digest(project) == payload_digest(AtlasCreate.model_validate_json(project.model_dump_json()))
    assert {"concerns", "assessments", "decisions", "references"} <= set(AtlasProject.model_json_schema()["required"])


@pytest.mark.parametrize(
    ("judgment", "expected_counts"),
    [("insufficient", (1, 0)), ("disputed", (0, 1))],
)
async def test_current_negative_counts_exclude_stale_and_superseded_assessments(
    judgment: AtlasJudgment, expected_counts: tuple[int, int]
) -> None:
    store = InMemoryAtlasStore()
    project = await store.create_project("magus", AtlasCreate(id=uuid4(), title="Recovery"))
    for statement in ("Recover the release", "Notify support"):
        project = await store.change_project("magus", project.id, mutation(project, add_concern(statement)))
    concern = project.concerns[0]
    assessment = AtlasConcernAssess(
        kind="concern.assess",
        concern_id=concern.id,
        judgment=judgment,
        rationale="The latest evidence does not settle recovery.",
        reference_ids=[],
    )
    project = await store.change_project("magus", project.id, mutation(project, assessment))
    project = await store.change_project("magus", project.id, mutation(project, update(project, lifecycle="paused")))
    summary = summarize_project(project)
    assert (summary.insufficient_count, summary.disputed_count) == expected_counts
    assert summary.unassessed_count == 1
    assert summary.review_needed_count == 0
    assert summary.lifecycle == "paused"

    sufficient = assessment.model_copy(update={"judgment": "sufficient"})
    project = await store.change_project("magus", project.id, mutation(project, sufficient))
    summary = summarize_project(project)
    assert summary.insufficient_count == summary.disputed_count == 0
    assert len(project.assessments) == 2

    project = await store.change_project("magus", project.id, mutation(project, assessment))
    changed_concern = AtlasConcernSave(
        kind="concern.save", concern_id=concern.id, statement=concern.statement, criteria="Revised conditions"
    )
    project = await store.change_project("magus", project.id, mutation(project, changed_concern))
    summary = summarize_project(project)
    assert summary.insufficient_count == summary.disputed_count == 0
    assert summary.review_needed_count == summary.unassessed_count == 1

    project = await store.change_project("magus", project.id, mutation(project, assessment))
    summary = summarize_project(project)
    assert (summary.insufficient_count, summary.disputed_count) == expected_counts
    assert summary.review_needed_count == 0
    project = await store.change_project("magus", project.id, mutation(project, update(project, brief="New brief")))
    summary = summarize_project(project)
    assert summary.insufficient_count == summary.disputed_count == 0
    assert summary.review_needed_count == summary.unassessed_count == 1
    assert summary.lifecycle == "paused"
    assert len(project.assessments) == 4


async def test_one_session_keeps_distinct_project_and_concern_relations() -> None:
    store = InMemoryAtlasStore()
    project = await store.create_project("magus", AtlasCreate(id=uuid4(), title="Shared conversation"))
    for statement in ("First concern", "Second concern"):
        project = await store.change_project("magus", project.id, mutation(project, add_concern(statement)))
    for concern_id in (None, *(concern.id for concern in project.concerns)):
        reference = AtlasReferenceAdd(
            kind="reference.add",
            reference_kind="session",
            target_id="sess_shared",
            concern_id=concern_id,
            note="Explicit relationship",
        )
        project = await store.change_project("magus", project.id, mutation(project, reference))
    assert len(project.references) == 3
    assert len(await store.projects_for_reference("magus", "session", "sess_shared")) == 1
    last_reference = project.references[-1]
    duplicate = AtlasReferenceAdd(
        kind="reference.add",
        reference_kind="session",
        target_id=last_reference.target_id,
        concern_id=last_reference.concern_id,
        note=last_reference.note,
    )
    with pytest.raises(AtlasConflictError, match="already linked"):
        await store.change_project("magus", project.id, mutation(project, duplicate))
    for concern in project.concerns:
        own_reference = next(reference for reference in project.references if reference.concern_id == concern.id)
        assessment = AtlasConcernAssess(
            kind="concern.assess",
            concern_id=concern.id,
            judgment="disputed",
            rationale="This concern uses its own relation.",
            reference_ids=[own_reference.id],
        )
        project = await store.change_project("magus", project.id, mutation(project, assessment))
    assert len({assessment.reference_ids[0] for assessment in project.assessments}) == 2
