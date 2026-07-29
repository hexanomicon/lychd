"""The semantic run-event plane (A4-U2, spec-00-FINAL C2).

The canonical `RunEvent` is a frozen, JSON-round-trippable pydantic model — events
are *semantic* (the web `EventProjector` validates inert JSON; agents emit raw data). `RunChannel`
fans one run's events out to any number of SSE subscribers with a bounded replay
buffer and a `subscribe(from_seq)` reconnect seam. `RunEventBus`/`InProcessEventBus`
own the run→channel bookkeeping that used to squat in `BridgeSessionStore`, and the
bus's emitter tees every non-`TOKEN` event into the `RunLedger` (tokens are too
chatty for Step rows; settled text lands on the session turn).

Topology A (v1): one process, one event loop — the in-process ghoul (`perform_run`)
and the SSE handler share this bus instance, so streaming survives byte-for-byte.
The `RunEvent` schema is deliberately JSON-serializable so a future
`PostgresEventBus` (LISTEN/NOTIFY) slots in behind `RunEventBus` without touching
emitters or the web layer (Topology B, out of v1 scope).
"""

from __future__ import annotations

import asyncio
import json
from collections import deque
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import uuid4

import structlog
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from lychd.domain.cortex.ledger import RunLedger

logger = structlog.get_logger()

# Grace window for dropping a closed channel that still has attached subscribers
# (F5/H4): the channel is removed when its last subscriber detaches, or after this
# ceiling, whichever comes first.
_CLOSE_GRACE_S = 60.0

__all__ = [
    "InProcessEventBus",
    "RunChannel",
    "RunChannelSnapshot",
    "RunEmitter",
    "RunEvent",
    "RunEventBus",
    "RunEventKind",
]

# Bounded replay retention per run (reconnect backfill ceiling).
_REPLAY_LIMIT = 256


class RunEventKind(StrEnum):
    """The semantic kinds carried on a run channel (kind ↔ SSE `event:` name 1:1)."""

    STATUS = "status"  # data = RunStatus value (or a progress keyword for the pill)
    NODE = "node"  # data = node key; drives the Loom highlight + progress rail
    DISPATCH = "dispatch"  # data = granted capability key; meta carries bounded selection facts
    TRANSITION = "transition"  # data = request id; meta carries bounded correlation
    TOKEN = "token"  # noqa: S105 - event-kind label, not a secret  # data = raw delta (NOT persisted)
    FRAGMENT = "fragment"  # data = JSON {"fragment": <registry name>, "params": {...}}
    CONSENT = "consent"  # data = JSON {"consent_id": ..., "tool_name": ...}
    LOG = "log"  # data = message; meta["level"] — feeds the Orb only
    DONE = "done"  # terminal; data = terminal RunStatus value
    RESYNC = "resync"  # synthetic replay-gap marker; clients must refetch a snapshot


class RunEvent(BaseModel):
    """One semantic event on a run's channel. Frozen and JSON-round-trippable."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    seq: int
    kind: RunEventKind
    data: str
    meta: dict[str, str] = Field(default_factory=dict)
    ts: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class RunChannelSnapshot:
    """One authoritative, replaceable projection at an exact event cursor."""

    run_id: str
    cursor: int
    content: str
    activity: str
    fragments: tuple[RunEvent, ...]
    occurrence_id: str | None
    dispatch_occurrence_id: str | None
    grant_id: str | None
    capability_key: str | None
    transition_occurrence_id: str | None
    transition_request_id: str | None
    transition_phase: str | None
    delegated_job_id: str | None
    delegated_runtime: str | None
    terminal: bool


@runtime_checkable
class RunEventBus(Protocol):
    """The run→channel surface consumed by the engine, the ghoul, and the web."""

    def open(self, run_id: str, *, from_seq: int | None = None) -> RunChannel:
        """Idempotent get-or-create of a run's channel.

        `from_seq` seeds a NEWLY minted channel's seq counter (reconcile/resume of a
        run that already has persisted Step history — see R1); it is ignored for a
        channel that already exists.
        """
        ...

    def emitter(self, run_id: str) -> RunEmitter:
        """Return an emitter bound to the run (tees non-TOKEN events to the ledger)."""
        ...

    def subscribe(self, run_id: str, *, from_seq: int | None = None) -> AsyncIterator[RunEvent]:
        """Subscribe to a run's events, optionally replaying from ``from_seq``."""
        ...

    def snapshot(self, run_id: str) -> RunChannelSnapshot | None:
        """Return the current replaceable projection, or ``None`` if no channel remains."""
        ...

    def close(self, run_id: str) -> None:
        """Drop a run's channel after it is done and its subscribers have drained."""
        ...


