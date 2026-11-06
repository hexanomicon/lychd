"""Concrete consumer capabilities over the one authenticated Discord executor."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any, Literal
from uuid import UUID

from lychd.compositions.reach.expressions import Reaction
from lychd.compositions.reach.schemas import ReachEvent
from lychd.interface.discord.rest import SUPPRESS_EMBEDS, DiscordRest, EffectJournal, EffectResult
from lychd.interface.discord.schemas import DiscordPolicy

MAX_PUBLICATION_TEXT = 1900


class GuildInspection:
    """Authenticated inventory is evidence, with no effect methods."""

    def __init__(self, rest: DiscordRest) -> None:
        """Expose the verified account's inventory without its effect methods."""
        self._rest = rest
        self.application_id = rest.application_id
        self.bot_user_id = rest.bot_user_id
        self.guild_id = rest.guild_id

    async def verify_identity(self) -> None:
        await self._rest.verify_identity()

    async def get(self, path: str) -> Any:
        return await self._rest.get(path)

    def bind_channels(self, ids: Iterable[str]) -> None:
        self._rest.bind_channels(ids)


class AdministrationEffects(GuildInspection):
    """The local reviewed-plan caller alone receives administrative writes."""

    @property
    def journal(self) -> EffectJournal:
        return self._rest.journal

    async def write(
        self, method: Literal["POST", "PATCH"], path: str, body: dict[str, Any], *, effect_key: str, scope: str
    ) -> EffectResult:
        return await self._rest.write(method, path, body, effect_key=effect_key, scope=scope)


class ReplyEffects:
    """Only configured audiences can become exact request-bound delivery ports."""

    def __init__(self, rest: DiscordRest, policy: DiscordPolicy) -> None:
        """Pin the configured reply places independently of discovered inventory."""
        self._rest = rest
        self._policy = policy

    def _validate(self, event: ReachEvent) -> None:
        policy = self._policy
        guild_place = event.space_id == policy.guild_id and (
            event.conversation_id in policy.allowed_channel_ids
            or event.parent_conversation_id in policy.allowed_thread_parent_ids
        )
        direct_place = (
            event.space_id is None and event.trigger == "message" and event.subject_id in policy.allowed_dm_user_ids
        )
        if (
            event.platform != "discord"
            or event.account_id != policy.application_id
            or not (guild_place or direct_place)
        ):
            msg = "reply_audience_binding"
            raise ValueError(msg)

    async def bind_conversation(self, event: ReachEvent) -> None:
        self._validate(event)
        if event.space_id is None:
            await self._rest.bind_direct_channel(event.conversation_id, event.subject_id)
        elif event.parent_conversation_id is not None:
            self._rest.bind_channels((event.conversation_id,))

    def for_event(self, event: ReachEvent, *, interaction_token: str | None = None) -> TurnEffects:
        self._validate(event)
        if (event.trigger == "command") != (interaction_token is not None):
            msg = "reply_interaction_binding"
            raise ValueError(msg)
        return TurnEffects(self._rest, event, interaction_token=interaction_token)


class TurnEffects:
    """No target, identity, method, path or scope can be supplied during a send."""

    def __init__(self, rest: DiscordRest, event: ReachEvent, *, interaction_token: str | None) -> None:
        """Freeze one admitted reply target and optional interaction credential."""
        self._rest = rest
        self._event = event
        self._interaction_token = interaction_token

    async def send_text(
        self, text: str, *, phase: Literal["ack", "plan", "final"], part: int = 0, silent: bool = False
    ) -> EffectResult:
        event = self._event
        if self._interaction_token is not None:
            if phase != "final":
                return EffectResult(status="rejected", code="interaction_phase")
            if part == 0:
                return await self._rest.edit_interaction_original(
                    self._interaction_token, text, event_id=event.event_id
                )
            return await self._rest.send_interaction_followup(
                self._interaction_token, text, event_id=event.event_id, part=part
            )
        return await self._rest.send_message(
            event.conversation_id,
            text,
            event_id=event.event_id,
            reply_to=event.event_id,
            phase=phase,
            part=part,
            **({"silent": True} if silent else {}),
        )

    async def react(self, emoji: Reaction, *, phase: Literal["seen", "reply"]) -> EffectResult:
        event = self._event
        if self._interaction_token is not None:
            return EffectResult(status="rejected", code="interaction_expression")
        return await self._rest.add_reaction(
            event.conversation_id, event.event_id, emoji, event_id=event.event_id, phase=phase
        )

    async def send_gif(self, url: str) -> EffectResult:
        event = self._event
        if self._interaction_token is not None:
            return EffectResult(status="rejected", code="interaction_expression")
        return await self._rest.send_gif(event.conversation_id, url, event_id=event.event_id, reply_to=event.event_id)


