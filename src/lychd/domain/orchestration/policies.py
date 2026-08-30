"""Switch policies over registry truth and the compiled conflict topology."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from lychd.domain.animation.conflicts import build_conflict_topology

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState
    from lychd.domain.animation.schemas.runes.animators import SoulstoneConfig

__all__ = [
    "DeclaredConflictPolicy",
    "SwitchDecision",
    "SwitchPolicy",
    "resolve_switch_policy",
]


@runtime_checkable
class _RegistryView(Protocol):
    """Read-only registry slice a policy may see."""

    def list_capabilities(self) -> list[CapabilitySpec]: ...

    def get_capability_state(self, key: str, /) -> CapabilityState | None: ...

    def get_soulstone_rune(self, name: str, /) -> SoulstoneConfig | None: ...


@dataclass(frozen=True, slots=True)
class SwitchDecision:
    """Animator-level transition chosen by a switch policy."""

    evict_animator_names: list[str]
    launch_animator_names: list[str]
    metabolic_cost: float


class SwitchPolicy(Protocol):
    """Eviction solver contract."""

    name: str

    def solve(self, target: CapabilitySpec, view: _RegistryView) -> SwitchDecision: ...


class DeclaredConflictPolicy:
    """Evict only active exact neighbors from the declared conflict graph."""

    name = "declared-conflicts"

    def solve(self, target: CapabilitySpec, view: _RegistryView) -> SwitchDecision:
        """Select the active conflict neighbors of the requested Animator."""
        runes: dict[str, SoulstoneConfig] = {}
        active_animators: set[str] = set()
        for spec in view.list_capabilities():
            rune = view.get_soulstone_rune(spec.animator_name)
            if rune is None:
                continue
            runes.setdefault(spec.animator_name, rune)
            state = view.get_capability_state(spec.key)
            if state is not None and state.runtime_started:
                active_animators.add(spec.animator_name)

        if target.animator_name in active_animators:
            return SwitchDecision(evict_animator_names=[], launch_animator_names=[], metabolic_cost=0.0)

        topology = build_conflict_topology(runes.values())
        evictees = sorted(active_animators.intersection(topology.neighbors_for(target.animator_name)))
        return SwitchDecision(
            evict_animator_names=evictees,
            launch_animator_names=[target.animator_name],
            metabolic_cost=float(len(evictees)),
        )


def resolve_switch_policy(name: str) -> SwitchPolicy:
    """Resolve the canonical policy and its retained compatibility spelling."""
    if name in {"declared-conflicts", "evict-idle"}:
        return DeclaredConflictPolicy()
    msg = f"Unknown switch policy '{name}'. Expected declared-conflicts or evict-idle."
    raise ValueError(msg)
