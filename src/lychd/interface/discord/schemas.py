"""Discord-specific configuration compiled into the transport-neutral Reach policy."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

from lychd.compositions.reach.schemas import ReachAction, ReachPolicy, ReachRule


def _snowflake(value: str) -> str:
    if int(value) > 2**64 - 1:
        msg = "Discord identity exceeds the unsigned 64-bit boundary."
        raise ValueError(msg)
    return value


type DiscordId = Annotated[str, Field(pattern=r"^[1-9][0-9]{0,19}$"), AfterValidator(_snowflake)]


class _Value(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, hide_input_in_errors=True)


class DiscordRule(_Value):
    """Friendly Discord selectors; rule evaluation belongs to Reach."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    user_ids: tuple[DiscordId, ...] = Field(default=(), max_length=100)
    role_ids: tuple[DiscordId, ...] = Field(default=(), max_length=100)
    actions: tuple[ReachAction, ...] = Field(min_length=1, max_length=2)

    def to_reach_rule(self) -> ReachRule:
        return ReachRule(name=self.name, subject_ids=self.user_ids, group_ids=self.role_ids, actions=self.actions)


class DiscordPolicy(_Value):
    """Public non-secret Discord configuration; no SDK or transport is constructed."""

    schema_version: Literal[1] = 1
    application_id: DiscordId
    bot_user_id: DiscordId
    guild_id: DiscordId
    allowed_channel_ids: tuple[DiscordId, ...] = Field(min_length=1, max_length=100)
    rules: tuple[DiscordRule, ...] = Field(min_length=1, max_length=100)
    allowed_triggers: tuple[Literal["mention", "slash"], ...] = Field(
        default=("mention", "slash"), min_length=1, max_length=2
    )
    event_ttl_seconds: int = Field(default=300, ge=1, le=3600)
    max_question_chars: int = Field(default=2000, ge=1, le=2000)
    context_message_limit: int = Field(default=0, ge=0, le=50)
    context_max_age_seconds: int = Field(default=600, ge=1, le=3600)

    @field_validator("schema_version", mode="before")
    @classmethod
    def original_integer(cls, value: object) -> object:
        if type(value) is not int:
            msg = "Discord policy version must be an original integer."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def check_compiled_policy(self) -> Self:
        self.to_reach_policy()
        return self

    def to_reach_policy(self) -> ReachPolicy:
        """Translate provider names once; preserve ordered rules and action semantics."""
        return ReachPolicy(
            platform="discord",
            account_id=self.application_id,
            agent_subject_id=self.bot_user_id,
            space_id=self.guild_id,
            allowed_conversation_ids=self.allowed_channel_ids,
            rules=tuple(rule.to_reach_rule() for rule in self.rules),
            allowed_triggers=tuple("command" if trigger == "slash" else "mention" for trigger in self.allowed_triggers),
            event_ttl_seconds=self.event_ttl_seconds,
            max_question_chars=self.max_question_chars,
            context_message_limit=self.context_message_limit,
            context_max_age_seconds=self.context_max_age_seconds,
        )

    @property
    def digest(self) -> str:
        return self.to_reach_policy().digest
