from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

import pytest

from lychd.config import QuadletConfig
from lychd.domain.animation.schemas import ConcurrencyIntent, GenericSoulstoneConfig
from lychd.domain.orchestration.actuator import (
    RuntimePreconditionError,
    TransitionIntent,
    build_compensation_intent,
)
from lychd.system.services.runtime_topology import RuntimeTopologyAttestor
from lychd.system.services.scribe import OwnedBindings
from lychd.system.unit_names import animator_service_unit, animator_target_unit, coven_target_unit

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from lychd.domain.animation.protocols import CapabilityRegistry

_SYSTEMCTL = "/usr/bin/systemctl"
_SHOW_PROPERTIES = (
    "Id",
    "LoadState",
    "NeedDaemonReload",
    "Wants",
    "Requires",
    "Before",
    "After",
    "Conflicts",
    "ConflictedBy",
    "PartOf",
    "BindsTo",
    "RequiredBy",
    "BoundBy",
    "DropInPaths",
    "FragmentPath",
    "SourcePath",
    "UnitFileState",
)
_SHOW_FLAGS = tuple(f"--property={property_name}" for property_name in _SHOW_PROPERTIES)
_POD = "lychd-pod.service"


@dataclass(slots=True)
class _ShowProcess:
    """Minimal faithful result of one blocking ``systemctl show`` query."""

    stdout: bytes
    stderr: bytes = b""
    returncode: int = 0

    async def communicate(self) -> tuple[bytes, bytes]:
        return self.stdout, self.stderr


def _stone(name: str, *, conflict_domains: list[str]) -> GenericSoulstoneConfig:
    return GenericSoulstoneConfig(
        name=name,
        quadlet=QuadletConfig(image=f"example/{name}:latest"),
        concurrency=ConcurrencyIntent(conflict_domains=tuple(conflict_domains)),
    )


def _registry(
    stones: list[GenericSoulstoneConfig],
    *,
    list_capabilities: Mock | None = None,
) -> CapabilityRegistry:
    registry = SimpleNamespace(
        list_soulstone_runes=lambda: list(stones),
        list_capabilities=list_capabilities or Mock(return_value=[]),
    )
    return cast("CapabilityRegistry", registry)


def _intent(*, evict_animators: tuple[str, ...] = ("alpha",)) -> TransitionIntent:
    return TransitionIntent(
        transition_id="a" * 32,
        config_generation="sha256:" + "b" * 64,
        target_animator="beta",
        target_capability_key="beta:default",
        evict_animators=evict_animators,
        launch_animators=("beta",),
        expected_active_animators=("alpha",),
    )


def _blank_properties(unit_name: str) -> dict[str, str]:
    return {
        "Id": unit_name,
        "LoadState": "loaded",
        "NeedDaemonReload": "no",
        "Wants": "",
        "Requires": "",
        "Before": "",
        "After": "",
        "Conflicts": "",
        "ConflictedBy": "",
        "PartOf": "",
        "BindsTo": "",
        "RequiredBy": "",
        "BoundBy": "",
        "DropInPaths": "",
        "FragmentPath": "",
        "SourcePath": "",
        "UnitFileState": "",
    }


def _service_properties(animator_name: str) -> dict[str, str]:
    unit_name = animator_service_unit(animator_name)
    properties = _blank_properties(unit_name)
    target = animator_target_unit(animator_name)
    properties["After"] = f"{_POD} {target}"
    properties["BindsTo"] = f"{_POD} {target}"
    properties["RequiredBy"] = target
    return properties


def _exact_pair_graph() -> dict[str, dict[str, str]]:
    alpha_target = animator_target_unit("alpha")
    beta_target = animator_target_unit("beta")

    alpha = _blank_properties(alpha_target)
    alpha["Requires"] = animator_service_unit("alpha")
    alpha["Before"] = animator_service_unit("alpha")
    alpha["After"] = _POD
    alpha["PartOf"] = _POD
    alpha["BoundBy"] = animator_service_unit("alpha")

    beta = _blank_properties(beta_target)
    beta["Requires"] = animator_service_unit("beta")
    beta["Before"] = animator_service_unit("beta")
    beta["After"] = f"{_POD} {alpha_target}"
    beta["Conflicts"] = alpha_target
    beta["PartOf"] = _POD
    beta["BoundBy"] = animator_service_unit("beta")

    return {
        animator_service_unit("alpha"): _service_properties("alpha"),
        alpha_target: alpha,
        animator_service_unit("beta"): _service_properties("beta"),
        beta_target: beta,
    }


