"""Orchestration scenarios across real coordination and inert runtime boundaries.

Only adapter observations/activation, model execution, and host actuation are fake.
The registry probe lock, dispatcher, leases, claim gate, policy, arbiter, and manager
retain their production behavior; a fake probe never makes a runtime warm by itself.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import AsyncExitStack

import pytest

from lychd.domain.animation.errors import HardwareTransitionRequired
from lychd.domain.cortex.leases import AnimatorAdmission
from lychd.domain.orchestration.actuator import RuntimePreconditionError, TransitionIntent
from lychd.domain.orchestration.arbiter import TransitionDeclined
from lychd.domain.orchestration.schema import TransitionTrace
from tests.capability_workflows import build_capability_scenario as _scenario


async def _eventually(predicate: Callable[[], bool]) -> None:
    async with asyncio.timeout(1):
        while not predicate():  # noqa: ASYNC110 - gate/trace observations expose no change event
            await asyncio.sleep(0)


@pytest.mark.asyncio
@pytest.mark.parametrize("planning_pass", [1, 2], ids=["preflight", "post-arbiter-replan"])
async def test_hung_planning_probe_declines_without_gates_or_late_state(planning_pass: int) -> None:
    scenario = _scenario(active={"a"})
    target = "b:chat:b-model"
    trace = TransitionTrace(target_capability_key=target, priority=50)
    interrupted = asyncio.Event()
    pass_number = 0

    async def block(name: str) -> None:
        nonlocal pass_number
        if name == "a":
            pass_number += 1
            if pass_number == planning_pass:
                try:
                    await asyncio.Event().wait()
                finally:
                    interrupted.set()

    scenario.world.before_probe = block
    with pytest.raises(RuntimePreconditionError, match=r"planning|Planning"):
        async with asyncio.timeout(0.5):
            await scenario.manager.request_transition(target, 50, trace=trace)

    assert interrupted.is_set()
    assert scenario.registry.get_capability_state("a:chat:a-model") is None
    assert scenario.actuator.intents == []
    assert scenario.leases.active() == []
    assert scenario.leases.admission("a") is AnimatorAdmission.OPEN
    assert not scenario.broker.paused
    assert trace.phase == "declined_no_effect"
    assert scenario.manager.containment_reason is None

    scenario.world.before_probe = None
    await scenario.manager.request_transition(target, 50)
    assert scenario.world.active == {"b"}


@pytest.mark.asyncio
@pytest.mark.parametrize("planning_pass", [1, 2], ids=["preflight", "post-arbiter-replan"])
async def test_trickling_peer_probes_share_one_planning_budget(planning_pass: int) -> None:
    scenario = _scenario(models={name: (f"{name}-model",) for name in ("a", "b", "c")}, active={"a"})
    pass_number = 0

    async def trickle(name: str) -> None:
        nonlocal pass_number
        if name == "a":
            pass_number += 1
        if pass_number == planning_pass:
            await asyncio.sleep(0.025)

    scenario.world.before_probe = trickle
    with pytest.raises(RuntimePreconditionError, match=r"planning|Planning"):
        await scenario.manager.request_transition("c:chat:c-model", 50)

    assert scenario.actuator.intents == []
    assert scenario.world.active == {"a"}
    assert not scenario.broker.paused


@pytest.mark.asyncio
async def test_planning_timeout_reaches_same_priority_cohort_and_allows_exact_retry() -> None:
    scenario = _scenario(active={"a"})
    entered = asyncio.Event()

    async def block(name: str) -> None:
        entered.set()
        await asyncio.Event().wait()

    scenario.world.before_probe = block
    target = "b:chat:b-model"
    owner = asyncio.create_task(scenario.manager.request_transition(target, 50))
    await entered.wait()
    follower_trace = TransitionTrace(target_capability_key=target, priority=50)
    follower = asyncio.create_task(scenario.manager.request_transition(target, 50, trace=follower_trace))
    await _eventually(lambda: follower_trace.phase == "arbitrating")
    async with asyncio.timeout(0.5):
        outcomes = await asyncio.gather(owner, follower, return_exceptions=True)

    assert all(isinstance(result, RuntimePreconditionError) for result in outcomes)
    assert outcomes[0] is outcomes[1]
    assert scenario.world.probes == ["a"]
    assert follower_trace.phase == "declined_no_effect"
    assert not scenario.broker.paused
    assert scenario.actuator.intents == []
    scenario.world.before_probe = None
    await scenario.manager.request_transition(target, 50)
    assert scenario.world.active == {"b"}


@pytest.mark.asyncio
async def test_cancelled_planning_owner_releases_cohort_and_real_probe_lock() -> None:
    scenario = _scenario(active={"a"})
    entered = asyncio.Event()

    async def block(name: str) -> None:
        entered.set()
        await asyncio.Event().wait()

    scenario.world.before_probe = block
    owner = asyncio.create_task(scenario.manager.request_transition("b:chat:b-model", 50))
    await entered.wait()
    follower_trace = TransitionTrace(target_capability_key="b:chat:b-model", priority=50)
    follower = asyncio.create_task(scenario.manager.request_transition("b:chat:b-model", 50, trace=follower_trace))
    await _eventually(lambda: follower_trace.phase == "arbitrating")
    owner.cancel()
    outcomes = await asyncio.gather(owner, follower, return_exceptions=True)

    assert all(isinstance(result, asyncio.CancelledError) for result in outcomes)
    assert scenario.actuator.intents == []
    assert not scenario.broker.paused
    scenario.world.before_probe = None
    await scenario.manager.request_transition("b:chat:b-model", 50)
    assert scenario.world.active == {"b"}


@pytest.mark.asyncio
async def test_planning_lock_wait_timeout_preserves_the_independent_probe_owner() -> None:
    scenario = _scenario(active={"a"})
    entered = asyncio.Event()
    release = asyncio.Event()
    original = scenario.registry.get_capability_state("a:chat:a-model")

    async def block(name: str) -> None:
        entered.set()
        await release.wait()

    scenario.world.before_probe = block
    independent = asyncio.create_task(scenario.registry.refresh_capability_state("a:chat:a-model"))
    await entered.wait()
    try:
        with pytest.raises(RuntimePreconditionError, match=r"planning|Planning"):
            await scenario.manager.request_transition("b:chat:b-model", 50)
        assert not independent.done()
        assert scenario.registry.get_capability_state("a:chat:a-model") is original
        assert scenario.actuator.intents == []
        assert not scenario.broker.paused
    finally:
        release.set()
        await independent

    scenario.world.before_probe = None
    await scenario.manager.request_transition("b:chat:b-model", 50)
    assert scenario.world.active == {"b"}


@pytest.mark.asyncio
@pytest.mark.parametrize("policy", ["declared-conflicts", "evict-idle"])
async def test_gpu_swap_drains_every_conflicting_lease_but_allows_independent_grants(policy: str) -> None:
    scenario = _scenario(
        models={"a": ("a-model",), "b": ("b-model",), "side": ("side-model",)},
        active={"a", "side"},
        coexist=("side",),
        policy=policy,
    )
    async with AsyncExitStack() as leases:
        for run_id in ("first", "second"):
            await leases.enter_async_context(
                scenario.dispatcher.lease_grant(family="chat", model_name="a-model", run_id=run_id),
            )
        transition = asyncio.create_task(scenario.manager.request_transition("b:chat:b-model", 80))
        await _eventually(lambda: scenario.broker.paused)
        assert len(scenario.leases.active(animator_name="a")) == 2
        assert scenario.actuator.intents == []
        assert scenario.leases.admission("b") is AnimatorAdmission.DRAINING
        with pytest.raises(HardwareTransitionRequired):
            async with scenario.dispatcher.lease_grant(family="chat", model_name="a-model", run_id="late"):
                pytest.fail("a draining GPU acquired another grant")
        async with scenario.dispatcher.lease_grant(family="chat", model_name="side-model", run_id="side"):
            assert len(scenario.leases.active(animator_name="side")) == 1
        await leases.aclose()
        await transition

    assert scenario.world.active == {"b", "side"}
    assert scenario.actuator.intents[0].evict_animators == ("a",)
    assert scenario.leases.active() == []
    assert not scenario.broker.paused


@pytest.mark.asyncio
async def test_switching_models_in_one_dedicated_runtime_drains_the_existing_model() -> None:
    scenario = _scenario(models={"router": ("small", "large")}, active={"router"})
    async with scenario.dispatcher.lease_grant(family="chat", model_name="small", run_id="reader"):
        with pytest.raises(HardwareTransitionRequired):
            async with scenario.dispatcher.lease_grant(family="chat", model_name="large", run_id="switcher"):
                pytest.fail("the unloaded model was granted")
        transition = asyncio.create_task(scenario.manager.request_transition("router:chat:large", 5))
        await _eventually(lambda: scenario.broker.paused)
        assert scenario.world.loaded["router"] == "small"
        assert scenario.world.activations == []

    plan = await transition
    assert plan.action_type == "SOFT_SWAP"
    assert scenario.actuator.intents == []
    assert scenario.world.activations == ["router:chat:large"]
    async with scenario.dispatcher.lease_grant(family="chat", model_name="large", run_id="resumed") as grant:
        assert grant.spec.model_id == "large"


@pytest.mark.asyncio
async def test_queued_gpu_targets_replan_after_predecessor_and_priority_orders_waiters() -> None:
    scenario = _scenario(models={name: (f"{name}-model",) for name in ("a", "b", "c", "d")}, active={"a"})
    first_submitted = asyncio.Event()
    finish_first = asyncio.Event()

    async def hold_first(intent: TransitionIntent) -> None:
        if intent.target_animator == "b":
            first_submitted.set()
            await finish_first.wait()

    scenario.actuator.before_apply = hold_first
    owner = asyncio.create_task(scenario.manager.request_transition("b:chat:b-model", 50))
    await first_submitted.wait()
    low_trace = TransitionTrace(target_capability_key="c:chat:c-model", priority=45)
    high_trace = TransitionTrace(target_capability_key="d:chat:d-model", priority=90)
    low = asyncio.create_task(scenario.manager.request_transition("c:chat:c-model", 45, trace=low_trace))
    high = asyncio.create_task(scenario.manager.request_transition("d:chat:d-model", 90, trace=high_trace))
    await _eventually(lambda: low_trace.phase == high_trace.phase == "arbitrating")
    finish_first.set()
    await asyncio.gather(owner, low, high)

    assert [intent.target_animator for intent in scenario.actuator.intents] == ["b", "d", "c"]
    assert [intent.evict_animators for intent in scenario.actuator.intents] == [("a",), ("b",), ("d",)]
    assert scenario.world.active == {"c"}
    assert not scenario.broker.paused


@pytest.mark.asyncio
async def test_same_target_followers_share_one_transaction_despite_one_follower_cancelling() -> None:
    scenario = _scenario(active={"a"})
    submitted = asyncio.Event()
    finish = asyncio.Event()

    async def hold(intent: TransitionIntent) -> None:
        submitted.set()
        await finish.wait()

    scenario.actuator.before_apply = hold
    target = "b:chat:b-model"
    owner = asyncio.create_task(scenario.manager.request_transition(target, 50))
    await submitted.wait()
    count = len(scenario.world.probes)
    cancelled_trace = TransitionTrace(target_capability_key=target, priority=50)
    survivor_trace = TransitionTrace(target_capability_key=target, priority=50)
    cancelled = asyncio.create_task(scenario.manager.request_transition(target, 50, trace=cancelled_trace))
    survivor = asyncio.create_task(scenario.manager.request_transition(target, 50, trace=survivor_trace))
    await _eventually(lambda: cancelled_trace.phase == survivor_trace.phase == "arbitrating")
    cancelled.cancel()
    with pytest.raises(asyncio.CancelledError):
        await cancelled
    assert len(scenario.world.probes) == count
    assert not owner.done()
    assert not survivor.done()
    finish.set()
    owner_plan, survivor_plan = await asyncio.gather(owner, survivor)

    assert owner_plan is survivor_plan
    assert len(scenario.actuator.intents) == 1
    assert scenario.world.active == {"b"}
    assert not scenario.broker.paused


@pytest.mark.asyncio
async def test_warm_independent_request_bypasses_an_unsettled_gpu_transaction() -> None:
    scenario = _scenario(
        models={"a": ("a-model",), "b": ("b-model",), "side": ("side-model",)},
        active={"a", "side"},
        coexist=("side",),
    )
    submitted = asyncio.Event()
    finish = asyncio.Event()

    async def hold(intent: TransitionIntent) -> None:
        submitted.set()
        await finish.wait()

    scenario.actuator.before_apply = hold
    owner = asyncio.create_task(scenario.manager.request_transition("b:chat:b-model", 50))
    await submitted.wait()
    try:
        async with asyncio.timeout(0.5):
            side_plan = await scenario.manager.request_transition("side:chat:side-model", 1)
        assert side_plan.action_type == "NO_OP"
        assert not owner.done()
        assert scenario.broker.paused
        assert scenario.leases.admission("side") is AnimatorAdmission.OPEN
    finally:
        finish.set()
        await owner


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True], ids=["timeout", "cancelled"])
async def test_interrupted_real_lease_drain_preserves_the_grant_and_allows_retry(*, cancel: bool) -> None:
    scenario = _scenario(active={"a"})
    async with scenario.dispatcher.lease_grant(family="chat", model_name="a-model", run_id="holder") as grant:
        owner = asyncio.create_task(scenario.manager.request_transition("b:chat:b-model", 50))
        await _eventually(lambda: scenario.broker.paused)
        if cancel:
            owner.cancel()
            with pytest.raises(asyncio.CancelledError):
                await owner
        else:
            with pytest.raises(RuntimeError, match="Lease drain timed out"):
                await owner
        assert scenario.world.active == {"a"}
        assert scenario.leases.active()[0].grant_id == grant.lease.grant_id
        assert scenario.actuator.intents == []
        assert not scenario.broker.paused
        assert scenario.leases.admission("a") is AnimatorAdmission.OPEN
        assert scenario.leases.admission("b") is AnimatorAdmission.OPEN
        assert scenario.manager.containment_reason is None

    await scenario.manager.request_transition("b:chat:b-model", 50)
    assert scenario.world.active == {"b"}
    assert scenario.leases.active() == []


@pytest.mark.asyncio
async def test_low_priority_decline_does_not_poison_same_target_high_priority() -> None:
    scenario = _scenario(active={"a"})
    entered = asyncio.Event()
    release = asyncio.Event()

    async def hold_first_probe(name: str) -> None:
        if not entered.is_set():
            entered.set()
            await release.wait()

    scenario.world.before_probe = hold_first_probe
    low = asyncio.create_task(scenario.manager.request_transition("b:chat:b-model", 20))
    await entered.wait()
    high = asyncio.create_task(scenario.manager.request_transition("b:chat:b-model", 80))
    release.set()
    low_result, high_result = await asyncio.gather(low, high, return_exceptions=True)

    assert isinstance(low_result, TransitionDeclined)
    assert not isinstance(high_result, BaseException)
    assert high_result.action_type == "HARD_SWAP"
    assert len(scenario.actuator.intents) == 1
    assert scenario.world.active == {"b"}
