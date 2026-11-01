"""Closed operator research catalogue and private source/progress frames.

The catalogue is a local operator assertion about exact public locators. A model
selects IDs, never network destinations, credentials or acquisition mechanisms.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from hashlib import sha256
from ipaddress import ip_address
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import AfterValidator, AwareDatetime, Field, field_validator, model_validator

from lychd.compositions.reach.operator_trace import TraceCorrelation
from lychd.compositions.reach.schemas import PolicyDigest, ReachEvent, ReachId, Record

type ResearchId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")]
type ResearchCallId = Annotated[str, Field(pattern=r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")]
type SourceId = Annotated[str, Field(pattern=r"^(?:web:[a-z][a-z0-9_]{0,31}|doc:[A-Za-z0-9_./-]{1,200})$")]

MAX_PUBLIC_URL_CHARS = 4096
ASCII_SPACE = 32
ASCII_DELETE = 127
MAX_SOURCE_FOCUS_CHARS = 80


def public_catalogue_url(value: str) -> str:
    """Check locator shape only; current destination and disclosure checks remain mandatory."""
    parsed = urlsplit(value)
    if (
        len(value) > MAX_PUBLIC_URL_CHARS
        or any(not ASCII_SPACE < ord(char) < ASCII_DELETE for char in value)
        or parsed.scheme != "https"
        or not parsed.hostname
        or "." not in parsed.hostname
        or parsed.netloc != parsed.hostname
        or parsed.query
        or parsed.fragment
        or "\\" in value
    ):
        msg = "research_url"
        raise ValueError(msg)
    return value


class ResearchSource(Record):
    id: ResearchId
    title: str = Field(min_length=1, max_length=120)
    url: Annotated[str, AfterValidator(public_catalogue_url)]
    focus: tuple[str, ...] = Field(default=(), max_length=4)

    @field_validator("focus")
    @classmethod
    def bounded_focus(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not 1 <= len(item) <= MAX_SOURCE_FOCUS_CHARS or not item.strip() for item in values):
            msg = "research_focus"
            raise ValueError(msg)
        return values


class ResearchOptions(Record):
    enabled: bool = False
    sources: tuple[ResearchSource, ...] = Field(default=(), max_length=8)

    @model_validator(mode="after")
    def unique_sources(self) -> Self:
        if (self.sources and not self.enabled) or len({item.id for item in self.sources}) != len(self.sources):
            msg = "research_catalogue"
            raise ValueError(msg)
        return self


class ResearchRuntimeProfile(Record):
    """Separate standing operator authority, never a Discord Principal or native consent."""

    source_kind: Literal["operator_public_catalogue"]
    public_catalogue_authorized: Literal[True]
    policy_revision: int = Field(ge=1)
    revocation_generation: int = Field(ge=0)
    expires_at: AwareDatetime
    catalogue: ResearchOptions
    allowed_subject_ids: tuple[ReachId, ...] = Field(min_length=1, max_length=16)
    allowed_channel_ids: tuple[ReachId, ...] = Field(default=(), max_length=16)
    allowed_dm_user_ids: tuple[ReachId, ...] = Field(default=(), max_length=8)
    resolver_address: str
    resolver_custody_statement: str = Field(min_length=10, max_length=300)
    max_attempts: int = Field(default=64, ge=1, le=1000)
    max_connects: int = Field(default=192, ge=3, le=3000)
    max_transmissions: int = Field(default=32768, ge=512, le=512000)
    max_wire_bytes: int = Field(default=67108864, ge=1048576, le=1073741824)

    @field_validator("resolver_address")
    @classmethod
    def numeric_resolver(cls, value: str) -> str:
        if str(ip_address(value)) != value:
            msg = "research_resolver"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def explicit_enabled_catalogue(self) -> Self:
        if not self.catalogue.enabled or not self.catalogue.sources:
            msg = "research_runtime_catalogue"
            raise ValueError(msg)
        return self

    @property
    def digest(self) -> str:
        raw = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(raw.encode()).hexdigest()


class ResearchJob(Record):
    """Local metadata only; the network request contains the catalogue locator alone."""

    event_id: ReachId
    subject_id: ReachId
    conversation_id: ReachId
    direct: bool
    source_ids: tuple[ResearchId, ...] = Field(min_length=1, max_length=2)


class SourceReadResult(Record):
    id: SourceId
    title: str = Field(min_length=1, max_length=120)
    url: Annotated[str, AfterValidator(public_catalogue_url)]
    status: Literal["ok", "unavailable", "refused"]
    text: str = Field(default="", max_length=4000, repr=False)
    source_digest: PolicyDigest | None = None
    text_digest: PolicyDigest | None = None
    source_chars: int = Field(default=0, ge=0)
    excerpt_start: int = Field(default=0, ge=0)
    truncated: bool = False
    receipt_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    reason: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,63}$")
    http_status: int | None = Field(default=None, ge=100, le=599)

    @model_validator(mode="after")
    def evidence_shape(self) -> Self:
        if self.status == "ok":
            if (
                not self.text.strip()
                or self.text_digest != sha256(self.text.encode()).hexdigest()
                or self.source_digest is None
                or self.reason is not None
                or self.excerpt_start + len(self.text) > self.source_chars
            ):
                msg = "research_evidence"
                raise ValueError(msg)
        elif self.text or self.source_digest is not None or self.text_digest is not None or self.reason is None:
            msg = "research_failure_body"
            raise ValueError(msg)
        return self


class OperatorResearchRequest(Record):
    kind: Literal["research_request"] = "research_request"
    call_id: ResearchCallId
    request_id: ReachId
    binding_digest: PolicyDigest
    event: ReachEvent = Field(repr=False)
    plan: str = Field(min_length=1, max_length=500, repr=False)
    source_ids: tuple[ResearchId, ...] = Field(default=(), max_length=2)
    correlation: TraceCorrelation | None = None


class OperatorResearchResponse(Record):
    kind: Literal["research_response"] = "research_response"
    call_id: ResearchCallId
    request_id: ReachId
    binding_digest: PolicyDigest
    status: Literal["ok", "refused"]
    sources: tuple[SourceReadResult, ...] = Field(default=(), max_length=2, repr=False)
    reason: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,63}$")

    @model_validator(mode="after")
    def coherent_response(self) -> Self:
        if (self.status == "ok") != (self.reason is None) or (self.status != "ok" and self.sources):
            msg = "research_response"
            raise ValueError(msg)
        return self


class ReachResearchProgress(Record):
    kind: Literal["progress"] = "progress"
    call_id: ResearchCallId
    request_id: ReachId
    binding_digest: PolicyDigest
    text: str = Field(min_length=1, max_length=500, repr=False)


class ReachResearchAcknowledgement(Record):
    kind: Literal["progress_ack"] = "progress_ack"
    call_id: ResearchCallId
    request_id: ReachId
    binding_digest: PolicyDigest
    accepted: bool


type ResearchRelay = Callable[[OperatorResearchRequest], Awaitable[OperatorResearchResponse]]
