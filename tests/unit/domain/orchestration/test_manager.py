from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from lychd.config.settings.orchestration import SwitchingSettings
from lychd.domain.animation.capabilities import (
    ActivationResult,
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    SourceKind,
)
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas import GenericSoulstoneConfig
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.cortex.dispatcher import HardwareTransitionRequired
from lychd.domain.cortex.leases import AnimatorAdmission, LeaseLedger
from lychd.domain.orchestration.actuator import (
    RuntimeActuationRestoredError,
    RuntimeCancellationRestoredError,
    RuntimePreconditionError,
    TransitionIntent,
)
from lychd.domain.orchestration.arbiter import TransitionArbiter
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.policies import EvictIdlePolicy
from lychd.domain.orchestration.schema import TransitionTrace
from lychd.system.services.runtime import SystemdRuntimeActuator


def _make_manager(broker: object, registry: object, *, leases: LeaseLedger | None = None) -> OrchestratorManager:
    """Construct an OrchestratorManager with the default evict-idle policy + arbiter."""
    return OrchestratorManager(
        broker,
        registry=registry,  # type: ignore[arg-type]
        leases=leases or LeaseLedger(),
        policy=EvictIdlePolicy(),
        arbiter=TransitionArbiter(),
        actuator=SystemdRuntimeActuator(registry, systemctl_bin="/usr/bin/systemctl"),  # type: ignore[arg-type]
        switching=SwitchingSettings(),
    )


def test_transition_observer_failure_cannot_change_transition_control_flow() -> None:
    manager = _make_manager(SimpleNamespace(), StubRegistry([], [], {}))

    def _broken_observer(trace: TransitionTrace) -> None:
        raise RuntimeError

    trace = TransitionTrace(
        target_capability_key="chat:local",
        priority=50,
        observer=_broken_observer,
    )

    manager._publish(trace, "verifying")  # pyright: ignore[reportPrivateUsage]

    assert trace.phase == "verifying"
    assert manager.transitions.get(trace.request_id) is not None


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
        first_specs_by_animator: dict[str, CapabilitySpec] = {}
        for spec in specs:
            first_specs_by_animator.setdefault(spec.animator_name, spec)
        self._soulstones = {
            name: GenericSoulstoneConfig(
                name=name,
                image=f"example/{name}:test",
                runtime=spec.runtime,
                concurrency=spec.concurrency,
            )
            for name, spec in first_specs_by_animator.items()
        }
        self.await_warm_calls: list[str] = []
        self.activate_calls: list[str] = []

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

    def get_soulstone_rune(self, name: str) -> GenericSoulstoneConfig | None:
        return self._soulstones.get(name)

    def list_soulstone_runes(self) -> list[GenericSoulstoneConfig]:
        return [self._soulstones[name] for name in sorted(self._soulstones)]

    async def activate_capability(self, key: str) -> ActivationResult:
        self.activate_calls.append(key)
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
        source_kind=SourceKind.SOULSTONE,
        family=family,
        model_id=key.rsplit(":", maxsplit=1)[-1],
        is_dynamic=lifecycle_mode == "dynamic_soft",
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
        is_dynamic=not is_static,
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
async def test_calculate_transition_plan_refreshes_stale_peer_before_policy() -> None:
    target = _spec(
        key="vision:vision:vision-8b",
        animator_name="vision",
        family=CapabilityFamily.VISION,
    )
    resident = _spec(key="titan:chat:titan-70b", animator_name="titan")

    class _BootRaceRegistry(StubRegistry):
        async def refresh_capability_states_for_animator(self, name: str) -> list[CapabilityState]:
            states = self.list_capability_states_for_animator(name)
            if name == resident.animator_name:
                for state in states:
                    state.phase = CapabilityPhase.WARM
                    state.health = "ok"
                    state.active_model_id = resident.model_id
                    state.loaded_model_ids = [resident.model_id]
            return states

    registry = _BootRaceRegistry(
        [target, resident],
        [_state(target), _state(resident)],
        {
            target.animator_name: _runtime(target.animator_name, up=False),
            resident.animator_name: _runtime(resident.animator_name, up=True),
        },
    )

    plan = await _make_manager(AsyncMock(), registry).calculate_transition_plan(target.key)

    assert plan.action_type == "HARD_SWAP"
    assert plan.evict_coven_ids == [resident.animator_name]
    assert plan.launch_coven_ids == [target.animator_name]


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
async def test_request_transition_soft_activates_without_host_restart() -> None:
    target = _spec(
        key="router:chat:router-main",
        animator_name="router",
        lifecycle_mode="dynamic_soft",
    )
    state = _state(target, is_static=False, is_active=False, warm=False)
    state.phase = CapabilityPhase.ACTIVATABLE
    registry = StubRegistry([target], [state], {"router": _runtime("router", up=True)})
    manager = _make_manager(AsyncMock(), registry)

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        plan = await manager.request_transition(target.key, priority=100)

    assert plan.action_type == "SOFT_SWAP"
    mock_exec.assert_not_called()
    assert registry.activate_calls == [target.key]
    assert registry.await_warm_calls == [target.key]


