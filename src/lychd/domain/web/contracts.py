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


class RunProjectionSnapshot(ClientContract):
    """Replaceable projection for one run at an exact event cursor."""

    schema_version: Literal[1] = 1
    session_id: str
    run_id: str
    cursor: int
    content: str
    run_status: str
    activity: str
    pattern_id: str
    pattern_revision: str
    loom_path: str | None
    orb_path: str
    evidence_capture: Literal["process_local", "durable_best_effort"]
    fragments: list[dict[str, Any]]
    occurrence_id: str | None
    dispatch_occurrence_id: str | None
    grant_id: str | None
    capability_key: str | None
    transition_occurrence_id: str | None
    transition_request_id: str | None
    transition_phase: str | None
    terminal: bool


class BridgeSnapshot(ClientContract):
    """Refresh-reconstructable Bridge projection."""

    sessions: list[SessionSummary]
    session: SessionView | None
    active_runs: list[RunProjectionSnapshot]
    pending_consents: list[ConsentCard]
    pending_count: int


class SessionCreated(ClientContract):
    """Identity returned after opening a session."""

    session: SessionView


class MessageIntent(ClientContract):
    """Complete text command admitted through the Bridge."""

    prompt: str = Field(min_length=1, max_length=100_000)


class MessageAccepted(ClientContract):
    """Authoritative run and Pattern identity returned after admission."""

    run_id: str
    pattern_id: str
    pattern_revision: str
    loom_path: str
    orb_path: str
    evidence_capture: Literal["process_local", "durable_best_effort"]
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
    event_id: str
    seq: int
    kind: Literal[
        "token",
        "status",
        "node",
        "dispatch",
        "transition",
        "fragment",
        "consent",
        "log",
        "done",
        "resync",
    ]
    occurred_at: datetime
    payload: dict[str, Any]


class TransitionRecordView(ClientContract):
    """One retained cross-source orchestration request."""

    request_id: str
    source: Literal["run", "operator"]
    target_capability_key: str
    priority: float
    phase: str
    requested_at: datetime
    observed_at: datetime
    run_id: str | None
    occurrence_id: str | None
    action_type: str | None
    physical_transition_id: str | None
    compensation_transition_id: str | None
    detail: str | None
    orb_path: str | None
    bridge_path: str | None


class NexusSnapshot(ClientContract):
    """A projection assembled from explicitly timestamped capability observations."""

    snapshot_at: datetime
    board: NexusBoard
    containment_reason: str | None
    transitions: list[TransitionRecordView]


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
    """Compact current Pattern catalogue entry."""

    pattern_id: str
    revision: str
    digest: str
    title: str
    description: str
    trigger_hint: str
    detail_path: str


class PatternReference(ClientContract):
    """Exact or explicitly unavailable Weaver identity attached to a Run."""

    pattern_id: str
    revision: str
    digest: str | None
    exact: bool
    loom_path: str | None


class OrbRunSummary(ClientContract):
    """Safe selected-Run truth seen by looking into the Orb."""

    run_id: str
    session_id: str
    status: str
    workflow_name: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_present: bool
    bridge_path: str


class EvidenceGap(ClientContract):
    """A sequence interval whose cause cannot be inferred from retained rows."""

    start_seq: int
    end_seq: int
    classification: Literal["unknown_or_omitted"] = "unknown_or_omitted"


class EvidenceItem(ClientContract):
    """One safe structural event in the selected Run's retained ledger."""

    event_id: str
    seq: int
    kind: str
    occurred_at: datetime
    summary: str
    subject_key: str | None = None
    phase: str | None = None
    occurrence_id: str | None = None
    transition_request_id: str | None = None
    nexus_path: str | None = None
    capture: Literal["process_local", "durable_best_effort"]


class OrbRunSnapshot(ClientContract):
    """Selected-run Orb evidence page with explicit capture and gap limits."""

    schema_version: Literal[1] = 1
    snapshot_at: datetime
    run: OrbRunSummary
    pattern: PatternReference
    capture: Literal["process_local", "durable_best_effort"]
    ledger_head_seq: int
    page_end_seq: int | None
    has_more: bool
    live_tail: Literal["not_available"] = "not_available"
    known_omissions: list[str]
    gaps: list[EvidenceGap]
    evidence: list[EvidenceItem]
    next_after_seq: int | None


class CsrfClientContract(ClientContract):
    """Public double-submit names configured by the trusted Vessel."""

    cookie_name: str
    header_name: str


class AltarStatus(ClientContract):
    """Shared shell status independent of any one instrument."""

    pending_consents: int
    csrf: CsrfClientContract
