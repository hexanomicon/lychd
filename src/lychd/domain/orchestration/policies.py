"""Switch policies — the honest eviction solver, extracted from the manager (wave3 §5.1).

O1 is a behavior-preserving extraction of the keel's manager-private honest solver
(`_AnimatorRecord` + `_solve_transition`) into a reusable, lease-aware policy surface.
The eviction law selects every other DEDICATED, non-persistent-resident,
ACTIVE animator. Leased evictees remain in the plan so the manager can close their
admission gate and drain them before eviction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lychd.domain.animation.capabilities import CapabilitySpec, CapabilityState
    from lychd.domain.cortex.leases import LeaseLedger

__all__ = [
    "SWITCH_POLICIES",
    "AnimatorRecord",
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


class EvictIdlePolicy:
    """Keel ``_solve_transition`` semantics over :class:`AnimatorRecord`.

    Target's animator already active → no-op decision; else evict every dedicated,
    non-persistent-resident, active animator and launch the target. Live leases do
    not spare an evictee; they make execution wait for an honest lease drain.
    """

    name = "evict-idle"

    def solve(self, target: CapabilitySpec, view: RegistryView, leases: LeaseLedger) -> SwitchDecision:
        """Select the eviction set honestly over the lease-aware animator records."""
        records = animator_records(view, leases)
        if any(record.name == target.animator_name and record.active for record in records):
            return SwitchDecision(evict_animator_names=[], launch_animator_names=[], metabolic_cost=0.0)

        evictees = sorted(
            record.name
            for record in records
            if record.dedicated
            and not record.persistent_resident
            and record.active
            and record.name != target.animator_name
        )
        return SwitchDecision(
            evict_animator_names=evictees,
            launch_animator_names=[target.animator_name],
            metabolic_cost=float(len(evictees)),
        )


SWITCH_POLICIES: dict[str, SwitchPolicy] = {"evict-idle": EvictIdlePolicy()}


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
