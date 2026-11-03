"""Native Reach context decisions shared by transport adapters.

The caller retains its admitted audience and delivery acknowledgement boundary.
Research source acquisition remains gated by the exact plan's delivered
acknowledgement through the host research relay's compound operation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Protocol

from lychd.compositions.reach.operator_wire import (
    HistoryState,
    ReachHistoryEntry,
    ReachWorkerRequest,
    ReachWorkerResult,
)
from lychd.compositions.reach.schemas import ReachEvent

MAX_REQUESTS = 512
MAX_CONTEXT_PAGES = 3
_LAST_CONTEXT_ROUND = 2


def request_digest(request: ReachWorkerRequest) -> str:
    canonical = json.dumps(
        request.model_dump(mode="json", exclude={"request_id"}), sort_keys=True, separators=(",", ":")
    )
    return sha256(canonical.encode()).hexdigest()


@dataclass
class _EventContinuation:
    request: ReachWorkerRequest
    digests: dict[int, str]
    expected_round: int | None = None


@dataclass
class ContextRounds:
    """Admit bounded fresh Runs only for exact, settled requests for older context."""

    events: dict[tuple[str, str, str], _EventContinuation] = field(default_factory=dict)
    admitted: int = 0

    @staticmethod
    def identity(request: ReachWorkerRequest) -> tuple[str, str, str]:
        event = request.event
        return event.platform, event.account_id, event.event_id

    def reason(self, request: ReachWorkerRequest, digest: str, *, adaptive: bool) -> str | None:  # noqa: PLR0911 - closed admission reasons
        previous = self.events.get(self.identity(request))
        if previous is not None:
            seen = previous.digests.get(request.context_round)
            if seen is not None:
                return "duplicate" if seen == digest else "duplicate_conflict"
            if not adaptive or previous.expected_round is None:
                return "context_continuation"
            if request.context_round != previous.expected_round:
                return "context_round"
            mutable = {"request_id", "context_round", "history", "history_state"}
            if request.model_dump(exclude=mutable) != previous.request.model_dump(exclude=mutable):
                return "context_binding"
            if not self._older_history(previous.request, request):
                return "context_history"
        elif request.context_round != 0:
            return "context_round"
        if self.admitted >= MAX_REQUESTS:
            return "generation_budget"
        return None

    @staticmethod
    def _older_history(previous: ReachWorkerRequest, request: ReachWorkerRequest) -> bool:
        history, known = request.history, previous.history
        added = len(history) - len(known)
        if added <= 0 or history[added:] != known:
            return False
        keys = tuple((item.occurred_at, item.event_id) for item in history)
        boundary = (
            (known[0].occurred_at, known[0].event_id)
            if known
            else (
                request.event.occurred_at,
                request.event.event_id,
            )
        )
        return (
            keys == tuple(sorted(keys))
            and len({item.event_id for item in history}) == len(history)
            and all(item.conversation_id == request.event.conversation_id for item in history)
            and all(key < boundary for key in keys[:added])
        )

    def admit(self, request: ReachWorkerRequest, digest: str) -> None:
        """Consume one generation slot and close the previous continuation grant."""
        identity = self.identity(request)
        previous = self.events.get(identity)
        digests = previous.digests if previous is not None else {}
        digests[request.context_round] = digest
        self.events[identity] = _EventContinuation(request, digests)
        self.admitted += 1

    def settled(self, request: ReachWorkerRequest, result: ReachWorkerResult, *, adaptive: bool) -> None:
        """Open exactly one next round after the native result has settled and been bound."""
        previous = self.events[self.identity(request)]
        if (
            adaptive
            and request.event.action == "converse"
            and request.history_state == "more"
            and request.context_round < _LAST_CONTEXT_ROUND
            and result.status == "need_context"
        ):
            previous.expected_round = request.context_round + 1


class ContextSource(Protocol):
    """Expose bounded cumulative observations and why paging stopped."""

    entries: tuple[ReachHistoryEntry, ...]
    state: HistoryState

    async def next_page(self) -> None:
        """Load at most one bounded page, retaining the current cumulative entries."""
        ...


class WorkerRequester(Protocol):
    """Request one exact native Run from normalized observations."""

    async def request(
        self,
        event: ReachEvent,
        history: tuple[ReachHistoryEntry, ...],
        /,
        *,
        context_round: int = 0,
        history_state: str = "exhausted",
        reply_to_event_id: str | None = None,
        reply_anchor: ReachHistoryEntry | None = None,
        continuation_anchor: ReachHistoryEntry | None = None,
    ) -> ReachWorkerResult:
        """Return the settled result bound to this request and context round."""
        ...


async def drive_context_turn(
    worker: WorkerRequester,
    event: ReachEvent,
    pager: ContextSource,
    *,
    reply_to_event_id: str | None = None,
    reply_anchor: ReachHistoryEntry | None = None,
    continuation_anchor: ReachHistoryEntry | None = None,
) -> ReachWorkerResult:
    """Bound page calls for all adapters; request older context only after a native decision."""
    result: ReachWorkerResult | None = None
    pages_read = 0
    for context_round in range(3):
        previous = pager.entries
        defer_page = context_round == 0 and event.trigger in {"reply", "followup"}
        if not defer_page:
            await pager.next_page()
            pages_read += 1
        while not defer_page and pager.state == "more" and pager.entries == previous and pages_read < MAX_CONTEXT_PAGES:
            await pager.next_page()
            pages_read += 1
        effective_state: HistoryState = (
            "budget" if pager.state == "more" and pages_read >= MAX_CONTEXT_PAGES else pager.state
        )
        if result is not None and pager.entries == previous:
            return result.model_copy(
                update={
                    "status": "clarify",
                    "text": "I couldn't load more relevant messages. Please quote the missing material or clarify your question.",
                }
            )
        result = await worker.request(
            event,
            pager.entries,
            context_round=context_round,
            history_state=effective_state,
            reply_to_event_id=reply_to_event_id,
            reply_anchor=reply_anchor,
            continuation_anchor=continuation_anchor,
        )
        if result.status != "need_context":
            return result
        if effective_state != "more":
            return result.model_copy(
                update={
                    "status": "clarify",
                    "text": "I'm missing relevant context. Please quote the message or clarify your question.",
                }
            )
    if result is None:
        msg = "context_result_missing"
        raise ValueError(msg)
    return result.model_copy(
        update={
            "status": "clarify",
            "text": "I've reached the history limit. Please quote the relevant part of the conversation.",
        }
    )
