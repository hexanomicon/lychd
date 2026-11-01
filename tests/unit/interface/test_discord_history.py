from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from lychd.compositions.reach.operator_wire import ReachHistoryEntry
from lychd.compositions.reach.schemas import ReachEvent
from lychd.interface.discord.history import HistoryPager
from lychd.interface.discord.schemas import DiscordPolicy, DiscordRule

NOW = datetime(2026, 11, 1, tzinfo=UTC)


def policy(limit: int = 50) -> DiscordPolicy:
    return DiscordPolicy(
        application_id="11",
        bot_user_id="22",
        guild_id="33",
        allowed_channel_ids=("44",),
        rules=(DiscordRule(name="sender", user_ids=("55",), actions=("answer_docs",)),),
        context_message_limit=limit,
    )


def event(*, dm: bool = False) -> ReachEvent:
    return ReachEvent(
        platform="discord",
        account_id="11",
        event_id="1000",
        space_id=None if dm else "33",
        conversation_id="44",
        subject_id="55",
        trigger="mention",
        action="answer_docs",
        question="question",
        occurred_at=NOW,
    )


def message(
    identity: int = 999,
    *,
    subject: str = "55",
    bot: bool = False,
    age: int = 1,
    channel_id: str = "44",
    text: str = "history",
    webhook: bool = False,
) -> Any:
    result = Mock(spec=discord.Message)
    result.id = identity
    result.channel = Mock(id=int(channel_id))
    result.author = Mock(spec=discord.Member)
    result.author.id = int(subject)
    result.author.bot = bot
    result.author.display_name = "  Person  "
    result.created_at = NOW - timedelta(seconds=age)
    result.content = text
    result.webhook_id = 1 if webhook else None
    return result


def anchor(*, text: str = "reply") -> ReachHistoryEntry:
    return ReachHistoryEntry(
        subject_id="55",
        event_id="950",
        conversation_id="44",
        occurred_at=NOW - timedelta(seconds=50),
        text=text,
    )


def snapshot(pager: HistoryPager) -> tuple[ReachHistoryEntry, ...]:
    """Read a fresh immutable view after each awaited page operation."""
    return pager.entries


class SDKPage:
    def __init__(self, messages: list[Any]) -> None:
        self.read = AsyncMock(side_effect=[*messages, StopAsyncIteration])

    def __aiter__(self) -> AsyncIterator[discord.Message]:
        return self

    async def __anext__(self) -> discord.Message:
        return cast("discord.Message", await self.read())


def channel(*pages: list[Any] | Exception) -> Any:
    result = Mock(spec=discord.TextChannel)
    result.id = 44
    result.history = Mock(side_effect=[SDKPage(page) if isinstance(page, list) else page for page in pages])
    return result


@pytest.mark.asyncio
@pytest.mark.parametrize(("enabled", "limit"), [(False, 50), (True, 0)])
async def test_disabled_history_is_inert(*, enabled: bool, limit: int) -> None:
    sdk = channel()
    pager = HistoryPager(policy(limit), event(), sdk, enabled=enabled, conversation=True, anchor=anchor())
    assert len(snapshot(pager)) == 0
    assert pager.state == "disabled"
    await pager.next_page()
    await pager.next_page()
    sdk.history.assert_not_called()


@pytest.mark.asyncio
async def test_three_pages_reuse_cumulative_cache_and_cursor_by_oldest_raw_snowflake() -> None:
    pages = [[message(identity) for identity in range(999 - offset, 993 - offset, -1)] for offset in (0, 6, 12)]
    pages[0][-1].author.bot = True
    sdk = channel(*pages)
    pager = HistoryPager(policy(), event(), sdk, enabled=True, conversation=True)
    sdk.history.assert_not_called()

    await pager.next_page()
    cached = snapshot(pager)
    assert len(cached) == 5
    assert pager.state == "more"
    pages[0][0].content = "changed outside this turn's cache"
    await pager.next_page()
    assert len(snapshot(pager)) == 11
    assert all(entry in snapshot(pager) for entry in cached)
    assert all(entry.text == "history" for entry in snapshot(pager))
    await pager.next_page()
    assert len(snapshot(pager)) == 17
    assert pager.state == "budget"
    assert [int(entry.event_id) for entry in snapshot(pager)] == sorted(
        int(entry.event_id) for entry in snapshot(pager)
    )
    await pager.next_page()
    assert sdk.history.call_count == 3
    for call, before in zip(sdk.history.call_args_list, (1000, 994, 988), strict=True):
        assert call.kwargs["limit"] == 6
        assert isinstance(call.kwargs["before"], discord.Object)
        assert call.kwargs["before"].id == before
        assert call.kwargs["after"] == NOW - timedelta(seconds=600)
        assert call.kwargs["oldest_first"] is False


