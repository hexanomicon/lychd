#!/usr/bin/env python3
"""Read-only installed Tumbleweed floor probe; JSON intent on stdin.

Never initializes Podman storage, changes maps or installs anything. Its
mechanism observations do not qualify rootless execution or application recovery.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import grp
import json
import os
import platform
import pwd
import re
import shutil
import stat
import struct
import subprocess
import sys
from pathlib import Path


class Refusal(ValueError):
    """The intent or observed host does not fit this narrow floor."""


def require(value: bool, message: str) -> None:
    if not value:
        raise Refusal(message)


def validate_intent(value: object) -> dict:
    """Keep all variable-derived process arguments in a closed data schema."""
    require(isinstance(value, dict), "intent must be an object")
    require(
        set(value) == {"name", "uid", "gid", "subuid_start", "subgid_start", "count", "keys"},
        "unknown or missing intent fields",
    )
    require(value["name"] == "lychd", "explicit runtime name must be lychd")
    for key in ("uid", "gid"):
        require(
            type(value[key]) is int and 1000 <= value[key] <= 60000, f"{key} must be an ordinary explicit numeric ID"
        )
    require(type(value["count"]) is int and value["count"] == 65536, "exactly 65536 subordinate IDs are required")
    for key in ("subuid_start", "subgid_start"):
        require(type(value[key]) is int and 65536 <= value[key] <= 2**32 - 1 - value["count"], f"invalid {key}")
    keys = value["keys"]
    require(
        isinstance(keys, list) and 1 <= len(keys) <= 16,
        "supply 1..16 runtime SSH public keys in private variables outside the checkout",
    )
    for key in keys:
        require(
            isinstance(key, str) and len(key) <= 8192 and "\n" not in key and "\r" not in key,
            "one public key per line required",
        )
        fields = key.split()
        require(
            len(fields) >= 2
            and fields[0]
            in {
                "ssh-ed25519",
                "ssh-rsa",
                "ecdsa-sha2-nistp256",
                "ecdsa-sha2-nistp384",
                "ecdsa-sha2-nistp521",
                "sk-ssh-ed25519@openssh.com",
                "sk-ecdsa-sha2-nistp256@openssh.com",
            },
            "plain public keys only; no authorized_keys options",
        )
        try:
            raw = base64.b64decode(fields[1], validate=True)
            size = struct.unpack(">I", raw[:4])[0]
        except (ValueError, struct.error) as error:
            raise Refusal("invalid SSH public key encoding") from error
        require(raw[4 : 4 + size] == fields[0].encode(), "SSH public key type mismatch")
        checked = subprocess.run(
            ["ssh-keygen", "-lf", "-"], input=key + "\n", text=True, capture_output=True, timeout=10, check=False
        )
        require(checked.returncode == 0, "ssh-keygen rejected a supplied public key")
    identities = [" ".join(k.split()[:2]) for k in keys]
    require(len(set(identities)) == len(keys), "duplicate SSH public keys")
    return value


def parse_mounts(text: str) -> dict:
    """Only exact mountpoints count; inherited parent mounts are insufficient."""
    result = {}
    for line in text.splitlines():
        left, right = line.split(" - ", 1)
        fields, tail = left.split(), right.split()
        if fields[4] in {"/", "/home", "/var"}:
            require(fields[4] not in result, "stacked host mountpoints are refused")
            result[fields[4]] = {
                "device": fields[2],
                "root": fields[3],
                "fstype": tail[0],
                "options": fields[5].split(","),
            }
    return result


def validate_mounts(mounts: dict, inodes: dict) -> None:
    require(set(mounts) == {"/", "/home", "/var"}, "installer must provide explicit /, /home and /var mounts")
    require(all(m["fstype"] == "btrfs" for m in mounts.values()), "root, /home and /var must be Btrfs")
    require(
        len({m["device"] for m in mounts.values()}) == 1, "root, /home and /var must use one existing Btrfs filesystem"
    )
    require(len({m["root"] for m in mounts.values()}) == 3, "root, /home and /var must mount distinct subvolumes")
    require(all("rw" in m["options"] for m in mounts.values()), "host floor requires writable mounted subvolumes")
    require(
        all(inodes[p] == 256 for p in ("/", "/home", "/var")),
        "mounts must be Btrfs subvolume roots, not bind-mounted ordinary directories",
    )
    require(
        all("/.snapshots/" not in mounts[p]["root"] for p in ("/home", "/var")),
        "/home and /var must not be snapshot mounts",
    )


def validate_ranges(text: str, name: str, real_id: int, start: int, count: int, real_ids: set[int]) -> bool:
    """Refuse collisions globally and all differing pre-existing runtime maps."""
    intervals, own = [], []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split(":")
        require(
            len(fields) == 3
            and re.fullmatch(r"(?:[A-Za-z_][A-Za-z0-9_$-]*|[0-9]+)", fields[0]) is not None
            and fields[1].isdigit()
            and fields[2].isdigit(),
            "malformed subordinate-ID file",
        )
        first, size = int(fields[1]), int(fields[2])
        require(first > 0 and size > 0 and first + size <= 2**32 - 1, "invalid existing subordinate range")
        if fields[0] in {name, str(real_id)}:
            own.append((fields[0], first, size))
        else:
            intervals.append((first, first + size))
    require(
        not own or own == [(name, start, count)],
        "existing runtime subid mapping differs; never remap or migrate active containers",
    )
    intervals.append((start, start + count))
    intervals.sort()
    require(all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:])), "overlapping subordinate ranges")
    require(
        all(not any(a <= value < b for value in real_ids | {real_id}) for a, b in intervals),
        "subordinate range overlaps a real host ID",
    )
    return bool(own)


def validate_receipt(
    receipt: object, intent: dict, account_exists: bool, group_exists: bool, maps: dict, linger: bool
) -> str:
    """Never infer map safety from a container path or an intent-only receipt.

    A run interrupted before the initialized-maps receipt needs manual recovery.
    After that atomic checkpoint, both exact maps must remain present forever.
    """
    if receipt is None:
        require(
            not account_exists and not group_exists and not any(maps.values()) and not linger,
            "unmanaged runtime identity, maps or linger; adoption refused",
        )
        return "absent"
    expected = {k: v for k, v in intent.items() if k != "keys"}
    require(
        isinstance(receipt, dict) and set(receipt) == {"schema_version", "stage", "identity"},
        "unknown/legacy management receipt; manual recovery required",
    )
    require(
        type(receipt["schema_version"]) is int and receipt["schema_version"] == 1,
        "unsupported management receipt schema",
    )
    require(receipt["identity"] == expected, "managed identity intent differs; ID changes are refused")
    stage = receipt["stage"]
    require(stage in {"creating", "maps_initialized", "configured"}, "unknown management receipt stage")
    require(stage != "creating", "interrupted pre-map creation; manual recovery required")
    require(
        account_exists and group_exists and all(maps.values()),
        "initialized identity requires exact retained maps regardless of container storage path; manual recovery required",
    )
    return stage


def validate_mount_parent(info: os.stat_result) -> None:
    """The runtime UID must not be able to replace its home during useradd."""
    require(
        stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
        "root and /home mount roots must be root-owned and not group/world writable",
    )


def require_no_sudo() -> None:
    """Check effective policy for the actual account; ambiguous policy fails closed."""
    if shutil.which("sudo"):
        sudo = subprocess.run(
            ["sudo", "-n", "-l", "-U", "lychd"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
        require(
            sudo.returncode == 1 and "not allowed" in (sudo.stdout + sudo.stderr).lower(),
            "runtime sudo grants or indeterminate sudo policy; administrator must resolve",
        )


def observe_identity(intent: dict) -> dict:
    """Post-creation gate before maps, keys or linger can make the UID useful."""
    require(
        os.geteuid() == 0 and os.environ.get("SUDO_USER") != "lychd",
        "use the separate existing administrator with become",
    )
    account, group = pwd.getpwnam("lychd"), grp.getgrnam("lychd")
    require(
        account.pw_uid == intent["uid"]
        and account.pw_gid == intent["gid"]
        and account.pw_dir == "/home/lychd"
        and account.pw_shell == "/bin/bash"
        and group.gr_gid == intent["gid"]
        and not group.gr_mem,
        "post-creation runtime identity differs",
    )
    require(not any("lychd" in g.gr_mem for g in grp.getgrall()), "runtime supplementary groups refused")
    require_no_sudo()
    return {"identity": "ordinary runtime account", "sudo": "no grants observed"}


def observe_maps(intent: dict) -> dict:
    """Confirm both exact maps before the root-owned initialization checkpoint."""
    observe_identity(intent)
    result = {}
    for kind, ids in (("uid", {u.pw_uid for u in pwd.getpwall()}), ("gid", {g.gr_gid for g in grp.getgrall()})):
        path = Path(f"/etc/sub{kind}")
        trusted_file(path, optional=False)
        result[kind] = validate_ranges(
            path.read_text(), "lychd", intent[kind], intent[f"sub{kind}_start"], intent["count"], ids
        )
    require(all(result.values()), "both exact subordinate maps must be present before enabling runtime access")
    return result


def trusted_file(path: Path, *, optional: bool = True) -> bool:
    require(not path.is_symlink(), f"symlink refused: {path}")
    if not path.exists():
        require(optional, f"required file absent: {path}")
        return False
    info = path.stat()
    require(
        stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022, f"untrusted host file: {path}"
    )
    return True


def config_values(path: Path) -> dict:
    """Parse data without sourcing administrator shell files."""
    result = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition("=")
        require(bool(sep) and key.strip() not in result, f"malformed/duplicate config entry: {path}")
        result[key.strip()] = value.strip().strip("\"'")
    return result


def command(*argv: str) -> str:
    return subprocess.run(argv, check=True, text=True, capture_output=True, timeout=30).stdout.strip()


def effective_generator() -> tuple[str, str]:
    """Inspect the executable selected by systemd's default directory precedence."""
    require("SYSTEMD_GENERATOR_PATH" not in os.environ, "SYSTEMD_GENERATOR_PATH override refused")
    for directory in (
        "/run/systemd/user-generators",
        "/etc/systemd/user-generators",
        "/usr/local/lib/systemd/user-generators",
        "/usr/lib/systemd/user-generators",
    ):
        candidate = Path(directory) / "podman-user-generator"
        if os.path.lexists(candidate):
            resolved = candidate.resolve(strict=True)
            require(
                resolved != Path("/dev/null") and resolved.is_file() and os.access(candidate, os.X_OK),
                "effective Quadlet generator is masked or unexecutable",
            )
            for path in {resolved, *resolved.parents, *candidate.parents}:
                info = path.stat()
                require(
                    info.st_uid == 0 and not info.st_mode & 0o022,
                    "effective Quadlet path is writable by an ordinary account",
                )
            version = command(str(candidate), "--version")
            require(version_at_least_54(version), "effective Quadlet generator must be >=5.4")
            return str(candidate), version
    raise Refusal("effective Quadlet user generator absent")


