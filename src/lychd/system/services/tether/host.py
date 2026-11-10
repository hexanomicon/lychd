"""Bounded native effects over exact Scribe-owned Tether units and incarnations."""

from __future__ import annotations

import json
import os
import re
import stat
import time
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from lychd.lib.json_objects import unique_json_object
from lychd.system.host_tools import trusted_host_tool
from lychd.system.operator.process import SubprocessRunner
from lychd.system.services.tether.models import TetherError

if TYPE_CHECKING:
    from lychd.domain.tether.compiler import RuntimeConfig
    from lychd.system.operator.process import InputProcessRunner

_ID = re.compile(r"[0-9a-f]{64}")
_MAX_OUTPUT = 1024 * 1024
_PRIVATE_DIRECTORY_MODE = 0o700
_POD_NAME = re.compile(r"lychd-tether-[0-9a-f]{16}")
_ROLE_NAME = re.compile(r"(lychd-tether-[0-9a-f]{16})-(?:wg|outbound|ingress|ssh-[0-9a-f]{12})")
_ROLE_FIELDS = {
    "container_id",
    "container_name",
    "unit_name",
    "pod_id",
    "image_id",
    "netns",
    "cgroup",
    "invocation_id",
    "unit_cgroup",
}
_POD_FIELDS = {
    "pod_id",
    "pod_name",
    "unit_name",
    "infra_id",
    "infra_cgroup",
    "netns",
    "invocation_id",
    "unit_cgroup",
}


def _require(value: bool) -> None:  # noqa: FBT001 - invariant assertion
    if not value:
        message = "Tether host ownership or runtime observation refused"
        raise TetherError(message)


def _identifier(value: Any) -> str:
    _require(type(value) is str and _ID.fullmatch(value) is not None)
    return value


def _user_group(group: str) -> Path:
    _require(type(group) is str)
    path = Path(group)
    _require(group.startswith("/") and str(path) == group and ".." not in path.parts)
    _require(path.parts[:3] == ("/", "user.slice", f"user-{os.getuid()}.slice"))
    return path


def _container_group(group: str, identity: str, unit_group: str | None = None) -> str:
    """Own the full exact payload/scope subtree, not the initial process's leaf."""
    parts = _user_group(group).parts
    markers = {f"libpod-payload-{identity}", f"libpod-{identity}.scope"}
    matches = [index for index, component in enumerate(parts) if component in markers]
    _require(len(matches) == 1)
    index = matches[0]
    root = Path(*parts[: index + 1])
    if parts[index].startswith("libpod-payload-") and unit_group is not None:
        _require(bool(unit_group) and root.is_relative_to(_user_group(unit_group)) and root != Path(unit_group))
    return str(root)


