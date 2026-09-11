"""Only an invoked activation can make soft-convergence failure uncertain.

Real registry, lease, claim, and arbitration boundaries surround inert runtime
observations. Device names are declared conflict domains, not measured placement.
"""

from __future__ import annotations

import asyncio
from typing import Literal

import pytest

from lychd.domain.animation.animators import RuntimeAnimator
from lychd.domain.animation.capabilities import ActivationResult, CapabilityPhase, CapabilitySpec, CapabilityState
from lychd.domain.animation.errors import ActivationTimeout
from lychd.domain.cortex.leases import AnimatorAdmission
from lychd.domain.orchestration.actuator import RuntimeCancellationNoEffectError, RuntimePreconditionError
from lychd.domain.orchestration.schema import TransitionTrace
from tests.capability_workflows import CapabilityScenario, build_capability_scenario

type FailureKind = Literal["error", "timeout", "cancelled"]


class ObservationError(RuntimeError):
    """An inert runtime could not supply an observation."""


def _scenario(domains: int = 2, *, dynamic: bool = True) -> CapabilityScenario:
    models = {"router": ("small", "large") if dynamic else ("large",)}
    models.update({f"peer-{index}": (f"chat-{index}",) for index in range(1, domains)})
    return build_capability_scenario(
        models=models,
        active=set(models),
        conflict_domains={name: (f"gpu-{index}",) for index, name in enumerate(models)},
    )


async def _fail(kind: FailureKind, entered: asyncio.Event, settled: asyncio.Event) -> None:
    entered.set()
    try:
        if kind == "error":
            message = "inert inventory observation failed"
            raise ObservationError(message)
        await asyncio.Event().wait()
    finally:
        settled.set()


async def _expect_no_effect(scenario: CapabilityScenario, kind: FailureKind, entered: asyncio.Event) -> TransitionTrace:
    trace = TransitionTrace(target_capability_key="router:chat:large", priority=80)
    owner = asyncio.create_task(scenario.manager.request_transition(trace.target_capability_key, 80, trace=trace))
    if kind == "cancelled":
        await asyncio.wait_for(entered.wait(), timeout=1)
        owner.cancel()
    error_type = RuntimeCancellationNoEffectError if kind == "cancelled" else RuntimePreconditionError
    with pytest.raises(error_type) as error:
        await asyncio.wait_for(owner, timeout=1)
    cause_type = {
        "error": ObservationError,
        "timeout": ActivationTimeout,
        "cancelled": asyncio.CancelledError,
    }[kind]
    assert isinstance(error.value.__cause__, cause_type)
    assert trace.phase == "declined_no_effect"
    assert scenario.manager.containment_reason is None
    assert not scenario.broker.paused
    assert scenario.leases.admission("router") is AnimatorAdmission.OPEN
    assert scenario.world.activations == []
    assert scenario.actuator.intents == []
    assert scenario.leases.active() == []
    return trace


@pytest.mark.asyncio
@pytest.mark.parametrize("domains", [2, 4])
@pytest.mark.parametrize("kind", ["error", "timeout", "cancelled"])
async def test_initial_soft_observation_failure_reopens_independent_domains(domains: int, kind: FailureKind) -> None:
    scenario = _scenario(domains)
    entered, settled = asyncio.Event(), asyncio.Event()

    async def fail_when_drained(name: str) -> None:
        if name == "router" and scenario.broker.paused:
            await _fail(kind, entered, settled)

    scenario.world.before_probe = fail_when_drained
    await _expect_no_effect(scenario, kind, entered)
    assert settled.is_set()
    assert scenario.world.loaded["router"] == "small"
    assert scenario.registry.get_capability_state("router:chat:large") is None

    # Neither the process claim gate nor mutation containment may strand an
    # independently declared warm domain after a read-only observation fails.
    plan = await scenario.manager.request_transition("peer-1:chat:chat-1", 80)
    assert plan.action_type == "NO_OP"
    async with scenario.dispatcher.lease_grant(family="chat", capability_key="peer-1:chat:chat-1", run_id="peer"):
        assert len(scenario.leases.active()) == 1
    scenario.world.before_probe = None
    await scenario.manager.request_transition("router:chat:large", 80)
    assert scenario.world.loaded["router"] == "large"
    assert scenario.world.activations == ["router:chat:large"]


