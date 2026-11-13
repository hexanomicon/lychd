"""Credential-only Gateway edge; native execution lives in another OCI process."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import stat
import sys
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, NoReturn, cast

import discord
from discord import app_commands
from discord.ext import commands

from lychd.compositions.reach.conversation_session import ContextTurnOutcome, ProgressHandler, drive_context_turn
from lychd.compositions.reach.operator_client import PipeWorker
from lychd.compositions.reach.operator_diagnostics import write_diagnostic_line
from lychd.compositions.reach.operator_limits import TurnDeadline, operator_limits
from lychd.compositions.reach.operator_session import OperatorSession
from lychd.compositions.reach.operator_trace import (
    ReachTraceEvent,
    TraceEmitter,
    TraceName,
    TraceStatus,
    error_code,
    platform_id_or_none,
    trace_bytes,
)
from lychd.compositions.reach.operator_wire import (
    MAX_HISTORY_BYTES,
    ReachHistoryEntry,
)
from lychd.compositions.reach.policy import prepare_turn
from lychd.compositions.reach.schemas import ReachEvent
from lychd.interface.discord.admin import ChannelSnapshot, GuildSnapshot, snapshot_guild
from lychd.interface.discord.delivery import (
    DiscordTurnDelivery,
    context_text,
    failure_text,
    worker_problem,
)
from lychd.interface.discord.followups import FollowupLedger
from lychd.interface.discord.history import HistoryPager, history_entry, history_lower_bound
from lychd.interface.discord.lifecycle import EdgeTasks, service_callback
from lychd.interface.discord.onboarding import OnboardingPanel, OnboardingProfile, OnboardingService
from lychd.interface.discord.operator_io import load_policy, read_token
from lychd.interface.discord.ports import GuildInspection, OnboardingEffects, PublicationEffects, ReplyEffects
from lychd.interface.discord.publications import PublicationQueue
from lychd.interface.discord.rest import DiscordRest, DiscordRestError, EffectJournal
from lychd.interface.discord.schemas import DiscordPolicy
from lychd.interface.http_observation import http_trace
from lychd.interface.observation import OperationObserver, observation_bytes

MAX_GENERATION_EVENTS = 10_000
MAX_GENERATION_THREADS = 1000
MAX_ONBOARDING_BYTES = 4096
MAX_ONBOARDING_MEMBERS = 1000
_COMMAND_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}\Z")


def _write_edge_trace(event: ReachTraceEvent) -> None:
    write_diagnostic_line(trace_bytes(event))


_EDGE_TRACE = TraceEmitter("edge", _write_edge_trace)


def _refuse(code: str) -> NoReturn:
    raise ValueError(code)


def diagnostic(code: str) -> None:
    """Keep protocol stdout and diagnostics free of payloads and credentials."""
    sys.stderr.write(f"reach_discord:{code}\n")


def load_onboarding_profile(path: Path) -> OnboardingProfile:
    """Read one bounded private JSON profile; never discover it from ambient configuration."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
            _refuse("onboarding_profile_permissions")
        raw = source.read(MAX_ONBOARDING_BYTES + 1)
    if len(raw) > MAX_ONBOARDING_BYTES:
        _refuse("onboarding_profile_limit")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                _refuse("onboarding_profile_json")
            result[key] = value
        return result

    def constant(_value: str) -> NoReturn:
        _refuse("onboarding_profile_json")

    json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    return OnboardingProfile.model_validate_json(raw)


def _verify_baseline_roles(profile: OnboardingProfile, snapshot: GuildSnapshot) -> None:
    """Verify baseline write authority and exact read-only community exemptions."""
    roles = {role.id: role for role in snapshot.roles}
    bot_roles = [role for identity, role in roles.items() if identity in {*snapshot.bot_role_ids, profile.guild_id}]
    highest = max(((role.position, -int(role.id)) for role in bot_roles), default=(0, 0))
    permissions = 0
    for role in bot_roles:
        permissions |= role.permissions
    if not permissions & ((1 << 28) | (1 << 3)):
        _refuse("onboarding_role_permissions")
    for identity, name in ((profile.magus_role_id, "Magus"), (profile.bot_role_id, "Bot")):
        role = roles.get(identity)
        if (
            role is None
            or role.name.split()[-1:] != [name]
            or role.managed
            or role.permissions
            or (role.position, -int(role.id)) >= highest
        ):
            _refuse("onboarding_role_binding")
    for identity in profile.elevated_human_role_ids:
        role = roles.get(identity)
        if role is None or role.managed:
            _refuse("onboarding_role_binding")


