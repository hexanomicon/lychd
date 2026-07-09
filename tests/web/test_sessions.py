"""BridgeSessionStore semantics: run index + settled-turn lookup (async, consent-free)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Self, cast
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from lychd.domain.web.schemas import BridgeTurn
from lychd.domain.web.sessions import BridgeSessionStore, DbBridgeSessionStore


@pytest.mark.asyncio
async def test_session_for_run_indexed_by_turn() -> None:
    """A settled agent turn indexes its run for O(1) session lookup."""
    store = BridgeSessionStore()
    session = await store.create_session()
    await store.add_turn(session.id, BridgeTurn(role="agent", content="risen", run_id="r1", state="settled"))
    assert (await store.session_for_run("r1")) is session
    settled = await store.settled_turn_for_run("r1")
    assert settled is not None
    assert settled.content == "risen"
    assert (await store.session_for_run("missing")) is None
    assert (await store.settled_turn_for_run("missing")) is None


@pytest.mark.asyncio
async def test_list_sessions_newest_first() -> None:
    """Sessions list newest-first."""
    store = BridgeSessionStore()
    first = await store.create_session(title="first")
    second = await store.create_session(title="second")
    listed = await store.list_sessions()
    assert [s.id for s in listed[:2]] == [second.id, first.id]


@pytest.mark.asyncio
async def test_db_add_turn_locks_row_before_jsonb_append() -> None:
    """The JSONB append is enclosed by a transaction-scoped PostgreSQL row lock."""

    class _Transaction:
        async def __aenter__(self) -> None:
            return None

        async def __aexit__(self, *_exc: object) -> None:
            return None

    class _Session:
        def __init__(self) -> None:
            self.row = SimpleNamespace(meta={"kept": True, "turns": []})
            self.statement: Any = None

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_exc: object) -> None:
            return None

        def begin(self) -> _Transaction:
            return _Transaction()

        async def scalar(self, statement: Any) -> Any:
            self.statement = statement
            return self.row

    session = _Session()
    factory = lambda: session  # noqa: E731 - a tiny async-sessionmaker structural fake
    store = DbBridgeSessionStore(cast("Any", factory), sigil_name="magus")

    await store.add_turn(str(uuid4()), BridgeTurn(role="agent", content="risen", run_id="run_1"))

    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql
    assert session.row.meta["kept"] is True
    assert [turn["content"] for turn in session.row.meta["turns"]] == ["risen"]
