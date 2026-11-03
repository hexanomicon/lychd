"""Offline transaction/schema tests; real PostgreSQL concurrency remains separate."""

from __future__ import annotations

import importlib.util
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self, cast
from uuid import UUID

import pytest
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lychd.db.dictation_lexicon import DbDictationLexiconStore, DictationLexiconStoreError
from lychd.db.models.dictation_lexicon import BridgeDictationLexiconRule
from lychd.domain.dictation_lexicon import DictationLexiconError
from tests.unit.db.test_dictation import Operations, columns, constraints
from tests.unit.domain.test_dictation_lexicon import NOW, approval

FIELDS = ("id", "owner", "language", "heard", "replacement", "created_at", "expires_at")


@dataclass
class Factory:
    rows: dict[UUID, dict[str, Any]] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)
    hide_parameters: bool = True
    fail_commit: bool = False
    now: datetime = NOW
    after_read: datetime | None = None
    after_commit: datetime | None = None

    def __call__(self) -> Session:
        return Session(self)


class Session:
    def __init__(self, factory: Factory) -> None:
        self.factory = factory
        self.rows = {key: BridgeDictationLexiconRule(**deepcopy(row)) for key, row in factory.rows.items()}

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        self.factory.events.append("close")

    def get_bind(self) -> Any:
        return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"), hide_parameters=self.factory.hide_parameters)

    @asynccontextmanager
    async def begin(self) -> AsyncGenerator[None]:
        yield
        self.factory.events.append("commit")
        self.factory.rows = {key: {name: getattr(row, name) for name in FIELDS} for key, row in self.rows.items()}
        if self.factory.after_commit is not None:
            self.factory.now = self.factory.after_commit
        if self.factory.fail_commit:
            msg = "PRIVATE DRIVER DIAGNOSTIC"
            raise RuntimeError(msg)

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> None:
        self.factory.events.append(str(statement))
        if "pg_advisory" in str(statement):
            assert params is not None
            assert isinstance(params["lock_id"], int)

    async def scalars(self, statement: Any) -> Any:
        self.factory.events.append("read")
        if self.factory.after_read is not None:
            self.factory.now = self.factory.after_read
        params = statement.compile().params
        assert params["param_1"] == 129
        return SimpleNamespace(all=lambda: [row for row in self.rows.values() if row.owner == params["owner_1"]])

    async def delete(self, row: BridgeDictationLexiconRule) -> None:
        del self.rows[row.id]

    def add(self, row: BridgeDictationLexiconRule) -> None:
        self.rows[row.id] = row

    async def flush(self) -> None:
        self.factory.events.append("flush")


def store(factory: Factory) -> DbDictationLexiconStore:
    return DbDictationLexiconStore(cast("async_sessionmaker[AsyncSession]", factory), now=lambda: factory.now)


@pytest.mark.asyncio
async def test_lock_precedes_read_and_commit_precedes_return_reconstruct_and_owner_delete() -> None:
    factory = Factory()
    first = await store(factory).approve("alice", approval(), NOW)
    assert factory.events.index("SELECT pg_advisory_xact_lock(CAST(:lock_id AS BIGINT))") < factory.events.index("read")
    assert factory.events[-2:] == ["commit", "close"]
    assert await store(factory).approve("alice", approval(), NOW) == first
    await store(factory).delete("bob", first.id, NOW)
    assert await store(factory).list_rules("alice", NOW) == (first,)
    await store(factory).delete("alice", first.id, NOW)
    assert await store(factory).list_rules("alice", NOW) == ()


@pytest.mark.asyncio
async def test_parameters_required_and_uncertain_commit_has_sanitized_recovery() -> None:
    unsafe = Factory(hide_parameters=False)
    with pytest.raises(DictationLexiconStoreError, match=r"^dictation_lexicon_private_parameters_required$"):
        await store(unsafe).approve("alice", approval(), NOW)
    assert "read" not in unsafe.events
    uncertain = Factory(fail_commit=True)
    with pytest.raises(DictationLexiconStoreError, match=r"^dictation_lexicon_commit_unknown$") as caught:
        await store(uncertain).approve("alice", approval(), NOW)
    assert "PRIVATE" not in str(caught.value)
    uncertain.fail_commit = False
    retained = await store(uncertain).list_rules("alice", NOW)
    assert len(retained) == 1
    assert await store(uncertain).approve("alice", approval(), NOW) == retained[0]


@pytest.mark.asyncio
async def test_owner_read_erases_expired_approval_before_reapproval() -> None:
    factory = Factory()
    original = await store(factory).approve("alice", approval(), NOW)
    factory.now = original.expires_at
    assert await store(factory).list_rules("alice", original.expires_at) == ()
    assert not factory.rows
    renewed = await store(factory).approve("alice", approval(), original.expires_at)
    assert renewed.id != original.id
    assert renewed.created_at == original.expires_at


def test_migration_model_parity_and_guarded_downgrade(monkeypatch: pytest.MonkeyPatch) -> None:
    path = Path(__file__).resolve().parents[3] / "src/lychd/db/migrations/versions/0026_bridge_dictation_lexicon.py"
    spec = importlib.util.spec_from_file_location("dictation_lexicon_migration", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ops = Operations()
    monkeypatch.setattr(module, "op", ops)
    module.upgrade()
    assert module.revision == "0026"
    assert module.down_revision == "0025"
    model = BridgeDictationLexiconRule.__table__
    assert isinstance(model, Table)
    assert columns(ops.tables[0]) == columns(model)
    assert constraints(ops.tables[0]) == constraints(model)
    assert not model.foreign_keys
    ops.sql.clear()
    module.downgrade()
    assert "ACCESS EXCLUSIVE" in ops.sql[2]
    assert "IF EXISTS" in ops.sql[3]
    assert "RAISE EXCEPTION" in ops.sql[3]


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["list", "approve"])
async def test_expiry_clock_is_sampled_after_owner_read(operation: str) -> None:
    factory = Factory()
    original = await store(factory).approve("alice", approval(), NOW)
    factory.after_read = original.expires_at
    if operation == "list":
        assert await store(factory).list_rules("alice", NOW) == ()
        assert not factory.rows
    else:
        renewed = await store(factory).approve("alice", approval(), NOW)
        assert renewed.id != original.id
        assert renewed.created_at == original.expires_at


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["list", "replay", "fresh"])
async def test_commit_crossing_deadline_never_returns_private_rule(operation: str) -> None:
    factory = Factory()
    bounded = DbDictationLexiconStore(
        cast("async_sessionmaker[AsyncSession]", factory),
        retention_seconds=1,
        now=lambda: factory.now,
    )
    if operation != "fresh":
        await bounded.approve("alice", approval(), NOW)
    factory.after_commit = NOW + timedelta(seconds=1)
    if operation == "list":
        assert await bounded.list_rules("alice", NOW) == ()
    else:
        with pytest.raises(DictationLexiconError, match="unavailable"):
            await bounded.approve("alice", approval(), NOW)
    assert factory.rows  # Commit remains durable; a later purge owns physical cleanup.
