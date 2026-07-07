from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from lychd.config.settings import SwitchingSettings
from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityLifecycle,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
)
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.cortex.dispatcher import HardwareTransitionRequired
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.orchestration.arbiter import TransitionArbiter
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.policies import EvictIdlePolicy


def _make_manager(broker: object, registry: object, *, leases: LeaseLedger | None = None) -> OrchestratorManager:
    """Construct an OrchestratorManager with the default evict-idle policy + arbiter."""
    return OrchestratorManager(
        broker,
        registry=registry,  # type: ignore[arg-type]
        leases=leases or LeaseLedger(),
        policy=EvictIdlePolicy(),
        arbiter=TransitionArbiter(),
        switching=SwitchingSettings(),
    )


@dataclass
class StubRuntime:
    id: str
    base_url: str
    connector: SimpleNamespace


class StubRegistry:
    def __init__(
        self,
        specs: list[CapabilitySpec],
        states: list[CapabilityState],
        runtimes: dict[str, StubRuntime],
    ) -> None:
        self._specs = {spec.key: spec for spec in specs}
        self._states = {state.capability_key: state for state in states}
        self._runtimes = runtimes
        self.await_warm_calls: list[str] = []

    def list_capabilities(self) -> list[CapabilitySpec]:
        return list(self._specs.values())

    def get_capability(self, key: str) -> CapabilitySpec | None:
        return self._specs.get(key)

    def get_capability_state(self, key: str) -> CapabilityState | None:
        return self._states.get(key)

    async def refresh_capability_state(self, key: str) -> CapabilityState | None:
        return self._states.get(key)

    def list_capability_states_for_animator(self, name: str) -> list[CapabilityState]:
        return [state for key, state in self._states.items() if self._specs[key].animator_name == name]

    async def refresh_capability_states_for_animator(self, name: str) -> list[CapabilityState]:
        states = self.list_capability_states_for_animator(name)
        runtime = self._runtimes[name]
        for state in states:
            state.health = "ok" if runtime.connector.link.up else "down"
            if not runtime.connector.link.up:
                state.phase = CapabilityPhase.COLD
        return states

    def get_runtime(self, name: str) -> StubRuntime | None:
        return self._runtimes.get(name)

    def get_soulstone_rune(self, name: str) -> SimpleNamespace | None:
        if name not in self._runtimes:
            return None
        concurrency = next(
            (spec.concurrency for spec in self._specs.values() if spec.animator_name == name),
            ConcurrencyIntent(),
        )
        return SimpleNamespace(service_name=f"lychd-{name}", concurrency=concurrency)

    async def activate_capability(self, key: str) -> ActivationResult:
        spec = self._specs[key]
        runtime = self._runtimes[spec.animator_name]
        runtime.connector.link.up = True
        state = self._states[key]
        state.health = "ok"
        state.phase = CapabilityPhase.WARM
        state.active_model_id = spec.model_id
        state.loaded_model_ids = [spec.model_id]
        return ActivationResult(accepted=True, phase=CapabilityPhase.WARM)

    async def await_warm(self, key: str, *, timeout_s: float = 120.0, interval_s: float = 0.75) -> CapabilityState:
        _ = (timeout_s, interval_s)
        self.await_warm_calls.append(key)
        state = self._states[key]
        state.phase = CapabilityPhase.WARM
        return state


def _spec(
    *,
    key: str,
    animator_name: str,
    family: CapabilityFamily = CapabilityFamily.CHAT,
    lifecycle_mode: str = "static",
    runtime: str = "llamacpp",
    dedicated: bool = True,
    persistent_resident: bool = False,
) -> CapabilitySpec:
    return CapabilitySpec(
        key=key,
        animator_name=animator_name,
        runtime=runtime,
        source_kind="soulstone",
        family=family,
        model_id=key.rsplit(":", maxsplit=1)[-1],
        lifecycle=CapabilityLifecycle("dynamic" if lifecycle_mode == "dynamic_soft" else lifecycle_mode),
        concurrency=ConcurrencyIntent(
            dedicated=dedicated,
            persistent_resident=persistent_resident,
        ),
    )


