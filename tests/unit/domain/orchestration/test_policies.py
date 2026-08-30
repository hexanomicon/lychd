"""Switch-policy behavior over registry truth."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from lychd.domain.animation.capabilities import (
    CapabilityPhase,
    CapabilitySpec,
    CapabilityState,
    SourceKind,
)
from lychd.domain.animation.schemas.capability_family import CapabilityFamily
from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.orchestration.policies import (
    DeclaredConflictPolicy,
    resolve_switch_policy,
)


def _spec(
    *,
    animator: str,
    dedicated: bool = True,
    resident: bool = False,
    conflict_domains: list[str] | None = None,
) -> CapabilitySpec:
    return CapabilitySpec(
        key=f"{animator}:chat:{animator}-model",
        animator_name=animator,
        runtime="llamacpp",
        source_kind=SourceKind.SOULSTONE,
        family=CapabilityFamily.CHAT,
        model_id=f"{animator}-model",
        is_dynamic=False,
        concurrency=ConcurrencyIntent(
            dedicated=dedicated,
            persistent_resident=resident,
            conflict_domains=None if conflict_domains is None else tuple(conflict_domains),
        ),
    )


def _state(spec: CapabilitySpec, *, active: bool) -> CapabilityState:
    return CapabilityState(
        capability_key=spec.key,
        phase=CapabilityPhase.WARM if active else CapabilityPhase.COLD,
        health="ok" if active else "down",
    )


class _View:
    def __init__(self, specs: list[CapabilitySpec], states: dict[str, CapabilityState]) -> None:
        self._specs = specs
        self._states = states

    def list_capabilities(self) -> list[CapabilitySpec]:
        return self._specs

    def get_capability_state(self, key: str) -> CapabilityState | None:
        return self._states.get(key)

    def get_soulstone_rune(self, name: str) -> Any:
        spec = next(s for s in self._specs if s.animator_name == name)
        return SimpleNamespace(name=name, groups=[], concurrency=spec.concurrency)


def test_evict_idle_evicts_dedicated_active_unleased_keeps_resident() -> None:
    titan = _spec(animator="titan")
    coding = _spec(animator="coding")
    resident = _spec(animator="embedder", dedicated=False, resident=True)
    vision = _spec(animator="vision")
    specs = [titan, coding, resident, vision]
    states = {
        titan.key: _state(titan, active=True),
        coding.key: _state(coding, active=True),
        resident.key: _state(resident, active=True),
        vision.key: _state(vision, active=False),
    }
    decision = DeclaredConflictPolicy().solve(vision, _View(specs, states))

    assert decision.evict_animator_names == ["coding", "titan"]
    assert decision.launch_animator_names == ["vision"]
    assert decision.metabolic_cost == 2.0


def test_declared_conflicts_evicts_only_active_exact_neighbors() -> None:
    target = _spec(animator="vision", conflict_domains=["gpu-0"])
    neighbor = _spec(animator="reasoner", conflict_domains=["gpu-0"])
    coexistent = _spec(animator="speech", conflict_domains=["gpu-1"])
    explicit_coexistent = _spec(animator="embedder", conflict_domains=[])
    specs = [target, neighbor, coexistent, explicit_coexistent]
    states = {
        target.key: _state(target, active=False),
        neighbor.key: _state(neighbor, active=True),
        coexistent.key: _state(coexistent, active=True),
        explicit_coexistent.key: _state(explicit_coexistent, active=True),
    }

    decision = DeclaredConflictPolicy().solve(target, _View(specs, states))
    assert decision.evict_animator_names == ["reasoner"]
    assert decision.launch_animator_names == ["vision"]
    assert decision.metabolic_cost == 1.0


def test_omitted_legacy_target_conflicts_with_every_nonempty_explicit_domain() -> None:
    target = _spec(animator="legacy")
    gpu_zero = _spec(animator="gpu-zero", conflict_domains=["gpu-0"])
    gpu_one = _spec(animator="gpu-one", conflict_domains=["gpu-1"])
    coexistent = _spec(animator="coexistent", conflict_domains=[])
    specs = [target, gpu_zero, gpu_one, coexistent]
    states = {
        target.key: _state(target, active=False),
        gpu_zero.key: _state(gpu_zero, active=True),
        gpu_one.key: _state(gpu_one, active=True),
        coexistent.key: _state(coexistent, active=True),
    }

    decision = DeclaredConflictPolicy().solve(target, _View(specs, states))

    assert decision.evict_animator_names == ["gpu-one", "gpu-zero"]
    assert decision.launch_animator_names == ["legacy"]


def test_evict_idle_no_op_when_target_animator_already_active() -> None:
    router = _spec(animator="router")
    specs = [router]
    states = {router.key: _state(router, active=True)}

    decision = DeclaredConflictPolicy().solve(router, _View(specs, states))

    assert decision.evict_animator_names == []
    assert decision.launch_animator_names == []
    assert decision.metabolic_cost == 0.0


@pytest.mark.parametrize("name", ["declared-conflicts", "evict-idle"])
def test_resolve_switch_policy_retains_accepted_names(name: str) -> None:
    assert isinstance(resolve_switch_policy(name), DeclaredConflictPolicy)


def test_resolve_switch_policy_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="declared-conflicts"):
        resolve_switch_policy("no-such-policy")
