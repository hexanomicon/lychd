"""Tests for trusted host-tool resolution at authority boundaries."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lychd.system.host_tools import trusted_host_tool


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
