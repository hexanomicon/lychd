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
async def test_same_key_different_priorities_do_not_share_a_declining_owner() -> None:
    """Priority cohorts stay separate so a hotter request gets its own execution."""
    arbiter = TransitionArbiter()
    gate = asyncio.Event()
    order: list[str] = []

    async def low_executor() -> TransitionPlan:
        order.append("low")
        await gate.wait()
        return _plan("low")

    low = asyncio.create_task(arbiter.run("same", 10.0, low_executor))
    await asyncio.sleep(0)
    high = asyncio.create_task(
        arbiter.run("same", 90.0, lambda: _await_plan(order, "high"))
    )
    await asyncio.sleep(0)
    gate.set()

    low_plan, high_plan = await asyncio.gather(low, high)

    assert low_plan.reason == "low"
    assert high_plan.reason == "high"
    assert order == ["low", "high"]


@pytest.mark.asyncio
async def test_cancelling_one_same_key_follower_does_not_poison_shared_transition() -> None:
    """A follower owns its wait only; cancelling it leaves owner and peers intact."""
    arbiter = TransitionArbiter()
    calls = 0
    gate = asyncio.Event()

    async def _executor() -> TransitionPlan:
        nonlocal calls
        calls += 1
        await gate.wait()
        return _plan("survived")

    owner = asyncio.create_task(arbiter.run("same", 50.0, _executor))
    await asyncio.sleep(0)
    cancelled_follower = asyncio.create_task(arbiter.run("same", 50.0, _executor))
    surviving_follower = asyncio.create_task(arbiter.run("same", 50.0, _executor))
    await asyncio.sleep(0)

    cancelled_follower.cancel()
    with pytest.raises(asyncio.CancelledError):
        await cancelled_follower

    gate.set()
    owner_plan, follower_plan = await asyncio.gather(owner, surviving_follower)

    assert calls == 1
    assert owner_plan is follower_plan
    assert follower_plan.reason == "survived"


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


# ---------------------------------------------------------------------------
# F2 (P1): a parked waiter that is cancelled must NOT wedge the arbiter — neither
# a ghost handoff (_busy stuck True) nor a leaked in-flight future may survive.
# The PoC that proved the pre-fix deadlock: after cancelling a parked waiter, a
# third transition hangs and a same-key retry hangs. asyncio.wait_for fails loudly.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancelled_parked_waiter_does_not_wedge_a_later_transition() -> None:
    """Cancel a parked waiter → the section still frees, so a later transition runs."""
    arbiter = TransitionArbiter()
    release_owner = asyncio.Event()

    async def _owner() -> TransitionPlan:
        await release_owner.wait()  # hold the section so the next caller parks
        return _plan("owner")

    owner = asyncio.create_task(arbiter.run("key-a", 50.0, _owner))
    await asyncio.sleep(0)  # owner claims the section

    waiter = asyncio.create_task(arbiter.run("key-b", 50.0, lambda: _await_plan([], "b")))
    await asyncio.sleep(0)  # waiter parks in the priority heap

    waiter.cancel()  # cancelled WHILE parked (plausible during a 120s drain)
    with pytest.raises(asyncio.CancelledError):
        await waiter

    release_owner.set()
    assert (await asyncio.wait_for(owner, timeout=1.0)).reason == "owner"

    # A subsequent, different-key transition must proceed — no ghost-handoff wedge.
    third = await asyncio.wait_for(arbiter.run("key-c", 50.0, lambda: _await_plan([], "third")), timeout=1.0)
    assert third.reason == "third"


@pytest.mark.asyncio
async def test_cancelled_parked_waiter_frees_inflight_for_same_key_retry() -> None:
    """Cancel a parked waiter → a same-key retry executes, not hangs on a leaked future."""
    arbiter = TransitionArbiter()
    release_owner = asyncio.Event()

    async def _owner() -> TransitionPlan:
        await release_owner.wait()
        return _plan("owner")

    owner = asyncio.create_task(arbiter.run("key-a", 50.0, _owner))
    await asyncio.sleep(0)

    waiter = asyncio.create_task(arbiter.run("key-b", 50.0, lambda: _await_plan([], "b1")))
    await asyncio.sleep(0)
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter

    release_owner.set()
    await asyncio.wait_for(owner, timeout=1.0)

    # Retrying the cancelled waiter's OWN key must execute — the leaked in-flight
    # future was popped, so `run` does not `return await` a never-resolving future.
    retry = await asyncio.wait_for(arbiter.run("key-b", 50.0, lambda: _await_plan([], "b2")), timeout=1.0)
    assert retry.reason == "b2"