@pytest.mark.asyncio
async def test_anchor_is_separate_deduplicated_and_consumes_policy_count() -> None:
    sdk = channel([message(950, age=50), message(999), message(999), message(998)])
    pager = HistoryPager(policy(3), event(), sdk, enabled=True, conversation=True, anchor=anchor())
    assert len(snapshot(pager)) == 0
    await pager.next_page()
    assert [entry.event_id for entry in snapshot(pager)] == ["998", "999"]
    assert pager.state == "budget"
    await pager.next_page()
    sdk.history.assert_called_once()


@pytest.mark.asyncio
async def test_anchor_can_exhaust_count_without_fetching() -> None:
    sdk = channel()
    pager = HistoryPager(policy(1), event(), sdk, enabled=True, conversation=True, anchor=anchor())
    assert len(snapshot(pager)) == 0
    assert pager.state == "budget"
    await pager.next_page()
    sdk.history.assert_not_called()


@pytest.mark.asyncio
async def test_utf8_byte_budget_includes_anchor_and_keeps_bounded_whole_excerpts() -> None:
    pinned = anchor(text="💠" * 2000)
    sdk = channel([message(999 - index, text="ž" * 2500) for index in range(6)])
    pager = HistoryPager(policy(), event(), sdk, enabled=True, conversation=True, anchor=pinned)
    await pager.next_page()
    assert len(snapshot(pager)) == 2
    assert all(len(entry.text) == 2000 for entry in snapshot(pager))
    assert sum(len(entry.text.encode("utf-8")) for entry in (*snapshot(pager), pinned)) == 16_000
    assert pager.state == "budget"
    await pager.next_page()
    sdk.history.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rejected",
    [
        {"channel_id": "88"},
        {"age": 600},
        {"age": 601},
        {"age": 0},
        {"age": -1},
        {"webhook": True},
        {"subject": "88", "bot": True},
        {"text": ""},
        {"identity": 1000},
    ],
)
async def test_foreign_or_ineligible_page_stops_without_claiming_more(rejected: dict[str, Any]) -> None:
    sdk = channel([message(**rejected)])
    pager = HistoryPager(policy(), event(), sdk, enabled=True, conversation=True)
    await pager.next_page()
    assert len(snapshot(pager)) == 0
    assert pager.state == ("budget" if rejected.get("identity") == 1000 else "exhausted")
    await pager.next_page()
    sdk.history.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("conversation", [False, True])
async def test_dm_includes_only_sender_and_permitted_own_bot(*, conversation: bool) -> None:
    sdk = channel(
        [
            message(999),
            message(998, subject="22", bot=True),
            message(997, subject="88"),
            message(996, subject="89", bot=True),
            message(995, subject="22", bot=True, webhook=True),
            message(994, channel_id="88"),
        ],
        [],
    )
    pager = HistoryPager(policy(), event(dm=True), sdk, enabled=True, conversation=conversation)
    await pager.next_page()
    assert {entry.subject_id for entry in snapshot(pager)} == ({"55", "22"} if conversation else {"55"})
    assert all(entry.subject_label == "Person" for entry in snapshot(pager))
    assert pager.state == "more"
    await pager.next_page()
    assert pager.state == "exhausted"


@pytest.mark.asyncio
async def test_duplicate_only_page_stops_without_refetching_or_losing_cache() -> None:
    first = [message(identity) for identity in range(999, 993, -1)]
    sdk = channel(first, first)
    pager = HistoryPager(policy(), event(), sdk, enabled=True, conversation=True)
    await pager.next_page()
    cached = snapshot(pager)
    await pager.next_page()
    assert snapshot(pager) == cached
    assert pager.state == "budget"
    await pager.next_page()
    assert sdk.history.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [403, 500])
async def test_permission_or_api_error_is_unavailable_and_retains_previous_cache(status: int) -> None:
    error = discord.HTTPException(Mock(status=status, reason="failure"), "private foreign payload")
    sdk = channel([message(identity) for identity in range(999, 993, -1)], error)
    pager = HistoryPager(policy(), event(), sdk, enabled=True, conversation=True)
    await pager.next_page()
    cached = snapshot(pager)
    await pager.next_page()
    assert pager.state == "unavailable"
    assert snapshot(pager) == cached
    await pager.next_page()
    assert sdk.history.call_count == 2


@pytest.mark.asyncio
async def test_foreign_bound_channel_never_fetches() -> None:
    sdk = channel()
    sdk.id = 88
    pager = HistoryPager(policy(), event(), sdk, enabled=True, conversation=True)
    assert pager.state == "unavailable"
    await pager.next_page()
    sdk.history.assert_not_called()
