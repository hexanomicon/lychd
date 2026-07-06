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
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.orchestration.manager import OrchestratorManager


@dataclass
class StubRuntime:
    id: str
    base_url: str
    connector: SimpleNamespace


class StubRegistry:
    def __init__(self, spec: CapabilitySpec, state: CapabilityState, runtime: StubRuntime) -> None:
        self._spec = spec
        self._state = state
        self._runtime = runtime

    def list_capabilities(self) -> list[CapabilitySpec]:
        return [self._spec]

    def get_capability(self, key: str) -> CapabilitySpec | None:
        return self._spec if key == self._spec.key else None

    def get_capability_state(self, key: str) -> CapabilityState | None:
        return self._state if key == self._spec.key else None

    async def refresh_capability_state(self, key: str) -> CapabilityState | None:
        return self.get_capability_state(key)

    def list_capability_states_for_animator(self, _name: str) -> list[CapabilityState]:
        return [self._state]

    async def refresh_capability_states_for_animator(self, _name: str) -> list[CapabilityState]:
        self._state.health = "ok" if self._runtime.connector.link.up else "down"
        return [self._state]

    def get_runtime(self, _name: str) -> StubRuntime:
        return self._runtime

    def get_soulstone_rune(self, _name: str) -> SimpleNamespace:
        return SimpleNamespace(service_name="lychd-router", concurrency=ConcurrencyIntent())

    async def activate_capability(self, key: str) -> ActivationResult:
        if key != self._spec.key:
            return ActivationResult(accepted=False, phase=CapabilityPhase.UNKNOWN, reason="unknown capability")
        self._runtime.connector.link.up = True
        self._state.health = "ok"
        self._state.phase = CapabilityPhase.WARM
        self._state.active_model_id = self._spec.model_id
        self._state.loaded_model_ids = [self._spec.model_id]
        return ActivationResult(accepted=True, phase=CapabilityPhase.WARM)

    async def await_warm(self, key: str, *, timeout_s: float = 120.0, interval_s: float = 0.75) -> CapabilityState:
        _ = (key, timeout_s, interval_s)
        return self._state


def _dynamic_spec() -> CapabilitySpec:
    return CapabilitySpec(
        key="router:chat:router-main",
        animator_name="router",
        runtime="llamacpp",
        source_kind="soulstone",
        family=CapabilityFamily.CHAT,
        model_id="router-main",
        lifecycle=CapabilityLifecycle.DYNAMIC,
    )


@pytest.mark.asyncio
async def test_orchestrator_hard_swap_then_dynamic_activation() -> None:
    spec = _dynamic_spec()
    state = CapabilityState(
        capability_key=spec.key,
        lifecycle=CapabilityLifecycle.DYNAMIC,
        phase=CapabilityPhase.COLD,
        health="down",
    )
    runtime = StubRuntime(
        id="router",
        base_url="http://localhost:8080/v1",
        connector=SimpleNamespace(link=Link(up=False, activatable=True)),
    )
    registry = StubRegistry(spec, state, runtime)
    broker = AsyncMock()
    broker.get_active_worker_count.return_value = 0
    manager = OrchestratorManager(worker_broker=broker, registry=registry, leases=LeaseLedger())

    process = AsyncMock()
    process.wait.return_value = None
    process.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=process) as mock_exec:
        await manager.handle_transition(HardwareTransitionRequired(spec.key, spec.animator_name), signal_priority=200.0)

    broker.pause_queues.assert_called_once()
    broker.broadcast_soft_stop.assert_called_once()
    broker.unpause_queues.assert_called_once()
    mock_exec.assert_called_once_with("systemctl", "--user", "start", "lychd-router.service")
    assert state.is_active is True


@pytest.mark.asyncio
async def test_orchestrator_soft_swap_only_when_runtime_is_already_warm() -> None:
    spec = _dynamic_spec()
    state = CapabilityState(
        capability_key=spec.key,
        lifecycle=CapabilityLifecycle.DYNAMIC,
        phase=CapabilityPhase.COLD,
        health="ok",
    )
    runtime = StubRuntime(
        id="router",
        base_url="http://localhost:8080/v1",
        connector=SimpleNamespace(link=Link(up=True, activatable=True)),
    )
    active_peer = CapabilityState(
        capability_key="router:vision:router-vision",
        lifecycle=CapabilityLifecycle.DYNAMIC,
        phase=CapabilityPhase.WARM,
        health="ok",
    )

    class WarmRegistry(StubRegistry):
        def list_capability_states_for_animator(self, _name: str) -> list[CapabilityState]:
            return [state, active_peer]

    registry = WarmRegistry(spec, state, runtime)
    broker = AsyncMock()
    manager = OrchestratorManager(worker_broker=broker, registry=registry, leases=LeaseLedger())

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        await manager.handle_transition(HardwareTransitionRequired(spec.key, spec.animator_name), signal_priority=200.0)

    broker.pause_queues.assert_not_called()
    broker.broadcast_soft_stop.assert_not_called()
    broker.unpause_queues.assert_not_called()
    mock_exec.assert_not_called()
    assert state.is_active is True