@pytest.mark.asyncio
async def test_same_key_requests_coalesce_through_soft_activation() -> None:
    target = _spec(
        key="router:chat:router-main",
        animator_name="router",
        lifecycle_mode="dynamic_soft",
    )
    state = _state(target, is_static=False, is_active=False, warm=False)
    state.phase = CapabilityPhase.ACTIVATABLE

    class _BlockingActivationRegistry(StubRegistry):
        def __init__(self) -> None:
            super().__init__([target], [state], {"router": _runtime("router", up=True)})
            self.activation_entered = asyncio.Event()
            self.release_activation = asyncio.Event()

        async def activate_capability(self, key: str) -> ActivationResult:
            self.activation_entered.set()
            await self.release_activation.wait()
            return await super().activate_capability(key)

    registry = _BlockingActivationRegistry()
    manager = _make_manager(AsyncMock(), registry)
    owner = asyncio.create_task(manager.request_transition(target.key, priority=100))
    await registry.activation_entered.wait()
    follower = asyncio.create_task(manager.request_transition(target.key, priority=100))
    await asyncio.sleep(0)

    registry.release_activation.set()
    owner_plan, follower_plan = await asyncio.gather(owner, follower)

    assert owner_plan.action_type == "SOFT_SWAP"
    assert follower_plan.action_type in {"SOFT_SWAP", "NO_OP"}
    assert registry.activate_calls == [target.key]


@pytest.mark.asyncio
async def test_warming_dynamic_capability_waits_without_duplicate_activation() -> None:
    target = _spec(
        key="router:chat:router-main",
        animator_name="router",
        lifecycle_mode="dynamic_soft",
    )
    state = _state(target, is_static=False, is_active=True, warm=False)
    registry = StubRegistry([target], [state], {"router": _runtime("router", up=True)})
    manager = _make_manager(AsyncMock(), registry)

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        await manager.handle_transition(
            HardwareTransitionRequired(target.key, target.animator_name),
            signal_priority=100,
        )

    mock_exec.assert_not_called()
    assert registry.activate_calls == []
    assert registry.await_warm_calls == [target.key]


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
            HardwareTransitionRequired(target.key, target.animator_name), signal_priority=100
        )

    broker.pause_queues.assert_called_once()
    broker.broadcast_soft_stop.assert_called_once()
    broker.unpause_queues.assert_called_once()
    mock_exec.assert_called_once_with(
        "/usr/bin/systemctl",
        "--user",
        "start",
        "--job-mode=fail",
        "lychd-animator-router.target",
    )
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
            HardwareTransitionRequired(target.key, target.animator_name), signal_priority=100
        )

    # Non-dynamic capability: no in-runtime activation, but convergence still awaits WARM.
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


class _SwapRegistry(StubRegistry):
    """Registry fake paired with `_StateTrackingActuator` below."""

    def set_runtime_started(self, animator_name: str, *, started: bool) -> None:
        self._runtimes[animator_name].connector.link.up = started
        if started:
            return
        for state in self.list_capability_states_for_animator(animator_name):
            state.health = "down"
            state.phase = CapabilityPhase.COLD


