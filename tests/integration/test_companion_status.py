"""Read-only owner snapshots across actual native admission, results and retirement."""

from __future__ import annotations

import asyncio
import json
from dataclasses import FrozenInstanceError, asdict
from uuid import uuid4

import pytest

from lychd.compositions.blockworld.companion import CompanionRequest, CompanionService, parse_text
from lychd.system.services.companion_session import CompanionSession, LocalCompanionRunner
from tests.integration.test_companion import FakeBridge, policy


@pytest.mark.asyncio
async def test_snapshot_preserves_expired_pending_slots_without_expiring_or_admitting_them() -> None:
    fake = FakeBridge()
    fake.delay = True
    bridge = fake.bridge()
    clock = [0.0]
    session = CompanionSession(
        LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge, clock=lambda: clock[0]
    )
    initial = session.snapshot()
    assert not initial.opened
    assert initial.fenced
    assert not fake.reads
    assert not fake.requests
    await session.open()
    try:
        first = CompanionRequest(request_id=str(uuid4()), action=parse_text("say first-private-synthetic"))
        active = session.enqueue(first)
        await asyncio.wait_for(fake.action_started.wait(), 2)
        second = CompanionRequest(request_id=str(uuid4()), action=parse_text("say second-private-synthetic"))
        queued = session.enqueue(second)
        clock[0] += 16
        before = fake.reads, len(fake.requests), len(session.run_ids), len(session.runner.queue.jobs)
        snapshot = session.snapshot()
        assert snapshot.current is not None
        assert snapshot.current.request_id == first.request_id
        assert snapshot.current.run_id in {None, fake.requests[0]["run_id"]}
        assert snapshot.current.phase in {"admission_pending", "response_pending"}
        assert [item.request_id for item in snapshot.pending] == [second.request_id]
        assert snapshot.pending[0].remaining_ms == 0
        assert snapshot.pending[0].run_id is None
        assert snapshot.pending[0].phase == "queued"
        assert not queued.done()
        assert before == (fake.reads, len(fake.requests), len(session.run_ids), len(session.runner.queue.jobs))
        assert not session.outcomes
        assert "private-synthetic" not in json.dumps(asdict(snapshot))
        with pytest.raises(FrozenInstanceError):
            snapshot.pending[0].phase = "queued"  # pyright: ignore[reportAttributeAccessIssue]
        assert session.snapshot().pending == snapshot.pending
        stopping = session.stop()
        assert session.outcomes[second.request_id].evidence_status == "not_requested"
        assert session.snapshot().pending_evidence == 0
        await stopping
        cancelled = await queued
        assert cancelled.reason == "cancelled_before_execution"
        assert cancelled.run_id is None
        await active
        assert len(fake.requests) == 1
    finally:
        fake.release_action.set()
        await session.aclose()


@pytest.mark.asyncio
async def test_snapshot_distinguishes_known_result_pending_evidence_and_admission_closed_from_retired() -> None:
    fake = FakeBridge()
    bridge = fake.bridge()
    publishing, release = asyncio.Event(), asyncio.Event()

    async def retain(_document: dict[str, object]) -> None:
        publishing.set()
        await release.wait()

    session = CompanionSession(LocalCompanionRunner(CompanionService(policy(), bridge), bridge), bridge, record=retain)
    await session.open()
    command = CompanionRequest(request_id=str(uuid4()), action=parse_text("say retained-private-synthetic"))
    result = session.enqueue(command)
    closing: asyncio.Task[None] | None = None
    try:
        await asyncio.wait_for(publishing.wait(), 2)
        snapshot = session.snapshot()
        assert snapshot.current is not None
        assert snapshot.current.phase == "settling"
        assert snapshot.current.run_id == fake.requests[0]["run_id"]
        assert snapshot.pending_evidence == 1
        assert session.outcomes[command.request_id].kind == "applied"
        assert not result.done()
        before = fake.reads, len(fake.requests), len(session.runner.queue.jobs)
        assert session.snapshot().pending_evidence == 1
        assert before == (fake.reads, len(fake.requests), len(session.runner.queue.jobs))
        closing = asyncio.create_task(session.aclose())
        await asyncio.sleep(0)
        snapshot = session.snapshot()
        assert snapshot.closed
        assert snapshot.opened
        assert snapshot.stopping
        assert not closing.done()
        release.set()
        await asyncio.wait_for(closing, 2)
        settled = session.snapshot()
        assert settled.closed
        assert not settled.opened
        assert settled.current is None
        assert settled.pending_evidence == 0
        assert (await result).kind == "applied"
        assert len(fake.requests) == 1
    finally:
        release.set()
        if closing is not None:
            await asyncio.gather(closing, return_exceptions=True)
        else:
            await session.aclose()
