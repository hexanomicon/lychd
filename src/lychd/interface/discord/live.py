"""Credential-only Gateway edge; native execution lives in another OCI process."""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NoReturn
from uuid import uuid4

import discord
from discord import app_commands
from discord.ext import commands

from lychd.compositions.reach.operator_wire import (
    MAX_WIRE_BYTES,
    ReachHistoryEntry,
    ReachWorkerReady,
    ReachWorkerRequest,
    ReachWorkerResult,
    protocol_bytes,
)
from lychd.compositions.reach.policy import prepare_turn
from lychd.compositions.reach.schemas import ReachEvent
from lychd.interface.discord.admin import snapshot_guild
from lychd.interface.discord.operator_io import load_policy, read_token
from lychd.interface.discord.publications import PublicationQueue
from lychd.interface.discord.rest import DiscordRest, DiscordRestError, EffectJournal
from lychd.interface.discord.schemas import DiscordPolicy

MAX_HISTORY_BYTES = 16_384
MAX_GENERATION_EVENTS = 10_000
MAX_GENERATION_THREADS = 1000
_COMMAND_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}\Z")


def _refuse(code: str) -> NoReturn:
    raise ValueError(code)


def diagnostic(code: str) -> None:
    """Keep protocol stdout and diagnostics free of payloads and credentials."""
    sys.stderr.write(f"reach_discord:{code}\n")


def result_text(result: ReachWorkerResult) -> str:
    """Render payload-free worker refusals without attempting an empty message."""
    if result.text.strip():
        return result.text
    if result.status == "refused":
        return "Túto požiadavku nemôžem vykonať. Skontroluj oprávnenia a povolený kanál."
    return "Odpoveď sa nepodarilo pripraviť. Skús novú požiadavku neskôr."


class PipeWorker:
    """One bounded outstanding request on the supervisor's private standard streams."""

    def __init__(self, reader: asyncio.StreamReader, ready: ReachWorkerReady) -> None:
        """Bind exactly one worker generation to the private pipe."""
        self.reader = reader
        self.ready = ready
        self.lock = asyncio.Lock()
        self.available = True

    @classmethod
    async def open(cls) -> PipeWorker:
        reader = asyncio.StreamReader(limit=MAX_WIRE_BYTES)
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_running_loop().connect_read_pipe(lambda: protocol, sys.stdin.buffer)
        async with asyncio.timeout(30):
            raw = await reader.readline()
        if not raw or len(raw) > MAX_WIRE_BYTES:
            msg = "worker_readiness"
            raise ValueError(msg)
        return cls(reader, ReachWorkerReady.model_validate_json(raw))

    async def request(self, event: ReachEvent, history: tuple[ReachHistoryEntry, ...]) -> ReachWorkerResult:
        if not self.available or self.lock.locked():
            msg = "worker_busy_or_unavailable"
            raise ValueError(msg)
        request = ReachWorkerRequest(request_id=str(uuid4()), event=event, history=history)
        frame = protocol_bytes(request)
        async with self.lock:
            try:
                sys.stdout.buffer.write(frame)
                sys.stdout.buffer.flush()
                async with asyncio.timeout(90):
                    raw = await self.reader.readline()
                if not raw or len(raw) > MAX_WIRE_BYTES:
                    _refuse("worker_protocol")
                result = ReachWorkerResult.model_validate_json(raw)
                if (
                    result.request_id != request.request_id
                    or result.policy_digest != self.ready.policy_digest
                    or result.corpus_digest != self.ready.corpus_digest
                    or result.model_binding_digest != self.ready.model_binding_digest
                ):
                    _refuse("worker_correlation")
            except (ValueError, OSError, TimeoutError, asyncio.CancelledError):
                self.available = False
                raise
            return result


def _parent(channel: object, policy: DiscordPolicy) -> str | None:
    if isinstance(channel, discord.Thread) and str(channel.parent_id) in policy.allowed_thread_parent_ids:
        return str(channel.parent_id)
    return None