class _StateTrackingActuator:
    """Manager-test actuator whose successful evictions become observable."""

    def __init__(self, registry: _SwapRegistry) -> None:
        self._registry = registry
        self.calls: list[TransitionIntent] = []

    async def apply(self, intent: TransitionIntent) -> None:
        self.calls.append(intent)
        for animator_name in intent.evict_animators:
            self._registry.set_runtime_started(animator_name, started=False)
        for animator_name in intent.launch_animators:
            self._registry.set_runtime_started(animator_name, started=True)


def _swap_manager(*, policy: object, leases: LeaseLedger, switching: SwitchingSettings) -> tuple[Any, Any]:
    target = _spec(key="vision:vision:vision-8b", animator_name="vision", family=CapabilityFamily.VISION)
    evictee = _spec(key="titan:chat:titan-70b", animator_name="titan")
    registry = _SwapRegistry(
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
        actuator=_StateTrackingActuator(registry),
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
        assert leases.admission("titan") is AnimatorAdmission.DRAINING
        assert leases.admission("vision") is AnimatorAdmission.DRAINING
        with pytest.raises(RuntimeError, match="is draining"):
            _acquire(leases, titan_spec, grant_id="late")
        leases.release("held")  # drain wakes
        plan = await task

    assert plan.action_type == "HARD_SWAP"
    assert leases.admission("titan") is AnimatorAdmission.OPEN
    assert leases.admission("vision") is AnimatorAdmission.OPEN


@pytest.mark.asyncio
async def test_hard_swap_drain_timeout_raises_naming_animators() -> None:
    """A never-released lease on an evictee makes the drain time out loudly, naming it."""
    leases = LeaseLedger()
    manager, target = _swap_manager(
        policy=_FixedPolicy(["titan"]), leases=leases, switching=SwitchingSettings(drain_timeout_s=0.05)
    )
    _acquire(leases, _spec(key="titan:chat:titan-70b", animator_name="titan"), grant_id="stuck")

    with pytest.raises(RuntimeError, match=r"Lease drain timed out on: \['titan', 'vision'\]"):
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
        actuator=SystemdRuntimeActuator(warm_reg, systemctl_bin="/usr/bin/systemctl"),  # type: ignore[arg-type]
        switching=SwitchingSettings(min_priority_for_hard_swap=90),
    )
    no_op = await warm_mgr.request_transition(warm.key, 1)
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
        actuator=SystemdRuntimeActuator(soft_reg, systemctl_bin="/usr/bin/systemctl"),  # type: ignore[arg-type]
        switching=SwitchingSettings(min_priority_for_hard_swap=90),
    )
    soft = await soft_mgr.request_transition(target.key, 1)
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
        self.paused_event = asyncio.Event()
        self.soft_stop_calls = 0

    async def pause_queues(self) -> None:
        self.paused = True
        self.paused_event.set()

    async def broadcast_soft_stop(self) -> None:
        self.soft_stop_calls += 1

    async def unpause_queues(self) -> None:
        self.paused = False
        self.paused_event.clear()

    async def get_active_worker_count(self) -> int:
        return 0


