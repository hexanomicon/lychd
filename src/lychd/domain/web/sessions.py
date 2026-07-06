"""`BridgeSessionStore` — in-memory sessions, turns, and parked consents (§5.6).

Loop-confined: every mutation is synchronous and only ever touched from a single
event loop, so no locks are needed. Written against ids, not objects, so a
Phylactery-backed implementation can replace it without changing callers.

Wave 2: run records and event channels were **shed** to the run substrate — the
`RunLedger` owns run truth/status and the `RunEventBus` owns channels. This store
keeps only sessions, settled turns, and parked consents (the consent record is the
Wave-4 HitL seam). `RunHandle` is re-exported from `domain/cortex/runs`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from lychd.domain.cortex.runs import RunHandle

if TYPE_CHECKING:
    from lychd.domain.web.schemas import BridgeTurn

__all__ = ["BridgeSessionStore", "ConsentRecord", "RunHandle", "SessionRecord"]

ConsentStatus = Literal["pending_consent", "consented", "refused"]


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


@dataclass
class ConsentRecord:
    """One parked, approval-bearing tool call awaiting the Magus's verdict."""

    id: str
    run_id: str
    session_id: str
    tool_name: str
    args: dict[str, Any]
    requests: Any
    status: ConsentStatus = "pending_consent"


class BridgeSessionStore:
    """In-memory store for Bridge sessions, settled turns, and parked consents."""

    def __init__(self) -> None:
        """Initialize the empty, loop-confined store."""
        self._sessions: dict[str, SessionRecord] = {}
        self._consents: dict[str, ConsentRecord] = {}
        self._run_to_session: dict[str, str] = {}

    # -- sessions ---------------------------------------------------------

    def create_session(self, *, title: str | None = None) -> SessionRecord:
        """Create and store a new empty session."""
        session_id = _new_id("sess")
        record = SessionRecord(
            id=session_id,
            title=title or "New Communion",
            created_at=datetime.now(UTC),
        )
        self._sessions[session_id] = record
        return record

    def get_session(self, session_id: str) -> SessionRecord | None:
        """Return the session record, or `None` if unknown."""
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[SessionRecord]:
        """Return sessions newest-first."""
        return sorted(self._sessions.values(), key=lambda record: record.created_at, reverse=True)

    def add_turn(self, session_id: str, turn: BridgeTurn) -> None:
        """Append a settled turn to a session, indexing it by run for O(1) lookup."""
        session = self._sessions.get(session_id)
        if session is not None:
            session.turns.append(turn)
            if turn.run_id:
                self._run_to_session[turn.run_id] = session_id

    def session_for_run(self, run_id: str) -> SessionRecord | None:
        """Return the session that owns a run (O(1) index), or `None`."""
        session_id = self._run_to_session.get(run_id)
        if session_id is None:
            record = self._consents_by_run(run_id)
            session_id = record.session_id if record is not None else None
        return self._sessions.get(session_id) if session_id is not None else None

    def settled_turn_for_run(self, run_id: str) -> BridgeTurn | None:
        """Return the newest settled agent turn for a run, or `None`."""
        session = self.session_for_run(run_id)
        if session is None:
            return None
        for turn in reversed(session.turns):
            if turn.run_id == run_id and turn.role == "agent":
                return turn
        return None

    def _consents_by_run(self, run_id: str) -> ConsentRecord | None:
        for record in self._consents.values():
            if record.run_id == run_id:
                return record
        return None

    # -- consents ---------------------------------------------------------

    def park_consent(
        self,
        *,
        run_id: str,
        session_id: str,
        tool_name: str,
        args: dict[str, Any],
        requests: Any,
    ) -> str:
        """Park a deferred tool request for approval and return its consent id.

        Live path only: this records enough to resume the run within the current
        process lifetime. The Durable/HitL path (Phylactery-backed) is Wave 4. Run
        status (AWAITING_CONSENT) is written by the ghoul via the `RunLedger`.
        """
        consent_id = _new_id("consent")
        self._consents[consent_id] = ConsentRecord(
            id=consent_id,
            run_id=run_id,
            session_id=session_id,
            tool_name=tool_name,
            args=args,
            requests=requests,
        )
        self._run_to_session[run_id] = session_id
        return consent_id

    def get_consent(self, consent_id: str) -> ConsentRecord | None:
        """Return the parked consent record, or `None` if unknown."""
        return self._consents.get(consent_id)

    def pending_consent_for_run(self, run_id: str) -> ConsentRecord | None:
        """Return the run's still-pending consent, or `None` (the ghoul park probe)."""
        record = self._consents_by_run(run_id)
        return record if record is not None and record.status == "pending_consent" else None

    def resolve_consent(self, consent_id: str, *, approved: bool) -> ConsentRecord | None:
        """Mark a parked consent consented or refused; return the updated record."""
        record = self._consents.get(consent_id)
        if record is None:
            return None
        record.status = "consented" if approved else "refused"
        return record

    def pending_consent_count(self) -> int:
        """Return the number of consents still awaiting a verdict (feeds the sigil)."""
        return sum(1 for record in self._consents.values() if record.status == "pending_consent")
