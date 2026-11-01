"""Nadir's admitted DM reaches acknowledgement, native handoff and journaled replies."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import discord
import httpx
import pytest

from lychd.compositions.reach.operator_wire import ReachWorkerResult
from lychd.interface.discord.live import PipeWorker, ReachCog, ReachService, event_from_message
from lychd.interface.discord.schemas import DiscordPolicy, DiscordRule
from tests.unit.interface.test_discord_history import SDKPage
from tests.unit.interface.test_discord_live import NOW, ready
from tests.unit.interface.test_discord_rest import identity, make_rest, transport


def policy() -> DiscordPolicy:
    return DiscordPolicy(
        application_id="101",
        bot_user_id="102",
        guild_id="103",
        allowed_channel_ids=("104",),
        allowed_dm_user_ids=("105",),
        rules=(DiscordRule(name="person", user_ids=("105",), actions=("converse",)),),
    )


def direct_message() -> Any:
    observed = Mock(spec=discord.Message)
    observed.id, observed.guild = 110, None
    observed.author = Mock(spec=discord.User, id=105, bot=False, display_name="Current Person")
    observed.channel = Mock(spec=discord.DMChannel, id=204, recipient=observed.author)
    observed.webhook_id, observed.reference, observed.mentions = None, None, []
    observed.content, observed.created_at = "Explain the earlier decision.", NOW
    return observed


def worker(configured: DiscordPolicy) -> Any:
    result = Mock(spec=PipeWorker)
    result.ready = ready().model_copy(update={"policy_digest": configured.digest})
    result.available, result.lock = True, asyncio.Lock()
    result.request = AsyncMock()
    return result


@pytest.mark.asyncio
@pytest.mark.parametrize("denial", ["unlisted", "group", "foreign_recipient", "first_subject_rule"])
async def test_dm_denial_precedes_acknowledgement_and_native_request(denial: str) -> None:
    configured, observed = policy(), direct_message()
    if denial == "unlisted":
        configured = configured.model_copy(update={"allowed_dm_user_ids": ()})
    elif denial == "group":
        observed.channel = Mock(spec=discord.GroupChannel, id=204)
    elif denial == "foreign_recipient":
        observed.channel.recipient = Mock(id=999)
    else:
        narrow = DiscordRule(name="first", user_ids=("105",), actions=("answer_docs",))
        configured = configured.model_copy(update={"rules": (narrow, *configured.rules)})
    native, rest = worker(configured), Mock()
    rest.send_message, rest.bind_direct_channel = AsyncMock(), AsyncMock()
    service = ReachService(configured, native, rest, admin_users=frozenset(), history_enabled=False, conversation=True)
    await ReachCog(service).on_message(observed)
    rest.send_message.assert_not_awaited()
    rest.bind_direct_channel.assert_not_awaited()
    native.request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_second_part", [False, True])
async def test_dm_ack_precedes_native_and_multipart_delivery_stops_on_unknown(
    tmp_path: Path,
    *,
    fail_second_part: bool,
) -> None:
    configured, observed = policy(), direct_message()
    event = event_from_message(observed, configured, conversation=True)
    assert event is not None
    assert (event.trigger, event.question, event.mention_subject_ids) == ("message", observed.content, ())
    native = worker(configured)
    timeline: list[str] = []
    bodies: list[dict[str, Any]] = []
    answer = "x" * 5000

    def handler(request: httpx.Request) -> httpx.Response:
        response = identity(request)
        if response is not None:
            return response
        if request.method == "GET":
            assert request.url.path == "/api/v10/channels/204"
            return httpx.Response(200, json={"id": "204", "type": 1, "recipients": [{"id": "105"}]})
        assert request.url.path == "/api/v10/channels/204/messages"
        bodies.append(json.loads(request.content))
        timeline.append("ack" if len(bodies) == 1 else f"final:{len(bodies) - 2}")
        return httpx.Response(500 if fail_second_part and len(bodies) == 3 else 201, json={"id": "301"})

    async def request_native(*_args: Any, **_kwargs: Any) -> ReachWorkerResult:
        assert timeline == ["ack"]
        timeline.append("native")
        return ReachWorkerResult(
            request_id="request",
            status="conversation",
            text=answer,
            policy_digest=configured.digest,
            corpus_digest="c" * 64,
        )

    native.request.side_effect = request_native
    async with transport(handler) as client:
        rest = make_rest(tmp_path, client)
        await rest.verify_identity()
        service = ReachService(
            configured, native, rest, admin_users=frozenset(), history_enabled=False, conversation=True
        )
        cog = ReachCog(service)
        await cog.on_message(observed)
        await cog.on_message(observed)
        labels = ["ack:0", "final:0", "final:1"] + ([] if fail_second_part else ["final:2"])
        records = {record.effect_key_digest: record for record in rest.journal.inspect()}
        assert set(records) == {sha256(f"message:101:110:{label}".encode()).hexdigest() for label in labels}
        assert [body["nonce"] for body in bodies] == [
            sha256(f"101:204:110:{label}".encode()).hexdigest()[:25] for label in labels
        ]
        assert timeline == ["ack", "native", "final:0", "final:1"] + ([] if fail_second_part else ["final:2"])
        assert bodies[0]["content"].startswith("I'll look into your request:")
        assert observed.content in bodies[0]["content"]
        assert all(body["message_reference"]["message_id"] == "110" for body in bodies)
        assert all(body["allowed_mentions"] == {"parse": [], "replied_user": False} for body in bodies)
        assert "".join(body["content"] for body in bodies[1:]) == (answer[:3800] if fail_second_part else answer)
        assert sum(record.status == "unknown" for record in records.values()) == int(fail_second_part)
    native.request.assert_awaited_once()


@pytest.mark.asyncio
async def test_busy_event_remains_fenced_after_active_turn_finishes() -> None:
    configured, observed = policy(), direct_message()
    observed.id = 111
    event = event_from_message(observed, configured, conversation=True)
    assert event is not None
    native, rest, acknowledge = worker(configured), Mock(), AsyncMock(return_value=True)
    service = ReachService(configured, native, rest, admin_users=frozenset(), history_enabled=False, conversation=True)
    service.turn_active = True
    with pytest.raises(ValueError, match=r"^worker_busy_or_unavailable$"):
        await service.run_event(event, observed.channel, acknowledge=acknowledge)
    service.turn_active = False
    assert await service.run_event(event, observed.channel, acknowledge=acknowledge) is None
    acknowledge.assert_not_awaited()
    native.request.assert_not_awaited()
    rest.bind_direct_channel.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("older_page", [False, True])
async def test_read_more_skips_full_filtered_page_or_clarifies_on_exhaustion(*, older_page: bool) -> None:
    configured = policy().model_copy(update={"context_message_limit": 50})
    observed = direct_message()
    observed.id = 1000
    pages: list[list[Any]] = []
    for page in range(3 if older_page else 1):
        entries: list[Any] = []
        for index in range(6):
            entry = direct_message()
            entry.id = 999 - page * 6 - index
            entry.created_at = NOW - timedelta(seconds=1 + page * 6 + index)
            entry.content = f"history:{entry.id}"
            if page == 1:
                entry.author.id, entry.author.bot = 999, index % 2 == 0
                entry.webhook_id = None if entry.author.bot else 1
            entries.append(entry)
        pages.append(entries)
    if not older_page:
        pages.append([])
    observed.channel.history = Mock(side_effect=[SDKPage(page) for page in pages])
    event = event_from_message(observed, configured, conversation=True)
    assert event is not None
    native, rest, acknowledge = worker(configured), Mock(bind_direct_channel=AsyncMock()), AsyncMock(return_value=True)
    native.ready = native.ready.model_copy(update={"adaptive_context": True})
    need = ReachWorkerResult(
        request_id="request",
        status="need_context",
        text="Read earlier context.",
        policy_digest=configured.digest,
        corpus_digest="c" * 64,
    )
    native.request.side_effect = [need, need.model_copy(update={"status": "conversation", "text": "Older answer."})]
    service = ReachService(configured, native, rest, admin_users=frozenset(), history_enabled=True, conversation=True)
    result = await service.run_event(event, observed.channel, acknowledge=acknowledge)
    assert result is not None
    assert result.status == ("conversation" if older_page else "clarify")
    assert result.text == "Older answer." if older_page else result.text != need.text and bool(result.text.strip())
    assert native.request.await_count == (2 if older_page else 1)
    assert observed.channel.history.call_count == (3 if older_page else 2)
    acknowledge.assert_awaited_once()
    first = native.request.await_args_list[0]
    assert first.kwargs["context_round"] == 0
    assert first.kwargs["history_state"] == "more"
    assert [entry.event_id for entry in first.args[1]] == [str(identity) for identity in range(994, 1000)]
    if older_page:
        second = native.request.await_args_list[1]
        assert second.kwargs["context_round"] == 1
        assert [entry.event_id for entry in second.args[1]] == [
            *(str(identity) for identity in range(982, 988)),
            *(str(identity) for identity in range(994, 1000)),
        ]