def _public_onboarding_channel(snapshot: GuildSnapshot, channel_id: str) -> ChannelSnapshot:
    """Require an everyone-visible text destination in the authenticated guild inventory."""
    roles = {role.id: role for role in snapshot.roles}
    everyone = roles.get(snapshot.guild_id)
    channel = next((item for item in snapshot.channels if item.id == channel_id), None)
    if everyone is None or channel is None or channel.type != 0:
        _refuse("onboarding_channel_binding")
    view = everyone.permissions & (1 << 10)
    for overwrite in channel.overwrites:
        if overwrite.type == 0 and overwrite.id == snapshot.guild_id:
            view = (view & ~overwrite.deny) | (overwrite.allow & (1 << 10))
    if not view:
        _refuse("onboarding_channel_not_public")
    return channel


async def verify_onboarding(
    service: OnboardingService, snapshot: GuildSnapshot, flags: discord.ApplicationFlags
) -> None:
    """Bind public panel and separate introduction destination before Gateway connect."""
    profile, rest = service.profile, service.effects
    if (
        snapshot.guild_id != profile.guild_id
        or snapshot.application_id != rest.application_id
        or snapshot.bot_user_id != rest.bot_user_id
        or not (flags.gateway_guild_members or flags.gateway_guild_members_limited)
    ):
        _refuse("onboarding_identity_or_intent")
    welcome_channel = _public_onboarding_channel(snapshot, profile.channel_id)
    if welcome_channel.name.split("・")[-1] != "start-here":
        _refuse("onboarding_channel_binding")
    _public_onboarding_channel(snapshot, profile.introduction_channel_id)
    _verify_baseline_roles(profile, snapshot)
    panel = await rest.get_message(profile.channel_id, profile.panel_message_id)
    raw_author: object = panel.get("author")
    author = cast("dict[str, Any]", raw_author) if isinstance(raw_author, dict) else None
    if (
        panel.get("id") != profile.panel_message_id
        or panel.get("channel_id") != profile.channel_id
        or panel.get("webhook_id") is not None
        or author is None
        or author.get("id") != rest.bot_user_id
        or author.get("bot") is not True
    ):
        _refuse("onboarding_panel_binding")
    rest.bind_member_roles((profile.magus_role_id, profile.bot_role_id))
    rest.bind_introduction_channel(profile.introduction_channel_id)


def onboarding_profile_for_guild(path: Path | None, guild_id: str) -> OnboardingProfile | None:
    """Keep absent onboarding inert and reject cross-guild host configuration."""
    profile = load_onboarding_profile(path) if path is not None else None
    if profile is not None and profile.guild_id != guild_id:
        _refuse("onboarding_guild_binding")
    return profile


def _parent(channel: object, policy: DiscordPolicy) -> str | None:
    if isinstance(channel, discord.Thread) and str(channel.parent_id) in policy.allowed_thread_parent_ids:
        return str(channel.parent_id)
    return None


def event_from_message(  # noqa: PLR0911 - cheap DM, mention and continuation refusals stay explicit
    message: discord.Message,
    policy: DiscordPolicy,
    *,
    conversation: bool = False,
    continuation: tuple[Literal["reply", "followup"], ReachHistoryEntry] | None = None,
) -> ReachEvent | None:
    """Translate SDK identity after cheap rejection, without retaining ambient messages."""
    if message.guild is None:
        channel = message.channel
        if (
            not conversation
            or not isinstance(channel, discord.DMChannel)
            or str(message.author.id) not in policy.allowed_dm_user_ids
            or message.author.bot
            or message.webhook_id is not None
            # Without a member cache the SDK builds an uncached DM channel with no recipient.
            # A non-bot author of a one-to-one DMChannel is then that recipient by construction.
            or (channel.recipient is not None and channel.recipient.id != message.author.id)
        ):
            return None
        return ReachEvent(
            platform="discord",
            account_id=policy.application_id,
            event_id=str(message.id),
            conversation_id=str(channel.id),
            subject_id=str(message.author.id),
            subject_label=str(message.author.display_name).strip()[:80] or None,
            trigger="message",
            action="converse",
            question=message.content.strip(),
            occurred_at=message.created_at,
        )
    if (
        str(message.guild.id) != policy.guild_id
        or (str(message.channel.id) not in policy.allowed_channel_ids and _parent(message.channel, policy) is None)
        or message.author.bot
        or message.webhook_id is not None
        or not isinstance(message.author, discord.Member)
    ):
        return None
    mentioned = any(str(person.id) == policy.bot_user_id for person in message.mentions)
    if not mentioned and (not conversation or continuation is None):
        return None
    if not mentioned and continuation is not None and continuation[1].conversation_id != str(message.channel.id):
        return None
    relationship: dict[str, Any] = {}
    trigger: Literal["mention", "reply", "followup"] = "mention"
    if not mentioned and continuation is not None:
        trigger, anchor = continuation
        relationship = {
            "related_event_id": anchor.event_id,
            "related_subject_id": anchor.subject_id,
            "related_occurred_at": anchor.occurred_at,
        }
    observed = ReachEvent(
        platform="discord",
        account_id=policy.application_id,
        event_id=str(message.id),
        space_id=str(message.guild.id),
        conversation_id=str(message.channel.id),
        parent_conversation_id=_parent(message.channel, policy),
        subject_id=str(message.author.id),
        subject_label=str(message.author.display_name).strip()[:80] or None,
        group_ids=tuple(str(role.id) for role in message.author.roles),
        mention_subject_ids=tuple(str(person.id) for person in message.mentions),
        trigger=trigger,
        action="converse" if conversation else "answer_docs",
        question="?",
        occurred_at=message.created_at,
        **relationship,
    )
    if trigger != "mention" and not prepare_turn(policy.to_reach_policy(), observed, now=datetime.now(UTC)).allowed:
        return None
    question = re.sub(rf"<@!?{re.escape(policy.bot_user_id)}>", "", message.content).strip()
    return observed.model_copy(update={"question": question})


