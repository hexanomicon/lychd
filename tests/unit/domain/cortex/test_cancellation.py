"""Topology-A run cancellation coordination."""

from __future__ import annotations

import asyncio

import pytest

from lychd.domain.cortex.cancellation import RunCancellationCoordinator


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


@pytest.mark.asyncio
async def test_wait_without_active_cancel_returns_immediately() -> None:
    """A worker with an unrelated cancellation never parks on an absent writer."""
    coordinator = RunCancellationCoordinator()
    await coordinator.wait("run-1")
