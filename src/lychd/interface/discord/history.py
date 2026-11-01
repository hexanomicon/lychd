"""Request-local, bounded observations of explicitly selected Discord history."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import discord

from lychd.compositions.reach.conversation_session import MAX_CONTEXT_PAGES
from lychd.compositions.reach.operator_wire import HistoryState, ReachHistoryEntry
from lychd.compositions.reach.schemas import ReachEvent
from lychd.interface.discord.schemas import DiscordPolicy

MAX_HISTORY_BYTES = 16_384
HISTORY_PAGE_SIZE = 6
MAX_HISTORY_PAGE_SIZE = 16


class HistoryPager:
    """Cache one turn's cumulative excerpts and expose why fetching stopped.

    No history is fetched during construction. Each explicit page request makes
    at most one SDK history call; terminal states keep subsequent calls inert.
    The reply anchor, when supplied, shares the count and UTF-8 budgets.
    """

    def __init__(
        self,
        policy: DiscordPolicy,
        event: ReachEvent,
        channel: discord.abc.Messageable,
        *,
        enabled: bool,
        conversation: bool,
        anchor: ReachHistoryEntry | None = None,
        page_size: int = HISTORY_PAGE_SIZE,
    ) -> None:
        """Bind an admitted turn without constructing any transport or cache."""
        if type(page_size) is not int or not 1 <= page_size <= MAX_HISTORY_PAGE_SIZE:
            msg = "history_page_size"
            raise ValueError(msg)
        self._page_size = page_size
        self.entries: tuple[ReachHistoryEntry, ...] = ()
        self.state: HistoryState = "more" if enabled and policy.context_message_limit else "disabled"
        self._policy = policy
        self._event = event
        self._channel = channel
        self._conversation = conversation
        self._cutoff = event.occurred_at - timedelta(seconds=policy.context_max_age_seconds)
        self._cursor = discord.Object(id=int(event.event_id))
        self._pages = 0
        self._bytes = 0
        self._anchor_count = 0
        self._seen = {event.event_id}
        self._lock = asyncio.Lock()
        if self.state == "disabled":
            return
        if str(getattr(channel, "id", None)) != event.conversation_id:
            self.state = "unavailable"
            return
        if anchor is not None:
            if (
                anchor.conversation_id != event.conversation_id
                or anchor.event_id == event.event_id
                or not self._cutoff < anchor.occurred_at < event.occurred_at
                or not self._subject_allowed(anchor.subject_id, bot=anchor.subject_id == policy.bot_user_id)
            ):
                self.state = "unavailable"
                return
            self._bytes = len(anchor.text.encode("utf-8"))
            if self._bytes > MAX_HISTORY_BYTES:
                self.state = "budget"
                return
            self._anchor_count = 1
            self._seen.add(anchor.event_id)
            if self._anchor_count >= policy.context_message_limit or self._bytes >= MAX_HISTORY_BYTES:
                self.state = "budget"

    def _subject_allowed(self, subject_id: str, *, bot: bool) -> bool:
        if bot and not (self._conversation and subject_id == self._policy.bot_user_id):
            return False
        return self._event.space_id is not None or subject_id in {
            self._event.subject_id,
            self._policy.bot_user_id,
        }

    def _entry(self, message: discord.Message) -> ReachHistoryEntry | None:
        identity = str(message.id)
        if identity in self._seen:
            return None
        self._seen.add(identity)
        if (
            str(message.channel.id) != self._event.conversation_id
            or not self._cutoff < message.created_at < self._event.occurred_at
            or message.webhook_id is not None
            or not self._subject_allowed(str(message.author.id), bot=message.author.bot)
            or not message.content
        ):
            return None
        return ReachHistoryEntry(
            subject_id=str(message.author.id),
            subject_label=str(message.author.display_name).strip()[:80] or None,
            event_id=identity,
            conversation_id=str(message.channel.id),
            text=message.content[:2000],
            occurred_at=message.created_at,
        )

    def _admit_page(self, raw: list[discord.Message]) -> bool:
        """Merge one observed page under the cumulative count and byte budget."""
        additions: list[ReachHistoryEntry] = []
        budget = False
        for message in raw:
            entry = self._entry(message)
            if entry is None:
                continue
            size = len(entry.text.encode("utf-8"))
            if self._bytes + size > MAX_HISTORY_BYTES:
                budget = True
                break
            additions.append(entry)
            self._bytes += size
            if self._anchor_count + len(self.entries) + len(additions) >= self._policy.context_message_limit:
                budget = True
                break
        self.entries = tuple(
            sorted((*self.entries, *additions), key=lambda item: (item.occurred_at, int(item.event_id)))
        )
        return budget

    async def next_page(self) -> None:
        """Extend cached history once, preserving explicit exhaustion and failure states."""
        async with self._lock:
            if self.state != "more":
                return
            if self._pages >= MAX_CONTEXT_PAGES:
                self.state = "budget"
                return
            self._pages += 1
            raw: list[discord.Message] = []
            try:
                async for message in self._channel.history(
                    limit=self._page_size,
                    before=self._cursor,
                    after=self._cutoff,
                    oldest_first=False,
                ):
                    raw.append(message)
                    if len(raw) >= self._page_size:
                        break
            except (discord.HTTPException, OSError, TimeoutError):
                self.state = "unavailable"
                return

            try:
                budget = self._admit_page(raw)
            except ValueError:
                self.state = "unavailable"
                return

            previous_cursor = self._cursor.id
            if raw:
                self._cursor = discord.Object(id=min(message.id for message in raw))
            if (
                budget
                or self._bytes >= MAX_HISTORY_BYTES
                or self._pages >= MAX_CONTEXT_PAGES
                or (self._cursor.id >= previous_cursor and bool(raw))
            ):
                self.state = "budget"
            elif len(raw) < self._page_size:
                self.state = "exhausted"