def _add_coexistent_animator(graph: dict[str, dict[str, str]], animator_name: str) -> None:
    target_unit = animator_target_unit(animator_name)
    target = _blank_properties(target_unit)
    target["Requires"] = animator_service_unit(animator_name)
    target["Before"] = animator_service_unit(animator_name)
    target["After"] = _POD
    target["PartOf"] = _POD
    target["BoundBy"] = animator_service_unit(animator_name)
    graph[target_unit] = target
    graph[animator_service_unit(animator_name)] = _service_properties(animator_name)


def _show_payload(properties: dict[str, str]) -> bytes:
    return ("".join(f"{name}={properties[name]}\n" for name in _SHOW_PROPERTIES)).encode()


def _owned_bindings(
    tmp_path: Path,
    *animator_names: str,
    stale_target: bool = False,
) -> OwnedBindings:
    quadlet = tmp_path / "quadlet"
    systemd = tmp_path / "systemd"
    quadlet_sources = tuple(quadlet / f"lychd-{name}.container" for name in animator_names)
    target_names = (*animator_names, *(("removed",) if stale_target else ()))
    systemd_sources = tuple(systemd / f"lychd-animator-{name}.target" for name in target_names)
    runtime_units = tuple(
        sorted(
            {
                *(f"lychd-{name}.service" for name in animator_names),
                *(f"lychd-animator-{name}.target" for name in target_names),
            }
        )
    )
    return OwnedBindings(
        receipt_present=True,
        generation="sha256:test-generation",
        quadlet_sources=quadlet_sources,
        systemd_sources=systemd_sources,
        runtime_units=runtime_units,
    )


def _attach_owned_sources(
    graph: dict[str, dict[str, str]],
    tmp_path: Path,
    *animator_names: str,
) -> None:
    for animator_name in animator_names:
        service = graph[animator_service_unit(animator_name)]
        service["SourcePath"] = str(tmp_path / "quadlet" / f"lychd-{animator_name}.container")
        service["FragmentPath"] = f"/run/user/1000/systemd/generator/lychd-{animator_name}.service"
        service["UnitFileState"] = "generated"
        target = graph[animator_target_unit(animator_name)]
        target["FragmentPath"] = str(tmp_path / "systemd" / f"lychd-animator-{animator_name}.target")
        target["UnitFileState"] = "static"


def _mock_systemctl_show(
    mocker: MockerFixture,
    graph: dict[str, dict[str, str]],
) -> tuple[Mock, list[str]]:
    observed_units: list[str] = []

    async def create_subprocess(*args: object, **kwargs: object) -> _ShowProcess:
        if len(args) >= 3 and args[2] in {"list-unit-files", "list-units"}:
            command = args[2]
            common_tail = (
                "lychd-animator-*.target",
                "lychd-coven-*.target",
            )
            expected_args = (
                (_SYSTEMCTL, "--user", "list-unit-files", "--no-legend", "--no-pager", *common_tail)
                if command == "list-unit-files"
                else (
                    _SYSTEMCTL,
                    "--user",
                    "list-units",
                    "--all",
                    "--plain",
                    "--no-legend",
                    "--no-pager",
                    *common_tail,
                )
            )
            assert args == expected_args
            assert kwargs == {
                "stdout": asyncio.subprocess.PIPE,
                "stderr": asyncio.subprocess.PIPE,
            }
            targets = sorted(unit for unit in graph if unit.endswith(".target"))
            payload = "".join(f"{unit} loaded inactive dead test\n" for unit in targets).encode()
            return _ShowProcess(stdout=payload)
        assert len(args) == 4 + len(_SHOW_FLAGS)
        arguments = list(args)
        unit_name = arguments[-1]
        assert isinstance(unit_name, str)
        assert args == (_SYSTEMCTL, "--user", "show", *_SHOW_FLAGS, unit_name)
        assert kwargs == {
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE,
        }
        observed_units.append(unit_name)
        return _ShowProcess(stdout=_show_payload(graph[unit_name]))

    subprocess = mocker.patch(
        "lychd.system.services.runtime_topology.asyncio.create_subprocess_exec",
        side_effect=create_subprocess,
    )
    return subprocess, observed_units


