"""Bounded process-local Nexus ticket retention."""

from __future__ import annotations

import asyncio

import pytest

from lychd.domain.web.tickets import TicketCapacityError, TicketStore


@pytest.mark.parametrize(
    ("capacity", "terminal_retention_s"),
    [(0, 60.0), (1, 0.0)],
)
def test_ticket_store_requires_positive_bounds(
    capacity: int,
    terminal_retention_s: float,
) -> None:
    with pytest.raises(
        ValueError,
        match=r"Ticket (capacity|terminal retention) must be positive",
    ):
        TicketStore(
            capacity=capacity,
            terminal_retention_s=terminal_retention_s,
        )


@pytest.mark.asyncio
async def test_terminal_ticket_survives_reconnect_window_then_retires() -> None:
    now = [100.0]
    store = TicketStore(
        capacity=1,
        terminal_retention_s=10.0,
        clock=lambda: now[0],
    )
    task = asyncio.create_task(asyncio.sleep(0))
    record = store.open(
        target="chat:local",
        action_type="SOFT_SWAP",
        total_metabolic_cost=1.0,
        task=task,
    )
    await task
    await asyncio.sleep(0)

    assert store.get(record.id) is record
    with pytest.raises(TicketCapacityError):
        store.ensure_capacity()

    now[0] = 109.99
    assert store.get(record.id) is record
    now[0] = 110.0
    assert store.get(record.id) is None
    store.ensure_capacity()


@pytest.mark.asyncio
async def test_capacity_refusal_cancels_unadmitted_task_without_evicting_active_truth() -> None:
    release = asyncio.Event()
    store = TicketStore(capacity=1)
    active = asyncio.create_task(release.wait())
    record = store.open(
        target="chat:first",
        action_type="SOFT_SWAP",
        total_metabolic_cost=1.0,
        task=active,
    )
    refused = asyncio.create_task(release.wait())

    with pytest.raises(TicketCapacityError):
        store.open(
            target="chat:second",
            action_type="SOFT_SWAP",
            total_metabolic_cost=1.0,
            task=refused,
        )
    await asyncio.sleep(0)

    assert refused.cancelled()
    assert store.get(record.id) is record
    assert not active.done()

    release.set()
    await active
    await store.aclose()


@pytest.mark.asyncio
async def test_capacity_reservation_fences_the_durable_admission_await() -> None:
    store = TicketStore(capacity=1)
    store.reserve_capacity("request-first")

    with pytest.raises(TicketCapacityError):
        store.reserve_capacity("request-second")

    task = asyncio.create_task(asyncio.sleep(0))
    record = store.open(
        target="chat:first",
        action_type="SOFT_SWAP",
        total_metabolic_cost=1.0,
        task=task,
        reservation="request-first",
    )
    await task

    assert store.get(record.id) is record
    store.release_capacity("request-first")  # idempotent after consumption
    await store.aclose()
