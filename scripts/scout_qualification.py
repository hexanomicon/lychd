"""Control only the explicitly admitted trusted Scout OCI qualification profile.

Host execution uses the standard library and the local Docker Unix socket. It
never runs Core tests on the host. Namespace quota masks are an outer setup
boundary; they do not remain field-specific after creation of a user namespace.
The unchanged static proof must establish the separate untrusted worker boundary.
"""

# Cancellation must settle owned identities even for SystemExit/KeyboardInterrupt.
# ruff: noqa: BLE001
from __future__ import annotations

import copy
import ctypes
import hashlib
import http.client
import io
import json
import os
import re
import signal
import socket
import stat
import subprocess
import sys
import tarfile
import time
import uuid
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote

Json = dict[str, Any]

PROC_MAGIC = 0x9FA0
CHECK_UID = 1000
NANO_CPUS = 2_000_000_000
PIDS = 256
NOT_FOUND = 404
CONFLICT = 409
MAX_RUN_SECONDS = 300
MAIN_ARGC = 4
ARTIFACT_PATH_PARTS = 2
PROFILE_NAME = "trusted-scout-c2"
CI_PROFILE_NAME = "trusted-scout-ci-c1"
PROFILE_ENGINES = {
    PROFILE_NAME: ("29.7.2-ce", "1.55", "1.5.1"),
    CI_PROFILE_NAME: ("29.9.3", "1.56", "1.5.2"),
}
PROFILE_SHA256 = "364494fcdb222ed262f98016de3855c51a15d6e4a6ef9eeb19e8bb6c86cd3c02"
SOCKET = "/var/run/docker.sock"
API = "/v1.55"
LABEL = "io.lychd.scout-qualification"
CAPS = {"CAP_NET_ADMIN", "CAP_SETUID", "CAP_SETGID", "CAP_SETPCAP"}
TOP = ("abi", "crypto", "debug", "dev", "fs", "kernel", "net", "user", "vm")
QUOTAS = (
    "max_cgroup_namespaces",
    "max_fanotify_groups",
    "max_fanotify_marks",
    "max_inotify_instances",
    "max_inotify_watches",
    "max_ipc_namespaces",
    "max_mnt_namespaces",
    "max_net_namespaces",
    "max_pid_namespaces",
    "max_time_namespaces",
    "max_user_namespaces",
    "max_uts_namespaces",
)
MASKS = tuple(f"/proc/sys/{name}" for name in TOP if name not in {"user", "kernel"}) + tuple(
    f"/proc/sys/user/{name}" for name in QUOTAS if name != "max_user_namespaces"
)
EXPORTS = {"boundary.json", "static-receipt.json", "fetch-receipt.json", "authority-receipt.json"}
COMMAND = [
    "--signal=TERM",
    "--kill-after=5s",
    "295s",
    "bash",
    "/work/scripts/container_scout_qualification.sh",
    "--inside-setup",
]


def require(condition: object, message: str) -> None:
    """Refuse rather than weaken an unsupported or unobserved boundary."""
    if not condition:
        raise ValueError(message)


def selected_profile() -> str:
    """Require one explicitly admitted fixture profile without negotiation."""
    value = os.environ.get("LYCHD_SCOUT_QUALIFICATION_PROFILE", "")
    require(value in PROFILE_ENGINES, "Explicit supported Scout qualification profile required")
    return value


def controller_socket(profile: str) -> str:
    """Bind CLI and controller to one local endpoint; refuse context overrides."""
    require(profile in PROFILE_ENGINES, "Unknown qualification profile")
    require(not os.environ.get("DOCKER_CONTEXT"), "Docker context override refused")
    explicit = os.environ.get("LYCHD_SCOUT_DOCKER_SOCKET", "")
    if profile == PROFILE_NAME:
        require(not explicit, "C2 uses only its fixed local Docker socket")
        endpoint = "unix://" + SOCKET
        require(os.environ.get("DOCKER_HOST", endpoint) == endpoint, "C2 Docker endpoint mismatch")
        return SOCKET
    require(
        explicit.startswith("unix:///")
        and "%" not in explicit
        and "?" not in explicit
        and "#" not in explicit
        and "\x00" not in explicit,
        "CI requires an explicit local Unix socket URI",
    )
    path = explicit.removeprefix("unix://")
    require(
        str(Path(path)) == path and Path(path).is_absolute() and ".." not in Path(path).parts,
        "Non-canonical Docker socket",
    )
    require(os.environ.get("DOCKER_HOST") == explicit, "CLI/controller Docker endpoints differ")
    information = Path(path).lstat()
    require(stat.S_ISSOCK(information.st_mode) and information.st_uid in {0, os.getuid()}, "Unsafe Docker socket")
    return path


