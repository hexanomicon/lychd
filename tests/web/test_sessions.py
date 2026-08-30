"""BridgeSessionStore semantics: run index + settled-turn lookup (async, consent-free)."""

# This module explicitly verifies the database adapter's legacy-row normalizer.
# pyright: reportPrivateUsage=false
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from lychd.db.sessions import DbBridgeSessionStore
from lychd.domain.web.schemas import BridgeTurn
from lychd.domain.web.sessions import BridgeSessionStore


@pytest.mark.asyncio
async def test_session_for_run_indexed_by_turn() -> None:
    """A settled agent turn indexes its run for O(1) session lookup."""
    store = BridgeSessionStore()
    session = await store.create_session()
    await store.add_turn(session.id, BridgeTurn(role="agent", content="risen", run_id="r1", state="settled"))
    owner = await store.session_for_run("r1")
    assert owner is not None
    assert owner.id == session.id
    assert [turn.content for turn in owner.turns] == ["risen"]
    assert owner is not session
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

    settled = await store.get_session(session.id)
    assert settled is not None
    assert [turn.content for turn in settled.turns] == ["first", "second"]
    assert settled.message_history == [*first_suffix, *second_suffix]


@pytest.mark.asyncio
async def test_settle_agent_turn_replay_is_idempotent_and_conflicts_fail_closed() -> None:
    store = BridgeSessionStore()
    session = await store.create_session()
    turn = BridgeTurn(role="agent", content="risen", run_id="run-1", fragments=({"kind": "text"},))
    suffix = [{"kind": "response"}]

    await store.settle_agent_turn(session.id, turn, new_messages=suffix)
    await store.settle_agent_turn(session.id, turn, new_messages=suffix)

    settled = await store.get_session(session.id)
    assert settled is not None
    assert settled.turns == [turn]
    assert settled.message_history == suffix

    with pytest.raises(ValueError, match="conflicting Bridge turns"):
        await store.settle_agent_turn(
            session.id,
            BridgeTurn(role="agent", content="changed", run_id="run-1"),
            new_messages=[{"kind": "different"}],
        )

    settled = await store.get_session(session.id)
    assert settled is not None
    assert settled.turns == [turn]
    assert settled.message_history == suffix


@pytest.mark.asyncio
async def test_memory_session_boundaries_detach_nested_values() -> None:
    store = BridgeSessionStore()
    created = await store.create_session()
    fragment: dict[str, Any] = {"kind": "text", "props": {"values": ["kept"]}}
    messages: list[Any] = [{"parts": [{"text": "kept"}]}]
    await store.settle_agent_turn(
        created.id,
        BridgeTurn(role="agent", content="risen", run_id="run-detached", fragments=(fragment,)),
        new_messages=messages,
    )

    cast("dict[str, Any]", fragment["props"])["values"].append("caller-write")
    cast("list[dict[str, Any]]", messages[0]["parts"])[0]["text"] = "caller-write"
    first = await store.get_session(created.id)
    assert first is not None
    assert first.turns[0].fragments[0]["props"] == {"values": ["kept"]}
    assert first.message_history == [{"parts": [{"text": "kept"}]}]

    cast("dict[str, Any]", first.turns[0].fragments[0]["props"])["values"].append("read-view-write")
    cast("list[dict[str, Any]]", first.message_history[0]["parts"])[0]["text"] = "read-view-write"
    second = await store.get_session(created.id)
    assert second is not None
    assert second.turns[0].fragments[0]["props"] == {"values": ["kept"]}
    assert second.message_history == [{"parts": [{"text": "kept"}]}]


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
