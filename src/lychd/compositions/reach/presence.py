"""Pure presence preparation and bounded model decisions, without scheduler or delivery.

A tick is inert intent for one exact destination. The host must independently own
durable attempt custody, current authority, model execution and publication. This
gate fabricates no user/bot event, schedules no work and retains no state.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta
from hashlib import sha256
from typing import Literal, NoReturn, Self
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, Field, field_validator, model_validator

from lychd.compositions.reach.schemas import PolicyDigest, ReachId, Record, require_aware

_TICK_NAMESPACE = UUID("38571b6f-0056-52fb-85fd-dcf3d8b67b09")
_MAX_TICK_LIFETIME = timedelta(hours=1)
_MAX_OUTPUT_WIRE_CHARS = 128_000
_ASCII_CONTROL_LIMIT = 32
_SCHEDULE_ID_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$"


def _content(value: str) -> str:
    if not value.strip():
        msg = "Presence text requires nonempty content."
        raise ValueError(msg)
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError as error:
        msg = "Presence text requires valid Unicode."
        raise ValueError(msg) from error
    if any(ord(character) < _ASCII_CONTROL_LIMIT and character not in "\t\n\r" for character in value):
        msg = "Presence text cannot contain control characters."
        raise ValueError(msg)
    return value


class ProactivePolicy(Record):
    """Explicit opt-in for one stable schedule and one exact opaque Reach target."""

    schema_version: Literal[1] = 1
    account_id: ReachId
    agent_subject_id: ReachId
    space_id: ReachId
    conversation_id: ReachId
    schedule_id: str = Field(min_length=1, max_length=64, pattern=_SCHEDULE_ID_PATTERN)
    topic: str = Field(min_length=1, max_length=1000, repr=False)
    timezone: str = Field(default="UTC", min_length=1, max_length=255)
    local_hour: int = Field(ge=0, le=23)
    cooldown_seconds: int = Field(default=86400, ge=86400, le=604800)
    enabled: bool = False

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            msg = "Presence requires a known IANA timezone."
            raise ValueError(msg) from error
        return value

    @field_validator("topic")
    @classmethod
    def valid_topic(cls, value: str) -> str:
        return _content(value)

    @property
    def digest(self) -> str:
        """Bind configuration separately from the stable daily attempt identity."""
        wire = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(wire.encode("utf-8")).hexdigest()


class PresenceTick(Record):
    """One expiring preparation; neither a Reach event nor permission to publish."""

    schema_version: Literal[1] = 1
    tick_id: ReachId
    policy_digest: PolicyDigest
    schedule_id: str = Field(min_length=1, max_length=64, pattern=_SCHEDULE_ID_PATTERN)
    account_id: ReachId
    agent_subject_id: ReachId
    space_id: ReachId
    conversation_id: ReachId
    topic: str = Field(min_length=1, max_length=1000, repr=False)
    local_date: date
    scheduled_at: AwareDatetime
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def finite_utc_window(self) -> Self:
        if self.scheduled_at.utcoffset() != timedelta(0) or self.expires_at.utcoffset() != timedelta(0):
            msg = "Presence tick clocks must be UTC."
            raise ValueError(msg)
        if not timedelta(0) < self.expires_at - self.scheduled_at <= _MAX_TICK_LIFETIME:
            msg = "Presence tick lifetime must be positive and at most one hour."
            raise ValueError(msg)
        return self


def plan_presence(policy: ProactivePolicy, now: datetime, last_attempt: datetime | None = None) -> PresenceTick | None:
    """Prepare only within today's selected local hour after an elapsed UTC cooldown.

    A repeated DST hour uses its first occurrence and expires before its repeated
    part. A partially skipped hour begins at its first existing instant. A fully
    skipped hour yields no tick. Configuration edits do not reset the daily key;
    the host must persist attempts under that key before any external effect.
    """
    require_aware(now)
    if last_attempt is not None:
        require_aware(last_attempt)
    policy = ProactivePolicy.model_validate(policy.model_dump(mode="python"))
    if not policy.enabled:
        return None
    now_utc = now.astimezone(UTC)
    if last_attempt is not None and now_utc - last_attempt.astimezone(UTC) < timedelta(seconds=policy.cooldown_seconds):
        return None
    zone = ZoneInfo(policy.timezone)
    local_now = now_utc.astimezone(zone)
    if local_now.hour != policy.local_hour:
        return None
    local_start = datetime.combine(local_now.date(), time(hour=policy.local_hour), tzinfo=zone)
    scheduled_at = local_start.astimezone(UTC)
    actual_start = scheduled_at.astimezone(zone)
    if actual_start.date() != local_now.date() or actual_start.hour != policy.local_hour:
        return None
    local_end = local_start + _MAX_TICK_LIFETIME
    expires_at = min(scheduled_at + _MAX_TICK_LIFETIME, local_end.astimezone(UTC))
    if not scheduled_at <= now_utc < expires_at:
        return None
    identity = json.dumps(
        [
            policy.account_id,
            policy.agent_subject_id,
            policy.space_id,
            policy.conversation_id,
            policy.schedule_id,
            local_now.date().isoformat(),
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return PresenceTick(
        tick_id=str(uuid5(_TICK_NAMESPACE, identity)),
        policy_digest=policy.digest,
        schedule_id=policy.schedule_id,
        account_id=policy.account_id,
        agent_subject_id=policy.agent_subject_id,
        space_id=policy.space_id,
        conversation_id=policy.conversation_id,
        topic=policy.topic,
        local_date=local_now.date(),
        scheduled_at=scheduled_at,
        expires_at=expires_at,
    )


class PresenceOutput(Record):
    """A bounded reason to skip or inert candidate text; no tools or publication."""

    kind: Literal["skip", "candidate"]
    text: str = Field(min_length=1, max_length=8000, repr=False)

    @field_validator("text")
    @classmethod
    def valid_text(cls, value: str) -> str:
        return _content(value)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = "Presence output cannot contain duplicate JSON keys."
            raise ValueError(msg)
        result[key] = value
    return result


def _invalid_constant(_value: str) -> NoReturn:
    msg = "Presence output requires standard JSON values."
    raise ValueError(msg)


def parse_presence_output(raw: str) -> PresenceOutput:
    """Parse exactly one strict decision object, rejecting ambiguous or tool-shaped data."""
    if type(raw) is not str or len(raw) > _MAX_OUTPUT_WIRE_CHARS:
        msg = "Presence output requires a bounded JSON string."
        raise ValueError(msg)
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except (json.JSONDecodeError, RecursionError) as error:
        msg = "Presence output requires one valid JSON object."
        raise ValueError(msg) from error
    return PresenceOutput.model_validate(value)
