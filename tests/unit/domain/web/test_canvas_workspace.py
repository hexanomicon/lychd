"""Primary Canvas custody, legacy replay compatibility and discard protection."""

from __future__ import annotations

import asyncio
import hashlib
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from pydantic import ValidationError

from lychd.compositions.canvas.schemas import CanvasDocument, CanvasScene
from lychd.compositions.canvas.workspace import (
    is_reserved_system_project_id,
    lychd_project_id,
    lychd_workspace_document,
)
from lychd.domain.web.atlas import (
    AtlasCanvasSave,
    AtlasChange,
    AtlasConcernSave,
    AtlasConflictError,
    AtlasCreate,
    AtlasDecisionRecord,
    AtlasMutation,
    AtlasNotFoundError,
    AtlasProject,
    AtlasProjectDiscard,
    AtlasProjectKeep,
    AtlasReferenceAdd,
    AtlasValidationError,
    CanvasProjectCreate,
    InMemoryAtlasStore,
    payload_digest,
)

pytestmark = pytest.mark.asyncio


def document(title: str = "Draft board") -> CanvasDocument:
    return CanvasDocument(
        format="lychd.canvas.document/1",
        scene=CanvasScene(
            format="lychd.canvas/1", id=str(uuid4()), revision=1, title=title, strokes=[], nodes=[], edges=[]
        ),
        past=[],
        future=[],
    )


def mutation(project: AtlasProject, change: AtlasChange) -> AtlasMutation:
    return AtlasMutation(request_id=uuid4(), expected_version=project.version, change=change)


async def test_creation_save_and_discard_replay_cannot_resurrect_a_draft() -> None:
    store = InMemoryAtlasStore()
    creation = CanvasProjectCreate(id=uuid4(), canvas_document=document())
    project = await store.create_canvas_project("magus", creation)
    assert project.workspace_state == "draft"
    assert project.canvas_document == creation.canvas_document
    assert (await store.list_projects("magus")).projects[0].has_canvas
    assert await store.create_canvas_project("magus", creation) == project
    assert project.canvas_document is not None
    revised = project.canvas_document.model_copy(
        update={"scene": project.canvas_document.scene.model_copy(update={"revision": 2, "title": "Revised board"})}
    )
    save = mutation(project, AtlasCanvasSave(kind="canvas.save", canvas_document=revised))
    project = await store.change_project("magus", project.id, save)
    discard = mutation(project, AtlasProjectDiscard(kind="project.discard"))
    tombstone = await store.change_project("magus", project.id, discard)
    assert tombstone.workspace_state == "discarded"
    assert tombstone.canvas_document == revised
    assert (await store.list_projects("magus")).total == 0
    assert await store.create_canvas_project("magus", creation) == tombstone
    assert await store.change_project("magus", project.id, save) == tombstone
    assert await store.change_project("magus", project.id, discard) == tombstone
    assert await store.replay_change("magus", project.id, save) == tombstone
    with pytest.raises(AtlasConflictError, match="discarded"):
        await store.change_project("magus", project.id, mutation(tombstone, AtlasProjectKeep(kind="project.keep")))
    with pytest.raises(AtlasConflictError, match="creation payload"):
        await store.create_canvas_project("magus", creation.model_copy(update={"canvas_document": revised}))
    with pytest.raises(AtlasNotFoundError):
        await store.create_canvas_project("other", creation)


async def test_keep_and_planning_records_protect_drafts_from_discard() -> None:
    store = InMemoryAtlasStore()
    kept = await store.create_canvas_project("magus", CanvasProjectCreate(id=uuid4(), canvas_document=document()))
    kept = await store.change_project("magus", kept.id, mutation(kept, AtlasProjectKeep(kind="project.keep")))
    for change in (
        AtlasConcernSave(kind="concern.save", concern_id=None, statement="Retained concern", criteria=""),
        AtlasDecisionRecord(
            kind="decision.record", statement="Retain", rationale="Authored record", supersedes_id=None
        ),
        AtlasReferenceAdd(
            kind="reference.add", reference_kind="run", target_id="run-retained", concern_id=None, note=""
        ),
    ):
        project = await store.create_canvas_project(
            "magus", CanvasProjectCreate(id=uuid4(), canvas_document=document())
        )
        project = await store.change_project("magus", project.id, mutation(project, change))
        discard = mutation(project, AtlasProjectDiscard(kind="project.discard"))
        with pytest.raises(AtlasValidationError, match="without retained planning records"):
            await store.change_project("magus", project.id, discard)
        assert await store.get_project("magus", project.id) == project
        assert await store.replay_change("magus", project.id, discard) is None
    legacy = await store.create_project("magus", AtlasCreate(id=uuid4(), title="Legacy"))
    for project in (kept, legacy):
        with pytest.raises(AtlasValidationError, match="Only a Canvas draft"):
            await store.change_project(
                "magus", project.id, mutation(project, AtlasProjectDiscard(kind="project.discard"))
            )


