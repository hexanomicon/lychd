"""Tests for trusted host-tool resolution at authority boundaries."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from lychd.system.host_tools import (
    trusted_executable,
    trusted_host_tool,
    trusted_podman_user_generator,
)


def _always_root_controlled(
    _path: Path,
    *,
    metadata: os.stat_result | None = None,
) -> bool:
    del metadata
    return True


def test_trusted_host_tool_rejects_user_controlled_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An executable below a user-writable ancestor never gains host authority."""
    executable = tmp_path / "systemctl"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)

    def user_tool(_name: str) -> str:
        return str(executable)

    monkeypatch.setattr("lychd.system.host_tools.shutil.which", user_tool)

    assert trusted_host_tool("systemctl", fallbacks=()) is None


def test_trusted_host_tool_returns_resolved_system_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A resolved executable whose complete chain is attested is accepted."""
    shell = tmp_path / "system" / "bin" / "sh"
    shell.parent.mkdir(parents=True)
    shell.write_text("#!/bin/sh\n", encoding="utf-8")
    shell.chmod(0o755)

    def missing_tool(_name: str) -> None:
        return None

    def root_controlled(
        _path: Path,
        *,
        metadata: os.stat_result | None = None,
    ) -> bool:
        _ = metadata
        return True

    monkeypatch.setattr("lychd.system.host_tools.shutil.which", missing_tool)
    monkeypatch.setattr(
        "lychd.system.host_tools._root_controlled",
        root_controlled,
    )

    assert trusted_host_tool("test-shell", fallbacks=(shell,)) == str(shell.resolve(strict=True))


def test_content_identical_tool_replacement_changes_attested_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-path replacement cannot compare equal to the approved executable."""
    executable = tmp_path / "systemctl"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)

    def no_discovery(_name: str) -> None:
        return None

    monkeypatch.setattr(
        "lychd.system.host_tools.shutil.which",
        no_discovery,
    )
    monkeypatch.setattr(
        "lychd.system.host_tools._root_controlled",
        _always_root_controlled,
    )
    before = trusted_executable("systemctl", fallbacks=(executable,))

    replacement = tmp_path / "replacement"
    replacement.write_text("#!/bin/sh\n", encoding="utf-8")
    replacement.chmod(0o755)
    replacement.replace(executable)
    after = trusted_executable("systemctl", fallbacks=(executable,))

    assert before is not None
    assert after is not None
    assert before.path == after.path
    assert before != after


def test_trusted_host_tool_rejects_user_owned_read_only_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A file owner can chmod a 0555 executable, so mode alone grants no trust."""
    executable = tmp_path / "umount"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o555)

    def user_tool(_name: str) -> str:
        return str(executable)

    def access(_path: Path, mode: int) -> bool:
        return mode == os.X_OK

    monkeypatch.setattr("lychd.system.host_tools.shutil.which", user_tool)
    monkeypatch.setattr("lychd.system.host_tools.os.access", access)

    assert trusted_host_tool("umount", fallbacks=()) is None


def test_nobody_owned_executable_is_not_system_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UID 65534 is a real principal unless immutable storage is separately proved."""
    executable = tmp_path / "podman"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o555)
    resolved = executable.resolve(strict=True)
    metadata = os.stat_result(
        (
            stat.S_IFREG | 0o555,
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

    def missing_tool(_name: str) -> None:
        return None

    def access(_path: Path, mode: int) -> bool:
        return mode == os.X_OK

    real_stat = Path.stat

    def path_stat(
        path: Path,
        *,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        if path == resolved:
            return metadata
        return real_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr("lychd.system.host_tools.shutil.which", missing_tool)
    monkeypatch.setattr("lychd.system.host_tools.os.access", access)
    monkeypatch.setattr(Path, "stat", path_stat)

    assert trusted_host_tool("podman", fallbacks=(executable,)) is None


def test_user_generator_honors_directory_priority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    high = tmp_path / "run"
    low = tmp_path / "usr"
    high.mkdir()
    low.mkdir()
    for directory in (high, low):
        generator = directory / "podman-user-generator"
        generator.write_text("#!/bin/sh\n", encoding="utf-8")
        generator.chmod(0o755)
    monkeypatch.setattr(
        "lychd.system.host_tools._root_controlled",
        _always_root_controlled,
    )

    selected = trusted_podman_user_generator(
        search_paths=(high, low),
    )

    assert selected == str((high / "podman-user-generator").resolve(strict=True))


@pytest.mark.parametrize("mask", ["empty", "dev-null"])
def test_user_generator_honors_higher_priority_masks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mask: str,
) -> None:
    high = tmp_path / "etc"
    low = tmp_path / "usr"
    high.mkdir()
    low.mkdir()
    winning = high / "podman-user-generator"
    if mask == "empty":
        winning.touch()
    else:
        winning.symlink_to("/dev/null")
    fallback = low / "podman-user-generator"
    fallback.write_text("#!/bin/sh\n", encoding="utf-8")
    fallback.chmod(0o755)
    monkeypatch.setattr(
        "lychd.system.host_tools._root_controlled",
        _always_root_controlled,
    )

    assert trusted_podman_user_generator(search_paths=(high, low)) is None
