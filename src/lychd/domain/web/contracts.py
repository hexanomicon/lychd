"""Versioned JSON contracts shared by the Altar and non-browser clients."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from lychd.domain.archive import RecallReceipt
from lychd.domain.weaver.inspection import InspectionBinding
from lychd.domain.web.schemas import ConsentCard, LoomView, NexusBoard, SwapTicket


class ClientContract(BaseModel):
    """Strict base for hostile client input and stable response shapes."""

    model_config = ConfigDict(extra="forbid")


class FrameworkError(ClientContract):
    """Litestar's stable JSON exception body as exposed to typed clients."""

    status_code: int
    detail: str
    extra: dict[str, Any] | list[Any] | None = None


class BridgeTurnView(ClientContract):
    """One serializable turn projected into a Bridge session."""

    role: Literal["user", "agent"]
    content: str
    run_id: str | None = None
    state: str = "settled"
    fragments: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class SessionSummary(ClientContract):
    """Compact session entry with its own authoritative pending-consent count."""

    id: str
    title: str
    created_at: datetime
    pending_count: int = Field(ge=0)


class SessionView(SessionSummary):
    """A selected Bridge session and its settled turns."""

    turns: list[BridgeTurnView] = Field(default_factory=list)


class SessionPage(ClientContract):
    """A bounded archive rail page with an opaque continuation cursor."""

    sessions: list[SessionSummary]
    next_cursor: str | None = None


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
    delegated_job_id: str | None
    delegated_runtime: str | None
    delegated_profile: str | None
    delegated_status: str | None
    terminal: bool


class BridgeComposer(ClientContract):
    """Current configured default casting, not the next Run or its readiness.

    Guidance describes input syntax only. Submission still resolves routing and
    rechecks current authority independently of this replaceable projection.
    """

    pattern_id: str
    pattern_revision: str
    guidance: str | None


class ArchiveBridgeDefault(ClientContract):
    """Current default's exact managed-profile match, without readiness or Run inference."""

    current_default: BridgeComposer | None
    requests_profile: bool | None


class ArchiveRunRecall(ClientContract):
    """Selection matching a retained request; model consumption/provider send are unproved.

    An exact public preseed can match before the workflow reaches recall. This view
    retains neither Context assembly nor source eligibility or current source content.
    """

    run_id: UUID
    status: Literal["not_applicable", "not_recorded", "recorded"]
    receipt: RecallReceipt | None
    capture: Literal["matching_retained_request"] = "matching_retained_request"

    @model_validator(mode="after")
    def consistent_receipt(self) -> ArchiveRunRecall:
        if (self.status == "recorded") != (self.receipt is not None):
            msg = "Recorded status requires exactly one matching receipt."
            raise ValueError(msg)
        if self.receipt is not None and self.receipt.run_id != self.run_id:
            msg = "Receipt belongs to another Run."
            raise ValueError(msg)
        return self


class BridgeSnapshot(ClientContract):
    """Refresh-reconstructable Bridge projection."""

    sessions: list[SessionSummary]
    sessions_next_cursor: str | None = None
    session: SessionView | None
    active_runs: list[RunProjectionSnapshot]
    pending_consents: list[ConsentCard]
    pending_count: int
    composer: BridgeComposer | None = None


class SessionCreated(ClientContract):
    """Identity returned after opening a session."""

    session: SessionView


class MessageIntent(ClientContract):
    """Complete text command admitted through the Bridge."""

    request_id: UUID
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
    review_binding_digest: (
        Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$", min_length=64, max_length=64)] | None
    ) = None


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


class DelegatedRuntimeObservation(ClientContract):
    """One selected extension's honest delegated-runtime delivery boundary."""

    runtime_id: str
    display_name: str
    registrant_id: str
    transport: str
    delivery: str
    runnable: bool
    coffin_profiles: list[str]
    provider_gate: Literal["not_required", "required_unavailable"]
    capacity_posture: Literal["not_configured"]
    limitations: list[str]


class NexusSnapshot(ClientContract):
    """A projection assembled from explicitly timestamped capability observations."""

    snapshot_at: datetime
    board: NexusBoard
    containment_reason: str | None
    transitions: list[TransitionRecordView]
    delegated_runtimes: list[DelegatedRuntimeObservation]


SwapRequestId = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]


class SwapIntent(ClientContract):
    """One requested capability transition."""

    request_id: SwapRequestId
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
    """Compact exact Pattern revision with explicit admission metadata."""

    pattern_id: str
    revision: str
    implementation_revision: str
    entry_node: str
    digest: str
    title: str
    description: str
    trigger_hint: str
    detail_path: str
    active: bool
    default: bool
    route_rank: int | None
    publication: Literal["published", "observed"] = "published"
    binding: InspectionBinding | None = None


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
    bridge_path: str | None
    application_path: str | None = None


