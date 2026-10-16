"""Shared helpers for inert and explicitly opted-in real systemd receipts."""

# ruff: noqa: INP001 - existing tests/support namespace is intentional

from __future__ import annotations

import errno
import os
import re
import stat
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NoReturn

import pytest

from lychd.config import QuadletConfig
from lychd.config.settings.root import Settings
from lychd.domain.animation.schemas import ConcurrencyIntent, GenericSoulstoneConfig
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import Transmuter
from lychd.system.services.scribe import ScribeService

_PROOF_REQUIRED_ENV = "LYCHD_REQUIRE_SYSTEMD_PROOF"
_OUTER_UNIT_ENV = "LYCHD_SYSTEMD_PROOF_OUTER_UNIT"
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
    "LoadState",
    "MainPID",
    "ControlPID",
    "InvocationID",
    "ControlGroup",
    "Result",
    "ExecMainCode",
    "ExecMainStatus",
    "ExecStart",
    "TimeoutStopUSec",
    "KillMode",
    "KillSignal",
    "SendSIGKILL",
    "SuccessExitStatus",
    "Restart",
    "NRestarts",
)


def unavailable(reason: str) -> NoReturn:
    """Skip optional host proof, or fail when the operator requires it."""
    if os.environ.get(_PROOF_REQUIRED_ENV) == "1" or os.environ.get("LYCHD_REQUIRE_QUADLET_PROOF") == "1":
        pytest.fail(reason)
    pytest.skip(reason)


def trusted_binary(name: str, candidates: Sequence[Path]) -> Path | None:
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


def required_binaries() -> dict[str, Path]:
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
        name: binary for name, paths in candidates.items() if (binary := trusted_binary(name, paths)) is not None
    }
    missing = sorted(candidates.keys() - resolved.keys())
    if missing:
        unavailable(f"root-controlled systemd proof binaries are unavailable: {', '.join(missing)}")
    require_delegated_manager_cgroup(resolved["systemctl"])
    return resolved


