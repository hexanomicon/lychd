"""Bootstrap-safe personal path selection and Click routing."""

from __future__ import annotations

import json
import subprocess
import sys
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


def test_unknown_host_exposes_only_the_platform_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(entry.sys, "platform", "freebsd")
    group = click.Group()
    monkeypatch.setattr(entry, "cli", group)
    entry._register_local_commands()  # pyright: ignore[reportPrivateUsage]
    assert set(group.commands) == {"platform"}
    assert json.loads(CliRunner().invoke(group, ["platform"]).output)["profile"] == "unsupported"


def test_fresh_desktop_services_import_without_linux_host_control() -> None:
    """Import the installed foreground server, database and access paths before provisioning."""
    program = """
import sys
from lychd.app import create_app
from lychd.config.logging import apply_logging
from lychd.db.bootstrap import bootstrap_database
from lychd.interface.server import run_native_server
from lychd.interface.vessel_owner import stop_native_vessel
from lychd.interface.web.lifespan import altar_services_lifespan
from lychd.system.desktop import desktop
from lychd.system.desktop.credentials import load_credentials
from lychd.system.services.local_access import load_local_access
from lychd.system.services.native_runtime import NativeRuntimeActuator
assert 'lychd.system.operator.composition' not in sys.modules
assert 'lychd.system.atomic_paths' not in sys.modules
assert 'lychd.system.descriptor_settlement' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", program], check=True)  # noqa: S603
