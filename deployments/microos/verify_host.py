#!/usr/bin/env python3
"""Observe the MicroOS pilot floor as the actual ordinary runtime user.

No sudo, package changes, image pulls, app initialization or service activation.
Podman may initialize its own metadata. Optional --container-image runs a short
probe in that explicit already-local image, with no host mounts or network.
This receipt cannot qualify nono, Codex containment, LychD or disaster recovery.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import pwd
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def run(*args: str) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=True, timeout=30)
    return result.stdout.strip()


def landlock_abi() -> int:
    """Query only; do not install rules or infer a sandbox from ABI availability."""
    if platform.machine() not in {"x86_64", "aarch64"}:
        raise ValueError("Landlock syscall mapping reviewed only for x86_64/aarch64")
    libc = ctypes.CDLL(None, use_errno=True)
    value = libc.syscall(444, 0, 0, 1)
    if value < 0:
        raise OSError(ctypes.get_errno(), "Landlock ABI query failed")
    return value


def version_at_least_54(text: str) -> bool:
    match = re.search(r"\b(\d+)\.(\d+)(?:\.(\d+))?", text)
    return match is not None and tuple(int(n or 0) for n in match.groups()) >= (5, 4, 0)


def local_image_id(value: str) -> str:
    """An immutable local ID cannot inject runtime flags or change with a tag."""
    if re.fullmatch(r"sha256:[a-f0-9]{64}", value) is None:
        raise argparse.ArgumentTypeError("use an already-local sha256: followed by 64 lowercase hex digits")
    return value


def home_storage_path(home: Path, value: str, label: str) -> Path:
    """Keep this pilot's effective persistent storage in its reviewed home budget."""
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{label} must be absolute")
    resolved, root = path.resolve(), home.resolve()
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError(f"{label} escapes the runtime home storage budget")
    return resolved


def effective_generator(paths: list[Path]) -> Path:
    """Respect generator directory precedence, including masks and overrides."""
    for directory in paths:
        candidate = directory / "podman-user-generator"
        if os.path.lexists(candidate):
            if (
                candidate.resolve() == Path("/dev/null")
                or not os.access(candidate, os.X_OK)
                or candidate.stat().st_size == 0
            ):
                raise ValueError(f"effective Quadlet generator masked/unexecutable: {candidate}")
            resolved = candidate.resolve(strict=True)
            if not stat.S_ISREG(resolved.stat().st_mode):
                raise ValueError("effective Quadlet executable must be a regular file")
            for component in (resolved, *resolved.parents, *candidate.parents):
                mode = component.stat()
                if mode.st_uid != 0 or mode.st_mode & 0o022:
                    raise ValueError(f"untrusted Quadlet executable ancestry: {component}")
            return candidate
    raise ValueError("effective Quadlet user generator absent")


