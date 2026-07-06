"""The semantic event plane: RunEvent JSON round-trip, channel replay + gap ruling."""

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
async def test_channel_gap_ruling_emits_resync_status() -> None:
    """An evicted from_seq yields a fresh STATUS resync, then continues — never errors."""
    channel = RunChannel(run_id="r")
    channel.emit(RunEventKind.STATUS, "running")  # seq 0 — becomes the resync source
    for i in range(400):  # overflow the 256 replay buffer; seq 0 is evicted
        channel.emit(RunEventKind.TOKEN, f"t{i}")
    channel.emit(RunEventKind.DONE, "done")

    seen = [event async for event in channel.subscribe(from_seq=0)]
    assert seen[0].kind is RunEventKind.STATUS  # synthetic resync first
    assert seen[0].data == "running"
    assert seen[-1].kind is RunEventKind.DONE  # stream still completes


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

    # Let the fire-and-forget ledger-tee tasks run.
    import asyncio

    await asyncio.sleep(0)
    await asyncio.sleep(0)

    kinds = [str(e.kind) for e in ledger.events("r")]
    assert "status" in kinds
    assert "done" in kinds
    assert "token" not in kinds  # tokens are too chatty for Step rows