def _state(
    spec: CapabilitySpec,
    *,
    is_static: bool = True,
    is_active: bool = False,
    warm: bool = False,
) -> CapabilityState:
    if warm:
        phase = CapabilityPhase.WARM
    elif is_active:
        phase = CapabilityPhase.WARMING
    else:
        phase = CapabilityPhase.COLD
    return CapabilityState(
        capability_key=spec.key,
        lifecycle=CapabilityLifecycle.STATIC if is_static else CapabilityLifecycle.DYNAMIC,
        phase=phase,
        health="ok" if warm else "down",
        active_model_id=spec.model_id if is_active else None,
        loaded_model_ids=[spec.model_id] if is_active else [],
    )


def _runtime(name: str, *, up: bool, base_url: str = "http://localhost:8080/v1") -> StubRuntime:
    return StubRuntime(
        id=name,
        base_url=base_url,
        connector=SimpleNamespace(link=Link(up=up, activatable=True)),
    )


@pytest.mark.asyncio
async def test_calculate_transition_plan_evicts_dedicated_and_keeps_persistent_resident() -> None:
    titan = _spec(key="titan:chat:titan-70b", animator_name="titan")
    coding = _spec(key="coding:chat:coding-8b", animator_name="coding")
    vision = _spec(
        key="vision:vision:vision-8b",
        animator_name="vision",
        family=CapabilityFamily.VISION,
    )
    resident = _spec(
        key="embedder:embedding:embed-1",
        animator_name="embedder",
        family=CapabilityFamily.EMBEDDING,
        persistent_resident=True,
        dedicated=False,
        runtime="vllm",
    )
    registry = StubRegistry(
        [titan, coding, vision, resident],
        [
            _state(titan, is_active=True, warm=True),
            _state(coding, is_active=True, warm=True),
            _state(vision),
            _state(resident, is_active=True, warm=True),
        ],
        {
            "titan": _runtime("titan", up=True),
            "coding": _runtime("coding", up=True),
            "vision": _runtime("vision", up=False),
            "embedder": _runtime("embedder", up=True),
        },
    )

    plan = await _make_manager(AsyncMock(), registry).calculate_transition_plan(vision.key)

    assert plan.action_type == "HARD_SWAP"
    assert plan.total_metabolic_cost == 2.0
    assert plan.evict_coven_ids == ["coding", "titan"]
    assert plan.launch_coven_ids == ["vision"]


@pytest.mark.asyncio
async def test_calculate_transition_plan_returns_soft_swap_for_warm_dynamic_runtime() -> None:
    active = _spec(key="router:chat:router-main", animator_name="router", lifecycle_mode="dynamic_soft")
    target = _spec(
        key="router:vision:router-vision",
        animator_name="router",
        family=CapabilityFamily.VISION,
        lifecycle_mode="dynamic_soft",
    )
    registry = StubRegistry(
        [active, target],
        [
            _state(active, is_static=False, is_active=True, warm=True),
            _state(target, is_static=False, is_active=False, warm=False),
        ],
        {"router": _runtime("router", up=True)},
    )

    plan = await _make_manager(AsyncMock(), registry).calculate_transition_plan(target.key)

    assert plan.action_type == "SOFT_SWAP"
    assert plan.evict_coven_ids == []
    assert plan.launch_coven_ids == []


@pytest.mark.asyncio
async def test_handle_transition_starts_runtime_then_loads_dynamic_capability() -> None:
    target = _spec(
        key="router:chat:router-main",
        animator_name="router",
        lifecycle_mode="dynamic_soft",
    )
    state = _state(target, is_static=False, is_active=False, warm=False)
    runtime = _runtime("router", up=False)
    registry = StubRegistry([target], [state], {"router": runtime})
    broker = AsyncMock()
    broker.get_active_worker_count.return_value = 0
    manager = _make_manager(broker, registry)

    process = AsyncMock()
    process.wait.return_value = None
    process.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=process) as mock_exec:
        await manager.handle_transition(
            HardwareTransitionRequired(target.key, target.animator_name), signal_priority=100.0
        )

    broker.pause_queues.assert_called_once()
    broker.broadcast_soft_stop.assert_called_once()
    broker.unpause_queues.assert_called_once()
    mock_exec.assert_called_once_with("systemctl", "--user", "start", "lychd-router.service")
    assert state.is_active is True
    assert registry.await_warm_calls == [target.key]  # terminal convergence (DYNAMIC)


