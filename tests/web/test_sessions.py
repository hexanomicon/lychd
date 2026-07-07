"""BridgeSessionStore semantics: run index + settled-turn lookup (async, consent-free)."""

from __future__ import annotations

import pytest

from lychd.domain.web.schemas import BridgeTurn
from lychd.domain.web.sessions import BridgeSessionStore


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
