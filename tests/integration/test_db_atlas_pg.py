"""[LINUX] Disposable PostgreSQL Atlas ownership and atomic retry receipts."""

# pyright: reportMissingImports=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest
import pytest_asyncio

pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from lychd.db.atlas import DbAtlasStore
from lychd.db.models.atlas import AtlasProjectRecord, AtlasRequestRecord
from lychd.domain.web.atlas import (
    AtlasConcernAssess,
    AtlasConcernSave,
    AtlasConflictError,
    AtlasCreate,
    AtlasMutation,
    AtlasNotFoundError,
    AtlasProject,
    AtlasProjectUpdate,
    AtlasReferenceAdd,
    AtlasValidationError,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.container, pytest.mark.asyncio]


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
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