class TetherHost:
    """Never act on a guessed process, wildcard unit, tag, or container name alone."""

    def __init__(self, runner: InputProcessRunner | None = None) -> None:
        """Resolve only root-controlled executables; keep command diagnostics private."""
        self.runner = runner or SubprocessRunner()

    def command(self, tool: str, *arguments: str) -> str:
        """Execute one finite literal command without reflecting captured diagnostics."""
        try:
            _require(tool in {"podman", "systemctl", "ip"})
            executable = trusted_host_tool(tool)
            _require(executable is not None)
            result = self.runner.run((cast("str", executable), *arguments), timeout_s=45)
            _require(not result.returncode and len(result.stdout.encode()) <= _MAX_OUTPUT)
        except Exception:  # noqa: BLE001 - quarantine process/observation diagnostics
            message = "Tether host command failed; private diagnostics suppressed"
            raise TetherError(message) from None
        else:
            return result.stdout

    def owned_unit(self, name: str) -> dict[str, str]:
        """Recheck current Scribe authority and effective generated unit provenance."""
        from lychd.system.services.deployment import DeploymentInspectionService
        from lychd.system.services.scribe.facade import ScribeService

        try:
            _require(type(name) is str and name.endswith(".service"))
            stem = name.removesuffix(".service")
            _require(
                stem == "lychd-vessel"
                or _ROLE_NAME.fullmatch(stem) is not None
                or (stem.endswith("-pod") and _POD_NAME.fullmatch(stem.removesuffix("-pod")) is not None)
            )
            owned = ScribeService().inspect_owned_bindings()
            _require(owned.receipt_present and name in owned.runtime_units)
            observed = DeploymentInspectionService(runner=self.runner).observe_owned_units(
                owned, unit_names=frozenset({name})
            )
            return observed[name]
        except Exception:  # noqa: BLE001 - never expose filesystem or process diagnostics
            message = "Tether unit lacks current effective binding authority"
            raise TetherError(message) from None

    def unit_incarnation(self, name: str) -> dict[str, str]:
        """Bind a launch to the current systemd invocation and owned control group."""
        unit = self.owned_unit(name)
        content = self.command(
            "systemctl",
            "--user",
            "show",
            name,
            "--property=Id",
            "--property=InvocationID",
            "--property=ControlGroup",
        )
        fields: dict[str, str] = {}
        for line in content.splitlines():
            key, separator, value = line.partition("=")
            _require(bool(separator) and key not in fields)
            fields[key] = value
        _require(set(fields) == {"Id", "InvocationID", "ControlGroup"} and fields["Id"] == name)
        invocation, group = fields["InvocationID"], fields["ControlGroup"]
        _require(not invocation or re.fullmatch(r"[0-9a-f]{32}", invocation) is not None)
        if group:
            _user_group(group)
            _require(Path(group).name == name)
        if not invocation:
            _require(self._quiescent(unit) and not group)
        return {"InvocationID": invocation, "ControlGroup": group}

    @staticmethod
    def _quiescent(unit: dict[str, str]) -> bool:
        return (
            unit.get("LoadState") == "loaded"
            and unit.get("ActiveState") == "inactive"
            and unit.get("SubState") == "dead"
            and unit.get("MainPID") == unit.get("ControlPID") == "0"
            and unit.get("Job") in {"", "0"}
        )

    def exists(self, kind: str, identity: str) -> bool:
        """Distinguish exact absence from an unsuccessful Podman observation."""
        if kind not in {"container", "pod"}:
            message = "Unsupported Tether runtime kind"
            raise TetherError(message)
        executable = trusted_host_tool("podman")
        if executable is None:
            message = "A trusted Podman executable is unavailable"
            raise TetherError(message)
        result = self.runner.run((executable, kind, "exists", identity), timeout_s=5)
        if result.returncode not in {0, 1}:
            message = "Tether runtime absence is uncertain"
            raise TetherError(message)
        return result.returncode == 0

    def row(self, kind: str, identity: str) -> dict[str, Any]:
        """Read exactly one requested Podman object; never dump WireGuard keys."""
        _require(
            kind in {"image", "container", "pod"}
            and type(identity) is str
            and bool(identity)
            and not identity.startswith("-")
        )
        rows = json.loads(
            self.command("podman", kind, "inspect", identity),
            object_pairs_hook=unique_json_object,
        )
        if type(rows) is not list:
            message = "Malformed Tether runtime observation"
            raise TetherError(message)
        validated_rows = cast("list[object]", rows)
        if len(validated_rows) != 1 or type(validated_rows[0]) is not dict:
            message = "Malformed Tether runtime observation"
            raise TetherError(message)
        return cast("dict[str, Any]", validated_rows[0])

    def image(self, reference: str) -> dict[str, str]:
        """Attest an already imported digest, including immutable image identity."""
        row = self.row("image", reference)
        identity = row.get("Id", "")
        expected = reference.rsplit("@", 1)[-1]
        if not _ID.fullmatch(identity) or not expected.startswith("sha256:") or row.get("Digest") != expected:
            message = "Tether requires the exact admitted local digest"
            raise TetherError(message)
        return {"id": identity, "digest": expected}

    def host_addresses(self) -> tuple[str, ...]:
        """Observe local numeric IPv4 addresses before admitting external backends."""
        rows = json.loads(self.command("ip", "-j", "-4", "address", "show"))
        return tuple(sorted({item["local"] for row in rows for item in row.get("addr_info", ())}))

    @staticmethod
    def runtime_directories(root: Path, directories: tuple[Path, ...]) -> None:
        """Create boot-local private directories without persisting tmpfs identities."""
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptor = os.open("/", flags)
        try:
            for component in root.parent.parts[1:]:
                child = os.open(component, flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            metadata = os.fstat(descriptor)
            if metadata.st_uid != os.getuid() or metadata.st_mode & 0o022:
                message = "Unsafe Tether runtime parent"
                raise TetherError(message)
            for path in (root, *directories):
                if root not in (path, path.parent):
                    message = "Runtime directory is outside its fixed parent"
                    raise TetherError(message)
                parent = descriptor if path == root else os.open(root.name, flags, dir_fd=descriptor)
                try:
                    with suppress(FileExistsError):
                        os.mkdir(path.name, _PRIVATE_DIRECTORY_MODE, dir_fd=parent)
                    child = os.open(path.name, flags, dir_fd=parent)
                    try:
                        observed = os.fstat(child)
                        if observed.st_uid != os.getuid() or stat.S_IMODE(observed.st_mode) != _PRIVATE_DIRECTORY_MODE:
                            message = "Unsafe Tether runtime directory"
                            raise TetherError(message)
                    finally:
                        os.close(child)
                finally:
                    if parent != descriptor:
                        os.close(parent)
        finally:
            os.close(descriptor)

    @staticmethod
    def process_cgroup(pid: int) -> str:
        """Retain the kernel's exact cgroup, never a process-group approximation."""
        _require(type(pid) is int and pid > 0)
        rows = Path(f"/proc/{pid}/cgroup").read_text().splitlines()
        paths = [line[3:] for line in rows if line.startswith("0::/")]
        _require(len(paths) == 1)
        _user_group(paths[0])
        return paths[0]

    @staticmethod
    def cgroup_empty(group: str) -> bool:
        """Require the complete retained subtree to contain no surviving tasks."""
        _user_group(group)
        root = Path("/sys/fs/cgroup") / group.lstrip("/")
        if not root.exists():
            return True
        _require((root / "cgroup.procs").is_file())
        return all(not path.read_text().strip() for path in root.rglob("cgroup.procs"))

    def _netns(self, pid: int) -> int:
        _require(type(pid) is int and pid > 0)
        netns = Path(f"/proc/{pid}/ns/net").stat().st_ino
        if netns == Path("/proc/self/ns/net").stat().st_ino:
            message = "Tether role unexpectedly shares the host network"
            raise TetherError(message)
        if self.exists("container", "lychd-vessel"):
            core = self.row("container", "lychd-vessel")
            core_pid = core.get("State", {}).get("Pid", 0)
            if type(core_pid) is int and core_pid > 0 and netns == Path(f"/proc/{core_pid}/ns/net").stat().st_ino:
                message = "Tether role unexpectedly shares the Core network"
                raise TetherError(message)
        return netns

    def capture(self, config: RuntimeConfig, image: dict[str, str]) -> dict[str, Any]:
        """Prove image, namespace and an exact owned cgroup before route admission."""
        match = _ROLE_NAME.fullmatch(config.name)
        _require(match is not None)
        if match is None:
            message = "Invalid Tether role name"
            raise TetherError(message)
        launch = self.unit_incarnation(config.name + ".service")
        _require(bool(launch["InvocationID"]))
        row = self.row("container", config.name)
        identity = _identifier(row.get("Id"))
        pod = self.row("pod", match[1])
        _require(pod.get("Name") == match[1])
        pod_id = _identifier(pod.get("Id"))
        state = row.get("State", {})
        _require(
            row.get("Name") == config.name
            and row.get("Image") == image["id"]
            and row.get("ImageDigest") == image["digest"]
            and row.get("Pod") == pod_id
            and state.get("Running") is True
        )
        pid = state.get("Pid")
        netns = self._netns(pid)
        group = _container_group(self.process_cgroup(pid), identity, launch["ControlGroup"])
        fresh = self.row("container", identity)
        _require(
            fresh.get("Id") == identity
            and fresh.get("State", {}).get("Pid") == pid
            and fresh.get("State", {}).get("Running") is True
        )
        _require(self.unit_incarnation(config.name + ".service") == launch)
        return {
            "container_id": identity,
            "container_name": config.name,
            "unit_name": config.name + ".service",
            "pod_id": pod_id,
            "image_id": image["id"],
            "netns": netns,
            "cgroup": group,
            "invocation_id": launch["InvocationID"],
            "unit_cgroup": launch["ControlGroup"],
        }

    def capture_pod(self, pod_name: str) -> dict[str, Any]:
        """Retain exact generated Pod/infra identity before admitting its roles."""
        _require(type(pod_name) is str and _POD_NAME.fullmatch(pod_name) is not None)
        unit = pod_name + "-pod.service"
        launch = self.unit_incarnation(unit)
        _require(bool(launch["InvocationID"]))
        row = self.row("pod", pod_name)
        pod_id, infra_id = (
            _identifier(row.get("Id")),
            _identifier(row.get("InfraContainerID")),
        )
        _require(row.get("Name") == pod_name)
        infra = self.row("container", infra_id)
        _require(
            infra.get("Id") == infra_id and infra.get("Pod") == pod_id and infra.get("State", {}).get("Running") is True
        )
        pid = infra["State"].get("Pid")
        netns = self._netns(pid)
        group = _container_group(self.process_cgroup(pid), infra_id, launch["ControlGroup"])
        fresh = self.row("pod", pod_id)
        _require(
            fresh.get("Id") == pod_id and fresh.get("InfraContainerID") == infra_id and fresh.get("Name") == pod_name
        )
        _require(self.unit_incarnation(unit) == launch)
        return {
            "pod_id": pod_id,
            "pod_name": pod_name,
            "unit_name": unit,
            "infra_id": infra_id,
            "infra_cgroup": group,
            "invocation_id": launch["InvocationID"],
            "unit_cgroup": launch["ControlGroup"],
            "netns": netns,
        }

    def observe(self, config: RuntimeConfig) -> dict[str, Any]:
        """Read a fresh role heartbeat bound to this exact public configuration."""
        raw = self.command(
            "podman",
            "exec",
            config.name,
            "python3",
            "-m",
            "lychd_tether_runtime",
            "--observe",
            "/etc/lychd-tether/config.json",
        )
        value = json.loads(raw)
        keys = (
            "role",
            "network_id",
            "installation_epoch",
            "generation",
            "policy_digest",
        )
        if any(value.get(key) != config.payload[key] for key in keys) or value.get("enabled") is not True:
            message = "Tether runtime has not acknowledged current admission"
            raise TetherError(message)
        return value

    @staticmethod
    def _retained_launch(retained: dict[str, Any]) -> None:
        invocation, group = retained["invocation_id"], retained["unit_cgroup"]
        _require(type(invocation) is str and re.fullmatch(r"[0-9a-f]{32}", invocation) is not None)
        _require(type(group) is str)
        if group:
            _require(_user_group(group).name == retained["unit_name"])

    @staticmethod
    def _retained_role(retained: dict[str, Any]) -> None:
        _require(type(retained) is dict and set(retained) == _ROLE_FIELDS)
        name = retained["container_name"]
        _require(
            type(name) is str and _ROLE_NAME.fullmatch(name) is not None and retained["unit_name"] == name + ".service"
        )
        for field in ("container_id", "pod_id", "image_id"):
            _identifier(retained[field])
        TetherHost._retained_launch(retained)
        _require(type(retained["netns"]) is int and retained["netns"] > 0)
        _require(
            _container_group(retained["cgroup"], retained["container_id"], retained["unit_cgroup"])
            == retained["cgroup"]
        )
        if "libpod-payload-" in retained["cgroup"]:
            _require(Path(retained["cgroup"]).parent.name == retained["unit_name"])

    def _role_present(self, retained: dict[str, Any]) -> bool:
        identity, name = retained["container_id"], retained["container_name"]
        by_id, by_name = (
            self.exists("container", identity),
            self.exists("container", name),
        )
        if by_name:
            _require(self.row("container", name).get("Id") == identity)
        if by_id:
            row = self.row("container", identity)
            _require(
                by_name
                and row.get("Id") == identity
                and row.get("Name") == name
                and row.get("Image") == retained["image_id"]
                and row.get("Pod") == retained["pod_id"]
            )
            return row.get("State", {}).get("Running") is True
        _require(not by_name)
        return False

    def _settled(self, unit: str, group: str) -> None:
        deadline = time.monotonic() + 10
        while not (self.cgroup_empty(group) and self._quiescent(self.owned_unit(unit))):
            if time.monotonic() >= deadline:
                message = "Tether descendant or unit-job closure remains incomplete"
                raise TetherError(message)
            time.sleep(0.05)

    def _unit_closed(self, name: str) -> bool:
        """Observe a retired fixed unit without acquiring authority to actuate it."""
        properties = ("Id", "LoadState", "ActiveState", "SubState", "MainPID", "ControlPID", "Job")
        executable = trusted_host_tool("systemctl")
        _require(executable is not None)
        result = self.runner.run(
            (cast("str", executable), "--user", "show", name, *("--property=" + key for key in properties)), timeout_s=5
        )
        _require(result.returncode in {0, 1, 4} and len(result.stdout.encode()) <= _MAX_OUTPUT)
        fields: dict[str, str] = {}
        for line in result.stdout.splitlines():
            key, separator, value = line.partition("=")
            _require(bool(separator) and key not in fields)
            fields[key] = value
        _require(set(fields) == set(properties) and fields["Id"] == name)
        if result.returncode:
            _require(fields["LoadState"] == "not-found")
        return (
            fields["LoadState"] in {"loaded", "not-found"}
            and fields["ActiveState"] == "inactive"
            and fields["SubState"] == "dead"
            and fields["MainPID"] == fields["ControlPID"] == "0"
            and fields["Job"] in {"", "0"}
        )

    def closed(self, retained: dict[str, Any]) -> bool:
        """Prove closure without effects even after a binding has been retired."""
        self._retained_role(retained)
        return (
            not self._role_present(retained)
            and self.cgroup_empty(retained["cgroup"])
            and self._unit_closed(retained["unit_name"])
        )

    def pod_closed(self, retained: dict[str, Any]) -> bool:
        """Prove retained Pod closure without requiring a surviving binding."""
        self._retained_pod(retained)
        return (
            not self._pod_present(retained)
            and self.cgroup_empty(retained["infra_cgroup"])
            and self._unit_closed(retained["unit_name"])
        )

    def require_core(self, image_reference: str) -> None:
        """Bind the running Core body to its exact owned manager invocation."""
        name, unit_name = "lychd-vessel", "lychd-vessel.service"
        unit = self.owned_unit(unit_name)
        _require(unit.get("LoadState") == "loaded" and unit.get("ActiveState") == "active")
        launch = self.unit_incarnation(unit_name)
        _require(bool(launch["InvocationID"]) and bool(launch["ControlGroup"]))
        expected = _identifier(self.row("image", image_reference).get("Id"))
        row = self.row("container", name)
        identity = _identifier(row.get("Id"))
        state = row.get("State", {})
        _require(row.get("Name") == name and row.get("Image") == expected and state.get("Running") is True)
        pid = state.get("Pid")
        _require(type(pid) is int and pid > 0)
        group = _container_group(self.process_cgroup(pid), identity, launch["ControlGroup"])
        # Core's Quadlet uses split cgroups: its payload belongs below this unit.
        _require(Path(group).is_relative_to(_user_group(launch["ControlGroup"])))
        fresh = self.row("container", identity)
        _require(
            fresh.get("Id") == identity
            and fresh.get("Name") == name
            and fresh.get("Image") == expected
            and fresh.get("State", {}).get("Running") is True
            and fresh.get("State", {}).get("Pid") == pid
        )
        _require(self.unit_incarnation(unit_name) == launch)

    def stop_unretained(self, container_name: str) -> None:
        """Cancel an owned failed launch only while no named body exists."""
        _require(type(container_name) is str and _ROLE_NAME.fullmatch(container_name) is not None)
        unit_name = container_name + ".service"
        _require(not self.exists("container", container_name))
        if self._unit_closed(unit_name):
            return
        launch = self.unit_incarnation(unit_name)
        group = launch["ControlGroup"]
        _require(not self.exists("container", container_name))
        self.command("systemctl", "--user", "stop", unit_name)
        deadline = time.monotonic() + 10
        while not (self._quiescent(self.owned_unit(unit_name)) and (not group or self.cgroup_empty(group))):
            if time.monotonic() >= deadline:
                message = "Tether failed-launch closure remains incomplete"
                raise TetherError(message)
            time.sleep(0.05)
        _require(not self.exists("container", container_name))

    def _stop_launch(self, retained: dict[str, Any]) -> None:
        current = self.unit_incarnation(retained["unit_name"])
        if current["InvocationID"]:
            _require(
                current
                == {
                    "InvocationID": retained["invocation_id"],
                    "ControlGroup": retained["unit_cgroup"],
                }
            )

    def stop(self, retained: dict[str, Any]) -> None:
        """Cancel exact owned-unit restart intent even if its retained body vanished."""
        if self.closed(retained):
            return
        self._stop_launch(retained)
        self._role_present(retained)
        self.command("systemctl", "--user", "stop", retained["unit_name"])
        self._settled(retained["unit_name"], retained["cgroup"])
        _require(not self._role_present(retained))

    @staticmethod
    def _retained_pod(retained: dict[str, Any]) -> None:
        _require(type(retained) is dict and set(retained) == _POD_FIELDS)
        name = retained["pod_name"]
        _require(
            type(name) is str
            and _POD_NAME.fullmatch(name) is not None
            and retained["unit_name"] == name + "-pod.service"
        )
        for field in ("pod_id", "infra_id"):
            _identifier(retained[field])
        TetherHost._retained_launch(retained)
        _require(type(retained["netns"]) is int and retained["netns"] > 0)
        _require(
            _container_group(retained["infra_cgroup"], retained["infra_id"], retained["unit_cgroup"])
            == retained["infra_cgroup"]
        )
        if "libpod-payload-" in retained["infra_cgroup"]:
            _require(Path(retained["infra_cgroup"]).parent.name == retained["unit_name"])

    def _pod_present(self, retained: dict[str, Any]) -> bool:
        identity, name, infra_id = (
            retained["pod_id"],
            retained["pod_name"],
            retained["infra_id"],
        )
        by_id, by_name = self.exists("pod", identity), self.exists("pod", name)
        if by_name:
            _require(self.row("pod", name).get("Id") == identity)
        if by_id:
            row = self.row("pod", identity)
            _require(
                by_name
                and row.get("Id") == identity
                and row.get("Name") == name
                and row.get("InfraContainerID") == infra_id
            )
            members = row.get("Containers")
            _require(type(members) is list)
            members = cast("list[Any]", members)
            _require(all(type(member) is dict and member.get("Id") == infra_id for member in members))
        else:
            _require(not by_name)
        if self.exists("container", infra_id):
            infra = self.row("container", infra_id)
            _require(infra.get("Id") == infra_id and infra.get("Pod") == identity)
            return infra.get("State", {}).get("Running") is True
        return False

    def stop_pod(self, retained: dict[str, Any]) -> None:
        """Stop only a retained generated Pod and settle its exact infra subtree."""
        if self.pod_closed(retained):
            return
        self._stop_launch(retained)
        self._pod_present(retained)
        self.command("systemctl", "--user", "stop", retained["unit_name"])
        self._settled(retained["unit_name"], retained["infra_cgroup"])
        _require(not self._pod_present(retained))