def event_from_interaction(
    interaction: discord.Interaction, policy: DiscordPolicy, *, question: str, action: str
) -> ReachEvent | None:
    if (
        str(interaction.application_id) != policy.application_id
        or interaction.guild_id is None
        or str(interaction.guild_id) != policy.guild_id
        or interaction.channel_id is None
        or (
            str(interaction.channel_id) not in policy.allowed_channel_ids
            and _parent(interaction.channel, policy) is None
        )
        or not isinstance(interaction.user, discord.Member)
        or interaction.user.bot
    ):
        return None
    return ReachEvent(
        platform="discord",
        account_id=str(interaction.application_id),
        event_id=str(interaction.id),
        space_id=str(interaction.guild_id),
        conversation_id=str(interaction.channel_id),
        parent_conversation_id=_parent(interaction.channel, policy),
        subject_id=str(interaction.user.id),
        subject_label=str(interaction.user.display_name).strip()[:80] or None,
        group_ids=tuple(str(role.id) for role in interaction.user.roles),
        trigger="command",
        action=action,
        question=question,
        occurred_at=interaction.created_at,
    )


class ReachService:
    """Coordinate eligible events; neither a Cog nor this edge executes native work."""

    def __init__(
        self,
        policy: DiscordPolicy,
        worker: PipeWorker,
        replies: ReplyEffects,
        *,
        admin_users: frozenset[str],
        history_enabled: bool,
        conversation: bool = False,
        publications: PublicationQueue | None = None,
        publication_effects: PublicationEffects | None = None,
        inspection: GuildInspection | None = None,
    ) -> None:
        """Bind the admitted social policy and separate inspection selectors."""
        self.policy = policy
        self.shared_policy = policy.to_reach_policy()
        self.worker = worker
        if isinstance(getattr(worker, "trace", None), TraceEmitter):
            worker.trace.sink = _EDGE_TRACE
        self.replies, self.inspection = replies, inspection
        self.admin_users = admin_users
        self.history_enabled = history_enabled
        self.conversation = conversation
        self.publications = publications
        self.publication_effects = publication_effects
        self.tasks = EdgeTasks(on_failure=lambda: diagnostic("background_failed"))
        self.seen: set[str] = set()
        self.bound_threads: set[str] = set()
        self.worker_reserved = False
        self.followups = FollowupLedger()
        if (policy.allowed_reply_channel_ids or policy.allowed_adjacent_followup_channel_ids) and (
            not conversation
            or not history_enabled
            or not policy.context_message_limit
            or not worker.ready.adaptive_context
        ):
            _refuse("continuation_profile_required")

    def observe(self, name: TraceName, event: ReachEvent, *, status: TraceStatus = "observed", **fields: Any) -> None:
        """Keep provider IDs and structural outcomes without retaining message content."""
        _EDGE_TRACE.record(
            name,
            status=status,
            generation=self.worker.ready.generation,
            platform=event.platform,
            platform_event_id=platform_id_or_none(event.event_id),
            conversation_id=platform_id_or_none(event.conversation_id),
            **fields,
        )

    def eligible(self, event: ReachEvent | None) -> bool:
        return (
            event is not None
            and not self.tasks.closing
            and event.occurred_at >= self.worker.ready.started_at
            and prepare_turn(self.shared_policy, event, now=datetime.now(UTC)).allowed
        )

    def message_continuation(
        self, message: discord.Message
    ) -> tuple[Literal["reply", "followup"], ReachHistoryEntry] | None:
        """Inspect only selected-place metadata and consume the adjacent invitation."""
        selected = self.policy.allowed_reply_channel_ids + self.policy.allowed_adjacent_followup_channel_ids
        if (
            not selected
            or message.guild is None
            or str(message.guild.id) != self.policy.guild_id
            or str(message.channel.id) not in selected
        ):
            return None
        reference = message.reference
        same_place_reference = (
            isinstance(reference, discord.MessageReference)
            and reference.message_id is not None
            and str(reference.channel_id) == str(message.channel.id)
        )
        reference_id = (
            str(reference.message_id)
            if same_place_reference and isinstance(reference, discord.MessageReference)
            else ("unresolved" if reference is not None else None)
        )
        candidate = self.followups.activity(
            str(message.channel.id),
            str(message.id),
            str(message.author.id),
            message.created_at,
            reference_id=reference_id,
            allow_reply=str(message.channel.id) in self.policy.allowed_reply_channel_ids,
            allow_followup=str(message.channel.id) in self.policy.allowed_adjacent_followup_channel_ids,
            followup_window=self.policy.adjacent_followup_window_seconds,
        )
        if candidate is None:
            return None
        if not self.worker.available or self.worker.lock.locked() or self.worker_reserved:
            return None
        return candidate

    async def history(self, channel: discord.abc.Messageable, event: ReachEvent) -> tuple[ReachHistoryEntry, ...]:
        if not self.history_enabled or not self.policy.context_message_limit:
            return ()
        entries: list[ReachHistoryEntry] = []
        total_bytes = 0
        cutoff = event.occurred_at - timedelta(seconds=self.policy.context_max_age_seconds)
        async for message in channel.history(
            limit=self.policy.context_message_limit,
            before=event.occurred_at,
            after=history_lower_bound(cutoff),
            oldest_first=False,
        ):
            entry = history_entry(self.policy, event, message, conversation=self.conversation)
            if entry is None:
                continue
            size = len(entry.text.encode("utf-8"))
            if total_bytes + size > MAX_HISTORY_BYTES:
                break
            total_bytes += size
            entries.append(entry)
        return tuple(sorted(entries, key=lambda item: (item.occurred_at, int(item.event_id))))

    def session(self, event: ReachEvent) -> OperatorSession:
        limits = operator_limits(conversation=self.conversation, research=self.worker.ready.research_enabled)
        return OperatorSession(
            event,
            TurnDeadline.start(
                event.occurred_at, self.policy.event_ttl_seconds, limits.session_seconds, now=datetime.now(UTC)
            ),
        )

    def delivery(
        self, session: OperatorSession, *, interaction_token: str | None = None, failure_diagnostic: str | None = None
    ) -> DiscordTurnDelivery:
        return DiscordTurnDelivery(
            session,
            self.replies.for_event(session.event, interaction_token=interaction_token),
            policy=self.policy,
            expressions=self.worker.ready.expressions,
            started_at=self.worker.ready.started_at,
            followups=self.followups,
            observe=self.observe,
            diagnostic=diagnostic,
            conversation=self.conversation,
            failure_diagnostic=failure_diagnostic,
        )

    async def run_event(
        self,
        session: OperatorSession,
        channel: discord.abc.Messageable,
        *,
        acknowledge: Callable[[], Awaitable[bool]] | None = None,
        reference: discord.MessageReference | None = None,
        continuation_anchor: ReachHistoryEntry | None = None,
        progress: ProgressHandler | None = None,
    ) -> ContextTurnOutcome | None:
        event = session.event
        if not self.eligible(event) or event.event_id in self.seen:
            self.observe(
                "admission",
                event,
                status="refused",
                code="duplicate" if event.event_id in self.seen else "permission_denied",
            )
            return None
        # A generation-local fence is in addition to the persistent transport journal.
        if len(self.seen) >= MAX_GENERATION_EVENTS:
            msg = "generation_event_budget"
            raise ValueError(msg)
        self.seen.add(event.event_id)
        if not self.worker.available or self.worker.lock.locked() or self.worker_reserved:
            self.observe("admission", event, status="refused", code="worker_unavailable")
            _refuse("worker_busy_or_unavailable")
        self.observe("admission", event, status="ok")
        self.worker_reserved = True
        try:
            async with asyncio.timeout(session.deadline.remaining()):
                session.deadline.check()
                await self._bind_conversation(event, channel)
                if acknowledge is not None and not await acknowledge():
                    return None
                session.outcome = await self._context_turn(
                    session, channel, reference=reference, continuation_anchor=continuation_anchor, progress=progress
                )
                return session.outcome
        except Exception as error:
            self.observe("admission", event, status="error", code=error_code(error))
            raise
        finally:
            self.worker_reserved = False

    async def _bind_conversation(self, event: ReachEvent, channel: discord.abc.Messageable) -> None:
        """Bind the observed place without extending private access to administration."""
        if str(getattr(channel, "id", None)) != event.conversation_id:
            _refuse("channel_identity_mismatch")
        if event.parent_conversation_id is not None:
            if _parent(channel, self.policy) != event.parent_conversation_id:
                _refuse("thread_parent_mismatch")
            if event.conversation_id not in self.bound_threads:
                if len(self.bound_threads) >= MAX_GENERATION_THREADS:
                    _refuse("generation_thread_budget")
                self.bound_threads.add(event.conversation_id)
        await self.replies.bind_conversation(event)

    async def _context_turn(
        self,
        session: OperatorSession,
        channel: discord.abc.Messageable,
        *,
        reference: discord.MessageReference | None,
        continuation_anchor: ReachHistoryEntry | None = None,
        progress: ProgressHandler | None = None,
    ) -> ContextTurnOutcome:
        """Ask for older pages only when the exact native result requests them."""
        event = session.event
        if not self.conversation or not self.worker.ready.adaptive_context:
            return ContextTurnOutcome(
                await self.worker.request(
                    event, await self.history(channel, event), progress=progress, deadline=session.deadline
                )
            )
        if event.trigger in {"reply", "followup"}:
            if continuation_anchor is None:
                _refuse("continuation_anchor_missing")
            reference_id = event.related_event_id if event.trigger == "reply" else None
            anchor = continuation_anchor if event.trigger == "reply" else None
        else:
            reference_id, anchor = await self._reply_anchor(event, channel, reference)
        pager = HistoryPager(
            self.policy,
            event,
            channel,
            enabled=self.history_enabled,
            conversation=True,
            anchor=continuation_anchor if event.trigger in {"reply", "followup"} else anchor,
            page_size=16 if self.worker.ready.research_enabled else 6,
        )
        return await drive_context_turn(
            self.worker,
            event,
            pager,
            reply_to_event_id=reference_id,
            reply_anchor=anchor,
            continuation_anchor=continuation_anchor if event.trigger == "followup" else None,
            progress=progress,
            deadline=session.deadline,
        )

    async def _reply_anchor(
        self,
        event: ReachEvent,
        channel: discord.abc.Messageable,
        reference: discord.MessageReference | None,
    ) -> tuple[str | None, ReachHistoryEntry | None]:
        """Resolve only an observed same-place reference under this turn's history limits."""
        if not isinstance(reference, discord.MessageReference) or reference.message_id is None:
            return None, None
        if str(reference.channel_id) != event.conversation_id:
            _refuse("reply_conversation_not_allowed")
        identity = str(reference.message_id)
        if not self.history_enabled or not self.policy.context_message_limit:
            return identity, None
        try:
            message = await channel.fetch_message(reference.message_id)
        except discord.HTTPException:
            return identity, None
        if str(message.id) != identity:
            return identity, None
        return identity, history_entry(self.policy, event, message, conversation=self.conversation)


