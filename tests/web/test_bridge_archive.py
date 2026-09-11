"""Archive pages avoid hydrating unrelated history and preserve complete navigation."""

# Poison stored history to make accidental archive hydration a failing oracle.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import asyncio
import base64
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock

import pytest

from lychd.db.sessions import DbBridgeSessionStore
from lychd.domain.codex.ledger import CodexConsentLedger
from lychd.domain.web.sessions import BridgeSessionStore

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import TestClient


class _UnreadableHistory:
    def __deepcopy__(self, _memo: object) -> None:
        message = "Archive metadata must not copy retained model history."
        raise AssertionError(message)


def test_archive_pages_reach_every_session_without_copying_history(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions = fake_services.bridge_sessions

    async def seed() -> list[str]:
        created = [await sessions.create_session(title=f"Session {index}") for index in range(53)]
        # Poison only archive histories; the selected newest conversation remains usable.
        for record in created[:-1]:
            sessions._sessions[record.id].message_history.append(_UnreadableHistory())
        return [item.id for item in reversed(created)]

    ids = asyncio.run(seed())
    forbidden = AsyncMock(side_effect=AssertionError("Archive snapshot used the unbounded record listing."))
    monkeypatch.setattr(sessions, "list_sessions", forbidden)
    selected_runs = AsyncMock(wraps=fake_services.ledger.list_for_session)
    monkeypatch.setattr(fake_services.ledger, "list_for_session", selected_runs)

    first_response = altar_client.get("/api/v1/bridge")
    assert first_response.status_code == 200
    first = first_response.json()
    assert [item["id"] for item in first["sessions"]] == ids[:50]
    assert first["session"]["id"] == ids[0]
    selected_runs.assert_awaited_once_with(ids[0])

    second_response = altar_client.get("/api/v1/bridge/sessions", params={"cursor": first["sessions_next_cursor"]})
    assert second_response.status_code == 200
    second = second_response.json()
    assert [item["id"] for item in second["sessions"]] == ids[50:]
    assert second["next_cursor"] is None
    selected_runs.assert_awaited_once()
    forbidden.assert_not_awaited()


@pytest.mark.parametrize(
    "cursor",
    [
        "%",
        "x" * 513,
        base64.urlsafe_b64encode(b"{}").decode(),
        base64.urlsafe_b64encode(b'{"created_at":"2026-09-08","id":"session"}').decode(),
        base64.urlsafe_b64encode(b'{"created_at":"2026-09-08T00:00:00Z","id":"../escape"}').decode(),
    ],
)
def test_archive_cursor_is_bounded_and_validated(altar_client: TestClient[Litestar], cursor: str) -> None:
    response = altar_client.get("/api/v1/bridge/sessions", params={"cursor": cursor})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_memory_archive_keyset_keeps_timestamp_ties_without_hydrating_payloads() -> None:
    store = BridgeSessionStore()
    created = [await store.create_session() for _ in range(52)]
    instant = datetime(2026, 9, 8, 12, 30, 0, 123456, tzinfo=UTC)
    for item in created:
        record = store._sessions[item.id]
        record.created_at = instant
        record.message_history.append(_UnreadableHistory())
    expected = sorted((item.id for item in created), reverse=True)

    first = await store.list_session_summaries()
    assert len(first) == 51
    last = first[49]
    second = await store.list_session_summaries(before=(last.created_at, last.id))
    assert [item.id for item in first[:50]] + [item.id for item in second] == expected
    assert last.created_at.microsecond == 123456


@pytest.mark.asyncio
async def test_db_archive_selects_only_identity_columns_and_limits_query() -> None:
    statements: list[Any] = []

    async def execute(statement: Any) -> Any:
        statements.append(statement)
        return SimpleNamespace(all=lambda: cast("list[Any]", []))

    session = AsyncMock()
    session.execute.side_effect = execute
    session.__aenter__.return_value = session
    store = DbBridgeSessionStore(cast("Any", lambda: session), sigil_name="magus")
    await store.list_session_summaries(
        before=(datetime(2026, 9, 8, tzinfo=UTC), "00000000-0000-0000-0000-000000000001")
    )

    assert len(statements) == 1
    statement = statements[0]
    assert [column.name for column in statement.selected_columns] == ["id", "title", "created_at"]
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "LIMIT 51" in sql
    assert "session.created_at <" in sql
    assert "session.id <" in sql


@pytest.mark.asyncio
async def test_db_pending_counts_group_without_loading_consent_or_run_payloads() -> None:
    session_id = "00000000-0000-0000-0000-000000000001"
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(all=lambda: [(session_id, 2)])
    session.__aenter__.return_value = session
    ledger = CodexConsentLedger(session_factory=cast("Any", lambda: session))

    run_session_id = AsyncMock(side_effect=AssertionError("Grouped DB query must not hydrate Runs"))
    counts = await ledger.pending_counts_for_sessions(frozenset({session_id}), run_session_id=run_session_id)

    assert counts == {session_id: 2}
    run_session_id.assert_not_awaited()
    session.execute.assert_awaited_once()
    sql = str(session.execute.await_args.args[0])
    assert "count(consent.id)" in sql
    assert "GROUP BY run.session_id" in sql
    assert "payload" not in sql
    assert "input" not in sql