@pytest.mark.asyncio
@pytest.mark.parametrize("dynamic", [False, True], ids=["static", "already-warming"])
@pytest.mark.parametrize("kind", ["error", "timeout", "cancelled"])
async def test_observation_only_warm_wait_failure_is_no_effect(
    monkeypatch: pytest.MonkeyPatch, *, dynamic: bool, kind: FailureKind
) -> None:
    scenario = _scenario(dynamic=dynamic)
    entered, settled = asyncio.Event(), asyncio.Event()
    original_probe = scenario.world.probe_capability_states
    closed_probes = 0

    async def observe_warming(animator: RuntimeAnimator, specs: list[CapabilitySpec]) -> list[CapabilityState]:
        nonlocal closed_probes
        states = await original_probe(animator, specs)
        if animator.name != "router":
            return states
        if scenario.broker.paused:
            closed_probes += 1
            if closed_probes > 1:
                await _fail(kind, entered, settled)
        return [state.model_copy(update={"phase": CapabilityPhase.WARMING}) for state in states]

    monkeypatch.setattr(scenario.world, "probe_capability_states", observe_warming)
    await _expect_no_effect(scenario, kind, entered)
    assert settled.is_set()
    assert closed_probes == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True], ids=["observation-error", "observation-cancel"])
async def test_soft_no_effect_classification_reaches_the_coalesced_follower(*, cancel: bool) -> None:
    scenario = _scenario()
    entered, release, joined = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def blocked_observation(name: str) -> None:
        if name == "router" and scenario.broker.paused:
            entered.set()
            await release.wait()
            message = "cohort observation failed"
            raise ObservationError(message)

    scenario.world.before_probe = blocked_observation
    owner_trace = TransitionTrace(target_capability_key="router:chat:large", priority=80)
    follower_trace = TransitionTrace(
        target_capability_key="router:chat:large",
        priority=80,
        observer=lambda record: joined.set() if record.phase == "arbitrating" else None,
    )
    owner = asyncio.create_task(
        scenario.manager.request_transition(owner_trace.target_capability_key, 80, trace=owner_trace)
    )
    await asyncio.wait_for(entered.wait(), timeout=1)
    follower = asyncio.create_task(
        scenario.manager.request_transition(follower_trace.target_capability_key, 80, trace=follower_trace)
    )
    await asyncio.wait_for(joined.wait(), timeout=1)
    if cancel:
        owner.cancel()
    else:
        release.set()
    error_type = RuntimeCancellationNoEffectError if cancel else RuntimePreconditionError
    # gather(return_exceptions=True) erases CancelledError subclasses, including
    # the no-effect receipt being checked here. Await each task to retain it.
    outcomes: list[BaseException] = []
    for task in (owner, follower):
        try:
            await asyncio.wait_for(task, timeout=1)
        except (RuntimeError, asyncio.CancelledError) as exc:
            outcomes.append(exc)
    assert len(outcomes) == 2
    assert all(isinstance(error, error_type) for error in outcomes)
    assert owner_trace.phase == follower_trace.phase == "declined_no_effect"
    assert scenario.manager.containment_reason is None
    assert not scenario.broker.paused
    assert scenario.leases.admission("router") is AnimatorAdmission.OPEN
    assert scenario.world.activations == []


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["rejected", "raised", "cancelled", "accepted-refresh", "warm-poll"])
async def test_invoking_activation_keeps_subsequent_failure_contained(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    scenario = _scenario()
    entered = asyncio.Event()
    original_activate = scenario.world.activate_capability
    post_activation_probes = 0

    async def activate(animator: RuntimeAnimator, spec: CapabilitySpec) -> ActivationResult:
        if failure in {"rejected", "raised", "cancelled"}:
            scenario.world.activations.append(spec.key)
            if failure == "rejected":
                return ActivationResult(accepted=False, reason="no authoritative no-effect receipt")
            if failure == "raised":
                message = "activation outcome unknown"
                raise ObservationError(message)
            entered.set()
            await asyncio.Event().wait()
        return await original_activate(animator, spec)

    async def fail_after_activation(name: str) -> None:
        nonlocal post_activation_probes
        if name == "router" and scenario.world.activations:
            post_activation_probes += 1
            if failure == "accepted-refresh" or (failure == "warm-poll" and post_activation_probes == 2):
                message = "post-activation observation failed"
                raise ObservationError(message)

    monkeypatch.setattr(scenario.world, "activate_capability", activate)
    scenario.world.before_probe = fail_after_activation
    trace = TransitionTrace(target_capability_key="router:chat:large", priority=80)
    owner = asyncio.create_task(scenario.manager.request_transition(trace.target_capability_key, 80, trace=trace))
    if failure == "cancelled":
        await asyncio.wait_for(entered.wait(), timeout=1)
        owner.cancel()
    error_type = asyncio.CancelledError if failure == "cancelled" else RuntimeError
    with pytest.raises(error_type):
        await asyncio.wait_for(owner, timeout=1)
    assert scenario.world.activations == ["router:chat:large"]
    assert scenario.actuator.intents == []
    assert scenario.manager.containment_reason is not None
    assert scenario.broker.paused
    assert scenario.leases.admission("router") is AnimatorAdmission.DRAINING
    assert scenario.leases.active() == []
    assert trace.phase == "contained_uncertain"
