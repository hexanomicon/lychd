"""Bootstrap-safe personal path selection and Click routing."""

from __future__ import annotations

import ctypes
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import click
import pytest
from click.testing import CliRunner

from lychd import __main__ as entry
from lychd.system import constants, vessel_mode


@pytest.mark.skipif(sys.platform == "win32", reason="macOS uses POSIX effective user IDs")
def test_macos_admin_login_can_run_natively_until_elevated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.delenv("LYCHD_VESSEL_MODE", raising=False)
    monkeypatch.setattr(vessel_mode.os, "getgroups", lambda: [20, 80])  # macOS staff and admin
    monkeypatch.setattr(vessel_mode.os, "geteuid", lambda: 501)
    vessel_mode.require_native_user()

    monkeypatch.setattr(vessel_mode.os, "geteuid", lambda: 0)
    with pytest.raises(ValueError, match="without sudo"):
        vessel_mode.require_native_user()


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


@pytest.mark.parametrize(
    ("choice", "profile", "dirname", "command"),
    [
        ("native", "personal-desktop", "lychd-native", "desktop"),
        ("container", "managed-linux", "lychd", "bind"),
        ("auto", "managed-linux", "lychd", "bind"),
    ],
)
@pytest.mark.skipif(sys.platform != "linux", reason="Checks the installed Linux command and its XDG paths.")
def test_linux_mode_selects_commands_and_disjoint_roots(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, choice: str, profile: str, dirname: str, command: str
) -> None:
    monkeypatch.setenv("LYCHD_VESSEL_MODE", choice)
    for category in ("config", "data", "cache"):
        monkeypatch.setenv(f"XDG_{category.upper()}_HOME", str(tmp_path / category))
    prefix = [sys.executable, "-m", "lychd"]
    report = subprocess.run([*prefix, "platform"], capture_output=True, text=True, check=True)  # noqa: S603
    actual = json.loads(report.stdout)
    assert actual["profile"] == profile
    assert actual["vessel_mode"] == ("native" if choice == "native" else "container")
    for category in ("config", "data", "cache"):
        assert Path(actual[category]) == tmp_path / category / dirname
        assert not Path(actual[category]).exists()
    help_text = subprocess.run([*prefix, "--help"], capture_output=True, text=True, check=True).stdout  # noqa: S603
    assert f"  {command} " in help_text


def test_invalid_mode_refuses_before_bootstrap(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LYCHD_VESSEL_MODE", "nativ")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    result = subprocess.run([sys.executable, "-m", "lychd", "start"], capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "LYCHD_VESSEL_MODE must be" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "config").exists()


@pytest.mark.parametrize("operating_system", ["darwin", "win32"])
def test_desktop_container_selection_routes_to_named_local_compose_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, operating_system: str
) -> None:
    from lychd.cli import portable

    monkeypatch.setattr(entry.sys, "platform", operating_system)
    monkeypatch.setenv("LYCHD_VESSEL_MODE", "container")
    monkeypatch.setenv("LYCHD_CONTAINER_DIR", str(tmp_path))
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    model = tmp_path / "private model.gguf"
    model.touch()
    (tmp_path / "compose.yaml").touch()
    monkeypatch.setenv("LYCHD_GGUF", str(model))
    monkeypatch.setattr(portable.shutil, "which", Mock(return_value="docker"))
    endpoint = (
        "unix:///local/docker.sock" if operating_system == "darwin" else "npipe:////./pipe/dockerDesktopLinuxEngine"
    )
    probes = iter(["desktop-linux", json.dumps(endpoint), "linux 29.4.0"])
    commands: list[list[str]] = []

    def run(arguments: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(arguments)
        return subprocess.CompletedProcess(arguments, 0, stdout=next(probes, ""))

    monkeypatch.setattr(portable.subprocess, "run", run)
    group = click.Group()
    monkeypatch.setattr(entry, "cli", group)
    entry._register_local_commands()  # pyright: ignore[reportPrivateUsage]
    runner = CliRunner()
    report = json.loads(runner.invoke(group, ["platform"]).output)
    assert (report["profile"], report["vessel_mode"]) == ("portable-container", "container")
    assert "settings" not in report
    assert runner.invoke(group, ["start"]).exit_code == 0
    assert commands[-1] == [
        "docker",
        "--context",
        "desktop-linux",
        "compose",
        "--project-directory",
        str(tmp_path),
        "-p",
        "lychd-portable",
        "-f",
        str(tmp_path / "compose.yaml"),
        "-f",
        str(tmp_path / "compose.chat.yaml"),
        "up",
        "--detach",
        "--no-build",
        "--wait",
        "--wait-timeout",
        "180",
    ]


def test_portable_start_refuses_remote_context_before_contact(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from lychd.cli import portable

    (tmp_path / "compose.yaml").touch()
    monkeypatch.setenv("LYCHD_CONTAINER_DIR", str(tmp_path))
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setattr(portable.shutil, "which", Mock(return_value="docker"))
    probes = iter(["remote", json.dumps("ssh://other-machine")])
    monkeypatch.setattr(portable, "_docker_output", Mock(side_effect=probes))
    result = CliRunner().invoke(portable.start)
    assert result.exit_code != 0
    assert "local Unix socket or Windows named pipe" in result.output


def test_portable_diagnostics_work_without_original_model_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from lychd.cli import portable

    (tmp_path / "compose.yaml").touch()
    monkeypatch.setenv("LYCHD_CONTAINER_DIR", str(tmp_path))
    monkeypatch.setenv("LYCHD_GGUF", str(tmp_path / "removed.gguf"))
    monkeypatch.setattr(portable, "_local_engine", Mock(return_value=["docker", "--context", "desktop-linux"]))
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(portable.subprocess, "run", run)
    assert CliRunner().invoke(portable.status).exit_code == 0
    args = run.call_args.args[0]
    assert args[-2:] == ["ps", "--all"]
    assert str(tmp_path / "compose.chat.yaml") not in args


@pytest.mark.parametrize("success", [False, True])
def test_unknown_windows_token_elevation_refuses(monkeypatch: pytest.MonkeyPatch, *, success: bool) -> None:
    # A successful query with a short output is also insufficient evidence.
    library = Mock()
    library.GetTokenInformation.return_value = success
    monkeypatch.setattr(ctypes, "WinDLL", Mock(return_value=library), raising=False)
    with pytest.raises(ValueError, match="Cannot verify the elevation"):
        vessel_mode._windows_process_elevated()  # pyright: ignore[reportPrivateUsage]
