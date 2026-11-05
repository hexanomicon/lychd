#!/usr/bin/env python3
"""Fresh-first-boot host floor; never adopt accounts or operate LychD services.

Only --check-config is intended for a development machine. --apply has no test-root
override and requires the actual offline Combustion transaction. Unit tests call
the pure validators; they never execute provisioning commands.
"""

from __future__ import annotations

import argparse
import base64
import grp
import json
import os
import pwd
import re
import shutil
import stat
import struct
import subprocess
import sys
from itertools import pairwise
from pathlib import Path


class Refusal(ValueError):
    """The supplied intent or observed host is outside this first-boot contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def exact_keys(value: object, keys: set[str], label: str) -> dict:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == keys, f"{label}: missing or unknown keys")
    return value


def integer(value: object, low: int, high: int, label: str) -> int:
    require(type(value) is int and low <= value <= high, f"invalid {label}")
    return value


def no_duplicates(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def validate_config(config: object) -> dict:
    """Validate closed versioned intent without executing or sourcing it."""
    cfg = exact_keys(
        config, {"schema_version", "hostname", "home_min_free_gib", "runtime_user", "recovery_root_ssh"}, "config"
    )
    integer(cfg["schema_version"], 1, 1, "schema_version")
    require(
        isinstance(cfg["hostname"], str)
        and re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", cfg["hostname"]) is not None,
        "hostname must be one DNS label",
    )
    integer(cfg["home_min_free_gib"], 10, 1024 * 1024, "home_min_free_gib")
    user = exact_keys(
        cfg["runtime_user"],
        {"name", "uid", "gid", "subuid_start", "subuid_count", "subgid_start", "subgid_count", "ssh_public_keys"},
        "runtime_user",
    )
    require(
        isinstance(user["name"], str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,30}", user["name"]) is not None,
        "invalid account name",
    )
    require(user["name"] not in {"root", "nobody", "daemon"}, "reserved runtime account")
    integer(user["uid"], 1000, 60000, "uid")
    integer(user["gid"], 1000, 60000, "gid")
    for kind in ("uid", "gid"):
        start = integer(user[f"sub{kind}_start"], 65536, 2**32 - 2, f"sub{kind}_start")
        count = integer(user[f"sub{kind}_count"], 65536, 2**32 - 2, f"sub{kind}_count")
        require(start + count <= 2**32 - 1, "subordinate interval overflows")
    recovery = exact_keys(cfg["recovery_root_ssh"], {"enabled", "public_keys"}, "recovery_root_ssh")
    require(recovery["enabled"] is True, "explicit separate root SSH recovery is required for this pilot")
    for paths in (user["ssh_public_keys"], recovery["public_keys"]):
        require(isinstance(paths, list) and 1 <= len(paths) <= 8, "supply 1..8 public key files per account")
        require(
            all(isinstance(p, str) and re.fullmatch(r"keys/[A-Za-z0-9_-]+\.pub", p) for p in paths),
            "keys must be keys/NAME.pub paths",
        )
        require(len(set(paths)) == len(paths), "duplicate public key path")
    return cfg


def public_key(path: Path) -> str:
    """Accept exactly one Ed25519 public key, without authorized_keys options."""
    require(not path.parent.is_symlink() and not path.is_symlink(), "public key symlink refused")
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and 1 <= info.st_size <= 4096, "invalid public key file")
    lines = path.read_text(encoding="ascii").splitlines()
    require(len(lines) == 1, "public key must occupy exactly one line")
    parts = lines[0].split()
    require(len(parts) >= 2 and parts[0] == "ssh-ed25519", "only plain Ed25519 public keys are accepted")
    try:
        raw = base64.b64decode(parts[1], validate=True)
    except ValueError as error:
        raise Refusal("invalid public key base64") from error
    require(
        len(raw) == 51 and raw[:19] == struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32),
        "invalid Ed25519 public key encoding",
    )
    return "ssh-ed25519 " + parts[1]


def load_config(path: Path) -> tuple[dict, list[str], list[str]]:
    require(not path.is_symlink() and path.stat().st_size <= 16384, "invalid config file")
    cfg = validate_config(json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicates))
    runtime = [public_key(path.parent / p) for p in cfg["runtime_user"]["ssh_public_keys"]]
    recovery = [public_key(path.parent / p) for p in cfg["recovery_root_ssh"]["public_keys"]]
    require(
        len(set(runtime + recovery)) == len(runtime + recovery), "runtime and recovery must use distinct public keys"
    )
    return cfg, runtime, recovery


def validate_ranges(text: str, name: str, uid: int, start: int, count: int, real_ids: set[int]) -> None:
    """Refuse all collisions and any prior mapping of the new account."""
    require(start >= 65536 and count >= 65536 and start + count <= 2**32 - 1, "invalid subordinate interval")
    intervals = [(start, start + count)]
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split(":")
        require(
            len(fields) == 3
            and re.fullmatch(r"(?:[A-Za-z_][A-Za-z0-9_$-]*|[0-9]+)", fields[0]) is not None
            and re.fullmatch(r"[0-9]+", fields[1]) is not None
            and re.fullmatch(r"[0-9]+", fields[2]) is not None,
            "malformed subordinate mapping",
        )
        owner, first, length = fields[0], int(fields[1]), int(fields[2])
        require(owner not in {name, str(uid)}, "existing runtime mapping: adoption/remapping refused")
        require(first >= 1 and length >= 1 and first + length <= 2**32 - 1, "invalid existing subordinate interval")
        intervals.append((first, first + length))
    ordered = sorted(intervals)
    require(all(left[1] <= right[0] for left, right in pairwise(ordered)), "overlapping subordinate intervals")
    require(
        all(not any(start <= value < end for value in real_ids) for start, end in ordered),
        "subordinate range overlaps a real ID",
    )


def validate_host_state(cfg: dict, facts: dict) -> None:
    """Pure refusal oracle, including failures that precede account creation."""
    require(facts["euid"] == 0, "requires root inside Combustion")
    require(
        facts["offline"] and facts["firstboot"] and facts["combustion_directory"],
        "requires fresh offline Combustion transaction",
    )
    require(facts["microos"] and not facts["completed"], "requires fresh openSUSE MicroOS")
    require(
        facts["root_btrfs"] and facts["home_btrfs_mount"], "installer must provide Btrfs root and mounted Btrfs /home"
    )
    require(facts["home_free"] >= cfg["home_min_free_gib"] * 1024**3, "insufficient /home free capacity")
    require(not facts["account_collision"], "existing account, UID, GID or group: adoption refused")
    require(not facts["home_exists"], "existing runtime home: adoption refused")
    require(not facts["custom_state"], "existing SSH, firewall, sudo or bootstrap state refused")
    require(facts["selinux_configured"], "SELinux must already be configured enforcing")


def run(*argv: str) -> str:
    result = subprocess.run(
        argv,
        check=True,
        text=True,
        capture_output=True,
        timeout=120,
        env={**os.environ, "LC_ALL": "C", "PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "SYSTEMD_OFFLINE": "1"},
    )
    return result.stdout.strip()


def existing(path: str) -> bool:
    return os.path.lexists(path)


def inspect_host(cfg: dict) -> None:
    """Inspect the real host; there is deliberately no alternate-root option."""
    user = cfg["runtime_user"]
    passwd, groups = pwd.getpwall(), grp.getgrall()
    os_release = Path("/etc/os-release").read_text()
    selinux = Path("/etc/selinux/config").read_text()
    hostname = Path("/etc/hostname")
    require(not hostname.is_symlink(), "hostname symlink refused")
    require(
        not hostname.exists()
        or hostname.read_text().strip() in {"", "localhost", "localhost.localdomain", cfg["hostname"]},
        "installer hostname differs from explicit config",
    )
    custom = any(
        existing(p)
        for p in (
            "/root/.ssh/authorized_keys",
            "/etc/ssh/sshd_config.d/00-lychd-host.conf",
            "/etc/firewalld/zones/lychd-host.xml",
            "/etc/firewalld/direct.xml",
            "/var/lib/lychd-host-bootstrap.started",
        )
    )
    for directory in (
        "/etc/firewalld/zones",
        "/etc/firewalld/policies",
        "/etc/sudoers.d",
    ):
        if Path(directory).exists():
            custom = custom or any(p.is_file() and not p.name.startswith(".") for p in Path(directory).iterdir())
    # Require pristine package-owned firewall/SSH/sudo files; never adopt edits.
    for package in ("openssh-server", "openssh-common", "firewalld", "sudo"):
        installed = subprocess.run(["rpm", "-q", package], capture_output=True, check=False).returncode == 0
        if installed:
            custom = custom or bool(run("rpm", "-V", package))
    validate_host_state(
        cfg,
        {
            "euid": os.geteuid(),
            "offline": subprocess.run(["systemd-detect-virt", "--quiet", "--chroot"], check=False).returncode == 0,
            "firstboot": not os.path.lexists("/etc/machine-id"),
            "combustion_directory": Path.cwd() == Path("/dev/shm/combustion/config"),
            "microos": re.search(r'^ID="?opensuse-microos"?$', os_release, re.MULTILINE) is not None,
            "completed": existing("/etc/lychd-host-bootstrap.json"),
            "root_btrfs": run("findmnt", "-n", "-o", "FSTYPE", "-T", "/") == "btrfs",
            "home_btrfs_mount": run("findmnt", "-n", "-o", "FSTYPE", "--mountpoint", "/home") == "btrfs",
            "home_free": shutil.disk_usage("/home").free,
            "account_collision": any(
                p.pw_name == user["name"] or p.pw_uid == user["uid"] or 1000 <= p.pw_uid < 60000 for p in passwd
            )
            or any(g.gr_name == user["name"] or g.gr_gid == user["gid"] for g in groups),
            "home_exists": existing(f"/home/{user['name']}"),
            "custom_state": custom,
            "selinux_configured": re.search(r"^SELINUX=enforcing$", selinux, re.MULTILINE) is not None,
        },
    )
    for line in Path("/etc/nsswitch.conf").read_text().splitlines():
        setting = line.split("#", 1)[0].strip()
        require(
            not setting.startswith("subid:") or setting.split(":", 1)[1].strip() == "files",
            "only file-backed subordinate IDs supported",
        )
    for kind, identities in (
        ("uid", {p.pw_uid for p in passwd} | {user["uid"]}),
        ("gid", {g.gr_gid for g in groups} | {user["gid"]}),
    ):
        path = Path(f"/etc/sub{kind}")
        require(not path.is_symlink(), "subordinate mapping symlink refused")
        validate_ranges(
            path.read_text() if path.exists() else "",
            user["name"],
            user["uid"],
            user[f"sub{kind}_start"],
            user[f"sub{kind}_count"],
            identities,
        )


def create_file(path: Path, data: str, mode: int = 0o600, uid: int = 0, gid: int = 0) -> None:
    """No-clobber publication in first-boot root-controlled directories."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, "w") as file:
        os.fchown(file.fileno(), uid, gid)
        os.fchmod(file.fileno(), mode)
        file.write(data)
        file.flush()
        os.fsync(file.fileno())


