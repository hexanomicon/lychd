"""Pure conflict-topology compilation for local Animator declarations."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Protocol

from lychd.domain.animation.schemas.concurrency import (
    CONFLICT_DOMAIN_PATTERN,
    DEFAULT_CONFLICT_DOMAIN,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent

__all__ = [
    "MIN_COVEN_MEMBERS",
    "ConflictDeclaration",
    "ConflictTopology",
    "ConflictTopologyError",
    "build_conflict_topology",
    "require_soulstone_capability_coverage",
]

MIN_COVEN_MEMBERS = 2
"""A named Coven becomes a generated aggregate only with two or more members."""


class ConflictDeclaration(Protocol):
    """Small declaration slice needed to compile physical exclusivity."""

    @property
    def name(self) -> str:
        """Stable Animator identity."""
        ...

    @property
    def groups(self) -> Sequence[str]:
        """Coven memberships used only for aggregate-safety validation."""
        ...

    @property
    def concurrency(self) -> ConcurrencyIntent:
        """Lifecycle and exclusivity declaration."""
        ...


class ConflictTopologyError(ValueError):
    """A declaration set cannot produce one safe systemd conflict graph."""


@dataclass(frozen=True, slots=True)
class ConflictTopology:
    """Deterministic conflict graph and compatible aggregate projection.

    ``oriented_edges`` stores each undirected edge exactly once as
    ``(lexically_lower, lexically_higher)``. A systemd compiler can therefore
    emit ordering from the higher endpoint without inventing another graph
    orientation rule. ``coven_members`` is the same validated declaration
    snapshot projected into operator aggregates, so no consumer recomputes the
    minimum-membership law.
    """

    domains_by_animator: Mapping[str, tuple[str, ...]]
    neighbors_by_animator: Mapping[str, tuple[str, ...]]
    coven_members: Mapping[str, tuple[str, ...]]
    oriented_edges: tuple[tuple[str, str], ...]

    def domains_for(self, animator_name: str) -> tuple[str, ...]:
        """Return the resolved exclusive-domain memberships for one Animator."""
        return self.domains_by_animator.get(animator_name, ())

    def neighbors_for(self, animator_name: str) -> tuple[str, ...]:
        """Return every exact conflict neighbor in lexical order."""
        return self.neighbors_by_animator.get(animator_name, ())

    def predecessors_for(self, animator_name: str) -> tuple[str, ...]:
        """Return lower endpoints whose ordering edge is emitted by this Animator."""
        return tuple(lower for lower, higher in self.oriented_edges if higher == animator_name)


def require_soulstone_capability_coverage(
    declarations: Iterable[ConflictDeclaration],
    *,
    capability_animator_names: Iterable[str],
) -> None:
    """Require every local lifecycle declaration to enter canonical activity truth.

    Phase one derives planning, drains, and the manager's expected physical world
    from capability state. A Soulstone with no synthesized capability would be
    visible to host systemd attestation but invisible to the Orchestrator, making
    every transition safely decline. Unadvertised infrastructure must therefore
    use a core/extension unit until a runtime-state port independent of
    ``CapabilitySpec`` exists.
    """
    advertised = set(capability_animator_names)
    missing = sorted(declaration.name for declaration in declarations if declaration.name not in advertised)
    if missing:
        msg = (
            "Soulstones must each synthesize at least one capability before entering "
            f"the lifecycle graph; unadvertised Soulstones: {', '.join(missing)}"
        )
        raise ConflictTopologyError(msg)


def build_conflict_topology(declarations: Iterable[ConflictDeclaration]) -> ConflictTopology:
    """Compile validated declarations into one deterministic undirected graph.

    Domain membership creates an edge. Coven membership is independent
    aggregation metadata, so a pair that both conflicts and belongs to one
    Coven is rejected: starting that aggregate could never be satisfiable.
    """
    declared = tuple(declarations)
    _validate_declarations(declared)

    by_name = {declaration.name: declaration for declaration in declared}
    domains_by_animator = {
        name: tuple(sorted(declaration.concurrency.resolved_conflict_domains))
        for name, declaration in sorted(by_name.items())
    }
    domain_members: dict[str, list[str]] = {}
    for name, domains in domains_by_animator.items():
        for domain in domains:
            domain_members.setdefault(domain, []).append(name)

    edge_set: set[tuple[str, str]] = set()
    for members in domain_members.values():
        ordered = sorted(members)
        for index, lower in enumerate(ordered):
            edge_set.update((lower, higher) for higher in ordered[index + 1 :])

    # Omission means "global exclusivity is still unknown", not membership in
    # one ordinary pool. During partial migration, connect that sentinel to
    # every other managed runtime with a non-empty declaration. Only explicit
    # ``[]`` is sufficient evidence of coexistence.
    wildcard_animators = sorted(
        name for name, domains in domains_by_animator.items() if DEFAULT_CONFLICT_DOMAIN in domains
    )
    non_coexistent_animators = sorted(name for name, domains in domains_by_animator.items() if domains)
    for wildcard in wildcard_animators:
        for other in non_coexistent_animators:
            if wildcard == other:
                continue
            edge_set.add((wildcard, other) if wildcard < other else (other, wildcard))
    oriented_edges = tuple(sorted(edge_set))

    _reject_coven_internal_conflicts(by_name, oriented_edges)
    _reject_resident_conflicts(by_name, oriented_edges)

    neighbors: dict[str, set[str]] = {name: set() for name in by_name}
    for lower, higher in oriented_edges:
        neighbors[lower].add(higher)
        neighbors[higher].add(lower)
    neighbors_by_animator = {
        name: tuple(sorted(animator_neighbors)) for name, animator_neighbors in sorted(neighbors.items())
    }
    all_groups = sorted({group for declaration in declared for group in declaration.groups})
    coven_members = {
        group: tuple(sorted(declaration.name for declaration in declared if group in declaration.groups))
        for group in all_groups
    }
    coven_members = {group: members for group, members in coven_members.items() if len(members) >= MIN_COVEN_MEMBERS}

    return ConflictTopology(
        domains_by_animator=MappingProxyType(domains_by_animator),
        neighbors_by_animator=MappingProxyType(neighbors_by_animator),
        coven_members=MappingProxyType(coven_members),
        oriented_edges=oriented_edges,
    )


def _validate_declarations(declarations: tuple[ConflictDeclaration, ...]) -> None:
    names = [declaration.name for declaration in declarations]
    duplicates = sorted(name for name in set(names) if names.count(name) > 1)
    if duplicates:
        msg = f"duplicate Animator declarations in conflict topology: {', '.join(duplicates)}"
        raise ConflictTopologyError(msg)

    for declaration in declarations:
        if CONFLICT_DOMAIN_PATTERN.fullmatch(declaration.name) is None:
            msg = (
                f"Animator name {declaration.name!r} cannot enter conflict topology; "
                f"expected {CONFLICT_DOMAIN_PATTERN.pattern}"
            )
            raise ConflictTopologyError(msg)
        duplicate_groups = sorted(group for group in set(declaration.groups) if declaration.groups.count(group) > 1)
        if duplicate_groups:
            msg = f"Animator '{declaration.name}' repeats Coven labels: {', '.join(duplicate_groups)}"
            raise ConflictTopologyError(msg)
        invalid_groups = [group for group in declaration.groups if CONFLICT_DOMAIN_PATTERN.fullmatch(group) is None]
        if invalid_groups:
            msg = (
                f"Animator '{declaration.name}' has malformed Coven labels: "
                f"{', '.join(repr(group) for group in invalid_groups)}"
            )
            raise ConflictTopologyError(msg)

        resolved = declaration.concurrency.resolved_conflict_domains
        if (not declaration.concurrency.dedicated or declaration.concurrency.persistent_resident) and resolved:
            msg = (
                f"Animator '{declaration.name}' lies outside exclusive lifecycle authority "
                "but resolves non-empty conflict domains"
            )
            raise ConflictTopologyError(msg)


def _reject_coven_internal_conflicts(
    declarations: dict[str, ConflictDeclaration],
    oriented_edges: tuple[tuple[str, str], ...],
) -> None:
    for lower, higher in oriented_edges:
        shared_groups = sorted(set(declarations[lower].groups).intersection(declarations[higher].groups))
        if shared_groups:
            msg = f"Animators '{lower}' and '{higher}' conflict but share Coven(s): {', '.join(shared_groups)}"
            raise ConflictTopologyError(msg)


def _reject_resident_conflicts(
    declarations: dict[str, ConflictDeclaration],
    oriented_edges: tuple[tuple[str, str], ...],
) -> None:
    for lower, higher in oriented_edges:
        residents = [name for name in (lower, higher) if declarations[name].concurrency.persistent_resident]
        if residents:
            msg = f"persistent-resident Animator(s) cannot participate in a realized conflict: {', '.join(residents)}"
            raise ConflictTopologyError(msg)
