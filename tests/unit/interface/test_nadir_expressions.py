"""Admitted dialogue uses a cosmetic receipt and decorates successful final delivery."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from lychd.compositions.reach.operator_wire import ReachWorkerResult
from lychd.interface.discord.live import ReachCog, ReachService
from lychd.interface.discord.ports import ReplyEffects
from lychd.interface.discord.rest import DiscordRestError, EffectResult
from tests.unit.compositions.test_reach_expressions import expressions
from tests.unit.interface.test_nadir_dialogue import direct_message, policy, worker


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["none", "seen", "seen_exception", "final", "reaction", "gif"])
async def test_expression_order_and_cosmetic_failures_preserve_the_answer(failure: str) -> None:
    configured, message = policy(), direct_message()
    native = worker(configured)
    native.ready = native.ready.model_copy(
        update={"expressions": expressions(), "adaptive_context": True, "model_binding_digest": "a" * 64}
    )
    timeline: list[str] = []

    async def send_message(_channel: str, _text: str, **kwargs: Any) -> EffectResult:
        phase = kwargs["phase"]
        timeline.append(phase)
        return EffectResult(status="unknown" if failure == "final" and phase == "final" else "succeeded")

    async def add_reaction(channel: str, target: str, emoji: str, **kwargs: Any) -> EffectResult:
        phase = kwargs["phase"]
        timeline.append(phase)
        assert (channel, target, kwargs["event_id"]) == ("204", "110", "110")
        assert emoji == ("👀" if phase == "seen" else "👍")
        if phase == "seen" and failure == "seen_exception":
            code = "network_error"
            raise DiscordRestError(code)
        return EffectResult(status="unknown" if failure == ("seen" if phase == "seen" else "reaction") else "succeeded")

    async def send_gif(channel: str, url: str, **kwargs: Any) -> EffectResult:
        timeline.append("gif")
        assert channel == "204"
        assert url == expressions().gifs[0].url
        assert kwargs == {"event_id": "110", "reply_to": "110"}
        return EffectResult(status="unknown" if failure == "gif" else "succeeded")

    async def generate(*_args: Any, **_kwargs: Any) -> ReachWorkerResult:
        timeline.append("native")
        return ReachWorkerResult(
            request_id="request",
            status="conversation",
            text="A completed answer.",
            reaction="👍",
            gif_id="cheer",
            policy_digest=configured.digest,
            corpus_digest="c" * 64,
            model_binding_digest="a" * 64,
        )

    native.request.side_effect = generate
    rest = Mock(
        bind_direct_channel=AsyncMock(),
        send_message=AsyncMock(side_effect=send_message),
        add_reaction=AsyncMock(side_effect=add_reaction),
        send_gif=AsyncMock(side_effect=send_gif),
    )
    service = ReachService(
        configured,
        native,
        ReplyEffects(rest, configured),
        admin_users=frozenset(),
        history_enabled=False,
        conversation=True,
    )
    cog = ReachCog(service)
    await cog.on_message(message)
    await cog.on_message(message)
    expected = ["seen", "native", "final"]
    if failure not in {"seen", "seen_exception", "final"}:
        expected.append("reply")
        if failure != "reaction":
            expected.append("gif")
    assert timeline == expected
    native.request.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("slash", [False, True])
async def test_disabled_or_command_expressions_do_not_publish_any_decorations(*, slash: bool) -> None:
    configured, message = policy(), direct_message()
    native = worker(configured)
    if slash:
        native.ready = native.ready.model_copy(
            update={"expressions": expressions(), "adaptive_context": True, "model_binding_digest": "a" * 64}
        )
    result = ReachWorkerResult(
        request_id="request",
        status="conversation",
        text="Answer.",
        policy_digest=configured.digest,
        corpus_digest="c" * 64,
        model_binding_digest="a" * 64 if slash else None,
        reaction="👍" if slash else None,
        gif_id="cheer" if slash else None,
    )
    native.request.return_value = result
    rest = Mock(
        add_reaction=AsyncMock(),
        send_gif=AsyncMock(),
        bind_direct_channel=AsyncMock(),
        send_message=AsyncMock(return_value=EffectResult(status="succeeded")),
        edit_interaction_original=AsyncMock(return_value=EffectResult(status="succeeded")),
    )
    service = ReachService(
        configured,
        native,
        ReplyEffects(rest, configured),
        admin_users=frozenset(),
        history_enabled=False,
        conversation=True,
    )
    cog = ReachCog(service)
    if slash:
        interaction = Mock(spec=discord.Interaction)
        interaction.application_id, interaction.guild_id, interaction.channel_id = 101, 103, 104
        interaction.id, interaction.created_at = message.id, message.created_at
        interaction.user = Mock(spec=discord.Member, id=105, bot=False, display_name="Current Person", roles=[])
        interaction.channel = Mock(spec=discord.TextChannel, id=104)
        interaction.token = "synthetic-interaction-token"  # noqa: S105 - inert interaction fixture
        interaction.response = Mock(defer=AsyncMock())
        callback = cast("Callable[[ReachCog, discord.Interaction, str], Awaitable[None]]", cog.ask.callback)
        await callback(cog, interaction, "Send something cheerful.")
        interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        rest.edit_interaction_original.assert_awaited_once()
        rest.send_message.assert_not_awaited()
    else:
        await cog.on_message(message)
        rest.send_message.assert_awaited_once()
        assert rest.send_message.await_args.kwargs["phase"] == "final"
    native.request.assert_awaited_once()
    rest.add_reaction.assert_not_awaited()
    rest.send_gif.assert_not_awaited()