def validate_engine(versions: Json, profile: str) -> None:
    """Check the exact separately admitted vendor engine/API/runc tuple."""
    require(profile in PROFILE_ENGINES, "Unknown qualification profile")
    engine, api, runtime = PROFILE_ENGINES[profile]
    require(
        versions["ApiVersion"] == api
        and versions["Version"] == engine
        and any(item["Name"] == "runc" and item["Version"] == runtime for item in versions["Components"]),
        "Unsupported Docker/API/runc profile",
    )


def native_type(path: str | Path) -> int:
    """Observe filesystem identity without testing write access."""
    buffer = ctypes.create_string_buffer(256)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.statfs(os.fsencode(path), buffer) != 0:
        raise OSError(ctypes.get_errno(), str(path))
    return ctypes.c_long.from_buffer(buffer).value


def inventory() -> Json:
    """Read the actual controller namespace; never write any outer quota."""
    root = Path("/proc/sys")
    require(tuple(sorted(path.name for path in root.iterdir())) == TOP, "Kernel sysctl inventory changed")
    require(tuple(sorted(path.name for path in (root / "user").iterdir())) == QUOTAS, "User quota inventory changed")
    for parent, names, expected in ((root, TOP, stat.S_ISDIR), (root / "user", QUOTAS, stat.S_ISREG)):
        for name in names:
            path = parent / name
            require(expected(path.lstat().st_mode) and native_type(path) == PROC_MAGIC, "Non-native sysctl inventory")
    return {
        "top": TOP,
        "quotas": QUOTAS,
        "quota": (root / "user/max_user_namespaces").read_text().strip(),
        "userns": str(Path("/proc/self/ns/user").readlink()),
        "netns": str(Path("/proc/self/ns/net").readlink()),
        "kernel": os.uname().release,
    }