class OrbRunPage(ClientContract):
    """A bounded newest-first Run catalogue, with explicit access to older identities."""

    schema_version: Literal[1] = 1
    snapshot_at: datetime
    runs: list[OrbRunSummary]
    next_cursor: str | None
    capture: Literal["process_local", "durable_best_effort"]


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
    animator_name: str | None = None
    capability_family: str | None = None
    model_id: str | None = None
    grant_id: str | None = None
    consent_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]{0,127}$",
        description="Syntactic historical reference only; no current status, review, or authority.",
    )
    capture: Literal["process_local", "durable_best_effort"]


class DelegatedJobEventView(ClientContract):
    """One bounded semantic AgentJob lifecycle event safe for the Orb."""

    event_id: str
    seq: int
    kind: str
    status: str
    occurred_at: datetime


class DelegatedJobSummary(ClientContract):
    """Prompt-free, output-free AgentJob evidence correlated to a selected Run."""

    job_id: str
    request_id: str
    step_id: str
    runtime: str
    profile: str
    status: str
    output_present: bool
    error_present: bool
    artifact_count: int
    events_truncated: bool
    events: list[DelegatedJobEventView]


class OrbBridgePreferenceRoute(ClientContract):
    """One retained admission observation; it is not current readiness."""

    capability_key: str = Field(min_length=1, max_length=512)
    weight: int = Field(strict=True, ge=0, le=1_000_000)
    phase: Literal["cold", "activatable", "warming", "warm", "error", "unknown"] | None
    observed_at: datetime | None
    admission_open: bool
    exclusion_code: Literal["disabled", "not_warm", "admission_closed", "readiness_changed"] | None


class OrbBridgePreferenceSummary(ClientContract):
    """Allowlisted immutable selection facts, never browser policy authority."""

    policy_schema_version: Literal[1]
    policy_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    batch_started_at: datetime
    batch_finished_at: datetime
    selected_capability_key: str = Field(min_length=1, max_length=512)
    routes: list[OrbBridgePreferenceRoute] = Field(min_length=2, max_length=2)


class OrbCreationSummary(ClientContract):
    """Authorized case metadata, separate from selected-Run execution status.

    When admission_current is false, the case's current outcome can include later
    admissions. Role presence means a retained response. Absence discloses neither
    configuration nor case existence.
    """

    case_id: UUID
    admission_id: UUID
    run_id: str
    admission_current: bool
    native_status: Literal[
        "reserved", "candidate", "accepted", "rejected", "partial", "incomplete", "unknown", "cancelled"
    ]
    reason_code: str | None = Field(max_length=64)
    deadline: datetime
    deadline_elapsed: bool
    slot_encumbered: bool
    constructor_present: bool
    constructor_adopted: bool
    verifier_present: bool
    verifier_adopted: bool
    candidate_present: bool
    verdict_present: bool
    native_disposition: Literal["accepted", "rejected", "partial", "incomplete"] | None
    external_disposition: Literal["accepted", "rejected", "partial", "incomplete", "not_assessed"] | None
    feedback_status: Literal["unassessed", "review_required", "hold", "rejected"]
    current_assessment_id: UUID | None
    current_decision_id: UUID | None


class OrbRunSnapshot(ClientContract):
    """Selected-run Orb evidence page with explicit capture and gap limits."""

    schema_version: Literal[1] = 1
    snapshot_at: datetime
    run: OrbRunSummary
    pattern: PatternReference
    workflow: LoomView | None = None
    capture: Literal["process_local", "durable_best_effort"]
    ledger_head_seq: int
    page_end_seq: int | None
    has_more: bool
    live_tail: Literal["ledger_poll"] = "ledger_poll"
    known_omissions: list[str]
    gaps: list[EvidenceGap]
    evidence: list[EvidenceItem]
    delegated_jobs: list[DelegatedJobSummary]
    bridge_preference: OrbBridgePreferenceSummary | None = None
    creation: OrbCreationSummary | None = None
    next_after_seq: int | None


class OrbEventEnvelope(ClientContract):
    """A bounded retained-evidence page, reset, or ledger-terminal settlement.

    ``after_seq`` names the requested retained cursor; ``cursor`` advances only
    through delivered evidence. Metadata-only updates may keep that cursor.
    A reset invalidates the cursor and requires a fresh selected-Run snapshot.
    """

    schema_version: Literal[1] = 1
    run_id: str
    kind: Literal["evidence", "reset", "settled"]
    after_seq: int = Field(ge=-1)
    cursor: int = Field(ge=-1)
    snapshot: OrbRunSnapshot


class CsrfClientContract(ClientContract):
    """Public double-submit names configured by the trusted Vessel."""

    cookie_name: str
    header_name: str


class AltarStatus(ClientContract):
    """Shared shell status independent of any one instrument."""

    pending_consents: int
    csrf: CsrfClientContract
