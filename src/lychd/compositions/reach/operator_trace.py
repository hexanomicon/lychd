"""Closed structural observations for the isolated operator's private diagnostic archive.

These records witness capture, never Run truth, delivery authority or hidden reasoning.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from datetime import UTC, datetime
from json import JSONDecodeError
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, Field, ValidationError

from lychd.compositions.reach.operator_diagnostics import DiagnosticId, DiagnosticUuid
from lychd.compositions.reach.schemas import PolicyDigest, ReachReviewIssue, Record

MAX_TRACE_BYTES = 2048

type TraceName = Literal[
    "session_started",
    "session_finished",
    "gateway",
    "capture_gap",
    "request_received",
    "request_finished",
    "admission",
    "history",
    "acknowledgement",
    "research_plan",
    "addressing",
    "interpretation",
    "checkback",
    "checkback_control",
    "reference_hints",
    "correction",
    "delivery",
    "expression",
    "run_started",
    "run_finished",
    "native_node",
    "native_status",
    "native_dispatch",
    "native_transition",
    "native_done",
    "model_call",
    "model_http",
    "research_call",
    "source_read",
    "child_diagnostic",
]
type TraceStatus = Literal[
    "started",
    "ok",
    "error",
    "failed",
    "refused",
    "unavailable",
    "unknown",
    "cancelled",
    "observed",
    "entered",
    "settled",
    "waiting",
    "succeeded",
    "rejected",
    "queued",
    "running",
    "done",
    "awaiting_hardware",
    "awaiting_consent",
    "awaiting_delegate",
    "awaiting_peer",
    "cancelling",
    "docs",
    "context",
    "conversation",
    "need_context",
    "clarify",
    "empty",
    "addressed",
    "ignore",
]
type TraceCode = Literal[
    "timeout",
    "invalid_json",
    "validation_error",
    "io_error",
    "value_error",
    "type_error",
    "runtime_error",
    "unexpected_error",
    "model_unavailable",
    "model_timeout",
    "model_refused",
    "model_protocol",
    "model_failed",
    "fetch_protocol",
    "source_unavailable",
    "worker_unavailable",
    "capture_unavailable",
    "queue_full",
    "protocol_error",
    "run_failed",
    "run_incomplete",
    "result_binding",
    "run_timeout",
    "run_missing",
    "permission_denied",
    "busy",
    "duplicate",
    "budget",
    "http_error",
    "generation_closed",
]
type PlatformTraceId = Annotated[str, Field(pattern=r"^[1-9][0-9]{0,19}$")]


class TraceCorrelation(Record):
    """Explicit Core attempt identities; correlation never grants authority."""

    generation: DiagnosticUuid
    request_id: DiagnosticUuid
    run_id: DiagnosticUuid
    occurrence_id: DiagnosticUuid | None = None
    step_id: DiagnosticUuid | None = None


class ReachTraceEvent(Record):
    """Allowlisted metadata only; producer custody is checked again by the receiver."""

    kind: Literal["reach_trace"] = "reach_trace"
    schema_version: Literal[1] = 1
    event_id: DiagnosticUuid = Field(default_factory=lambda: str(uuid4()))
    observed_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    producer: Literal["host", "core", "edge"]
    trace_seq: int = Field(default=0, ge=0, le=2**63 - 1)
    name: TraceName
    status: TraceStatus = "observed"
    code: TraceCode | None = None
    generation: DiagnosticUuid | None = None
    request_id: DiagnosticUuid | None = None
    run_id: DiagnosticUuid | None = None
    call_id: DiagnosticUuid | None = None
    pattern_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    pattern_revision: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    platform: Literal["discord", "telegram"] | None = None
    platform_event_id: PlatformTraceId | None = None
    conversation_id: PlatformTraceId | None = None
    context_round: int | None = Field(default=None, ge=0, le=2)
    node: DiagnosticId | None = None
    occurrence_id: DiagnosticUuid | None = None
    step_id: DiagnosticUuid | None = None
    native_event_id: DiagnosticUuid | None = None
    native_seq: int | None = Field(default=None, ge=0, le=2**63 - 1)
    source_id: str | None = Field(default=None, pattern=r"^(?:web:[a-z][a-z0-9_]{0,31}|doc:[A-Za-z0-9_./-]{1,200})$")
    excerpt_start: int | None = Field(default=None, ge=0)
    excerpt_chars: int | None = Field(default=None, ge=0, le=16_000)
    source_digest: PolicyDigest | None = None
    text_digest: PolicyDigest | None = None
    issue_codes: tuple[ReachReviewIssue, ...] | None = Field(default=None, max_length=4)
    request_digest: PolicyDigest | None = None
    evidence_digest: PolicyDigest | None = None
    candidate_digest: PolicyDigest | None = None
    objective_digest: PolicyDigest | None = None
    reference_digest: PolicyDigest | None = None
    reference_count: int | None = Field(default=None, ge=0, le=3)
    reference_version: Literal["anchor-order-v1", "anchor-order-v2"] | None = None
    runtime_claim_count: int | None = Field(default=None, ge=0, le=4)
    runtime_claim_digest: PolicyDigest | None = None
    guard_rule: (
        Literal["unchanged_explanation", "runtime_evidence_authority", "misbound_reference_clarification"] | None
    ) = None
    guard_version: (
        Literal["unchanged-explanation-v1", "runtime-evidence-authority-v1", "misbound-reference-clarification-v1"]
        | None
    ) = None
    guard_status: (
        Literal[
            "not_applicable",
            "clear",
            "unchanged_requested_transformation",
            "current_runtime_claim_without_observation",
            "no_current_runtime_claim_observed",
            "unrequested_target_clarification",
        ]
        | None
    ) = None
    effective_verdict: Literal["accept", "revise", "needs_evidence"] | None = None
    goal_count: int | None = Field(default=None, ge=0, le=8)
    goal_coverage: tuple[Literal["complete", "missing", "unsupported"], ...] | None = Field(default=None, max_length=8)
    verdict: Literal["accept", "revise", "needs_evidence", "addressed", "ignore"] | None = None
    attempt: int | None = Field(default=None, ge=0, le=1)
    operation: (
        Literal[
            "probe",
            "generate",
            "health",
            "inventory",
            "completion",
            "plan",
            "fetch",
            "synthesis",
            "ack",
            "final",
            "reaction",
            "gif",
            "history",
            "lookup",
            "validation",
            "flush",
            "execute",
        ]
        | None
    ) = None
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)
    http_status: int | None = Field(default=None, ge=100, le=599)
    count: int | None = Field(default=None, ge=0, le=2**31 - 1)
    chars: int | None = Field(default=None, ge=0, le=2**31 - 1)
    bytes_count: int | None = Field(default=None, ge=0, le=2**31 - 1)
    part: int | None = Field(default=None, ge=0, le=1000)
    parts: int | None = Field(default=None, ge=0, le=1000)
    remote_id: PlatformTraceId | None = None
    truncated: bool = False


type TraceSink = Callable[[ReachTraceEvent], None]


def uuid_or_none(value: str | None) -> str | None:
    """Withhold generic caller labels that could contain private material."""
    try:
        return value if value is not None and str(UUID(value)) == value else None
    except ValueError:
        return None


def platform_id_or_none(value: str | None) -> str | None:
    """Retain only numeric platform identifiers, never arbitrary foreign labels."""
    return value if value is not None and re.fullmatch(r"[1-9][0-9]{0,19}", value) else None


def error_code(error: BaseException) -> TraceCode:  # noqa: PLR0911 - closed failure categories
    """Classify failure without rendering its text, class name or validation input."""
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, JSONDecodeError):
        return "invalid_json"
    if isinstance(error, ValidationError):
        return "validation_error"
    if isinstance(error, OSError):
        return "io_error"
    if isinstance(error, TypeError):
        return "type_error"
    if isinstance(error, ValueError):
        return "value_error"
    if isinstance(error, RuntimeError):
        return "runtime_error"
    return "unexpected_error"


class TraceEmitter:
    """Sequence attempted structural capture without giving its sink execution authority."""

    def __init__(self, producer: Literal["host", "core", "edge"], sink: TraceSink | None) -> None:
        """Bind one producer and its non-authoritative observation sink."""
        self.producer: Literal["host", "core", "edge"] = producer
        self.sink, self.sequence = sink, 0

    def __call__(self, event: ReachTraceEvent) -> None:
        self.sequence += 1
        if self.sink is None or event.producer != self.producer:
            return
        try:
            self.sink(event.model_copy(update={"trace_seq": self.sequence}))
        except (Exception, asyncio.CancelledError):  # noqa: BLE001 - observation never changes execution or delivery
            return

    def record(self, name: TraceName, **fields: Any) -> None:
        """Reject unknown fields locally rather than emitting unstructured diagnostics."""
        try:
            event = ReachTraceEvent(producer=self.producer, name=name, **fields)
        except (ValueError, TypeError):
            return
        self(event)


def trace_bytes(event: ReachTraceEvent) -> bytes:
    """Emit one bounded line without empty fields or arbitrary extra metadata."""
    raw = event.model_dump_json(exclude_none=True).encode("ascii") + b"\n"
    if len(raw) > MAX_TRACE_BYTES:
        msg = "trace_limit"
        raise ValueError(msg)
    return raw