async def test_attach_preserves_legacy_title_records_and_primary_scene_identity() -> None:
    store = InMemoryAtlasStore()
    creation = AtlasCreate(id=uuid4(), title="L" * 200, brief="Keep the original basis")
    project = await store.create_project("magus", creation)
    concern = AtlasConcernSave(kind="concern.save", concern_id=None, statement="Retained", criteria="")
    project = await store.change_project("magus", project.id, mutation(project, concern))
    original = project.model_copy(deep=True)
    board = document("A separate board title")
    project = await store.change_project(
        "magus", project.id, mutation(project, AtlasCanvasSave(kind="canvas.save", canvas_document=board))
    )
    assert project.title == original.title
    assert project.concerns == original.concerns
    assert project.brief_revision == original.brief_revision
    assert project.workspace_state == "kept"
    assert await store.create_project("magus", creation) == project
    invalid = mutation(project, AtlasCanvasSave(kind="canvas.save", canvas_document=document()))
    with pytest.raises(AtlasValidationError, match="primary scene identity"):
        await store.change_project("magus", project.id, invalid)
    assert await store.get_project("magus", project.id) == project
    assert await store.replay_change("magus", project.id, invalid) is None
    assert project.canvas_document is not None
    project.canvas_document.past.append(board.scene)
    assert (await store.get_project("magus", project.id)).canvas_document == board


async def test_concurrent_versions_reject_one_and_exact_retries_apply_once() -> None:
    store = InMemoryAtlasStore()
    board = document()
    project = await store.create_canvas_project("magus", CanvasProjectCreate(id=uuid4(), canvas_document=board))
    commands = [
        mutation(
            project,
            AtlasCanvasSave(
                kind="canvas.save",
                canvas_document=board.model_copy(
                    update={"scene": board.scene.model_copy(update={"revision": 2, "title": title})}
                ),
            ),
        )
        for title in ("First", "Second")
    ]
    results = await asyncio.gather(
        *(store.change_project("magus", project.id, command) for command in commands), return_exceptions=True
    )
    assert sum(isinstance(result, AtlasProject) for result in results) == 1
    assert sum(isinstance(result, AtlasConflictError) for result in results) == 1
    project = await store.get_project("magus", project.id)
    command = mutation(project, AtlasProjectKeep(kind="project.keep"))
    first, second = await asyncio.gather(
        store.change_project("magus", project.id, command), store.change_project("magus", project.id, command)
    )
    assert first == second
    assert first.version == 3


async def test_mutated_documents_are_revalidated_without_claiming_a_receipt() -> None:
    store = InMemoryAtlasStore()
    board = document()
    project = await store.create_canvas_project("magus", CanvasProjectCreate(id=uuid4(), canvas_document=board))
    command = mutation(project, AtlasCanvasSave(kind="canvas.save", canvas_document=board))
    assert isinstance(command.change, AtlasCanvasSave)
    command.change.canvas_document.past.extend([board.scene] * 21)
    with pytest.raises(ValidationError):
        await store.change_project("magus", project.id, command)
    assert await store.get_project("magus", project.id) == project
    assert await store.replay_change("magus", project.id, command) is None


async def test_seed_is_reserved_owner_scoped_and_pinned_independently_of_pagination() -> None:
    store = InMemoryAtlasStore()
    seed = CanvasProjectCreate(id=lychd_project_id("magus"), canvas_document=lychd_workspace_document("magus"))
    assert len(seed.canvas_document.scene.nodes) == 14
    assert seed.canvas_document == lychd_workspace_document("magus")
    assert seed.canvas_document.scene.id != lychd_workspace_document("other").scene.id
    with pytest.raises(AtlasConflictError, match="reserved"):
        await store.create_project("magus", AtlasCreate(id=seed.id, title="Squat"))
    with pytest.raises(AtlasConflictError, match="reserved"):
        await store.create_canvas_project("magus", seed)
    project = await store.create_canvas_project("magus", seed, builtin=True)
    assert project.builtin
    assert project.workspace_state == "kept"
    assert "Static reference" in project.brief
    assert await store.create_canvas_project("magus", seed, builtin=True) == project
    for title in ("First", "Second"):
        await store.create_canvas_project("magus", CanvasProjectCreate(id=uuid4(), canvas_document=document(title)))
    for offset, expected_size in ((0, 1), (1, 1), (2, 0)):
        page = await store.list_projects("magus", limit=1, offset=offset)
        assert page.total == 2
        assert len(page.projects) == expected_size
        assert page.pinned is not None
        assert page.pinned.id == project.id
    assert (await store.list_projects("other")).pinned is None
    with pytest.raises(AtlasValidationError):
        await store.change_project("magus", project.id, mutation(project, AtlasProjectDiscard(kind="project.discard")))


