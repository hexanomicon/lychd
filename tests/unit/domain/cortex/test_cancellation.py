"""Topology-A run cancellation coordination."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import pytest

from lychd.agents.router import Intent
from lychd.agents.workflows import BRIDGE_CHAT, builtin_workflow_registry
from lychd.domain.cortex.cancellation import RunCancellationCoordinator
from lychd.domain.cortex.claims import RunClaimCoordinator
from lychd.domain.cortex.engine import QueueRouter, RouteRule, RunEngine
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.ledger import InMemoryRunLedger
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.cortex.stasis import InMemoryStasisStore
from lychd.ghouls.runs import _settle_interrupted_claim

if TYPE_CHECKING:
    from lychd.domain.cortex.runs import RunRecord
    from lychd.domain.cortex.substrate import RunSubstrate


@pytest.mark.asyncio
async def test_begin_elects_one_writer_and_releases_waiters_on_finish() -> None:
    """Concurrent API callers share one fence and only the leader may write."""
    coordinator = RunCancellationCoordinator()
    assert coordinator.begin("run-1") is True
    assert coordinator.begin("run-1") is False
    waiter = asyncio.create_task(coordinator.wait("run-1"))
    await asyncio.sleep(0)

    assert coordinator.active("run-1") is True
    assert waiter.done() is False

    coordinator.finish("run-1")
    await waiter
    assert coordinator.active("run-1") is False
    await asyncio.wait_for(coordinator.wait("run-1"), timeout=0.1)


@pytest.mark.asyncio
@pytest.mark.parametrize("election_fails", [False, True])
async def test_interrupted_worker_waits_for_election_not_its_own_abort(
    monkeypatch: pytest.MonkeyPatch,
    *,
    election_fails: bool,
) -> None:
    """A pre-election interruption must not depend on full API cancellation."""
    ledger = InMemoryRunLedger(honor_intent_run_id=True)
    run = await ledger.create(
        Intent(session_id="s", run_id="election-race", prompt="inert"),
        workflow_name=BRIDGE_CHAT.name,
        pattern_manifest=BRIDGE_CHAT.manifest.snapshot(),
        queue_name="runs",
        priority=50,
    )
    assert await ledger.try_claim_run(run.run_id, enqueue_seq=0)
    election_entered = asyncio.Event()
    election_release = asyncio.Event()
    worker_waiting = asyncio.Event()
    real_begin = ledger.begin_cancel

    async def delayed_begin(run_id: str) -> RunRecord | None:
        election_entered.set()
        await election_release.wait()
        if election_fails:
            msg = "election unavailable"
            raise RuntimeError(msg)
        return await real_begin(run_id)

    class _ObservedCoordinator(RunCancellationCoordinator):
        async def wait(self, run_id: str) -> None:
            worker_waiting.set()
            await super().wait(run_id)

        async def wait_election(self, run_id: str) -> None:
            worker_waiting.set()
            await super().wait_election(run_id)

    class _AbortQueue:
        worker: asyncio.Task[bool] | None = None
        aborted = False

        async def enqueue(self, job_or_func: str, /, **kwargs: Any) -> None:
            _ = (job_or_func, kwargs)

        async def job(self, job_key: str, /) -> object:
            return job_key

        async def abort(self, job: Any, error: str, /, ttl: float = 5) -> None:
            _ = (job, error, ttl)
            assert self.worker is not None
            await asyncio.shield(self.worker)
            self.aborted = True

    coordinator = _ObservedCoordinator()
    queue = _AbortQueue()
    store = InMemoryStasisStore()
    engine = RunEngine(
        ledger=ledger,
        bus=InProcessEventBus(ledger=ledger),
        workflows=builtin_workflow_registry(),
        queue_router=QueueRouter(routing={"default": RouteRule(queue="runs", priority=50)}),
        queues={"runs": queue},
        cancellations=coordinator,
        stasis_store=store,
    )

    def release_context(_run_id: str) -> None:
        pass

    substrate = cast(
        "RunSubstrate",
        SimpleNamespace(
            ledger=ledger,
            cancellations=coordinator,
            claims=RunClaimCoordinator(),
            context=SimpleNamespace(release=release_context),
            stasis_store=store,
            consents=None,
            delegates=None,
        ),
    )
    monkeypatch.setattr(ledger, "begin_cancel", delayed_begin)
    monkeypatch.setattr("lychd.domain.cortex.engine.RUN_CONTAINMENT_TIMEOUT_S", 0.1)
    caller = asyncio.create_task(engine.cancel(run.run_id))
    await election_entered.wait()
    worker = asyncio.create_task(
        _settle_interrupted_claim(substrate, run, enqueue_seq=0, error="interrupted", persistence=None)
    )
    queue.worker = worker
    await worker_waiting.wait()
    election_release.set()
    results = await asyncio.wait_for(asyncio.gather(caller, worker, return_exceptions=True), timeout=1)

    current = await ledger.get(run.run_id)
    assert current is not None
    if election_fails:
        assert isinstance(results[0], RuntimeError)
        assert str(results[0]) == "election unavailable"
        assert results[1] is True
        assert current.status is RunStatus.FAILED
        assert queue.aborted is False
    else:
        assert results == [None, False]
        assert current.status is RunStatus.CANCELLED
        assert queue.aborted is True
    assert coordinator.active(run.run_id) is False