def require_delegated_manager_cgroup(systemctl: Path) -> dict[str, str]:
    """Refuse a nested manager outside an exclusive, delegated proof service.

    Private HOME and bus paths do not isolate systemd's cgroup effects. A nested
    manager may migrate processes from its inherited cgroup into init.scope.
    Read only the declared outer service in the ordinary manager to attest its
    identity; all nested-manager effects still use their isolated private bus.
    """
    unit = os.environ.get(_OUTER_UNIT_ENV, "")
    if re.fullmatch(r"lychd-(?:bootstrap|proof)-[a-z0-9-]+\.service", unit) is None:
        unavailable(f"private manager requires an explicit unique {_OUTER_UNIT_ENV} delegated service")
    try:
        result = subprocess.run(  # noqa: S603 - attested systemctl, exact declared outer unit, read-only show
            [
                str(systemctl),
                "--user",
                "--no-pager",
                "show",
                unit,
                "--property=Id,ControlGroup,MainPID,InvocationID,Delegate,Transient,ActiveState",
            ],
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
        fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        if result.returncode or set(fields) != {
            "Id",
            "ControlGroup",
            "MainPID",
            "InvocationID",
            "Delegate",
            "Transient",
            "ActiveState",
        }:
            unavailable("cannot attest the declared outer proof service")
        if (
            fields["Id"] != unit
            or fields["Delegate"] != "yes"
            or fields["Transient"] != "yes"
            or fields["ActiveState"] != "active"
            or not fields["InvocationID"]
        ):
            unavailable("outer proof service is not an active delegated invocation")
        relative = Path(fields["ControlGroup"])
        if not relative.is_absolute() or relative.name != unit or ".." in relative.parts:
            unavailable("outer proof service has an unexpected cgroup identity")
        root = Path("/sys/fs/cgroup") / str(relative).lstrip("/")
        metadata = root.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
            unavailable("outer proof cgroup is not an operator-owned directory")
        # systemd v261 writes this informational xattr only for system-manager
        # units (src/core/cgroup.c:cgroup_xattr_apply). A user
        # manager's Delegate=yes is attested below without inventing that xattr.
        delegate_xattr = _delegate_xattr(root)
        if not all(os.access(root / name, os.W_OK) for name in ("cgroup.procs", "cgroup.subtree_control")):
            unavailable("outer proof cgroup delegation or writable control files are unavailable")
        current = Path("/proc/self/cgroup").read_text(encoding="ascii").strip()
        if not current.startswith("0::"):
            unavailable("a unified cgroup identity is required for the private manager")
        caller_group = Path(current.removeprefix("0::"))
        if caller_group not in {relative, relative / "init.scope"}:
            unavailable("caller is outside the declared exclusive outer proof cgroup")
        ancestors = _require_exclusive_cgroup_processes(root, int(fields["MainPID"]))
        return {
            **fields,
            "CallerControlGroup": str(caller_group),
            "CgroupPath": str(root),
            "DelegateXattr": delegate_xattr,
            "AncestorPids": " ".join(map(str, ancestors)),
            **{
                name: (root / name).read_text(encoding="ascii").strip() if (root / name).exists() else "unavailable"
                for name in ("cgroup.controllers", "cgroup.subtree_control", "pids.max", "cpu.max", "memory.max")
            },
        }
    except (OSError, ValueError, subprocess.SubprocessError):
        unavailable("exclusive delegated outer proof cgroup could not be verified")


def _delegate_xattr(root: Path) -> str:
    try:
        return os.getxattr(root, "user.delegate").decode("ascii")
    except OSError as exc:
        if exc.errno != errno.ENODATA:
            raise
        return "unavailable:ENODATA:user-manager"


def _require_exclusive_cgroup_processes(root: Path, main_pid: int) -> tuple[int, ...]:
    ancestors: set[int] = set()
    pid = os.getpid()
    while pid > 1:
        ancestors.add(pid)
        if pid == main_pid:
            break
        process_fields = Path(f"/proc/{pid}/stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
        pid = int(process_fields[1])
    if main_pid <= 1 or main_pid not in ancestors:
        unavailable("outer proof service MainPID is not the caller or its ancestor")
    files = tuple(root.rglob("cgroup.procs"))
    if len(files) > 100:
        unavailable("outer proof cgroup tree exceeds the bounded ownership probe")
    pids = {int(value) for path in files for value in path.read_text(encoding="ascii").split()}
    if not pids.issubset(ancestors):
        unavailable("outer proof cgroup contains a process outside this invocation's ancestor chain")
    return tuple(sorted(ancestors))


def write_harness_units(
    directory: Path,
    *,
    alpha_target: str,
    alpha_service: str,
    beta_target: str,
    beta_service: str,
    marker_name: str,
    binaries: Mapping[str, Path],
    inert_services: bool = True,
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
    if not inert_services:
        del support_units[alpha_service], support_units[beta_service]
    for filename, content in support_units.items():
        (directory / filename).write_text(content, encoding="utf-8")


def inscribe_conflicting_targets(
    *,
    generated_dir: Path,
    quadlet_dir: Path,
    alpha_name: str,
    beta_name: str,
    settings: Settings,
) -> None:
    """Render production targets from two real Soulstones sharing one domain."""
    shared_gpu = ConcurrencyIntent(conflict_domains=("proof-gpu",))
    soulstones = tuple(
        GenericSoulstoneConfig(
            name=name,
            quadlet=QuadletConfig(image="example/runtime"),
            groups=(),
            concurrency=shared_gpu,
        )
        for name in (alpha_name, beta_name)
    )
    manifests = Transmuter(
        settings=settings,
        runtime_planner=RuntimeAdapterRegistry(),
    ).transmute_all(soulstones)
    ScribeService(output_dir=quadlet_dir, systemd_dir=generated_dir).reconcile_all(manifests, plain_units={})


def manager_environment(
    root: Path, generated_dir: Path, harness_dir: Path, *, inherit_environment: bool = True
) -> dict[str, str]:
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

    environment = os.environ.copy() if inherit_environment else {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
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


def run_systemctl(
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


def wait_for_manager(
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
                probe = run_systemctl(systemctl, environment, "show", "-P", "Version", timeout=0.5)
            except subprocess.TimeoutExpired:
                last_diagnostic = "manager property probe timed out"
            else:
                if probe.returncode == 0 and probe.stdout.strip():
                    return ""
                last_diagnostic = (probe.stderr or probe.stdout).strip() or "manager property probe failed"
        time.sleep(0.05)
    return f"private systemd did not become ready in {timeout:.1f}s: {last_diagnostic}"


def wait_for_jobs(
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
            result = run_systemctl(systemctl, environment, "list-jobs", "--no-legend", "--plain", timeout=0.5)
        except subprocess.TimeoutExpired:
            last_output = "list-jobs timed out"
        else:
            last_output = (result.stdout + result.stderr).strip()
            if result.returncode == 0 and unique_stem not in result.stdout:
                return ""
        time.sleep(0.05)
    return f"jobs did not quiesce in {timeout:.1f}s:\n{last_output}"


def read_properties(
    *,
    systemctl: Path,
    environment: Mapping[str, str],
    units: Sequence[str],
) -> dict[str, dict[str, str]]:
    """Read the exact relation and state surface used by runtime attestation."""
    ordered_units = tuple(sorted(units))
    loaded = run_systemctl(systemctl, environment, "show", "--property=Id", *ordered_units)
    assert loaded.returncode == 0, loaded.stderr or loaded.stdout
    result = run_systemctl(
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


def managed_relations(
    properties: Mapping[str, str],
    *,
    managed_units: frozenset[str],
) -> dict[str, frozenset[str]]:
    """Discard systemd's ambient basic/shutdown edges from relation assertions."""
    return {
        relation: frozenset(properties.get(relation, "").split()).intersection(managed_units)
        for relation in _RELATION_PROPERTIES
    }


def assert_initial_topology(
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
        unit: managed_relations(snapshot, managed_units=managed_units) for unit, snapshot in snapshots.items()
    }
    diagnostic = diagnostics(manager_log=manager_log, properties=snapshots)
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


def diagnostics(
    *,
    manager_log: Path,
    properties: Mapping[str, Mapping[str, str]] | None = None,
    command: subprocess.CompletedProcess[str] | None = None,
) -> str:
    """Render bounded evidence when a semantic assertion fails."""
    with manager_log.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        stream.seek(max(0, stream.tell() - 65536))
        log_tail = stream.read().decode("utf-8", errors="replace")
    sections = [f"private manager log (last 64 KiB):\n{log_tail}"]
    if command is not None:
        sections.append(f"systemctl exit={command.returncode}\nstdout:\n{command.stdout}\nstderr:\n{command.stderr}")
    if properties is not None:
        rendered = "\n".join(f"{unit}: {dict(snapshot)}" for unit, snapshot in sorted(properties.items()))
        sections.append(f"unit properties:\n{rendered}")
    return "\n\n".join(sections)


def stop_private_manager(manager: subprocess.Popen[str], runtime_dir: Path) -> None:
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