def generator() -> Path:
    override = os.environ.get("SYSTEMD_GENERATOR_PATH")
    if override is not None:
        raise ValueError("unset SYSTEMD_GENERATOR_PATH before verifying the login user manager")
    if any(
        line.startswith("SYSTEMD_GENERATOR_PATH=")
        for line in run("systemctl", "--user", "show-environment").splitlines()
    ):
        raise ValueError("user manager has a SYSTEMD_GENERATOR_PATH override; inspect it through the admin path")
    # systemd.generator(7): /run overrides /etc, then /usr/local, then /usr.
    return effective_generator(
        [
            Path(p)
            for p in (
                "/run/systemd/user-generators",
                "/etc/systemd/user-generators",
                "/usr/local/lib/systemd/user-generators",
                "/usr/lib/systemd/user-generators",
            )
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--container-image", type=local_image_id, help="already-local sha256 image ID with python3; never pulled"
    )
    args = parser.parse_args()
    results = []

    def check(label: str, probe) -> None:
        try:
            detail = probe()
            if detail is False:
                raise ValueError("required condition absent")
            results.append({"check": label, "status": "pass", "detail": str(detail)})
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            results.append({"check": label, "status": "fail", "detail": str(error)})

    uid = os.getuid()
    if uid == 0 or os.geteuid() != uid or os.environ.get("SUDO_USER"):
        print("Refused: log in directly as the ordinary runtime account; no sudo.", file=sys.stderr)
        return 2
    user = pwd.getpwuid(uid)
    home = Path(user.pw_dir)
    receipt = Path("/etc/lychd-host-bootstrap.json")

    def identity():
        data = json.loads(receipt.read_text())
        if (data["runtime_user"], data["uid"], data["gid"]) != (user.pw_name, uid, os.getgid()):
            raise ValueError("login identity differs from bootstrap receipt")
        if Path(os.environ.get("HOME", "")).resolve() != home.resolve():
            raise ValueError("HOME differs from the account database")
        return f"{user.pw_name} uid={uid} gid={os.getgid()} home={home}"

    def podman():
        info = json.loads(run("podman", "info", "--format=json"))
        host = info["host"]
        if (
            host["security"]["rootless"] is not True
            or host["cgroupVersion"] != "v2"
            or host["cgroupManager"] != "systemd"
        ):
            raise ValueError("Podman needs rootless=true, cgroupVersion=v2, cgroupManager=systemd")
        if host["security"].get("selinuxEnabled") is not True:
            raise ValueError("Podman reports SELinux disabled")
        version = run("podman", "--version")
        if not version_at_least_54(version):
            raise ValueError(version)
        graph_root = home_storage_path(home, info["store"]["graphRoot"], "Podman graphRoot")
        if run("findmnt", "-n", "-o", "FSTYPE", "-T", str(graph_root)) != "btrfs":
            raise ValueError("effective Podman graphRoot is not on Btrfs")
        if run("findmnt", "-n", "-o", "TARGET", "-T", str(graph_root)) != "/home":
            raise ValueError("effective Podman graphRoot is not on the reviewed /home mount")
        return f"{version}; graphRoot={graph_root}"

    def xdg_storage():
        defaults = {
            "XDG_CONFIG_HOME": home / ".config",
            "XDG_DATA_HOME": home / ".local/share",
            "XDG_CACHE_HOME": home / ".cache",
        }
        for key, default in defaults.items():
            home_storage_path(home, os.environ.get(key) or str(default), key)
        return "effective XDG roots remain under the runtime home; recheck after application initialization"

    def quadlet():
        executable = generator()
        version = run(str(executable), "--version")
        if not version_at_least_54(version):
            raise ValueError(version)
        return f"{executable}: {version}"

    def landlock():
        abi = landlock_abi()
        if abi < 6:
            raise ValueError(f"Landlock ABI {abi}; pilot requires >=6")
        return f"ABI {abi}; availability only, no confinement qualification"

    def masked(unit):
        result = subprocess.run(
            ["systemctl", "is-enabled", unit], check=False, capture_output=True, text=True, timeout=10
        )
        return result.returncode in {0, 1} and result.stdout.strip() == "masked"

    def capacity():
        minimum = json.loads(receipt.read_text())["home_min_free_gib"]
        free = shutil.disk_usage(home).free
        if free < minimum * 1024**3:
            raise ValueError(f"home free bytes {free}, below configured {minimum} GiB")
        return f"{free} free bytes (shared Btrfs capacity is not a reservation)"

    def mappings():
        for kind in ("uid", "gid"):
            mapping = run("podman", "unshare", "cat", f"/proc/self/{kind}_map")
            rows = [[int(value) for value in line.split()] for line in mapping.splitlines()]
            if not any(len(row) == 3 and row[0] >= 1 and row[2] >= 65536 for row in rows):
                raise ValueError(f"effective subordinate {kind} map lacks >=65536 IDs")
        return "effective rootless UID and GID namespaces contain subordinate ranges"

    def firewall():
        if run("firewall-cmd", "--get-default-zone") != "lychd-host":
            raise ValueError("default firewall zone differs")
        active = run("firewall-cmd", "--get-active-zones")
        zones = {line.strip() for line in active.splitlines() if line and not line[0].isspace()}
        if zones - {"lychd-host"}:
            raise ValueError(f"non-pilot active firewall zones: {sorted(zones)}")
        for option, expected in (
            ("--get-target", "DROP"),
            ("--list-ports", "22/tcp"),
            ("--list-services", ""),
            ("--list-rich-rules", ""),
            ("--list-forward-ports", ""),
            ("--list-source-ports", ""),
            ("--list-protocols", ""),
        ):
            if run("firewall-cmd", "--zone=lychd-host", option) != expected:
                raise ValueError(f"unexpected live firewall state for {option}")
        return "default DROP with TCP22 only; all active zones are the pilot zone"

    check("bootstrap identity", identity)
    check("Linux", lambda: platform.system() == "Linux")
    check("MicroOS", lambda: platform.freedesktop_os_release().get("ID") == "opensuse-microos")
    check("read-only OS root", lambda: "ro" in run("findmnt", "-n", "-o", "OPTIONS", "-T", "/").split(","))
    check("root Btrfs", lambda: run("findmnt", "-n", "-o", "FSTYPE", "-T", "/") == "btrfs")
    check("home Btrfs mount", lambda: run("findmnt", "-n", "-o", "FSTYPE", "--mountpoint", "/home") == "btrfs")
    check("runtime data Btrfs", lambda: run("findmnt", "-n", "-o", "FSTYPE", "-T", str(home)) == "btrfs")
    check("home free capacity", capacity)
    check("XDG storage paths", xdg_storage)
    check("cgroup v2", lambda: Path("/sys/fs/cgroup/cgroup.controllers").is_file())
    check("SELinux enforcing", lambda: run("getenforce") == "Enforcing")
    check(
        "home SSH labels",
        lambda: (
            run("matchpathcon", "-V", str(home), str(home / ".ssh"), str(home / ".ssh/authorized_keys"))
            or "matchpathcon agrees"
        ),
    )
    check("linger", lambda: run("loginctl", "show-user", user.pw_name, "--property=Linger", "--value") == "yes")
    check("user bus and manager", lambda: run("systemctl", "--user", "show", "--property=Version", "--value"))
    check("rootless Podman", podman)
    check("effective subordinate mappings", mappings)
    check("effective user Quadlet >=5.4", quadlet)
    check("host Landlock >=6", landlock)
    check("automatic OS update timer masked", lambda: masked("transactional-update.timer"))
    check("automatic reboot service masked", lambda: masked("rebootmgr.service"))
    check("host firewall active", lambda: run("systemctl", "is-active", "firewalld.service") == "active")
    check("SSH-only live firewall zones", firewall)
    check("git", lambda: run("git", "--version"))
    results.append(
        {
            "check": "uv operator hand-off",
            "status": "pass" if shutil.which("uv") else "pending",
            "detail": "not installed by bootstrap; review upstream installation separately",
        }
    )
    if args.container_image:

        def container_landlock():
            code = "import ctypes,os; c=ctypes.CDLL(None,use_errno=True); a=c.syscall(444,0,0,1); print(a); assert a>=6, (a,ctypes.get_errno())"
            return run(
                "podman",
                "run",
                "--rm",
                "--pull=never",
                "--network=none",
                "--read-only",
                "--cap-drop=all",
                "--security-opt=no-new-privileges",
                "--pids-limit=64",
                "--memory=128m",
                "--entrypoint=python3",
                args.container_image,
                "-c",
                code,
            )

        check("explicit container Landlock >=6", container_landlock)
    else:
        results.append(
            {
                "check": "container Landlock",
                "status": "pending",
                "detail": "requires --container-image EXACT-LOCAL-IMAGE with python3; no default/pull",
            }
        )
    print(json.dumps({"scope": "host floor observations only", "checks": results}, indent=2))
    return 1 if any(item["status"] == "fail" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