def event_from_message(
    message: discord.Message, policy: DiscordPolicy, *, conversation: bool = False
) -> ReachEvent | None:
    """Translate SDK identity after cheap rejection, without retaining ambient messages."""
    if (
        message.guild is None
        or str(message.guild.id) != policy.guild_id
        or (str(message.channel.id) not in policy.allowed_channel_ids and _parent(message.channel, policy) is None)
        or message.author.bot
        or message.webhook_id is not None
        or not isinstance(message.author, discord.Member)
        or not any(str(person.id) == policy.bot_user_id for person in message.mentions)
    ):
        return None
    question = re.sub(rf"<@!?{re.escape(policy.bot_user_id)}>", "", message.content).strip()
    return ReachEvent(
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
        trigger="mention",
        action="converse" if conversation else "answer_docs",
        question=question,
        occurred_at=message.created_at,
    )


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
        rest: DiscordRest,
        *,
        admin_users: frozenset[str],
        history_enabled: bool,
        conversation: bool = False,
        publications: PublicationQueue | None = None,
    ) -> None:
        """Bind the admitted social policy and separate inspection selectors."""
        self.policy = policy
        self.shared_policy = policy.to_reach_policy()
        self.worker = worker
        self.rest = rest
        self.admin_users = admin_users
        self.history_enabled = history_enabled
        self.conversation = conversation
        self.publications = publications
        self.seen: set[str] = set()
        self.bound_threads: set[str] = set()

    def eligible(self, event: ReachEvent | None) -> bool:
        return (
            event is not None
            and event.occurred_at >= self.worker.ready.started_at
            and prepare_turn(self.shared_policy, event, now=datetime.now(UTC)).allowed
        )

    async def history(self, channel: discord.abc.Messageable, event: ReachEvent) -> tuple[ReachHistoryEntry, ...]:
        if not self.history_enabled or not self.policy.context_message_limit:
            return ()
        entries: list[ReachHistoryEntry] = []
        total_bytes = 0
        cutoff = event.occurred_at - timedelta(seconds=self.policy.context_max_age_seconds)
        async for message in channel.history(
            limit=self.policy.context_message_limit, before=event.occurred_at, after=cutoff, oldest_first=False
        ):
            if (
                str(message.channel.id) != event.conversation_id
                or message.created_at >= event.occurred_at
                or message.created_at < cutoff
                or (
                    message.author.bot and not (self.conversation and str(message.author.id) == self.policy.bot_user_id)
                )
                or message.webhook_id is not None
                or not message.content
            ):
                continue
            text = message.content[:2000]
            size = len(text.encode("utf-8"))
            if total_bytes + size > MAX_HISTORY_BYTES:
                break
            total_bytes += size
            entries.append(
                ReachHistoryEntry(
                    subject_id=str(message.author.id),
                    subject_label=(str(message.author.display_name).strip()[:80] or None),
                    event_id=str(message.id),
                    conversation_id=str(message.channel.id),
                    text=text,
                    occurred_at=message.created_at,
                )
            )
        return tuple(sorted(entries, key=lambda item: (item.occurred_at, int(item.event_id))))

    async def run_event(self, event: ReachEvent, channel: discord.abc.Messageable) -> ReachWorkerResult | None:
        if not self.eligible(event) or event.event_id in self.seen:
            return None
        if not self.worker.available or self.worker.lock.locked():
            _refuse("worker_busy_or_unavailable")
        if str(getattr(channel, "id", None)) != event.conversation_id:
            _refuse("channel_identity_mismatch")
        if event.parent_conversation_id is not None:
            if _parent(channel, self.policy) != event.parent_conversation_id:
                _refuse("thread_parent_mismatch")
            if event.conversation_id not in self.bound_threads:
                if len(self.bound_threads) >= MAX_GENERATION_THREADS:
                    _refuse("generation_thread_budget")
                self.rest.bind_channels((event.conversation_id,))
                self.bound_threads.add(event.conversation_id)
        # A generation-local fence is in addition to the persistent transport journal.
        if len(self.seen) >= MAX_GENERATION_EVENTS:
            msg = "generation_event_budget"
            raise ValueError(msg)
        self.seen.add(event.event_id)
        return await self.worker.request(event, await self.history(channel, event))


