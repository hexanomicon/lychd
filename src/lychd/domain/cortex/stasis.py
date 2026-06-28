"""Live Stasis Phylactery and per-run event channel (ADR 24).

`LiveStasisPhylactery` is the in-memory, Live-Stasis-only persistence handed to
`GraphRunner`. `RunChannel` carries server-rendered run events (token/status/
fragment/consent/done) to SSE subscribers with a bounded replay buffer.
"""

from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from pydantic_graph.persistence.in_mem import FullStatePersistence

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

RunEventKind = Literal["token", "status", "fragment", "consent", "done"]

_REPLAY_LIMIT = 256


class LiveStasisPhylactery(FullStatePersistence[Any, Any]):
    """In-memory persistence with Live Stasis rehydration for `GraphRunner`.

    Subclasses `FullStatePersistence` (which already implements the whole
    `snapshot_*`/`load_*`/`record_run`/`set_graph_types` surface). Adds the
    `job_id` handle and the two stasis hooks `GraphRunner` calls when a
    `HardwareTransitionRequired` is caught mid-run.
    """

    job_id: str

    def __init__(self, *, job_id: str) -> None:
        """Bind the phylactery to one run id (the job id)."""
        super().__init__()
        self.job_id = job_id

    async def rehydrate_stasis(self, state: Any, node: Any) -> None:
        """Append a fresh 'created' snapshot so `load_next` resumes from `node`.

        The node carried out of a failed `graph.iter()` still holds the cached
        snapshot id of its errored attempt; clearing it forces `snapshot_node` to
        mint a new, unique id so the resumed snapshot is found (not the errored
        one that shares the node's id) by `record_run`.
        """
        with suppress(AttributeError):
            node.__dict__.pop("__snapshot_id", None)
        await self.snapshot_node(state, node)

    async def mark_job_resumed(self, job_id: str) -> None:
        """Finalize rehydration. No-op in the Live tier (resident loop)."""
        _ = job_id


@dataclass(frozen=True, kw_only=True)
class RunEvent:
    """One server-rendered event on a run's channel."""

    run_id: str
    seq: int
    kind: RunEventKind
    payload: str


@dataclass
class RunChannel:
    """Per-run event fan-out: a live queue plus a bounded replay buffer.

    A subscriber that connects mid-run first drains the replay buffer (backfill),
    then live-tails the queue until a `done` event closes the stream.
    """

    run_id: str
    _seq: int = 0
    _replay: deque[RunEvent] = field(default_factory=lambda: deque(maxlen=_REPLAY_LIMIT))
    _queue: asyncio.Queue[RunEvent] = field(default_factory=asyncio.Queue)
    _closed: bool = False

    def emit(self, kind: RunEventKind, payload: str) -> RunEvent:
        """Publish one event to the replay buffer and the live queue."""
        event = RunEvent(run_id=self.run_id, seq=self._seq, kind=kind, payload=payload)
        self._seq += 1
        self._replay.append(event)
        self._queue.put_nowait(event)
        if kind == "done":
            self._closed = True
        return event

    @property
    def closed(self) -> bool:
        """Whether a terminal `done` event has been emitted."""
        return self._closed

    async def subscribe(self) -> AsyncIterator[RunEvent]:
        """Backfill the replay buffer, then live-tail until `done`.

        Loop-confined: one channel is only ever driven by a single event loop.
        """
        backfilled_seq = -1
        for event in list(self._replay):
            backfilled_seq = event.seq
            yield event
            if event.kind == "done":
                return

        if self._closed:
            return

        while True:
            event = await self._queue.get()
            if event.seq <= backfilled_seq:
                continue
            yield event
            if event.kind == "done":
                return
