"""Fixed disposable-guest actions, sent through pinned SSH by qualify.py.

This is qualification infrastructure, not an application lifecycle or host-upgrade API.
Every privileged action rechecks the prepared-image marker and this run's QEMU UUID.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import pwd
import re
import shlex
import stat
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen


def require(value, message):
    if not value:
        raise ValueError(message)


def run(argv, timeout=120):
    return subprocess.run(argv, capture_output=True, text=True, check=True, timeout=timeout).stdout.strip()


def os_release():
    return dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)


def guard(payload):
    require(os.geteuid() == 0, "privileged guest observation requires root")
    marker = Path("/etc/lychd-qualification.json")
    info = marker.lstat()
    require(
        stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1 and not info.st_mode & 0o077,
        "untrusted disposable marker",
    )
    require(
        json.loads(marker.read_text()) == {"schema": 1, "disposable": True, "baseline_id": payload["baseline_id"]},
        "baseline identity mismatch",
    )
    require(Path("/etc/machine-id").read_text().strip() == payload["machine_id"], "machine identity mismatch")
    require(
        Path("/sys/class/dmi/id/product_uuid").read_text().strip().lower() == payload["run_id"],
        "owned QEMU UUID mismatch",
    )
    release = os_release()
    require(shlex.split(release["ID"]) == ["opensuse-tumbleweed"], "Tumbleweed required")
    require(shlex.split(release["VERSION_ID"]) == [payload["snapshot"]], "snapshot mismatch")


def observe(payload):
    guard(payload)
    packages = {}
    for name in ("openSUSE-release", "kernel-default", "systemd", "podman", "zypper"):
        packages[name] = run(["/usr/bin/rpm", "-q", "--queryformat", "%{NAME}-%{VERSION}-%{RELEASE}\\n", name])
    require(
        run(["/usr/bin/rpm", "-q", "--queryformat", "%{VERSION}", "openSUSE-release"]) == payload["snapshot"],
        "release package does not match snapshot",
    )
    return {"boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(), "packages": packages}


def runtime():
    require(os.geteuid() != 0 and pwd.getpwuid(os.geteuid()).pw_name == "lychd", "direct runtime SSH required")
    require(
        bool(run(["/usr/bin/systemctl", "--user", "show", "--property=Version", "--value"])),
        "user manager did not respond",
    )
    info = json.loads(run(["/usr/bin/podman", "info", "--format=json"]))
    require(info["host"]["security"]["rootless"] is True, "rootless Podman required")
    return {"runtime_login": True, "user_manager": True, "rootless_podman": True}


def administrator():
    require(os.geteuid() != 0 and pwd.getpwuid(os.geteuid()).pw_name == "operator", "ordinary operator SSH required")
    return {"administrator_login": True, "unprivileged": True}


def metadata(payload, snapshot=None):
    guard(payload)
    selected = snapshot or payload["snapshot"]
    for repo in payload["repositories"]:
        require(repo["name"] in {"oss", "non-oss"}, "unknown repository")
        require(
            repo["url"] == f"https://download.opensuse.org/history/{selected}/tumbleweed/repo/{repo['name']}/",
            "dated official repository required",
        )
        with urlopen(repo["url"] + "repodata/repomd.xml", timeout=60) as response:
            require(response.url.startswith("https://"), "HTTPS repository retrieval required")
            content = response.read(4 * 1024 * 1024 + 1)
        require(len(content) <= 4 * 1024 * 1024, "oversized repository metadata")
        require(hashlib.sha256(content).hexdigest() == repo["repomd_sha256"], "repository metadata hash mismatch")
    return {"metadata_pins_verified": True}


def directory(path, mode):
    if not path.exists():
        path.mkdir(mode=mode)
    info = path.lstat()
    require(
        stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
        "untrusted qualification directory",
    )


def upgrade(payload):
    guard(payload)
    target = payload["candidate_snapshot"]
    require(re.fullmatch(r"20[0-9]{6}", target) and target > payload["snapshot"], "later exact target required")
    metadata(payload, target)
    parent = Path("/var/lib/lychd-qualification")
    directory(parent, 0o700)
    work = parent / payload["run_id"]
    require(not work.exists() and not work.is_symlink(), "upgrade occurrence already exists; no automatic retry")
    work.mkdir(mode=0o700)
    (work / "intent.json").write_text(
        json.dumps({"run_id": payload["run_id"], "baseline": payload["snapshot"], "candidate": target}) + "\n"
    )
    repos, services, raw = work / "repos", work / "services", work / "raw"
    for path in (repos, services, raw):
        path.mkdir(mode=0o700)
    for repo in payload["repositories"]:
        key = base64.b64decode(repo["key_data"], validate=True)
        require(hashlib.sha256(key).hexdigest() == repo["key"]["sha256"], "admitted public key hash mismatch")
        key_path = work / (repo["name"] + ".asc")
        key_path.write_bytes(key)
        run(["/usr/bin/rpmkeys", "--import", str(key_path)])
        (repos / (repo["name"] + ".repo")).write_text(
            f"[{repo['name']}]\nname=qualification-{target}-{repo['name']}\n"
            f"baseurl={repo['url']}\nenabled=1\nautorefresh=0\n"
            "gpgcheck=1\nrepo_gpgcheck=1\npkg_gpgcheck=1\n"
        )
    command = [
        "/usr/bin/zypper",
        "--non-interactive",
        "--reposd-dir",
        str(repos),
        "--servicesd-dir",
        str(services),
        "--cache-dir",
        str(work / "cache"),
        "--raw-cache-dir",
        str(raw),
    ]
    # No auto-import, no signature bypass, no configured moving repositories or services.
    print(run([*command, "refresh", "--force"], timeout=300), flush=True)
    for repo in payload["repositories"]:
        files = list((raw / repo["name"]).rglob("repomd.xml"))
        require(
            len(files) == 1 and hashlib.sha256(files[0].read_bytes()).hexdigest() == repo["repomd_sha256"],
            "refreshed repository metadata drifted",
        )
    print(run([*command, "--no-refresh", "dup", "--no-allow-vendor-change"], timeout=1700), flush=True)
    guard({**payload, "snapshot": target})
    return {"upgrade_completed": True, "snapshot": target}


def main():
    action = sys.argv[1]
    if action not in {"runtime", "administrator"}:
        require(len(sys.argv) == 3 and re.fullmatch(r"[0-9a-f]{64}", sys.argv[2]), "sudo input marker required")
        require(
            sys.stdin.readline(128) == "lychd-qualification-sudo-v1:" + sys.argv[2] + "\n",
            "sudo password consumption was not established",
        )
    else:
        require(len(sys.argv) == 2, "direct unprivileged action does not accept sudo framing")
    payload = json.load(sys.stdin)
    if action == "runtime":
        result = runtime()
    elif action == "administrator":
        result = administrator()
    elif action == "observe":
        result = observe(payload)
    elif action == "metadata":
        result = metadata(payload)
    elif action == "upgrade":
        result = upgrade(payload)
    elif action in {"reboot", "shutdown"}:
        guard(payload)
        run(["/usr/bin/systemctl", "reboot" if action == "reboot" else "poweroff", "--no-block"])
        result = {action + "_requested": True}
    else:
        raise ValueError("unknown guest action")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
