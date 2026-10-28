from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, cast
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from lychd.compositions.reach.operator_wire import ReachHistoryEntry, ReachWorkerReady, ReachWorkerResult
from lychd.interface.discord.live import (
    PipeWorker,
    ReachBot,
    ReachCog,
    ReachService,
    event_from_interaction,
    event_from_message,
    result_text,
    startup_error_code,
)
from lychd.interface.discord.operator_io import load_policy, read_token
from lychd.interface.discord.rest import DiscordRestError, EffectResult
from lychd.interface.discord.schemas import DiscordPolicy

ROOT = Path(__file__).resolve().parents[3]
NOW = datetime.now(UTC)


def policy() -> DiscordPolicy:
    return load_policy(ROOT / "examples" / "reach" / "policy.toml")


def message() -> Any:
    value = Mock(spec=discord.Message)
    value.id = 777777777777777777
    value.guild = Mock(id=333333333333333333)
    value.channel = Mock(spec=discord.TextChannel)
    value.channel.id = 444444444444444444
    value.author = Mock(spec=discord.Member)
    value.author.id = 555555555555555555
    value.author.bot = False
    value.author.roles = [Mock(id=666666666666666666)]
    value.webhook_id = None
    value.mentions = [Mock(id=222222222222222222)]
    value.content = "<@222222222222222222> extension authoring"
    value.created_at = NOW
    return value


def ready() -> ReachWorkerReady:
    return ReachWorkerReady(
        generation="bd9383c7-46c0-43da-82af-c428a5568362",
        started_at=NOW - timedelta(seconds=1),
        policy_digest=policy().digest,
        corpus_digest="c" * 64,
    )


def service() -> ReachService:
    worker = Mock()
    worker.ready = ready()
    worker.available = True
    worker.lock = asyncio.Lock()
    worker.request = AsyncMock(
        return_value=ReachWorkerResult(
            request_id="request",
            status="docs",
            text="Public excerpt",
            run_id="run",
            policy_digest=policy().digest,
            corpus_digest="c" * 64,
        )
    )
    return ReachService(policy(), worker, Mock(), admin_users=frozenset(), history_enabled=False)


def test_sdk_event_preserves_identity_and_roles() -> None:
    event = event_from_message(message(), policy())
    assert event is not None
    assert event.question == "extension authoring"
    assert event.subject_id == "555555555555555555"
    assert event.group_ids == ("666666666666666666",)


@pytest.mark.parametrize("kind", ["ambient", "dm", "bot", "webhook", "wrong_guild", "wrong_channel"])
def test_sdk_ignores_unselected_message_without_reading_content(kind: str) -> None:
    observed = message()
    observed.content = object()
    if kind == "ambient":
        observed.mentions = []
    elif kind == "dm":
        observed.guild = None
    elif kind == "bot":
        observed.author.bot = True
    elif kind == "webhook":
        observed.webhook_id = 888888888888888888
    elif kind == "wrong_guild":
        observed.guild.id = 888888888888888888
    else:
        observed.channel.id = 888888888888888888
    assert event_from_message(observed, policy()) is None


def test_sdk_interaction_uses_observed_application_and_member() -> None:
    observed = message()
    interaction = Mock(spec=discord.Interaction)
    interaction.application_id = 111111111111111111
    interaction.guild_id = observed.guild.id
    interaction.channel_id = observed.channel.id
    interaction.id = observed.id
    interaction.user = observed.author
    interaction.created_at = NOW
    event = event_from_interaction(interaction, policy(), question="extensions", action="answer_docs")
    assert event is not None
    assert event.trigger == "command"
    interaction.application_id = 888888888888888888
    assert event_from_interaction(interaction, policy(), question="extensions", action="answer_docs") is None


@pytest.mark.asyncio
async def test_shared_gate_and_generation_fence_precede_worker_and_history() -> None:
    configured = service()
    event = event_from_message(message(), policy())
    assert event is not None
    channel = Mock(spec=discord.TextChannel)
    channel.id = int(event.conversation_id)
    assert await configured.run_event(event, channel) is not None
    assert await configured.run_event(event, channel) is None
    cast("AsyncMock", configured.worker.request).assert_awaited_once()
    channel.history.assert_not_called()
    assert not configured.eligible(event.model_copy(update={"subject_id": "888888888888888888", "group_ids": ()}))
    assert not configured.eligible(event.model_copy(update={"occurred_at": NOW - timedelta(minutes=1)}))


@pytest.mark.asyncio
async def test_local_cog_registration_never_syncs_globally_or_requests_privileged_intents() -> None:
    bot = ReachBot(service())
    async with bot:
        await bot.setup_hook()
        commands = bot.tree.get_commands(guild=discord.Object(id=333333333333333333))
        assert [command.name for command in commands] == ["reach"]
        assert bot.tree.get_commands() == []
        assert not bot.intents.members
        assert not bot.intents.presences
        assert not bot.intents.message_content
        assert bot.intents.guild_messages
        assert bot.allowed_mentions is not None
        assert not bot.allowed_mentions.everyone


