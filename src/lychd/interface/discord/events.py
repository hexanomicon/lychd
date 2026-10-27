"""Normalize selected guild messages and commands before native admission.

These functions consume observations supplied by a future authenticated Gateway
owner. Parsing a JSON object does not authenticate a Discord person or event.
Ambient messages, DMs, bots and webhooks return before message content is parsed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Annotated, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lychd.compositions.reach.schemas import ReachEvent
from lychd.interface.discord.schemas import DiscordId


class _Wire(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True, hide_input_in_errors=True)

    @field_validator("type", mode="before", check_fields=False)
    @classmethod
    def original_integer(cls, value: object) -> object:
        if type(value) is not int:
            msg = "Discord object type must be an original integer."
            raise ValueError(msg)
        return value


class _User(_Wire):
    id: DiscordId
    bot: bool = False


class _Member(_Wire):
    roles: list[DiscordId] = Field(default_factory=list, max_length=250)


class _CommandMember(_Member):
    user: _User


class _Mention(_Wire):
    id: DiscordId


class _Message(_Wire):
    id: DiscordId
    guild_id: DiscordId
    channel_id: DiscordId
    author: _User
    member: _Member
    mentions: list[_Mention] = Field(max_length=100)
    content: str = Field(max_length=4000)
    timestamp: str = Field(max_length=64)


class _Question(_Wire):
    name: Literal["question"]
    type: Literal[3]
    value: str = Field(min_length=1, max_length=4000)


class _Subcommand(_Wire):
    name: Literal["ask", "summarize"]
    type: Literal[1]
    options: Annotated[list[_Question], Field(min_length=1, max_length=1)]


class _Command(_Wire):
    name: Literal["reach"]
    type: Literal[1]
    options: Annotated[list[_Subcommand], Field(min_length=1, max_length=1)]


class _Interaction(_Wire):
    id: DiscordId
    application_id: DiscordId
    type: Literal[2]
    guild_id: DiscordId
    channel_id: DiscordId
    member: _CommandMember
    data: _Command


def _object(value: object) -> Mapping[str, object] | None:
    return cast("Mapping[str, object]", value) if isinstance(value, dict) else None


def normalize_message(data: Mapping[str, object], *, application_id: str, bot_user_id: str) -> ReachEvent | None:
    """Select only actual bot mentions; never interpret username text as identity."""
    author = _object(data.get("author"))
    if (
        data.get("guild_id") is None
        or data.get("webhook_id") is not None
        or author is None
        or author.get("bot") is True
    ):
        return None
    mentions = data.get("mentions")
    if not isinstance(mentions, list):
        return None
    mention_objects = (_object(item) for item in cast("list[object]", mentions))
    if not any(item is not None and item.get("id") == bot_user_id for item in mention_objects):
        return None
    message = _Message.model_validate(data)
    question = re.sub(rf"<@!?{re.escape(bot_user_id)}>", "", message.content).strip()
    return ReachEvent(
        platform="discord",
        account_id=application_id,
        event_id=message.id,
        space_id=message.guild_id,
        conversation_id=message.channel_id,
        subject_id=message.author.id,
        group_ids=tuple(message.member.roles),
        is_automated=message.author.bot,
        mention_subject_ids=tuple(mention.id for mention in message.mentions),
        trigger="mention",
        action="answer_docs",
        question=question,
        occurred_at=datetime.fromisoformat(message.timestamp),
    )


def normalize_interaction(data: Mapping[str, object], *, occurred_at: datetime) -> ReachEvent | None:
    """Prepare /reach ask or summarize; the caller supplies observed event time.

    No interaction token is retained. A future Gateway owner must authenticate,
    deduplicate and acknowledge the interaction independently of this parser.
    """
    command = _object(data.get("data"))
    member = _object(data.get("member"))
    user = None if member is None else _object(member.get("user"))
    if (
        type(data.get("type")) is not int
        or data.get("type") != 2  # noqa: PLR2004 - Discord APPLICATION_COMMAND
        or data.get("guild_id") is None
        or command is None
        or command.get("name") != "reach"
        or (user is not None and user.get("bot") is True)
    ):
        return None
    interaction = _Interaction.model_validate(data)
    if interaction.member.user.bot:
        return None
    subcommand = interaction.data.options[0]
    return ReachEvent(
        platform="discord",
        account_id=interaction.application_id,
        event_id=interaction.id,
        space_id=interaction.guild_id,
        conversation_id=interaction.channel_id,
        subject_id=interaction.member.user.id,
        group_ids=tuple(interaction.member.roles),
        trigger="command",
        action="answer_docs" if subcommand.name == "ask" else "summarize_context",
        question=subcommand.options[0].value,
        occurred_at=occurred_at,
    )
