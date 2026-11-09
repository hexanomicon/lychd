"""Read-only refusal checks for the bounded ordinary-user source staging role."""

import hashlib
import json
import os
import platform
import pwd
import re
import stat
import subprocess
import sys
from pathlib import Path


def require(condition, message):
    """Refuse before effects when an input or filesystem observation is unsafe."""
    if not condition:
        raise ValueError(message)


def safe_path(path, uid, directory=True):
    """Inspect each existing component with lstat, never adopting a symlink."""
    for component in reversed((path, *path.parents)):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode), f"symlink refused: {component}")
        require(info.st_uid in (0, uid), f"foreign owner: {component}")
        require(not info.st_mode & 0o022, f"writable shared path: {component}")
        if component != path or directory:
            require(stat.S_ISDIR(info.st_mode), f"not a directory: {component}")
    if path.exists():
        require(path.stat().st_uid == uid, f"runtime ownership required: {path}")


def git(path, *args):
    """Observe only this checkout with ambient Git configuration disabled."""
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
    return subprocess.check_output(
        ["/usr/bin/git", "--no-optional-locks", "-C", str(path), *args],
        env=env,
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def inspect_source(home, revision, uv_sha256, python, uid):
    """Accept only absent source or this role's exact, clean versioned checkout."""
    require(re.fullmatch(r"[0-9a-f]{40}", revision), "exact source SHA required")
    require(re.fullmatch(r"[0-9a-f]{64}", uv_sha256), "uv checksum required")
    require(python in ("3.14.8", "3.15.0"), "unsupported interpreter lane")
    checkout = home / "src" / f"lychd-{revision}"
    uv = home / ".local/lib/lychd-tools/uv-0.13.4"
    for path in (home, home / "src", checkout, uv.parent, uv.parent / "python", uv.parent / "cache"):
        safe_path(path, uid)
    safe_path(uv, uid, directory=False)
    if uv.exists():
        require(stat.S_ISREG(uv.stat().st_mode), "uv must be a regular executable")
        require(hashlib.sha256(uv.read_bytes()).hexdigest() == uv_sha256, "uv checksum mismatch")
    if not checkout.exists():
        return {"exists": False, "complete": False}

    # .venv contains standard interpreter symlinks; only that subtree permits them.
    # Every inode, including those links, must still belong to the runtime account.
    for parent, directories, files in os.walk(checkout, followlinks=False):
        for name in (*directories, *files):
            path = Path(parent) / name
            info = path.lstat()
            require(info.st_uid == uid, "foreign inode in source checkout")
            # uv deliberately creates its empty advisory environment lock with mode 0666.
            uv_lock = path == checkout / ".venv/.lock" and stat.S_ISREG(info.st_mode) and info.st_size == 0
            require(stat.S_ISLNK(info.st_mode) or uv_lock or not info.st_mode & 0o022, "shared-writable source inode")
            inside_venv = path.relative_to(checkout).parts[0] == ".venv"
            require(not stat.S_ISLNK(info.st_mode) or inside_venv, "source symlink refused")
    require((checkout / ".git").is_dir(), "ordinary Git checkout required")
    receipt_path = checkout / ".git/lychd-source.json"
    require(receipt_path.is_file(), "unreceipted checkout refused; do not adopt existing workspaces")
    receipt = json.loads(receipt_path.read_text())
    expected = {"revision": revision, "uv_sha256": uv_sha256, "python": python}
    require(all(receipt.get(key) == value for key, value in expected.items()), "receipt mismatch")
    complete = receipt.get("complete")
    require(type(complete) is bool, "invalid completion receipt")
    require(git(checkout, "rev-parse", "--show-toplevel") == str(checkout), "wrong Git root")
    require(git(checkout, "rev-parse", "HEAD") == revision, "source SHA mismatch")
    require(
        git(checkout, "config", "--get", "remote.origin.url") == "https://github.com/hexanomicon/lychd.git",
        "foreign source remote",
    )
    require(not git(checkout, "status", "--porcelain", "--untracked-files=all"), "dirty checkout refused")
    ignored = git(checkout, "ls-files", "--others", "--ignored", "--exclude-standard").splitlines()
    require(all(path.startswith(".venv/") for path in ignored), "foreign ignored material refused")
    venv = checkout / ".venv"
    require(not venv.is_symlink(), "symlinked environment refused")
    require(complete == venv.is_dir(), "partial environment refused; separate recovery required")
    if complete:
        safe_path(venv / "bin", uid)
        safe_path(venv / "bin/lychd", uid, directory=False)
        require((venv / "bin/lychd").is_file(), "installed CLI missing")
    return {"exists": True, "complete": complete}


def main():
    """Check actual execution identity rather than trusting inventory declarations."""
    uid = os.getuid()
    account = pwd.getpwuid(uid)
    require(uid != 0 and account.pw_name == "lychd", "direct ordinary lychd login required")
    require(account.pw_dir == "/home/lychd", "unexpected runtime home")
    require(platform.system() == "Linux" and platform.machine() == "x86_64", "Linux x86_64 required")
    print(json.dumps(inspect_source(Path(account.pw_dir), *sys.argv[1:], uid)))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        sys.exit(f"source staging refused: {error}")
