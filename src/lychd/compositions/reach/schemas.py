"""Bounded Reach preparation values; identity observations never confer grants."""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from typing import Annotated, Literal, Self
from unicodedata import category

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


def _identifier(value: str) -> str:
    if any(character.isspace() or category(character) in {"Cc", "Cf", "Cs"} for character in value):
        msg = "Reach identity cannot contain whitespace or control characters."
        raise ValueError(msg)
    return value


type ReachId = Annotated[str, Field(strict=True, min_length=1, max_length=128), AfterValidator(_identifier)]
type ReachPlatform = Annotated[str, Field(strict=True, pattern=r"^[a-z][a-z0-9-]{0,31}$")]
type ReachAction = Literal["answer_docs", "summarize_context"]
type ReachTrigger = Literal["mention", "command"]
type PolicyDigest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
type ReachReason = Literal[
    "prepared",
    "wrong_platform",
    "wrong_account",
    "wrong_space",
    "conversation_not_allowed",
    "self_event",
    "automated_subject",
    "trigger_not_allowed",
    "missing_agent_mention",
    "action_not_supported",
    "subject_not_allowed",
    "action_not_allowed",
    "event_from_future",
    "event_expired",
    "question_empty",
    "question_too_large",
    "question_invalid",
    "context_disabled",
]


def _unique(values: tuple[object, ...], label: str) -> None:
    if len(values) != len(set(values)):
        msg = f"Duplicate {label} are not permitted."
        raise ValueError(msg)


class Record(BaseModel):
    """Strict immutable local values, with hostile input omitted from errors."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, hide_input_in_errors=True)

    @field_validator("schema_version", mode="before", check_fields=False)
    @classmethod
    def original_schema_version(cls, value: object) -> object:
        if type(value) is not int:
            msg = "Schema revision must be an original integer."
            raise ValueError(msg)
        return value


class ReachRule(Record):
    """First matching subject-or-group selector decides permitted preparation actions."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    subject_ids: tuple[ReachId, ...] = Field(default=(), max_length=100)
    group_ids: tuple[ReachId, ...] = Field(default=(), max_length=100)
    actions: tuple[ReachAction, ...] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def selectors(self) -> Self:
        if not self.subject_ids and not self.group_ids:
            msg = "A Reach rule requires an explicit subject or group selector."
            raise ValueError(msg)
        _unique(self.subject_ids, "subject ids")
        _unique(self.group_ids, "group ids")
        _unique(self.actions, "actions")
        return self


class ReachPolicy(Record):
    """Preparation policy only; selecting a person or action grants no external effect."""

    schema_version: Literal[1] = 1
    platform: ReachPlatform
    account_id: ReachId
    agent_subject_id: ReachId
    space_id: ReachId | None = None
    allowed_conversation_ids: tuple[ReachId, ...] = Field(min_length=1, max_length=100)
    rules: tuple[ReachRule, ...] = Field(min_length=1, max_length=100)
    allowed_triggers: tuple[ReachTrigger, ...] = Field(default=("mention", "command"), min_length=1, max_length=2)
    event_ttl_seconds: int = Field(default=300, ge=1, le=3600)
    max_question_chars: int = Field(default=2000, ge=1, le=2000)
    context_message_limit: int = Field(default=0, ge=0, le=50)
    context_max_age_seconds: int = Field(default=600, ge=1, le=3600)

    @model_validator(mode="after")
    def unique_configuration(self) -> Self:
        _unique(self.allowed_conversation_ids, "conversation ids")
        _unique(self.allowed_triggers, "triggers")
        _unique(tuple(rule.name for rule in self.rules), "rule names")
        return self

    @property
    def digest(self) -> str:
        """Bind the complete ordered policy without reading configuration again."""
        wire = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(wire.encode("utf-8")).hexdigest()


class ReachEvent(Record):
    """Transient normalized observation from a separately trusted adapter, never a grant."""

    platform: ReachPlatform
    account_id: ReachId
    event_id: ReachId
    space_id: ReachId | None = None
    conversation_id: ReachId
    subject_id: ReachId
    group_ids: tuple[ReachId, ...] = Field(default=(), max_length=250)
    is_automated: bool = False
    mention_subject_ids: tuple[ReachId, ...] = Field(default=(), max_length=100)
    trigger: Literal["mention", "command", "message"]
    action: str = Field(min_length=1, max_length=64)
    question: str = Field(max_length=8192, repr=False)
    occurred_at: AwareDatetime

    @model_validator(mode="after")
    def unique_observations(self) -> Self:
        _unique(self.group_ids, "observed group ids")
        _unique(self.mention_subject_ids, "observed mention ids")
        return self


class ReachEventIdentity(Record):
    """Exact observed place and event identity, excluding all message content."""

    platform: ReachPlatform
    account_id: ReachId
    event_id: ReachId
    space_id: ReachId | None = None
    conversation_id: ReachId
    subject_id: ReachId
    trigger: Literal["mention", "command", "message"]

    @classmethod
    def from_event(cls, event: ReachEvent) -> Self:
        return cls(**{name: getattr(event, name) for name in cls.model_fields})


class PreparedReachTurn(Record):
    """Accepted preparation data, without a ReachTurn, cognition or delivery claim."""

    policy_digest: PolicyDigest
    identity: ReachEventIdentity
    event: ReachEvent = Field(repr=False)
    rule_name: str
    action: ReachAction
    prepared_at: AwareDatetime
    expires_at: AwareDatetime


class ReachDecision(Record):
    """Content-free refusal or one bounded preparation; neither authorizes a send."""

    allowed: bool
    reason: ReachReason
    identity: ReachEventIdentity
    policy_digest: PolicyDigest
    evaluated_at: AwareDatetime
    prepared: PreparedReachTurn | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def coherent_result(self) -> Self:
        if self.allowed != (self.reason == "prepared") or self.allowed != (self.prepared is not None):
            msg = "Reach decision status and preparation disagree."
            raise ValueError(msg)
        if self.prepared is not None and (
            self.prepared.identity != self.identity
            or self.prepared.policy_digest != self.policy_digest
            or self.prepared.prepared_at != self.evaluated_at
            or self.prepared.identity != ReachEventIdentity.from_event(self.prepared.event)
        ):
            msg = "Reach decision does not bind its exact preparation."
            raise ValueError(msg)
        return self


class ReachPreparationState(Record):
    """JSON-safe continuation bound to one admitted Run, session, event and policy."""

    model_config = ConfigDict(
        extra="forbid", frozen=False, strict=True, validate_assignment=True, hide_input_in_errors=True
    )

    schema_version: Literal[1] = 1
    run_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    prepared: PreparedReachTurn = Field(repr=False)
    result: ReachDecision | None = Field(default=None, repr=False)


def require_aware(value: datetime) -> None:
    """Require an explicit clock instant rather than guessing the host timezone."""
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "Reach requires a timezone-aware clock."
        raise ValueError(msg)
