"""Tests for the shared binding-site authority law."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from lychd.system.binding_sites import (
    BindingSiteState,
    inspect_binding_site,
)


def _directory_metadata(*, mode: int, uid: int) -> os.stat_result:
    return os.stat_result((stat.S_IFDIR | mode, 1, 1, 1, uid, uid, 0, 0, 0, 0))


@pytest.mark.parametrize(
    ("target", "ancestor_mode", "ancestor_uid"),
    [
        (Path("/untrusted-sticky/site"), 0o1777, 65534),
        (Path("/foreign-parent/site"), 0o755, 2000),
    ],
)
def test_untrusted_ancestor_owner_blocks_binding_site(
    monkeypatch: pytest.MonkeyPatch,
    target: Path,
    ancestor_mode: int,
    ancestor_uid: int,
) -> None:
    target_metadata = _directory_metadata(mode=0o700, uid=1000)
    ancestor_metadata = _directory_metadata(mode=ancestor_mode, uid=ancestor_uid)

    def no_symlink(_path: Path) -> None:
        return None

    def lexists(_path: object) -> bool:
        return True

    def accessible(_path: Path, _mode: int) -> bool:
        return True

    def lstat(path: Path) -> os.stat_result:
        return target_metadata if path == target else ancestor_metadata

    monkeypatch.setattr(
        "lychd.system.binding_sites.path_has_symlink_component",
        no_symlink,
    )
    monkeypatch.setattr("lychd.system.binding_sites.os.path.lexists", lexists)
    monkeypatch.setattr("lychd.system.binding_sites.os.access", accessible)
    monkeypatch.setattr(Path, "lstat", lstat)

    inspection = inspect_binding_site(target, current_uid=1000)

    assert inspection.state is BindingSiteState.BLOCKED
    assert "writable ancestor is not trusted" in inspection.detail


def test_content_identical_site_replacement_changes_attested_identity(
    tmp_path: Path,
) -> None:
    """An empty replacement directory is not the site approved previously."""
    target = tmp_path / "systemd"
    target.mkdir(mode=0o700)
    before = inspect_binding_site(target, current_uid=os.getuid())

    displaced = tmp_path / "displaced"
    target.rename(displaced)
    target.mkdir(mode=0o700)
    after = inspect_binding_site(target, current_uid=os.getuid())

    assert before.state is BindingSiteState.PREPARED
    assert after.state is BindingSiteState.PREPARED
    assert before.identity is not None
    assert after.identity is not None
    assert before.identity != after.identity
