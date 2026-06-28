"""`BridgeSessionStore` — in-memory sessions, runs, and parked consents (§5.6).

Loop-confined: every mutation is synchronous and only ever touched from a single
event loop, so no locks are needed. Written against ids, not objects, so a
Phylactery-backed implementation can replace it without changing callers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from lychd.domain.cortex.stasis import RunChannel

if TYPE_CHECKING:
    import asyncio

    from lychd.agents.workflows.base import Workflow
    from lychd.domain.web.schemas import BridgeTurn

RunStatus = Literal["routed", "running", "awaiting_consent", "done", "failed"]
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
class RunRecord:
    """One graph run: its event channel, task handle, and lifecycle status."""

    run_id: str
    channel: RunChannel
    workflow_name: str
    status: RunStatus
    task: asyncio.Task[Any] | None = None


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


@dataclass(frozen=True, kw_only=True)
class RunHandle:
    """The handle `submit()` returns: run id, workflow, live channel, task."""

    run_id: str
    workflow_name: str
    channel: RunChannel
    task: asyncio.Task[Any] | None = None


class BridgeSessionStore:
    """In-memory store for Bridge sessions, runs, and parked consents."""

    def __init__(self) -> None:
        """Initialize the empty, loop-confined store."""
        self._sessions: dict[str, SessionRecord] = {}
        self._runs: dict[str, RunRecord] = {}
        self._consents: dict[str, ConsentRecord] = {}

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
        """Append a settled turn to a session."""
        session = self._sessions.get(session_id)
        if session is not None:
            session.turns.append(turn)

    # -- runs -------------------------------------------------------------

    def record_route(self, run_id: str, workflow_name: str) -> RunRecord:
        """Persist the router's choice and open the run's event channel."""
        record = RunRecord(
            run_id=run_id,
            channel=RunChannel(run_id=run_id),
            workflow_name=workflow_name,
            status="routed",
        )
        self._runs[run_id] = record
        return record

    def register_run(self, run_id: str, workflow: Workflow, task: asyncio.Task[Any]) -> RunHandle:
        """Attach the launched task to the run and return its handle."""
        record = self._runs.get(run_id)
        if record is None:
            record = self.record_route(run_id, workflow.name)
        record.task = task
        record.status = "running"
        return RunHandle(
            run_id=run_id,
            workflow_name=record.workflow_name,
            channel=record.channel,
            task=task,
        )

    def channel(self, run_id: str) -> RunChannel:
        """Return the run's event channel, opening one on demand."""
        record = self._runs.get(run_id)
        if record is None:
            record = RunRecord(
                run_id=run_id,
                channel=RunChannel(run_id=run_id),
                workflow_name="",
                status="routed",
            )
            self._runs[run_id] = record
        return record.channel

    def get_run(self, run_id: str) -> RunRecord | None:
        """Return the run record, or `None` if unknown."""
        return self._runs.get(run_id)

    def set_run_status(self, run_id: str, status: RunStatus) -> None:
        """Update a run's lifecycle status."""
        record = self._runs.get(run_id)
        if record is not None:
            record.status = status

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
        process lifetime. The Durable/HitL path (Phylactery-backed) is future work.
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
        self.set_run_status(run_id, "awaiting_consent")
        return consent_id

    def get_consent(self, consent_id: str) -> ConsentRecord | None:
        """Return the parked consent record, or `None` if unknown."""
        return self._consents.get(consent_id)

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
