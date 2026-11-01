"""Content-free stderr records for one disposable operator Core generation.

These observations disappear with their process. They are neither a trace store
nor authority over the Run ledger or the result sent through stdout.
"""

from __future__ import annotations

import fcntl
import os
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, AwareDatetime, Field

from lychd.compositions.reach.operator_wire import ReachWorkerStatus, strict_json
from lychd.compositions.reach.schemas import ReachReason, Record

MAX_DIAGNOSTIC_BYTES = 2048


def write_diagnostic_line(raw: bytes, *, descriptor: int = 2) -> None:
    """Attempt one atomic nonblocking pipe write; drop when the reader cannot keep up."""
    if len(raw) > MAX_DIAGNOSTIC_BYTES:
        return
    try:
        flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        try:
            if len(raw) > os.fpathconf(descriptor, "PC_PIPE_BUF"):
                return
            fcntl.fcntl(descriptor, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            os.write(descriptor, raw)
        finally:
            fcntl.fcntl(descriptor, fcntl.F_SETFL, flags)
    except (OSError, ValueError):
        return


def _uuid(value: str) -> str:
    if str(UUID(value)) != value:
        msg = "diagnostic_identity"
        raise ValueError(msg)
    return value


type DiagnosticUuid = Annotated[str, Field(max_length=36), AfterValidator(_uuid)]
type DiagnosticId = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9:_-]+$")]
type DiagnosticCode = Literal[
    "conversation_output",
    "conversation_checkpoint",
    "conversation_fresh_state",
    "conversation_grant",
    "model_unavailable",
    "model_timeout",
    "model_refused",
    "model_protocol",
    "model_failed",
]
type DiagnosticStage = Literal["execute", "evidence_flush", "result_lookup", "result_validation"]
type DiagnosticReason = (
    ReachReason | Literal["run_missing", "run_incomplete", "result_binding", "run_timeout", "run_failed"]
)
type DiagnosticRunStatus = Literal[
    "queued",
    "running",
    "awaiting_hardware",
    "awaiting_consent",
    "awaiting_delegate",
    "awaiting_peer",
    "cancelling",
    "done",
    "failed",
    "cancelled",
]


class FailedNodeDiagnostic(Record):
    """Identity of the latest retained NODE only when its actual phase is failed."""

    event_id: DiagnosticUuid
    seq: int = Field(ge=0, le=2**63 - 1)
    node: DiagnosticId
    occurrence_id: DiagnosticUuid
    phase: Literal["failed"] = "failed"


class ReachRunDiagnostic(Record):
    """One strictly allowlisted observation of an admitted Run's operator result."""

    schema_version: Literal[1] = 1
    kind: Literal["reach_run_diagnostic"] = "reach_run_diagnostic"
    producer: Literal["reach_core"] = "reach_core"
    observed_at: AwareDatetime
    generation: DiagnosticUuid
    request_id: DiagnosticUuid | None
    run_id: DiagnosticUuid
    status: ReachWorkerStatus
    reason: DiagnosticReason | None = None
    stage: DiagnosticStage
    run_status: DiagnosticRunStatus | None = None
    capture: Literal["process_local"] = "process_local"
    evidence: Literal["flushed", "unavailable"]
    failure_code: DiagnosticCode | None = None
    failed_node: FailedNodeDiagnostic | None = None


def diagnostic_bytes(value: ReachRunDiagnostic) -> bytes:
    """Serialize one bounded line, never a provider or exception payload."""
    raw = value.model_dump_json().encode("ascii") + b"\n"
    if len(raw) > MAX_DIAGNOSTIC_BYTES:
        msg = "diagnostic_limit"
        raise ValueError(msg)
    return raw


def parse_diagnostic(raw: bytes) -> ReachRunDiagnostic:
    """Reject duplicate keys, excess bytes and every field outside the record."""
    if len(raw) > MAX_DIAGNOSTIC_BYTES:
        msg = "diagnostic_limit"
        raise ValueError(msg)
    strict_json(raw)
    return ReachRunDiagnostic.model_validate_json(raw)
