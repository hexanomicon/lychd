"""The semantic run-event plane (A4-U2, spec-00-FINAL C2).

The canonical `RunEvent` is a frozen, JSON-round-trippable pydantic model — events
are *semantic* (the web `Projector` renders; agents emit raw data). `RunChannel`
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
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from lychd.domain.cortex.ledger import RunLedger

__all__ = [
    "InProcessEventBus",
    "RunChannel",
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
    TOKEN = "token"  # noqa: S105 - event-kind label, not a secret  # data = raw delta (NOT persisted)
    FRAGMENT = "fragment"  # data = JSON {"fragment": <registry name>, "params": {...}}
    CONSENT = "consent"  # data = JSON {"consent_id": ..., "tool_name": ...}
    LOG = "log"  # data = message; meta["level"] — feeds Scrying only
    DONE = "done"  # terminal; data = terminal RunStatus value


class RunEvent(BaseModel):
    """One semantic event on a run's channel. Frozen and JSON-round-trippable."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    seq: int
    kind: RunEventKind
    data: str
    meta: dict[str, str] = Field(default_factory=dict)
    ts: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class RunEventBus(Protocol):
    """The run→channel surface consumed by the engine, the ghoul, and the web."""

    def open(self, run_id: str) -> RunChannel:
        """Idempotent get-or-create of a run's channel."""
        ...

    def emitter(self, run_id: str) -> RunEmitter:
        """Return an emitter bound to the run (tees non-TOKEN events to the ledger)."""
        ...

    def subscribe(self, run_id: str, *, from_seq: int | None = None) -> AsyncIterator[RunEvent]:
        """Subscribe to a run's events, optionally replaying from ``from_seq``."""
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

    Gap ruling (spec-00-FINAL C2): if `from_seq` names an event already evicted from
    the bounded buffer, a fresh synthetic `STATUS` is emitted first and the stream
    then continues live — an evicted cursor never errors the stream.
    """

    run_id: str
    _seq: int = 0
    _replay: deque[RunEvent] = field(default_factory=lambda: deque(maxlen=_REPLAY_LIMIT))
    _subscribers: set[asyncio.Queue[RunEvent]] = field(default_factory=set)
    _closed: bool = False
    _last_status: RunEvent | None = None

    def emit(self, kind: RunEventKind, data: str, **meta: str) -> RunEvent:
        """Publish one event to the replay buffer and every live subscriber."""
        event = RunEvent(run_id=self.run_id, seq=self._seq, kind=kind, data=data, meta=dict(meta))
        self._seq += 1
        self._replay.append(event)
        if kind is RunEventKind.STATUS:
            self._last_status = event
        for queue in self._subscribers:
            queue.put_nowait(event)
        if kind is RunEventKind.DONE:
            self._closed = True
        return event

    @property
    def closed(self) -> bool:
        """Whether a terminal `DONE` event has been emitted."""
        return self._closed

    @property
    def next_seq(self) -> int:
        """The seq the next emitted event will carry."""
        return self._seq

    def _resync_event(self) -> RunEvent:
        """Synthetic `STATUS` emitted when a reconnect cursor was already evicted."""
        if self._last_status is not None:
            return self._last_status
        return RunEvent(run_id=self.run_id, seq=max(self._seq - 1, 0), kind=RunEventKind.STATUS, data="running")

    async def subscribe(self, from_seq: int | None = None) -> AsyncIterator[RunEvent]:
        """Backfill (after ``from_seq``), then live-tail until `DONE`.

        Loop-confined: one channel is only ever driven by a single event loop.
        """
        queue: asyncio.Queue[RunEvent] = asyncio.Queue()
        self._subscribers.add(queue)
        try:
            replay = list(self._replay)
            # Gap ruling: the requested cursor precedes the oldest retained event.
            if from_seq is not None and replay and (from_seq + 1) < replay[0].seq:
                yield self._resync_event()

            backfilled_seq = -1
            for event in replay:
                if from_seq is not None and event.seq <= from_seq:
                    continue
                backfilled_seq = event.seq
                yield event
                if event.kind is RunEventKind.DONE:
                    return

            if self._closed:
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


@dataclass
class RunEmitter:
    """Emits semantic events onto one run's channel, teeing non-TOKEN to the ledger.

    `emit` is the primitive; the semantic helpers (`status`/`token`/`fragment`/…)
    are byte-shaped for the `Projector`. Tokens are emitted RAW — the `Projector`
    is the sole escaper (spec-00-FINAL C2).
    """

    channel: RunChannel
    persist: Callable[[RunEvent], None] = lambda _event: None

    def emit(self, kind: RunEventKind, data: str, **meta: str) -> RunEvent:
        """Publish one event to the channel and tee it to the ledger sink."""
        event = self.channel.emit(kind, data, **meta)
        self.persist(event)
        return event

    def status(self, status: str) -> RunEvent:
        """Emit a status keyword (RunStatus value or a progress pill keyword)."""
        return self.emit(RunEventKind.STATUS, status)

    def node(self, key: str) -> RunEvent:
        """Emit the active node key (drives the Loom highlight + progress rail)."""
        return self.emit(RunEventKind.NODE, key)

    def token(self, text: str) -> RunEvent | None:
        """Emit a RAW token delta (the Projector escapes). Empty deltas are dropped."""
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
        """Emit a log line (feeds Scrying only)."""
        return self.emit(RunEventKind.LOG, message, level=level)

    def done(self, status: str) -> RunEvent:
        """Emit the single terminal `DONE` carrying the terminal RunStatus value."""
        return self.emit(RunEventKind.DONE, status)


class InProcessEventBus:
    """A `dict[str, RunChannel]` bus for Topology A (one process, one loop).

    Owns the run/channel bookkeeping that used to live on `BridgeSessionStore`.
    The emitter tees every non-`TOKEN` event to the injected `RunLedger` via a
    fire-and-forget task (Step rows are observability; the SSE path is authoritative
    and stays synchronous).
    """

    def __init__(self, *, ledger: RunLedger | None = None) -> None:
        """Create an empty bus, optionally teeing non-TOKEN events to ``ledger``."""
        self._channels: dict[str, RunChannel] = {}
        self._ledger = ledger
        self._pending: set[asyncio.Task[None]] = set()

    def open(self, run_id: str) -> RunChannel:
        """Return the run's channel, creating it on first access."""
        channel = self._channels.get(run_id)
        if channel is None:
            channel = RunChannel(run_id=run_id)
            self._channels[run_id] = channel
        return channel

    def emitter(self, run_id: str) -> RunEmitter:
        """Return an emitter bound to the run (tees non-TOKEN events to the ledger)."""
        return RunEmitter(channel=self.open(run_id), persist=self._persist)

    def subscribe(self, run_id: str, *, from_seq: int | None = None) -> AsyncIterator[RunEvent]:
        """Subscribe to a run's channel, optionally replaying after ``from_seq``."""
        return self.open(run_id).subscribe(from_seq)

    def close(self, run_id: str) -> None:
        """Drop the run's channel (call after DONE + subscriber linger)."""
        self._channels.pop(run_id, None)

    def _persist(self, event: RunEvent) -> None:
        """Fire-and-forget the ledger append for non-TOKEN events."""
        if self._ledger is None or event.kind is RunEventKind.TOKEN:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # no loop (sync test context): the ledger tee is best-effort
        task = loop.create_task(self._ledger.append_event(event))
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)
