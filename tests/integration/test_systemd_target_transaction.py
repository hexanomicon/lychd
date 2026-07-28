"""Hermetic receipt for LychD's generated systemd target transaction."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NoReturn

import pytest

from lychd.config.settings.root import get_settings
from lychd.domain.animation.schemas import ConcurrencyIntent, GenericSoulstoneConfig
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import Transmuter
from lychd.system.services.scribe import ScribeService
from lychd.system.unit_names import animator_service_unit, animator_target_unit

pytestmark = pytest.mark.integration

_PROOF_REQUIRED_ENV = "LYCHD_REQUIRE_SYSTEMD_PROOF"
_RELATION_PROPERTIES = (
    "Requires",
    "RequiredBy",
    "BindsTo",
    "BoundBy",
    "Before",
    "After",
    "Conflicts",
    "ConflictedBy",
    "PartOf",
)
_SHOW_PROPERTIES = (
    "Id",
    "FragmentPath",
    *_RELATION_PROPERTIES,
    "ActiveState",
    "SubState",
)


def _unavailable(reason: str) -> NoReturn:
    """Skip optional host proof, or fail when the operator requires it."""
    if os.environ.get(_PROOF_REQUIRED_ENV) == "1":
        pytest.fail(reason)
    pytest.skip(reason)


def _trusted_binary(name: str, candidates: Sequence[Path]) -> Path | None:
    """Resolve one root-owned binary that an unprivileged user cannot replace."""
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
            metadata = resolved.stat()
        except OSError:
            continue
        if (
            stat.S_ISREG(metadata.st_mode)
            and metadata.st_uid == 0
            and metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH) == 0
        ):
            return resolved
    return None


def _required_binaries() -> dict[str, Path]:
    """Resolve every executable used by the private-manager harness."""
    candidates = {
        "systemd": (
            Path("/usr/lib/systemd/systemd"),
            Path("/lib/systemd/systemd"),
            Path("/usr/bin/systemd"),
        ),
        "systemctl": (Path("/usr/bin/systemctl"), Path("/bin/systemctl")),
        "sleep": (Path("/usr/bin/sleep"), Path("/bin/sleep")),
        "test": (Path("/usr/bin/test"), Path("/bin/test")),
        "touch": (Path("/usr/bin/touch"), Path("/bin/touch")),
        "true": (Path("/usr/bin/true"), Path("/bin/true")),
    }
    resolved = {
        name: binary for name, paths in candidates.items() if (binary := _trusted_binary(name, paths)) is not None
    }
    missing = sorted(candidates.keys() - resolved.keys())
    if missing:
        _unavailable(f"root-controlled systemd proof binaries are unavailable: {', '.join(missing)}")
    return resolved


def _write_harness_units(
    directory: Path,
    *,
    alpha_target: str,
    alpha_service: str,
    beta_target: str,
    beta_service: str,
    marker_name: str,
    binaries: Mapping[str, Path],
) -> None:
    """Write inert services and the minimal user-manager support units."""
    support_units = {
        "basic.target": "[Unit]\nDescription=LychD proof basic target\nDefaultDependencies=no\n",
        "shutdown.target": "[Unit]\nDescription=LychD proof shutdown target\nDefaultDependencies=no\n",
        "lychd-pod.service": (
            "[Unit]\n"
            "Description=LychD proof inert pod\n"
            "DefaultDependencies=no\n"
            "[Service]\n"
            "Type=oneshot\n"
            f"ExecStart={binaries['true']}\n"
            "RemainAfterExit=yes\n"
        ),
        alpha_service: (
            "[Unit]\n"
            "Description=LychD proof alpha Animator\n"
            f"BindsTo={alpha_target}\n"
            f"After={alpha_target}\n"
            "[Service]\n"
            "Type=oneshot\n"
            f"ExecStart={binaries['true']}\n"
            f"ExecStop={binaries['sleep']} 0.15\n"
            f'ExecStop={binaries["touch"]} "%t/{marker_name}"\n'
            "RemainAfterExit=yes\n"
        ),
        beta_service: (
            "[Unit]\n"
            "Description=LychD proof beta Animator\n"
            f"BindsTo={beta_target}\n"
            f"After={beta_target}\n"
            "[Service]\n"
            "Type=oneshot\n"
            f'ExecStart={binaries["test"]} -f "%t/{marker_name}"\n'
            "RemainAfterExit=yes\n"
        ),
    }
    for filename, content in support_units.items():
        (directory / filename).write_text(content, encoding="utf-8")


def _inscribe_conflicting_targets(
    *,
    generated_dir: Path,
    quadlet_dir: Path,
    alpha_name: str,
    beta_name: str,
) -> None:
    """Render production targets from two real Soulstones sharing one domain."""
    shared_gpu = ConcurrencyIntent(conflict_domains=["proof-gpu"])
    soulstones = tuple(
        GenericSoulstoneConfig(
            name=name,
            image="example/runtime",
            groups=[],
            concurrency=shared_gpu,
        )
        for name in (alpha_name, beta_name)
    )
    manifests = Transmuter(
        settings=get_settings(),
        runtime_planner=RuntimeAdapterRegistry(),
    ).transmute_all(soulstones)
    ScribeService(output_dir=quadlet_dir, systemd_dir=generated_dir).generate_all(manifests)


def _manager_environment(root: Path, generated_dir: Path, harness_dir: Path) -> dict[str, str]:
    """Build a bus and filesystem environment isolated from the live user manager."""
    root.mkdir()
    runtime_dir = root / "runtime"
    home_dir = root / "home"
    config_dir = root / "config"
    cache_dir = root / "cache"
    data_dir = root / "data"
    for directory in (runtime_dir, home_dir, config_dir, cache_dir, data_dir):
        directory.mkdir()
        directory.chmod(0o700)

    environment = os.environ.copy()
    environment.pop("DBUS_SESSION_BUS_ADDRESS", None)
    environment.update(
        {
            "HOME": str(home_dir),
            "XDG_RUNTIME_DIR": str(runtime_dir),
            "XDG_CONFIG_HOME": str(config_dir),
            "XDG_CACHE_HOME": str(cache_dir),
            "XDG_DATA_HOME": str(data_dir),
            "SYSTEMD_UNIT_PATH": f"{generated_dir}:{harness_dir}",
            "SYSTEMD_GENERATOR_PATH": "",
            "SYSTEMD_ENVIRONMENT_GENERATOR_PATH": "",
        }
    )
    return environment


def _systemctl(
    binary: Path,
    environment: Mapping[str, str],
    *arguments: str,
    timeout: float = 3.0,
) -> subprocess.CompletedProcess[str]:
    """Call only the private manager selected by the supplied environment."""
    return subprocess.run(  # noqa: S603 - the absolute executable is root-owned and pre-attested
        [str(binary), "--user", "--no-pager", *arguments],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _wait_for_manager(
    manager: subprocess.Popen[str],
    *,
    systemctl: Path,
    environment: Mapping[str, str],
    timeout: float = 5.0,
) -> str:
    """Wait until the isolated private bus answers a manager property probe."""
    socket = Path(environment["XDG_RUNTIME_DIR"]) / "systemd" / "private"
    deadline = time.monotonic() + timeout
    last_diagnostic = "private socket not created"
    while time.monotonic() < deadline:
        return_code = manager.poll()
        if return_code is not None:
            return f"private systemd exited with status {return_code}"
        if socket.exists():
            try:
                probe = _systemctl(systemctl, environment, "show", "-P", "Version", timeout=0.5)
            except subprocess.TimeoutExpired:
                last_diagnostic = "manager property probe timed out"
            else:
                if probe.returncode == 0 and probe.stdout.strip():
                    return ""
                last_diagnostic = (probe.stderr or probe.stdout).strip() or "manager property probe failed"
        time.sleep(0.05)
    return f"private systemd did not become ready in {timeout:.1f}s: {last_diagnostic}"


def _wait_for_jobs(
    *,
    systemctl: Path,
    environment: Mapping[str, str],
    unique_stem: str,
    timeout: float = 5.0,
) -> str:
    """Poll until the private manager has no job for this proof's unique units."""
    deadline = time.monotonic() + timeout
    last_output = ""
    while time.monotonic() < deadline:
        try:
            result = _systemctl(systemctl, environment, "list-jobs", "--no-legend", "--plain", timeout=0.5)
        except subprocess.TimeoutExpired:
            last_output = "list-jobs timed out"
        else:
            last_output = (result.stdout + result.stderr).strip()
            if result.returncode == 0 and unique_stem not in result.stdout:
                return ""
        time.sleep(0.05)
    return f"jobs did not quiesce in {timeout:.1f}s:\n{last_output}"


