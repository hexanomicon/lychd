"""PostgreSQL Atlas aggregates with owner-scoped locks and atomic retry receipts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from lychd.domain.web.atlas import (
    AtlasCatalogue,
    AtlasConflictError,
    AtlasCreate,
    AtlasMutation,
    AtlasNotFoundError,
    AtlasProject,
    AtlasReferenceKind,
    AtlasSummary,
    apply_change,
    new_project,
    payload_digest,
    summarize_project,
    validate_page,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from lychd.db.models.atlas import AtlasProjectRecord

__all__ = ["DbAtlasStore"]


def _document(row: AtlasProjectRecord) -> AtlasProject:
    project = AtlasProject.model_validate(row.document)
    if project.id != row.id or project.version != row.version:
        message = "Atlas retained document identity or version differs from its aggregate row."
        raise RuntimeError(message)
    return project


class DbAtlasStore:
    """Persist each aggregate successor and its exact request identity together."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Bind the adapter to the Vessel's configured database factory."""
        self._session_factory = session_factory

    async def _owned_row(self, session: AsyncSession, owner: str, project_id: UUID) -> AtlasProjectRecord:
        from lychd.db.models.atlas import AtlasProjectRecord

        row = await session.scalar(
            select(AtlasProjectRecord)
            .where(AtlasProjectRecord.id == project_id, AtlasProjectRecord.sigil_name == owner)
            .with_for_update()
        )
        if row is None:
            message = "Atlas Project is unavailable."
            raise AtlasNotFoundError(message)
        return row

    async def _receipt_matches(self, session: AsyncSession, project_id: UUID, data: AtlasMutation) -> bool:
        from lychd.db.models.atlas import AtlasRequestRecord

        receipt = await session.get(AtlasRequestRecord, data.request_id)
        if receipt is None:
            return False
        if receipt.project_id != project_id or receipt.payload_digest != payload_digest(data):
            message = "Atlas request identity was already used for a different Project or payload."
            raise AtlasConflictError(message)
        return True

    async def list_projects(self, owner: str, limit: int = 50, offset: int = 0) -> AtlasCatalogue:
        from lychd.db.models.atlas import AtlasProjectRecord

        validate_page(limit, offset)
        async with self._session_factory() as session, session.begin():
            # Both statements must describe one catalogue snapshot, including
            # an empty page beyond the end of a concurrently growing catalogue.
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            total = await session.scalar(
                select(func.count()).select_from(AtlasProjectRecord).where(AtlasProjectRecord.sigil_name == owner)
            )
            rows = await session.scalars(
                select(AtlasProjectRecord)
                .where(AtlasProjectRecord.sigil_name == owner)
                .order_by(AtlasProjectRecord.updated_at.desc(), AtlasProjectRecord.id.desc())
                .limit(limit)
                .offset(offset)
            )
            return AtlasCatalogue(
                projects=[summarize_project(_document(row)) for row in rows],
                total=total or 0,
                limit=limit,
                offset=offset,
            )

    async def get_project(self, owner: str, project_id: UUID) -> AtlasProject:
        from lychd.db.models.atlas import AtlasProjectRecord

        async with self._session_factory() as session:
            row = await session.scalar(
                select(AtlasProjectRecord).where(
                    AtlasProjectRecord.id == project_id, AtlasProjectRecord.sigil_name == owner
                )
            )
            if row is None:
                message = "Atlas Project is unavailable."
                raise AtlasNotFoundError(message)
            return _document(row)

    async def create_project(self, owner: str, data: AtlasCreate) -> AtlasProject:
        from lychd.db.models.atlas import AtlasProjectRecord

        digest = payload_digest(data)
        project = new_project(data, now=datetime.now(UTC))
        async with self._session_factory() as session, session.begin():
            await session.execute(
                insert(AtlasProjectRecord)
                .values(
                    id=project.id,
                    sigil_name=owner,
                    version=project.version,
                    document=project.model_dump(mode="json"),
                    creation_digest=digest,
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                )
                .on_conflict_do_nothing(index_elements=[AtlasProjectRecord.id])
            )
            row = await self._owned_row(session, owner, data.id)
            if row.creation_digest != digest:
                message = "Atlas Project identity was already used for a different creation payload."
                raise AtlasConflictError(message)
            return _document(row)

    async def replay_change(self, owner: str, project_id: UUID, data: AtlasMutation) -> AtlasProject | None:
        """Read a committed replay before reference admission, without claiming a new request."""
        async with self._session_factory() as session, session.begin():
            row = await self._owned_row(session, owner, project_id)
            if await self._receipt_matches(session, project_id, data):
                return _document(row)
            return None

    async def change_project(self, owner: str, project_id: UUID, data: AtlasMutation) -> AtlasProject:
        from lychd.db.models.atlas import AtlasRequestRecord

        try:
            async with self._session_factory() as session, session.begin():
                row = await self._owned_row(session, owner, project_id)
                project = _document(row)
                if await self._receipt_matches(session, project_id, data):
                    return project
                successor = apply_change(project, data, author=owner, now=datetime.now(UTC), record_id=uuid4())
                session.add(
                    AtlasRequestRecord(id=data.request_id, project_id=project_id, payload_digest=payload_digest(data))
                )
                row.document = successor.model_dump(mode="json")
                row.version = successor.version
                row.updated_at = successor.updated_at
                await session.flush()
                return successor
        except IntegrityError as error:
            # A request UUID may race across different locked Projects. The
            # transaction context rolls back both the losing document and receipt.
            message = "Atlas request identity conflicts with a retained request. Reload and reconcile the draft."
            raise AtlasConflictError(message) from error

    async def projects_for_reference(self, owner: str, kind: AtlasReferenceKind, target_id: str) -> list[AtlasSummary]:
        from lychd.db.models.atlas import AtlasProjectRecord

        async with self._session_factory() as session:
            rows = await session.scalars(
                select(AtlasProjectRecord)
                .where(
                    AtlasProjectRecord.sigil_name == owner,
                    AtlasProjectRecord.document.contains({"references": [{"kind": kind, "target_id": target_id}]}),
                )
                .order_by(AtlasProjectRecord.updated_at.desc(), AtlasProjectRecord.id.desc())
            )
            return [summarize_project(_document(row)) for row in rows]
