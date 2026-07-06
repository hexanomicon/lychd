from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock

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
from lychd.domain.cortex.leases import LeaseLedger
from lychd.domain.orchestration.arbiter import TransitionArbiter
from lychd.domain.orchestration.manager import OrchestratorManager
from lychd.domain.orchestration.policies import EvictIdlePolicy


def _make_manager(broker: object, registry: object) -> OrchestratorManager:
    return OrchestratorManager(
        broker,
        registry=registry,  # type: ignore[arg-type]
        leases=LeaseLedger(),
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
    def __init__(self, specs: list[CapabilitySpec], states: list[CapabilityState]) -> None:
        self._specs = {spec.key: spec for spec in specs}
        self._states = {state.capability_key: state for state in states}
        self._runtimes = {
            spec.animator_name: StubRuntime(
                id=spec.animator_name,
                base_url="http://localhost:8080/v1",
                connector=SimpleNamespace(link=Link(up=self._states[spec.key].warm, activatable=True)),
            )
            for spec in specs
        }

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
        return self.list_capability_states_for_animator(name)

    def get_runtime(self, name: str) -> StubRuntime | None:
        return self._runtimes.get(name)

    def get_soulstone_rune(self, name: str) -> SimpleNamespace | None:
        concurrency = next(
            (spec.concurrency for spec in self._specs.values() if spec.animator_name == name),
            ConcurrencyIntent(),
        )
        return SimpleNamespace(service_name=f"lychd-{name}", concurrency=concurrency)

    async def activate_capability(self, key: str) -> ActivationResult:
        phase = self._states[key].phase if key in self._states else CapabilityPhase.UNKNOWN
        return ActivationResult(accepted=key in self._states, phase=phase)


def _spec(
    *,
    key: str,
    animator_name: str,
    family: CapabilityFamily = CapabilityFamily.CHAT,
    dedicated: bool = True,
    persistent_resident: bool = False,
) -> CapabilitySpec:
    return CapabilitySpec(
        key=key,
        animator_name=animator_name,
        runtime="llamacpp",
        source_kind="soulstone",
        family=family,
        model_id=key.rsplit(":", maxsplit=1)[-1],
        concurrency=ConcurrencyIntent(dedicated=dedicated, persistent_resident=persistent_resident),
    )


def _state(spec: CapabilitySpec, *, is_active: bool) -> CapabilityState:
    return CapabilityState(
        capability_key=spec.key,
        lifecycle=CapabilityLifecycle.STATIC,
        phase=CapabilityPhase.WARM if is_active else CapabilityPhase.COLD,
        health="ok" if is_active else "down",
        active_model_id=spec.model_id if is_active else None,
        loaded_model_ids=[spec.model_id] if is_active else [],
    )


@pytest.mark.asyncio
async def test_matrix_solver_evicts_all_active_dedicated_animators() -> None:
    titan = _spec(key="titan:chat:titan-70b", animator_name="titan")
    coding = _spec(key="coding:chat:coding-8b", animator_name="coding")
    vision = _spec(
        key="vision:vision:vision-8b",
        animator_name="vision",
        family=CapabilityFamily.VISION,
    )
    registry = StubRegistry(
        [titan, coding, vision],
        [
            _state(titan, is_active=True),
            _state(coding, is_active=True),
            _state(vision, is_active=False),
        ],
    )

    plan = await _make_manager(AsyncMock(), registry).calculate_transition_plan(vision.key)

    assert plan.total_metabolic_cost == 2.0
    assert plan.evict_coven_ids == ["coding", "titan"]
    assert plan.launch_coven_ids == ["vision"]


@pytest.mark.asyncio
async def test_matrix_solver_keeps_non_dedicated_persistent_resident() -> None:
    resident = _spec(
        key="embedder:embedding:embed-1",
        animator_name="embedder",
        family=CapabilityFamily.EMBEDDING,
        dedicated=False,
        persistent_resident=True,
    )
    vision = _spec(
        key="vision:vision:vision-8b",
        animator_name="vision",
        family=CapabilityFamily.VISION,
    )
    registry = StubRegistry(
        [resident, vision],
        [
            _state(resident, is_active=True),
            _state(vision, is_active=False),
        ],
    )

    plan = await _make_manager(AsyncMock(), registry).calculate_transition_plan(vision.key)

    assert plan.total_metabolic_cost == 0.0
    assert plan.evict_coven_ids == []
    assert plan.launch_coven_ids == ["vision"]