@pytest.mark.asyncio
async def test_static_warming_runtime_uses_convergence_only_path() -> None:
    """A started fixed runtime awaits readiness without an impossible relaunch."""
    target = _spec(key="titan:chat:titan-70b", animator_name="titan")
    state = _state(target, is_active=True, warm=False)
    registry = StubRegistry(
        [target],
        [state],
        {"titan": _runtime("titan", up=True)},
    )
    leases = LeaseLedger()
    broker = _RecordingBroker()
    manager = OrchestratorManager(
        broker,
        registry=registry,  # type: ignore[arg-type]
        leases=leases,
        policy=EvictIdlePolicy(),
        arbiter=TransitionArbiter(),
        actuator=SystemdRuntimeActuator(registry, systemctl_bin="/usr/bin/systemctl"),  # type: ignore[arg-type]
        switching=SwitchingSettings(),
    )
    wait_entered = asyncio.Event()
    release_wait = asyncio.Event()

    async def block_warm(
        key: str,
        *,
        timeout_s: float = 120.0,
        interval_s: float = 0.75,
    ) -> CapabilityState:
        _ = (timeout_s, interval_s)
        wait_entered.set()
        await release_wait.wait()
        warmed = registry.get_capability_state(key)
        assert warmed is not None
        warmed.phase = CapabilityPhase.WARM
        return warmed

    with (
        patch.object(registry, "await_warm", side_effect=block_warm),
        patch("asyncio.create_subprocess_exec") as subprocess,
    ):
        task = asyncio.create_task(manager.request_transition(target.key, 100))
        await wait_entered.wait()
        assert leases.admission("titan") is AnimatorAdmission.DRAINING
        subprocess.assert_not_called()
        release_wait.set()
        plan = await task

    assert plan.action_type == "SOFT_SWAP"
    assert registry.activate_calls == []
    assert leases.admission("titan") is AnimatorAdmission.OPEN


@pytest.mark.asyncio
async def test_soft_swap_drains_same_animator_leases_before_activation() -> None:
    """Loading model B cannot invalidate an in-flight grant for model A."""
    active = _spec(
        key="router:chat:model-a",
        animator_name="router",
        lifecycle_mode="dynamic_soft",
    )
    target = _spec(
        key="router:vision:model-b",
        animator_name="router",
        family=CapabilityFamily.VISION,
        lifecycle_mode="dynamic_soft",
    )
    target_state = _state(target, is_static=False)
    target_state.phase = CapabilityPhase.ACTIVATABLE
    registry = StubRegistry(
        [active, target],
        [_state(active, is_static=False, is_active=True, warm=True), target_state],
        {"router": _runtime("router", up=True)},
    )
    leases = LeaseLedger()
    _acquire(leases, active, grant_id="model-a-held")
    broker = _RecordingBroker()
    manager = OrchestratorManager(
        broker,
        registry=registry,  # type: ignore[arg-type]
        leases=leases,
        policy=EvictIdlePolicy(),
        arbiter=TransitionArbiter(),
        actuator=SystemdRuntimeActuator(registry, systemctl_bin="/usr/bin/systemctl"),  # type: ignore[arg-type]
        switching=SwitchingSettings(drain_timeout_s=5.0),
    )

    task = asyncio.create_task(manager.request_transition(target.key, 100))
    await broker.paused_event.wait()

    assert registry.activate_calls == []
    assert leases.admission("router") is AnimatorAdmission.DRAINING
    with pytest.raises(RuntimeError, match="is draining"):
        _acquire(leases, active, grant_id="late-model-a")

    leases.release("model-a-held")
    plan = await task

    assert plan.action_type == "SOFT_SWAP"
    assert registry.activate_calls == [target.key]
    assert leases.admission("router") is AnimatorAdmission.OPEN


def _swap_manager_with_broker(broker: object, *, leases: LeaseLedger, switching: SwitchingSettings) -> tuple[Any, Any]:
    target = _spec(key="vision:vision:vision-8b", animator_name="vision", family=CapabilityFamily.VISION)
    evictee = _spec(key="titan:chat:titan-70b", animator_name="titan")
    registry = _SwapRegistry(
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
        actuator=_StateTrackingActuator(registry),
        switching=switching,
    )
    return manager, target