@dataclass
class RunChannel:
    """Per-run fan-out: a bounded replay buffer plus live per-subscriber queues.

    A subscriber that connects mid-run first drains the replay buffer (backfill),
    then live-tails until a terminal `DONE` closes the stream. `subscribe(from_seq)`
    is the reconnect seam: only events strictly after `from_seq` are replayed.

    Gap ruling (ADR 15 §3): if `from_seq` names an event already evicted from
    the bounded buffer, an explicit synthetic `RESYNC` is emitted first and the
    stream then continues live — an evicted cursor never errors the stream.
    """

    run_id: str
    _seq: int = 0
    _replay: deque[RunEvent] = field(default_factory=lambda: deque(maxlen=_REPLAY_LIMIT))
    _subscribers: set[asyncio.Queue[RunEvent]] = field(default_factory=set)
    _closed: bool = False
    _content: list[str] = field(default_factory=list)
    _activity: str = "queued"
    _fragments: list[RunEvent] = field(default_factory=list)
    _occurrence_id: str | None = None
    _dispatch_occurrence_id: str | None = None
    _grant_id: str | None = None
    _capability_key: str | None = None
    _transition_occurrence_id: str | None = None
    _transition_request_id: str | None = None
    _transition_phase: str | None = None
    _delegated_job_id: str | None = None
    _delegated_runtime: str | None = None
    _drained: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self) -> None:
        """Start a fresh channel drained (no subscribers attached)."""
        self._drained.set()

    def emit(self, kind: RunEventKind, data: str, **meta: str) -> RunEvent:
        """Publish one event to the replay buffer and every live subscriber.

        Closed-guard (F2/H3): once a terminal `DONE` has been emitted the channel is
        closed; any further emit (a second terminal from the cancel/completion race,
        or a late token) is logged and dropped WITHOUT touching the buffer, the seq
        counter, or subscribers — so a run yields exactly one terminal event.
        """
        if self._closed:
            logger.debug("run_channel_emit_after_close", run_id=self.run_id, kind=str(kind))
            return RunEvent(run_id=self.run_id, seq=max(self._seq - 1, 0), kind=kind, data=data, meta=dict(meta))
        event = RunEvent(run_id=self.run_id, seq=self._seq, kind=kind, data=data, meta=dict(meta))
        self._seq += 1
        self._replay.append(event)
        if kind in {RunEventKind.STATUS, RunEventKind.DONE}:
            self._activity = data
        elif kind is RunEventKind.TOKEN:
            self._content.append(data)
        elif kind is RunEventKind.FRAGMENT:
            self._fragments.append(event)
        elif kind is RunEventKind.NODE:
            self._occurrence_id = meta.get("occurrence_id") or self._occurrence_id
            self._delegated_job_id = meta.get("delegated_job_id") or self._delegated_job_id
            self._delegated_runtime = meta.get("delegated_runtime") or self._delegated_runtime
        elif kind is RunEventKind.DISPATCH:
            self._occurrence_id = meta.get("occurrence_id") or self._occurrence_id
            self._dispatch_occurrence_id = meta.get("occurrence_id") or self._dispatch_occurrence_id
            self._grant_id = meta.get("grant_id") or self._grant_id
            self._capability_key = data
        elif kind is RunEventKind.TRANSITION:
            self._transition_occurrence_id = meta.get("occurrence_id") or self._transition_occurrence_id
            self._capability_key = meta.get("capability_key") or self._capability_key
            self._transition_request_id = data
            self._transition_phase = meta.get("phase") or self._transition_phase
        for queue in self._subscribers:
            queue.put_nowait(event)
        if kind is RunEventKind.DONE:
            self._closed = True
        return event

    def mark_closed(self) -> None:
        """Force the closed flag (used when a run ends without a terminal emit)."""
        self._closed = True

    @property
    def has_subscribers(self) -> bool:
        """Whether any live subscriber is currently attached."""
        return bool(self._subscribers)

    async def wait_drained(self) -> None:
        """Block until the last subscriber detaches (used by the close grace)."""
        await self._drained.wait()

    @property
    def closed(self) -> bool:
        """Whether a terminal `DONE` event has been emitted."""
        return self._closed

    @property
    def next_seq(self) -> int:
        """The seq the next emitted event will carry."""
        return self._seq

    def snapshot(self) -> RunChannelSnapshot:
        """Capture the live projection and the exact cursor it includes."""
        return RunChannelSnapshot(
            run_id=self.run_id,
            cursor=self._seq - 1,
            content="".join(self._content),
            activity=self._activity,
            fragments=tuple(self._fragments),
            occurrence_id=self._occurrence_id,
            dispatch_occurrence_id=self._dispatch_occurrence_id,
            grant_id=self._grant_id,
            capability_key=self._capability_key,
            transition_occurrence_id=self._transition_occurrence_id,
            transition_request_id=self._transition_request_id,
            transition_phase=self._transition_phase,
            delegated_job_id=self._delegated_job_id,
            delegated_runtime=self._delegated_runtime,
            terminal=self._closed,
        )

    def _resync_event(self) -> RunEvent:
        """Return an explicit marker requiring clients to refetch the run snapshot."""
        return RunEvent(
            run_id=self.run_id,
            seq=max(self._seq - 1, 0),
            kind=RunEventKind.RESYNC,
            data="snapshot_required",
        )

    def _cursor_aligned(self, from_seq: int, replay: list[RunEvent]) -> bool:
        """Whether a reconnect `from_seq` continues the stream without a gap.

        Per-run seqs are contiguous (emit increments by one; eviction only trims the
        deque's front), so the retained window is ``replay[0].seq .. self._seq - 1``.
        The client's next expected seq is ``from_seq + 1``; it aligns iff that seq is
        the head (`self._seq`, caught up) or sits within the retained window.
        """
        expected = from_seq + 1
        if replay:
            return replay[0].seq <= expected <= self._seq
        return expected == self._seq

    async def subscribe(self, from_seq: int | None = None) -> AsyncIterator[RunEvent]:
        """Backfill (after ``from_seq``), then live-tail until `DONE`.

        Loop-confined: one channel is only ever driven by a single event loop.
        """
        queue: asyncio.Queue[RunEvent] = asyncio.Queue()
        self._subscribers.add(queue)
        self._drained.clear()
        try:
            replay = list(self._replay)
            client_cursor = from_seq if from_seq is not None else -1
            resync_required = not self._cursor_aligned(client_cursor, replay)
            # Gap ruling (F5/H4): a reconnect cursor that does not line up with the
            # live head ALWAYS fires the explicit RESYNC first, then continues live.
            # "Lines up" means the next event the client expects (client cursor + 1) is
            # either the head (fully caught up) or still inside the retained buffer.
            # A first subscriber starts before seq 0, so an already-evicted prefix
            # also receives the marker. This covers every hang/loss case the old
            # `replay-only` check missed: an empty/fresh channel after restart, a
            # cursor above the head, and a late first subscriber.
            #
            # The marker establishes a replacement boundary at the current head.
            # Events at or before that boundary are supplied by the run snapshot,
            # never replayed after the marker; only events emitted later live-tail.
            backfilled_seq = -1
            if resync_required:
                snapshot_cursor = self._seq - 1
                yield self._resync_event()
                backfilled_seq = snapshot_cursor
            else:
                for event in replay:
                    if from_seq is not None and event.seq <= from_seq:
                        continue
                    backfilled_seq = event.seq
                    yield event
                    if event.kind is RunEventKind.DONE:
                        return

            if self._closed and queue.empty():
                return

            while True:
                event = await queue.get()
                if event.seq <= backfilled_seq:
                    continue
                yield event
                if event.kind is RunEventKind.DONE:
                    return
        finally:
            self._subscribers.discard(queue)
            if not self._subscribers:
                self._drained.set()