@pytest.mark.asyncio
async def test_handle_transition_converges_via_await_warm_for_static_capability() -> None:
    target = _spec(key="titan:chat:titan-70b", animator_name="titan", lifecycle_mode="static")
    state = _state(target, is_static=True, is_active=False, warm=False)
    runtime = _runtime("titan", up=False)
    registry = StubRegistry([target], [state], {"titan": runtime})
    broker = AsyncMock()
    broker.get_active_worker_count.return_value = 0
    manager = _make_manager(broker, registry)

    process = AsyncMock()
    process.wait.return_value = None
    process.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=process):
        await manager.handle_transition(
            HardwareTransitionRequired(target.key, target.animator_name), signal_priority=100.0
        )

    # STATIC lifecycle: no in-runtime activation, but convergence still awaits WARM.
    assert registry.await_warm_calls == [target.key]


# ---------------------------------------------------------------------------
# O4: lease-drain honesty + the hard-swap priority gate + arbiter serialization
# ---------------------------------------------------------------------------

import asyncio  # noqa: E402
from datetime import UTC, datetime  # noqa: E402

from lychd.domain.animation.capabilities import GrantLease  # noqa: E402
from lychd.domain.orchestration.arbiter import TransitionDeclined  # noqa: E402
from lychd.domain.orchestration.policies import SwitchDecision  # noqa: E402


class _FixedPolicy:
    """A test policy that always returns a fixed evict set (independent of lease truth)."""

    name = "fixed"

    def __init__(self, evict: list[str]) -> None:
        self._evict = evict

    def solve(self, target: CapabilitySpec, view: object, leases: object) -> SwitchDecision:
        _ = (view, leases)
        return SwitchDecision(
            evict_animator_names=list(self._evict),
            launch_animator_names=[target.animator_name],
            metabolic_cost=float(len(self._evict)),
        )


def _acquire(leases: LeaseLedger, spec: CapabilitySpec, *, grant_id: str) -> None:
    grant = SimpleNamespace(lease=GrantLease(grant_id=grant_id, holder="run:x", issued_at=datetime.now(UTC)), spec=spec)
    leases.acquire(grant, priority=50)  # type: ignore[arg-type]


def _swap_manager(*, policy: object, leases: LeaseLedger, switching: SwitchingSettings) -> tuple[Any, Any]:
    target = _spec(key="vision:vision:vision-8b", animator_name="vision", family=CapabilityFamily.VISION)
    evictee = _spec(key="titan:chat:titan-70b", animator_name="titan")
    registry = StubRegistry(
        [target, evictee],
        [_state(target), _state(evictee, is_active=True, warm=True)],
        {"vision": _runtime("vision", up=False), "titan": _runtime("titan", up=True)},
    )
    manager = OrchestratorManager(
        AsyncMock(),
        registry=registry,  # type: ignore[arg-type]
        leases=leases,
        policy=policy,  # type: ignore[arg-type]
        arbiter=TransitionArbiter(),
        switching=switching,
    )
    return manager, target


@pytest.mark.asyncio
async def test_hard_swap_waits_for_lease_drain_then_completes() -> None:
    """A HARD_SWAP whose evictee is leased blocks until the lease releases, then completes."""
    leases = LeaseLedger()
    manager, target = _swap_manager(
        policy=_FixedPolicy(["titan"]), leases=leases, switching=SwitchingSettings(drain_timeout_s=5.0)
    )
    titan_spec = _spec(key="titan:chat:titan-70b", animator_name="titan")
    _acquire(leases, titan_spec, grant_id="held")

    process = AsyncMock()
    process.wait.return_value = None
    process.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=process):
        task = asyncio.create_task(manager.request_transition(target.key, 100.0))
        await asyncio.sleep(0.01)
        assert not task.done()  # blocked on the live lease drain
        leases.release("held")  # drain wakes
        plan = await task

    assert plan.action_type == "HARD_SWAP"


