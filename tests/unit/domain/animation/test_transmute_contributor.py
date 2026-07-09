"""QuadletContributor seam: signature honesty + the identity guarantee (P3/P4)."""

from __future__ import annotations

import inspect

import pytest

from lychd.config.runes.registry import RuneRegistry
from lychd.domain.animation.schemas import GenericSoulstoneConfig
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import (
    QuadletContribution,
    QuadletContributor,
    TransmutationContext,
    TransmutationStore,
    Transmuter,
)
from lychd.system.schemas import QuadletContainer, QuadletPod


def _transmuter(*contributors: QuadletContributor) -> Transmuter:
    return Transmuter(runtime_planner=RuntimeAdapterRegistry(), contributors=list(contributors))


def test_transmute_all_has_no_extension_runes_param() -> None:
    """P4: the legacy ``extension_runes`` parameter is gone; ``runes`` replaces it."""
    params = inspect.signature(Transmuter.transmute_all).parameters
    assert "extension_runes" not in params
    assert "runes" in params


def test_no_contributors_reproduces_core_only() -> None:
    """AnimatorRegistry builds a contributor-free Transmuter by design (identity guarantee)."""
    manifests = _transmuter().transmute_all([], runes=RuneRegistry([]))
    pod = next(m for m in manifests if isinstance(m, QuadletPod))
    assert len(pod.publish_ports) == 2
    names = {m.container_name for m in manifests if isinstance(m, QuadletContainer)}
    assert names == {"lychd-vessel", "lychd-phylactery", "lychd-migrate"}


def test_runes_defaults_to_empty_registry() -> None:
    """runes=None is tolerated (empty registry) -- no contributor finds a rune."""
    manifests = _transmuter().transmute_all([])
    assert any(isinstance(m, QuadletPod) for m in manifests)


class _PortOnlyContributor:
    """A contributor adding only a pod port -- proves ports append AFTER core ports."""

    def contribute(self, ctx: TransmutationContext) -> QuadletContribution:
        _ = ctx
        return QuadletContribution(pod_ports=["9999:9999"])


class _ContainerContributor:
    """A contributor adding one container -- proves it lands after core, before targets."""

    def contribute(self, ctx: TransmutationContext) -> QuadletContribution:
        _ = ctx
        return QuadletContribution(
            containers=[QuadletContainer(description="x", image="img", container_name="lychd-extra", pod="lychd.pod")]
        )


def test_contribution_ports_append_after_core() -> None:
    manifests = _transmuter(_PortOnlyContributor()).transmute_all([], runes=RuneRegistry([]))
    pod = next(m for m in manifests if isinstance(m, QuadletPod))
    assert pod.publish_ports[-1] == "127.0.0.1:9999:9999"
    assert len(pod.publish_ports) == 3


def test_contribution_container_lands_after_core_before_stones() -> None:
    stone = GenericSoulstoneConfig(name="alpha", image="registry.example/alpha:1", groups=[])
    manifests = _transmuter(_ContainerContributor()).transmute_all([stone], runes=RuneRegistry([]))
    order = [
        type(m).__name__ + ":" + (getattr(m, "container_name", "") or getattr(m, "pod_name", "")) for m in manifests
    ]
    extra_idx = order.index("QuadletContainer:lychd-extra")
    phylactery_idx = order.index("QuadletContainer:lychd-phylactery")
    stone_idx = order.index("QuadletContainer:lychd-alpha")
    assert phylactery_idx < extra_idx < stone_idx


def test_contribution_is_frozen_no_mutation_surface() -> None:
    """§8.4: QuadletContribution is a frozen dataclass (structural identity guarantee)."""
    contribution = QuadletContribution()
    with pytest.raises((AttributeError, TypeError)):
        contribution.pod_ports = ["1:1"]  # type: ignore[misc]


def test_transmutation_store_registration_order() -> None:
    store = TransmutationStore()
    first = _PortOnlyContributor()
    second = _ContainerContributor()
    store.add_contributor(first)
    store.add_contributor(second)
    assert store.contributors == (first, second)
