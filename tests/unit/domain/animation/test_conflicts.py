"""Conflict-domain schema and pure topology contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lychd.config import QuadletConfig
from lychd.domain.animation.conflicts import (
    ConflictTopologyError,
    build_conflict_topology,
    require_soulstone_capability_coverage,
)
from lychd.domain.animation.schemas import (
    DEFAULT_CONFLICT_DOMAIN,
    ConcurrencyIntent,
    GenericSoulstoneConfig,
)


def _stone(
    name: str,
    *,
    domains: list[str] | None = None,
    groups: list[str] | None = None,
    dedicated: bool = True,
    resident: bool = False,
) -> GenericSoulstoneConfig:
    return GenericSoulstoneConfig(
        name=name,
        quadlet=QuadletConfig(image="example/runtime"),
        groups=groups or [],
        concurrency=ConcurrencyIntent(
            dedicated=dedicated,
            persistent_resident=resident,
            conflict_domains=domains,
        ),
    )


def test_conflict_domain_omission_preserves_conservative_pool() -> None:
    intent = ConcurrencyIntent()

    assert intent.conflict_domains is None
    assert intent.resolved_conflict_domains == (DEFAULT_CONFLICT_DOMAIN,)


def test_omission_is_a_wildcard_during_partial_migration() -> None:
    topology = build_conflict_topology(
        [
            _stone("legacy"),
            _stone("gpu-zero", domains=["gpu-0"]),
            _stone("gpu-one", domains=["gpu-1"]),
            _stone("coexistent", domains=[]),
        ]
    )

    assert topology.neighbors_for("legacy") == ("gpu-one", "gpu-zero")
    assert topology.neighbors_for("gpu-zero") == ("legacy",)
    assert topology.neighbors_for("gpu-one") == ("legacy",)
    assert topology.neighbors_for("coexistent") == ()


def test_explicit_empty_conflict_domains_declares_coexistence() -> None:
    assert ConcurrencyIntent(conflict_domains=[]).resolved_conflict_domains == ()


def test_every_soulstone_requires_canonical_capability_coverage() -> None:
    stones = [_stone("voice"), _stone("vision", domains=[])]

    with pytest.raises(ConflictTopologyError, match=r"at least one capability.*vision"):
        require_soulstone_capability_coverage(
            stones,
            capability_animator_names=["voice"],
        )

    require_soulstone_capability_coverage(
        stones,
        capability_animator_names=["voice", "vision"],
    )


@pytest.mark.parametrize(
    ("intent", "message"),
    [
        (
            {"dedicated": False, "conflict_domains": ["gpu-0"]},
            "non-dedicated",
        ),
        (
            {"persistent_resident": True, "conflict_domains": ["gpu-0"]},
            "persistent-resident",
        ),
    ],
)
def test_unmanaged_or_resident_runtime_cannot_claim_conflict_domains(
    intent: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        ConcurrencyIntent.model_validate(intent)


@pytest.mark.parametrize("intent", [{"dedicated": False}, {"persistent_resident": True}])
def test_unmanaged_or_resident_omission_resolves_empty(intent: dict[str, object]) -> None:
    assert ConcurrencyIntent.model_validate(intent).resolved_conflict_domains == ()


@pytest.mark.parametrize(
    "domains",
    [
        ["gpu-0", "gpu-0"],
        [""],
        ["GPU-0"],
        ["gpu 0"],
        ["-gpu"],
        [DEFAULT_CONFLICT_DOMAIN],
    ],
)
def test_conflict_domain_labels_are_unique_safe_slugs(domains: list[str]) -> None:
    with pytest.raises(ValidationError, match="conflict_domains"):
        ConcurrencyIntent(conflict_domains=domains)


def test_topology_projects_undirected_neighbors_and_one_lexical_edge() -> None:
    topology = build_conflict_topology(
        [
            _stone("vision", domains=["gpu-0"]),
            _stone("reasoner", domains=["gpu-1", "gpu-0"]),
            _stone("speech", domains=["gpu-1"]),
            _stone("embedder", domains=[]),
        ]
    )

    assert topology.domains_for("reasoner") == ("gpu-0", "gpu-1")
    assert topology.neighbors_for("reasoner") == ("speech", "vision")
    assert topology.neighbors_for("vision") == ("reasoner",)
    assert topology.neighbors_for("embedder") == ()
    assert topology.oriented_edges == (
        ("reasoner", "speech"),
        ("reasoner", "vision"),
    )
    assert topology.predecessors_for("speech") == ("reasoner",)
    assert topology.predecessors_for("reasoner") == ()


def test_topology_owns_only_real_compatible_coven_aggregates() -> None:
    topology = build_conflict_topology(
        [
            _stone("eye", domains=["gpu"], groups=["solo"]),
            _stone("voice", domains=["audio"], groups=["senses"]),
            _stone("scribe", domains=["cpu"], groups=["senses"]),
        ]
    )

    assert dict(topology.coven_members) == {
        "senses": ("scribe", "voice"),
    }


def test_topology_rejects_conflict_inside_one_coven() -> None:
    with pytest.raises(ConflictTopologyError, match=r"conflict.*share Coven.*vision"):
        build_conflict_topology(
            [
                _stone("eye", domains=["gpu-0"], groups=["vision"]),
                _stone("scribe", domains=["gpu-0"], groups=["vision"]),
            ]
        )


def test_topology_rejects_duplicate_animator_names() -> None:
    with pytest.raises(ConflictTopologyError, match="duplicate Animator"):
        build_conflict_topology([_stone("eye"), _stone("eye", domains=[])])


@pytest.mark.parametrize(
    "stone",
    [
        _stone("eye", groups=["vision", "vision"]),
        _stone("eye", groups=["Vision"]),
    ],
)
def test_topology_rejects_malformed_coven_declarations(
    stone: GenericSoulstoneConfig,
) -> None:
    with pytest.raises(ConflictTopologyError, match="Coven"):
        build_conflict_topology([stone])
