"""InMemoryRunLedger: the QUEUED→RUNNING→DONE trail, Step rows, transition guard."""

from __future__ import annotations

import pytest

from lychd.agents.router import Intent
from lychd.domain.cortex.events import RunEvent, RunEventKind
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import IllegalRunTransitionError, RunStatus


def _intent(run_id: str = "run_1") -> Intent:
    return Intent(session_id="sess_1", run_id=run_id, prompt="hello", source="bridge")


@pytest.mark.asyncio
async def test_create_persists_queued_run() -> None:
    """create() persists a fresh run as QUEUED keyed by intent.run_id."""
    ledger = InMemoryRunLedger()
    run = await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=70)
    assert run.run_id == "run_1"
    assert run.status is RunStatus.QUEUED
    assert run.workflow_name == "bridge_chat"
    assert run.queue_name == "runs"
    assert run.priority == 70
    assert (await ledger.get("run_1")) is run


@pytest.mark.asyncio
async def test_queued_running_done_trail() -> None:
    """The lifecycle trail QUEUED→RUNNING→DONE sets started/finished timestamps."""
    ledger = InMemoryRunLedger()
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)

    await ledger.set_status("run_1", RunStatus.RUNNING)
    running = await ledger.get("run_1")
    assert running is not None
    assert running.status is RunStatus.RUNNING
    assert running.started_at is not None

    await ledger.set_status("run_1", RunStatus.DONE)
    done = await ledger.get("run_1")
    assert done is not None
    assert done.status is RunStatus.DONE
    assert done.finished_at is not None


@pytest.mark.asyncio
async def test_illegal_transition_raises() -> None:
    """An illegal edge (QUEUED→DONE) raises IllegalRunTransitionError."""
    ledger = InMemoryRunLedger()
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)
    with pytest.raises(IllegalRunTransitionError):
        await ledger.set_status("run_1", RunStatus.DONE)  # must pass through RUNNING


@pytest.mark.asyncio
async def test_same_status_is_idempotent_noop() -> None:
    """Re-setting the current status is a no-op (duplicate claim / terminal write)."""
    ledger = InMemoryRunLedger()
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.set_status("run_1", RunStatus.RUNNING)
    await ledger.set_status("run_1", RunStatus.RUNNING)  # no raise
    assert (await ledger.get("run_1")).status is RunStatus.RUNNING  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_failed_retry_bumps_attempt() -> None:
    """FAILED→QUEUED (explicit retry) increments attempt."""
    ledger = InMemoryRunLedger()
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.set_status("run_1", RunStatus.RUNNING)
    await ledger.set_status("run_1", RunStatus.FAILED, error="boom")
    await ledger.set_status("run_1", RunStatus.QUEUED)
    run = await ledger.get("run_1")
    assert run is not None
    assert run.attempt == 1
    assert run.status is RunStatus.QUEUED


@pytest.mark.asyncio
async def test_bump_enqueue_seq_is_monotonic() -> None:
    """bump_enqueue_seq yields a fresh, increasing seq per resume hop."""
    ledger = InMemoryRunLedger()
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)
    assert await ledger.bump_enqueue_seq("run_1") == 1
    assert await ledger.bump_enqueue_seq("run_1") == 2


@pytest.mark.asyncio
async def test_append_event_excludes_tokens() -> None:
    """append_event records non-TOKEN events only (tokens are too chatty for Steps)."""
    ledger = InMemoryRunLedger()
    await ledger.create(_intent(), workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.append_event(RunEvent(run_id="run_1", seq=0, kind=RunEventKind.STATUS, data="running"))
    await ledger.append_event(RunEvent(run_id="run_1", seq=1, kind=RunEventKind.TOKEN, data="chatty"))
    await ledger.append_event(RunEvent(run_id="run_1", seq=2, kind=RunEventKind.DONE, data="done"))
    kinds = [str(e.kind) for e in ledger.events("run_1")]
    assert kinds == ["status", "done"]


@pytest.mark.asyncio
async def test_list_by_status_and_get_by_consent() -> None:
    """list_by_status feeds reconcile; get_by_consent feeds engine.approve."""
    ledger = InMemoryRunLedger()
    await ledger.create(_intent("a"), workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.create(_intent("b"), workflow_name="bridge_chat", queue_name="runs", priority=50)
    await ledger.set_status("a", RunStatus.RUNNING)

    running = await ledger.list_by_status(RunStatus.RUNNING)
    assert [r.run_id for r in running] == ["a"]

    await ledger.set_status("b", RunStatus.RUNNING)
    await ledger.set_status("b", RunStatus.AWAITING_CONSENT)
    await ledger.set_consent("b", "consent_9")
    found = await ledger.get_by_consent("consent_9")
    assert found is not None
    assert found.run_id == "b"
    assert await ledger.get_by_consent("missing") is None
