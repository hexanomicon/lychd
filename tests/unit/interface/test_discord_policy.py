from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from lychd.interface.discord.schemas import DiscordPolicy, DiscordRule


def policy(**changes: Any) -> DiscordPolicy:
    values: dict[str, Any] = {
        "application_id": "101",
        "bot_user_id": "102",
        "guild_id": "103",
        "allowed_channel_ids": ("104",),
        "rules": (
            DiscordRule(name="owner", user_ids=("105",), actions=("answer_docs",)),
            DiscordRule(name="team", role_ids=("106",), actions=("summarize_context",)),
        ),
    }
    return DiscordPolicy(**(values | changes))


def test_provider_configuration_compiles_without_owning_policy_semantics() -> None:
    configured = policy()
    shared = configured.to_reach_policy()
    assert shared.platform == "discord"
    assert shared.account_id == "101"
    assert shared.agent_subject_id == "102"
    assert shared.space_id == "103"
    assert shared.allowed_conversation_ids == ("104",)
    assert shared.allowed_triggers == ("mention", "command")
    assert shared.rules[0].subject_ids == ("105",)
    assert shared.rules[0].group_ids == ()
    assert shared.rules[1].group_ids == ("106",)
    assert shared.rules[1].actions == ("summarize_context",)
    assert shared.digest == configured.digest
    assert shared.context_message_limit == 0


@pytest.mark.parametrize("identity", [101, True, "-100101", "user@example", "0", "0101", "18446744073709551616"])
def test_discord_only_adapter_refuses_non_snowflake_ids(identity: object) -> None:
    with pytest.raises(ValidationError):
        policy(application_id=identity)


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": True},
        {"allowed_channel_ids": ("104", "104")},
        {"allowed_triggers": ("mention", "mention")},
        {"allowed_triggers": ("command",)},
        {"rules": (DiscordRule(name="nobody", actions=("answer_docs",)),)},
        {"context_message_limit": 51},
        {"bot_token": "synthetic-secret"},
    ],
)
def test_bad_provider_configuration_never_expands_shared_policy(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        policy(**changes)
