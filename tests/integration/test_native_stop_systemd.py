"""Opt-in native stop settlement through an isolated, real systemd user manager.

One finite proof runs required-close failure, clean closure, and reference loss. It uses
the actual generated native unit, CLI, owned lifespan, signed HTTP admission,
Scribe ownership, inventory and controller. The explicit inert factory and local
installation shim do not qualify an installed production graph or model body.
No host user-manager fallback, installed units, or inherited environment is used.
Receipts and credentials belong to an explicit basetemp outside the checkout.
"""

from __future__ import annotations

import errno
import hashlib
import importlib.metadata
import json
import os
import secrets
import shutil
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Generator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from dbus_fast.aio import MessageBus
from pydantic import SecretStr

from lychd.config.settings.root import SettingsSnapshot
from lychd.system.operator import stop_evidence
from lychd.system.operator.admission_client import StopAdmissionClient
from lychd.system.operator.control import OperatorControlService
from lychd.system.operator.inventory import ConfiguredAnimatorDeclarations, OperatorInventoryService, OperatorPaths
from lychd.system.operator.models import OperatorAction, OperatorError, OperatorTarget, VesselAuthority
from lychd.system.operator.process import ProcessInvocationError, ProcessResult
from lychd.system.operator.storage import StorageInventoryService
from lychd.system.operator.targets import OperatorTargetResolver
from lychd.system.operator.units import OwnedUnitInventoryService
from lychd.system.schemas import systemd_executable_token
from lychd.system.services import bind_compilation
from lychd.system.services.lifecycle.lock import LifecycleLock
from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore
from lychd.system.services.local_access import LocalAccess
from lychd.system.services.scribe import ScribeService
from tests.support.native_stop_bus import NativeStopBus, broker_binaries, prepare_bus
from tests.support.systemd_transaction import (
    manager_environment,
    read_properties,
    require_delegated_manager_cgroup,
    required_binaries,
    run_systemctl,
    stop_private_manager,
    wait_for_jobs,
    wait_for_manager,
)
from tests.support.systemd_transaction import unavailable as proof_unavailable

pytestmark = pytest.mark.integration