@dataclass
class RunEmitter:
    """Emits semantic events onto one run's channel, teeing non-TOKEN to the ledger.

    `emit` is the primitive; the semantic helpers (`status`/`token`/`fragment`/…)
    are byte-shaped for the `EventProjector`. Tokens are emitted raw text — the client
    is the sole escaper (spec-00-FINAL C2).
    """

    channel: RunChannel
    persist: Callable[[RunEvent], None] = lambda _event: None

    def emit(self, kind: RunEventKind, data: str, **meta: str) -> RunEvent:
        """Publish one event to the channel and tee it to the ledger sink.

        If the channel was already closed this emit is a dropped no-op (F2/H3), so it
        is NOT teed to the ledger — persisting a dropped duplicate would collide with
        the already-persisted terminal (verbatim seq, H5) or double a Step row.
        """
        already_closed = self.channel.closed
        event = self.channel.emit(kind, data, **meta)
        if not already_closed:
            self.persist(event)
        return event

    def status(self, status: str) -> RunEvent:
        """Emit a status keyword (RunStatus value or a progress pill keyword)."""
        return self.emit(RunEventKind.STATUS, status)

    def node(self, key: str, **meta: str) -> RunEvent:
        """Emit one typed node-occurrence phase for a stable Pattern node key."""
        return self.emit(RunEventKind.NODE, key, **meta)

    def dispatch(self, capability_key: str, **meta: str) -> RunEvent:
        """Emit the capability grant actually selected by the Dispatcher."""
        return self.emit(RunEventKind.DISPATCH, capability_key, **meta)

    def transition(self, request_id: str, **meta: str) -> RunEvent:
        """Emit one orchestration request phase without embedding a host intent."""
        return self.emit(RunEventKind.TRANSITION, request_id, **meta)

    def token(self, text: str) -> RunEvent | None:
        """Emit a raw token delta. Clients render it as text; empty deltas are dropped."""
        if not text:
            return None
        return self.emit(RunEventKind.TOKEN, text)

    def fragment(self, name: str, params: dict[str, object]) -> RunEvent:
        """Emit a validated genUI fragment as `{"fragment": name, "params": {...}}`."""
        return self.emit(RunEventKind.FRAGMENT, json.dumps({"fragment": name, "params": params}))

    def consent(self, consent_id: str, *, tool_name: str = "") -> RunEvent:
        """Emit a parked consent as `{"consent_id": ..., "tool_name": ...}` JSON.

        The consent record is written BEFORE this event (spec-00-FINAL C2/C3).
        """
        return self.emit(RunEventKind.CONSENT, json.dumps({"consent_id": consent_id, "tool_name": tool_name}))

    def log(self, message: str, *, level: str = "info") -> RunEvent:
        """Emit a log line (feeds the Orb only)."""
        return self.emit(RunEventKind.LOG, message, level=level)

    def done(self, status: str) -> RunEvent:
        """Emit the single terminal `DONE` carrying the terminal RunStatus value."""
        return self.emit(RunEventKind.DONE, status)


