"""Versioned JSON contracts shared by the Altar and non-browser clients."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from lychd.domain.web.schemas import ConsentCard, NexusBoard, SwapTicket


class ClientContract(BaseModel):
    """Strict base for hostile client input and stable response shapes."""

    model_config = ConfigDict(extra="forbid")


class BridgeTurnView(ClientContract):
    """One serializable turn projected into a Bridge session."""

    role: Literal["user", "agent"]
    content: str
    run_id: str | None = None
    state: str = "settled"
    fragments: list[str] = Field(default_factory=list)
    created_at: datetime


class SessionSummary(ClientContract):
    """Compact session entry for the Bridge rail."""

    id: str
    title: str
    created_at: datetime


class SessionView(SessionSummary):
    """A selected Bridge session and its settled turns."""

    turns: list[BridgeTurnView] = Field(default_factory=list)


class BridgeSnapshot(ClientContract):
    """Refresh-reconstructable Bridge projection."""

    sessions: list[SessionSummary]
    session: SessionView | None
    pending_consents: list[ConsentCard]
    pending_count: int


class SessionCreated(ClientContract):
    """Identity returned after opening a session."""

    session: SessionView


class MessageIntent(ClientContract):
    """Complete text command admitted through the Bridge."""

    prompt: str = Field(min_length=1, max_length=100_000)


class MessageAccepted(ClientContract):
    """Run identity and optimistic user turn returned after admission."""

    run_id: str
    turn: BridgeTurnView


class ConsentDecisionIntent(ClientContract):
    """One explicit operator verdict."""

    verdict: Literal["approve", "deny"]


class ConsentDecisionResult(ClientContract):
    """Settled consent projection after the Vessel rechecks the intent."""

    consent: ConsentCard
    pending_count: int


class SessionInspector(ClientContract):
    """Small, non-authoritative contextual session projection."""

    session_id: str
    title: str | None
    turn_count: int
    pending_count: int


class RunEventEnvelope(ClientContract):
    """Versioned semantic SSE payload."""

    schema_version: Literal[1] = 1
    run_id: str
    seq: int
    kind: Literal["token", "status", "node", "fragment", "consent", "log", "done", "resync"]
    occurred_at: datetime
    payload: dict[str, Any]


class NexusSnapshot(ClientContract):
    """The current capability board."""

    board: NexusBoard


class SwapIntent(ClientContract):
    """One requested capability transition."""

    target: str = Field(min_length=1)


class SwapAccepted(ClientContract):
    """A process-local transition ticket."""

    ticket: SwapTicket


class TransitionEventEnvelope(ClientContract):
    """Versioned semantic Nexus transition event."""

    schema_version: Literal[1] = 1
    seq: int
    ticket: SwapTicket


class LoomSummary(ClientContract):
    """Compact workflow catalogue entry."""

    name: str
    title: str
    description: str
    trigger_hint: str


class AltarStatus(ClientContract):
    """Shared shell status independent of any one instrument."""

    pending_consents: int
