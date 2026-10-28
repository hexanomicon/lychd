from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from lychd.interface.discord.admin import GuildSnapshot
from lychd.interface.discord.live import ReachBot, ReachService, verify_onboarding
from lychd.interface.discord.onboarding import OnboardingPanel, OnboardingProfile, OnboardingService
from lychd.interface.discord.rest import EffectResult


def onboarding() -> OnboardingService:
    profile = OnboardingProfile(
        guild_id="300000000000000003",
        channel_id="400000000000000004",
        panel_message_id="700000000000000007",
        magus_role_id="600000000000000006",
        bot_role_id="800000000000000008",
    )
    rest = Mock(application_id="100000000000000001", bot_user_id="200000000000000002", guild_id=profile.guild_id)
    rest.ensure_member_role = AsyncMock(return_value=EffectResult(status="succeeded"))
    rest.get_message = AsyncMock(
        return_value={
            "id": profile.panel_message_id,
            "channel_id": profile.channel_id,
            "author": {"id": rest.bot_user_id, "bot": True},
        }
    )
    return OnboardingService(profile, rest)


def reach() -> Any:
    result = Mock(spec=ReachService)
    result.history_enabled = False
    result.policy = Mock(guild_id="300000000000000003")
    result.publications = None
    return result


def member(configured: OnboardingService) -> Any:
    result = Mock(spec=discord.Member)
    result.id = 500000000000000005
    result.guild = Mock(id=int(configured.profile.guild_id))
    result.bot = False
    result.roles = []
    result.joined_at = datetime(2026, 10, 28, 10, 0, tzinfo=UTC)
    return result


def snapshot(configured: OnboardingService) -> Any:
    profile = configured.profile
    result = Mock(spec=GuildSnapshot)
    result.guild_id = profile.guild_id
    result.application_id = configured.rest.application_id
    result.bot_user_id = configured.rest.bot_user_id
    result.bot_role_ids = ("900000000000000009",)
    result.roles = [
        Mock(id=profile.guild_id, name="@everyone", permissions=1 << 10, position=0, managed=False),
        Mock(id=profile.magus_role_id, name="Magus", permissions=0, position=1, managed=False),
        Mock(id=profile.bot_role_id, name="Bot", permissions=0, position=2, managed=False),
        Mock(id="900000000000000009", name="Application", permissions=1 << 28, position=3, managed=True),
    ]
    # Mock's name argument names the mock itself, rather than the role's name attribute.
    for role, name in zip(result.roles, ("@everyone", "Magus", "Bot", "Application"), strict=True):
        role.name = name
    channel = Mock(id=profile.channel_id, type=0, overwrites=[])
    channel.name = "start-here"
    result.channels = [channel]
    return result


@pytest.mark.asyncio
async def test_onboarding_alone_enables_member_intent_and_registers_persistent_panel() -> None:
    default = ReachBot(reach())
    enabled = ReachBot(reach(), onboarding=onboarding())
    async with default, enabled:
        await default.setup_hook()
        await enabled.setup_hook()
        assert not default.intents.members
        assert not default.intents.presences
        assert default.persistent_views == []
        assert enabled.intents.members
        assert not enabled.intents.presences
        assert not enabled.intents.message_content
        assert len(enabled.persistent_views) == 1
        assert isinstance(enabled.persistent_views[0], OnboardingPanel)
        assert enabled._connection.member_cache_flags.value == 0


@pytest.mark.asyncio
async def test_member_join_uses_join_timestamp_and_skips_existing_roles_and_wrong_guild() -> None:
    configured = onboarding()
    bot = ReachBot(reach(), onboarding=configured)
    observed = member(configured)
    async with bot:
        await bot.on_member_join(observed)
        configured.rest.ensure_member_role.assert_awaited_once_with(
            str(observed.id),
            configured.profile.magus_role_id,
            event_id=str(discord.utils.time_snowflake(observed.joined_at)),
        )
        assert configured.rest.ensure_member_role.await_args.kwargs["event_id"] != str(observed.id)
        observed.roles = [Mock(id=int(configured.profile.magus_role_id))]
        await bot.on_member_join(observed)
        observed.guild.id += 1
        await bot.on_member_join(observed)
        assert configured.rest.ensure_member_role.await_count == 1


