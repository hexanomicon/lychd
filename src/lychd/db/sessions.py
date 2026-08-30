"""PostgreSQL persistence adapter for Bridge conversation sessions."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from sqlalchemy import select

from lychd.db.models import Run, Session
from lychd.domain.web.sessions import SessionRecord, assert_compatible_turn

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from lychd.domain.web.schemas import BridgeTurn

__all__ = ["DbBridgeSessionStore"]


def _turn_to_json(turn: BridgeTurn) -> dict[str, Any]:
    from pydantic_core import to_jsonable_python

    return cast("dict[str, Any]", to_jsonable_python(turn))


def _turn_from_json(payload: dict[str, Any]) -> BridgeTurn:
    from lychd.domain.web.schemas import BridgeTurn

    data = dict(payload)
    created = data.get("created_at")
    if isinstance(created, str):
        data["created_at"] = datetime.fromisoformat(created)
    fragments = data.get("fragments")
    if isinstance(fragments, list):
        normalized: list[dict[str, Any]] = []
        for fragment in cast("list[Any]", fragments):
            if isinstance(fragment, dict):
                normalized.append(cast("dict[str, Any]", fragment))
            elif isinstance(fragment, str):
                normalized.append(
                    {
                        "kind": fragment,
                        "schema_version": 0,
                        "props": {},
                        "actions": [],
                    }
                )
        data["fragments"] = tuple(normalized)
    return BridgeTurn(**data)


def _owned_turn_payload(turns: list[Any], turn: BridgeTurn) -> dict[str, Any] | None:
    """Find a retained JSON turn with the same Run and role identity."""
    if turn.run_id is None:
        return None
    for item in turns:
        if not isinstance(item, dict):
            continue
        payload = cast("dict[str, Any]", item)
        if payload.get("run_id") == turn.run_id and payload.get("role") == turn.role:
            return payload
    return None


class DbBridgeSessionStore:
    """Durable session store over the ``Session`` row and its JSONB turn ledger."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], *, sigil_name: str) -> None:
        """Bind the store to a session factory and composition-owned Sigil name."""
        self._session_factory = session_factory
        self._sigil_name = sigil_name

    def _record(self, row: Any) -> SessionRecord:
        meta: dict[str, Any] = dict(row.meta or {})
        raw_turns: list[Any] = meta.get("turns", []) if isinstance(meta.get("turns"), list) else []
        turns = [_turn_from_json(cast("dict[str, Any]", turn)) for turn in raw_turns if isinstance(turn, dict)]
        return SessionRecord(
            id=str(row.id),
            title=str(row.title or "New Communion"),
            created_at=row.created_at,
            turns=turns,
            message_history=deepcopy(row.message_history or []),
        )

    async def create_session(self, *, title: str | None = None) -> SessionRecord:
        """Insert a fresh Bridge session row and return its detached record."""
        async with self._session_factory() as session:
            row = Session(
                channel="bridge",
                title=title or "New Communion",
                sigil_name=self._sigil_name,
                meta={"turns": []},
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._record(row)

    async def get_session(self, session_id: str) -> SessionRecord | None:
        """Return one session for a valid UUID, or ``None`` when absent."""
        try:
            row_id = UUID(session_id)
        except ValueError:
            return None
        async with self._session_factory() as session:
            row = await session.get(Session, row_id)
            return self._record(row) if row is not None else None

    async def list_sessions(self) -> list[SessionRecord]:
        """Return sessions newest-first with a stable UUID tiebreaker."""
        async with self._session_factory() as session:
            rows = (await session.scalars(select(Session).order_by(Session.created_at.desc(), Session.id.desc()))).all()
            return [self._record(row) for row in rows]

    async def add_turn(self, session_id: str, turn: BridgeTurn) -> None:
        """Append one settled turn under a transaction-scoped row lock."""
        sid = UUID(session_id)
        async with self._session_factory() as session, session.begin():
            row = await session.scalar(select(Session).where(Session.id == sid).with_for_update())
            if row is None:
                return
            meta: dict[str, Any] = dict(row.meta or {})
            raw = meta.get("turns", [])
            turns: list[Any] = list(cast("list[Any]", raw)) if isinstance(raw, list) else []
            existing = _owned_turn_payload(turns, turn)
            if existing is not None:
                assert_compatible_turn(_turn_from_json(existing), turn)
                return
            turns.append(_turn_to_json(turn))
            row.meta = {**meta, "turns": turns}

    async def settle_agent_turn(
        self,
        session_id: str,
        turn: BridgeTurn,
        *,
        new_messages: list[Any],
    ) -> None:
        """Commit the visible reply and completed model-history suffix together."""
        sid = UUID(session_id)
        async with self._session_factory() as session, session.begin():
            row = await session.scalar(select(Session).where(Session.id == sid).with_for_update())
            if row is None:
                return
            meta: dict[str, Any] = dict(row.meta or {})
            raw = meta.get("turns", [])
            turns: list[Any] = list(cast("list[Any]", raw)) if isinstance(raw, list) else []
            existing = _owned_turn_payload(turns, turn)
            if existing is not None:
                assert_compatible_turn(_turn_from_json(existing), turn)
                return
            turns.append(_turn_to_json(turn))
            row.meta = {**meta, "turns": turns}
            row.message_history = [*(row.message_history or []), *new_messages]

    async def session_for_run(self, run_id: str) -> SessionRecord | None:
        """Resolve the session that owns a Run through its authoritative foreign key."""
        try:
            row_id = UUID(run_id)
        except ValueError:
            return None
        async with self._session_factory() as session:
            session_id = await session.scalar(select(Run.session_id).where(Run.id == row_id))
        return await self.get_session(str(session_id)) if session_id is not None else None

    async def settled_turn_for_run(self, run_id: str) -> BridgeTurn | None:
        """Return the newest settled agent turn for a Run, or ``None``."""
        session = await self.session_for_run(run_id)
        if session is None:
            return None
        for turn in reversed(session.turns):
            if turn.run_id == run_id and turn.role == "agent":
                return turn
        return None
