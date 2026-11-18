"""Bootstrap-safe personal path selection and Click routing."""

from __future__ import annotations

import json
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from lychd import __main__ as entry
from lychd.system import constants


@pytest.mark.parametrize("operating_system", ["darwin", "win32"])
def test_desktop_bootstrap_routes_and_personal_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, operating_system: str
) -> None:
    monkeypatch.setattr(entry.sys, "platform", operating_system)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    group = click.Group()
    monkeypatch.setattr(entry, "cli", group)
    entry._register_local_commands()  # pyright: ignore[reportPrivateUsage]
    assert set(group.commands) == {"platform", "desktop", "start", "stop", "access"}
    for args in (["--help"], ["start", "--help"], ["stop", "--help"], ["access", "--help"]):
        assert CliRunner().invoke(group, args).exit_code == 0
    assert json.loads(CliRunner().invoke(group, ["platform"]).output)["profile"] == "personal-desktop"
    config, data, cache = constants._personal_roots()  # pyright: ignore[reportPrivateUsage]
    base = tmp_path / "Library" / "Application Support" if operating_system == "darwin" else tmp_path
    assert (config, data) == (base / "LychD" / "config", base / "LychD" / "data")
    assert cache == (
        tmp_path / "Library" / "Caches" / "LychD" if operating_system == "darwin" else base / "LychD" / "cache"
    )
