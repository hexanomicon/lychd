"""BridgeSessionStore semantics: run index + settled-turn lookup (async, consent-free)."""

# This module explicitly verifies the database adapter's legacy-row normalizer.
# pyright: reportPrivateUsage=false
from __future__ import annotations

from datetime import UTC, datetime
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
async def test_settle_agent_turn_appends_visible_reply_and_model_suffix_together() -> None:
    store = BridgeSessionStore()
    session = await store.create_session()
    first_suffix = [{"kind": "request"}, {"kind": "response"}]
    second_suffix = [{"kind": "request", "run_id": "run-2"}]

    await store.settle_agent_turn(
        session.id,
        BridgeTurn(role="agent", content="first", run_id="run-1"),
        new_messages=first_suffix,
    )
    await store.settle_agent_turn(
        session.id,
        BridgeTurn(role="agent", content="second", run_id="run-2"),
        new_messages=second_suffix,
    )

    assert [turn.content for turn in session.turns] == ["first", "second"]
    assert session.message_history == [*first_suffix, *second_suffix]


@pytest.mark.asyncio
async def test_settle_agent_turn_replay_is_idempotent_and_conflicts_fail_closed() -> None:
    store = BridgeSessionStore()
    session = await store.create_session()
    turn = BridgeTurn(role="agent", content="risen", run_id="run-1", fragments=({"kind": "text"},))
    suffix = [{"kind": "response"}]

    await store.settle_agent_turn(session.id, turn, new_messages=suffix)
    await store.settle_agent_turn(session.id, turn, new_messages=suffix)

    assert session.turns == [turn]
    assert session.message_history == suffix

    with pytest.raises(ValueError, match="conflicting Bridge turns"):
        await store.settle_agent_turn(
            session.id,
            BridgeTurn(role="agent", content="changed", run_id="run-1"),
            new_messages=[{"kind": "different"}],
        )

    assert session.turns == [turn]
    assert session.message_history == suffix


def test_db_record_normalizes_legacy_fragment_keys_into_inert_descriptors() -> None:
    store = DbBridgeSessionStore(cast("Any", lambda: None), sigil_name="magus")
    row = SimpleNamespace(
        id=uuid4(),
        title="Old communion",
        created_at=datetime.now(UTC),
        message_history=[],
        meta={
            "turns": [
                {
                    "role": "agent",
                    "content": "retained",
                    "run_id": "run-old",
                    "fragments": ["genui.plan_checklist"],
                }
            ]
        },
    )

    record = store._record(row)

    assert record.turns[0].fragments == (
        {
            "kind": "genui.plan_checklist",
            "schema_version": 0,
            "props": {},
            "actions": [],
        },
    )


@pytest.mark.asyncio
async def test_db_read_boundaries_treat_malformed_ids_as_absent() -> None:
    def forbidden_factory() -> None:
        message = "Malformed identifiers must not reach PostgreSQL."
        raise AssertionError(message)

    store = DbBridgeSessionStore(cast("Any", forbidden_factory), sigil_name="magus")

    assert await store.get_session("not-a-uuid") is None
    assert await store.session_for_run("not-a-uuid") is None
    assert await store.settled_turn_for_run("not-a-uuid") is None


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


@pytest.mark.asyncio
async def test_db_settlement_updates_turn_and_message_history_under_one_lock() -> None:
    class _Transaction:
        async def __aenter__(self) -> None:
            return None

        async def __aexit__(self, *_exc: object) -> None:
            return None

    class _Session:
        def __init__(self) -> None:
            self.row = SimpleNamespace(meta={"turns": []}, message_history=[{"kind": "request"}])

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_exc: object) -> None:
            return None

        def begin(self) -> _Transaction:
            return _Transaction()

        async def scalar(self, statement: Any) -> Any:
            _ = statement
            return self.row

    session = _Session()
    factory = lambda: session  # noqa: E731 - structural async-sessionmaker fake
    store = DbBridgeSessionStore(cast("Any", factory), sigil_name="magus")

    session_id = str(uuid4())
    turn = BridgeTurn(role="agent", content="risen", run_id="run-1")
    suffix = [{"kind": "response"}]

    await store.settle_agent_turn(session_id, turn, new_messages=suffix)
    await store.settle_agent_turn(session_id, turn, new_messages=suffix)

    assert [turn["content"] for turn in session.row.meta["turns"]] == ["risen"]
    assert session.row.message_history == [{"kind": "request"}, {"kind": "response"}]

    with pytest.raises(ValueError, match="conflicting Bridge turns"):
        await store.settle_agent_turn(
            session_id,
            BridgeTurn(role="agent", content="changed", run_id="run-1"),
            new_messages=[{"kind": "different"}],
        )

    assert [item["content"] for item in session.row.meta["turns"]] == ["risen"]
    assert session.row.message_history == [{"kind": "request"}, {"kind": "response"}]