class ReachCog(commands.GroupCog, group_name="reach", group_description="Bounded Reach operator tools"):
    def __init__(self, service: ReachService) -> None:
        """Bind one explicitly configured edge, never ambient Core settings."""
        self.service = service

    async def _request(self, interaction: discord.Interaction, question: str, action: str) -> None:
        event = event_from_interaction(interaction, self.service.policy, question=question, action=action)
        if not self.service.eligible(event):
            await interaction.response.send_message("Táto požiadavka tu nie je povolená.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        if event is None or not isinstance(interaction.channel, discord.abc.Messageable):
            return
        try:
            result = await self.service.run_event(event, interaction.channel)
            if result is not None:
                outcome = await self.service.rest.edit_interaction_original(
                    interaction.token, result_text(result), event_id=str(interaction.id)
                )
                if outcome.status != "succeeded":
                    diagnostic("request_failed")
        except (ValueError, OSError, TimeoutError, discord.HTTPException, DiscordRestError):
            diagnostic("request_failed")

    @app_commands.command(description="Ask Reach using this connection's configured mode")
    @app_commands.describe(question="What would you like to ask?")
    async def ask(self, interaction: discord.Interaction, question: str) -> None:
        await self._request(interaction, question, "converse" if self.service.conversation else "answer_docs")

    @app_commands.command(description="Show bounded recent context when explicitly enabled")
    async def context(self, interaction: discord.Interaction) -> None:
        await self._request(interaction, "Recent conversation context", "summarize_context")

    @app_commands.command(description="Show this operator connection's readiness")
    async def status(self, interaction: discord.Interaction) -> None:
        """Report admitted connection availability without issuing native work."""
        event = event_from_interaction(interaction, self.service.policy, question="status", action="answer_docs")
        if not self.service.eligible(event):
            text = "Prístup odmietnutý."
        elif self.service.worker.available:
            text = (
                "Reach operator: konverzačný worker je pripravený."
                if self.service.conversation
                else "Reach operator: dokumentačný worker je pripravený."
            )
        else:
            text = (
                "Reach operator: konverzačný worker nie je dostupný."
                if self.service.conversation
                else "Reach operator: dokumentačný worker nie je dostupný."
            )
        await interaction.response.send_message(text, ephemeral=True)

    @app_commands.command(name="admin-inspect", description="Inspect server setup; administration applies locally")
    async def admin_inspect(self, interaction: discord.Interaction) -> None:
        event = event_from_interaction(interaction, self.service.policy, question="inspect", action="answer_docs")
        if not self.service.eligible(event) or str(interaction.user.id) not in self.service.admin_users:
            await interaction.response.send_message("Prístup odmietnutý.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            snapshot = await snapshot_guild(self.service.rest)
            text = f"Server má {len(snapshot.roles)} rolí a {len(snapshot.channels)} kanálov. Zmeny sa aplikujú lokálnym plánom."
            outcome = await self.service.rest.edit_interaction_original(
                interaction.token, text, event_id=str(interaction.id)
            )
            if outcome.status != "succeeded":
                diagnostic("inspection_failed")
        except (ValueError, OSError, TimeoutError, DiscordRestError):
            diagnostic("inspection_failed")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        event = event_from_message(message, self.service.policy, conversation=self.service.conversation)
        if not self.service.eligible(event) or event is None:
            return
        try:
            result = await self.service.run_event(event, message.channel)
            if result is not None:
                outcome = await self.service.rest.send_message(
                    event.conversation_id, result_text(result), event_id=event.event_id, reply_to=event.event_id
                )
                if outcome.status != "succeeded":
                    diagnostic("message_failed")
        except (ValueError, OSError, TimeoutError, discord.HTTPException, DiscordRestError):
            diagnostic("message_failed")


class ReachBot(commands.Bot):
    def __init__(self, service: ReachService, *, command_name: str = "reach") -> None:
        """Create a slash-only client without privileged member/presence caches."""
        if not _COMMAND_NAME.fullmatch(command_name):
            _refuse("command_name")
        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = service.history_enabled
        super().__init__(
            command_prefix=(),
            help_command=None,
            intents=intents,
            member_cache_flags=discord.MemberCacheFlags.none(),
            chunk_guilds_at_startup=False,
            max_messages=None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.service = service
        self.command_name = command_name
        self.publications_task: asyncio.Task[None] | None = None

    async def setup_hook(self) -> None:
        cog = ReachCog(self.service)
        if cog.app_command is not None:
            cog.app_command.name = self.command_name
        await self.add_cog(cog, guild=discord.Object(id=int(self.service.policy.guild_id)))

    async def on_ready(self) -> None:
        diagnostic("ready")
        if self.service.publications is not None and self.publications_task is None:
            self.publications_task = asyncio.create_task(self._publications())

    async def _publications(self) -> None:
        while not self.is_closed():
            try:
                if self.service.publications is not None:
                    await self.service.publications.process_once(self.service.rest)
            except (ValueError, OSError, DiscordRestError):
                diagnostic("publication_failed")
            await asyncio.sleep(2)

    async def close(self) -> None:
        if self.publications_task is not None:
            self.publications_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.publications_task
        await super().close()

    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
        del event_method, args, kwargs
        diagnostic("gateway_event_failed")


async def run(args: argparse.Namespace) -> None:
    policy = load_policy(args.policy)
    if bool(policy.context_message_limit) != args.history:
        msg = "history_policy_flag_mismatch"
        raise ValueError(msg)
    if args.conversation and not any("converse" in rule.actions for rule in policy.rules):
        _refuse("conversation_policy_flag_mismatch")
    if bool(args.publications_dir) != bool(args.publication_channel):
        _refuse("publication_configuration")
    token = read_token(args.token_file)
    worker = await PipeWorker.open()
    if args.conversation != (worker.ready.model_binding_digest is not None):
        _refuse("conversation_worker_flag_mismatch")
    if worker.ready.policy_digest != policy.digest:
        msg = "worker_policy_mismatch"
        raise ValueError(msg)
    rest = DiscordRest(
        token=token,
        application_id=policy.application_id,
        bot_user_id=policy.bot_user_id,
        guild_id=policy.guild_id,
        journal=EffectJournal(args.effects_dir),
    )
    publications = (
        PublicationQueue(args.publications_dir, allowed_channels=frozenset(args.publication_channel))
        if args.publications_dir
        else None
    )
    service = ReachService(
        policy,
        worker,
        rest,
        admin_users=frozenset(args.admin_user),
        history_enabled=args.history,
        conversation=args.conversation,
        publications=publications,
    )
    bot = ReachBot(service, command_name=args.command_name)
    try:
        async with bot:
            await bot.login(token)
            actual = await bot.application_info()
            if bot.user is None or str(bot.user.id) != policy.bot_user_id or str(actual.id) != policy.application_id:
                msg = "discord_identity_mismatch"
                raise ValueError(msg)
            await rest.verify_identity()
            snapshot = await snapshot_guild(rest)
            observed_channels = {channel.id for channel in snapshot.channels}
            selected_channels = {
                *policy.allowed_channel_ids,
                *policy.allowed_thread_parent_ids,
                *args.publication_channel,
            }
            if not selected_channels <= observed_channels:
                msg = "discord_channel_binding"
                raise ValueError(msg)
            if args.sync_commands:
                await bot.tree.sync(guild=discord.Object(id=int(policy.guild_id)))
            diagnostic("connecting")
            await bot.connect(reconnect=True)
    finally:
        await rest.close()


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