@pytest.mark.asyncio
async def test_exact_loaded_graph_is_bound_to_scribe_sources(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    stones = [
        _stone("alpha", conflict_domains=["gpu-0"]),
        _stone("beta", conflict_domains=["gpu-0"]),
    ]
    graph = _exact_pair_graph()
    _attach_owned_sources(graph, tmp_path, "alpha", "beta")
    subprocess, observed_units = _mock_systemctl_show(mocker, graph)

    await RuntimeTopologyAttestor(
        _registry(stones),
        systemctl_bin=_SYSTEMCTL,
        owned_bindings_provider=lambda: _owned_bindings(tmp_path, "alpha", "beta"),
    ).attest(_intent())

    assert observed_units == sorted(graph)
    assert subprocess.await_count == len(graph) + 2


@pytest.mark.asyncio
async def test_attestation_rejects_stale_scribe_target_before_systemd(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    stones = [
        _stone("alpha", conflict_domains=["gpu-0"]),
        _stone("beta", conflict_domains=["gpu-0"]),
    ]
    subprocess = mocker.patch(
        "lychd.system.services.runtime_topology.asyncio.create_subprocess_exec",
    )

    with pytest.raises(RuntimePreconditionError, match="stale runtime topology targets"):
        await RuntimeTopologyAttestor(
            _registry(stones),
            systemctl_bin=_SYSTEMCTL,
            owned_bindings_provider=lambda: _owned_bindings(
                tmp_path,
                "alpha",
                "beta",
                stale_target=True,
            ),
        ).attest(_intent())

    subprocess.assert_not_awaited()


@pytest.mark.parametrize(
    ("unit_name", "property_name", "observed", "match"),
    [
        (animator_target_unit("beta"), "NeedDaemonReload", "yes", r"beta\.target requires daemon-reload"),
        (
            animator_service_unit("alpha"),
            "DropInPaths",
            "/home/operator/.config/systemd/user/lychd-alpha.service.d/override.conf",
            r"alpha\.service is altered by drop-ins",
        ),
    ],
)
@pytest.mark.asyncio
async def test_attestation_rejects_unloaded_runtime_overrides(
    tmp_path: Path,
    mocker: MockerFixture,
    unit_name: str,
    property_name: str,
    observed: str,
    match: str,
) -> None:
    stones = [
        _stone("alpha", conflict_domains=["gpu-0"]),
        _stone("beta", conflict_domains=["gpu-0"]),
    ]
    graph = _exact_pair_graph()
    graph[unit_name][property_name] = observed
    _attach_owned_sources(graph, tmp_path, "alpha", "beta")
    _mock_systemctl_show(mocker, graph)

    with pytest.raises(RuntimePreconditionError, match=match):
        await RuntimeTopologyAttestor(
            _registry(stones),
            systemctl_bin=_SYSTEMCTL,
            owned_bindings_provider=lambda: _owned_bindings(tmp_path, "alpha", "beta"),
        ).attest(_intent())


@pytest.mark.parametrize(
    ("unit_name", "property_name", "observed"),
    [
        (animator_target_unit("alpha"), "Requires", ""),
        (animator_target_unit("alpha"), "After", ""),
        (animator_target_unit("beta"), "After", _POD),
        (animator_target_unit("alpha"), "After", f"{_POD} lychd-unowned.service"),
        (animator_target_unit("beta"), "Conflicts", animator_target_unit("beta")),
        (
            animator_target_unit("alpha"),
            "RequiredBy",
            animator_service_unit("alpha"),
        ),
        (
            animator_target_unit("alpha"),
            "Before",
            animator_target_unit("beta"),
        ),
        (
            animator_target_unit("alpha"),
            "ConflictedBy",
            animator_target_unit("beta"),
        ),
    ],
    ids=[
        "missing-requires",
        "missing-pod-ordering",
        "missing-predecessor-ordering",
        "unauthorized-managed-after",
        "tampered-conflicts",
        "impossible-inverse-requires",
        "unauthorized-managed-before",
        "unauthorized-managed-conflicted-by",
    ],
)
@pytest.mark.asyncio
async def test_attestation_rejects_missing_or_tampered_managed_relation(
    tmp_path: Path,
    mocker: MockerFixture,
    unit_name: str,
    property_name: str,
    observed: str,
) -> None:
    stones = [
        _stone("alpha", conflict_domains=["gpu-0"]),
        _stone("beta", conflict_domains=["gpu-0"]),
    ]
    graph = _exact_pair_graph()
    graph[unit_name][property_name] = observed
    _attach_owned_sources(graph, tmp_path, "alpha", "beta")
    _mock_systemctl_show(mocker, graph)

    with pytest.raises(RuntimePreconditionError, match=rf"{unit_name}\.{property_name}"):
        await RuntimeTopologyAttestor(
            _registry(stones),
            systemctl_bin=_SYSTEMCTL,
            owned_bindings_provider=lambda: _owned_bindings(tmp_path, "alpha", "beta"),
        ).attest(_intent())


@pytest.mark.parametrize(
    "after",
    [
        f"{_POD} {animator_target_unit('alpha')} {animator_target_unit('beta')}",
        f"{animator_target_unit('alpha')} {animator_target_unit('beta')}",
        f"{_POD} {animator_target_unit('alpha')}",
        f"{_POD} {animator_target_unit('alpha')} {animator_target_unit('beta')} lychd-unowned.service",
    ],
    ids=["exact-pod-and-members", "missing-pod", "missing-member", "unexpected-managed-edge"],
)
@pytest.mark.asyncio
async def test_coven_requires_exact_pod_and_member_ordering(tmp_path: Path, mocker: MockerFixture, after: str) -> None:
    """PartOf=pod default ordering belongs to the declared aggregate graph."""
    stones = [
        GenericSoulstoneConfig(
            name=name,
            quadlet=QuadletConfig(image=f"example/{name}:latest"),
            groups=("logic",),
            concurrency=ConcurrencyIntent(conflict_domains=()),
        )
        for name in ("alpha", "beta")
    ]
    coven = coven_target_unit("logic")
    members = " ".join(animator_target_unit(name) for name in ("alpha", "beta"))
    graph: dict[str, dict[str, str]] = {}
    for name in ("alpha", "beta"):
        _add_coexistent_animator(graph, name)
        graph[animator_target_unit(name)]["PartOf"] = f"{_POD} {coven}"
        graph[animator_target_unit(name)]["Before"] = f"{animator_service_unit(name)} {coven}"
    _attach_owned_sources(graph, tmp_path, "alpha", "beta")
    source = tmp_path / "systemd" / coven
    graph[coven] = {
        **_blank_properties(coven),
        "Wants": members,
        "After": after,
        "PartOf": _POD,
        "FragmentPath": str(source),
        "UnitFileState": "static",
    }
    owned = _owned_bindings(tmp_path, "alpha", "beta")
    owned = replace(
        owned,
        systemd_sources=(*owned.systemd_sources, source),
        runtime_units=(*owned.runtime_units, coven),
    )
    _mock_systemctl_show(mocker, graph)
    attestor = RuntimeTopologyAttestor(
        _registry(stones), systemctl_bin=_SYSTEMCTL, owned_bindings_provider=lambda: owned
    )
    if after == f"{_POD} {members}":
        await attestor.attest_current_topology()
    else:
        with pytest.raises(RuntimePreconditionError, match=rf"{coven}\.After"):
            await attestor.attest_current_topology()


@pytest.mark.parametrize(
    ("unit_name", "property_name", "observed", "error"),
    [
        ("", "", "", ""),
        (
            animator_target_unit("alpha"),
            "Before",
            f"{animator_service_unit('alpha')} {coven_target_unit('review')}",
            rf"{animator_target_unit('alpha')}\.Before",
        ),
        (
            animator_target_unit("alpha"),
            "Before",
            f"{animator_service_unit('alpha')} {coven_target_unit('logic')}",
            rf"{animator_target_unit('alpha')}\.Before",
        ),
        (
            animator_target_unit("alpha"),
            "Before",
            f"{coven_target_unit('logic')} {coven_target_unit('review')}",
            rf"{animator_target_unit('alpha')}\.Before",
        ),
        (
            animator_target_unit("alpha"),
            "Before",
            f"{animator_service_unit('alpha')} {coven_target_unit('logic')} {coven_target_unit('review')} lychd-unowned.service",
            rf"{animator_target_unit('alpha')}\.Before",
        ),
        (
            animator_target_unit("alpha"),
            "Before",
            f"{animator_service_unit('alpha')} {coven_target_unit('logic')} {coven_target_unit('review')} {coven_target_unit('singleton')}",
            rf"{animator_target_unit('alpha')}\.Before",
        ),
        (
            animator_target_unit("beta"),
            "Before",
            f"{animator_service_unit('beta')} {coven_target_unit('logic')} {coven_target_unit('review')}",
            rf"{animator_target_unit('beta')}\.Before",
        ),
        (
            animator_target_unit("alpha"),
            "FragmentPath",
            "/foreign/alpha.target",
            rf"Loaded target source mismatch for {animator_target_unit('alpha')}",
        ),
        (
            animator_service_unit("alpha"),
            "SourcePath",
            "/foreign/alpha.container",
            rf"Loaded Quadlet source mismatch for {animator_service_unit('alpha')}",
        ),
        (
            coven_target_unit("logic"),
            "FragmentPath",
            "/foreign/logic.target",
            rf"Loaded target source mismatch for {coven_target_unit('logic')}",
        ),
    ],
    ids=[
        "exact-two-coven-membership",
        "missing-first-coven",
        "missing-second-coven",
        "missing-own-service",
        "extra-unowned-before",
        "singleton-is-not-a-coven",
        "nonmember-compiled-coven",
        "target-source-still-required",
        "service-source-still-required",
        "coven-source-still-required",
    ],
)
@pytest.mark.asyncio
async def test_members_require_exact_inverse_ordering_for_every_compiled_coven(
    tmp_path: Path, mocker: MockerFixture, unit_name: str, property_name: str, observed: str, error: str
) -> None:
    """Compatible aggregates add exact inverse ordering without broad allowances."""
    groups = {"alpha": ("logic", "review", "singleton"), "beta": ("logic",), "gamma": ("review",)}
    covens = {"logic": ("alpha", "beta"), "review": ("alpha", "gamma")}
    stones = [
        GenericSoulstoneConfig(
            name=name,
            quadlet=QuadletConfig(image=f"example/{name}:latest"),
            groups=memberships,
            concurrency=ConcurrencyIntent(conflict_domains=()),
        )
        for name, memberships in groups.items()
    ]
    graph: dict[str, dict[str, str]] = {}
    for name in groups:
        _add_coexistent_animator(graph, name)
    _attach_owned_sources(graph, tmp_path, *groups)
    sources: list[Path] = []
    for group, names in covens.items():
        unit = coven_target_unit(group)
        source = tmp_path / "systemd" / unit
        sources.append(source)
        members = " ".join(animator_target_unit(name) for name in names)
        graph[unit] = {
            **_blank_properties(unit),
            "Wants": members,
            "After": f"{_POD} {members}",
            "PartOf": _POD,
            "FragmentPath": str(source),
            "UnitFileState": "static",
        }
        for name in names:
            member = graph[animator_target_unit(name)]
            member["Before"] += f" {unit}"
            member["PartOf"] += f" {unit}"
    owned = _owned_bindings(tmp_path, *groups)
    owned = replace(
        owned,
        systemd_sources=(*owned.systemd_sources, *sources),
        runtime_units=(*owned.runtime_units, *(coven_target_unit(group) for group in covens)),
    )
    if unit_name:
        graph[unit_name][property_name] = observed
    _mock_systemctl_show(mocker, graph)
    attestor = RuntimeTopologyAttestor(
        _registry(stones), systemctl_bin=_SYSTEMCTL, owned_bindings_provider=lambda: owned
    )
    if error:
        with pytest.raises(RuntimePreconditionError, match=error):
            await attestor.attest_current_topology()
    else:
        await attestor.attest_current_topology()


@pytest.mark.asyncio
async def test_conflict_closure_mismatch_is_rejected_before_systemd_query(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    stones = [
        _stone("alpha", conflict_domains=["gpu-0"]),
        _stone("beta", conflict_domains=["gpu-0"]),
        _stone("gamma", conflict_domains=[]),
    ]
    subprocess = mocker.patch("lychd.system.services.runtime_topology.asyncio.create_subprocess_exec")
    intent = TransitionIntent(
        transition_id="a" * 32,
        config_generation="sha256:" + "b" * 64,
        target_animator="beta",
        target_capability_key="beta:default",
        evict_animators=("alpha", "gamma"),
        launch_animators=("beta",),
        expected_active_animators=("alpha", "gamma"),
    )

    with pytest.raises(RuntimePreconditionError, match="conflict closure is stale"):
        await RuntimeTopologyAttestor(
            _registry(stones),
            systemctl_bin=_SYSTEMCTL,
            owned_bindings_provider=lambda: _owned_bindings(tmp_path, "alpha", "beta", "gamma"),
        ).attest(intent)

    subprocess.assert_not_awaited()


@pytest.mark.asyncio
async def test_stop_only_compensation_is_accepted_by_public_attestation(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    stone = _stone("beta", conflict_domains=[])
    forward = TransitionIntent(
        transition_id="c" * 32,
        config_generation="sha256:" + "d" * 64,
        target_animator="beta",
        target_capability_key="beta:default",
        launch_animators=("beta",),
    )

    graph: dict[str, dict[str, str]] = {}
    _add_coexistent_animator(graph, "beta")
    _attach_owned_sources(graph, tmp_path, "beta")
    _mock_systemctl_show(mocker, graph)

    await RuntimeTopologyAttestor(
        _registry([stone]),
        systemctl_bin=_SYSTEMCTL,
        owned_bindings_provider=lambda: _owned_bindings(tmp_path, "beta"),
    ).attest(build_compensation_intent(forward))


@pytest.mark.asyncio
async def test_attestation_covers_capability_empty_soulstones(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    stones = [
        _stone("alpha", conflict_domains=["gpu-0"]),
        _stone("beta", conflict_domains=["gpu-0"]),
        _stone("silent", conflict_domains=[]),
    ]
    capabilities = Mock(side_effect=AssertionError("topology must not be capability-derived"))
    graph = _exact_pair_graph()
    _add_coexistent_animator(graph, "silent")
    _attach_owned_sources(graph, tmp_path, "alpha", "beta", "silent")
    _, observed_units = _mock_systemctl_show(mocker, graph)

    await RuntimeTopologyAttestor(
        _registry(stones, list_capabilities=capabilities),
        systemctl_bin=_SYSTEMCTL,
        owned_bindings_provider=lambda: _owned_bindings(tmp_path, "alpha", "beta", "silent"),
    ).attest(_intent())

    capabilities.assert_not_called()
    assert animator_target_unit("silent") in observed_units
    assert animator_service_unit("silent") in observed_units


@pytest.mark.asyncio
async def test_recovery_attests_current_topology_without_fabricating_intent(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    stones = [_stone("alpha", conflict_domains=["gpu-0"]), _stone("beta", conflict_domains=["gpu-0"])]
    graph = _exact_pair_graph()
    _attach_owned_sources(graph, tmp_path, "alpha", "beta")
    subprocess, observed_units = _mock_systemctl_show(mocker, graph)
    await RuntimeTopologyAttestor(
        _registry(stones),
        systemctl_bin=_SYSTEMCTL,
        owned_bindings_provider=lambda: _owned_bindings(tmp_path, "alpha", "beta"),
    ).attest_current_topology()
    assert observed_units == sorted(graph)
    assert subprocess.await_count == len(graph) + 2
