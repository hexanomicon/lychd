from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState
from lychd.domain.animation.links import Link
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.orchestration.manager import OrchestratorManager


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

    def refresh_capability_state(self, key: str) -> CapabilityState | None:
        return self._states.get(key)

    def list_capability_states_for_animator(self, name: str) -> list[CapabilityState]:
        return [state for key, state in self._states.items() if self._specs[key].animator_name == name]

    def refresh_capability_states_for_animator(self, name: str) -> list[CapabilityState]:
        return self.list_capability_states_for_animator(name)

    def get_runtime(self, name: str) -> StubRuntime | None:
        return self._runtimes.get(name)

    def get_soulstone_rune(self, name: str) -> SimpleNamespace | None:
        return SimpleNamespace(service_name=f"lychd-{name}")

    def activate_capability(self, key: str) -> bool:
        return key in self._states


def _spec(
    *,
    key: str,
    animator_name: str,
    matrix_sets: list[str],
    evict_cost: int,
    family: CapabilityFamily = CapabilityFamily.CHAT,
) -> CapabilitySpec:
    return CapabilitySpec(
        key=key,
        animator_name=animator_name,
        runtime="llamacpp",
        source_kind="soulstone",
        family=family,
        model_id=key.rsplit(":", maxsplit=1)[-1],
        concurrency=ConcurrencyIntent(matrix_sets=matrix_sets, evict_cost=evict_cost),
    )


def _state(spec: CapabilitySpec, *, is_active: bool) -> CapabilityState:
    return CapabilityState(
        capability_key=spec.key,
        is_static=True,
        is_active=is_active,
        is_available=True,
        warm=is_active,
        health="ok" if is_active else "down",
        active_model_id=spec.model_id if is_active else None,
        loaded_model_ids=[spec.model_id] if is_active else [],
    )


@pytest.mark.asyncio
async def test_matrix_solver_lowest_cost_path() -> None:
    titan = _spec(key="titan:chat:titan-70b", animator_name="titan", matrix_sets=["titan_set"], evict_cost=100)
    coding = _spec(key="coding:chat:coding-8b", animator_name="coding", matrix_sets=["lite_set", "coding_set"], evict_cost=10)
    vision = _spec(
        key="vision:vision:vision-8b",
        animator_name="vision",
        matrix_sets=["lite_set", "vision_set"],
        evict_cost=10,
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

    plan = await OrchestratorManager(AsyncMock(), registry=registry).calculate_transition_plan(vision.key)

    assert plan.total_metabolic_cost == 100.0
    assert plan.evict_coven_ids == ["titan"]
    assert plan.launch_coven_ids == ["vision"]


@pytest.mark.asyncio
async def test_matrix_solver_no_eviction_required() -> None:
    coding = _spec(key="coding:chat:coding-8b", animator_name="coding", matrix_sets=["lite_set"], evict_cost=10)
    vision = _spec(
        key="vision:vision:vision-8b",
        animator_name="vision",
        matrix_sets=["lite_set"],
        evict_cost=10,
        family=CapabilityFamily.VISION,
    )
    registry = StubRegistry(
        [coding, vision],
        [
            _state(coding, is_active=True),
            _state(vision, is_active=False),
        ],
    )

    plan = await OrchestratorManager(AsyncMock(), registry=registry).calculate_transition_plan(vision.key)

    assert plan.total_metabolic_cost == 0.0
    assert plan.evict_coven_ids == []
    assert plan.launch_coven_ids == ["vision"]