def observe() -> Json:
    """Record the trusted setup boundary, including its child-quota limitation."""
    status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines() if ":" in line)
    mounts = [
        line
        for line in Path("/proc/self/mountinfo").read_text().splitlines()
        if line.split()[4] == "/proc" or line.split()[4].startswith("/proc/sys")
    ]
    kernel = [line for line in mounts if line.split()[4] == "/proc/sys/kernel"]
    paths: list[Json] = []
    for name in ("/proc/sys/kernel", "/proc/sys/user/max_user_namespaces", *MASKS):
        information = Path(name).lstat()
        paths.append(
            {
                "path": name,
                "procfs": native_type(name) == PROC_MAGIC,
                "mode": stat.S_IFMT(information.st_mode),
                "rdev": information.st_rdev,
            }
        )
    return {
        "uid": os.getuid(),
        "gid": os.getgid(),
        "userns": str(Path("/proc/self/ns/user").readlink()),
        "netns": str(Path("/proc/self/ns/net").readlink()),
        "paths": paths,
        "mountinfo": mounts,
        "kernel_readonly_procfs": len(kernel) == 1
        and "ro" in kernel[0].split()[5].split(",")
        and native_type("/proc/sys/kernel") == PROC_MAGIC,
        "allowed_leaf_native_procfs": native_type("/proc/sys/user/max_user_namespaces") == PROC_MAGIC,
        "quota_masks_hold": all(native_type(path) != PROC_MAGIC for path in MASKS if "/user/" in path),
        "global_masks_hold": all(native_type(path) != PROC_MAGIC for path in MASKS if "/user/" not in path),
        "caps": {name: status[name].strip() for name in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")},
        "no_new_privs": status["NoNewPrivs"].strip(),
        "seccomp": status["Seccomp"].strip(),
        "lsm": Path("/proc/self/attr/current").read_bytes().decode(errors="replace"),
        "cgroup": {
            name: (Path("/sys/fs/cgroup") / name).read_text().strip() for name in ("memory.max", "cpu.max", "pids.max")
        },
    }


def inside_boundary() -> None:
    """Check ordinary test authority before any unchanged proof starts."""
    require(Path("/opt/lychd-scout-qualification").is_file(), "Qualification image required")
    outer = observe()
    profile = selected_profile()
    if profile == CI_PROFILE_NAME:
        require(outer["lsm"].strip() == "unconfined", "CI trusted outer AppArmor boundary differs")
    require(outer["uid"] == outer["gid"] == CHECK_UID, "Tests require ordinary check user")
    require(all(int(value, 16) == 0 for value in outer["caps"].values()), "Tests retained capabilities")
    require(outer["no_new_privs"] == "1" and outer["seccomp"] == "2", "Missing process restrictions")
    require(
        outer["kernel_readonly_procfs"] and outer["global_masks_hold"] and outer["quota_masks_hold"],
        "Outer procfs restrictions differ from admitted profile",
    )
    require(outer["allowed_leaf_native_procfs"], "Quota interface is not native procfs")
    require(outer["netns"] != os.environ["LYCHD_SCOUT_HOST_NETNS"], "Host network namespace reused")
    require([name for _, name in socket.if_nameindex()] == ["lo"], "Non-loopback interface")
    require(
        outer["cgroup"]["memory.max"] == str(2 * 1024**3) and outer["cgroup"]["pids.max"] == "256",
        "Missing cgroup memory/PID limits",
    )
    quota, period = outer["cgroup"]["cpu.max"].split()
    require(int(quota) == 2 * int(period), "Missing two-CPU limit")
    child = subprocess.run(  # noqa: S603 - Fixed metadata script and empty child environment.
        [sys.executable, "-I", "-S", __file__, "--observe-child"], capture_output=True, timeout=10, check=True, env={}
    )
    outer["fresh_child"] = json.loads(child.stdout)
    require(outer["fresh_child"]["userns"] != outer["userns"], "Fresh child user namespace unobserved")
    require(
        outer["fresh_child"]["kernel_readonly_procfs"] and outer["fresh_child"]["global_masks_hold"],
        "Child lost global restrictions",
    )
    outer["profile"] = profile
    outer["trusted_setup_limitation"] = "Native user-quota interfaces become visible in a fresh user namespace."
    outer["extraction_profile"] = json.loads(Path("/opt/scout-runtime.json").read_text())
    Path("/qualification/export/boundary.json").write_text(json.dumps(outer, indent=2) + "\n")


class EngineError(RuntimeError):
    """Preserve actual HTTP status for safe reconciliation."""

    def __init__(self, status: int, message: bytes) -> None:
        """Retain the actual bounded Engine error response."""
        super().__init__(f"Docker Engine HTTP {status}: {message[:1024]!r}")
        self.status = status


class Engine:
    """One admitted local endpoint; no remote endpoint or credential discovery."""

    def __init__(self, endpoint: str = SOCKET) -> None:
        self.endpoint = endpoint

    def request(
        self, method: str, path: str, body: Json | None = None, *, statuses: tuple[int, ...] = (200,), raw: bool = False
    ) -> Any:
        connection = http.client.HTTPConnection("localhost", timeout=10)
        connection.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.sock.settimeout(10)
        try:
            connection.sock.connect(self.endpoint)
            connection.request(
                method,
                API + path,
                body=None if body is None else json.dumps(body).encode(),
                headers={} if body is None else {"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            data = response.read(4 * 1024 * 1024 + 1)
            require(len(data) <= 4 * 1024 * 1024, "Oversized Engine response")
            if response.status not in statuses:
                raise EngineError(response.status, data)
            return data if raw else json.loads(data) if data else None
        finally:
            connection.close()


def security(options: list[str]) -> Json:
    """Compare embedded seccomp JSON semantically, rejecting duplicate options."""
    result: Json = {}
    for option in options:
        key, _, value = option.partition("=")
        require(key not in result, "Duplicate security option")
        result[key] = json.loads(value) if key == "seccomp" else value
    return result


def boundary(container: Json, image: str, environment: list[str]) -> None:
    """Validate every bootstrap effect before start; setup later drops all caps."""
    host, config = container["HostConfig"], container["Config"]
    require(container["Image"] == config["Image"] == image and config["User"] == "0:0", "Wrong image or setup user")
    require(config["Entrypoint"] == ["/usr/bin/timeout"] and config["Cmd"] == COMMAND, "Unreviewed command")
    require(config["Env"] == environment, "Unexpected environment")
    require(host["NetworkMode"] == "none" and not host["Privileged"], "Unexpected network/privilege")
    require(host["CapDrop"] == ["ALL"] and set(host["CapAdd"] or ()) == CAPS, "Unexpected setup capabilities")
    require(
        host["Memory"] == 2 * 1024**3 and host["NanoCpus"] == NANO_CPUS and host["PidsLimit"] == PIDS,
        "Unexpected resource limits",
    )
    require(
        not any(
            host.get(key) for key in ("Binds", "Mounts", "VolumesFrom", "Devices", "DeviceRequests", "PortBindings")
        ),
        "Unexpected host mount/device/port",
    )
    require(
        not container["Mounts"] and not config["Volumes"] and not host["PublishAllPorts"], "Unexpected exposed resource"
    )
    require(host["Sysctls"] == {"net.ipv4.ip_unprivileged_port_start": "0"}, "Unexpected sysctl")


def derive_profile(baseline: Json, profile: str, *, qualification_profile: str = PROFILE_NAME) -> Json:
    """Preserve observed defaults with the selected explicit trusted-setup delta."""
    require(qualification_profile in PROFILE_ENGINES, "Unknown qualification profile")
    host = copy.deepcopy(baseline)
    require(
        host["ReadonlyPaths"].count("/proc/sys") == 1 and bool(host["MaskedPaths"]),
        "Unexpected default path restrictions",
    )
    host["ReadonlyPaths"] = [path for path in host["ReadonlyPaths"] if path != "/proc/sys"]
    host["ReadonlyPaths"].append("/proc/sys/kernel")
    host["MaskedPaths"] += [path for path in MASKS if path not in host["MaskedPaths"]]
    host["SecurityOpt"] = ["no-new-privileges=true", "seccomp=" + profile, "label=disable"]
    if qualification_profile == CI_PROFILE_NAME:
        host["SecurityOpt"].append("apparmor=unconfined")
    return host


def validate_profile(actual: Json, baseline: Json, expected: Json) -> list[str]:
    """Reject ignored path/security fields and any unrelated daemon-side delta."""
    require(
        actual["MaskedPaths"] == expected["MaskedPaths"] and actual["ReadonlyPaths"] == expected["ReadonlyPaths"],
        "Path restrictions changed",
    )
    require(security(actual["SecurityOpt"]) == security(expected["SecurityOpt"]), "Security options changed")
    changed = {key for key in actual if actual[key] != baseline.get(key)}
    require(changed <= {"MaskedPaths", "ReadonlyPaths", "SecurityOpt"}, "Unexpected bootstrap configuration delta")
    return sorted(changed)


def export_archive(data: bytes, destination: Path) -> None:
    """Export only fixed safe JSON files, never arbitrary archive paths or keys."""
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            name = Path(member.name)
            if member.isdir() and member.name.rstrip("/") == "export":
                continue
            require(
                member.isfile()
                and len(name.parts) == ARTIFACT_PATH_PARTS
                and name.parts[0] == "export"
                and name.name in EXPORTS
                and 0 <= member.size <= 1024**2,
                "Unapproved export member",
            )
            stream = archive.extractfile(member)
            if stream is None:
                message = "Missing export body"
                raise ValueError(message)
            content = stream.read(1024**2 + 1)
            require(len(content) == member.size, "Truncated export")
            with (destination / name.name).open("xb") as output:
                output.write(content)


def validate_exports(directory: Path, *, profile: str = PROFILE_NAME) -> None:
    """Require the exact boundary and three distinct actual passed proof receipts."""
    require({path.name for path in directory.iterdir()} == EXPORTS, "Incomplete or extra safe export closure")
    boundary_record = json.loads((directory / "boundary.json").read_text())
    require(profile in PROFILE_ENGINES and boundary_record.get("profile") == profile, "Wrong measured boundary profile")
    identities = {
        "static": ("profile", "scout-static-extract@1"),
        "fetch": ("schema", "scout-fetch-local-proof@1"),
        "authority": ("schema", "scout-network-authority-local-proof@1"),
    }
    for phase, (field, expected) in identities.items():
        receipt = json.loads((directory / f"{phase}-receipt.json").read_text())
        checks = receipt.get("checks")
        require(
            receipt.get(field) == expected
            and receipt.get("status") == "passed"
            and isinstance(checks, list)
            and bool(cast("list[Any]", checks))
            and all(isinstance(value, str) for value in cast("list[Any]", checks)),
            "Incomplete or wrong actual proof receipt",
        )
        if phase == "fetch":
            require(receipt.get("extraction") == "passed_with_explicit_runtime_profile", "Missing actual extraction")


class Controller:
    """Track only fresh owned identities through failure and cancellation."""

    def __init__(self, output: Path, image: str, engine: Any = None, *, profile: str = PROFILE_NAME) -> None:
        """Bind a fresh occurrence without creating a container."""
        self.output, self.image = output, image
        self.engine: Any = Engine() if engine is None else engine
        self.occurrence = uuid.uuid4().hex
        self.owned: dict[str, str] = {}
        self.pending: dict[str, str] = {}
        self.summary: Json = {"occurrence": self.occurrence, "image": image, "profile": profile, "settlement": {}}

    def save(self, name: str, value: object) -> None:
        (self.output / name).write_text(json.dumps(value, indent=2) + "\n")

    def name(self, phase: str) -> str:
        return f"lychd-scout-{self.occurrence}-{phase}"

    def inspect(self, identity: str, phase: str) -> Json:
        value = self.engine.request("GET", f"/containers/{quote(identity, safe='')}/json")
        require(
            re.fullmatch("[a-f0-9]{64}", value["Id"])
            and value["Image"] == self.image
            and value["Name"] == "/" + self.name(phase)
            and value["Config"]["Labels"].get(LABEL) == self.occurrence
            and value["Config"]["Labels"].get(LABEL + ".phase") == phase,
            "Container ownership mismatch",
        )
        return value

    def register(self, identity: str, phase: str) -> None:
        require(re.fullmatch("[a-f0-9]{64}", identity), "Malformed created container identity")
        self.owned[identity] = phase
        self.pending.pop(phase, None)
        self.save(f"{phase}-identity.json", {"id": identity, "name": self.name(phase), "owner": self.occurrence})

    def reconcile(self, phase: str) -> None:
        try:
            value = self.inspect(self.name(phase), phase)
        except EngineError as error:
            if error.status != NOT_FOUND:
                raise
            self.save(
                f"{phase}-ambiguous-404.json",
                {
                    "name": self.name(phase),
                    "owner": self.occurrence,
                    "observation": "404; no blind create retry or claimed successful occurrence",
                },
            )
        else:
            self.register(value["Id"], phase)

    def remove(self, identity: str, phase: str) -> None:
        value = self.inspect(identity, phase)
        export_error = None
        try:
            if value["State"]["Running"]:
                self.engine.request("POST", f"/containers/{identity}/kill?signal=SIGKILL", statuses=(204, 409))
                value = self.inspect(identity, phase)
                require(
                    not value["State"]["Running"], "Kill acknowledged but exit still unobserved; force removal required"
                )
            self.save(f"{phase}-final-inspect.json", value)
            if phase == "proof":
                logs = self.engine.request("GET", f"/containers/{identity}/logs?stdout=1&stderr=1", raw=True)
                (self.output / "container-logs.bin").write_bytes(logs)
                archive = self.engine.request(
                    "GET", f"/containers/{identity}/archive?path=/qualification/export", raw=True
                )
                export_archive(archive, self.output / "raw")
        except BaseException as error:
            export_error = error
        delete_error = None
        try:
            self.engine.request("DELETE", f"/containers/{identity}?force=1&v=0", statuses=(204,))
        except BaseException as error:
            delete_error = error
        try:
            self.engine.request("GET", f"/containers/{identity}/json")
        except EngineError as error:
            require(error.status == NOT_FOUND, "Unproved owned container removal")
        else:
            message = "Owned container remained after removal"
            raise ValueError(message)
        self.owned.pop(identity)
        self.summary["settlement"][phase] = {"id": identity, "removed_and_404_observed": True}
        if delete_error is not None:
            self.summary["settlement"][phase]["delete_response_error_reconciled"] = str(delete_error)
        if export_error is not None:
            message = "Safe export failed after owned container settlement"
            raise RuntimeError(message) from export_error


def terminal(number: int, _frame: object) -> None:
    """Route cancellation through bounded owned-container settlement."""
    raise SystemExit(128 + number)


def run(image: str, output: Path, profile_path: Path) -> int:  # noqa: C901, PLR0912, PLR0915 - One bounded create/start/export/settle occurrence.
    """Build no image, run no host tests, and never update maintained receipts."""
    profile_name = selected_profile()
    endpoint = controller_socket(profile_name)
    require(re.fullmatch("sha256:[a-f0-9]{64}", image), "Exact existing image ID required")
    require(hashlib.sha256(profile_path.read_bytes()).hexdigest() == PROFILE_SHA256, "Unreviewed seccomp profile")
    require(
        output.is_absolute() and output.is_dir() and profile_path.resolve().parent == output.resolve(),
        "Existing private artifact directory and its profile required",
    )
    controller = Controller(output, image, Engine(endpoint), profile=profile_name)
    signal.signal(signal.SIGTERM, terminal)
    signal.signal(signal.SIGINT, terminal)
    result = 1
    before: Json = {}
    try:
        controller.save(
            "occurrence.json",
            {
                "owner": controller.occurrence,
                "image": image,
                "names": {phase: controller.name(phase) for phase in ("baseline", "proof")},
                "controller_pid": os.getpid(),
                "started_at": time.time(),
                "socket": endpoint,
            },
        )
        before = inventory()
        controller.save("host-before.json", before)
        versions = controller.engine.request("GET", "/version")
        controller.save("engine-version.json", versions)
        validate_engine(versions, profile_name)
        profile = profile_path.read_text()
        controller.save("profile-identity.json", {"sha256": hashlib.sha256(profile.encode()).hexdigest()})
        phase = "baseline"
        cli = [
            "docker",
            "--host",
            "unix://" + endpoint,
            "create",
            "--pull=never",
            "--name",
            controller.name(phase),
            "--label",
            f"{LABEL}={controller.occurrence}",
            "--label",
            f"{LABEL}.phase={phase}",
            "--network=none",
            "--cap-drop=ALL",
            *[f"--cap-add={name.removeprefix('CAP_')}" for name in sorted(CAPS)],
            "--security-opt=no-new-privileges",
            "--security-opt=seccomp=" + str(profile_path),
            "--memory=2g",
            "--cpus=2",
            "--pids-limit=256",
            "--user=0:0",
            "--sysctl=net.ipv4.ip_unprivileged_port_start=0",
            "--env=LYCHD_SCOUT_HOST_NETNS=" + before["netns"],
            "--env=LYCHD_SCOUT_QUALIFICATION_PROFILE=" + profile_name,
            "--entrypoint=/usr/bin/timeout",
            image,
            *COMMAND,
        ]
        controller.save("baseline-command.json", cli)
        controller.pending[phase] = controller.name(phase)
        created = subprocess.run(  # noqa: S603 - Fixed local Docker endpoint and bounded literal profile.
            cli, capture_output=True, text=True, timeout=20, check=False
        )
        controller.save(
            "baseline-create.json", {"exit": created.returncode, "stdout": created.stdout, "stderr": created.stderr}
        )
        if created.returncode and "already in use" in created.stderr:
            controller.pending.pop(phase)
        require(created.returncode == 0, "Baseline creation failed")
        controller.register(created.stdout.strip(), phase)
        require(not created.stderr.strip(), "Baseline creation emitted warnings")
        baseline = controller.inspect(created.stdout.strip(), phase)
        controller.save("baseline-inspect.json", baseline)
        boundary(baseline, image, baseline["Config"]["Env"])
        require(baseline["State"]["Status"] == "created", "Baseline was started")
        controller.remove(created.stdout.strip(), phase)
        config = copy.deepcopy(baseline["Config"])
        config["Hostname"] = ""
        config["Labels"][LABEL + ".phase"] = "proof"
        config["HostConfig"] = derive_profile(baseline["HostConfig"], profile, qualification_profile=profile_name)
        controller.save("proof-create-request.json", config)
        controller.pending["proof"] = controller.name("proof")
        try:
            created = controller.engine.request(
                "POST", "/containers/create?name=" + controller.name("proof"), config, statuses=(201,)
            )
        except EngineError as error:
            if error.status == CONFLICT:
                controller.pending.pop("proof")
            raise
        controller.register(created["Id"], "proof")
        controller.save("proof-create-response.json", created)
        require(not created.get("Warnings"), "Proof creation emitted warnings")
        observed = controller.inspect(created["Id"], "proof")
        if profile_name == CI_PROFILE_NAME:
            require(observed.get("AppArmorProfile") == "unconfined", "CI trusted outer AppArmor setting ignored")
        controller.save("proof-prestart-inspect.json", observed)
        boundary(observed, image, baseline["Config"]["Env"])
        changed = validate_profile(observed["HostConfig"], baseline["HostConfig"], config["HostConfig"])
        require(not observed["State"]["Running"], "Proof started before inspection")
        controller.save("prestart-accepted.json", {"changed_fields": sorted(changed), "masks": MASKS})
        started = time.monotonic()
        controller.engine.request("POST", f"/containers/{created['Id']}/start", statuses=(204,))
        while True:
            observed = controller.inspect(created["Id"], "proof")
            if not observed["State"]["Running"]:
                break
            require(time.monotonic() - started < MAX_RUN_SECONDS, "Proof runtime ceiling exceeded")
            time.sleep(0.25)
        controller.summary["proof_runtime_seconds"] = time.monotonic() - started
        controller.summary["proof_exit_code"] = observed["State"]["ExitCode"]
        result = 0 if observed["State"]["ExitCode"] == 0 else 1
    except BaseException as error:
        result = 1
        controller.summary["error"] = f"{type(error).__name__}: {error}"
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        for phase in list(controller.pending):
            try:
                controller.reconcile(phase)
            except BaseException as error:
                result = 1
                controller.summary.setdefault("unresolved_creates", {})[phase] = str(error)
        for identity, phase in list(controller.owned.items()):
            try:
                controller.remove(identity, phase)
            except BaseException as error:
                result = 1
                controller.summary.setdefault("unresolved_containers", {})[identity] = str(error)
        if result == 0:
            try:
                validate_exports(output / "raw", profile=profile_name)
            except BaseException as error:
                result = 1
                controller.summary["receipt_error"] = str(error)
        try:
            after = inventory()
            controller.save("host-after.json", after)
            require(after == before, "Host quota/inventory/namespace changed")
        except BaseException as error:
            result = 1
            controller.summary["host_observation_error"] = str(error)
        controller.summary["exit_code"] = result
        controller.save("result.json", controller.summary)
        sys.stdout.write(json.dumps(controller.summary, indent=2) + "\n")
        sys.stdout.flush()
    return result


if __name__ == "__main__":
    if sys.argv[1:] == ["--preflight-engine"]:
        selected = selected_profile()
        socket_path = controller_socket(selected)
        measured = Engine(socket_path).request("GET", "/version")
        validate_engine(measured, selected)
        sys.stdout.write(json.dumps({"profile": selected, "socket": socket_path, "engine": measured}, indent=2) + "\n")
    elif sys.argv[1:] == ["--observe-child"]:
        require(ctypes.CDLL(None).unshare(0x10000000) == 0, "Fresh child user namespace unavailable")
        sys.stdout.write(json.dumps(observe()) + "\n")
    elif sys.argv[1:] == ["--observe-inside"]:
        inside_boundary()
    else:
        require(
            len(sys.argv) == MAIN_ARGC, "Expected exact image ID, existing artifact directory and reviewed seccomp file"
        )
        raise SystemExit(run(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])))
