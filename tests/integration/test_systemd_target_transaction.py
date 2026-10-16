"""Isolated real-manager receipts for generated systemd topology and transactions."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from lychd.config import QuadletConfig
from lychd.config.settings.root import SettingsSnapshot, get_settings
from lychd.domain.animation.schemas import ConcurrencyIntent, GenericSoulstoneConfig
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import Transmuter
from lychd.system.host_tools import trusted_podman_user_generator_executable
from lychd.system.services.runtime_topology import RuntimeTopologyAttestor
from lychd.system.services.scribe import ScribeService
from lychd.system.unit_names import animator_service_unit, animator_target_unit, coven_target_unit
from tests.support.systemd_transaction import (
    assert_initial_topology,
    diagnostics,
    inscribe_conflicting_targets,
    manager_environment,
    read_properties,
    required_binaries,
    run_systemctl,
    stop_private_manager,
    wait_for_jobs,
    wait_for_manager,
    write_harness_units,
)
from tests.support.systemd_transaction import (
    unavailable as proof_unavailable,
)

if TYPE_CHECKING:
    from lychd.domain.animation.protocols import CapabilityRegistry

pytestmark = pytest.mark.integration


def test_generated_conflict_targets_execute_one_ordered_systemd_transaction(tmp_path: Path) -> None:
    """Prove target relations and conflict switching in an isolated real manager."""
    if sys.platform != "linux":
        proof_unavailable("the real systemd transaction receipt requires Linux")
    binaries = required_binaries()

    token = uuid.uuid4().hex[:10]
    alpha_name = f"proof-{token}-alpha"
    beta_name = f"proof-{token}-beta"
    alpha_target = animator_target_unit(alpha_name)
    beta_target = animator_target_unit(beta_name)
    alpha_service = animator_service_unit(alpha_name)
    beta_service = animator_service_unit(beta_name)
    managed_units = frozenset((alpha_target, alpha_service, beta_target, beta_service))
    marker_name = f"lychd-{token}-alpha-stopped"

    generated_dir = tmp_path / "generated"
    quadlet_dir = tmp_path / "quadlet"
    harness_dir = tmp_path / "harness"
    for directory in (generated_dir, quadlet_dir, harness_dir):
        directory.mkdir()
    inscribe_conflicting_targets(
        generated_dir=generated_dir,
        quadlet_dir=quadlet_dir,
        alpha_name=alpha_name,
        beta_name=beta_name,
        settings=get_settings(),
    )
    write_harness_units(
        harness_dir,
        alpha_target=alpha_target,
        alpha_service=alpha_service,
        beta_target=beta_target,
        beta_service=beta_service,
        marker_name=marker_name,
        binaries=binaries,
    )

    manager_temp = tempfile.TemporaryDirectory(prefix=f"lychd-systemd-{token}-")
    environment = manager_environment(Path(manager_temp.name) / "manager", generated_dir, harness_dir)
    runtime_dir = Path(environment["XDG_RUNTIME_DIR"])
    manager_log = tmp_path / "systemd-manager.log"
    with manager_log.open("w", encoding="utf-8") as log_stream:
        try:
            manager = subprocess.Popen(  # noqa: S603 - the absolute executable is root-owned and pre-attested
                [
                    str(binaries["systemd"]),
                    "--user",
                    f"--unit={alpha_target}",
                    "--log-target=console",
                    "--log-level=warning",
                    "--no-pager",
                ],
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log_stream,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
        except OSError as exc:
            manager_temp.cleanup()
            proof_unavailable(f"isolated user manager could not start: {exc}")
        try:
            unavailable = wait_for_manager(
                manager,
                systemctl=binaries["systemctl"],
                environment=environment,
            )
            if unavailable:
                proof_unavailable(f"isolated user manager is unavailable: {unavailable}")

            unsettled = wait_for_jobs(
                systemctl=binaries["systemctl"],
                environment=environment,
                unique_stem=token,
            )
            assert not unsettled, f"{unsettled}\n{diagnostics(manager_log=manager_log)}"

            initial = read_properties(
                systemctl=binaries["systemctl"],
                environment=environment,
                units=tuple(managed_units),
            )
            assert_initial_topology(
                initial,
                alpha_target=alpha_target,
                alpha_service=alpha_service,
                beta_target=beta_target,
                beta_service=beta_service,
                generated_dir=generated_dir,
                harness_dir=harness_dir,
                manager_log=manager_log,
            )

            switched = run_systemctl(
                binaries["systemctl"],
                environment,
                "start",
                "--job-mode=fail",
                beta_target,
                timeout=5.0,
            )
            assert switched.returncode == 0, diagnostics(
                manager_log=manager_log,
                properties=initial,
                command=switched,
            )
            unsettled = wait_for_jobs(
                systemctl=binaries["systemctl"],
                environment=environment,
                unique_stem=token,
            )
            assert not unsettled, f"{unsettled}\n{diagnostics(manager_log=manager_log)}"

            final = read_properties(
                systemctl=binaries["systemctl"],
                environment=environment,
                units=tuple(managed_units),
            )
            states = {unit: (snapshot["ActiveState"], snapshot["SubState"]) for unit, snapshot in final.items()}
            assert states == {
                alpha_target: ("inactive", "dead"),
                alpha_service: ("inactive", "dead"),
                beta_target: ("active", "active"),
                beta_service: ("active", "exited"),
            }, diagnostics(manager_log=manager_log, properties=final)
            assert (runtime_dir / marker_name).is_file(), diagnostics(
                manager_log=manager_log,
                properties=final,
            )
        finally:
            stop_private_manager(manager, runtime_dir)
            manager_temp.cleanup()


def test_generated_topology_attests_with_real_default_dependencies(  # noqa: PLR0915 - one load-only manager receipt
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Load real generated metadata without starting a Pod or container service.

    The delegated private-manager prerequisite is the same as the target-switch
    proof. Only basic.target starts; the Quadlet generator runs offline, and the
    production attestor reads the complete declared Animator/Coven topology.
    """
    if sys.platform != "linux":
        proof_unavailable("the real default-dependency receipt requires Linux")
    binaries = required_binaries()
    generator = trusted_podman_user_generator_executable()
    if generator is None:
        proof_unavailable("the real default-dependency receipt requires a trusted Quadlet user generator")

    token = uuid.uuid4().hex[:10]
    alpha_name, beta_name, gamma_name = (f"proof-{token}-{suffix}" for suffix in ("alpha", "beta", "gamma"))
    group = f"proof-{token}-logic"
    stones = (
        GenericSoulstoneConfig(
            name=alpha_name,
            quadlet=QuadletConfig(image="example/runtime"),
            groups=(group,),
            concurrency=ConcurrencyIntent(conflict_domains=("proof-gpu",)),
        ),
        GenericSoulstoneConfig(
            name=beta_name,
            quadlet=QuadletConfig(image="example/runtime"),
            concurrency=ConcurrencyIntent(conflict_domains=("proof-gpu",)),
        ),
        GenericSoulstoneConfig(
            name=gamma_name,
            quadlet=QuadletConfig(image="example/runtime"),
            groups=(group,),
            concurrency=ConcurrencyIntent(conflict_domains=()),
        ),
    )
    alpha_target, beta_target, gamma_target = map(animator_target_unit, (alpha_name, beta_name, gamma_name))
    coven = coven_target_unit(group)
    pod = "lychd-pod.service"
    defaults_units = (pod, alpha_target, beta_target, gamma_target, coven)
    quadlet_dir, targets_dir, harness_dir = (tmp_path / name for name in ("quadlet", "targets", "harness"))
    for directory in (quadlet_dir, targets_dir, harness_dir):
        directory.mkdir()
    scribe = ScribeService(output_dir=quadlet_dir, systemd_dir=targets_dir)
    settings = SettingsSnapshot(
        payload=json.dumps(
            {
                "extensions": {"builtins": [], "crypt": []},
                "orchestration": {"switching": {"host_reactor_dir": str(tmp_path / "inbox")}},
            }
        )
    ).materialize()
    scribe.reconcile_all(
        Transmuter(settings=settings, runtime_planner=RuntimeAdapterRegistry()).transmute_all(stones),
        plain_units={},
    )
    owned = scribe.inspect_owned_bindings()
    for unit in ("basic.target", "shutdown.target"):
        (harness_dir / unit).write_text(
            "[Unit]\nDescription=LychD load-only proof support\nDefaultDependencies=no\n", encoding="utf-8"
        )

    manager_log = tmp_path / "systemd-manager.log"
    receipt_path = tmp_path / "default-dependencies.json"
    with tempfile.TemporaryDirectory(prefix=f"lychd-defaults-{token}-") as manager_root:
        environment = manager_environment(
            Path(manager_root) / "manager", targets_dir, harness_dir, inherit_environment=False
        )
        runtime_dir = Path(environment["XDG_RUNTIME_DIR"])
        generated_dir = runtime_dir / "systemd" / "generator"
        generated_dir.mkdir(parents=True)
        environment["SYSTEMD_UNIT_PATH"] = f"{targets_dir}:{generated_dir}:{harness_dir}"
        environment["QUADLET_UNIT_DIRS"] = str(quadlet_dir)
        generated = subprocess.run(  # noqa: S603 - attested offline generator; never start generated services
            [generator.path, "--user", str(generated_dir)],
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
        )
        assert generated.returncode == 0, generated.stdout + generated.stderr
        assert all((generated_dir / unit).is_file() for unit in owned.runtime_units if unit.endswith(".service"))
        with manager_log.open("w", encoding="utf-8") as log_stream:
            manager = subprocess.Popen(  # noqa: S603 - admitted private manager; never start generated units
                [
                    str(binaries["systemd"]),
                    "--user",
                    "--unit=basic.target",
                    "--log-target=console",
                    "--log-level=warning",
                    "--no-pager",
                ],
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log_stream,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
            try:
                unavailable = wait_for_manager(manager, systemctl=binaries["systemctl"], environment=environment)
                if unavailable:
                    proof_unavailable(f"isolated default-dependency manager is unavailable: {unavailable}")
                initial = read_properties(
                    systemctl=binaries["systemctl"], environment=environment, units=owned.runtime_units
                )
                defaults_result = run_systemctl(
                    binaries["systemctl"], environment, "show", "--property=Id,DefaultDependencies", *defaults_units
                )
                assert defaults_result.returncode == 0, defaults_result.stderr
                defaults: dict[str, str] = {}
                for block in defaults_result.stdout.strip().split("\n\n"):
                    fields = dict(line.split("=", 1) for line in block.splitlines())
                    assert set(fields) == {"Id", "DefaultDependencies"}, fields
                    assert fields["Id"] not in defaults, fields
                    defaults[fields["Id"]] = fields["DefaultDependencies"]
                receipt = {
                    "kind": "real-systemd-load-only-default-dependency-topology",
                    "defaults": defaults,
                    "loaded_units": initial,
                    "scribe_generation": owned.generation,
                    "attested": False,
                }
                receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                assert defaults == dict.fromkeys(defaults_units, "yes"), defaults
                assert Path(initial[pod]["FragmentPath"]) == generated_dir / pod
                assert pod in initial[alpha_target]["After"].split()
                assert {pod, alpha_target} <= set(initial[beta_target]["After"].split())
                assert {pod, alpha_target, gamma_target} <= set(initial[coven]["After"].split())

                # The read-only attestor consumes only declaration truth. No
                # runtime construction, capability warmth or model probes occur.
                registry = cast("CapabilityRegistry", SimpleNamespace(list_soulstone_runes=lambda: list(stones)))
                with monkeypatch.context() as private_bus:
                    for name in tuple(os.environ):
                        private_bus.delenv(name)
                    for name, value in environment.items():
                        private_bus.setenv(name, value)
                    asyncio.run(
                        RuntimeTopologyAttestor(
                            registry,
                            systemctl_bin=str(binaries["systemctl"]),
                            systemctl_timeout_s=3.0,
                            owned_bindings_provider=scribe.inspect_owned_bindings,
                        ).attest_current_topology()
                    )
                expected_after = {
                    alpha_target: [pod],
                    beta_target: [pod, alpha_target],
                    gamma_target: [pod],
                    coven: [pod, alpha_target, gamma_target],
                }
                for unit, after in expected_after.items():
                    assert f"After={' '.join(after)}" in (targets_dir / unit).read_text(encoding="utf-8").splitlines()
                final = read_properties(
                    systemctl=binaries["systemctl"], environment=environment, units=owned.runtime_units
                )
                assert all(
                    properties["ActiveState"] == "inactive" and properties["InvocationID"] in {"", "0" * 32}
                    for observations in (initial, final)
                    for properties in observations.values()
                ), (initial, final)
                # Process properties belong to services. Real target metadata
                # omits them; absence on a service must still fail the proof.
                assert all(
                    properties["MainPID"] == "0" and properties["ControlPID"] == "0"
                    for observations in (initial, final)
                    for unit, properties in observations.items()
                    if unit.endswith(".service")
                ), (initial, final)
                assert all(
                    "MainPID" not in properties and "ControlPID" not in properties
                    for observations in (initial, final)
                    for unit, properties in observations.items()
                    if unit.endswith(".target")
                ), (initial, final)
                assert all(
                    properties["NRestarts"] == "0"
                    for observations in (initial, final)
                    for unit, properties in observations.items()
                    if unit.endswith(".service")
                ), (initial, final)
                receipt.update({"attested": True, "loaded_units_after_attestation": final})
                receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            finally:
                stop_private_manager(manager, runtime_dir)
