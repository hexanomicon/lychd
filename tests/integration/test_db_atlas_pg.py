"""[LINUX] Disposable PostgreSQL Atlas ownership and atomic retry receipts."""

# pyright: reportMissingImports=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from __future__ import annotations

import asyncio
import hashlib
import os
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

from sqlalchemy import Table, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from lychd.compositions.canvas.workspace import lychd_project_id, lychd_workspace_document
from lychd.db.atlas import DbAtlasStore
from lychd.db.models.atlas import AtlasProjectRecord, AtlasRequestRecord
from lychd.domain.web.atlas import (
    AtlasCanvasSave,
    AtlasConcernAssess,
    AtlasConcernSave,
    AtlasConflictError,
    AtlasCreate,
    AtlasMutation,
    AtlasNotFoundError,
    AtlasProject,
    AtlasProjectDiscard,
    AtlasProjectKeep,
    AtlasProjectUpdate,
    AtlasReferenceAdd,
    AtlasValidationError,
    CanvasProjectCreate,
    apply_change,
    new_project,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.container, pytest.mark.asyncio]


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    # The daemon-free profile receives only an owned, disposable sidecar URL.
    # It never grants a test container control over the host Docker daemon.
    direct = os.environ.get("LYCHD_ATLAS_TEST_DATABASE_URL")
    if direct:
        url = make_url(direct)
        if (
            os.environ.get("LYCHD_TEST_CONTAINER") != "1"
            or url.drivername != "postgresql+asyncpg"
            or url.host != "canvas-postgres"
            or url.port != 5432
            or url.database != "canvas_test"
        ):
            message = "Atlas direct database tests require the isolated canvas-postgres/canvas_test OCI fixture."
            raise ValueError(message)
        yield direct
        return
    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as pg:
        yield pg.get_connection_url()


