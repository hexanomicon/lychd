"""The semantic event plane: RunEvent JSON round-trip, channel replay + gap ruling."""
# White-box assertions read RunChannel._replay directly.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import pytest

from lychd.domain.cortex.events import InProcessEventBus, RunChannel, RunEvent, RunEventKind


def test_run_event_json_round_trips() -> None:
    """A RunEvent survives model_dump_json → model_validate_json intact (PostgresEventBus)."""
    event = RunEvent(run_id="r1", seq=3, kind=RunEventKind.TOKEN, data="<b>x</b>", meta={"level": "info"})
    restored = RunEvent.model_validate_json(event.model_dump_json())
    assert restored == event
    assert restored.kind is RunEventKind.TOKEN
    assert restored.data == "<b>x</b>"
    assert restored.meta == {"level": "info"}


@pytest.mark.asyncio
async def test_channel_backfill_then_terminates_on_done() -> None:
    """A pre-seeded channel drains its replay buffer and closes on DONE (no hang)."""
    channel = RunChannel(run_id="r")
    channel.emit(RunEventKind.STATUS, "running")
    channel.emit(RunEventKind.TOKEN, "hi")
    channel.emit(RunEventKind.DONE, "done")
    assert channel.closed is True

    seen = [event async for event in channel.subscribe()]
    assert [str(e.kind) for e in seen] == ["status", "token", "done"]
    assert [e.seq for e in seen] == [0, 1, 2]


@pytest.mark.asyncio
async def test_channel_from_seq_replays_only_after_cursor() -> None:
    """subscribe(from_seq) replays strictly after the cursor (reconnect seam)."""
    channel = RunChannel(run_id="r")
    for i in range(3):
        channel.emit(RunEventKind.TOKEN, f"t{i}")
    channel.emit(RunEventKind.DONE, "done")

    seen = [event async for event in channel.subscribe(from_seq=1)]
    assert [e.seq for e in seen] == [2, 3]  # events 0,1 already delivered before reconnect


@pytest.mark.asyncio
async def test_channel_gap_ruling_emits_explicit_resync() -> None:
    """An evicted cursor yields one marker; the snapshot replaces retained history."""
    channel = RunChannel(run_id="r")
    channel.emit(RunEventKind.STATUS, "running")
    for i in range(400):  # overflow the 256 replay buffer; seq 0 is evicted
        channel.emit(RunEventKind.TOKEN, f"t{i}")
    channel.emit(RunEventKind.DONE, "done")

    seen = [event async for event in channel.subscribe(from_seq=0)]
    assert [event.kind for event in seen] == [RunEventKind.RESYNC]
    assert seen[0].data == "snapshot_required"
    assert seen[0].seq == channel.snapshot().cursor


@pytest.mark.asyncio
async def test_late_first_subscriber_resyncs_when_initial_prefix_was_evicted() -> None:
    channel = RunChannel(run_id="r")
    for i in range(400):
        channel.emit(RunEventKind.TOKEN, f"old-{i}")
    channel.emit(RunEventKind.DONE, "done")

    seen = [event async for event in channel.subscribe()]

    assert [event.kind for event in seen] == [RunEventKind.RESYNC]
    assert seen[0].seq == channel.snapshot().cursor


@pytest.mark.asyncio
async def test_channel_resync_live_tails_only_events_after_snapshot_boundary() -> None:
    channel = RunChannel(run_id="r")
    for i in range(400):
        channel.emit(RunEventKind.TOKEN, f"old-{i}")
    source = channel.subscribe(from_seq=0)

    reset = await anext(source)
    current = channel.emit(RunEventKind.TOKEN, "current")
    done = channel.emit(RunEventKind.DONE, "done")
    tail = [event async for event in source]

    assert reset.kind is RunEventKind.RESYNC
    assert reset.seq == 399
    assert tail == [current, done]


@pytest.mark.asyncio
async def test_reconnect_onto_fresh_channel_resyncs_never_hangs() -> None:
    """The infinite-silent-hang regression (F5/H4): a reconnect cursor onto a fresh/empty
    channel ALWAYS fires an explicit RESYNC first, then live-tails to the terminal.

    Before the fix, a `Last-Event-ID` onto a channel with an empty replay buffer (post
    restart / post close) yielded no resync, no error, and no DONE — a silent hang.
    """
    import asyncio

    channel = RunChannel(run_id="r")

    async def produce() -> None:
        await asyncio.sleep(0.01)  # let the subscriber attach and await first
        channel.emit(RunEventKind.STATUS, "running")
        channel.emit(RunEventKind.DONE, "done")

    task = asyncio.create_task(produce())
    seen = [event async for event in channel.subscribe(from_seq=5)]  # cursor set, buffer empty
    await task

    assert seen[0].kind is RunEventKind.RESYNC  # resync fired first — never silence
    assert seen[-1].kind is RunEventKind.DONE  # stream still completes


