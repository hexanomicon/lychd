"""O2: the TransitionArbiter — serialization, priority admission, same-key coalescing."""

from __future__ import annotations

import asyncio

import pytest

from lychd.domain.orchestration.arbiter import TransitionArbiter
from lychd.domain.orchestration.schema import TransitionPlan


def _plan(reason: str) -> TransitionPlan:
    return TransitionPlan(
        total_metabolic_cost=0.0,
        evict_coven_ids=[],
        launch_coven_ids=[],
        action_type="HARD_SWAP",
        reason=reason,
    )


@pytest.mark.asyncio
async def test_transitions_serialize_highest_priority_first() -> None:
    """Two concurrent requests run serially; the higher-priority contender goes first."""
    arbiter = TransitionArbiter()
    order: list[str] = []
    gate = asyncio.Event()

    async def _first_executor() -> TransitionPlan:
        order.append("low-start")
        await gate.wait()  # hold the section so the second waiter must queue
        order.append("low-end")
        return _plan("low")

    async def _hi_executor() -> TransitionPlan:
        order.append("hi")
        return _plan("hi")

    low = asyncio.create_task(arbiter.run("low-key", 10.0, _first_executor))
    await asyncio.sleep(0)  # let low claim the section
    hi = asyncio.create_task(arbiter.run("hi-key", 90.0, _hi_executor))
    med = asyncio.create_task(arbiter.run("med-key", 50.0, lambda: _await_plan(order, "med")))
    await asyncio.sleep(0)  # let hi + med enqueue as waiters

    gate.set()
    await asyncio.gather(low, hi, med)

    # low held the section first; on release the HIGHER-priority waiter (hi) precedes med.
    assert order == ["low-start", "low-end", "hi", "med"]


async def _await_plan(order: list[str], tag: str) -> TransitionPlan:
    order.append(tag)
    return _plan(tag)


@pytest.mark.asyncio
async def test_same_key_contenders_coalesce_onto_one_plan() -> None:
    """Same-key callers share ONE in-flight plan; the executor runs exactly once."""
    arbiter = TransitionArbiter()
    calls = 0
    gate = asyncio.Event()

    async def _executor() -> TransitionPlan:
        nonlocal calls
        calls += 1
        await gate.wait()
        return _plan("coalesced")

    first = asyncio.create_task(arbiter.run("same", 50.0, _executor))
    await asyncio.sleep(0)  # first registers the in-flight future + claims the section
    second = asyncio.create_task(arbiter.run("same", 50.0, _executor))
    await asyncio.sleep(0)

    gate.set()
    a, b = await asyncio.gather(first, second)

    assert calls == 1  # coalesced: executor invoked once
    assert a is b  # both callers received the SAME plan object
    assert a.reason == "coalesced"


@pytest.mark.asyncio
async def test_executor_exception_releases_section_and_reaches_all_same_key_waiters() -> None:
    """An executor error propagates to the owner AND every coalesced same-key waiter."""
    arbiter = TransitionArbiter()
    gate = asyncio.Event()

    async def _boom() -> TransitionPlan:
        await gate.wait()
        msg = "drain failed"
        raise RuntimeError(msg)

    owner = asyncio.create_task(arbiter.run("k", 50.0, _boom))
    await asyncio.sleep(0)
    waiter = asyncio.create_task(arbiter.run("k", 50.0, _boom))
    await asyncio.sleep(0)
    gate.set()

    with pytest.raises(RuntimeError, match="drain failed"):
        await owner
    with pytest.raises(RuntimeError, match="drain failed"):
        await waiter

    # the section was released — a fresh transition can still run
    assert (await arbiter.run("k2", 50.0, lambda: _await_plan([], "after"))).reason == "after"