class ReachCog(commands.GroupCog, group_name="reach", group_description="Bounded Reach operator tools"):
    def __init__(self, service: ReachService) -> None:
        """Delegate invocation state and delivery to their request-local owners."""
        self.service = service

    @service_callback
    async def _request(self, interaction: discord.Interaction, question: str, action: str) -> None:
        event = event_from_interaction(interaction, self.service.policy, question=question, action=action)
        if event is None:
            await interaction.response.send_message("This request isn't allowed here.", ephemeral=True)
            return
        if not self.service.eligible(event):
            decision = prepare_turn(self.service.shared_policy, event, now=datetime.now(UTC))
            await interaction.response.send_message(
                worker_problem(
                    decision.reason if not decision.allowed else None,
                    refused=True,
                    agent_name=self.service.policy.agent_display_name,
                ),
                ephemeral=True,
            )
            return
        session = self.service.session(event)
        delivery = self.service.delivery(session, interaction_token=interaction.token)
        try:
            async with asyncio.timeout(session.deadline.remaining()):
                await interaction.response.defer(ephemeral=True, thinking=True)
                if not isinstance(interaction.channel, discord.abc.Messageable):
                    return
                try:
                    outcome = await self.service.run_event(session, interaction.channel, progress=delivery.plan)
                    if outcome is not None and session.visible():
                        await delivery.final(
                            context_text(outcome, agent_name=self.service.policy.agent_display_name),
                            result=outcome.result,
                        )
                except (ValueError, OSError, TimeoutError, discord.HTTPException, DiscordRestError) as error:
                    diagnostic("request_failed")
                    if session.can_report_failure():
                        await delivery.final(failure_text(error, agent_name=self.service.policy.agent_display_name))
        except TimeoutError:
            diagnostic("request_expired")
        finally:
            session.retire()

    @app_commands.command(description="Ask Reach using this connection's configured mode")
    @app_commands.describe(question="What would you like to ask?")
    async def ask(self, interaction: discord.Interaction, question: str) -> None:
        await self._request(interaction, question, "converse" if self.service.conversation else "answer_docs")

    @app_commands.command(description="Show bounded recent context when explicitly enabled")
    async def context(self, interaction: discord.Interaction) -> None:
        await self._request(interaction, "Recent conversation context", "summarize_context")

    @app_commands.command(description="Show this operator connection's readiness")
    @service_callback
    async def status(self, interaction: discord.Interaction) -> None:
        event = event_from_interaction(interaction, self.service.policy, question="status", action="answer_docs")
        if not self.service.eligible(event):
            text = "Access denied."
        else:
            mode = "conversation" if self.service.conversation else "documentation"
            state = "ready" if self.service.worker.available else "unavailable"
            text = f"Reach operator: {mode} worker is {state}."
        await interaction.response.send_message(text, ephemeral=True)

    @app_commands.command(name="admin-inspect", description="Inspect server setup; administration applies locally")
    @service_callback
    async def admin_inspect(self, interaction: discord.Interaction) -> None:
        event = event_from_interaction(interaction, self.service.policy, question="inspect", action="answer_docs")
        if (
            event is None
            or not self.service.eligible(event)
            or str(interaction.user.id) not in self.service.admin_users
            or self.service.inspection is None
        ):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
        session = self.service.session(event)
        delivery = self.service.delivery(
            session, interaction_token=interaction.token, failure_diagnostic="inspection_failed"
        )
        try:
            async with asyncio.timeout(session.deadline.remaining()):
                await interaction.response.defer(ephemeral=True, thinking=True)
                snapshot = await snapshot_guild(self.service.inspection)
                text = f"The server has {len(snapshot.roles)} roles and {len(snapshot.channels)} channels. Changes require a local plan."
                await delivery.final(text)
        except (ValueError, OSError, TimeoutError, DiscordRestError):
            diagnostic("inspection_failed")
        finally:
            session.retire()

    @commands.Cog.listener()
    @service_callback
    async def on_message(self, message: discord.Message) -> None:
        continuation = self.service.message_continuation(message)
        event = event_from_message(
            message, self.service.policy, conversation=self.service.conversation, continuation=continuation
        )
        if event is None or not self.service.eligible(event):
            return
        session = self.service.session(event)
        delivery = self.service.delivery(session)
        try:
            async with asyncio.timeout(session.deadline.remaining()):
                try:
                    outcome = await self.service.run_event(
                        session,
                        message.channel,
                        acknowledge=None if session.candidate else delivery.acknowledge,
                        reference=message.reference,
                        continuation_anchor=continuation[1] if session.candidate and continuation is not None else None,
                        progress=delivery.plan,
                    )
                    if not session.visible():
                        return
                    result = outcome.result if outcome is not None else None
                    agent_name = self.service.policy.agent_display_name
                    text = (
                        context_text(outcome, agent_name=agent_name)
                        if outcome is not None
                        else worker_problem(None, agent_name=agent_name)
                    )
                    delivered = await delivery.final(text, result=result)
                    if delivered and result is not None:
                        await delivery.expressions(result)
                except (ValueError, OSError, TimeoutError, discord.HTTPException, DiscordRestError) as error:
                    self.service.observe("delivery", event, status="error", code=error_code(error))
                    diagnostic("message_failed")
                    if session.can_report_failure():
                        if event.trigger == "message":
                            await self.service.replies.bind_conversation(event)
                        await delivery.final(failure_text(error, agent_name=self.service.policy.agent_display_name))
        except TimeoutError:
            diagnostic("request_expired")
        finally:
            session.retire()