def _read_properties(
    *,
    systemctl: Path,
    environment: Mapping[str, str],
    units: Sequence[str],
) -> dict[str, dict[str, str]]:
    """Read the exact relation and state surface used by runtime attestation."""
    ordered_units = tuple(sorted(units))
    loaded = _systemctl(systemctl, environment, "show", "--property=Id", *ordered_units)
    assert loaded.returncode == 0, loaded.stderr or loaded.stdout
    result = _systemctl(
        systemctl,
        environment,
        "show",
        f"--property={','.join(_SHOW_PROPERTIES)}",
        *ordered_units,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    snapshots: dict[str, dict[str, str]] = {}
    for block in result.stdout.strip().split("\n\n"):
        properties = dict(line.split("=", 1) for line in block.splitlines() if "=" in line)
        unit_id = properties.get("Id")
        if unit_id:
            snapshots[unit_id] = properties
    assert set(snapshots) == set(ordered_units), result.stdout
    return snapshots


def _managed_relations(
    properties: Mapping[str, str],
    *,
    managed_units: frozenset[str],
) -> dict[str, frozenset[str]]:
    """Discard systemd's ambient basic/shutdown edges from relation assertions."""
    return {
        relation: frozenset(properties.get(relation, "").split()).intersection(managed_units)
        for relation in _RELATION_PROPERTIES
    }


def _assert_initial_topology(
    snapshots: Mapping[str, Mapping[str, str]],
    *,
    alpha_target: str,
    alpha_service: str,
    beta_target: str,
    beta_service: str,
    generated_dir: Path,
    harness_dir: Path,
    manager_log: Path,
) -> None:
    """Assert LychD's intended relations against systemd's loaded relation surface."""
    managed_units = frozenset((alpha_target, alpha_service, beta_target, beta_service))
    empty: frozenset[str] = frozenset()
    expected_relations = {
        alpha_target: {
            "Requires": frozenset((alpha_service,)),
            "RequiredBy": empty,
            "BindsTo": empty,
            "BoundBy": frozenset((alpha_service,)),
            # systemd exposes Before=/Conflicts= as declared on the forward
            # endpoint; it does not synthesize inverse Before/ConflictedBy
            # properties for beta's After=/Conflicts= declaration.
            "Before": frozenset((alpha_service,)),
            "After": empty,
            "Conflicts": empty,
            "ConflictedBy": empty,
            "PartOf": empty,
        },
        beta_target: {
            "Requires": frozenset((beta_service,)),
            "RequiredBy": empty,
            "BindsTo": empty,
            "BoundBy": frozenset((beta_service,)),
            "Before": frozenset((beta_service,)),
            "After": frozenset((alpha_target,)),
            "Conflicts": frozenset((alpha_target,)),
            "ConflictedBy": empty,
            "PartOf": empty,
        },
        alpha_service: {
            "Requires": empty,
            "RequiredBy": frozenset((alpha_target,)),
            "BindsTo": frozenset((alpha_target,)),
            "BoundBy": empty,
            "Before": empty,
            "After": frozenset((alpha_target,)),
            "Conflicts": empty,
            "ConflictedBy": empty,
            "PartOf": empty,
        },
        beta_service: {
            "Requires": empty,
            "RequiredBy": frozenset((beta_target,)),
            "BindsTo": frozenset((beta_target,)),
            "BoundBy": empty,
            "Before": empty,
            "After": frozenset((beta_target,)),
            "Conflicts": empty,
            "ConflictedBy": empty,
            "PartOf": empty,
        },
    }
    actual_relations = {
        unit: _managed_relations(snapshot, managed_units=managed_units) for unit, snapshot in snapshots.items()
    }
    diagnostic = _diagnostics(manager_log=manager_log, properties=snapshots)
    assert actual_relations == expected_relations, diagnostic
    assert Path(snapshots[alpha_target]["FragmentPath"]) == generated_dir / alpha_target, diagnostic
    assert Path(snapshots[beta_target]["FragmentPath"]) == generated_dir / beta_target, diagnostic
    assert Path(snapshots[alpha_service]["FragmentPath"]) == harness_dir / alpha_service, diagnostic
    assert Path(snapshots[beta_service]["FragmentPath"]) == harness_dir / beta_service, diagnostic
    assert snapshots[alpha_target]["PartOf"].split() == ["lychd-pod.service"], diagnostic
    assert snapshots[beta_target]["PartOf"].split() == ["lychd-pod.service"], diagnostic
    assert (
        snapshots[alpha_target]["ActiveState"],
        snapshots[alpha_service]["ActiveState"],
    ) == ("active", "active"), diagnostic
    assert (
        snapshots[beta_target]["ActiveState"],
        snapshots[beta_service]["ActiveState"],
    ) == ("inactive", "inactive"), diagnostic


def _diagnostics(
    *,
    manager_log: Path,
    properties: Mapping[str, Mapping[str, str]] | None = None,
    command: subprocess.CompletedProcess[str] | None = None,
) -> str:
    """Render bounded evidence when a semantic assertion fails."""
    sections = [f"private manager log:\n{manager_log.read_text(encoding='utf-8', errors='replace')}"]
    if command is not None:
        sections.append(f"systemctl exit={command.returncode}\nstdout:\n{command.stdout}\nstderr:\n{command.stderr}")
    if properties is not None:
        rendered = "\n".join(f"{unit}: {dict(snapshot)}" for unit, snapshot in sorted(properties.items()))
        sections.append(f"unit properties:\n{rendered}")
    return "\n\n".join(sections)


def _stop_private_manager(manager: subprocess.Popen[str], runtime_dir: Path) -> None:
    """Terminate only the child manager and reopen its cleanup-hostile sentinel."""
    if manager.poll() is None:
        manager.terminate()
        try:
            manager.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            manager.kill()
            manager.wait(timeout=2.0)
    inaccessible = runtime_dir / "systemd" / "inaccessible"
    if os.path.lexists(inaccessible):
        inaccessible.chmod(0o700, follow_symlinks=False)
        for directory, children, _files in os.walk(inaccessible):
            for child in children:
                Path(directory, child).chmod(0o700, follow_symlinks=False)


def test_generated_conflict_targets_execute_one_ordered_systemd_transaction(tmp_path: Path) -> None:
    """Prove target relations and conflict switching in an isolated real manager."""
    if sys.platform != "linux":
        _unavailable("the real systemd transaction receipt requires Linux")
    binaries = _required_binaries()

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
    _inscribe_conflicting_targets(
        generated_dir=generated_dir,
        quadlet_dir=quadlet_dir,
        alpha_name=alpha_name,
        beta_name=beta_name,
    )
    _write_harness_units(
        harness_dir,
        alpha_target=alpha_target,
        alpha_service=alpha_service,
        beta_target=beta_target,
        beta_service=beta_service,
        marker_name=marker_name,
        binaries=binaries,
    )

    manager_temp = tempfile.TemporaryDirectory(prefix=f"lychd-systemd-{token}-")
    environment = _manager_environment(Path(manager_temp.name) / "manager", generated_dir, harness_dir)
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
            _unavailable(f"isolated user manager could not start: {exc}")
        try:
            unavailable = _wait_for_manager(
                manager,
                systemctl=binaries["systemctl"],
                environment=environment,
            )
            if unavailable:
                _unavailable(f"isolated user manager is unavailable: {unavailable}")

            unsettled = _wait_for_jobs(
                systemctl=binaries["systemctl"],
                environment=environment,
                unique_stem=token,
            )
            assert not unsettled, f"{unsettled}\n{_diagnostics(manager_log=manager_log)}"

            initial = _read_properties(
                systemctl=binaries["systemctl"],
                environment=environment,
                units=tuple(managed_units),
            )
            _assert_initial_topology(
                initial,
                alpha_target=alpha_target,
                alpha_service=alpha_service,
                beta_target=beta_target,
                beta_service=beta_service,
                generated_dir=generated_dir,
                harness_dir=harness_dir,
                manager_log=manager_log,
            )

            switched = _systemctl(
                binaries["systemctl"],
                environment,
                "start",
                "--job-mode=fail",
                beta_target,
                timeout=5.0,
            )
            assert switched.returncode == 0, _diagnostics(
                manager_log=manager_log,
                properties=initial,
                command=switched,
            )
            unsettled = _wait_for_jobs(
                systemctl=binaries["systemctl"],
                environment=environment,
                unique_stem=token,
            )
            assert not unsettled, f"{unsettled}\n{_diagnostics(manager_log=manager_log)}"

            final = _read_properties(
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
            }, _diagnostics(manager_log=manager_log, properties=final)
            assert (runtime_dir / marker_name).is_file(), _diagnostics(
                manager_log=manager_log,
                properties=final,
            )
        finally:
            _stop_private_manager(manager, runtime_dir)
            manager_temp.cleanup()
