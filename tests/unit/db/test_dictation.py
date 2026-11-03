"""Offline adapter and schema evidence; this does not qualify PostgreSQL concurrency."""

from __future__ import annotations

import importlib.util
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self, cast
from uuid import UUID

import pytest
from sqlalchemy import CheckConstraint, MetaData, PrimaryKeyConstraint, Table, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.db.dictation import DbDictationStore, DictationStoreError
from lychd.db.models.dictation import BridgeDictationAttempt
from lychd.domain.dictation import DictationAttemptIdentity, DictationResult
from lychd.domain.dictation_store import DictationEntry, StoredDictationContent

NOW = datetime(2026, 11, 3, tzinfo=UTC)
ID = UUID(int=(int(NOW.timestamp() * 1000) << 80) | (7 << 76) | (2 << 62) | 1)
FIELDS = (
    "owner",
    "attempt_id",
    "created_at",
    "expires_at",
    "audio_expires_at",
    "tombstone_until",
    "content_json",
    "raw_audio",
    "raw_size",
)


def entry() -> DictationEntry:
    identity = DictationAttemptIdentity(
        owner="alice",
        attempt_id=ID,
        source_digest="sha256:" + "a" * 64,
        profile_digest="sha256:" + "b" * 64,
        language="en",
    )
    return DictationEntry(
        attempt_id=ID,
        created_at=NOW,
        expires_at=NOW + timedelta(days=1),
        audio_expires_at=NOW + timedelta(seconds=1),
        tombstone_until=NOW + timedelta(seconds=300),
        raw_present=True,
        raw_audio=b"x" * 46,
        content=StoredDictationContent(
            identity=identity,
            result=DictationResult(
                attempt_id=ID,
                status="unknown",
                source_digest=identity.source_digest,
                profile_digest=identity.profile_digest,
                language="en",
                reason="outcome_unknown",
            ),
        ),
    )


@dataclass
class Factory:
    rows: dict[tuple[str, UUID], dict[str, Any]] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)
    params: list[dict[str, Any] | None] = field(default_factory=list)
    fail_commit: bool = False
    fail_flush: bool = False
    dialect: str = "postgresql"
    hide_parameters: bool = True
    now: datetime = NOW

    def __call__(self) -> Session:
        return Session(self)


class Session:
    def __init__(self, factory: Factory) -> None:
        self.factory = factory
        self.rows = {key: BridgeDictationAttempt(**deepcopy(row)) for key, row in factory.rows.items()}

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        self.factory.events.append("close")

    def get_bind(self) -> Any:
        return SimpleNamespace(
            dialect=SimpleNamespace(name=self.factory.dialect), hide_parameters=self.factory.hide_parameters
        )

    @asynccontextmanager
    async def begin(self) -> AsyncGenerator[None]:
        yield
        self.factory.events.append("commit")
        self.factory.rows = {key: {name: getattr(row, name) for name in FIELDS} for key, row in self.rows.items()}
        if self.factory.fail_commit:
            msg = "PRIVATE DRIVER SQL PARAMETERS"
            raise RuntimeError(msg)

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> None:
        self.factory.events.append(str(statement))
        self.factory.params.append(params)

    async def scalars(self, statement: Any) -> Any:
        self.factory.events.append("read")
        params = statement.compile().params
        owner = params["owner_1"]
        assert params["param_1"] == 1001
        rows = [row for row in self.rows.values() if row.owner == owner]
        return SimpleNamespace(all=lambda: rows)

    def add(self, row: BridgeDictationAttempt) -> None:
        self.rows[(row.owner, row.attempt_id)] = row

    async def delete(self, row: BridgeDictationAttempt) -> None:
        del self.rows[(row.owner, row.attempt_id)]

    async def flush(self) -> None:
        self.factory.events.append("flush")
        if self.factory.fail_flush:
            msg = "PRIVATE DRIVER SQL PARAMETERS"
            raise RuntimeError(msg)


def store(factory: Factory) -> DbDictationStore:
    return DbDictationStore(cast("async_sessionmaker[AsyncSession]", factory), now=lambda: factory.now)


@pytest.mark.asyncio
async def test_adapter_commits_before_return_and_fresh_instance_reconstructs_private_result() -> None:
    factory = Factory()
    original = entry()
    async with store(factory)._records("alice") as rows:  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
        rows[ID] = original
    assert factory.events[-3:] == ["flush", "commit", "close"]
    assert original.content is not None
    assert await store(factory).get_result("alice", ID, NOW) == original.content.result
    assert await store(factory).get_result("bob", ID, NOW) is None
    sql = "SELECT pg_advisory_xact_lock(CAST(:lock_id AS BIGINT))"
    assert factory.events.index(sql) < factory.events.index("read")
    assert "alice" not in sql
    assert factory.params[3] is not None
    assert isinstance(factory.params[3]["lock_id"], int)
    assert "raw_audio" not in str(select_attempt())


def select_attempt() -> Any:
    from sqlalchemy import select

    return select(BridgeDictationAttempt)


@pytest.mark.asyncio
async def test_durable_read_purges_raw_and_delete_removes_private_content() -> None:
    factory = Factory()
    async with store(factory)._records("alice") as rows:  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
        rows[ID] = entry()
    factory.now = NOW + timedelta(seconds=2)
    assert await store(factory).get_result("alice", ID, factory.now) is not None
    assert factory.rows[("alice", ID)]["raw_audio"] is None
    assert await store(factory).delete("alice", ID, NOW + timedelta(seconds=2))
    assert factory.rows[("alice", ID)]["content_json"] is None
    assert factory.rows[("alice", ID)]["raw_size"] == 0
    factory.now = NOW + timedelta(seconds=301)
    assert await store(factory).get_result("alice", ID, factory.now) is None
    assert not factory.rows