@pytest.mark.asyncio
async def test_hard_swap_drain_timeout_raises_naming_animators() -> None:
    """A never-released lease on an evictee makes the drain time out loudly, naming it."""
    leases = LeaseLedger()
    manager, target = _swap_manager(
        policy=_FixedPolicy(["titan"]), leases=leases, switching=SwitchingSettings(drain_timeout_s=0.05)
    )
    _acquire(leases, _spec(key="titan:chat:titan-70b", animator_name="titan"), grant_id="stuck")

    with pytest.raises(RuntimeError, match=r"Lease drain timed out on: \['titan'\]"):
        await manager.request_transition(target.key, 100.0)


@pytest.mark.asyncio
async def test_hard_swap_below_gate_is_declined() -> None:
    """priority 25 < min_priority_for_hard_swap → TransitionDeclined (no physical action)."""
    manager, target = _swap_manager(
        policy=_FixedPolicy([]), leases=LeaseLedger(), switching=SwitchingSettings(min_priority_for_hard_swap=40)
    )
    with pytest.raises(TransitionDeclined) as exc_info:
        await manager.request_transition(target.key, 25.0)
    assert exc_info.value.threshold == 40
    assert exc_info.value.priority == 25.0
    assert exc_info.value.plan.action_type == "HARD_SWAP"


@pytest.mark.asyncio
async def test_hard_swap_above_gate_proceeds() -> None:
    """priority 70 >= gate → the HARD_SWAP executes."""
    manager, target = _swap_manager(
        policy=_FixedPolicy([]), leases=LeaseLedger(), switching=SwitchingSettings(min_priority_for_hard_swap=40)
    )
    process = AsyncMock()
    process.wait.return_value = None
    process.returncode = 0
    with patch("asyncio.create_subprocess_exec", return_value=process):
        plan = await manager.request_transition(target.key, 70.0)
    assert plan.action_type == "HARD_SWAP"


@pytest.mark.asyncio
async def test_soft_swap_and_no_op_are_never_gated() -> None:
    """SOFT_SWAP / NO_OP return before the gate — even at a priority below the threshold."""
    # NO_OP: a warm target.
    warm = _spec(key="titan:chat:titan-70b", animator_name="titan")
    warm_reg = StubRegistry([warm], [_state(warm, is_active=True, warm=True)], {"titan": _runtime("titan", up=True)})
    warm_mgr = OrchestratorManager(
        AsyncMock(),
        registry=warm_reg,  # type: ignore[arg-type]
        leases=LeaseLedger(),
        policy=EvictIdlePolicy(),
        arbiter=TransitionArbiter(),
        switching=SwitchingSettings(min_priority_for_hard_swap=90),
    )
    no_op = await warm_mgr.request_transition(warm.key, 1.0)
    assert no_op.action_type == "NO_OP"

    # SOFT_SWAP: a dynamic target whose animator is already warm.
    active = _spec(key="router:chat:router-main", animator_name="router", lifecycle_mode="dynamic_soft")
    target = _spec(
        key="router:vision:router-vision",
        animator_name="router",
        family=CapabilityFamily.VISION,
        lifecycle_mode="dynamic_soft",
    )
    soft_reg = StubRegistry(
        [active, target],
        [_state(active, is_static=False, is_active=True, warm=True), _state(target, is_static=False)],
        {"router": _runtime("router", up=True)},
    )
    soft_mgr = OrchestratorManager(
        AsyncMock(),
        registry=soft_reg,  # type: ignore[arg-type]
        leases=LeaseLedger(),
        policy=EvictIdlePolicy(),
        arbiter=TransitionArbiter(),
        switching=SwitchingSettings(min_priority_for_hard_swap=90),
    )
    soft = await soft_mgr.request_transition(target.key, 1.0)
    assert soft.action_type == "SOFT_SWAP"