@pytest.mark.asyncio
async def test_hard_swap_keeps_admission_closed_until_target_is_warm() -> None:
    """Durable intent publication is not completion; the barrier spans convergence."""
    leases = LeaseLedger()
    broker = _RecordingBroker()
    manager, target = _swap_manager_with_broker(
        broker,
        leases=leases,
        switching=SwitchingSettings(drain_timeout_s=5.0),
    )
    warm_wait_entered = asyncio.Event()
    release_warm_wait = asyncio.Event()

    async def block_warm(
        key: str,
        *,
        timeout_s: float = 120.0,
        interval_s: float = 0.75,
    ) -> CapabilityState:
        _ = (timeout_s, interval_s)
        warm_wait_entered.set()
        await release_warm_wait.wait()
        state = manager.registry.get_capability_state(key)
        assert state is not None
        state.phase = CapabilityPhase.WARM
        return state

    process = AsyncMock()
    process.wait.return_value = None
    process.returncode = 0
    with (
        patch.object(manager.registry, "await_warm", side_effect=block_warm),
        patch("asyncio.create_subprocess_exec", return_value=process),
    ):
        task = asyncio.create_task(manager.request_transition(target.key, 100.0))
        try:
            await asyncio.wait_for(warm_wait_entered.wait(), timeout=1.0)
            assert broker.paused is True
            assert leases.admission("titan") is AnimatorAdmission.DRAINING
            assert leases.admission("vision") is AnimatorAdmission.DRAINING
            release_warm_wait.set()
            await task
        finally:
            release_warm_wait.set()
            if not task.done():
                task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    assert broker.paused is False
    assert leases.admission("titan") is AnimatorAdmission.OPEN
    assert leases.admission("vision") is AnimatorAdmission.OPEN


@pytest.mark.asyncio
async def test_hard_swap_readiness_failure_runs_typed_compensation() -> None:
    """A physically applied swap is inverted before admission reopens."""
    leases = LeaseLedger()
    broker = _RecordingBroker()
    manager, target = _swap_manager_with_broker(
        broker,
        leases=leases,
        switching=SwitchingSettings(drain_timeout_s=5.0),
    )

    trace = TransitionTrace(
        target_capability_key=target.key,
        priority=100,
        run_id="run-1",
        occurrence_id="occurrence-1",
    )
    with (
        patch.object(manager.registry, "await_warm", side_effect=RuntimeError("warm failed")),
        pytest.raises(RuntimeError, match="warm failed"),
    ):
        await manager.request_transition(target.key, 100, trace=trace)

    actuator = manager._actuator
    assert isinstance(actuator, _StateTrackingActuator)
    assert [intent.operation for intent in actuator.calls] == ["forward", "compensation"]
    assert actuator.calls[1].rollback_of == actuator.calls[0].transition_id
    assert trace.physical_transition_id == actuator.calls[0].transition_id
    assert trace.compensation_transition_id == actuator.calls[1].transition_id
    assert trace.phase == "failed_restored"
    titan_runtime = manager.registry.get_runtime("titan")
    vision_runtime = manager.registry.get_runtime("vision")
    assert titan_runtime is not None
    assert titan_runtime.connector.link.up is True
    assert vision_runtime is not None
    assert vision_runtime.connector.link.up is False
    assert broker.paused is False
    assert leases.admission("titan") is AnimatorAdmission.OPEN
    assert leases.admission("vision") is AnimatorAdmission.OPEN


@pytest.mark.asyncio
async def test_failed_hard_swap_compensation_keeps_admission_closed() -> None:
    """An unknown half-restored world fails closed for operator recovery."""
    leases = LeaseLedger()
    broker = _RecordingBroker()
    manager, target = _swap_manager_with_broker(
        broker,
        leases=leases,
        switching=SwitchingSettings(drain_timeout_s=5.0),
    )
    successful_forward = manager._actuator
    assert isinstance(successful_forward, _StateTrackingActuator)

    class _FailingCompensation:
        async def apply(self, intent: TransitionIntent) -> None:
            if intent.operation == "compensation":
                message = "inverse failed"
                raise RuntimeError(message)
            await successful_forward.apply(intent)

    manager._actuator = _FailingCompensation()
    with (
        patch.object(manager.registry, "await_warm", side_effect=RuntimeError("warm failed")),
        pytest.raises(RuntimeError, match="admission remains closed"),
    ):
        await manager.request_transition(target.key, 100)

    assert broker.paused is True
    assert leases.admission("titan") is AnimatorAdmission.DRAINING
    assert leases.admission("vision") is AnimatorAdmission.DRAINING


