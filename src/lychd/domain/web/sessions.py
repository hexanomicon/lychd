"""Session stores: `SessionStorePort` + in-memory + DB-backed (§4.1, §5.6).

`SessionStorePort` is the async surface the turn ledger + web read; it carries ONLY
sessions and settled turns — consent lives in the `ConsentLedger` now (the consent
half was shed in 4C-5). `BridgeSessionStore` is the loop-confined in-memory tier
(dev floor + tests); `DbBridgeSessionStore` persists over the `Session` table so a
session and its turns survive a restart. `RunHandle` is re-exported for callers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable
from uuid import UUID

from lychd.domain.cortex.runs import RunHandle

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from lychd.domain.web.schemas import BridgeTurn

__all__ = ["BridgeSessionStore", "DbBridgeSessionStore", "RunHandle", "SessionRecord", "SessionStorePort"]


def _new_id(prefix: str) -> str:
    """Return a short, prefixed, collision-resistant id."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class SessionRecord:
    """One Bridge session: its identity and settled turns."""

    id: str
    title: str
    created_at: datetime
    turns: list[BridgeTurn] = field(default_factory=list)


@runtime_checkable
class SessionStorePort(Protocol):
    """The async session/turn surface (in-memory or DB-backed)."""

    async def create_session(self, *, title: str | None = None) -> SessionRecord: ...

    async def get_session(self, session_id: str) -> SessionRecord | None: ...

    async def list_sessions(self) -> list[SessionRecord]: ...

    async def add_turn(self, session_id: str, turn: BridgeTurn) -> None: ...

    async def session_for_run(self, run_id: str) -> SessionRecord | None: ...

    async def settled_turn_for_run(self, run_id: str) -> BridgeTurn | None: ...


class BridgeSessionStore:
    """In-memory store for Bridge sessions and settled turns (loop-confined)."""

    def __init__(self) -> None:
        """Initialize the empty, loop-confined store."""
        self._sessions: dict[str, SessionRecord] = {}
        self._run_to_session: dict[str, str] = {}

    async def create_session(self, *, title: str | None = None) -> SessionRecord:
        """Create and store a new empty session."""
        session_id = _new_id("sess")
        record = SessionRecord(id=session_id, title=title or "New Communion", created_at=datetime.now(UTC))
        self._sessions[session_id] = record
        return record

    async def get_session(self, session_id: str) -> SessionRecord | None:
        """Return the session record, or `None` if unknown."""
        return self._sessions.get(session_id)

    async def list_sessions(self) -> list[SessionRecord]:
        """Return sessions newest-first."""
        return sorted(self._sessions.values(), key=lambda record: record.created_at, reverse=True)

    async def add_turn(self, session_id: str, turn: BridgeTurn) -> None:
        """Append a settled turn to a session, indexing it by run for O(1) lookup."""
        session = self._sessions.get(session_id)
        if session is not None:
            session.turns.append(turn)
            if turn.run_id:
                self._run_to_session[turn.run_id] = session_id

    async def session_for_run(self, run_id: str) -> SessionRecord | None:
        """Return the session that owns a run (O(1) index), or `None`."""
        session_id = self._run_to_session.get(run_id)
        return self._sessions.get(session_id) if session_id is not None else None

    async def settled_turn_for_run(self, run_id: str) -> BridgeTurn | None:
        """Return the newest settled agent turn for a run, or `None`."""
        session = await self.session_for_run(run_id)
        if session is None:
            return None
        for turn in reversed(session.turns):
            if turn.run_id == run_id and turn.role == "agent":
                return turn
        return None


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
        data["fragments"] = tuple(cast("list[Any]", fragments))
    return BridgeTurn(**data)


class DbBridgeSessionStore:
    """Durable session store over the `Session` table (turns → `Session.meta["turns"]`).

    Runtime-validation seam (PG, Linux): requires the `session`/`run` tables. Turns
    persist as a JSONB list under `meta["turns"]`; `message_history` stays RESERVED.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], *, sigil_name: str) -> None:
        """Bind the store to a session factory + the composition-root sigil name."""
        self._session_factory = session_factory
        self._sigil_name = sigil_name

    def _record(self, row: Any) -> SessionRecord:
        meta: dict[str, Any] = dict(row.meta or {})
        raw_turns: list[Any] = meta.get("turns", []) if isinstance(meta.get("turns"), list) else []
        turns = [_turn_from_json(cast("dict[str, Any]", t)) for t in raw_turns if isinstance(t, dict)]
        return SessionRecord(
            id=str(row.id), title=str(row.title or "New Communion"), created_at=row.created_at, turns=turns
        )

    async def create_session(self, *, title: str | None = None) -> SessionRecord:
        """Insert a fresh `Session` row (bridge channel) and return its record."""
        from lychd.db.models import Session
        from lychd.domain.web.services import SessionService

        async with self._session_factory() as session:
            row = await SessionService(session=session).create(
                Session(
                    channel="bridge", title=title or "New Communion", sigil_name=self._sigil_name, meta={"turns": []}
                ),
                auto_commit=True,
            )
            return self._record(row)

    async def get_session(self, session_id: str) -> SessionRecord | None:
        """Return the session record for a UUID string, or `None`."""
        from lychd.domain.web.services import SessionService

        async with self._session_factory() as session:
            row = await SessionService(session=session).get_one_or_none(id=UUID(session_id))
            return self._record(row) if row is not None else None

    async def list_sessions(self) -> list[SessionRecord]:
        """Return sessions newest-first."""
        from lychd.db.models import Session
        from lychd.domain.web.services import SessionService

        async with self._session_factory() as session:
            rows = await SessionService(session=session).list(order_by=[(Session.created_at, True)])
            return [self._record(row) for row in reversed(rows)]

    async def add_turn(self, session_id: str, turn: BridgeTurn) -> None:
        """Append one settled turn while holding the session row lock.

        Turns currently share ``Session.meta`` with other session metadata, so the
        append remains a JSONB read-modify-write.  ``SELECT ... FOR UPDATE`` makes
        that operation transaction-safe across concurrent requests and processes:
        each writer reads the previous writer's committed list before appending.
        Reassigning ``meta`` wholesale still makes SQLAlchemy's JSONB change
        detection explicit.  A future normalized Turn table can replace this
        storage detail without changing the port.
        """
        from sqlalchemy import select

        from lychd.db.models import Session

        sid = UUID(session_id)
        async with self._session_factory() as session, session.begin():
            row = await session.scalar(select(Session).where(Session.id == sid).with_for_update())
            if row is None:
                return
            meta: dict[str, Any] = dict(row.meta or {})
            raw = meta.get("turns", [])
            turns: list[Any] = list(cast("list[Any]", raw)) if isinstance(raw, list) else []
            turns.append(_turn_to_json(turn))
            row.meta = {**meta, "turns": turns}

    async def session_for_run(self, run_id: str) -> SessionRecord | None:
        """Return the session that owns a run via the Run.session_id FK, or `None`."""
        from lychd.domain.cortex.services import RunService

        async with self._session_factory() as session:
            run = await RunService(session=session).get_one_or_none(id=UUID(run_id))
            if run is None or run.session_id is None:
                return None
            session_fk = cast("Any", run.session_id)
        return await self.get_session(str(session_fk))

    async def settled_turn_for_run(self, run_id: str) -> BridgeTurn | None:
        """Return the newest settled agent turn for a run, or `None`."""
        session = await self.session_for_run(run_id)
        if session is None:
            return None
        for turn in reversed(session.turns):
            if turn.run_id == run_id and turn.role == "agent":
                return turn
        return None