@pytest.mark.asyncio
async def test_command_alias_uses_public_group_without_global_registration() -> None:
    bot = ReachBot(service(), command_name="nadir")
    async with bot:
        await bot.setup_hook()
        commands = bot.tree.get_commands(guild=discord.Object(id=333333333333333333))
        assert [command.name for command in commands] == ["nadir"]
        assert bot.tree.get_commands() == []


@pytest.mark.parametrize("name", ["Nadir", "two words", "nadir-update", "", "x" * 33])
def test_invalid_command_alias_is_rejected(name: str) -> None:
    with pytest.raises(ValueError, match="command_name"):
        ReachBot(service(), command_name=name)


@pytest.mark.parametrize("status", ["refused", "error", "empty"])
def test_empty_worker_outcome_renders_fixed_useful_message(status: Literal["empty", "refused", "error"]) -> None:
    result = ReachWorkerResult(
        request_id="request",
        status=status,
        policy_digest=policy().digest,
        corpus_digest="c" * 64,
        reason="foreign_failure",
    )
    text = result_text(result)
    assert text.strip()
    assert "foreign_failure" not in text
    assert "oprávnenia" in text if status == "refused" else "neskôr" in text


@pytest.mark.asyncio
async def test_worker_correlation_failure_permanently_fences_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = asyncio.StreamReader()
    worker = PipeWorker(reader, ready())
    observed = event_from_message(message(), policy())
    assert observed is not None
    result = ReachWorkerResult(
        request_id="wrong",
        status="docs",
        text="excerpt",
        policy_digest=policy().digest,
        corpus_digest="c" * 64,
    )
    reader.feed_data(result.model_dump_json().encode() + b"\n")
    output = Mock()
    monkeypatch.setattr("lychd.interface.discord.live.sys.stdout", Mock(buffer=output))
    with pytest.raises(ValueError, match="worker_correlation"):
        await worker.request(observed, ())
    assert not worker.available
    with pytest.raises(ValueError, match="worker_busy_or_unavailable"):
        await worker.request(observed, ())


def test_token_is_owner_only_and_never_a_symlink(tmp_path: Path) -> None:
    token = tmp_path / "token"
    token.write_text("synthetic.only-for-tests.abcdefghijklmnop")
    token.chmod(0o600)
    assert read_token(token) == "synthetic.only-for-tests.abcdefghijklmnop"
    token.chmod(0o644)
    with pytest.raises(ValueError, match="credential_permissions"):
        read_token(token)
    token.chmod(0o600)
    link = tmp_path / "linked"
    link.symlink_to(token)
    with pytest.raises(OSError, match="symbolic link"):
        read_token(link)


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (discord.LoginFailure("foreign credential payload"), "login_failed"),
        (DiscordRestError("discord_identity_mismatch"), "discord_identity_mismatch"),
        (ValueError("worker_readiness"), "worker_readiness"),
        (ValueError("foreign credential payload"), "edge_stopped"),
        (RuntimeError("foreign message content"), "edge_stopped"),
    ],
)
def test_startup_diagnostics_hide_foreign_error_payloads(error: Exception, code: str) -> None:
    assert startup_error_code(error) == code


@pytest.mark.asyncio
async def test_history_respects_aggregate_utf8_budget_before_serialization() -> None:
    configured = service()
    profile = policy()
    configured.policy = type(profile).model_validate({**profile.model_dump(), "context_message_limit": 50})
    configured.history_enabled = True
    observed = event_from_message(message(), policy())
    assert observed is not None

    async def messages(**kwargs: Any) -> Any:
        assert kwargs["limit"] == 50
        for index in range(50):
            item = message()
            item.id += index + 1
            item.content = "ž" * 2000
            item.created_at = NOW - timedelta(seconds=index + 1)
            yield item

    channel = Mock()
    channel.history = messages
    history = await configured.history(channel, observed)
    assert len(history) == 4
    assert sum(len(item.text.encode("utf-8")) for item in history) <= 16_384


@pytest.mark.asyncio
async def test_local_frame_rejection_does_not_poison_worker_connection() -> None:
    worker = PipeWorker(asyncio.StreamReader(), ready())
    observed = event_from_message(message(), policy())
    assert observed is not None
    oversized = tuple(
        ReachHistoryEntry(
            subject_id="subject",
            event_id=str(index + 1),
            conversation_id=observed.conversation_id,
            text="ž" * 2000,
            occurred_at=NOW - timedelta(seconds=index + 1),
        )
        for index in range(50)
    )
    with pytest.raises(ValueError, match="output_limit"):
        await worker.request(observed, oversized)
    assert worker.available


