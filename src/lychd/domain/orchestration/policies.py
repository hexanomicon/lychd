"""Switch policies over registry truth and the compiled conflict topology."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

from lychd.domain.animation.conflicts import build_conflict_topology

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState
    from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
    from lychd.domain.cortex.leases import LeaseLedger

__all__ = [
    "SWITCH_POLICIES",
    "AnimatorRecord",
    "DeclaredConflictPolicy",
    "EvictIdlePolicy",
    "RegistryView",
    "SwitchDecision",
    "SwitchPolicy",
    "animator_records",
    "resolve_switch_policy",
]


@runtime_checkable
class RegistryView(Protocol):
    """Read-only registry slice a policy may see."""

    def list_capabilities(self) -> list[CapabilitySpec]: ...

    def get_capability_state(self, key: str, /) -> CapabilityState | None: ...

    def get_soulstone_rune(self, name: str, /) -> Any | None: ...


@dataclass(frozen=True, slots=True)
class AnimatorRecord:
    """Animator-level projection the solver reasons over. Built from registry truth.

    Field-identical to the keel's ``_AnimatorRecord`` (extracted VERBATIM, O1).
    """

    name: str
    dedicated: bool  # rune.concurrency.dedicated
    persistent_resident: bool  # rune.concurrency.persistent_resident
    active: bool  # any capability reports its owning runtime unit started
    leased: bool  # LeaseLedger.active(animator_name=name) != []


@dataclass(frozen=True, slots=True)
class _ConflictProjection:
    """Registry declaration normalized to the topology compiler's exact slice."""

    name: str
    groups: list[str]
    concurrency: ConcurrencyIntent


def animator_records(view: RegistryView, leases: LeaseLedger) -> list[AnimatorRecord]:
    """Project one record per soulstone-sourced animator over registry truth.

    Portals are excluded (``get_soulstone_rune(name) is None`` — not lifecycle-managed).
    Concurrency comes from THE RUNE (``rune.concurrency``), NEVER from an arbitrary spec.
    ``active`` is any capability state whose owning runtime is started. This
    includes ``ACTIVATABLE`` dynamic routers: an unloaded model is still a live,
    resource-owning systemd unit.
    """
    records: list[AnimatorRecord] = []
    seen: set[str] = set()
    specs = view.list_capabilities()
    for spec in specs:
        name = spec.animator_name
        if name in seen:
            continue
        rune = view.get_soulstone_rune(name)
        if rune is None:
            continue
        seen.add(name)
        active = any(
            (state := view.get_capability_state(peer.key)) is not None and state.runtime_started
            for peer in specs
            if peer.animator_name == name
        )
        records.append(
            AnimatorRecord(
                name=name,
                dedicated=rune.concurrency.dedicated,
                persistent_resident=rune.concurrency.persistent_resident,
                active=active,
                leased=bool(leases.active(animator_name=name)),
            )
        )
    return records


@dataclass(frozen=True, slots=True)
class SwitchDecision:
    """The animator-level plan a switch policy returns (manager maps it to a TransitionPlan)."""

    evict_animator_names: list[str]
    launch_animator_names: list[str]
    metabolic_cost: float
    reason: str | None = None


class SwitchPolicy(Protocol):
    """The pluggable eviction solver contract (spec-00 C4)."""

    name: str

    def solve(self, target: CapabilitySpec, view: RegistryView, leases: LeaseLedger) -> SwitchDecision: ...


class DeclaredConflictPolicy:
    """Evict only active exact neighbors from the declared conflict graph.

    Omitted conflict domains preserve the former conservative global switching
    pool, while explicit empty domains allow coexistence. Live leases do not
    spare a neighbor; the manager closes admission and drains the exact selected
    set before systemd enforces the same graph.
    """

    name = "declared-conflicts"

    def solve(self, target: CapabilitySpec, view: RegistryView, leases: LeaseLedger) -> SwitchDecision:
        """Select the exact active neighbor closure for the requested Animator."""
        records = animator_records(view, leases)
        if any(record.name == target.animator_name and record.active for record in records):
            return SwitchDecision(evict_animator_names=[], launch_animator_names=[], metabolic_cost=0.0)

        runes: list[_ConflictProjection] = []
        seen: set[str] = set()
        for spec in view.list_capabilities():
            if spec.animator_name in seen:
                continue
            rune = view.get_soulstone_rune(spec.animator_name)
            if rune is None:
                continue
            seen.add(spec.animator_name)
            runes.append(
                _ConflictProjection(
                    name=spec.animator_name,
                    groups=list(getattr(rune, "groups", ())),
                    concurrency=cast("ConcurrencyIntent", rune.concurrency),
                )
            )
        topology = build_conflict_topology(runes)
        neighbors = set(topology.neighbors_for(target.animator_name))
        evictees = sorted(record.name for record in records if record.active and record.name in neighbors)
        return SwitchDecision(
            evict_animator_names=evictees,
            launch_animator_names=[target.animator_name],
            metabolic_cost=float(len(evictees)),
        )


class EvictIdlePolicy(DeclaredConflictPolicy):
    """Compatibility class for the former ``evict-idle`` configuration name.

    It inherits the declared-conflict solver exactly; it must never revive the
    former all-active implementation independently of the generated systemd
    graph.
    """


_DECLARED_CONFLICT_POLICY = DeclaredConflictPolicy()
SWITCH_POLICIES: dict[str, SwitchPolicy] = {
    "declared-conflicts": _DECLARED_CONFLICT_POLICY,
    "evict-idle": _DECLARED_CONFLICT_POLICY,
}


def resolve_switch_policy(name: str) -> SwitchPolicy:
    """Return the registered policy by name, or raise loudly naming the registered names.

    (Extension hook onto ``SWITCH_POLICIES`` is a Wave-5 follow-up, spec-00 C4.)
    """
    try:
        return SWITCH_POLICIES[name]
    except KeyError as exc:
        registered = ", ".join(sorted(SWITCH_POLICIES))
        msg = f"Unknown switch policy '{name}'. Registered policies: {registered}."
        raise ValueError(msg) from exc