class InProcessEventBus:
    """A `dict[str, RunChannel]` bus for Topology A (one process, one loop).

    Owns the run/channel bookkeeping that used to live on `BridgeSessionStore`.
    The emitter tees every non-`TOKEN` event to the injected `RunLedger` through a
    per-run ORDERED writer chain (F4/H5): each append awaits the prior one for the
    same run, so Step rows land in emit order (never reordered by the scheduler) and
    a persistence failure is logged loudly rather than silently swallowed. The SSE
    path itself stays synchronous and authoritative.
    """

    def __init__(self, *, ledger: RunLedger | None = None) -> None:
        """Create an empty bus, optionally teeing non-TOKEN events to ``ledger``."""
        self._channels: dict[str, RunChannel] = {}
        self._ledger = ledger
        self._pending: set[asyncio.Task[None]] = set()
        self._writer_tails: dict[str, asyncio.Task[None]] = {}  # run_id -> chain tail

    def open(self, run_id: str, *, from_seq: int | None = None) -> RunChannel:
        """Return the run's channel, creating it on first access.

        Seq seeding (R1): a fresh `RunChannel` restarts its seq at 0, which collides
        with existing Step rows when a run with persisted history is reconciled or
        resumed after a restart (`append_event` writes `event.seq` verbatim against
        `uq_step_run_seq`). Reconcile/resume paths pass `from_seq=next_seq` so the
        newly minted channel picks up where the persisted history left off. An
        already-live channel keeps its own counter (the arg is ignored).
        """
        channel = self._channels.get(run_id)
        if channel is None:
            channel = RunChannel(run_id=run_id, _seq=from_seq or 0)
            self._channels[run_id] = channel
        return channel

    def emitter(self, run_id: str) -> RunEmitter:
        """Return an emitter bound to the run (tees non-TOKEN events to the ledger)."""
        return RunEmitter(channel=self.open(run_id), persist=self._persist)

    def subscribe(self, run_id: str, *, from_seq: int | None = None) -> AsyncIterator[RunEvent]:
        """Subscribe to a KNOWN run's channel, optionally replaying after ``from_seq``.

        No auto-mint (F5/H4): unlike the old bus, this never conjures an empty channel
        for an arbitrary id (which then hangs on keepalives forever). A missing channel
        yields an empty, immediately-terminating stream; the SSE handler consults the
        ledger FIRST (unknown → 404, terminal → synthetic replay) so it only subscribes
        to a live run whose channel exists.
        """
        channel = self._channels.get(run_id)
        if channel is None:
            return _empty_stream()
        return channel.subscribe(from_seq)

    def snapshot(self, run_id: str) -> RunChannelSnapshot | None:
        """Return the channel's replaceable projection without minting a channel."""
        channel = self._channels.get(run_id)
        return channel.snapshot() if channel is not None else None

    def close(self, run_id: str) -> None:
        """Mark a run's channel closed and drop it once its subscribers drain (H4).

        Removal is deferred until the last subscriber detaches (so an in-flight SSE
        reader still drains the terminal), or `_CLOSE_GRACE_S` elapses — whichever
        comes first. With no subscribers (or no running loop) the channel is dropped
        immediately.
        """
        channel = self._channels.get(run_id)
        if channel is None:
            return
        channel.mark_closed()
        if not channel.has_subscribers:
            self._channels.pop(run_id, None)
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._channels.pop(run_id, None)
            return
        task = loop.create_task(self._drop_after_drain(run_id, channel))
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)

    async def aclose(self) -> None:
        """Await in-flight persist/close tasks before shutdown (R10).

        The ledger tee and the close-grace run as fire-and-scheduled tasks; without a
        drain, a tail Step write (or a terminal persist) in flight when the lifespan
        unwinds is dropped. Snapshot the pending set and await it (each task already
        logs its own failure) so the durable Step history is complete at shutdown.
        """
        pending = [task for task in self._pending if not task.done()]
        for task in pending:
            with suppress(Exception):
                await task

    async def _drop_after_drain(self, run_id: str, channel: RunChannel) -> None:
        """Wait for subscribers to detach (bounded by the grace), then drop the channel."""
        with suppress(TimeoutError):
            await asyncio.wait_for(channel.wait_drained(), timeout=_CLOSE_GRACE_S)
        if self._channels.get(run_id) is channel:
            self._channels.pop(run_id, None)

    def _persist(self, event: RunEvent) -> None:
        """Chain the ledger append for non-TOKEN events (per-run ordered, error-logged)."""
        if self._ledger is None or event.kind is RunEventKind.TOKEN:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # no loop (sync test context): the ledger tee is best-effort
        prev = self._writer_tails.get(event.run_id)
        task = loop.create_task(self._append_chained(prev, event))
        self._writer_tails[event.run_id] = task
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)
        if event.kind is RunEventKind.DONE:
            self._writer_tails.pop(event.run_id, None)  # chain ends at the terminal

    async def _append_chained(self, prev: asyncio.Task[None] | None, event: RunEvent) -> None:
        """Await the prior same-run append (ordering), then persist this one."""
        if prev is not None:
            with suppress(Exception):  # prev logged its own failure; we only need ordering
                await prev
        if self._ledger is None:
            return
        try:
            await self._ledger.append_event(event)
        except Exception:
            logger.exception("run_event_persist_failed", run_id=event.run_id, kind=str(event.kind), seq=event.seq)


async def _empty_stream() -> AsyncIterator[RunEvent]:
    """Yield nothing — the stream for an unknown/closed-and-dropped channel."""
    return
    yield  # pragma: no cover - marks this a generator
