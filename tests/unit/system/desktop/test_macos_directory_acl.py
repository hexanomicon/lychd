"""Exercise native desktop private-directory policy against actual macOS extended ACLs."""

from __future__ import annotations

import stat
import subprocess
import sys
from pathlib import Path

import pytest

from lychd.system.desktop.private import private_directory, verify_private_directory


@pytest.mark.skipif(sys.platform != "darwin", reason="Requires macOS filesystem ACLs and system chmod.")
def test_macos_extended_access_is_refused_until_provisioning_removes_it(tmp_path: Path) -> None:
    directory = tmp_path.resolve() / "private directory"
    private_directory(directory)
    verify_private_directory(directory)
    subprocess.run(["/bin/chmod", "+a", "everyone allow list,search", directory], check=True)  # noqa: S603
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700

    for _ in range(2):
        with pytest.raises(ValueError, match="without an extended ACL"):
            verify_private_directory(directory)

    private_directory(directory)
    verify_private_directory(directory)
    canary = directory / "owner.txt"
    canary.write_text("owner", encoding="utf-8")
    assert canary.read_text(encoding="utf-8") == "owner"
