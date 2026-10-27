from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from lychd.interface.discord.events import normalize_interaction, normalize_message

APP = "111111111111111111"
BOT = "222222222222222222"
NOW = datetime(2026, 10, 27, tzinfo=UTC)


def message() -> dict[str, Any]:
    return {
        "id": "777777777777777777",
        "guild_id": "333333333333333333",
        "channel_id": "444444444444444444",
        "author": {"id": "555555555555555555", "username": "a-label"},
        "member": {"roles": ["666666666666666666"]},
        "mentions": [{"id": BOT}],
        "content": f"<@{BOT}> Where is the guide?",
        "timestamp": NOW.isoformat(),
    }


def interaction() -> dict[str, Any]:
    return {
        "id": "777777777777777777",
        "application_id": APP,
        "type": 2,
        "guild_id": "333333333333333333",
        "channel_id": "444444444444444444",
        "member": {"user": {"id": "555555555555555555"}, "roles": ["666666666666666666"]},
        "data": {
            "name": "reach",
            "type": 1,
            "options": [{"name": "ask", "type": 1, "options": [{"name": "question", "type": 3, "value": "Guide?"}]}],
        },
        "token": "synthetic-interaction-secret",
    }


@pytest.mark.parametrize("mention", [f"<@{BOT}>", f"<@!{BOT}>"])
def test_message_preserves_stable_actor_roles_and_strips_only_bot_mention(mention: str) -> None:
    data = message()
    data["content"] = f"{mention} Where is <@888888888888888888>'s guide?"
    event = normalize_message(data, application_id=APP, bot_user_id=BOT)
    assert event is not None
    assert event.subject_id == "555555555555555555"
    assert event.group_ids == ("666666666666666666",)
    assert event.question == "Where is <@888888888888888888>'s guide?"
    assert event.action == "answer_docs"


@pytest.mark.parametrize("kind", ["ambient", "dm", "bot", "webhook", "name_only"])
def test_ignored_message_is_discarded_before_content_validation(kind: str) -> None:
    data = message()
    data["content"] = object()
    if kind == "ambient":
        data["mentions"] = []
    elif kind == "dm":
        del data["guild_id"]
    elif kind == "bot":
        data["author"]["bot"] = True
    elif kind == "webhook":
        data["webhook_id"] = "888888888888888888"
    else:
        data["mentions"] = [{"id": "888888888888888888", "username": "Reachy"}]
    assert normalize_message(data, application_id=APP, bot_user_id=BOT) is None


def test_selected_malformed_message_fails_closed() -> None:
    data = message()
    data["member"]["roles"] = [True]
    with pytest.raises(ValidationError):
        normalize_message(data, application_id=APP, bot_user_id=BOT)


@pytest.mark.parametrize(("command", "action"), [("ask", "answer_docs"), ("summarize", "summarize_context")])
def test_commands_keep_source_app_and_drop_interaction_token(command: str, action: str) -> None:
    data = interaction()
    data["data"]["options"][0]["name"] = command
    event = normalize_interaction(data, occurred_at=NOW)
    assert event is not None
    assert event.account_id == APP
    assert event.platform == "discord"
    assert event.action == action
    assert event.trigger == "command"
    assert "synthetic-interaction-secret" not in event.model_dump_json()


@pytest.mark.parametrize("kind", ["ping", "dm", "other_command", "bot"])
def test_unselected_interaction_does_not_parse_question(kind: str) -> None:
    data = interaction()
    data["data"]["options"] = object()
    if kind == "ping":
        data["type"] = 1
    elif kind == "dm":
        del data["guild_id"]
    elif kind == "bot":
        data["member"]["user"]["bot"] = True
    else:
        data["data"]["name"] = "other"
    assert normalize_interaction(data, occurred_at=NOW) is None


@pytest.mark.parametrize("options", [[], [{"name": "shell", "type": 1}], [{"name": "ask", "type": True}]])
def test_unknown_or_malformed_command_never_becomes_an_action(options: list[dict[str, Any]]) -> None:
    data = interaction()
    data["data"]["options"] = options
    with pytest.raises(ValidationError):
        normalize_interaction(data, occurred_at=NOW)
