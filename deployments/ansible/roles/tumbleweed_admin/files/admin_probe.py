"""Admit a fresh vendor sudo policy or observe an exact standalone operator policy.

This read-only helper never changes passwords, users or sudoers. Custom policy and drop-ins
require manual reconciliation; their digest is not permission to discard their semantics.
"""

import json
import os
import pwd
import re
import stat
import sys
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def policy(admin):
    require(isinstance(admin, str) and re.fullmatch(r"[a-z_][a-z0-9_-]{0,30}", admin), "invalid administrator")
    require(admin not in {"root", "lychd", "lychd-view"}, "choose a separate named administrator")
    return (
        "# Managed by LychD host preparation: named administrator only.\n"
        "Defaults env_reset,use_pty\n"
        'Defaults secure_path="/usr/sbin:/usr/bin:/sbin:/bin"\n'
        "root ALL=(ALL:ALL) ALL\n"
        f"{admin} ALL=(ALL:ALL) ALL\n"
    )


def classify(current, vendor, desired, dropins):
    if current == desired:
        return "configured"
    require(current == vendor, "custom sudoers refused; reconcile it through the provider console")
    require(not dropins, "existing sudoers drop-ins refused; preserve and review their policy")
    return "vendor"


def trusted_text(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022, "untrusted sudo policy")
    return path.read_text()


def main():
    require(os.geteuid() == 0, "administrator privilege required")
    admin = json.load(sys.stdin)["admin"]
    desired = policy(admin)
    os_release = Path("/etc/os-release").read_text()
    require(re.search(r'^ID="?opensuse-tumbleweed"?$', os_release, re.M), "Tumbleweed required")
    account = pwd.getpwnam(admin)
    require(
        account.pw_uid >= 1000 and account.pw_shell not in {"/bin/false", "/usr/sbin/nologin"},
        "ordinary login administrator required",
    )
    # Never output the hash. The new policy authenticates this user's own password.
    shadow = [
        line.split(":")[1] for line in Path("/etc/shadow").read_text().splitlines() if line.split(":")[0] == admin
    ]
    require(
        len(shadow) == 1 and shadow[0].startswith("$"),
        "administrator needs an unlocked own password before policy changes",
    )
    vendor = trusted_text(Path("/usr/etc/sudoers"))
    override = Path("/etc/sudoers")
    current = trusted_text(override) if os.path.lexists(override) else vendor
    dropins = [
        str(entry)
        for root in ("/usr/etc/sudoers.d", "/etc/sudoers.d")
        if Path(root).exists()
        for entry in Path(root).iterdir()
    ]
    print(json.dumps({"state": classify(current, vendor, desired, dropins), "policy": desired}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError):
        sys.exit(
            "Administrator policy refused; inspect the selected account, vendor policy and drop-ins through the console."
        )