@pytest.mark.asyncio
async def test_commit_loss_releases_no_claim_and_read_reconstructs_unknown_without_reexecution() -> None:
    factory = Factory(fail_commit=True)
    with pytest.raises(DictationStoreError, match=r"^dictation_commit_unknown$") as caught:
        async with store(factory)._records("alice") as rows:  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
            rows[ID] = entry()
    assert "PRIVATE" not in str(caught.value)
    assert caught.value.__suppress_context__
    factory.fail_commit = False
    recovered = await store(factory).get_result("alice", ID, NOW)
    assert recovered is not None
    assert recovered.status == "unknown"


@pytest.mark.asyncio
async def test_flush_failure_and_wrong_dialect_fail_closed() -> None:
    factory = Factory(fail_flush=True)
    with pytest.raises(DictationStoreError, match=r"^dictation_storage_failure$"):
        async with store(factory)._records("alice") as rows:  # pyright: ignore[reportPrivateUsage] - inspect the custody boundary under test
            rows[ID] = entry()
    assert not factory.rows
    other = Factory(dialect="sqlite")
    with pytest.raises(DictationStoreError, match=r"^dictation_postgresql_required$"):
        await store(other).get_result("alice", ID, NOW)
    assert "read" not in other.events


@dataclass
class Operations:
    metadata: MetaData = field(default_factory=MetaData)
    tables: list[Table] = field(default_factory=list)
    sql: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)

    @staticmethod
    def f(name: str) -> str:
        return name

    def execute(self, statement: Any) -> None:
        self.sql.append(" ".join(str(statement).split()))

    def create_table(self, name: str, *items: Any) -> None:
        self.tables.append(Table(name, self.metadata, *items))

    def drop_table(self, name: str) -> None:
        self.dropped.append(name)


def migration() -> Any:
    path = Path(__file__).resolve().parents[3] / "src/lychd/db/migrations/versions/0025_bridge_dictation.py"
    spec = importlib.util.spec_from_file_location("dictation_migration_candidate", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def columns(table: Table) -> dict[str, tuple[str, bool | None, bool]]:
    return {
        c.name: (str(c.type.compile(dialect=postgresql.dialect())), c.nullable, c.primary_key) for c in table.columns
    }


def constraints(table: Table) -> set[tuple[str, str, object]]:
    result: set[tuple[str, str, object]] = set()
    for c in table.constraints:
        assert c.name is not None
        if isinstance(c, CheckConstraint):
            result.add(("check", str(c.name), " ".join(str(c.sqltext).split())))
        elif isinstance(c, (PrimaryKeyConstraint, UniqueConstraint)):
            result.add((type(c).__name__, str(c.name), tuple(column.name for column in c.columns)))
        else:
            raise TypeError(type(c))
    return result


def test_migration_matches_model_and_downgrade_is_locked_and_non_destructive(monkeypatch: pytest.MonkeyPatch) -> None:
    module, ops = migration(), Operations()
    monkeypatch.setattr(module, "op", ops)
    module.upgrade()
    assert module.revision == "0025"
    assert module.down_revision == "0024"
    model = BridgeDictationAttempt.__table__
    assert isinstance(model, Table)
    assert columns(ops.tables[0]) == columns(model)
    assert constraints(ops.tables[0]) == constraints(model)
    assert not model.foreign_keys
    ops.sql.clear()
    module.downgrade()
    assert ops.sql[2] == "LOCK TABLE bridge_dictation_attempt IN ACCESS EXCLUSIVE MODE"
    assert "IF EXISTS (SELECT 1 FROM bridge_dictation_attempt LIMIT 1)" in ops.sql[3]
    assert "RAISE EXCEPTION" in ops.sql[3]
    assert ops.dropped == ["bridge_dictation_attempt"]


@pytest.mark.asyncio
async def test_parameter_logging_must_be_disabled_before_private_sql() -> None:
    factory = Factory(hide_parameters=False)
    with pytest.raises(DictationStoreError, match=r"^dictation_private_parameters_required$"):
        await store(factory).get_result("alice", ID, NOW)
    assert "read" not in factory.events


@pytest.mark.asyncio
@pytest.mark.parametrize("replay", [False, True])
async def test_claim_refuses_when_commit_crosses_custody_deadline(
    monkeypatch: pytest.MonkeyPatch,
    *,
    replay: bool,
) -> None:
    from lychd.domain.dictation import DictationError
    from tests.unit.domain.test_dictation_store import identity, profile, result, wav

    factory = Factory()
    pinned = profile(retention_seconds=1)
    owned = identity(pinned, now=NOW)
    bounded = DbDictationStore(cast("async_sessionmaker[AsyncSession]", factory), now=lambda: factory.now)
    if replay:
        await bounded.claim(owned, wav(), NOW, pinned)
        await bounded.settle(owned, result(owned), NOW)
    close = Session.__aexit__

    async def cross_deadline(self: Session, *args: object) -> None:
        await close(self, *args)
        self.factory.now = NOW + timedelta(seconds=1)

    monkeypatch.setattr(Session, "__aexit__", cross_deadline)
    with pytest.raises(DictationError, match="expired"):
        await bounded.claim(owned, wav(), NOW, pinned)
    assert factory.rows  # Expired response does not undo the acknowledged claim.
