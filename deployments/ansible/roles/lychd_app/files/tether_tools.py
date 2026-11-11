"""Read-only proof of the distribution WireGuard tool used by native key custody."""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path


class PrerequisiteError(Exception):
    """The host package or executable requires administrator preparation."""


def require(condition, message):
    if not condition:
        raise PrerequisiteError(message)


def trusted_executable(name):
    original = Path(name)
    path = original.resolve(strict=True)
    for item in (path, *path.parents, *original.parents):
        metadata = item.stat()
        require(metadata.st_uid == 0 and not metadata.st_mode & 0o022, "Untrusted WireGuard prerequisite executable")
    require(stat.S_ISREG(path.stat().st_mode) and os.access(path, os.X_OK), "WireGuard prerequisite is not executable")
    return str(path)


def run(executable, *arguments):
    result = subprocess.run(
        [executable, *arguments],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        env={"PATH": "/usr/sbin:/usr/bin", "LC_ALL": "C"},
    )
    require(
        len(result.stdout.encode()) <= 65536 and len(result.stderr.encode()) <= 65536,
        "Tool observation exceeded its bound",
    )
    require(
        result.returncode == 0,
        "Install wireguard-tools through administrator preparation; verification never installs it",
    )
    return result.stdout.strip()


def observe(command=run, resolve=trusted_executable):
    rpm = resolve("/usr/bin/rpm")
    require(
        command(rpm, "-q", "--qf", "%{NAME}", "wireguard-tools") == "wireguard-tools", "WireGuard tools RPM is absent"
    )
    wg = resolve("/usr/bin/wg")
    require(
        command(rpm, "-qf", "--qf", "%{NAME}", wg) == "wireguard-tools",
        "WireGuard executable is not supplied by its distribution package",
    )
    require(bool(command(wg, "--version")), "WireGuard executable did not report its version")
    return {"package_installed": True, "executable_verified": True}


def main():
    try:
        print(json.dumps(observe(), sort_keys=True))
    except (OSError, ValueError, subprocess.SubprocessError, PrerequisiteError):
        print(
            "WireGuard tools prerequisite refused; install or repair the distribution wireguard-tools package before native preparation.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
