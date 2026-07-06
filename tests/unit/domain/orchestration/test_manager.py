from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

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
from lychd.domain.orchestration.manager import OrchestratorManager


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

    def list_capabilities(self) -> list[CapabilitySpec]:
        return list(self._specs.values())

    def get_capability(self, key: str) -> CapabilitySpec | None:
        return self._specs.get(key)

    def get_capability_state(self, key: str) -> CapabilityState | None:
        return self._states.get(key)

    def refresh_capability_state(self, key: str) -> CapabilityState | None:
        return self._states.get(key)

    def list_capability_states_for_animator(self, name: str) -> list[CapabilityState]:
        return [state for key, state in self._states.items() if self._specs[key].animator_name == name]

    def refresh_capability_states_for_animator(self, name: str) -> list[CapabilityState]:
        states = self.list_capability_states_for_animator(name)
        runtime = self._runtimes[name]
        for state in states:
            state.health = "ok" if runtime.connector.link.up else "down"
            if not runtime.connector.link.up:
                state.warm = False
                state.is_active = False
        return states

    def get_runtime(self, name: str) -> StubRuntime | None:
        return self._runtimes.get(name)

    def get_soulstone_rune(self, name: str) -> SimpleNamespace | None:
        if name not in self._runtimes:
            return None
        return SimpleNamespace(service_name=f"lychd-{name}")

    def activate_capability(self, key: str) -> ActivationResult:
        spec = self._specs[key]
        runtime = self._runtimes[spec.animator_name]
        runtime.connector.link.up = True
        state = self._states[key]
        state.health = "ok"
        state.phase = CapabilityPhase.WARM
        state.active_model_id = spec.model_id
        state.loaded_model_ids = [spec.model_id]
        return ActivationResult(accepted=True, phase=CapabilityPhase.WARM)


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

    plan = await OrchestratorManager(AsyncMock(), registry=registry).calculate_transition_plan(vision.key)

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

    plan = await OrchestratorManager(AsyncMock(), registry=registry).calculate_transition_plan(target.key)

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
    manager = OrchestratorManager(broker, registry=registry)

    process = AsyncMock()
    process.wait.return_value = None
    process.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=process) as mock_exec:
        await manager.handle_transition(HardwareTransitionRequired(target, state, runtime), signal_priority=100.0)

    broker.pause_queues.assert_called_once()
    broker.broadcast_soft_stop.assert_called_once()
    broker.unpause_queues.assert_called_once()
    mock_exec.assert_called_once_with("systemctl", "--user", "start", "lychd-router.service")
    assert state.is_active is True