async def test_system_range_blocks_cross_owner_squatting_without_rejecting_other_uuid5_ids() -> None:
    store = InMemoryAtlasStore()
    victim_id = lychd_project_id("magus")
    assert is_reserved_system_project_id(victim_id)
    assert victim_id.version == 5
    for owner in ("other", "magus"):
        with pytest.raises(AtlasConflictError, match="reserved"):
            await store.create_project(owner, AtlasCreate(id=victim_id, title="Squat"))
        with pytest.raises(AtlasConflictError, match="reserved"):
            await store.create_canvas_project(owner, CanvasProjectCreate(id=victim_id, canvas_document=document()))
    with pytest.raises(AtlasConflictError, match="reserved"):
        await store.create_canvas_project(
            "other", CanvasProjectCreate(id=victim_id, canvas_document=document()), builtin=True
        )
    ordinary_id = uuid5(NAMESPACE_URL, "ordinary-caller-project")
    ordinary = await store.create_project("other", AtlasCreate(id=ordinary_id, title="Ordinary UUID5"))
    assert ordinary.id == ordinary_id
    seed = await store.create_canvas_project(
        "magus", CanvasProjectCreate(id=victim_id, canvas_document=lychd_workspace_document("magus")), builtin=True
    )
    assert seed.builtin


async def test_exact_creations_replay_before_a_newly_reserved_range_is_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    store = InMemoryAtlasStore()
    legacy_creation = AtlasCreate(id=uuid4(), title="Already retained")
    legacy = await store.create_project("magus", legacy_creation)
    canvas_creation = CanvasProjectCreate(id=uuid4(), canvas_document=document())
    canvas = await store.create_canvas_project("magus", canvas_creation)
    monkeypatch.setattr("lychd.compositions.canvas.workspace._SYSTEM_PROJECT_PREFIX", legacy.id.bytes[:4])
    assert is_reserved_system_project_id(legacy.id)
    assert await store.create_project("magus", legacy_creation) == legacy
    monkeypatch.setattr("lychd.compositions.canvas.workspace._SYSTEM_PROJECT_PREFIX", canvas.id.bytes[:4])
    assert is_reserved_system_project_id(canvas.id)
    assert await store.create_canvas_project("magus", canvas_creation) == canvas


async def test_legacy_canonical_create_and_mutation_bytes_and_old_documents_remain_compatible() -> None:
    identity = UUID("10000000-0000-4000-8000-000000000001")
    creation = AtlasCreate(id=identity, title="Legacy")
    legacy_create = b'{"brief":"","id":"10000000-0000-4000-8000-000000000001","next_action":"","title":"Legacy"}'
    assert payload_digest(creation) == hashlib.sha256(legacy_create).hexdigest()
    command = AtlasMutation(
        request_id=UUID("20000000-0000-4000-8000-000000000002"),
        expected_version=1,
        change=AtlasConcernSave(kind="concern.save", concern_id=None, statement="Question", criteria=""),
    )
    legacy_mutation = (
        b'{"change":{"concern_id":null,"criteria":"","kind":"concern.save","statement":"Question"},'
        b'"expected_version":1,"request_id":"20000000-0000-4000-8000-000000000002"}'
    )
    assert payload_digest(command) == hashlib.sha256(legacy_mutation).hexdigest()
    store = InMemoryAtlasStore()
    project = await store.create_project("magus", creation)
    project = await store.change_project("magus", project.id, command)
    old_document = project.model_dump(mode="json", exclude={"canvas_document", "workspace_state", "builtin"})
    restored = AtlasProject.model_validate(old_document)
    assert restored.workspace_state == "kept"
    assert restored.canvas_document is None
    assert not restored.builtin
    assert restored.concerns == project.concerns
