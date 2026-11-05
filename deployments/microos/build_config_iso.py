#!/usr/bin/env python3
"""Build a private Combustion config ISO; no package installation or VPS contact.

Requires operator-installed xorriso or mkisofs. Output and host.json must be outside a Git
checkout. Only this reviewed script/helper, host.json and its validated public
key files enter the ISO; no recursive copy of an operator directory occurs.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("host_bootstrap", HERE / "combustion/host_bootstrap.py")
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


def outside_checkout(path: Path) -> bool:
    resolved = path.resolve()
    if resolved == HERE.parents[1] or HERE.parents[1] in resolved.parents:
        return False
    # Some managed workspaces contain an empty .git permission sentinel. A real
    # checkout has a HEAD, or a .git file pointing at worktree administration.
    return not any((parent / ".git").is_file() or (parent / ".git/HEAD").is_file() for parent in resolved.parents)


def build(config: Path, output: Path) -> None:
    bootstrap.require(config.is_absolute() and output.is_absolute(), "use absolute private config/output paths")
    bootstrap.require(
        outside_checkout(config) and outside_checkout(output), "config and output must be outside checkouts"
    )
    bootstrap.require(not os.path.lexists(output), "output already exists; refusing overwrite")
    parent = output.parent
    info = parent.stat()
    bootstrap.require(
        info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700 and not parent.is_symlink(),
        "output parent must be an owned private 0700 directory",
    )
    cfg, _, _ = bootstrap.load_config(config)
    xorriso, mkisofs = shutil.which("xorriso"), shutil.which("mkisofs")
    bootstrap.require(
        xorriso is not None or mkisofs is not None, "install xorriso or mkisofs separately on the workstation"
    )
    iso_command = [xorriso, "-as", "mkisofs"] if xorriso else [mkisofs]
    with tempfile.TemporaryDirectory(prefix="combustion-", dir=parent) as temp:
        staging = Path(temp)
        bundle = staging / "combustion"
        (bundle / "keys").mkdir(parents=True, mode=0o700)
        for name in ("script", "host_bootstrap.py"):
            shutil.copyfile(HERE / "combustion" / name, bundle / name)
        shutil.copyfile(config, bundle / "host.json")
        keys = cfg["runtime_user"]["ssh_public_keys"] + cfg["recovery_root_ssh"]["public_keys"]
        for key in keys:
            shutil.copyfile(config.parent / key, bundle / key)
        os.chmod(bundle / "script", 0o700)
        # Rock Ridge preserves long filenames and executable permissions.
        subprocess.run(
            [*iso_command, "-R", "-V", "combustion", "-o", str(output), str(staging)], check=True, timeout=120
        )
        os.chmod(output, 0o600)
    print(f"Private config ISO: {output}")
    print("Record its digest privately; provider ISO-swap/first-boot acceptance remains required.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        build(args.config, args.output)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"ISO build refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