@pytest.mark.asyncio
async def test_cursor_above_head_resyncs_then_completes() -> None:
    """A cursor above the current head resyncs (never swallows the stream) and completes."""
    channel = RunChannel(run_id="r")
    channel.emit(RunEventKind.STATUS, "running")  # seq 0
    channel.emit(RunEventKind.DONE, "done")  # seq 1, closed

    seen = [event async for event in channel.subscribe(from_seq=99)]
    assert seen[0].kind is RunEventKind.RESYNC  # explicit resync, not silence


def test_channel_snapshot_carries_projection_and_exact_cursor() -> None:
    channel = RunChannel(run_id="r")
    channel.emit(RunEventKind.STATUS, "thinking")
    channel.emit(RunEventKind.TOKEN, "ashes")
    fragment = channel.emit(RunEventKind.FRAGMENT, '{"fragment":"known","params":{}}')

    snapshot = channel.snapshot()

    assert snapshot.cursor == 2
    assert snapshot.content == "ashes"
    assert snapshot.activity == "thinking"
    assert snapshot.fragments == (fragment,)
    assert snapshot.terminal is False


@pytest.mark.asyncio
async def test_emit_after_done_is_dropped() -> None:
    """The closed-guard (F2/H3): emits after a terminal DONE are dropped, one terminal remains."""
    channel = RunChannel(run_id="r")
    channel.emit(RunEventKind.STATUS, "running")
    channel.emit(RunEventKind.DONE, "done")
    assert channel.closed is True

    channel.emit(RunEventKind.DONE, "cancelled")  # dropped
    channel.emit(RunEventKind.TOKEN, "late")  # dropped

    dones = [e for e in list(channel._replay) if e.kind is RunEventKind.DONE]
    assert len(dones) == 1
    assert dones[0].data == "done"
    assert not any(e.kind is RunEventKind.TOKEN for e in channel._replay)


@pytest.mark.asyncio
async def test_bus_subscribe_unknown_run_yields_empty_stream() -> None:
    """No auto-mint (F5/H4): subscribing to an unknown run yields an immediately-empty stream."""
    bus = InProcessEventBus()
    seen = [event async for event in bus.subscribe("ghost")]
    assert seen == []
    assert bus.open("ghost")  # only NOW is a channel created (explicit open, not subscribe)


@pytest.mark.asyncio
async def test_bus_close_drops_channel_without_subscribers() -> None:
    """close() drops a subscriber-less channel immediately (no per-run leak, H4)."""
    bus = InProcessEventBus()
    channel = bus.open("gone")
    channel.emit(RunEventKind.DONE, "done")
    bus.close("gone")
    assert bus.open("gone") is not channel  # a fresh channel — the old one was dropped


@pytest.mark.asyncio
async def test_bus_emitter_tees_non_token_to_ledger() -> None:
    """The bus emitter pushes to the channel AND tees non-TOKEN events to the ledger."""
    from lychd.domain.cortex.ledger import InMemoryRunLedger
    from lychd.domain.cortex.runs import RunStatus

    ledger = InMemoryRunLedger()
    # Seed a run so append_event has a home to key against (InMemory keys by run_id).
    from lychd.agents.router import Intent

    await ledger.create(
        Intent(session_id="s", run_id="r", prompt="p"),
        workflow_name="bridge_chat",
        queue_name="runs",
        priority=50,
    )
    _ = RunStatus  # imported for clarity of the lifecycle under test

    bus = InProcessEventBus(ledger=ledger)
    emitter = bus.emitter("r")
    emitter.status("running")
    emitter.token("chatty")  # NOT persisted
    emitter.done("done")

    # Drain the per-run ORDERED writer chain (H5): each append awaits the prior, so
    # give the loop enough turns for the whole chain to settle.
    import asyncio

    for _ in range(10):
        await asyncio.sleep(0)

    kinds = [str(e.kind) for e in ledger.events("r")]
    assert kinds == ["status", "done"]  # ORDERED, tokens dropped
    assert "token" not in kinds  # tokens are too chatty for Step rows