@pytest.mark.asyncio
async def test_uncertain_actuator_failure_keeps_admission_closed() -> None:
    """A raising actuator cannot silently reopen into a partial physical swap."""
    leases = LeaseLedger()
    broker = _RecordingBroker()
    manager, target = _swap_manager_with_broker(
        broker,
        leases=leases,
        switching=SwitchingSettings(drain_timeout_s=5.0),
    )

    class _UncertainActuator:
        def __init__(self) -> None:
            self.calls = 0

        async def apply(self, intent: TransitionIntent) -> None:
            _ = intent
            self.calls += 1
            message = "effect outcome unknown"
            raise RuntimeError(message)

    uncertain = _UncertainActuator()
    manager._actuator = uncertain
    with pytest.raises(RuntimeError, match="outcome unknown"):
        await manager.request_transition(target.key, 100)

    assert broker.paused is True
    assert leases.admission("titan") is AnimatorAdmission.DRAINING
    assert leases.admission("vision") is AnimatorAdmission.DRAINING
    assert manager.containment_reason == "runtime actuator outcome is uncertain"

    with pytest.raises(RuntimeError, match="containment is active"):
        await manager.request_transition(target.key, 100)
    with pytest.raises(RuntimeError, match="containment is active"):
        await manager.request_transition("titan:chat:titan-70b", 100)
    assert uncertain.calls == 1


@pytest.mark.asyncio
async def test_safe_precondition_decline_reopens_barrier_without_containment() -> None:
    """A host stale-world decline is proven no-effect and remains retryable."""
    leases = LeaseLedger()
    broker = _RecordingBroker()
    manager, target = _swap_manager_with_broker(
        broker,
        leases=leases,
        switching=SwitchingSettings(drain_timeout_s=5.0),
    )

    class _DecliningActuator:
        async def apply(self, intent: TransitionIntent) -> None:
            _ = intent
            message = "host active set changed"
            raise RuntimePreconditionError(message)

    manager._actuator = _DecliningActuator()
    with pytest.raises(RuntimePreconditionError, match="active set changed"):
        await manager.request_transition(target.key, 100)

    assert manager.containment_reason is None
    assert broker.paused is False
    assert leases.admission("titan") is AnimatorAdmission.OPEN
    assert leases.admission("vision") is AnimatorAdmission.OPEN


@pytest.mark.asyncio
async def test_verified_actuator_restoration_reopens_barrier_without_containment() -> None:
    """A failed systemd transaction may reopen only after exact-world proof."""
    leases = LeaseLedger()
    broker = _RecordingBroker()
    manager, target = _swap_manager_with_broker(
        broker,
        leases=leases,
        switching=SwitchingSettings(drain_timeout_s=5.0),
    )

    class _RestoringActuator:
        async def apply(self, intent: TransitionIntent) -> None:
            _ = intent
            message = "systemd transaction failed; prior runtime world restored"
            raise RuntimeActuationRestoredError(message)

    manager._actuator = _RestoringActuator()
    with pytest.raises(RuntimeActuationRestoredError, match="prior runtime world restored"):
        await manager.request_transition(target.key, 100)

    assert manager.containment_reason is None
    assert broker.paused is False
    assert leases.admission("titan") is AnimatorAdmission.OPEN
    assert leases.admission("vision") is AnimatorAdmission.OPEN


@pytest.mark.asyncio
async def test_verified_cancellation_restoration_reopens_barrier_without_containment() -> None:
    """Preserve cancellation semantics after the actuator proves exact restoration."""
    leases = LeaseLedger()
    broker = _RecordingBroker()
    manager, target = _swap_manager_with_broker(
        broker,
        leases=leases,
        switching=SwitchingSettings(drain_timeout_s=5.0),
    )

    class _CancellationRestoringActuator:
        async def apply(self, intent: TransitionIntent) -> None:
            _ = intent
            message = "cancelled systemd transaction restored its prior runtime world"
            raise RuntimeCancellationRestoredError(message)

    manager._actuator = _CancellationRestoringActuator()
    with pytest.raises(RuntimeCancellationRestoredError, match="restored its prior runtime world"):
        await manager.request_transition(target.key, 100)

    assert manager.containment_reason is None
    assert broker.paused is False
    assert leases.admission("titan") is AnimatorAdmission.OPEN
    assert leases.admission("vision") is AnimatorAdmission.OPEN


