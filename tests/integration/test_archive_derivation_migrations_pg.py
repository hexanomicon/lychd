"""0013 atomic DDL, schema parity and retained derivation downgrade refusal."""

from __future__ import annotations

from typing import Any

import pytest
from alembic import command, op
from sqlalchemy.exc import DBAPIError

from lychd.db.models.archive_derivation import ArchiveEmbeddingGeneration, ArchiveNoteEmbedding
from tests.integration import test_archive_migrations_pg as migration

pytestmark = [pytest.mark.integration, pytest.mark.container]
pg_url = migration.pg_url


def test_derivation_upgrade_atomicity_and_empty_downgrade(pg_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    command.upgrade(migration.config(pg_url), "0012")
    original = op.create_table

    def fail_late(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "archive_note_embedding":
            msg = "injected derivation DDL failure"
            raise RuntimeError(msg)
        return original(name, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(op, "create_table", fail_late)
        with pytest.raises(RuntimeError, match="injected derivation"):
            command.upgrade(migration.config(pg_url), "head")
    assert migration.run(
        pg_url, "SELECT version_num,to_regclass('public.archive_embedding_generation')::text FROM lychd_db_version"
    ) == [("0012", None)]
    command.upgrade(migration.config(pg_url), "head")
    for model in (ArchiveEmbeddingGeneration, ArchiveNoteEmbedding):
        columns = migration.run(
            pg_url,
            "SELECT column_name,is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name=:table",
            {"table": model.__tablename__},
        )
        assert dict(columns) == {column.name: "YES" if column.nullable else "NO" for column in model.__table__.columns}
    assert migration.run(
        pg_url,
        "SELECT format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid='archive_note_embedding'::regclass AND attname='vector'",
    ) == [("vector(1024)",)]
    command.downgrade(migration.config(pg_url), "0012")
    assert migration.run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0012",)]


def test_retired_generation_is_retained_history(pg_url: str) -> None:
    command.upgrade(migration.config(pg_url), "head")
    migration.run(
        pg_url,
        "INSERT INTO archive_namespace(id,owner_subject,policy_revision,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000001','owner','one',now(),now())",
    )
    migration.run(
        pg_url,
        "INSERT INTO archive_embedding_generation(id,namespace_id,manifest_digest,manifest,state,version,retired_at,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001',repeat('a',64),'{}','retired',2,now(),now(),now())",
    )
    with pytest.raises(DBAPIError, match="Retained Archive derivation history prevents downgrade"):
        command.downgrade(migration.config(pg_url), "0012")
    assert migration.run(pg_url, "SELECT version_num FROM lychd_db_version") == [("0017",)]
    assert migration.run(pg_url, "SELECT state FROM archive_embedding_generation") == [("retired",)]
