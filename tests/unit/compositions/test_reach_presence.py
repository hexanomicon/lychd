"""Independent clocks, strict identities and inert decisions for presence preparation."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from lychd.compositions.reach.presence import (
    PresenceOutput,
    PresenceTick,
    ProactivePolicy,
    parse_presence_output,
    plan_presence,
)

NOW = datetime(2026, 11, 1, 10, 30, tzinfo=UTC)


def policy(**changes: Any) -> ProactivePolicy:
    values: dict[str, Any] = {
        "account_id": "account:opaque",
        "agent_subject_id": "agent:opaque",
        "space_id": "space:opaque",
        "conversation_id": "conversation:opaque",
        "schedule_id": "morning-presence",
        "topic": "One useful update about the agreed topic.",
        "local_hour": 10,
        "enabled": True,
    }
    return ProactivePolicy(**(values | changes))


def test_policy_requires_explicit_enablement_and_is_strict_frozen() -> None:
    configured = policy(enabled=False)
    defaults = configured.model_dump(exclude={"enabled", "timezone", "cooldown_seconds"})
    disabled = ProactivePolicy.model_validate(defaults)
    assert disabled.enabled is False
    assert disabled.timezone == "UTC"
    assert disabled.cooldown_seconds == 86400
    assert plan_presence(disabled, NOW) is None
    with pytest.raises(ValidationError):
        disabled.enabled = True
    assert ProactivePolicy.model_validate_json(disabled.model_dump_json()) == disabled
    assert "One useful update" not in repr(disabled)


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": True},
        {"schema_version": 2},
        {"enabled": 1},
        {"local_hour": True},
        {"local_hour": -1},
        {"local_hour": 24},
        {"local_hour": "10"},
        {"cooldown_seconds": 86399},
        {"cooldown_seconds": 604801},
        {"cooldown_seconds": True},
        {"timezone": "Unknown/Nowhere"},
        {"timezone": "../UTC"},
        {"timezone": ""},
        {"schedule_id": ""},
        {"schedule_id": "a" * 65},
        {"schedule_id": "two schedules"},
        {"schedule_id": "unsafe/path"},
        {"topic": " "},
        {"topic": "a" * 1001},
        {"topic": "bad\x00"},
        {"account_id": 123},
        {"account_id": "has whitespace"},
        {"agent_subject_id": "bad\u202e"},
        {"space_id": None},
        {"conversation_id": ""},
        {"tools": ["send_message"]},
    ],
)
def test_policy_rejects_ambiguous_unbounded_or_unselected_values(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        policy(**changes)


def test_policy_accepts_boundaries_and_opaque_non_numeric_targets() -> None:
    configured = policy(local_hour=0, cooldown_seconds=604800, schedule_id="A" * 64, topic="x" * 1000)
    assert configured.account_id == "account:opaque"
    assert configured.space_id == "space:opaque"
    assert policy(local_hour=23).local_hour == 23


def test_tick_binds_exact_destination_and_one_utc_hour_without_fabricating_an_event() -> None:
    configured = policy()
    tick = plan_presence(configured, NOW)
    assert tick is not None
    assert tick.account_id == configured.account_id
    assert tick.agent_subject_id == configured.agent_subject_id
    assert tick.space_id == configured.space_id
    assert tick.conversation_id == configured.conversation_id
    assert tick.topic == configured.topic
    assert tick.policy_digest == configured.digest
    assert tick.local_date == date(2026, 11, 1)
    assert tick.scheduled_at == NOW.replace(minute=0)
    assert tick.expires_at == NOW.replace(hour=11, minute=0)
    assert tick.scheduled_at.tzinfo is UTC
    assert tick.expires_at.tzinfo is UTC
    assert UUID(tick.tick_id).version == 5
    assert PresenceTick.model_validate_json(tick.model_dump_json()) == tick
    assert not {"event", "event_id", "subject_id", "trigger", "is_automated"}.intersection(type(tick).model_fields)
    with pytest.raises(ValidationError):
        tick.topic = "changed"


def test_hour_window_includes_start_and_excludes_expiry_without_catchup() -> None:
    assert plan_presence(policy(), NOW.replace(minute=0)) is not None
    assert plan_presence(policy(), NOW.replace(minute=59, second=59, microsecond=999999)) is not None
    assert plan_presence(policy(), NOW.replace(hour=9, minute=59, second=59)) is None
    assert plan_presence(policy(), NOW.replace(hour=11, minute=0)) is None
    assert plan_presence(policy(), NOW.replace(hour=23)) is None


def test_tick_uses_local_date_across_utc_midnight() -> None:
    instant = datetime(2026, 11, 1, 23, 30, tzinfo=UTC)
    tick = plan_presence(policy(timezone="Asia/Tokyo", local_hour=8), instant)
    assert tick is not None
    assert tick.local_date == date(2026, 11, 2)
    assert tick.scheduled_at == instant.replace(minute=0)
    assert tick.expires_at == datetime(2026, 11, 2, tzinfo=UTC)
    assert (
        plan_presence(policy(timezone="Asia/Tokyo", local_hour=8), instant.astimezone(ZoneInfo("Asia/Tokyo"))) == tick
    )


def test_tick_identity_survives_policy_edits_and_changes_next_local_date() -> None:
    tick = plan_presence(policy(), NOW)
    assert tick is not None
    changed = plan_presence(
        policy(topic="A revised topic", timezone="Europe/Bratislava", local_hour=11, cooldown_seconds=172800), NOW
    )
    assert changed is not None
    assert changed.policy_digest != tick.policy_digest
    assert changed.tick_id == tick.tick_id
    later = plan_presence(policy(), NOW.replace(minute=59))
    assert later is not None
    assert later.tick_id == tick.tick_id
    tomorrow = plan_presence(policy(), NOW + timedelta(days=1))
    assert tomorrow is not None
    assert tomorrow.tick_id != tick.tick_id
    for key in ("schedule_id", "account_id", "agent_subject_id", "space_id", "conversation_id"):
        redirected = plan_presence(policy(**{key: "another"}), NOW)
        assert redirected is not None
        assert redirected.tick_id != tick.tick_id


def test_cooldown_counts_actual_elapsed_utc_time_and_refuses_future_attempts() -> None:
    assert plan_presence(policy(), NOW, NOW - timedelta(seconds=86400)) is not None
    assert plan_presence(policy(), NOW, NOW - timedelta(seconds=86399)) is None
    assert plan_presence(policy(), NOW, NOW + timedelta(seconds=1)) is None
    assert plan_presence(policy(cooldown_seconds=604800), NOW, NOW - timedelta(days=6)) is None
    assert plan_presence(policy(cooldown_seconds=604800), NOW, NOW - timedelta(days=7)) is not None


def test_spring_dst_gap_is_not_caught_up_and_twenty_three_hours_do_not_clear_cooldown() -> None:
    zone = ZoneInfo("Europe/Bratislava")
    gap_day = datetime(2026, 3, 29, 1, 30, tzinfo=UTC)
    assert plan_presence(policy(timezone=zone.key, local_hour=2), gap_day) is None
    before_gap = datetime(2026, 3, 28, 10, 30, tzinfo=zone)
    after_gap = datetime(2026, 3, 29, 10, 30, tzinfo=zone)
    assert plan_presence(policy(timezone=zone.key), after_gap, before_gap) is None
    assert plan_presence(policy(timezone=zone.key), after_gap, before_gap - timedelta(hours=1)) is not None


def test_fall_dst_repeated_hour_expires_after_first_occurrence() -> None:
    configured = policy(timezone="Europe/Bratislava", local_hour=2)
    first = datetime(2026, 10, 25, 0, 30, tzinfo=UTC)
    repeated = datetime(2026, 10, 25, 1, 30, tzinfo=UTC)
    tick = plan_presence(configured, first)
    assert tick is not None
    assert tick.scheduled_at == first.replace(minute=0)
    assert tick.expires_at == first.replace(hour=1, minute=0)
    assert plan_presence(configured, repeated) is None


def test_fall_dst_cooldown_uses_twenty_five_elapsed_hours() -> None:
    zone = ZoneInfo("Europe/Bratislava")
    previous = datetime(2026, 10, 24, 10, 30, tzinfo=zone)
    current = datetime(2026, 10, 25, 10, 30, tzinfo=zone)
    assert plan_presence(policy(timezone=zone.key, cooldown_seconds=90000), current, previous) is not None


def test_half_hour_dst_gap_starts_at_first_existing_instant_and_ends_with_local_hour() -> None:
    instant = datetime(2026, 10, 3, 15, 45, tzinfo=UTC)
    tick = plan_presence(policy(timezone="Australia/Lord_Howe", local_hour=2), instant)
    assert tick is not None
    assert tick.local_date == date(2026, 10, 4)
    assert tick.scheduled_at == instant.replace(minute=30)
    assert tick.expires_at == instant.replace(hour=16, minute=0)
    assert tick.expires_at - tick.scheduled_at == timedelta(minutes=30)


@pytest.mark.parametrize("enabled", [False, True])
def test_naive_clocks_are_refused_even_for_disabled_policy(*, enabled: bool) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        plan_presence(policy(enabled=enabled), NOW.replace(tzinfo=None))
    with pytest.raises(ValueError, match="timezone-aware"):
        plan_presence(policy(enabled=enabled), NOW, NOW.replace(tzinfo=None))


def test_boundary_revalidates_forged_policy_instead_of_trusting_model_copy() -> None:
    forged = policy().model_copy(update={"enabled": 1})
    with pytest.raises(ValidationError):
        plan_presence(forged, NOW)


def test_output_has_only_a_nonempty_skip_reason_or_a_bounded_inert_candidate() -> None:
    skip = parse_presence_output('{"kind":"skip","text":"No useful update today."}')
    assert skip.kind == "skip"
    assert skip.text == "No useful update today."
    candidate = parse_presence_output('{"kind":"candidate","text":"One useful update.\\nSecond line."}')
    assert candidate.kind == "candidate"
    assert candidate.text == "One useful update.\nSecond line."
    assert set(type(candidate).model_fields) == {"kind", "text"}
    assert PresenceOutput.model_validate_json(candidate.model_dump_json()) == candidate
    assert "One useful update" not in repr(candidate)
    with pytest.raises(ValidationError):
        candidate.kind = "skip"
    maximum = parse_presence_output(json.dumps({"kind": "candidate", "text": "\U0001f600" * 8000}))
    assert len(maximum.text) == 8000


@pytest.mark.parametrize(
    "raw",
    [
        "not JSON",
        '```json\n{"kind":"skip","text":"No news."}\n```',
        '{"kind":"send","text":"Publish now."}',
        '{"kind":"candidate","text":""}',
        '{"kind":"skip","text":" "}',
        '{"kind":"skip"}',
        '{"kind":"candidate","text":7}',
        '{"kind":"candidate","text":null}',
        '{"kind":"candidate","text":"message","tools":[]}',
        '{"kind":"candidate","text":"message","recipient":"elsewhere"}',
        '{"kind":"skip","text":"reason","kind":"candidate"}',
        '{"kind":"candidate","text":"one","text":"two"}',
        '{"kind":"candidate","text":NaN}',
        '{"kind":"candidate","text":Infinity}',
        '{"kind":"candidate","text":-Infinity}',
        '[{"kind":"skip","text":"No news."}]',
        '"skip"',
        "null",
        '{"kind":"skip","text":"reason"} {"kind":"candidate","text":"more"}',
        json.dumps({"kind": "candidate", "text": "x" * 8001}),
        json.dumps({"kind": "skip", "text": "bad\x00"}),
        json.dumps({"kind": "candidate", "text": "\ud800"}),
        " " * 128001,
        "[" * 2000,
    ],
)
def test_output_refuses_invalid_ambiguous_unbounded_or_tool_shaped_decisions(raw: str) -> None:
    with pytest.raises(ValueError, match=r"Presence|validation error"):
        parse_presence_output(raw)


def test_tick_rejects_naive_non_utc_or_unbounded_expiry() -> None:
    tick = plan_presence(policy(), NOW)
    assert tick is not None
    values = tick.model_dump(mode="python")
    for changes in (
        {"scheduled_at": tick.scheduled_at.replace(tzinfo=None)},
        {"expires_at": tick.expires_at.replace(tzinfo=None)},
        {"scheduled_at": tick.scheduled_at.astimezone(ZoneInfo("Europe/Bratislava"))},
        {"expires_at": tick.scheduled_at},
        {"expires_at": tick.scheduled_at + timedelta(hours=1, microseconds=1)},
    ):
        with pytest.raises(ValidationError):
            PresenceTick.model_validate(values | changes)
