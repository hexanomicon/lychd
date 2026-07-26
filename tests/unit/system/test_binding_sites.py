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


def test_sticky_ancestor_owned_by_nobody_is_not_trusted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sticky protection does not constrain the directory's own untrusted owner."""
    target = Path("/untrusted-sticky/site")
    target_metadata = os.stat_result(
        (
            stat.S_IFDIR | 0o700,
            1,
            1,
            1,
            1000,
            1000,
            0,
            0,
            0,
            0,
        )
    )
    ancestor_metadata = os.stat_result(
        (
            stat.S_IFDIR | 0o1777,
            1,
            1,
            1,
            65534,
            65534,
            0,
            0,
            0,
            0,
        )
    )

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


def test_foreign_owned_private_ancestor_is_not_trusted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign owner can chmod or replace descendants despite mode 0755."""
    target = Path("/foreign-parent/site")
    target_metadata = os.stat_result(
        (
            stat.S_IFDIR | 0o700,
            1,
            1,
            1,
            1000,
            1000,
            0,
            0,
            0,
            0,
        )
    )
    foreign_parent_metadata = os.stat_result(
        (
            stat.S_IFDIR | 0o755,
            1,
            1,
            1,
            2000,
            2000,
            0,
            0,
            0,
            0,
        )
    )

    def no_symlink(_path: Path) -> None:
        return None

    def lexists(_path: object) -> bool:
        return True

    def accessible(_path: Path, _mode: int) -> bool:
        return True

    def lstat(path: Path) -> os.stat_result:
        return target_metadata if path == target else foreign_parent_metadata

    monkeypatch.setattr(
        "lychd.system.binding_sites.path_has_symlink_component",
        no_symlink,
    )
    monkeypatch.setattr(
        "lychd.system.binding_sites.os.path.lexists",
        lexists,
    )
    monkeypatch.setattr(
        "lychd.system.binding_sites.os.access",
        accessible,
    )
    monkeypatch.setattr(
        Path,
        "lstat",
        lstat,
    )

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
