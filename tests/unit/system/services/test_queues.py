"""Cancellation authority at the SAQ PostgreSQL queue boundary."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import pytest
from saq.job import Status

from lychd.system.services.queues import CancellationSafePostgresRunQueue


class _Connection:
    def __init__(self) -> None:
        self.in_transaction = False
        self.transaction_entries = 0

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        assert not self.in_transaction
        self.transaction_entries += 1
        self.in_transaction = True
        try:
            yield
        finally:
            self.in_transaction = False


class _Pool:
    def __init__(self) -> None:
        self.acquired = _Connection()

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[_Connection]:
        yield self.acquired


class _PartiallyOpenedPool:
    def __init__(self) -> None:
        self.closed = False
        self.close_calls = 0

    async def close(self) -> None:
        self.close_calls += 1
        self.closed = True


class _PartialConnectQueue:
    name = "runs"
    _manage_pool_lifecycle = True

    def __init__(self) -> None:
        self.pool = _PartiallyOpenedPool()
        self.disconnect_calls = 0

    async def connect(self) -> None:
        msg = "schema initialization failed"
        raise RuntimeError(msg)

    async def disconnect(self) -> None:
        self.disconnect_calls += 1


@dataclass
class _Job:
    key: str = "run:r:0"
    status: Status = Status.ACTIVE
    refresh_to: Status | None = Status.ABORTED

    async def refresh(self, until_complete: float | None = None) -> None:
        _ = until_complete
        if self.refresh_to is not None:
            self.status = self.refresh_to


class _PostgresQueueDouble:
    name = "runs"

    def __init__(self, status: Status | None) -> None:
        self.pool = _Pool()
        self.status = status
        self.finished: list[Status] = []
        self.updated: list[Status] = []
        self.transaction_observations: list[tuple[str, bool]] = []

    def _observe_transaction(self, operation: str, kwargs: dict[str, Any]) -> None:
        connection = kwargs.get("connection")
        assert connection is self.pool.acquired
        self.transaction_observations.append((operation, self.pool.acquired.in_transaction))

    async def get_job_status(self, key: str, **kwargs: Any) -> Status | None:
        _ = key
        self._observe_transaction("get_job_status", kwargs)
        return self.status

    async def finish(self, job: _Job, status: Status, **kwargs: Any) -> None:
        _ = job
        self._observe_transaction("finish", kwargs)
        self.finished.append(status)
        self.status = status

    async def update(self, job: _Job, *, status: Status, **kwargs: Any) -> None:
        _ = job
        self._observe_transaction("update", kwargs)
        self.updated.append(status)
        self.status = status


@pytest.mark.asyncio
async def test_failed_connect_closes_pool_even_when_saq_disconnect_is_a_noop() -> None:
    queue = _PartialConnectQueue()
    guarded = CancellationSafePostgresRunQueue(queue)

    with pytest.raises(RuntimeError, match="schema initialization failed"):
        await guarded.connect()

    assert queue.disconnect_calls == 1
    assert queue.pool.close_calls == 1
    assert queue.pool.closed is True


@pytest.mark.asyncio
async def test_abort_is_atomic_noop_for_terminal_job() -> None:
    queue = _PostgresQueueDouble(Status.COMPLETE)
    guarded = CancellationSafePostgresRunQueue(queue)

    await guarded.abort(_Job(status=Status.COMPLETE), "cancel")

    assert queue.finished == []
    assert queue.updated == []


@pytest.mark.asyncio
async def test_abort_finishes_queued_job_without_worker_ack() -> None:
    queue = _PostgresQueueDouble(Status.QUEUED)
    guarded = CancellationSafePostgresRunQueue(queue)

    await guarded.abort(_Job(status=Status.QUEUED), "cancel")

    assert queue.finished == [Status.ABORTED]
    assert queue.updated == []


@pytest.mark.asyncio
async def test_abort_waits_for_active_worker_ack() -> None:
    queue = _PostgresQueueDouble(Status.ACTIVE)
    guarded = CancellationSafePostgresRunQueue(queue)
    job = _Job(status=Status.ACTIVE, refresh_to=Status.ABORTED)

    await guarded.abort(job, "cancel", ttl=0.1)

    assert queue.updated == [Status.ABORTING]
    assert job.status is Status.ABORTED


@pytest.mark.asyncio
async def test_abort_guards_and_updates_inside_one_explicit_transaction() -> None:
    queue = _PostgresQueueDouble(Status.ACTIVE)
    guarded = CancellationSafePostgresRunQueue(queue)

    await guarded.abort(_Job(), "cancel")

    assert queue.pool.acquired.transaction_entries == 1
    assert queue.transaction_observations == [
        ("get_job_status", True),
        ("update", True),
    ]
    assert not queue.pool.acquired.in_transaction


@pytest.mark.asyncio
async def test_abort_refuses_to_claim_ack_when_worker_does_not_finish() -> None:
    queue = _PostgresQueueDouble(Status.ACTIVE)
    guarded = CancellationSafePostgresRunQueue(queue)
    job = _Job(status=Status.ACTIVE, refresh_to=None)

    with pytest.raises(TimeoutError, match="did not acknowledge"):
        await guarded.abort(job, "cancel", ttl=0.1)


@pytest.mark.asyncio
async def test_orphan_abort_force_fences_preboot_active_job() -> None:
    queue = _PostgresQueueDouble(Status.ACTIVE)
    guarded = CancellationSafePostgresRunQueue(queue)

    await guarded.abort_orphan(_Job(), "reanimation")

    assert queue.finished == [Status.ABORTED]
    assert queue.updated == []