@pytest.mark.asyncio
async def test_warm_request_does_not_noop_while_animator_is_draining() -> None:
    """A warm pre-plan must queue behind the transition currently evicting it."""
    leases = LeaseLedger()
    broker = _RecordingBroker()
    manager, target = _swap_manager_with_broker(
        broker,
        leases=leases,
        switching=SwitchingSettings(drain_timeout_s=5.0),
    )
    titan = _spec(key="titan:chat:titan-70b", animator_name="titan")
    _acquire(leases, titan, grant_id="hold-drain")

    process = AsyncMock()
    process.wait.return_value = None
    process.returncode = 0
    with patch("asyncio.create_subprocess_exec", return_value=process):
        evicting = asyncio.create_task(manager.request_transition(target.key, 100.0))
        await broker.paused_event.wait()
        returning = asyncio.create_task(manager.request_transition(titan.key, 100.0))
        await asyncio.sleep(0)
        assert returning.done() is False

        returning.cancel()
        with pytest.raises(asyncio.CancelledError):
            await returning
        leases.release("hold-drain")
        await evicting


@pytest.mark.asyncio
async def test_noop_recheck_rejects_orphaned_closed_admission() -> None:
    """A warm cache cannot report success through a stranded drain gate."""
    target = _spec(key="titan:chat:titan-70b", animator_name="titan")
    registry = StubRegistry(
        [target],
        [_state(target, is_active=True, warm=True)],
        {"titan": _runtime("titan", up=True)},
    )
    leases = LeaseLedger()
    leases.begin_drain(["titan"])
    manager = OrchestratorManager(
        AsyncMock(),
        registry=registry,  # type: ignore[arg-type]
        leases=leases,
        policy=EvictIdlePolicy(),
        arbiter=TransitionArbiter(),
        actuator=SystemdRuntimeActuator(registry, systemctl_bin="/usr/bin/systemctl"),  # type: ignore[arg-type]
        switching=SwitchingSettings(),
    )

    with pytest.raises(RuntimeError, match="admission remains closed"):
        await manager.request_transition(target.key, 100)


@pytest.mark.asyncio
async def test_noop_fast_path_rechecks_containment_after_async_planning() -> None:
    """Containment latched during refresh cannot leak through a stale NO_OP."""
    target = _spec(key="titan:chat:titan-70b", animator_name="titan")
    registry = StubRegistry(
        [target],
        [_state(target, is_active=True, warm=True)],
        {"titan": _runtime("titan", up=True)},
    )
    manager = _make_manager(AsyncMock(), registry)
    original_calculate = manager.calculate_transition_plan
    planning = asyncio.Event()
    release = asyncio.Event()

    async def block_plan(key: str) -> Any:
        planning.set()
        await release.wait()
        return await original_calculate(key)

    with patch.object(manager, "calculate_transition_plan", side_effect=block_plan):
        task = asyncio.create_task(manager.request_transition(target.key, 100))
        await planning.wait()
        manager._contain("concurrent uncertain mutation")  # pyright: ignore[reportPrivateUsage]
        release.set()
        with pytest.raises(RuntimeError, match="containment is active"):
            await task


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
    assert leases.admission("titan") is AnimatorAdmission.OPEN


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
    assert leases.admission("titan") is AnimatorAdmission.OPEN


@pytest.mark.asyncio
async def test_preflight_failure_records_terminal_no_effect_phase() -> None:
    """A request rejected before arbitration never remains falsely `requested`."""
    manager = _make_manager(
        AsyncMock(),
        StubRegistry([], [], {}),
    )
    trace = TransitionTrace(target_capability_key="missing:chat", priority=100.0)

    with pytest.raises(ValueError, match="Unknown capability: missing:chat"):
        await manager.request_transition("missing:chat", 100, trace=trace)

    record = manager.transitions.get(trace.request_id)
    assert record is not None
    assert record.phase == "declined_no_effect"
    assert record.physical_transition_id is None
