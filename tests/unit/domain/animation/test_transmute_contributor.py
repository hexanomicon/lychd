"""QuadletContributor seam: signature honesty + the identity guarantee (P3/P4)."""

from __future__ import annotations

import inspect

import pytest

from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import get_settings
from lychd.domain.animation.schemas import (
    ConcurrencyIntent,
    GenericSoulstoneConfig,
)
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import (
    QuadletContribution,
    QuadletContributor,
    TransmutationContext,
    TransmutationStore,
    Transmuter,
)
from lychd.extensions.context import ExtensionContext
from lychd.system.constants import CONTAINER_LYCHD_PORT
from lychd.system.schemas import QuadletContainer, QuadletPod


def _transmuter(*contributors: QuadletContributor) -> Transmuter:
    return Transmuter(
        settings=get_settings(), runtime_planner=RuntimeAdapterRegistry(), contributors=list(contributors)
    )


def test_transmute_all_has_no_extension_runes_param() -> None:
    """P4: the legacy ``extension_runes`` parameter is gone; ``runes`` replaces it."""
    params = inspect.signature(Transmuter.transmute_all).parameters
    assert "extension_runes" not in params
    assert "runes" in params


def test_no_contributors_reproduces_core_only() -> None:
    """A contributor-free physical compilation retains the exact core body."""
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
        return QuadletContribution(pod_ports=("9999:9999",))


class _ContainerContributor:
    """A contributor adding one container -- proves it lands after core, before targets."""

    def contribute(self, ctx: TransmutationContext) -> QuadletContribution:
        _ = ctx
        return QuadletContribution(
            containers=(QuadletContainer(description="x", image="img", container_name="lychd-extra", pod="lychd.pod"),)
        )


class _UnsafePortContributor:
    def __init__(self, mapping: str) -> None:
        self._mapping = mapping

    def contribute(self, ctx: TransmutationContext) -> QuadletContribution:
        _ = ctx
        return QuadletContribution(pod_ports=(self._mapping,))


def test_contribution_ports_append_after_core() -> None:
    manifests = _transmuter(_PortOnlyContributor()).transmute_all([], runes=RuneRegistry([]))
    pod = next(m for m in manifests if isinstance(m, QuadletPod))
    assert pod.publish_ports[-1] == "127.0.0.1:9999:9999"
    assert len(pod.publish_ports) == 3


@pytest.mark.parametrize(
    "mapping",
    [
        "9999:9999\nNetwork=host",
        "0:9999",
        "65536:9999",
        "9999:9999:udp",
        "not-a-port",
    ],
)
def test_contribution_ports_cannot_escape_the_loopback_port_boundary(mapping: str) -> None:
    with pytest.raises(ValueError, match="PublishPort|single-line"):
        _transmuter(_UnsafePortContributor(mapping)).transmute_all([], runes=RuneRegistry([]))


def test_contribution_port_cannot_duplicate_a_core_host_port() -> None:
    from lychd.config.settings.root import get_settings

    server_port = get_settings().server.port
    with pytest.raises(ValueError, match=f"duplicate host port {server_port}"):
        _transmuter(_UnsafePortContributor(f"{server_port}:9999")).transmute_all([], runes=RuneRegistry([]))


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
        contribution.pod_ports = ("1:1",)  # type: ignore[misc]


def test_contributors_receive_isolated_deep_snapshots() -> None:
    """One extension cannot mutate core declarations or a later contributor."""
    settings = get_settings().model_copy(deep=True)
    original_port = settings.server.port
    stone = GenericSoulstoneConfig(
        name="alpha",
        image="registry.example/alpha:1",
        concurrency=ConcurrencyIntent(dedicated=True),
    )
    observed: list[tuple[int, bool]] = []

    class Mutator:
        def contribute(
            self,
            ctx: TransmutationContext,
        ) -> QuadletContribution:
            ctx.settings.server.port = original_port + 1
            ctx.soulstones[0].concurrency.dedicated = False
            return QuadletContribution()

    class Observer:
        def contribute(
            self,
            ctx: TransmutationContext,
        ) -> QuadletContribution:
            observed.append(
                (
                    ctx.settings.server.port,
                    ctx.soulstones[0].concurrency.dedicated,
                )
            )
            return QuadletContribution()

    manifests = Transmuter(
        settings=settings,
        runtime_planner=RuntimeAdapterRegistry(),
        contributors=(Mutator(), Observer()),
    ).transmute_all((stone,), runes=RuneRegistry(()))

    pod = next(manifest for manifest in manifests if isinstance(manifest, QuadletPod))
    assert observed == [(original_port, True)]
    assert settings.server.port == original_port
    assert stone.concurrency.dedicated is True
    assert f"127.0.0.1:{original_port}:{CONTAINER_LYCHD_PORT}" in pod.publish_ports


def test_transmuter_detaches_contributor_owned_payloads() -> None:
    """A retained extension object cannot mutate the emitted manifest later."""
    contributed = QuadletContainer(
        description="approved",
        image="img",
        container_name="lychd-extra",
        pod="lychd.pod",
    )

    class Contributor:
        def contribute(
            self,
            ctx: TransmutationContext,
        ) -> QuadletContribution:
            del ctx
            return QuadletContribution(containers=(contributed,))

    manifests = _transmuter(Contributor()).transmute_all(())
    emitted = next(
        manifest
        for manifest in manifests
        if isinstance(manifest, QuadletContainer) and manifest.container_name == "lychd-extra"
    )
    contributed.env_vars["MUTATED_LATER"] = "yes"

    assert emitted.description == "approved"
    assert "MUTATED_LATER" not in emitted.env_vars


def test_transmutation_store_registration_order() -> None:
    store = TransmutationStore()
    first = _PortOnlyContributor()
    second = _ContainerContributor()
    store.add_contributor(first)
    store.add_contributor(second)
    assert store.contributors == (first, second)


def test_transmutation_store_rejects_cross_provider_replay() -> None:
    context = ExtensionContext()
    contributor = _PortOnlyContributor()
    with context.provenance("one"):
        context.transmutation.add_contributor(contributor)
    with context.provenance("two"), pytest.raises(ValueError, match="owned by 'one'"):
        context.transmutation.add_contributor(contributor)


def test_bootstrap_assembly_seals_a_hand_built_context() -> None:
    from lychd.extensions.host import AssembledExtensions

    context = ExtensionContext()
    AssembledExtensions(context=context, active_ids=("manual",))

    with pytest.raises(RuntimeError, match="frozen after extension assembly"):
        context.transmutation.add_contributor(_PortOnlyContributor())
