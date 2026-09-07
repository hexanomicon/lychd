"""Bridge conversation records and loop-confined in-memory storage.

Sessions retain visible turns and settled invocation history; Run lifecycle
remains ledger-owned. The durable adapter lives in ``lychd.db.sessions``.
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from lychd.domain.cortex.runs import RunHandle

if TYPE_CHECKING:
    from lychd.domain.web.schemas import BridgeTurn

__all__ = ["BridgeSessionStore", "RunHandle", "SessionRecord", "SessionStorePort"]


def _new_id(prefix: str) -> str:
    """Return a short, prefixed, collision-resistant id."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class SessionRecord:
    """One conversation's identity, visible turns, and settled model history."""

    id: str
    title: str
    created_at: datetime
    sigil_name: str = "magus"
    turns: list[BridgeTurn] = field(default_factory=list)
    message_history: list[Any] = field(default_factory=list)


@runtime_checkable
class SessionStorePort(Protocol):
    """The async session/turn surface (in-memory or DB-backed)."""

    async def create_session(self, *, title: str | None = None) -> SessionRecord: ...

    async def get_session(self, session_id: str) -> SessionRecord | None: ...

    async def list_sessions(self) -> list[SessionRecord]: ...

    async def add_turn(self, session_id: str, turn: BridgeTurn) -> None: ...

    async def settle_agent_turn(
        self,
        session_id: str,
        turn: BridgeTurn,
        *,
        new_messages: list[Any],
    ) -> None: ...

    async def session_for_run(self, run_id: str) -> SessionRecord | None: ...

    async def settled_turn_for_run(self, run_id: str) -> BridgeTurn | None: ...


class BridgeSessionStore:
    """Loop-confined memory storage for conversation projection and history."""

    def __init__(self, *, sigil_name: str = "magus") -> None:
        """Initialize the empty, loop-confined store."""
        self._sessions: dict[str, SessionRecord] = {}
        self._sigil_name = sigil_name
        self._run_to_session: dict[str, str] = {}

    async def create_session(self, *, title: str | None = None) -> SessionRecord:
        """Create and store a new empty session."""
        session_id = _new_id("sess")
        record = SessionRecord(
            id=session_id,
            title=title or "New Communion",
            created_at=datetime.now(UTC),
            sigil_name=self._sigil_name,
        )
        self._sessions[session_id] = record
        return deepcopy(record)

    async def get_session(self, session_id: str) -> SessionRecord | None:
        """Return the session record, or `None` if unknown."""
        record = self._sessions.get(session_id)
        return deepcopy(record) if record is not None else None

    async def list_sessions(self) -> list[SessionRecord]:
        """Return sessions newest-first."""
        records = sorted(self._sessions.values(), key=lambda record: record.created_at, reverse=True)
        return deepcopy(records)

    async def add_turn(self, session_id: str, turn: BridgeTurn) -> None:
        """Append a visible turn, indexing its Run for O(1) lookup."""
        session = self._sessions.get(session_id)
        if session is not None:
            existing = next(
                (
                    item
                    for item in session.turns
                    if turn.run_id is not None and item.run_id == turn.run_id and item.role == turn.role
                ),
                None,
            )
            if existing is not None:
                assert_compatible_turn(existing, turn)
                return
            session.turns.append(deepcopy(turn))
            if turn.run_id:
                self._run_to_session[turn.run_id] = session_id

    async def settle_agent_turn(
        self,
        session_id: str,
        turn: BridgeTurn,
        *,
        new_messages: list[Any],
    ) -> None:
        """Atomically append the visible reply and its Pydantic AI history suffix."""
        session = self._sessions.get(session_id)
        if session is None:
            return
        existing = next(
            (
                item
                for item in session.turns
                if turn.run_id is not None and item.run_id == turn.run_id and item.role == turn.role
            ),
            None,
        )
        if existing is not None:
            assert_compatible_turn(existing, turn)
            return
        session.turns.append(deepcopy(turn))
        session.message_history.extend(deepcopy(new_messages))
        if turn.run_id:
            self._run_to_session[turn.run_id] = session_id

    async def session_for_run(self, run_id: str) -> SessionRecord | None:
        """Return the session that owns a run (O(1) index), or `None`."""
        session_id = self._run_to_session.get(run_id)
        record = self._sessions.get(session_id) if session_id is not None else None
        return deepcopy(record) if record is not None else None

    async def settled_turn_for_run(self, run_id: str) -> BridgeTurn | None:
        """Return the newest settled agent turn for a run, or `None`."""
        session = await self.session_for_run(run_id)
        if session is None:
            return None
        for turn in reversed(session.turns):
            if turn.run_id == run_id and turn.role == "agent":
                return turn
        return None


def _same_turn_outcome(existing: BridgeTurn, incoming: BridgeTurn) -> bool:
    """Compare replay-significant turn fields while ignoring write timestamps."""
    return (
        existing.role,
        existing.content,
        existing.run_id,
        existing.state,
        existing.fragments,
    ) == (
        incoming.role,
        incoming.content,
        incoming.run_id,
        incoming.state,
        incoming.fragments,
    )


def assert_compatible_turn(existing: BridgeTurn, incoming: BridgeTurn) -> None:
    """Reject reuse of one Run/role identity for a different visible outcome."""
    if not _same_turn_outcome(existing, incoming):
        msg = "One Run cannot retain conflicting Bridge turns for the same role."
        raise ValueError(msg)
