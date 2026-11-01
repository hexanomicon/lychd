"""Direct-message preparation requires explicit users and isolated participant history."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from lychd.compositions.reach.documents import validate_history
from lychd.compositions.reach.operator_wire import ReachHistoryEntry, ReachWorkerRequest
from lychd.compositions.reach.policy import prepare_turn
from lychd.compositions.reach.schemas import ReachEvent, ReachPolicy
from lychd.interface.discord.schemas import DiscordPolicy, DiscordRule

NOW = datetime(2026, 11, 1, 12, tzinfo=UTC)


def policy(**changes: Any) -> DiscordPolicy:
    values: dict[str, Any] = {
        "application_id": "101",
        "bot_user_id": "102",
        "guild_id": "103",
        "allowed_channel_ids": ("104",),
        "allowed_dm_user_ids": ("105",),
        "rules": (DiscordRule(name="person", user_ids=("105",), actions=("converse",)),),
    }
    return DiscordPolicy(**(values | changes))


def event(**changes: Any) -> ReachEvent:
    values: dict[str, Any] = {
        "platform": "discord",
        "account_id": "101",
        "event_id": "110",
        "conversation_id": "204",
        "subject_id": "105",
        "trigger": "message",
        "action": "converse",
        "question": "How does Reach work?",
        "occurred_at": NOW - timedelta(seconds=1),
    }
    return ReachEvent(**(values | changes))


def history_entry(**changes: Any) -> ReachHistoryEntry:
    values: dict[str, Any] = {
        "subject_id": "105",
        "event_id": "109",
        "conversation_id": "204",
        "text": "An earlier direct message.",
        "occurred_at": NOW - timedelta(seconds=2),
    }
    return ReachHistoryEntry(**(values | changes))


def test_dm_policy_is_an_explicit_default_deny_opt_in() -> None:
    configured = policy(allowed_dm_user_ids=())
    shared = configured.to_reach_policy()
    assert configured.allowed_dm_user_ids == ()
    assert shared.allowed_direct_subject_ids == ()
    assert shared.allowed_triggers == ("mention", "command")
    assert prepare_turn(shared, event(), now=NOW).reason == "subject_not_allowed"
    omitted = configured.model_dump(exclude={"allowed_dm_user_ids"})
    assert DiscordPolicy(**omitted).allowed_dm_user_ids == ()
    shared_omitted = shared.model_dump(exclude={"allowed_direct_subject_ids"})
    assert ReachPolicy(**shared_omitted).allowed_direct_subject_ids == ()


def test_opted_in_dm_compiles_and_prepares_without_a_guild_channel_grant() -> None:
    configured = policy(allowed_triggers=("slash",))
    shared = configured.to_reach_policy()
    assert shared.allowed_direct_subject_ids == ("105",)
    assert shared.allowed_triggers == ("command",)
    assert "204" not in shared.allowed_conversation_ids
    assert shared.digest != policy(allowed_dm_user_ids=()).digest
    assert DiscordPolicy.model_validate_json(configured.model_dump_json()) == configured
    decision = prepare_turn(shared, event(), now=NOW)
    assert decision.allowed
    assert decision.prepared is not None
    assert decision.prepared.rule_name == "person"
    assert decision.prepared.action == "converse"
    assert decision.prepared.expires_at == event().occurred_at + timedelta(seconds=300)


def test_duplicate_dm_subjects_are_refused_at_both_configuration_boundaries() -> None:
    with pytest.raises(ValidationError, match="Duplicate direct subject ids"):
        policy(allowed_dm_user_ids=("105", "105"))
    values = policy().to_reach_policy().model_dump()
    with pytest.raises(ValidationError, match="Duplicate direct subject ids"):
        ReachPolicy.model_validate(values | {"allowed_direct_subject_ids": ("105", "105")})


def test_dm_role_rule_never_authorizes_and_first_subject_rule_decides() -> None:
    role = DiscordRule(name="role", role_ids=("106",), actions=("converse",))
    assert prepare_turn(policy(rules=(role,)).to_reach_policy(), event(), now=NOW).reason == "subject_not_allowed"
    narrow = DiscordRule(name="narrow", user_ids=("105",), actions=("answer_docs",))
    broad = DiscordRule(name="broad", user_ids=("105",), role_ids=("106",), actions=("converse",))
    denied = prepare_turn(policy(rules=(role, narrow, broad)).to_reach_policy(), event(), now=NOW)
    assert denied.reason == "action_not_allowed"
    allowed = prepare_turn(policy(rules=(role, broad)).to_reach_policy(), event(), now=NOW)
    assert allowed.prepared is not None
    assert allowed.prepared.rule_name == "broad"


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"space_id": "999"}, "wrong_space"),
        ({"space_id": "103", "conversation_id": "104"}, "trigger_not_allowed"),
        ({"parent_conversation_id": "104"}, "conversation_not_allowed"),
        ({"group_ids": ("106",)}, "subject_not_allowed"),
        ({"subject_id": "107"}, "subject_not_allowed"),
        ({"action": "answer_docs"}, "action_not_allowed"),
        ({"action": "summarize_context"}, "action_not_allowed"),
        ({"action": "run_shell"}, "action_not_supported"),
        ({"platform": "telegram"}, "wrong_platform"),
        ({"account_id": "201"}, "wrong_account"),
        ({"is_automated": True}, "automated_subject"),
        ({"occurred_at": NOW + timedelta(microseconds=1)}, "event_from_future"),
        ({"occurred_at": NOW - timedelta(seconds=300)}, "event_expired"),
        ({"question": " \n\t"}, "question_empty"),
        ({"question": "x" * 2001}, "question_too_large"),
        ({"question": "invalid\x00question"}, "question_invalid"),
    ],
)
def test_dm_refuses_forged_context_and_retains_common_gates(changes: dict[str, Any], reason: str) -> None:
    decision = prepare_turn(policy().to_reach_policy(), event(**changes), now=NOW)
    assert not decision.allowed
    assert decision.reason == reason
    assert decision.prepared is None
    assert "question" not in decision.model_dump(mode="json")


def test_dm_self_event_still_refuses_even_with_explicit_subject_opt_in() -> None:
    configured = policy(
        allowed_dm_user_ids=("102",),
        rules=(DiscordRule(name="self", user_ids=("102",), actions=("converse",)),),
    )
    assert prepare_turn(configured.to_reach_policy(), event(subject_id="102"), now=NOW).reason == "self_event"


def test_guild_role_and_trigger_policy_remain_independent_from_dm_opt_in() -> None:
    configured = policy(
        allowed_dm_user_ids=(),
        allowed_triggers=("mention",),
        rules=(DiscordRule(name="role", role_ids=("106",), actions=("answer_docs",)),),
    ).to_reach_policy()
    guild = event(
        space_id="103",
        conversation_id="104",
        subject_id="107",
        group_ids=("106",),
        trigger="mention",
        mention_subject_ids=("102",),
        action="answer_docs",
    )
    assert prepare_turn(configured, guild, now=NOW).allowed
    assert prepare_turn(configured, guild.model_copy(update={"trigger": "command"}), now=NOW).reason == (
        "trigger_not_allowed"
    )


def test_dm_history_accepts_only_the_sender_and_current_bot() -> None:
    configured = policy(context_message_limit=3).to_reach_policy()
    history = (history_entry(), history_entry(subject_id="102", event_id="108"))
    request = ReachWorkerRequest(request_id="request", event=event(), history=history)
    validate_history(configured, request)
    stranger = history_entry(subject_id="107", event_id="107")
    with pytest.raises(ValueError, match="history_binding"):
        validate_history(configured, request.model_copy(update={"history": (*history, stranger)}))


@pytest.mark.parametrize(
    "changes",
    [
        {"conversation_id": "999"},
        {"occurred_at": NOW},
        {"occurred_at": NOW - timedelta(seconds=602)},
        {"text": "invalid\x00history"},
    ],
)
def test_dm_history_retains_conversation_time_and_text_checks(changes: dict[str, Any]) -> None:
    request = ReachWorkerRequest(request_id="request", event=event(), history=(history_entry(**changes),))
    with pytest.raises(ValueError, match="history_binding"):
        validate_history(policy(context_message_limit=3).to_reach_policy(), request)


def test_dm_history_retains_duplicate_and_budget_checks() -> None:
    entry = history_entry()
    request = ReachWorkerRequest(request_id="request", event=event(), history=(entry,))
    with pytest.raises(ValueError, match="history_limit"):
        validate_history(policy().to_reach_policy(), request)
    configured = policy(context_message_limit=10).to_reach_policy()
    with pytest.raises(ValueError, match="history_binding"):
        validate_history(configured, request.model_copy(update={"history": (entry, entry)}))
    oversized = tuple(history_entry(event_id=str(index + 200), text="x" * 2000) for index in range(9))
    with pytest.raises(ValueError, match="history_limit"):
        validate_history(configured, request.model_copy(update={"history": oversized}))