@pytest_asyncio.fixture
async def pg_factory(pg_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine: AsyncEngine = create_async_engine(pg_url)
    tables = cast("list[Table]", [AtlasProjectRecord.__table__, AtlasRequestRecord.__table__])
    async with engine.begin() as connection:
        await connection.run_sync(AtlasProjectRecord.metadata.drop_all, tables=tables)
        await connection.run_sync(AtlasProjectRecord.metadata.create_all, tables=tables)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def concern_mutation(project: AtlasProject, statement: str = "Demonstrate recovery") -> AtlasMutation:
    return AtlasMutation(
        request_id=uuid4(),
        expected_version=project.version,
        change=AtlasConcernSave(kind="concern.save", concern_id=None, statement=statement, criteria="Retained result"),
    )


async def test_concurrent_creation_replays_same_payload_and_refuses_different_payload(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    first = DbAtlasStore(pg_factory)
    second = DbAtlasStore(pg_factory)
    data = AtlasCreate(id=uuid4(), title="Same creation")
    projects = await asyncio.gather(first.create_project("magus", data), second.create_project("magus", data))
    assert projects[0] == projects[1]
    conflicting_id = uuid4()
    results = await asyncio.gather(
        first.create_project("magus", AtlasCreate(id=conflicting_id, title="First draft")),
        second.create_project("magus", AtlasCreate(id=conflicting_id, title="Second draft")),
        return_exceptions=True,
    )
    assert sum(isinstance(result, AtlasProject) for result in results) == 1
    assert sum(isinstance(result, AtlasConflictError) for result in results) == 1
    assert (await first.list_projects("magus")).total == 2


async def test_concurrent_versions_and_replay_survive_store_reconstruction(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    first = DbAtlasStore(pg_factory)
    second = DbAtlasStore(pg_factory)
    creation = AtlasCreate(id=uuid4(), title="Concurrent edits", brief="Original brief")
    project = await first.create_project("magus", creation)
    commands = [concern_mutation(project, "First concern"), concern_mutation(project, "Second concern")]
    results = await asyncio.gather(
        first.change_project("magus", project.id, commands[0]),
        second.change_project("magus", project.id, commands[1]),
        return_exceptions=True,
    )
    assert sum(isinstance(result, AtlasProject) for result in results) == 1
    assert sum(isinstance(result, AtlasConflictError) for result in results) == 1
    winner = next(
        command for command, result in zip(commands, results, strict=True) if isinstance(result, AtlasProject)
    )
    project = await first.get_project("magus", project.id)
    changed = AtlasMutation(
        request_id=uuid4(),
        expected_version=project.version,
        change=AtlasProjectUpdate(
            kind="project.update", title="Revised", brief="Revised brief", lifecycle="paused", next_action="Review"
        ),
    )
    current = await second.change_project("magus", project.id, changed)
    reconstructed = DbAtlasStore(pg_factory)
    assert await reconstructed.replay_change("magus", project.id, winner) == current
    assert await reconstructed.change_project("magus", project.id, winner) == current
    assert await reconstructed.create_project("magus", creation) == current
    assert len(current.concerns) == 1
    assert current.version == 3
    assert current.brief_revision == 2
    async with pg_factory() as session:
        row = await session.get(AtlasProjectRecord, project.id)
        assert row is not None
        assert row.version == current.version == row.document["version"]
        assert row.document["brief_revision"] == 2
        assert AtlasProject.model_validate(row.document) == current


async def test_concurrent_exact_mutation_creates_one_child_and_one_receipt(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = DbAtlasStore(pg_factory)
    project = await store.create_project("magus", AtlasCreate(id=uuid4(), title="Exact retries"))
    command = concern_mutation(project)
    first, second = await asyncio.gather(
        store.change_project("magus", project.id, command),
        DbAtlasStore(pg_factory).change_project("magus", project.id, command),
    )
    assert first == second
    assert first.version == 2
    assert len(first.concerns) == 1
    async with pg_factory() as session:
        receipts = list(await session.scalars(select(AtlasRequestRecord)))
        assert len(receipts) == 1


async def test_cross_project_request_race_rolls_back_losing_document_and_receipt(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = DbAtlasStore(pg_factory)
    projects = [
        await store.create_project("magus", AtlasCreate(id=uuid4(), title=title))
        for title in ("First project", "Second project")
    ]
    request_id = uuid4()
    commands = [concern_mutation(project).model_copy(update={"request_id": request_id}) for project in projects]
    results = await asyncio.gather(
        store.change_project("magus", projects[0].id, commands[0]),
        DbAtlasStore(pg_factory).change_project("magus", projects[1].id, commands[1]),
        return_exceptions=True,
    )
    assert sum(isinstance(result, AtlasProject) for result in results) == 1
    assert sum(isinstance(result, AtlasConflictError) for result in results) == 1
    retained = [await store.get_project("magus", project.id) for project in projects]
    assert sorted(project.version for project in retained) == [1, 2]
    assert sum(len(project.concerns) for project in retained) == 1
    async with pg_factory() as session:
        receipts = list(await session.scalars(select(AtlasRequestRecord)))
        assert len(receipts) == 1
        winner = next(project for project in retained if project.version == 2)
        assert receipts[0].project_id == winner.id


async def test_foreign_access_and_invalid_change_leave_no_partial_receipt(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = DbAtlasStore(pg_factory)
    creation = AtlasCreate(id=uuid4(), title="Owned")
    project = await store.create_project("magus", creation)
    command = concern_mutation(project)
    with pytest.raises(AtlasNotFoundError):
        await store.get_project("other", project.id)
    with pytest.raises(AtlasNotFoundError):
        await store.create_project("other", creation)
    with pytest.raises(AtlasNotFoundError):
        await store.change_project("other", project.id, command)
    with pytest.raises(AtlasNotFoundError):
        await store.replay_change("other", project.id, command)
    assert (await store.list_projects("other")).total == 0
    project = await store.change_project("magus", project.id, command)
    invalid = AtlasMutation(
        request_id=uuid4(),
        expected_version=project.version,
        change=AtlasConcernAssess(
            kind="concern.assess",
            concern_id=project.concerns[0].id,
            judgment="sufficient",
            rationale="Not retained",
            reference_ids=[uuid4()],
        ),
    )
    with pytest.raises(AtlasValidationError):
        await store.change_project("magus", project.id, invalid)
    assert await store.get_project("magus", project.id) == project
    assert await store.replay_change("magus", project.id, invalid) is None
    async with pg_factory() as session:
        assert await session.get(AtlasRequestRecord, invalid.request_id) is None


async def test_reverse_references_are_typed_explicit_and_owner_scoped(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = DbAtlasStore(pg_factory)
    project = await store.create_project("magus", AtlasCreate(id=uuid4(), title="Linked"))
    command = AtlasMutation(
        request_id=uuid4(),
        expected_version=project.version,
        change=AtlasReferenceAdd(
            kind="reference.add", reference_kind="session", target_id="sess_existing", concern_id=None, note="Context"
        ),
    )
    project = await store.change_project("magus", project.id, command)
    assert [summary.id for summary in await store.projects_for_reference("magus", "session", "sess_existing")] == [
        project.id
    ]
    assert await store.projects_for_reference("magus", "run", "sess_existing") == []
    assert await store.projects_for_reference("other", "session", "sess_existing") == []


async def test_canvas_pinning_filters_discarded_before_pagination_and_survives_reconstruction(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = DbAtlasStore(pg_factory)
    seed = CanvasProjectCreate(id=lychd_project_id("magus"), canvas_document=lychd_workspace_document("magus"))
    for owner in ("magus", "other"):
        with pytest.raises(AtlasConflictError, match="reserved"):
            await store.create_project(owner, AtlasCreate(id=seed.id, title="Squat"))
        with pytest.raises(AtlasConflictError, match="reserved"):
            await store.create_canvas_project(owner, seed)
    first, replay = await asyncio.gather(
        store.create_canvas_project("magus", seed, builtin=True),
        DbAtlasStore(pg_factory).create_canvas_project("magus", seed, builtin=True),
    )
    assert first == replay
    creations = [CanvasProjectCreate(id=uuid4(), canvas_document=lychd_workspace_document("draft")) for _ in range(3)]
    projects = [await store.create_canvas_project("magus", creation) for creation in creations]
    discarded = projects[-1]
    discard = AtlasMutation(
        request_id=uuid4(), expected_version=discarded.version, change=AtlasProjectDiscard(kind="project.discard")
    )
    tombstone = await store.change_project("magus", discarded.id, discard)
    assert tombstone.workspace_state == "discarded"
    reconstructed = DbAtlasStore(pg_factory)
    for offset, expected_size in ((0, 1), (1, 1), (2, 0)):
        page = await reconstructed.list_projects("magus", limit=1, offset=offset)
        assert page.total == 2
        assert len(page.projects) == expected_size
        assert all(project.id != discarded.id for project in page.projects)
        assert page.pinned is not None
        assert page.pinned.id == first.id
    assert await reconstructed.get_project("magus", first.id) == first
    assert await reconstructed.create_canvas_project("magus", creations[-1]) == tombstone
    assert await reconstructed.change_project("magus", discarded.id, discard) == tombstone
    assert await reconstructed.replay_change("magus", discarded.id, discard) == tombstone
    with pytest.raises(AtlasConflictError, match="discarded"):
        await reconstructed.change_project(
            "magus",
            discarded.id,
            AtlasMutation(
                request_id=uuid4(), expected_version=tombstone.version, change=AtlasProjectKeep(kind="project.keep")
            ),
        )
    with pytest.raises(AtlasNotFoundError):
        await reconstructed.create_canvas_project("other", creations[0])
    assert (await reconstructed.list_projects("other")).pinned is None


async def test_canvas_concurrent_saves_share_the_project_lock_and_replay_after_discard(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = DbAtlasStore(pg_factory)
    creation = CanvasProjectCreate(id=uuid4(), canvas_document=lychd_workspace_document("draft"))
    project = await store.create_canvas_project("magus", creation)
    commands = [
        AtlasMutation(
            request_id=uuid4(),
            expected_version=project.version,
            change=AtlasCanvasSave(
                kind="canvas.save",
                canvas_document=creation.canvas_document.model_copy(
                    update={"scene": creation.canvas_document.scene.model_copy(update={"revision": 2, "title": title})}
                ),
            ),
        )
        for title in ("First", "Second")
    ]
    results = await asyncio.gather(
        store.change_project("magus", project.id, commands[0]),
        DbAtlasStore(pg_factory).change_project("magus", project.id, commands[1]),
        return_exceptions=True,
    )
    assert sum(isinstance(result, AtlasProject) for result in results) == 1
    assert sum(isinstance(result, AtlasConflictError) for result in results) == 1
    winner = next(
        command for command, result in zip(commands, results, strict=True) if isinstance(result, AtlasProject)
    )
    current = await store.get_project("magus", project.id)
    assert current.canvas_document is not None
    assert current.version == 2
    tombstone = await store.change_project(
        "magus",
        project.id,
        AtlasMutation(
            request_id=uuid4(), expected_version=current.version, change=AtlasProjectDiscard(kind="project.discard")
        ),
    )
    reconstructed = DbAtlasStore(pg_factory)
    assert await reconstructed.change_project("magus", project.id, winner) == tombstone
    assert await reconstructed.create_canvas_project("magus", creation) == tombstone
    async with pg_factory() as session:
        receipts = list(await session.scalars(select(AtlasRequestRecord)))
        assert len(receipts) == 2
        row = await session.get(AtlasProjectRecord, project.id)
        assert row is not None
        assert row.version == row.document["version"] == 3
        assert row.document["workspace_state"] == "discarded"


async def test_legacy_json_and_retained_create_and_request_digests_survive_canvas_attachment(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    creation = AtlasCreate(id=UUID("1ec4d000-0000-4000-8000-000000000001"), title="Legacy")
    command = AtlasMutation(
        request_id=UUID("20000000-0000-4000-8000-000000000002"),
        expected_version=1,
        change=AtlasConcernSave(kind="concern.save", concern_id=None, statement="Question", criteria=""),
    )
    legacy_creation_digest = hashlib.sha256(
        b'{"brief":"","id":"1ec4d000-0000-4000-8000-000000000001","next_action":"","title":"Legacy"}'
    ).hexdigest()
    legacy_request_digest = hashlib.sha256(
        b'{"change":{"concern_id":null,"criteria":"","kind":"concern.save","statement":"Question"},'
        b'"expected_version":1,"request_id":"20000000-0000-4000-8000-000000000002"}'
    ).hexdigest()
    original = apply_change(
        new_project(creation, now=datetime.now(UTC)),
        command,
        author="magus",
        now=datetime.now(UTC),
        record_id=uuid4(),
    )
    old_document = original.model_dump(mode="json", exclude={"canvas_document", "workspace_state", "builtin"})
    async with pg_factory() as session, session.begin():
        session.add(
            AtlasProjectRecord(
                id=original.id,
                sigil_name="magus",
                version=original.version,
                document=old_document,
                creation_digest=legacy_creation_digest,
                created_at=original.created_at,
                updated_at=original.updated_at,
            )
        )
        await session.flush()
        session.add(
            AtlasRequestRecord(id=command.request_id, project_id=original.id, payload_digest=legacy_request_digest)
        )
    store = DbAtlasStore(pg_factory)
    restored = await store.get_project("magus", original.id)
    assert restored == original
    assert restored.workspace_state == "kept"
    assert (await store.list_projects("magus")).total == 1
    assert await store.create_project("magus", creation) == restored
    assert await store.change_project("magus", original.id, command) == restored
    attached = await store.change_project(
        "magus",
        restored.id,
        AtlasMutation(
            request_id=uuid4(),
            expected_version=restored.version,
            change=AtlasCanvasSave(kind="canvas.save", canvas_document=lychd_workspace_document("legacy")),
        ),
    )
    assert attached.concerns == original.concerns
    assert attached.title == original.title
    assert attached.workspace_state == "kept"
    assert await DbAtlasStore(pg_factory).create_project("magus", creation) == attached
    assert await DbAtlasStore(pg_factory).replay_change("magus", original.id, command) == attached
    with pytest.raises(AtlasValidationError):
        await store.change_project(
            "magus",
            attached.id,
            AtlasMutation(
                request_id=uuid4(),
                expected_version=attached.version,
                change=AtlasProjectDiscard(kind="project.discard"),
            ),
        )
    async with pg_factory() as session:
        row = await session.get(AtlasProjectRecord, original.id)
        receipt = await session.get(AtlasRequestRecord, command.request_id)
        assert row is not None
        assert row.creation_digest == legacy_creation_digest
        assert receipt is not None
        assert receipt.payload_digest == legacy_request_digest
