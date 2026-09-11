"""Rootless database ownership may be preserved without adopting or entering it."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from lychd.system.services.layout import LayoutService
from lychd.system.services.layout_directory_traversal import (
    inspect_preserved_datastore,
    require_existing_directory,
)
from lychd.system.services.lifecycle._authority import current_authority
from lychd.system.services.lifecycle.models import LifecycleDisposition
from lychd.system.services.lifecycle.paths import inspect_init_directory


def test_mapped_datastore_is_preserved_without_opening_or_adopting_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A second init may observe a container-owned 0700 leaf without reading it."""
    parent = tmp_path / "postgres"
    parent.mkdir(mode=0o700)
    data = parent / "data"
    data.mkdir(mode=0o700)
    sentinel = data / "PG_VERSION"
    sentinel.write_bytes(b"17\n")
    original = data.stat()
    mapped = list(original)
    mapped[4] = os.getuid() + 100_000
    mapped_metadata = os.stat_result(mapped)
    real_stat, real_open = os.stat, os.open
    authority = replace(current_authority(), postgres_root=parent, postgres_data=data)
    monkeypatch.setattr("lychd.system.services.layout.PATH_POSTGRESS_DATA_DIR", data)

    def stat_leaf(path: object, *args: object, **kwargs: object) -> os.stat_result:
        if path == data.name and kwargs.get("dir_fd") is not None:
            assert kwargs.get("follow_symlinks") is False
            return mapped_metadata
        return real_stat(path, *args, **kwargs)  # type: ignore[arg-type]

    def open_parent_only(path: object, *args: object, **kwargs: object) -> int:
        assert path not in (data, str(data), data.name), "must not enter mapped PGDATA"
        return real_open(path, *args, **kwargs)  # type: ignore[arg-type]

    with patch("os.stat", side_effect=stat_leaf), patch("os.open", side_effect=open_parent_only):
        assert inspect_preserved_datastore(data).st_uid == mapped_metadata.st_uid
        action = inspect_init_directory(data, authority=authority)
        resources = LayoutService(paths=(data,)).initialize()

    assert action.disposition is LifecycleDisposition.PRESERVE
    assert not resources.directories
    assert data.stat() == original
    assert sentinel.read_bytes() == b"17\n"


@pytest.mark.parametrize("unsafe_part", ["parent", "leaf"])
def test_preserved_datastore_rejects_other_writers(tmp_path: Path, unsafe_part: str) -> None:
    """The UID exception cannot admit a namespace another account can rewrite."""
    parent = tmp_path / "postgres"
    parent.mkdir(mode=0o700)
    data = parent / "data"
    data.mkdir(mode=0o700)
    (parent if unsafe_part == "parent" else data).chmod(0o770)

    with pytest.raises(RuntimeError, match="writ"):
        inspect_preserved_datastore(data)


@pytest.mark.parametrize("linked_part", ["parent", "leaf"])
def test_preserved_datastore_rejects_symlink_components(tmp_path: Path, linked_part: str) -> None:
    """The exception does not follow a leaf or parent into a foreign tree."""
    actual = tmp_path / "actual"
    actual.mkdir(mode=0o700)
    (actual / "data").mkdir(mode=0o700)
    parent = tmp_path / "postgres"
    if linked_part == "parent":
        parent.symlink_to(actual, target_is_directory=True)
    else:
        parent.mkdir(mode=0o700)
        (parent / "data").symlink_to(actual / "data", target_is_directory=True)

    with pytest.raises(RuntimeError):
        inspect_preserved_datastore(parent / "data")


def test_preservation_exception_never_accepts_a_foreign_parent(tmp_path: Path) -> None:
    """Only the database leaf may differ from the invoking UID."""
    data = tmp_path / "data"
    data.mkdir(mode=0o700)
    mapped = list(tmp_path.stat())
    mapped[4] = os.getuid() + 100_000
    with (
        patch("os.fstat", return_value=os.stat_result(mapped)),
        pytest.raises(RuntimeError, match="owned"),
    ):
        inspect_preserved_datastore(data)


def test_generic_existing_directory_still_requires_host_ownership(tmp_path: Path) -> None:
    """Mapped-owner preservation grants no blanket layout ownership exemption."""
    mapped = list(tmp_path.stat())
    mapped[4] = os.getuid() + 100_000
    with (
        patch("os.fstat", return_value=os.stat_result(mapped)),
        pytest.raises(RuntimeError, match="owned"),
    ):
        require_existing_directory(tmp_path)