class ReachBot(commands.Bot):
    def __init__(
        self,
        service: ReachService,
        *,
        command_name: str = "reach",
        onboarding: OnboardingService | None = None,
    ) -> None:
        """Keep member intent opt-in and avoid member/presence caches in every profile."""
        if not _COMMAND_NAME.fullmatch(command_name):
            _refuse("command_name")
        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True
        intents.dm_messages = bool(service.policy.allowed_dm_user_ids)
        intents.message_content = service.history_enabled
        intents.members = onboarding is not None
        super().__init__(
            command_prefix=(),
            help_command=None,
            intents=intents,
            member_cache_flags=discord.MemberCacheFlags.none(),
            chunk_guilds_at_startup=False,
            max_messages=None,
            http_trace=http_trace(
                OperationObserver(
                    generation=service.worker.ready.generation,
                    producer_id="reach.discord-sdk",
                    source="reach.discord-sdk",
                    target="reach.sdk-unclassified",
                    sink=lambda event: write_diagnostic_line(observation_bytes(event)),
                ),
                targets={
                    "discord.com": "reach.discord-api",
                    "gateway.discord.gg": "reach.discord-gateway",
                    "cdn.discordapp.com": "reach.discord-cdn",
                    "media.discordapp.net": "reach.discord-cdn",
                },
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.service = service
        self.command_name = command_name
        self.onboarding = onboarding
        self.onboarding_backfill_task: asyncio.Task[None] | None = None
        self.publications_task: asyncio.Task[None] | None = None

    async def setup_hook(self) -> None:
        cog = ReachCog(self.service)
        if cog.app_command is not None:
            cog.app_command.name = self.command_name
        await self.add_cog(cog, guild=discord.Object(id=int(self.service.policy.guild_id)))
        if self.onboarding is not None:
            self.add_view(OnboardingPanel(self.onboarding), message_id=int(self.onboarding.profile.panel_message_id))

    async def on_ready(self) -> None:
        if self.service.tasks.closing:
            return
        diagnostic("ready")
        if self.onboarding is not None and self.onboarding_backfill_task is None:
            self.onboarding_backfill_task = self.service.tasks.spawn(self._backfill_onboarding())
        if self.service.publications is not None and self.publications_task is None:
            self.publications_task = self.service.tasks.spawn(self._publications())

    async def _ensure_onboarding_role(self, member: discord.Member) -> None:
        onboarding = self.onboarding
        if onboarding is None or not onboarding.member_allowed(member):
            return
        role_id = onboarding.base_role_id(member)
        if role_id is None or any(str(role.id) == role_id for role in member.roles):
            return
        joined = member.joined_at
        if joined is None or joined.tzinfo is None or joined.utcoffset() is None:
            diagnostic("onboarding_join_identity")
            return
        try:
            event_id = str(discord.utils.time_snowflake(joined))
            outcome = await onboarding.ensure_base_role(member, event_id=event_id)
            if outcome.status != "succeeded":
                diagnostic("onboarding_role_failed")
        except (ValueError, OSError, TimeoutError, discord.HTTPException, DiscordRestError):
            diagnostic("onboarding_role_failed")

    @service_callback
    async def on_member_join(self, member: discord.Member) -> None:
        await self._ensure_onboarding_role(member)

    async def _backfill_onboarding(self) -> None:
        if self.onboarding is None:
            return
        guild = self.get_guild(int(self.onboarding.profile.guild_id))
        if guild is None:
            diagnostic("onboarding_guild_unavailable")
            return
        try:
            async for member in guild.fetch_members(limit=MAX_ONBOARDING_MEMBERS):
                await self._ensure_onboarding_role(member)
        except (ValueError, OSError, TimeoutError, discord.HTTPException, DiscordRestError):
            diagnostic("onboarding_backfill_failed")

    async def _publications(self) -> None:
        while not self.is_closed():
            try:
                if self.service.publications is not None and self.service.publication_effects is not None:
                    await self.service.publications.process_once(self.service.publication_effects)
            except (ValueError, OSError, DiscordRestError):
                diagnostic("publication_failed")
            await asyncio.sleep(2)

    async def close(self) -> None:
        await self.service.tasks.close()
        await super().close()

    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
        del event_method, args, kwargs
        diagnostic("gateway_event_failed")


def _publication_profile(
    args: argparse.Namespace, rest: DiscordRest
) -> tuple[PublicationQueue | None, PublicationEffects | None]:
    if not args.publications_dir:
        return None, None
    channels = frozenset(args.publication_channel)
    return PublicationQueue(args.publications_dir, allowed_channels=channels), PublicationEffects(
        rest, allowed_channels=channels
    )


def _validate_live_profile(args: argparse.Namespace, policy: DiscordPolicy) -> None:
    if bool(policy.context_message_limit) != args.history:
        _refuse("history_policy_flag_mismatch")
    if args.conversation and not any("converse" in rule.actions for rule in policy.rules):
        _refuse("conversation_policy_flag_mismatch")
    if bool(args.publications_dir) != bool(args.publication_channel):
        _refuse("publication_configuration")


async def run(args: argparse.Namespace) -> None:
    policy = load_policy(args.policy)
    _validate_live_profile(args, policy)
    onboarding_profile = onboarding_profile_for_guild(args.onboarding_profile, policy.guild_id)
    token = read_token(args.token_file)
    worker = await PipeWorker.open()
    if args.conversation != (worker.ready.model_binding_digest is not None):
        _refuse("conversation_worker_flag_mismatch")
    if worker.ready.policy_digest != policy.digest:
        _refuse("worker_policy_mismatch")
    journal = EffectJournal(args.effects_dir)
    service: ReachService | None = None
    with journal.session():
        rest = DiscordRest(
            token=token,
            application_id=policy.application_id,
            bot_user_id=policy.bot_user_id,
            guild_id=policy.guild_id,
            journal=journal,
            observer=OperationObserver(
                generation=worker.ready.generation,
                producer_id="reach.discord-rest",
                source="reach.discord-rest",
                target="reach.discord-api",
                sink=lambda event: write_diagnostic_line(observation_bytes(event)),
            ),
        )
        try:
            publications, publication_effects = _publication_profile(args, rest)
            inspection = GuildInspection(rest)
            service = ReachService(
                policy,
                worker,
                ReplyEffects(rest, policy),
                admin_users=frozenset(args.admin_user),
                history_enabled=args.history,
                conversation=args.conversation,
                publications=publications,
                publication_effects=publication_effects,
                inspection=inspection,
            )
            onboarding = None
            if onboarding_profile is not None:
                onboarding = OnboardingService(
                    onboarding_profile,
                    OnboardingEffects(
                        rest,
                        roles=frozenset((onboarding_profile.magus_role_id, onboarding_profile.bot_role_id)),
                        panel_channel=onboarding_profile.channel_id,
                        panel_message=onboarding_profile.panel_message_id,
                        introduction_channel=onboarding_profile.introduction_channel_id,
                    ),
                    tasks=service.tasks,
                )
            bot = ReachBot(service, command_name=args.command_name, onboarding=onboarding)
            async with bot:
                await bot.login(token)
                actual = await bot.application_info()
                if (
                    bot.user is None
                    or str(bot.user.id) != policy.bot_user_id
                    or str(actual.id) != policy.application_id
                ):
                    _refuse("discord_identity_mismatch")
                snapshot = await snapshot_guild(inspection)
                observed_channels = {channel.id for channel in snapshot.channels}
                selected_channels = {
                    *policy.allowed_channel_ids,
                    *policy.allowed_thread_parent_ids,
                    *args.publication_channel,
                }
                if not selected_channels <= observed_channels:
                    _refuse("discord_channel_binding")
                if onboarding is not None:
                    await verify_onboarding(onboarding, snapshot, actual.flags)
                if args.sync_commands:
                    await bot.tree.sync(guild=discord.Object(id=int(policy.guild_id)))
                diagnostic("connecting")
                await bot.connect(reconnect=True)
        finally:
            if service is not None:
                await _retire_generation(service.tasks)
            await rest.close()


async def _retire_generation(tasks: EdgeTasks) -> None:
    """Fail-stop this edge if business work cannot retire before dependency release."""
    try:
        await tasks.close()
    except TimeoutError:
        diagnostic("retirement_failed")
        # Only kernel process death can safely release the writer lease with live callbacks.
        os._exit(1)


def startup_error_code(error: Exception) -> str:
    """Translate startup failures without rendering foreign exception payloads."""
    if isinstance(error, discord.LoginFailure):
        return "login_failed"
    if isinstance(error, discord.PrivilegedIntentsRequired):
        return "privileged_intent_required"
    if isinstance(error, DiscordRestError):
        return error.code
    safe_codes = {
        "history_policy_flag_mismatch",
        "conversation_policy_flag_mismatch",
        "conversation_worker_flag_mismatch",
        "publication_configuration",
        "command_name",
        "worker_readiness",
        "worker_policy_mismatch",
        "discord_identity_mismatch",
        "discord_channel_binding",
        "credential_permissions",
        "credential_shape",
        "onboarding_profile_permissions",
        "onboarding_profile_limit",
        "onboarding_profile_json",
        "onboarding_identity_or_intent",
        "onboarding_channel_binding",
        "onboarding_channel_not_public",
        "onboarding_role_permissions",
        "onboarding_role_binding",
        "onboarding_panel_binding",
        "onboarding_guild_binding",
        "policy_too_large",
    }
    if isinstance(error, ValueError) and str(error) in safe_codes:
        return str(error)
    return "edge_stopped"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--effects-dir", type=Path, required=True)
    parser.add_argument("--admin-user", action="append", default=[])
    parser.add_argument("--sync-commands", action="store_true")
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--conversation", action="store_true")
    parser.add_argument("--publications-dir", type=Path)
    parser.add_argument("--publication-channel", action="append", default=[])
    parser.add_argument("--command-name", default="reach")
    parser.add_argument("--onboarding-profile", type=Path)
    args = parser.parse_args(argv)
    previous_level = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130
    except Exception as error:  # noqa: BLE001 - no exception payload may expose credentials or Discord content
        diagnostic(startup_error_code(error))
        return 1
    finally:
        logging.disable(previous_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