class OnboardingEffects:
    """Only the verified panel, baseline roles and introduction place are available."""

    def __init__(
        self,
        rest: DiscordRest,
        *,
        roles: frozenset[str],
        panel_channel: str,
        panel_message: str,
        introduction_channel: str,
    ) -> None:
        """Pin the independently verified onboarding resources."""
        self._rest = rest
        self._roles = roles
        self._panel_channel, self._panel_message = panel_channel, panel_message
        self._introduction_channel = introduction_channel
        self.application_id, self.bot_user_id, self.guild_id = rest.application_id, rest.bot_user_id, rest.guild_id

    async def get_message(self, channel_id: str, message_id: str) -> dict[str, Any]:
        if (channel_id, message_id) != (self._panel_channel, self._panel_message):
            msg = "onboarding_panel_binding"
            raise ValueError(msg)
        return await self._rest.get_message(channel_id, message_id)

    def bind_member_roles(self, ids: Iterable[str]) -> None:
        if frozenset(ids) != self._roles:
            msg = "member_role_binding"
            raise ValueError(msg)
        self._rest.bind_member_roles(self._roles)

    def bind_introduction_channel(self, channel_id: str) -> None:
        if channel_id != self._introduction_channel:
            msg = "introduction_channel_binding"
            raise ValueError(msg)
        self._rest.bind_introduction_channel(channel_id)

    async def ensure_member_role(self, user_id: str, role_id: str, *, event_id: str) -> EffectResult:
        if role_id not in self._roles:
            return EffectResult(status="rejected", code="member_role_binding")
        return await self._rest.ensure_member_role(user_id, role_id, event_id=event_id)

    async def publish_introduction(self, channel_id: str, text: str, *, subject_id: str, event_id: str) -> EffectResult:
        if channel_id != self._introduction_channel:
            return EffectResult(status="rejected", code="introduction_channel_binding")
        return await self._rest.publish_introduction(channel_id, text, subject_id=subject_id, event_id=event_id)


class PublicationEffects:
    """Owner-authored publication text can reach only frozen publication channels."""

    def __init__(self, rest: DiscordRest, *, allowed_channels: frozenset[str]) -> None:
        """Freeze the host-selected publication destinations."""
        self._rest = rest
        self._channels = allowed_channels

    def _payload(self, publication_id: str, channel_id: str, text: str) -> tuple[str, str, dict[str, Any], str]:
        if str(UUID(publication_id)) != publication_id:
            msg = "publication_binding"
            raise ValueError(msg)
        if not 1 <= len(text) <= MAX_PUBLICATION_TEXT:
            msg = "publication_body"
            raise ValueError(msg)
        key = f"publication:{self._rest.application_id}:{publication_id}"
        body: dict[str, Any] = {
            "content": text,
            "flags": SUPPRESS_EMBEDS,
            "allowed_mentions": {"parse": []},
            "nonce": hashlib.sha256(key.encode()).hexdigest()[:25],
            "enforce_nonce": True,
        }
        return key, f"/channels/{channel_id}/messages", body, f"{key}:{channel_id}"

    def retained(self, publication_id: str, channel_id: str, text: str) -> EffectResult | None:
        key, path, body, scope = self._payload(publication_id, channel_id, text)
        previous = self._rest.journal.lookup(key)
        if previous is None:
            return None
        payload = json.dumps(
            {"method": "POST", "path": path, "body": body},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        if (
            previous.payload_digest != hashlib.sha256(payload.encode()).hexdigest()
            or previous.scope_digest != hashlib.sha256(scope.encode()).hexdigest()
            or previous.method != "POST"
            or previous.target != "channel_messages"
        ):
            return EffectResult(status="unknown", code="publication_binding")
        if previous.status in {"attempting", "unknown"}:
            return EffectResult(
                status="unknown", remote_id=previous.remote_id, code=previous.code or "effect_unresolved"
            )
        return EffectResult(
            status="succeeded" if previous.status == "succeeded" else "rejected",
            remote_id=previous.remote_id,
            code=previous.code,
        )

    async def publish(self, publication_id: str, channel_id: str, text: str) -> EffectResult:
        if channel_id not in self._channels:
            return EffectResult(status="rejected", code="publication_channel")
        key, path, body, scope = self._payload(publication_id, channel_id, text)
        return await self._rest.write("POST", path, body, effect_key=key, scope=scope)