def install_keys(home: Path, keys: list[str], uid: int, gid: int) -> None:
    directory = home / ".ssh"
    require(not directory.is_symlink(), "SSH directory symlink refused")
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.stat()
    require(info.st_uid == uid and stat.S_IMODE(info.st_mode) == 0o700, "unsafe SSH directory")
    os.chown(directory, uid, gid)
    create_file(directory / "authorized_keys", "\n".join(keys) + "\n", uid=uid, gid=gid)


def apply(cfg: dict, runtime_keys: list[str], recovery_keys: list[str]) -> None:
    inspect_host(cfg)
    # /var and /home survive OS snapshot rollback. Any interruption requires
    # console inspection/reimage; never rerun and adopt partially created state.
    create_file(
        Path("/var/lib/lychd-host-bootstrap.started"), "First-boot host bootstrap started; preserve on failure.\n"
    )
    user = cfg["runtime_user"]
    name, uid, gid = user["name"], user["uid"], user["gid"]
    run("groupadd", "--gid", str(gid), name)
    run(
        "useradd",
        "--uid",
        str(uid),
        "--gid",
        str(gid),
        "--home-dir",
        f"/home/{name}",
        "--create-home",
        "--shell",
        "/bin/bash",
        "--no-user-group",
        "-K",
        "SUB_UID_COUNT=0",
        "-K",
        "SUB_GID_COUNT=0",
        name,
    )
    for kind in ("uid", "gid"):
        start, count = user[f"sub{kind}_start"], user[f"sub{kind}_count"]
        run("usermod", f"--add-sub{kind}s", f"{start}-{start + count - 1}", name)
    home = Path(f"/home/{name}")
    os.chmod(home, 0o700)
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir(mode=0o700)
    os.chown(ssh_dir, uid, gid)
    install_keys(home, runtime_keys, uid, gid)
    install_keys(Path("/root"), recovery_keys, 0, 0)
    Path("/etc/ssh/sshd_config.d").mkdir(mode=0o755, exist_ok=True)
    create_file(
        Path("/etc/ssh/sshd_config.d/00-lychd-host.conf"),
        f"Port 22\nPasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitEmptyPasswords no\nPubkeyAuthentication yes\nUsePAM yes\nPermitRootLogin prohibit-password\nAllowUsers root {name}\n",
        0o600,
    )
    run("ssh-keygen", "-A")
    run("sshd", "-t")
    effective = run("sshd", "-T")
    for setting in ("port 22", "passwordauthentication no", "kbdinteractiveauthentication no", "usepam yes"):
        require(setting in effective.splitlines(), f"effective SSH setting not admitted: {setting}")
    require(
        any(
            setting in effective.splitlines()
            for setting in ("permitrootlogin without-password", "permitrootlogin prohibit-password")
        ),
        "root SSH must require public keys",
    )
    # Fresh offline firewall: one zone, default DROP, SSH TCP/22 only.
    run("firewall-offline-cmd", "--new-zone=lychd-host")
    run("firewall-offline-cmd", "--zone=lychd-host", "--set-target=DROP")
    run("firewall-offline-cmd", "--zone=lychd-host", "--add-port=22/tcp")
    run("firewall-offline-cmd", "--set-default-zone=lychd-host")
    run("firewall-offline-cmd", "--check-config")
    Path("/etc/hostname").write_text(cfg["hostname"] + "\n")
    # Offline loginctl cannot reach a live bus. This is loginctl's persistent
    # linger marker; real login/user-manager behavior is verified after boot.
    Path("/var/lib/systemd/linger").mkdir(mode=0o755, exist_ok=True)
    create_file(Path("/var/lib/systemd/linger") / name, "", 0o644)
    run("systemctl", "--root=/", "enable", "sshd.service", "firewalld.service")
    run("systemctl", "--root=/", "mask", "transactional-update.timer", "rebootmgr.service")
    run(
        "restorecon",
        "-RF",
        str(home),
        "/root/.ssh",
        "/etc/ssh/sshd_config.d",
        "/etc/firewalld",
        "/var/lib/systemd/linger",
    )
    run("matchpathcon", "-V", str(home), str(ssh_dir), str(ssh_dir / "authorized_keys"), "/root/.ssh/authorized_keys")
    create_file(
        Path("/etc/lychd-host-bootstrap.json"),
        json.dumps(
            {
                "schema_version": 1,
                "runtime_user": name,
                "uid": uid,
                "gid": gid,
                "home_min_free_gib": cfg["home_min_free_gib"],
            },
            indent=2,
        )
        + "\n",
        0o644,
    )
    print("First-boot host preparation complete. Real-boot ordinary-user verification remains required.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-config", type=Path)
    group.add_argument("--apply", type=Path)
    args = parser.parse_args()
    try:
        cfg, runtime, recovery = load_config(args.check_config or args.apply)
        if args.apply:
            apply(cfg, runtime, recovery)
        else:
            print("Config and separate public keys valid; no host acceptance or mutation performed.")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"MicroOS bootstrap refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