def version_at_least_54(text: str) -> bool:
    match = re.search(r"\b(\d+)\.(\d+)(?:\.(\d+))?", text)
    return match is not None and tuple(int(n or 0) for n in match.groups()) >= (5, 4, 0)


def landlock_abi() -> dict:
    """Observe the actual syscall ABI; this installs no sandbox."""
    if platform.machine() not in {"x86_64", "aarch64"}:
        return {"status": "unobserved", "reason": "syscall number reviewed only for x86_64/aarch64"}
    libc = ctypes.CDLL(None, use_errno=True)
    value = libc.syscall(444, 0, 0, 1)
    return {"abi": value, "at_least_6": value >= 6, "errno": ctypes.get_errno() if value < 0 else 0}


def observe(intent: dict, verify: bool) -> dict:
    require(os.geteuid() == 0, "use the separate existing administrator with become")
    require(os.environ.get("SUDO_USER") != "lychd", "the runtime account must never be the become administrator")
    release = config_values(Path("/etc/os-release"))
    require(
        release.get("ID") == "opensuse-tumbleweed" and not any("slowroll" in str(v).lower() for v in release.values()),
        "requires already installed openSUSE Tumbleweed, not MicroOS/Leap/Slowroll",
    )
    require(
        Path("/run/systemd/system").is_dir() and Path("/sys/fs/cgroup/cgroup.controllers").is_file(),
        "requires systemd and cgroup v2",
    )
    enforce = Path("/sys/fs/selinux/enforce")
    require(
        enforce.is_file() and enforce.read_text().strip() == "1",
        "SELinux must already be Enforcing; this role does not enable it or reboot",
    )
    mounts = parse_mounts(Path("/proc/self/mountinfo").read_text())
    for path in ("/", "/home", "/var"):
        require(not Path(path).is_symlink(), "mount path symlink refused")
    validate_mounts(mounts, {p: os.stat(p).st_ino for p in ("/", "/home", "/var")})
    for path in ("/", "/home"):
        validate_mount_parent(os.stat(path))
    skeleton = Path("/etc/lychd-host-floor-empty-skel")
    require(not skeleton.is_symlink(), "empty account skeleton symlink refused")
    if skeleton.exists():
        validate_mount_parent(skeleton.stat())
        require(not any(skeleton.iterdir()), "account skeleton must remain empty")
    nsswitch = Path("/etc/nsswitch.conf").read_text()
    subid_sources = re.findall(r"^\s*subid:\s*([^#\n]+)", nsswitch, re.M)
    require(
        not subid_sources or [s.strip() for s in subid_sources] == ["files"], "subid delegation must use local files"
    )
    marker = Path("/etc/lychd-host-floor.json")
    managed = trusted_file(marker)
    receipt = json.loads(marker.read_text()) if managed else None
    users, groups = pwd.getpwall(), grp.getgrall()
    # NSS backends need not enumerate every identity; query selected IDs/names too.
    for lookup, value, collection in (
        (pwd.getpwnam, "lychd", users),
        (pwd.getpwuid, intent["uid"], users),
        (grp.getgrnam, "lychd", groups),
        (grp.getgrgid, intent["gid"], groups),
    ):
        try:
            identity = lookup(value)
        except KeyError:
            continue
        if identity not in collection:
            collection.append(identity)
    require(len([u for u in users if u.pw_name == "lychd"]) <= 1, "duplicate runtime account name")
    require(len([g for g in groups if g.gr_name == "lychd"]) <= 1, "duplicate runtime group name")
    account = next((u for u in users if u.pw_name == "lychd"), None)
    group = next((g for g in groups if g.gr_name == "lychd"), None)
    require(
        all(u.pw_uid != intent["uid"] or u.pw_name == "lychd" for u in users),
        "runtime UID already belongs to another account",
    )
    require(
        all(g.gr_gid != intent["gid"] or g.gr_name == "lychd" for g in groups),
        "runtime GID already belongs to another group",
    )
    require(
        managed or (account is None and group is None), "existing unmanaged runtime account/group; adoption refused"
    )
    home = Path("/home/lychd")
    if group:
        require(group.gr_gid == intent["gid"] and not group.gr_mem, "runtime primary group conflicts")
    if account:
        require(
            account.pw_uid == intent["uid"]
            and account.pw_gid == intent["gid"]
            and account.pw_dir == str(home)
            and account.pw_shell == "/bin/bash",
            "existing runtime identity/home/shell differs",
        )
        require(not any("lychd" in g.gr_mem for g in groups), "runtime supplementary groups refused")
        require(
            home.is_dir()
            and not home.is_symlink()
            and home.stat().st_uid == intent["uid"]
            and home.stat().st_gid == intent["gid"],
            "runtime home missing, symlinked or owned by another UID",
        )
        for path in (home / ".ssh", home / ".ssh/authorized_keys"):
            require(not path.is_symlink(), "runtime SSH symlink refused")
        require_no_sudo()
    else:
        require(not os.path.lexists(home), "pre-existing home without managed account; adoption refused")
    maps = {}
    for kind, real_ids in (("uid", {u.pw_uid for u in users}), ("gid", {g.gr_gid for g in groups})):
        path = Path(f"/etc/sub{kind}")
        text = path.read_text() if trusted_file(path) else ""
        maps[kind] = validate_ranges(text, "lychd", intent[kind], intent[f"sub{kind}_start"], intent["count"], real_ids)
    snapper = Path("/etc/snapper/configs/root")
    if trusted_file(snapper):
        cfg = config_values(snapper)
        require(
            cfg.get("SUBVOLUME") == "/" and cfg.get("FSTYPE") == "btrfs",
            "existing Snapper root config does not target Btrfs /",
        )
    linger = Path("/var/lib/systemd/linger/lychd")
    trusted_file(linger)
    receipt_stage = validate_receipt(receipt, intent, account is not None, group is not None, maps, linger.exists())
    result = {
        "account_exists": account is not None,
        "managed_identity": managed,
        "receipt_stage": receipt_stage,
        "subuid_matches": maps["uid"],
        "subgid_matches": maps["gid"],
        "linger": linger.exists(),
        "mounts": mounts,
        "selinux": "Enforcing",
        "root_snapper_config": snapper.exists(),
        "scope": "host mechanism evidence only; runtime login, firewall narrowing and LychD acceptance remain separate",
    }
    if verify:
        require(receipt_stage == "configured" and linger.exists(), "host floor is incomplete")
        require(
            all(shutil.which(name) for name in ("newuidmap", "newgidmap")),
            "rootless subordinate-ID helpers are missing",
        )
        version = command("podman", "--version")
        require(version_at_least_54(version), "Podman must be >=5.4")
        manager_environment = command("systemctl", "--machine=lychd@", "--user", "show-environment")
        require(
            not any(line.startswith("SYSTEMD_GENERATOR_PATH=") for line in manager_environment.splitlines()),
            "runtime user manager overrides the Quadlet generator path",
        )
        generator, generator_version = effective_generator()
        command("/usr/sbin/sshd", "-t")
        keys_path = home / ".ssh/authorized_keys"
        require(
            keys_path.is_file() and keys_path.read_text() == "\n".join(intent["keys"]) + "\n",
            "runtime public keys differ",
        )
        firewall = subprocess.run(["firewall-cmd", "--state"], capture_output=True, text=True, timeout=10, check=False)
        result.update(
            {
                "podman": version,
                "quadlet_generator": generator,
                "quadlet_version": generator_version,
                "landlock": landlock_abi(),
                "firewalld_state": firewall.stdout.strip() or firewall.stderr.strip(),
                "firewall_narrowing": "requires independent admin review; no rules changed",
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("preflight", "verify", "identity", "maps", "landlock"))
    args = parser.parse_args()
    try:
        if args.phase == "landlock":
            print(json.dumps(landlock_abi(), sort_keys=True))
        else:
            intent = validate_intent(json.load(sys.stdin))
            if args.phase == "identity":
                result = observe_identity(intent)
            elif args.phase == "maps":
                result = observe_maps(intent)
            else:
                result = observe(intent, args.phase == "verify")
            print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"Refused: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