_VESSEL = "lychd-uncaged-vessel.service"
_REPOSITORY = Path(__file__).resolve().parents[2]
_FIXTURE = _REPOSITORY / "tests/fixtures/web/systemd_server_app.py"
_CONTROL_OUTER_SECONDS = 45.0
_LISTENER_SECONDS = 10.0
_OBSERVATION_SECONDS = 5.0
_OUTPUT_BYTES = 65536
_SOURCES = (
    "pyproject.toml",
    "uv.lock",
    "src/lychd/__main__.py",
    "src/lychd/app.py",
    "src/lychd/config/constants.py",
    "src/lychd/interface/server.py",
    "src/lychd/interface/server_policy.py",
    "src/lychd/interface/api/lifecycle.py",
    "src/lychd/domain/codex/local_access.py",
    "src/lychd/system/operator/admission.py",
    "src/lychd/system/operator/admission_client.py",
    "src/lychd/system/operator/control.py",
    "src/lychd/system/operator/stop_evidence.py",
    "src/lychd/system/operator/units.py",
    "src/lychd/system/operator/inventory.py",
    "src/lychd/system/operator/targets.py",
    "src/lychd/system/services/bind_compilation.py",
    "src/lychd/system/services/lifecycle/lock.py",
    "src/lychd/system/schemas.py",
    "tests/support/systemd_transaction.py",
    "tests/support/native_stop_bus.py",
    "tests/fixtures/web/systemd_server_app.py",
    "tests/integration/test_native_stop_systemd.py",
)
_CLEAN_EXIT = {
    "Id": _VESSEL,
    "LoadState": "loaded",
    "ActiveState": "inactive",
    "SubState": "dead",
    "MainPID": "0",
    "ControlPID": "0",
    "Result": "success",
    "ExecMainCode": "1",
    "ExecMainStatus": "0",
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


@dataclass(frozen=True)
class _Process:
    pid: int
    starttime: int
    pgid: int
    session: int
    parent: int
    state: str
    cgroup: str


def _process(pid: int) -> _Process | None:
    try:
        directory = Path("/proc") / str(pid)
        assert directory.stat().st_uid == os.getuid()
        fields = (directory / "stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
        return _Process(
            pid=pid,
            starttime=int(fields[19]),
            pgid=int(fields[2]),
            session=int(fields[3]),
            parent=int(fields[1]),
            state=fields[0],
            cgroup=(directory / "cgroup").read_text(encoding="ascii"),
        )
    except (FileNotFoundError, ProcessLookupError):
        return None


def _same_process(expected: _Process) -> bool:
    actual = _process(expected.pid)
    return actual is not None and actual.starttime == expected.starttime


def _group(pgid: int) -> dict[int, _Process]:
    assert pgid > 1
    assert pgid != os.getpgrp()
    result: dict[int, _Process] = {}
    for directory in Path("/proc").iterdir():
        try:
            if not directory.name.isdigit() or directory.stat().st_uid != os.getuid():
                continue
            process = _process(int(directory.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
        if process is not None and process.pgid == pgid:
            result[process.pid] = process
    return result


def _cgroup_members(control_group: str) -> tuple[int, ...] | None:
    if not control_group:
        return None
    relative = Path(control_group)
    assert relative.is_absolute()
    assert ".." not in relative.parts
    assert relative.name == _VESSEL
    directory = Path("/sys/fs/cgroup") / control_group.lstrip("/")
    if not directory.exists():
        return ()
    files = tuple(directory.rglob("cgroup.procs"))
    assert len(files) <= 100
    pids = {int(pid) for path in files for pid in path.read_text(encoding="ascii").split()}
    assert len(pids) <= 128
    return tuple(sorted(pids))


@dataclass
class _Manager:
    process: subprocess.Popen[str]
    identity: _Process
    environment: dict[str, str]
    binaries: Mapping[str, Path]
    root: Path
    units: tuple[str, ...]
    outer_group: str
    ancestors: tuple[_Process, ...]
    bus: NativeStopBus
    calls: list[dict[str, object]] = field(default_factory=list)
    deadline: float | None = None
    reference_held: bool = False
    reference_buses: list[MessageBus] = field(default_factory=list)
    lose_reference: bool = False
    loss_event: dict[str, object] | None = None

    def attest(self) -> None:
        assert self.process.poll() is None, "private manager exited"
        assert _same_process(self.identity), "private manager identity changed"
        assert Path(f"/proc/{self.process.pid}/exe").resolve() == self.binaries["systemd"]
        current = _process(self.process.pid)
        assert current is not None
        assert Path(current.cgroup.strip().removeprefix("0::")).is_relative_to(self.outer_group)
        assert self.environment["DBUS_SESSION_BUS_ADDRESS"] == self.bus.address
        assert self.environment["DBUS_SYSTEM_BUS_ADDRESS"] == f"unix:path={self.bus.runtime / 'disabled-system-bus'}"
        runtime = Path(self.environment["XDG_RUNTIME_DIR"])
        metadata = runtime.lstat()
        assert stat.S_ISDIR(metadata.st_mode)
        assert stat.S_IMODE(metadata.st_mode) == 0o700
        assert metadata.st_uid == os.getuid()
        assert runtime.parent.name == "manager"
        assert runtime.parent.parent.name.startswith("lns-")
        assert stat.S_ISDIR((runtime / "systemd").lstat().st_mode)
        private = runtime / "systemd/private"
        metadata = private.lstat()
        assert stat.S_ISSOCK(metadata.st_mode)
        assert metadata.st_uid == os.getuid()
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(0.5)
            connection.connect(str(private))
            peer = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        assert peer == (self.process.pid, os.getuid(), os.getgid()), "private bus is not owned by the child manager"

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        self.attest()
        assert argv[:2] == (str(self.binaries["systemctl"]), "--user")
        assert argv[2] in {"show", "stop", "list-jobs"}
        assert all(not argument.endswith(".service") or argument in self.units for argument in argv[3:])
        if self.deadline is not None:
            timeout_s = min(timeout_s, self.deadline - time.monotonic())
        if timeout_s <= 0:
            message = "private controller observation window expired"
            raise ProcessInvocationError(message)
        call: dict[str, object] = {
            "argv": argv,
            "timeout_s": timeout_s,
            "monotonic_ns": time.monotonic_ns(),
            "reference_held": self.reference_held,
        }
        self.calls.append(call)
        try:
            with tempfile.TemporaryFile(dir=self.root) as stdout, tempfile.TemporaryFile(dir=self.root) as stderr:
                completed = subprocess.run(  # noqa: S603 - attested binary and closed private-manager argv
                    argv,
                    env=self.environment,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    timeout=timeout_s,
                    check=False,
                )
                stdout.seek(0)
                stderr.seek(0)
                out, err = stdout.read(_OUTPUT_BYTES + 1), stderr.read(_OUTPUT_BYTES + 1)
            assert len(out) <= _OUTPUT_BYTES, "private systemctl stdout exceeded budget"
            assert len(err) <= _OUTPUT_BYTES, "private systemctl stderr exceeded budget"
        except (OSError, subprocess.SubprocessError) as exc:
            call["error"] = type(exc).__name__
            message = "private systemctl invocation failed or timed out"
            raise ProcessInvocationError(message) from exc
        call.update(returncode=completed.returncode, stdout=out.decode(), stderr=err.decode())
        if "--property=ExecMainCode" in argv:
            assert self.reference_held
            assert len(self.reference_buses) == 1
            reference_bus = self.reference_buses[0]
            assert reference_bus.connected
            fields = dict(line.split("=", 1) for line in out.decode().splitlines())
            call["terminal_fields"] = fields
            call["reference_unique_name"] = reference_bus.unique_name
            call["terminal_capture_ns"] = time.monotonic_ns()
            if self.lose_reference:
                assert fields == _CLEAN_EXIT
                assert self.loss_event is None
                # This shuts down the actual production bus socket. The next
                # production verify must refuse the real lost connection.
                reference_bus.disconnect()
                self.loss_event = {
                    "monotonic_ns": time.monotonic_ns(),
                    "reference_unique_name": reference_bus.unique_name,
                    "connected_after_disconnect": reference_bus.connected,
                }
        return ProcessResult(argv, completed.returncode, out.decode(), err.decode())


@contextmanager
def _control_deadline() -> Generator[None]:
    def expired(signum: int, frame: object) -> None:
        del signum, frame
        message = "native controller exceeded its declared 45-second outer window"
        raise TimeoutError(message)

    previous = signal.signal(signal.SIGALRM, expired)
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    signal.setitimer(signal.ITIMER_REAL, _CONTROL_OUTER_SECONDS)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return cast("int", listener.getsockname()[1])


def _listener_absent(port: int) -> bool:
    with socket.socket() as connection:
        connection.settimeout(0.2)
        result = connection.connect_ex(("127.0.0.1", port))
    assert result in {0, errno.ECONNREFUSED}, f"listener absence is unknown: {result}"
    return result == errno.ECONNREFUSED


def _private_listener_absent(runtime: Path) -> bool:
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(0.2)
        result = connection.connect_ex(str(runtime / "systemd/private"))
    assert result in {0, errno.ECONNREFUSED, errno.ENOENT}, f"private listener absence is unknown: {result}"
    return result != 0


def _ready(manager: _Manager, port: int, token: str) -> None:
    deadline = time.monotonic() + _LISTENER_SECONDS
    with httpx.Client(trust_env=False, follow_redirects=False, timeout=0.5) as client:
        while time.monotonic() < deadline:
            manager.attest()
            try:
                reply = client.get(f"http://127.0.0.1:{port}/ready")
            except httpx.TransportError:
                time.sleep(0.05)
                continue
            assert reply.status_code == 200, "unready listener"
            assert reply.json() == {"marker": token}, "foreign listener"
            return
    pytest.fail("synthetic native listener did not become ready in 10 seconds")


def _inventory(scribe: ScribeService, manager: _Manager) -> OperatorInventoryService:
    paths = OperatorPaths(
        *(
            manager.root / name
            for name in ("codex", "config", "receipt", "runes", "quadlet", "generated", "storage", "snapshots")
        )
    )
    return OperatorInventoryService(
        paths=paths,
        receipt=LifecycleReceiptStore(paths.receipt),
        units=OwnedUnitInventoryService(scribe, manager, systemctl_bin=str(manager.binaries["systemctl"])),
        storage=StorageInventoryService(manager, findmnt_bin=None),
        animators=ConfiguredAnimatorDeclarations(runes_dir=paths.runes),
    )


def _prepare(
    root: Path, case: str, token: str, port: int, binaries: Mapping[str, Path], monkeypatch: pytest.MonkeyPatch
) -> tuple[ScribeService, dict[str, str], tuple[str, ...], dict[str, object], NativeStopBus]:
    generated, quadlet, harness = (root / name for name in ("generated", "quadlet", "harness"))
    installation = root / "installation"
    for directory in (generated, quadlet, harness, installation / "bin"):
        directory.mkdir(parents=True, mode=0o700)
    credential = root / "credential"
    with credential.open("x", encoding="ascii") as stream:
        credential.chmod(0o600)
        stream.write(secrets.token_urlsafe(32))
    events = root / "events.jsonl"
    events.touch(mode=0o600)
    config = root / "fixture.json"
    _write_json(
        config,
        {
            "case": "clean" if case == "reference-loss" else case,
            "token": token,
            "port": port,
            "credential_path": str(credential),
            "events_path": str(events),
        },
    )
    shim = installation / "bin/lychd"
    shim.write_text(
        f"#!{sys.executable}\nimport runpy\nrunpy.run_path({_FIXTURE.as_posix()!r}, run_name='__main__', init_globals={{'CONFIG_PATH': {str(config)!r}}})\n",
        encoding="utf-8",
    )
    shim.chmod(0o700)
    marker_script = root / "marker.py"
    marker_script.write_text(
        "import pathlib, sys, time\npathlib.Path(sys.argv[1]).write_text(str(time.monotonic_ns()), encoding='ascii')\n",
        encoding="utf-8",
    )
    settings = SettingsSnapshot(
        payload=json.dumps({"server": {"port": port, "database": {"profile": "memory"}}})
    ).materialize()
    with monkeypatch.context() as patch:
        # Substitute the compiler's installation, never the process-global sys.prefix.
        patch.setattr(bind_compilation, "sys", SimpleNamespace(prefix=str(installation)))
        native = bind_compilation._compile_uncaged_vessel_unit(settings=settings)  # pyright: ignore[reportPrivateUsage]
    assert native.filename == _VESSEL
    assert native.exec_start == f"{systemd_executable_token(shim)} serve --host 127.0.0.1 --port {port}"
    dependencies = tuple(f"lychd-proof-{token}-dependency-{name}.service" for name in ("a", "b"))
    plain_units = {_VESSEL: native.render()}
    for unit in dependencies:
        marker = root / f"{unit}.stopped"
        plain_units[unit] = "\n".join(
            (
                "[Unit]",
                "Description=LychD inert dependency sentinel",
                "[Service]",
                "Type=oneshot",
                f"ExecStart={binaries['true']}",
                f"ExecStop={systemd_executable_token(Path(sys.executable))} {systemd_executable_token(marker_script)} {systemd_executable_token(marker)}",
                "RemainAfterExit=yes",
                "",
            )
        )
    for unit in ("basic.target", "shutdown.target"):
        (harness / unit).write_text(
            "[Unit]\nDescription=LychD private native proof support\nDefaultDependencies=no\n", encoding="utf-8"
        )
    scribe = ScribeService(output_dir=quadlet, systemd_dir=generated)
    scribe.reconcile_all((), plain_units=plain_units)
    manager_storage = Path(tempfile.mkdtemp(prefix="lns-"))
    environment = manager_environment(manager_storage / "manager", generated, harness, inherit_environment=False)
    bus = prepare_bus(
        runtime=Path(environment["XDG_RUNTIME_DIR"]), harness=harness, root=root, binaries=broker_binaries()
    )
    environment["DBUS_SESSION_BUS_ADDRESS"] = bus.address
    environment["DBUS_SYSTEM_BUS_ADDRESS"] = f"unix:path={bus.runtime / 'disabled-system-bus'}"
    metadata: dict[str, object] = {
        "generated_sha256": {name: _digest(generated / name) for name in plain_units},
        "shim_sha256": _digest(shim),
        "marker_sha256": _digest(marker_script),
        "fixture_config_sha256": _digest(config),
        "installation_substitution": str(installation),
        "generated_exec_start": native.exec_start,
        "credential_mode": "0600; synthetic value excluded from argv/environment/receipt",
    }
    return scribe, environment, dependencies, metadata, bus


def _capture_native(snapshot: Mapping[str, str], owned: dict[int, _Process], outer_group: str) -> _Process:
    native = _process(int(snapshot["MainPID"]))
    assert native is not None
    assert native.pid > 1
    assert native.pgid != os.getpgrp()
    assert Path(native.cgroup.strip().removeprefix("0::")).is_relative_to(outer_group)
    assert Path(snapshot["ControlGroup"]).is_relative_to(outer_group)
    assert snapshot["ControlGroup"] != outer_group
    owned.update(_group(native.pgid))
    members = _cgroup_members(snapshot["ControlGroup"])
    if members is not None:
        assert native.pid in members, "manager native cgroup does not contain its MainPID"
        for pid in members:
            process = _process(pid)
            assert process is not None
            owned[pid] = process
    return native


def _outer_descendants(manager: _Manager) -> dict[int, _Process]:
    directory = Path("/sys/fs/cgroup") / manager.outer_group.lstrip("/")
    assert directory.is_dir(), "outer proof cgroup disappeared during owned cleanup"
    files = tuple(directory.rglob("cgroup.procs"))
    assert len(files) <= 100
    pids = {int(pid) for path in files for pid in path.read_text(encoding="ascii").split()}
    assert len(pids) <= 128
    baseline = {process.pid: process.starttime for process in manager.ancestors}
    descendants: dict[int, _Process] = {}
    for pid in pids:
        process = _process(pid)
        if process is not None and baseline.get(pid) != process.starttime:
            assert Path(process.cgroup.strip().removeprefix("0::")).is_relative_to(manager.outer_group)
            descendants[pid] = process
    return descendants


def _cleanup(
    manager: _Manager,
    port: int,
    owned: dict[int, _Process],
    native: _Process | None,
    control_group: str,
    receipt: dict[str, Any],
) -> None:
    cleanup: dict[str, object] = {}
    receipt["cleanup"] = cleanup
    try:
        # The pre-launch outer baseline pins the caller and every ancestor by
        # PID/starttime. Capture all later occurrences in the exclusive subtree
        # even when startup failed before native MainPID or bus observation.
        owned.update(_outer_descendants(manager))
        if manager.process.poll() is None:
            manager.attest()
            snapshots = read_properties(
                systemctl=manager.binaries["systemctl"], environment=manager.environment, units=manager.units
            )
            current = snapshots[_VESSEL]
            if int(current["MainPID"]):
                native = _capture_native(current, owned, manager.outer_group)
                control_group = current["ControlGroup"]
            stopped = run_systemctl(
                manager.binaries["systemctl"],
                manager.environment,
                "stop",
                "--job-mode=fail",
                *manager.units,
                timeout=5.0,
            )
            cleanup["exact_stop_returncode"] = stopped.returncode
            manager.attest()
            bus_stopped = run_systemctl(
                manager.binaries["systemctl"],
                manager.environment,
                "stop",
                "--job-mode=fail",
                *manager.bus.units,
                timeout=5.0,
            )
            cleanup["bus_stop_returncode"] = bus_stopped.returncode
    except (AssertionError, OSError, subprocess.SubprocessError) as exc:
        cleanup["manager_stop_error"] = type(exc).__name__
    finally:
        stop_private_manager(manager.process, Path(manager.environment["XDG_RUNTIME_DIR"]))
    cleanup["manager_exit"] = manager.process.returncode
    owned.update(_outer_descendants(manager))
    # Kill only exact captured occurrences, after rechecking PID reuse. Never
    # signal a shared group, broad cgroup or the installed user manager.
    forced: list[dict[str, object]] = []
    for process in owned.values():
        if _same_process(process):
            forced.append(asdict(process))
            with suppress(ProcessLookupError):
                os.kill(process.pid, signal.SIGKILL)
    cleanup["forced_pid_occurrences"] = forced
    deadline = time.monotonic() + _OBSERVATION_SECONDS
    while True:
        live = [pid for pid, process in owned.items() if _same_process(process)]
        group = _group(native.pgid) if native is not None else {}
        members = _cgroup_members(control_group)
        descendants = _outer_descendants(manager)
        absent = _listener_absent(port)
        bus_absent = manager.bus.listener_absent()
        private_absent = _private_listener_absent(manager.bus.runtime)
        if not live and not group and not members and not descendants and absent and bus_absent and private_absent:
            cleanup.update(
                captured_processes_absent=True,
                native_group_absent=True,
                native_cgroup_members=members,
                listener_absent=True,
                outer_descendants_absent=True,
                full_bus_listener_absent=True,
                private_peer_listener_absent=True,
            )
            break
        if time.monotonic() >= deadline:
            cleanup.update(
                captured_processes_absent=not live,
                native_group_survivors=list(group),
                native_cgroup_members=members,
                listener_absent=absent,
                outer_descendants_absent=not descendants,
                full_bus_listener_absent=bus_absent,
                private_peer_listener_absent=private_absent,
            )
            break
        time.sleep(0.05)
    cleanup["captured_processes"] = [asdict(process) for process in owned.values()]
    cleanup["success"] = (
        cleanup.get("captured_processes_absent") is True
        and cleanup.get("native_group_absent") is True
        and cleanup.get("listener_absent") is True
        and cleanup.get("outer_descendants_absent") is True
        and cleanup.get("full_bus_listener_absent") is True
        and cleanup.get("private_peer_listener_absent") is True
    )
    assert cleanup["success"], f"owned native cleanup is unproved; inspect {manager.root / 'receipt.json'}"


def _assert_outcome(
    *,
    manager: _Manager,
    root: Path,
    case: str,
    dependencies: tuple[str, ...],
    after: dict[str, dict[str, str]],
    error: OperatorError | None,
    receipt: dict[str, Any],
) -> None:
    stops = [
        tuple(cast("tuple[str, ...]", call["argv"])[4:])
        for call in manager.calls
        if cast("tuple[str, ...]", call["argv"])[2] == "stop"
    ]
    events = [
        cast("dict[str, Any]", json.loads(line))
        for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    receipt["events"] = events
    names = [event["event"] for event in events]
    assert names[:3] == ["fixture-cli-argv-accepted", "fixture-startup-enter", "fixture-startup-complete"]
    assert names.count("fixture-close-enter") == 1
    assert after[_VESSEL]["MainPID"] == "0"
    assert after[_VESSEL]["ControlPID"] == "0"
    captured = [call for call in manager.calls if "terminal_fields" in call]
    assert len(captured) == 1
    terminal = cast("dict[str, str]", captured[0]["terminal_fields"])
    assert captured[0]["reference_held"] is True
    if case == "close-failure":
        assert error is not None
        assert stops == [(_VESSEL,)]
        assert after[_VESSEL]["Result"] == "exit-code"
        assert after[_VESSEL]["ExecMainStatus"] == "1"
        assert terminal["ExecMainCode"] == "1"
        assert terminal["ExecMainStatus"] == "1"
        assert terminal["Result"] == "exit-code"
        assert "fixture-required-close-failure" in names
        assert "fixture-close-complete" not in names
        assert all(after[unit]["ActiveState"] == "active" for unit in dependencies)
        assert not any((root / f"{unit}.stopped").exists() for unit in dependencies)
    elif case == "clean":
        assert error is None
        assert stops == [(_VESSEL,), tuple(sorted(dependencies))]
        assert (
            after[_VESSEL]["ActiveState"],
            after[_VESSEL]["SubState"],
        ) == ("inactive", "dead")
        assert terminal == _CLEAN_EXIT
        closed = next(event["monotonic_ns"] for event in events if event["event"] == "fixture-close-complete")
        markers = {unit: int((root / f"{unit}.stopped").read_text(encoding="ascii")) for unit in dependencies}
        receipt["dependency_stop_markers"] = markers
        assert all(stopped > closed for stopped in markers.values())
        assert all(snapshot["ActiveState"] == "inactive" for snapshot in after.values())
    else:
        assert case == "reference-loss"
        assert terminal == _CLEAN_EXIT
        assert manager.loss_event is not None
        assert manager.loss_event["connected_after_disconnect"] is False
        assert cast("int", manager.loss_event["monotonic_ns"]) > cast("int", captured[0]["terminal_capture_ns"])
        assert error is not None
        assert stops == [(_VESSEL,)]
        assert all(after[unit]["ActiveState"] == "active" for unit in dependencies)
        assert not any((root / f"{unit}.stopped").exists() for unit in dependencies)
        assert "fixture-close-complete" in names


def _case(root: Path, case: str, binaries: Mapping[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: PLR0915, C901 - finite orchestration and cleanup stay explicit
    root.mkdir(mode=0o700)
    token, port = uuid.uuid4().hex, _free_port()
    scribe, environment, dependencies, metadata, bus = _prepare(root, case, token, port, binaries, monkeypatch)
    units = (_VESSEL, *dependencies)
    receipt: dict[str, Any] = {
        "case": case,
        "token": token,
        "port": port,
        "units": units,
        "source_sha256": {name: _digest(_REPOSITORY / name) for name in _SOURCES},
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in ("litestar", "granian", "httpx", "http-message-signatures", "dbus-fast")
        },
        "python": {"version": sys.version, "executable": sys.executable, "sha256": _digest(Path(sys.executable))},
        "binaries": {name: {"path": str(path), "sha256": _digest(path)} for name, path in binaries.items()},
        "environment": environment,
        "budgets_seconds": {
            "manager_ready": 5,
            "bus_registration": 5,
            "start": 5,
            "listener_ready": _LISTENER_SECONDS,
            "controller_process": 30,
            "controller_outer": _CONTROL_OUTER_SECONDS,
            "observation": _OBSERVATION_SECONDS,
            "cleanup_stop": 5,
            "manager_terminate": 2,
            "manager_kill": 2,
            "cleanup_observation": _OBSERVATION_SECONDS,
        },
        **metadata,
        "proof_success": False,
    }
    manager: _Manager | None = None
    child: subprocess.Popen[str] | None = None
    native: _Process | None = None
    owned: dict[int, _Process] = {}
    control_group = ""
    with (root / "manager.log").open("w", encoding="utf-8") as log:
        try:
            outer = require_delegated_manager_cgroup(binaries["systemctl"])
            receipt["outer_service"] = outer
            ancestors = tuple(_process(int(pid)) for pid in outer["AncestorPids"].split())
            assert all(process is not None for process in ancestors)
            baseline = cast("tuple[_Process, ...]", ancestors)
            receipt["outer_baseline_processes"] = [asdict(process) for process in baseline]
            child = subprocess.Popen(  # noqa: S603 - root-controlled manager, closed options and private environment
                [
                    str(binaries["systemd"]),
                    "--user",
                    "--unit=basic.target",
                    "--log-target=console",
                    "--log-level=warning",
                    "--no-pager",
                ],
                env=environment,
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
            identity = _process(child.pid)
            assert identity is not None
            manager = _Manager(
                child, identity, environment, binaries, root, units, outer["ControlGroup"], baseline, bus
            )
            manager.lose_reference = case == "reference-loss"
            receipt["manager_identity"] = asdict(identity)
            version = subprocess.run(  # noqa: S603 - attested binary and literal read-only argument
                [str(binaries["systemd"]), "--version"],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=3.0,
            )
            receipt["manager_version"] = version.stdout
            unavailable = wait_for_manager(child, systemctl=binaries["systemctl"], environment=environment, timeout=5.0)
            if unavailable:
                proof_unavailable(f"isolated native-stop manager unavailable: {unavailable}")
            manager.attest()
            private = Path(environment["XDG_RUNTIME_DIR"]) / "systemd/private"
            receipt["private_socket"] = {
                "path": str(private),
                "inode": private.lstat().st_ino,
                "uid": private.lstat().st_uid,
            }
            manager.attest()
            bus_start = run_systemctl(
                binaries["systemctl"], environment, "start", "--job-mode=fail", *bus.units, timeout=5.0
            )
            assert bus_start.returncode == 0, bus_start.stderr
            bus_snapshot = bus.attest(
                manager_pid=child.pid,
                outer_group=outer["ControlGroup"],
                systemctl=binaries["systemctl"],
                environment=environment,
            )
            receipt["full_bus"] = bus_snapshot
            for pid in bus_snapshot["process_pids"]:
                process = _process(pid)
                assert process is not None
                owned[pid] = process
            started = run_systemctl(
                binaries["systemctl"], environment, "start", "--job-mode=fail", *dependencies, _VESSEL, timeout=5.0
            )
            assert started.returncode == 0, started.stderr
            _ready(manager, port, token)
            before = read_properties(systemctl=binaries["systemctl"], environment=environment, units=units)
            receipt["before"] = before
            assert all(snapshot["ActiveState"] == "active" for snapshot in before.values())
            for unit, snapshot in before.items():
                assert snapshot["FragmentPath"] == str(root / "generated" / unit)
                if snapshot["ControlGroup"]:
                    assert Path(snapshot["ControlGroup"]).is_relative_to(outer["ControlGroup"])
                    assert snapshot["ControlGroup"] != outer["ControlGroup"]
            assert before[_VESSEL]["FragmentPath"] == str(root / "generated" / _VESSEL)
            assert before[_VESSEL]["InvocationID"]
            assert before[_VESSEL]["Restart"] == "on-failure"
            assert before[_VESSEL]["RequiredBy"] == ""
            assert before[_VESSEL]["BoundBy"] == ""
            incoming = run_systemctl(binaries["systemctl"], environment, "show", _VESSEL, "--property=WantedBy")
            assert incoming.returncode == 0
            assert incoming.stdout == "WantedBy=\n"
            receipt["native_incoming_wants"] = incoming.stdout
            assert str(root / "installation/bin/lychd") in before[_VESSEL]["ExecStart"]
            native = _capture_native(before[_VESSEL], owned, outer["ControlGroup"])
            control_group = before[_VESSEL]["ControlGroup"]
            receipt["native_identity"] = asdict(native)
            receipt["effective_defaults"] = {
                name: before[_VESSEL][name]
                for name in ("TimeoutStopUSec", "KillMode", "KillSignal", "SendSIGKILL", "SuccessExitStatus", "Restart")
            }
            inventory = _inventory(scribe, manager)
            access = LocalAccess(
                url=f"http://127.0.0.1:{port}/", password=SecretStr((root / "credential").read_text(encoding="ascii"))
            )
            client = StopAdmissionClient(access_loader=lambda: access)
            admissions: list[str] = []

            def admit(generation: str) -> None:
                client.admit(generation)
                admissions.append(generation)

            reference_events: list[dict[str, object]] = []

            @contextmanager
            def hold_reference() -> Generator[stop_evidence.ExitReference]:
                with stop_evidence.hold_native_exit(runtime_dir=bus.runtime) as reference:
                    manager.reference_held = True
                    reference_events.append({"event": "reference-held", "monotonic_ns": time.monotonic_ns()})
                    try:
                        yield reference
                    finally:
                        manager.reference_held = False
                        reference_events.append({"event": "reference-scope-exit", "monotonic_ns": time.monotonic_ns()})

            new_bus = stop_evidence._new_bus  # pyright: ignore[reportPrivateUsage]

            def capture_reference_bus(address: str) -> Any:
                reference_bus = new_bus(address)
                manager.reference_buses.append(reference_bus)
                return reference_bus

            control = OperatorControlService(
                inventory=inventory,
                targets=OperatorTargetResolver(inventory),
                runner=manager,
                systemctl_bin=str(binaries["systemctl"]),
                lock_factory=lambda: LifecycleLock(root / "lifecycle.lock"),
                stop_admission=admit,
                exit_reference_factory=hold_reference,
            )
            error: OperatorError | None = None
            manager.deadline = time.monotonic() + _CONTROL_OUTER_SECONDS
            with monkeypatch.context() as patch, _control_deadline():
                patch.setattr(stop_evidence, "_new_bus", capture_reference_bus)
                try:
                    result = control.execute(OperatorAction.STOP, OperatorTarget.SYSTEM)
                    assert result.authority is VesselAuthority.VESSEL
                except OperatorError as exc:
                    error = exc
            manager.deadline = None
            receipt["controller_calls"] = manager.calls
            receipt["admissions"] = admissions
            receipt["controller_error"] = str(error) if error else None
            receipt["reference_events"] = reference_events
            receipt["reference_loss"] = manager.loss_event
            assert len(manager.reference_buses) == 1
            reference_bus = manager.reference_buses[0]
            assert not reference_bus.connected
            reference_socket = reference_bus._sock  # pyright: ignore[reportPrivateUsage]
            assert reference_socket is None or reference_socket.fileno() == -1
            assert len(admissions) == 1
            assert admissions[0] == scribe.inspect_owned_bindings().generation
            assert not wait_for_jobs(
                systemctl=binaries["systemctl"],
                environment=environment,
                unique_stem="lychd-",
                timeout=_OBSERVATION_SECONDS,
            )
            after = read_properties(systemctl=binaries["systemctl"], environment=environment, units=units)
            receipt["after"] = after
            _assert_outcome(
                manager=manager,
                root=root,
                case=case,
                dependencies=dependencies,
                after=after,
                error=error,
                receipt=receipt,
            )
            time.sleep(0.3)
            stable = read_properties(systemctl=binaries["systemctl"], environment=environment, units=units)
            receipt["after_restart_observation"] = stable
            assert stable[_VESSEL]["NRestarts"] == before[_VESSEL]["NRestarts"]
            assert stable[_VESSEL]["MainPID"] == "0"
            assert _listener_absent(port)
            assert not _same_process(native)
            assert not _group(native.pgid), "native process group survived normal retirement"
            assert _cgroup_members(control_group) == (), "native cgroup survived normal retirement"
            assert set(_outer_descendants(manager)) == {manager.process.pid, *bus_snapshot["process_pids"]}
            receipt["proof_success"] = True
        finally:
            try:
                if manager is not None:
                    receipt["controller_calls"] = manager.calls
                    _cleanup(manager, port, owned, native, control_group, receipt)
                elif child is not None:
                    stop_private_manager(child, Path(environment["XDG_RUNTIME_DIR"]))
                    receipt["cleanup"] = {"success": False, "reason": "manager occurrence identity was not captured"}
            finally:
                # Keep diagnostics, generated bytes and receipts for review;
                # destroy only the synthetic credential after process cleanup.
                if receipt.get("cleanup", {}).get("success") is True:
                    (root / "credential").unlink(missing_ok=True)
                    shutil.rmtree(Path(environment["XDG_RUNTIME_DIR"]).parent.parent)
                _write_json(root / "receipt.json", receipt)


def test_native_failed_clean_and_lost_reference_stop_under_private_systemd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Require three ordered cases without altering installed units."""
    if os.environ.get("LYCHD_REQUIRE_SYSTEMD_PROOF") != "1":
        pytest.skip("native systemd stop proof requires explicit LYCHD_REQUIRE_SYSTEMD_PROOF=1")
    if sys.platform != "linux":
        proof_unavailable("native systemd stop proof requires Linux")
    assert not tmp_path.resolve().is_relative_to(_REPOSITORY), "explicit basetemp must be outside the checkout"
    assert tmp_path.resolve().is_relative_to(Path("/tmp")), "native fixture data must use ordinary private /tmp"  # noqa: S108 - explicitly admitted proof workspace
    binaries = required_binaries()
    _case(tmp_path / "01-close-failure", "close-failure", binaries, monkeypatch)
    _case(tmp_path / "02-clean", "clean", binaries, monkeypatch)
    _case(tmp_path / "03-reference-loss", "reference-loss", binaries, monkeypatch)