@pytest.mark.asyncio
async def test_join_guard_and_unsuccessful_role_result_have_only_fixed_diagnostics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configured = onboarding()
    bot = ReachBot(reach(), onboarding=configured)
    observed = member(configured)
    async with bot:
        observed.joined_at = None
        await bot.on_member_join(observed)
        configured.rest.ensure_member_role.assert_not_awaited()
        observed.joined_at = datetime(2026, 10, 28, tzinfo=UTC)
        configured.rest.ensure_member_role.return_value = EffectResult(
            status="rejected", code="private_foreign_payload"
        )
        await bot.on_member_join(observed)
    assert capsys.readouterr().err.splitlines() == [
        "reach_discord:onboarding_join_identity",
        "reach_discord:onboarding_role_failed",
    ]


@pytest.mark.asyncio
async def test_backfill_runs_once_with_bounded_member_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    configured = onboarding()
    bot = ReachBot(reach(), onboarding=configured)
    observed = member(configured)

    async def members() -> Any:
        yield observed

    guild = Mock()
    guild.fetch_members.return_value = members()
    monkeypatch.setattr(bot, "get_guild", Mock(return_value=guild))
    async with bot:
        await bot.on_ready()
        task = bot.onboarding_backfill_task
        assert task is not None
        await task
        await bot.on_ready()
        assert bot.onboarding_backfill_task is task
        guild.fetch_members.assert_called_once_with(limit=1000)
        configured.rest.ensure_member_role.assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_binds_only_verified_roles_panel_and_public_introduction_channel() -> None:
    configured = onboarding()
    flags = Mock(gateway_guild_members=True, gateway_guild_members_limited=False)
    await verify_onboarding(configured, snapshot(configured), flags)
    configured.rest.bind_member_roles.assert_called_once_with(
        (configured.profile.magus_role_id, configured.profile.bot_role_id)
    )
    configured.rest.bind_introduction_channel.assert_called_once_with(configured.profile.channel_id)


@pytest.mark.asyncio
async def test_startup_accepts_display_emoji_and_discord_role_position_ties() -> None:
    configured = onboarding()
    observed = snapshot(configured)
    observed.channels[0].name = "👋・start-here"
    observed.roles[1].name = "🔮 Magus"
    observed.roles[2].name = "🤖 Bot"
    observed.roles[2].position = 1
    observed.roles[3].id = "550000000000000005"
    observed.roles[3].position = 1
    observed.bot_role_ids = (observed.roles[3].id,)
    flags = Mock(gateway_guild_members=True, gateway_guild_members_limited=False)
    await verify_onboarding(configured, observed, flags)
    configured.rest.bind_member_roles.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind",
    [
        "private",
        "role_exception",
        "wrong_role_name",
        "managed",
        "permissions",
        "hierarchy",
        "panel_author",
        "webhook",
        "intent",
    ],
)
async def test_startup_refuses_private_channel_or_unsafe_resource_binding(kind: str) -> None:
    configured = onboarding()
    observed = snapshot(configured)
    flags = Mock(gateway_guild_members=True, gateway_guild_members_limited=False)
    if kind in {"private", "role_exception"}:
        observed.roles[0].permissions = 0
        if kind == "role_exception":
            observed.channels[0].overwrites = [Mock(id=configured.profile.magus_role_id, type=0, allow=1 << 10, deny=0)]
    elif kind == "wrong_role_name":
        observed.roles[1].name = "Admin"
    elif kind == "managed":
        observed.roles[1].managed = True
    elif kind == "permissions":
        observed.roles[1].permissions = 1 << 3
    elif kind == "hierarchy":
        observed.roles[1].position = 3
    elif kind == "panel_author":
        configured.rest.get_message.return_value["author"]["id"] = "500000000000000005"
    elif kind == "webhook":
        configured.rest.get_message.return_value["webhook_id"] = "500000000000000005"
    else:
        flags.gateway_guild_members = False
    with pytest.raises(ValueError, match="onboarding_"):
        await verify_onboarding(configured, observed, flags)
    configured.rest.bind_member_roles.assert_not_called()
    configured.rest.bind_introduction_channel.assert_not_called()
