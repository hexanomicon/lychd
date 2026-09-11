"""Runtime authority and bootstrap refusal at their real dependency seams."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr
from saq.queue.postgres_migrations import get_migrations

from lychd.config.settings.server import DatabaseSettings
from lychd.db import bootstrap, engine
from lychd.db.authority import DatabaseAuthorityError, RuntimePostgresQueue, verify_sqlalchemy_connection


@pytest.mark.parametrize("unsafe", [True, None, 0, "false"])
def test_sqlalchemy_rejects_unsafe_or_unproven_authority_and_closes_cursor(unsafe: object) -> None:
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.fetchone.return_value = (unsafe,)
    with pytest.raises(DatabaseAuthorityError):
        verify_sqlalchemy_connection(connection, None)
    cursor.close.assert_called_once()


def test_sqlalchemy_accepts_verified_runtime_authority() -> None:
    connection = MagicMock()
    connection.cursor.return_value.fetchone.return_value = (False,)
    verify_sqlalchemy_connection(connection, None)
    connection.cursor.return_value.close.assert_called_once()


@pytest.mark.parametrize(
    "row",
    [
        (True, True, False, False, False, False, "lychd:database-role:v1:runtime", False, False),
        (True, False, False, False, False, False, None, False, False),
        (True, False, False, False, False, False, "lychd:database-role:v1:runtime", True, False),
    ],
)
def test_bootstrap_preserves_unmarked_or_privileged_existing_role(row: tuple[object, ...]) -> None:
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = row
    with pytest.raises(ValueError, match="preserved unchanged"):
        bootstrap._prepare_role(connection, "lychd_runtime", SecretStr("synthetic"), "runtime")  # pyright: ignore[reportPrivateUsage]
    assert connection.execute.call_count == 1


def test_bootstrap_preserves_runtime_role_with_object_or_schema_authority() -> None:
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = (
        True,
        False,
        False,
        False,
        False,
        False,
        "lychd:database-role:v1:runtime",
        False,
        True,
    )
    with pytest.raises(ValueError, match="preserved unchanged"):
        bootstrap._prepare_role(connection, "lychd_runtime", SecretStr("replacement"), "runtime")  # pyright: ignore[reportPrivateUsage]
    assert connection.execute.call_count == 1


def test_bootstrap_refuses_unrelated_phoenix_owner_before_role_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = ("someone_else", None)
    connect = MagicMock()
    connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr(bootstrap.psycopg, "connect", connect)
    monkeypatch.setattr(bootstrap, "_verify_administrator", MagicMock())
    prepare = MagicMock()
    monkeypatch.setattr(bootstrap, "_prepare_role", prepare)
    with pytest.raises(ValueError, match="unrelated owner"):
        bootstrap._prepare_databases(DatabaseSettings(password=SecretStr("synthetic")))  # pyright: ignore[reportPrivateUsage]
    prepare.assert_not_called()
    assert all("ALTER" not in str(call) for call in connection.execute.call_args_list)


@pytest.mark.asyncio
@pytest.mark.parametrize("current", [True, False])
async def test_saq_runtime_only_verifies_schema(*, current: bool) -> None:
    queue = RuntimePostgresQueue(url="postgresql://unused")
    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=(False,))
    target = get_migrations(jobs_table=queue.jobs_table, stats_table=queue.stats_table)[-1][0]
    cursor.fetchall = AsyncMock(return_value=[(target if current else 0,)])
    connection = MagicMock()
    connection.cursor.return_value.__aenter__.return_value = cursor
    queue.pool = MagicMock()
    queue.pool.connection.return_value.__aenter__.return_value = connection
    if current:
        await queue.init_db()
    else:
        with pytest.raises(DatabaseAuthorityError, match="not current"):
            await queue.init_db()
    statements = [str(call.args[0]) for call in cursor.execute.call_args_list]
    assert len(statements) == 2
    assert all(
        "CREATE" not in statement.replace("'CREATE'", "") and "ALTER" not in statement for statement in statements
    )


@pytest.mark.asyncio
async def test_saq_failed_authority_check_closes_owned_pool() -> None:
    queue = RuntimePostgresQueue(url="postgresql://unused")
    queue.pool = MagicMock()
    queue.pool.open = AsyncMock()
    queue.pool.resize = AsyncMock()
    queue.pool.close = AsyncMock()
    queue.init_db = AsyncMock(side_effect=DatabaseAuthorityError("unsafe"))
    with pytest.raises(DatabaseAuthorityError):
        await queue.connect()
    queue.pool.close.assert_awaited_once()


def test_cached_session_factory_cannot_cross_migration_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    state: dict[str, Any] = {"engine": MagicMock(), "session_factory": MagicMock(), "migration": False}
    monkeypatch.setattr(engine, "_state", state)
    assert engine.get_session_factory() is state["session_factory"]
    with engine.database_migration_scope(), pytest.raises(RuntimeError, match="authority boundary"):
        engine.get_session_factory()
