"""Source-only candidate tests: adapter semantics and migration shape, without a DB.

The transactional fake models retained records and injected failures only. These
checks cannot prove PostgreSQL locking, races, actual timeouts, role admission,
physical rollback, or the retained-row downgrade guard's execution.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Self, cast
from uuid import UUID

import pytest
from sqlalchemy import CheckConstraint, MetaData, PrimaryKeyConstraint, Table, UniqueConstraint
from sqlalchemy.dialects import postgresql

from lychd.compositions.blockworld.companion_memory import MAX_RECIPES, CommandRecipe, recipe_key
from lychd.db.companion_memory import DbCompanionRecipeStore, RecipeStoreError
from lychd.db.models.companion_memory import CompanionRecipe

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_NAMESPACE = "a" * 64
_OTHER_NAMESPACE = "b" * 64
_REQUEST = "00000000-0000-4000-8000-000000000001"
_RUN = "00000000-0000-4000-8000-000000000002"
_OTHER_RUN = "00000000-0000-4000-8000-000000000003"
_DRIVER_DETAIL = "injected driver detail must never appear in the public error"
_TIMEOUTS = ["SET LOCAL statement_timeout = '5s'", "SET LOCAL lock_timeout = '2s'"]
_Row = dict[str, Any]


def _recipe(phrase: str = "come along", command: str = "follow me") -> CommandRecipe:
    return CommandRecipe(
        language="en",
        phrase=phrase,
        command=command,
        learned_request_id=_REQUEST,
        learned_run_id=_RUN,
    )


def _document_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )


def _record(recipe: CommandRecipe, namespace: str = _NAMESPACE) -> _Row:
    payload = _document_bytes(recipe.model_dump(mode="json"))
    return {
        "namespace": namespace,
        "key": recipe_key(recipe.language, recipe.phrase),
        "language": recipe.language,
        "phrase": recipe.phrase,
        "recipe_bytes": payload,
        "recipe_digest": hashlib.sha256(payload).hexdigest(),
        "learned_request_id": UUID(recipe.learned_request_id),
        "learned_run_id": UUID(recipe.learned_run_id),
    }


@dataclass
class _Factory:
    rows: dict[tuple[str, str], _Row] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)
    statements: list[tuple[str, dict[str, Any] | None]] = field(default_factory=list)
    sessions: int = 0
    commits: int = 0
    flushes: int = 0
    dialect: str = "postgresql"
    fail_select: bool = False
    fail_flush: bool = False
    fail_commit: bool = False
    retain_before_commit_error: bool = False
    fail_close: bool = False
    # Integrity tests may deliberately inject a returned row inconsistent with
    # its SELECT predicate. This is an untrusted-result seam, not SQL behavior.
    selected_override: list[_Row] | None = None

    def __call__(self) -> _Session:
        self.sessions += 1
        return _Session(self)

    def seed(self, recipe: CommandRecipe, namespace: str = _NAMESPACE) -> None:
        row = _record(recipe, namespace)
        self.rows[(namespace, row["key"])] = row


class _Transaction:
    def __init__(self, session: _Session) -> None:
        self.session = session

    async def __aenter__(self) -> Self:
        self.session.factory.events.append("begin")
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        factory = self.session.factory
        if exc_type is not None:
            factory.events.append("rollback")
            return False
        factory.commits += 1
        factory.events.append("commit")
        if not factory.fail_commit or factory.retain_before_commit_error:
            factory.rows = {key: value.copy() for key, value in self.session.working.items()}
        if factory.fail_commit:
            raise RuntimeError(_DRIVER_DETAIL)
        return False


class _Session:
    def __init__(self, factory: _Factory) -> None:
        self.factory = factory
        self.working = {key: value.copy() for key, value in factory.rows.items()}

    async def __aenter__(self) -> Self:
        self.factory.events.append("open")
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        self.factory.events.append("close")
        if self.factory.fail_close:
            raise RuntimeError(_DRIVER_DETAIL)
        return False

    def get_bind(self) -> Any:
        return SimpleNamespace(dialect=SimpleNamespace(name=self.factory.dialect))

    def begin(self) -> _Transaction:
        return _Transaction(self)

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> None:
        rendered = str(statement)
        self.factory.events.append(rendered)
        self.factory.statements.append((rendered, params))

    async def scalars(self, statement: Any) -> Any:
        self.factory.events.append("select")
        if self.factory.fail_select:
            raise RuntimeError(_DRIVER_DETAIL)
        parameters = statement.compile().params
        namespace = parameters["namespace_1"]
        limit = parameters["param_1"]
        assert limit == MAX_RECIPES + 1
        rows = self.factory.selected_override
        if rows is None:
            rows = [value for value in self.working.values() if value["namespace"] == namespace]
        selected = [CompanionRecipe(**row.copy()) for row in sorted(rows, key=lambda row: row["key"])[:limit]]
        return SimpleNamespace(all=lambda: selected)

    def add(self, row: CompanionRecipe) -> None:
        self.factory.events.append("add")
        values = {
            name: getattr(row, name)
            for name in (
                "namespace",
                "key",
                "language",
                "phrase",
                "recipe_bytes",
                "recipe_digest",
                "learned_request_id",
                "learned_run_id",
            )
        }
        self.working[(row.namespace, row.key)] = values

    async def delete(self, row: CompanionRecipe) -> None:
        self.factory.events.append("delete")
        del self.working[(row.namespace, row.key)]

    async def flush(self) -> None:
        self.factory.events.append("flush")
        self.factory.flushes += 1
        if self.factory.fail_flush:
            raise RuntimeError(_DRIVER_DETAIL)


def _store(factory: _Factory, namespace: str = _NAMESPACE) -> DbCompanionRecipeStore:
    return DbCompanionRecipeStore(cast("async_sessionmaker[AsyncSession]", factory), namespace)


@pytest.mark.asyncio
async def test_retained_records_reconstruct_across_store_instances_and_namespace() -> None:
    factory = _Factory()
    original = _recipe()
    await _store(factory).remember(original)
    recalled = await _store(factory).find("en", " COME ALONG ")
    assert recalled == original
    assert recalled is not original
    assert await _store(factory, _OTHER_NAMESPACE).find("en", original.phrase) is None
    assert factory.events[-2:] == ["commit", "close"]


@pytest.mark.asyncio
async def test_identical_replay_is_idempotent_and_changed_recipe_requires_forget() -> None:
    factory = _Factory()
    await _store(factory).remember(_recipe())
    await _store(factory).remember(_recipe())
    assert len(factory.rows) == 1
    assert factory.flushes == 1
    before = {key: row.copy() for key, row in factory.rows.items()}
    with pytest.raises(ValueError, match="Forget the previous recipe"):
        await _store(factory).remember(_recipe(command="idle"))
    assert factory.rows == before
    assert await _store(factory).forget("en", "come along") is True
    assert await _store(factory).forget("en", "come along") is False
    assert await _store(factory).find("en", "come along") is None
    await _store(factory).remember(_recipe(command="idle"))
    assert await _store(factory).find("en", "come along") == _recipe(command="idle")


@pytest.mark.asyncio
async def test_provenance_and_confirmation_changes_are_conflicts() -> None:
    factory = _Factory()
    original = _recipe()
    await _store(factory).remember(original)
    for changed in (
        original.model_copy(update={"learned_run_id": _OTHER_RUN}),
        original.model_copy(update={"skip_confirmation": True}),
    ):
        with pytest.raises(ValueError, match="Forget the previous recipe"):
            await _store(factory).remember(changed)
    assert await _store(factory).find("en", original.phrase) == original


@pytest.mark.asyncio
async def test_capacity_is_per_namespace_and_identical_replay_works_at_capacity() -> None:
    factory = _Factory()
    for index in range(MAX_RECIPES):
        factory.seed(_recipe(f"alias {index}", "state"))
    await _store(factory).remember(_recipe("alias 0", "state"))
    with pytest.raises(ValueError, match="Recipe capacity reached"):
        await _store(factory).remember(_recipe("one more", "state"))
    assert len(factory.rows) == MAX_RECIPES
    assert factory.flushes == 0
    await _store(factory, _OTHER_NAMESPACE).remember(_recipe("one more", "state"))
    assert len(factory.rows) == MAX_RECIPES + 1


@pytest.mark.asyncio
async def test_excess_retained_capacity_is_an_integrity_failure_not_a_miss() -> None:
    factory = _Factory()
    for index in range(MAX_RECIPES + 1):
        factory.seed(_recipe(f"alias {index}", "state"))
    with pytest.raises(RecipeStoreError, match=r"^recipe_integrity$"):
        await _store(factory).find("en", "absent alias")


def _tamper(row: _Row, change: str) -> _Row:  # noqa: C901, PLR0912 - independent corruptions retain explicit mutation oracles
    row = row.copy()
    if change == "namespace":
        row["namespace"] = _OTHER_NAMESPACE
    elif change == "key":
        row["key"] = "0" * 64
    elif change == "digest":
        row["recipe_digest"] = "0" * 64
    elif change == "language":
        row["language"] = "sk"
    elif change == "phrase":
        row["phrase"] = "different phrase"
    elif change == "provenance":
        row["learned_run_id"] = UUID(_OTHER_RUN)
    elif change == "bytes_type":
        row["recipe_bytes"] = row["recipe_bytes"].decode("utf-8")
    elif change == "oversize":
        row["recipe_bytes"] = b"x" * 4097
    else:
        document = json.loads(row["recipe_bytes"])
        if change == "noncanonical":
            row["recipe_bytes"] = json.dumps(document, indent=2).encode("utf-8")
        elif change == "malformed":
            row["recipe_bytes"] = b"not a JSON document"
        elif change == "extra_field":
            document["authority"] = "console"
            row["recipe_bytes"] = _document_bytes(document)
        elif change == "unsupported_command":
            document["command"] = "/kill @a"
            row["recipe_bytes"] = _document_bytes(document)
        elif change == "document_mismatch":
            document["phrase"] = "another alias"
            row["recipe_bytes"] = _document_bytes(document)
        else:
            raise AssertionError(change)
        row["recipe_digest"] = hashlib.sha256(row["recipe_bytes"]).hexdigest()
    return row


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        "namespace",
        "key",
        "digest",
        "language",
        "phrase",
        "provenance",
        "bytes_type",
        "oversize",
        "noncanonical",
        "malformed",
        "extra_field",
        "unsupported_command",
        "document_mismatch",
    ],
)
async def test_every_returned_record_is_revalidated_and_corruption_is_never_a_miss(change: str) -> None:
    factory = _Factory(selected_override=[_tamper(_record(_recipe()), change)])
    with pytest.raises(RecipeStoreError, match=r"^recipe_integrity$"):
        await _store(factory).find("en", "absent alias")
    assert factory.sessions == 1
    assert factory.commits == 0
    assert "rollback" in factory.events


@pytest.mark.asyncio
async def test_invalid_model_copy_is_revalidated_before_database_access() -> None:
    factory = _Factory()
    invalid = _recipe().model_copy(update={"phrase": "COME ALONG"})
    with pytest.raises(ValueError, match="normalized exact key"):
        await _store(factory).remember(invalid)
    assert factory.sessions == 0


@pytest.mark.asyncio
async def test_writer_sets_local_bounds_and_locks_before_capacity_read() -> None:
    factory = _Factory()
    await _store(factory).remember(_recipe())
    statements = [sql for sql, _ in factory.statements]
    assert statements[:2] == _TIMEOUTS
    assert statements[2] == "SET TRANSACTION ISOLATION LEVEL READ COMMITTED"
    lock_sql = "SELECT pg_advisory_xact_lock(CAST(:lock_id AS BIGINT))"
    assert statements[3:] == [lock_sql]
    lock_id = factory.statements[3][1]
    assert lock_id is not None
    assert type(lock_id["lock_id"]) is int
    assert -(2**63) <= lock_id["lock_id"] < 2**63
    assert factory.events.index(lock_sql) < factory.events.index("select")
    assert factory.events.index("select") < factory.events.index("flush") < factory.events.index("commit")
    factory.statements.clear()
    await _store(factory).find("en", "come along")
    assert [sql for sql, _ in factory.statements] == [*_TIMEOUTS, statements[2]]


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["find", "remember", "forget"])
async def test_storage_failure_is_fixed_and_never_retried(operation: str) -> None:
    factory = _Factory(fail_select=True)
    store = _store(factory)
    action = (
        store.remember(_recipe())
        if operation == "remember"
        else store.forget("en", "come along")
        if operation == "forget"
        else store.find("en", "come along")
    )
    with pytest.raises(RecipeStoreError, match=r"^recipe_storage_failure$") as caught:
        await action
    assert factory.sessions == 1
    assert factory.commits == 0
    assert factory.events.count("select") == 1
    assert caught.value.__suppress_context__
    assert _DRIVER_DETAIL not in str(caught.value)


@pytest.mark.asyncio
async def test_flush_failure_rolls_back_and_does_not_retry() -> None:
    factory = _Factory(fail_flush=True)
    with pytest.raises(RecipeStoreError, match=r"^recipe_storage_failure$"):
        await _store(factory).remember(_recipe())
    assert factory.rows == {}
    assert factory.sessions == factory.flushes == 1
    assert factory.commits == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("retained", [False, True])
@pytest.mark.parametrize("operation", ["remember", "forget"])
async def test_commit_failure_has_unknown_outcome_and_requires_explicit_read(*, retained: bool, operation: str) -> None:
    factory = _Factory(fail_commit=True, retain_before_commit_error=retained)
    if operation == "forget":
        factory.seed(_recipe())
    action = (
        _store(factory).forget("en", "come along") if operation == "forget" else _store(factory).remember(_recipe())
    )
    with pytest.raises(RecipeStoreError, match=r"^recipe_commit_unknown$") as caught:
        await action
    assert factory.sessions == factory.flushes == factory.commits == 1
    assert caught.value.__suppress_context__
    assert _DRIVER_DETAIL not in str(caught.value)
    factory.fail_commit = False
    recovered = await _store(factory).find("en", "come along")
    expected_present = retained if operation == "remember" else not retained
    assert recovered == (_recipe() if expected_present else None)


@pytest.mark.asyncio
async def test_cleanup_failure_after_commit_keeps_unknown_outcome() -> None:
    factory = _Factory(fail_close=True)
    with pytest.raises(RecipeStoreError, match=r"^recipe_commit_unknown$"):
        await _store(factory).remember(_recipe())
    assert len(factory.rows) == 1
    assert factory.sessions == factory.commits == 1


@pytest.mark.parametrize("namespace", ["", "A" * 64, "a" * 63, "a" * 64 + "\n", None])
def test_namespace_requires_exact_lowercase_sha256(namespace: Any) -> None:
    factory = _Factory()
    with pytest.raises(ValueError, match="lowercase SHA256"):
        _store(factory, namespace)
    assert factory.sessions == 0


@pytest.mark.asyncio
async def test_non_postgresql_factory_is_refused_before_transaction() -> None:
    factory = _Factory(dialect="sqlite")
    with pytest.raises(RecipeStoreError, match=r"^recipe_postgresql_required$"):
        await _store(factory).find("en", "come along")
    assert factory.statements == []
    assert "begin" not in factory.events


@dataclass
class _Operations:
    """Capture migration source operations; execute never evaluates SQL."""

    metadata: MetaData = field(default_factory=MetaData)
    tables: list[Table] = field(default_factory=list)
    sql: list[str] = field(default_factory=list)
    events: list[tuple[str, str]] = field(default_factory=list)

    @staticmethod
    def f(name: str) -> str:
        return name

    def execute(self, statement: Any) -> None:
        self.sql.append(str(statement))
        self.events.append(("execute", str(statement)))

    def create_table(self, name: str, *items: Any, **kwargs: Any) -> None:
        self.tables.append(Table(name, self.metadata, *items, **kwargs))
        self.events.append(("create", name))

    def drop_table(self, name: str) -> None:
        self.events.append(("drop", name))


def _migration() -> Any:
    path = Path(__file__).resolve().parents[3] / "src/lychd/db/migrations/versions/0024_companion_recipes.py"
    spec = importlib.util.spec_from_file_location("companion_recipes_migration_candidate", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalize(sql: str) -> str:
    return " ".join(sql.split())


def _column_shapes(table: Table) -> dict[str, tuple[str, bool | None, bool]]:
    return {
        column.name: (
            str(column.type.compile(dialect=postgresql.dialect())),
            column.nullable,
            column.primary_key,
        )
        for column in table.columns
    }


def _constraint_shapes(table: Table) -> set[tuple[str, str, tuple[str, ...] | str]]:
    shapes: set[tuple[str, str, tuple[str, ...] | str]] = set()
    for constraint in table.constraints:
        assert constraint.name is not None
        if isinstance(constraint, CheckConstraint):
            shapes.add(("check", str(constraint.name), _normalize(str(constraint.sqltext))))
        elif isinstance(constraint, PrimaryKeyConstraint):
            shapes.add(("primary", str(constraint.name), tuple(column.name for column in constraint.columns)))
        elif isinstance(constraint, UniqueConstraint):
            shapes.add(("unique", str(constraint.name), tuple(column.name for column in constraint.columns)))
        else:
            msg = f"Unexpected constraint type: {type(constraint).__name__}"
            raise TypeError(msg)
    return shapes


def test_migration_upgrade_matches_orm_postgresql_shape_and_fixed_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    migration = _migration()
    operations = _Operations()
    monkeypatch.setattr(migration, "op", operations)
    migration.upgrade()
    assert migration.revision == "0024"
    assert migration.down_revision == "0023"
    assert migration.branch_labels is None
    assert migration.depends_on is None
    assert operations.sql == _TIMEOUTS
    assert len(operations.tables) == 1
    generated = operations.tables[0]
    model_table = CompanionRecipe.__table__
    assert isinstance(model_table, Table)
    assert generated.name == model_table.name == "companion_recipe"
    assert _column_shapes(generated) == _column_shapes(model_table)
    assert _constraint_shapes(generated) == _constraint_shapes(model_table)
    assert not generated.foreign_keys
    assert operations.events[-1] == ("create", "companion_recipe")


def test_migration_downgrade_locks_and_declares_retained_row_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    migration = _migration()
    operations = _Operations()
    monkeypatch.setattr(migration, "op", operations)
    migration.downgrade()
    assert [_normalize(sql) for sql in operations.sql] == [
        *_TIMEOUTS,
        "LOCK TABLE companion_recipe IN ACCESS EXCLUSIVE MODE",
        (
            "DO $$ BEGIN IF EXISTS (SELECT 1 FROM companion_recipe LIMIT 1) THEN "
            "RAISE EXCEPTION 'Retained companion recipes prevent downgrade'; END IF; END $$;"
        ),
    ]
    assert operations.events[-1] == ("drop", "companion_recipe")
    assert [event for event in operations.events if event[0] == "drop"] == [("drop", "companion_recipe")]
    # Capturing this guard's source does not prove that PostgreSQL refuses a
    # populated table, or that the exclusive lock serializes actual writers.
