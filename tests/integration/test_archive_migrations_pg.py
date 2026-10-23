"""Archive migration DDL atomicity, ORM parity and retained-history downgrade refusal."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

pytest.importorskip("testcontainers", reason="optional disposable PostgreSQL receipt")

from advanced_alchemy.alembic.commands import AlembicCommandConfig
from alembic import command, op
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from lychd.config.constants import DB_MIGRATION_VERSION_TABLE, PATH_MIGRATION_CONFIG
from lychd.db.archive import DbArchiveStore
from lychd.db.models.archive import ArchiveIntake, ArchiveNamespace, ArchiveNote, ArchiveRecall
from lychd.domain.archive import (
    ArchiveAuthorization,
    ArchiveProfile,
    ArchiveService,
    ArchiveSubject,
    NoteProposal,
    text_digest,
)

pytestmark = [pytest.mark.integration, pytest.mark.container]


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    with PostgresContainer("pgvector/pgvector:pg18-trixie", driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


def config(url: str) -> AlembicCommandConfig:
    return AlembicCommandConfig(
        engine=create_async_engine(url),
        version_table_name=DB_MIGRATION_VERSION_TABLE,
        file_=PATH_MIGRATION_CONFIG,
        render_as_batch=False,
    )


async def execute(url: str, statement: str, parameters: dict[str, Any] | None = None) -> list[tuple[Any, ...]]:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            result = await connection.execute(text(statement), parameters or {})
            return list(result.tuples()) if result.returns_rows else []
    finally:
        await engine.dispose()


def run(url: str, statement: str, parameters: dict[str, Any] | None = None) -> list[tuple[Any, ...]]:
    return asyncio.run(execute(url, statement, parameters))


def test_archive_migration_is_atomic_and_empty_cycle_matches_orm(pg_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    command.upgrade(config(pg_url), "0011")
    create_table = op.create_table

    def fail_late(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "archive_recall":
            msg = "injected late Archive DDL failure"
            raise RuntimeError(msg)
        return create_table(name, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(op, "create_table", fail_late)
        with pytest.raises(RuntimeError, match="injected late"):
            command.upgrade(config(pg_url), "head")
    assert run(pg_url, "SELECT version_num,to_regclass('public.archive_namespace')::text FROM lychd_db_version") == [
        ("0011", None)
    ]
    command.upgrade(config(pg_url), "head")
    assert run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0017",)]
    for model in (ArchiveNamespace, ArchiveNote, ArchiveIntake, ArchiveRecall):
        columns = run(
            pg_url,
            "SELECT column_name,is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name=:table",
            {"table": model.__tablename__},
        )
        assert dict(columns) == {column.name: "YES" if column.nullable else "NO" for column in model.__table__.columns}
    assert run(
        pg_url,
        "SELECT is_generated FROM information_schema.columns WHERE table_name='archive_note' AND column_name='search_vector'",
    ) == [("ALWAYS",)]
    assert run(
        pg_url, "SELECT indexdef LIKE '%USING gin%' FROM pg_indexes WHERE indexname='ix_archive_note_search'"
    ) == [(True,)]
    command.downgrade(config(pg_url), "0011")
    assert run(pg_url, "SELECT version_num,to_regclass('public.archive_namespace')::text FROM lychd_db_version") == [
        ("0011", None)
    ]


class Authority:
    def __init__(self, profile: ArchiveProfile) -> None:
        self.profile = profile

    def authorize(self, request: ArchiveAuthorization) -> bool:
        return request.namespace_id == self.profile.namespace_id and request.subject == self.profile.owner_subject


async def retain_note(url: str) -> str:
    engine = create_async_engine(url)
    subject = ArchiveSubject(identity="migration-fixture-operator")
    profile = ArchiveProfile(namespace_id=uuid4(), owner_subject=subject, policy_revision="public.1")
    try:
        archive = ArchiveService(
            profile=profile,
            store=DbArchiveStore(async_sessionmaker(engine, expire_on_commit=False)),
            authorizer=Authority(profile),
        )
        proposal = NoteProposal(
            namespace_id=profile.namespace_id,
            request_id=uuid4(),
            source_key="fixture",
            source_revision="1",
            source_digest=text_digest("retained public note"),
            text="retained public note",
            producer="operator",
            observed_at=datetime.now(UTC),
        )
        record = await archive.admit(subject, proposal, purpose="retain-fixture")
        return str(record.reference.record_id)
    finally:
        await engine.dispose()


def test_archive_downgrade_retains_history(pg_url: str) -> None:
    command.upgrade(config(pg_url), "head")
    record_id = asyncio.run(retain_note(pg_url))
    with pytest.raises(DBAPIError, match="Archive history requires explicit retirement"):
        command.downgrade(config(pg_url), "0011")
    assert run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0017",)]
    assert run(pg_url, "SELECT content,lifecycle FROM archive_note WHERE id=CAST(:id AS uuid)", {"id": record_id}) == [
        ("retained public note", "candidate")
    ]
    assert run(pg_url, "SELECT count(*) FROM archive_intake") == [(1,)]