@pytest.mark.asyncio
async def test_requesting_run_not_counted_empty_ledger_drains_immediately() -> None:
    """A parked requester holds no lease: an empty ledger drains at once (no self-block)."""
    leases = LeaseLedger()
    manager, target = _swap_manager(
        policy=_FixedPolicy(["titan"]), leases=leases, switching=SwitchingSettings(drain_timeout_s=0.05)
    )
    process = AsyncMock()
    process.wait.return_value = None
    process.returncode = 0
    with patch("asyncio.create_subprocess_exec", return_value=process):
        plan = await manager.request_transition(target.key, 100.0)
    assert plan.action_type == "HARD_SWAP"  # no lease held → no wait, no timeout


# ---------------------------------------------------------------------------
# F1 (P1): the claim gate MUST reopen on drain-timeout AND cancellation, or every
# future perform_run wedges at intake. QuiescentBroker.pause_queues is a no-op, so
# these use a broker fake that records the gate state.
# ---------------------------------------------------------------------------


class _RecordingBroker:
    """A broker fake that records claim-gate state (QuiescentBroker's is a no-op)."""

    def __init__(self) -> None:
        self.paused = False
        self.soft_stop_calls = 0

    async def pause_queues(self) -> None:
        self.paused = True

    async def broadcast_soft_stop(self) -> None:
        self.soft_stop_calls += 1

    async def unpause_queues(self) -> None:
        self.paused = False

    async def get_active_worker_count(self) -> int:
        return 0


def _swap_manager_with_broker(broker: object, *, leases: LeaseLedger, switching: SwitchingSettings) -> tuple[Any, Any]:
    target = _spec(key="vision:vision:vision-8b", animator_name="vision", family=CapabilityFamily.VISION)
    evictee = _spec(key="titan:chat:titan-70b", animator_name="titan")
    registry = StubRegistry(
        [target, evictee],
        [_state(target), _state(evictee, is_active=True, warm=True)],
        {"vision": _runtime("vision", up=False), "titan": _runtime("titan", up=True)},
    )
    manager = OrchestratorManager(
        broker,
        registry=registry,  # type: ignore[arg-type]
        leases=leases,
        policy=_FixedPolicy(["titan"]),
        arbiter=TransitionArbiter(),
        switching=switching,
    )
    return manager, target


@pytest.mark.asyncio
async def test_drain_timeout_reopens_claim_gate() -> None:
    """A drain that times out fails the run loudly but leaves the queues UNPAUSED (F1)."""
    leases = LeaseLedger()
    broker = _RecordingBroker()
    manager, target = _swap_manager_with_broker(
        broker, leases=leases, switching=SwitchingSettings(drain_timeout_s=0.05)
    )
    _acquire(leases, _spec(key="titan:chat:titan-70b", animator_name="titan"), grant_id="stuck")

    with pytest.raises(RuntimeError, match="Lease drain timed out"):
        await manager.request_transition(target.key, 100.0)

    assert broker.soft_stop_calls == 1  # we did pass the pause and enter the drain
    assert broker.paused is False  # gate reopened on the timeout path


@pytest.mark.asyncio
async def test_cancel_mid_drain_reopens_claim_gate() -> None:
    """Cancellation during the (up-to-120s) drain wait still leaves the queues UNPAUSED (F1)."""
    leases = LeaseLedger()
    broker = _RecordingBroker()
    manager, target = _swap_manager_with_broker(broker, leases=leases, switching=SwitchingSettings(drain_timeout_s=5.0))
    _acquire(leases, _spec(key="titan:chat:titan-70b", animator_name="titan"), grant_id="held")  # never released

    task = asyncio.create_task(manager.request_transition(target.key, 100.0))
    await asyncio.sleep(0.02)  # let it pause + park on the live lease drain
    assert broker.paused is True  # gate closed while draining

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert broker.paused is False  # gate reopened on the cancellation path
