"""Bounded, credential-free JSON lines for the disposable operator development profile."""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AfterValidator, AwareDatetime, Field

from lychd.compositions.reach.schemas import PolicyDigest, ReachEvent, ReachId, Record

MAX_WIRE_BYTES = 65_536
type ReachWorkerStatus = Literal["docs", "context", "conversation", "empty", "refused", "error"]


def _uuid(value: str) -> str:
    if str(UUID(value)) != value:
        msg = "generation"
        raise ValueError(msg)
    return value


class ReachHistoryEntry(Record):
    """One attributed excerpt; authorization remains the receiving policy's decision."""

    subject_id: ReachId
    subject_label: str | None = Field(default=None, min_length=1, max_length=80)
    event_id: ReachId
    conversation_id: ReachId
    text: str = Field(max_length=2000, repr=False)
    occurred_at: AwareDatetime


class ReachWorkerRequest(Record):
    """One normalized event and its explicitly selected, bounded history."""

    kind: Literal["request"] = "request"
    request_id: ReachId
    event: ReachEvent = Field(repr=False)
    history: tuple[ReachHistoryEntry, ...] = Field(default=(), max_length=50, repr=False)


class ReachWorkerResult(Record):
    """One process-generation result; this is neither delivery nor durable truth."""

    kind: Literal["result"] = "result"
    request_id: ReachId
    status: ReachWorkerStatus
    text: str = Field(default="", max_length=1900, repr=False)
    run_id: ReachId | None = None
    policy_digest: PolicyDigest
    corpus_digest: PolicyDigest
    model_binding_digest: PolicyDigest | None = None
    reason: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")] | None = None


class ReachWorkerReady(Record):
    """Announce a fresh, nonrecoverable generation before accepting events."""

    kind: Literal["ready"] = "ready"
    generation: Annotated[str, AfterValidator(_uuid)]
    started_at: AwareDatetime
    policy_digest: PolicyDigest
    corpus_digest: PolicyDigest
    model_binding_digest: PolicyDigest | None = None


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            msg = "duplicate_key"
            raise ValueError(msg)
        result[key] = value
    return result


def strict_json(raw: bytes) -> Any:
    """Reject duplicate keys, nonfinite values and oversized UTF-8 input."""
    if len(raw) > MAX_WIRE_BYTES:
        msg = "input_limit"
        raise ValueError(msg)

    def invalid_constant(_value: str) -> Any:
        msg = "invalid_json"
        raise ValueError(msg)

    return json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique, parse_constant=invalid_constant)


def parse_request_line(raw: bytes) -> ReachWorkerRequest:
    """Validate JSON mode after detecting duplicate keys at every depth."""
    strict_json(raw)
    return ReachWorkerRequest.model_validate_json(raw)


def protocol_bytes(value: ReachWorkerReady | ReachWorkerRequest | ReachWorkerResult) -> bytes:
    """Produce exactly one bounded newline-terminated protocol value."""
    raw = value.model_dump_json().encode("utf-8") + b"\n"
    if len(raw) > MAX_WIRE_BYTES:
        msg = "output_limit"
        raise ValueError(msg)
    return raw