@pytest.mark.asyncio
@pytest.mark.parametrize("available", [True, False])
async def test_status_reports_worker_availability_without_requesting_work(*, available: bool) -> None:
    configured = service()
    configured.worker.available = available
    observed = message()
    interaction = Mock(spec=discord.Interaction)
    interaction.application_id = 111111111111111111
    interaction.guild_id = observed.guild.id
    interaction.channel_id = observed.channel.id
    interaction.id = observed.id
    interaction.user = observed.author
    interaction.created_at = NOW
    interaction.response = Mock(send_message=AsyncMock())
    cog = ReachCog(configured)

    callback = cast("Callable[[ReachCog, discord.Interaction], Awaitable[None]]", cog.status.callback)
    await callback(cog, interaction)

    expected = (
        "Reach operator: dokumentačný worker je pripravený."
        if available
        else "Reach operator: dokumentačný worker nie je dostupný."
    )
    interaction.response.send_message.assert_awaited_once_with(expected, ephemeral=True)
    cast("AsyncMock", configured.worker.request).assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["ask", "inspect", "mention"])
@pytest.mark.parametrize("status", ["succeeded", "rejected", "unknown"])
async def test_effect_outcomes_report_failure_without_retrying(
    path: Literal["ask", "inspect", "mention"],
    status: Literal["succeeded", "rejected", "unknown"],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    configured = service()
    configured.admin_users = frozenset({"555555555555555555"})
    outcome = EffectResult(status=status)
    edit = AsyncMock(return_value=outcome)
    send = AsyncMock(return_value=outcome)
    configured.rest.edit_interaction_original = edit
    configured.rest.send_message = send
    snapshot = AsyncMock(return_value=Mock(roles=(), channels=()))
    monkeypatch.setattr("lychd.interface.discord.live.snapshot_guild", snapshot)
    observed = message()
    interaction = Mock(spec=discord.Interaction)
    interaction.application_id = 111111111111111111
    interaction.guild_id = observed.guild.id
    interaction.channel_id = observed.channel.id
    interaction.channel = observed.channel
    interaction.id = observed.id
    interaction.user = observed.author
    interaction.created_at = NOW
    interaction.token = "synthetic-interaction-token"  # noqa: S105 - inert interaction fixture
    interaction.response = Mock(defer=AsyncMock())
    cog = ReachCog(configured)

    if path == "mention":
        await cog.on_message(observed)
        send.assert_awaited_once_with(
            str(observed.channel.id), "Public excerpt", event_id=str(observed.id), reply_to=str(observed.id)
        )
        edit.assert_not_awaited()
        code = "message_failed"
    elif path == "inspect":
        inspect_callback = cast(
            "Callable[[ReachCog, discord.Interaction], Awaitable[None]]", cog.admin_inspect.callback
        )
        await inspect_callback(cog, interaction)
        snapshot.assert_awaited_once()
        edit.assert_awaited_once()
        send.assert_not_awaited()
        code = "inspection_failed"
    else:
        ask_callback = cast("Callable[[ReachCog, discord.Interaction, str], Awaitable[None]]", cog.ask.callback)
        await ask_callback(cog, interaction, "extensions")
        edit.assert_awaited_once()
        send.assert_not_awaited()
        code = "request_failed"

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ("" if status == "succeeded" else f"reach_discord:{code}\n")


@pytest.mark.asyncio
async def test_conversation_history_is_chronological_and_includes_only_own_bot() -> None:
    configured = service()
    configured.conversation = True
    configured.history_enabled = True
    configured.policy = policy().model_copy(update={"context_message_limit": 10})
    observed = event_from_message(message(), configured.policy, conversation=True)
    assert observed is not None
    assert observed.action == "converse"

    async def messages(**kwargs: Any) -> Any:
        del kwargs
        for index, author in enumerate((configured.policy.bot_user_id, "888888888888888888", observed.subject_id)):
            item = message()
            item.id += index + 1
            item.author.id = int(author)
            item.author.bot = author != observed.subject_id
            item.author.display_name = "Vesper" if author == configured.policy.bot_user_id else "Chirayu"
            item.created_at = NOW - timedelta(seconds=index + 1)
            yield item

    channel = Mock(history=messages)
    history = await configured.history(channel, observed)
    assert [entry.subject_id for entry in history] == [observed.subject_id, configured.policy.bot_user_id]
    assert [entry.subject_label for entry in history] == ["Chirayu", "Vesper"]


def test_only_observed_discord_thread_can_supply_admitted_parent() -> None:
    configured = policy().model_copy(update={"allowed_thread_parent_ids": ("444444444444444444",)})
    observed = message()
    observed.channel = Mock(spec=discord.Thread)
    observed.channel.id = 999999999999999999
    observed.channel.parent_id = 444444444444444444
    event = event_from_message(observed, configured, conversation=True)
    assert event is not None
    assert event.parent_conversation_id == "444444444444444444"
    observed.channel = Mock(spec=discord.TextChannel)
    observed.channel.id = 999999999999999999
    observed.channel.parent_id = 444444444444444444
    assert event_from_message(observed, configured, conversation=True) is None


@pytest.mark.asyncio
async def test_busy_worker_refuses_before_history() -> None:
    configured = service()
    configured.worker.available = False
    observed = event_from_message(message(), configured.policy)
    assert observed is not None
    channel = Mock(spec=discord.TextChannel)
    channel.id = int(observed.conversation_id)
    with pytest.raises(ValueError, match="worker_busy_or_unavailable"):
        await configured.run_event(observed, channel)
    channel.history.assert_not_called()
