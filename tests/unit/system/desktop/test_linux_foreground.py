"""Linux native selection must preserve the ordinary-user, foreground-only boundary."""

from __future__ import annotations

import os
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from click import Group
from click.testing import CliRunner

from lychd import app
from lychd.config.settings import Settings
from lychd.config.settings.server import DatabaseSettings
from lychd.interface import server, vessel_owner
from lychd.interface.server_policy import ServerRuntimePolicyError, validate_host_actuator
from lychd.system import desktop
from lychd.system.services import local_access

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux foreground deployment")


@pytest.fixture(autouse=True)
def native(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LYCHD_VESSEL_MODE", "native")


def test_linux_foreground_listener_uses_only_loopback(mocker: MockerFixture) -> None:
    settings = mocker.patch("lychd.config.settings.root.get_settings").return_value
    settings.server.database = DatabaseSettings()
    settings.server.port = 7134
    run = mocker.patch.object(server, "_run_listener")
    server.run_native_server()
    run.assert_called_once_with("127.0.0.1", 7134)
    with pytest.raises(ServerRuntimePolicyError, match="container mode"):
        server.run_production_server()
    assert run.call_count == 1
    validate_host_actuator("native", "native-process")
    for actuator in ("systemd", "host-reactor"):
        with pytest.raises(ServerRuntimePolicyError, match="native-process"):
            validate_host_actuator("native", actuator)


@pytest.mark.parametrize("database", [DatabaseSettings(profile="memory"), DatabaseSettings(host="another-host")])
@pytest.mark.asyncio
async def test_native_start_and_retirement_require_local_postgres(
    mocker: MockerFixture, database: DatabaseSettings
) -> None:
    settings = mocker.patch("lychd.config.settings.root.get_settings").return_value
    settings.server.database = database
    run = mocker.patch.object(server, "_run_listener")
    connect = mocker.patch.object(vessel_owner.asyncpg, "connect")
    with pytest.raises(ServerRuntimePolicyError, match="PostgreSQL"):
        server.run_native_server()
    with pytest.raises(ServerRuntimePolicyError, match="PostgreSQL"):
        await vessel_owner.stop_native_vessel()
    run.assert_not_called()
    connect.assert_not_called()


def test_native_root_refused_before_effects(mocker: MockerFixture) -> None:
    mocker.patch.object(os, "geteuid", return_value=0)
    read = mocker.patch.object(app, "get_settings")
    lock = mocker.patch.object(desktop, "management_lock")
    result = CliRunner().invoke(desktop.desktop, ["install"])
    assert result.exit_code == 1
    assert "ordinary" in result.output
    with pytest.raises(ServerRuntimePolicyError, match="ordinary"):
        app.create_app()
    with pytest.raises(ServerRuntimePolicyError, match="ordinary"):
        server.run_native_server()
    read.assert_not_called()
    lock.assert_not_called()


@pytest.mark.parametrize(
    "arguments",
    [
        ("enable-login",),
        ("disable-login",),
        ("enable-vault", "."),
        ("recover-credentials", ".", "--rebind-vault"),
        ("volume", "revoke"),
        ("backup", "--destination", ".", "--method", "apfs-clone"),
    ],
)
def test_platform_specific_options_refused_before_management_lock(
    mocker: MockerFixture, arguments: tuple[str, ...]
) -> None:
    lock = mocker.patch.object(desktop, "management_lock")
    result = CliRunner().invoke(desktop.desktop, arguments)
    assert result.exit_code == 1
    assert "macOS" in result.output
    lock.assert_not_called()


def test_direct_module_in_managed_mode_preserves_storage(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "lychd.system.desktop", "install"],
        env={**os.environ, "XDG_DATA_HOME": str(tmp_path), "LYCHD_VESSEL_MODE": "container"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "LYCHD_VESSEL_MODE=native" in result.stderr
    assert not tuple(tmp_path.iterdir())


def test_session_starts_its_cluster_and_dispatches_the_native_start(mocker: MockerFixture) -> None:
    from lychd import __main__ as entry
    from lychd.cli.native import start_native

    mocker.patch.object(entry, "cli", Group())
    entry._register_local_commands()  # pyright: ignore[reportPrivateUsage]
    mocker.patch.object(desktop, "management_lock", return_value=nullcontext())
    mocker.patch.object(desktop, "desktop_settings").return_value.server.database.port = 55432
    cluster = mocker.patch.object(desktop, "start_cluster")
    listener = mocker.patch.object(start_native, "callback")
    login = mocker.patch("lychd.system.desktop.login.load_environment")
    result = CliRunner().invoke(desktop.desktop, ["session"])
    assert result.exit_code == 0, result.output
    cluster.assert_called_once_with(55432)
    listener.assert_called_once_with()
    login.assert_not_called()


def test_linux_pg_start_disables_distribution_socket_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(desktop, "_data", lambda: tmp_path / "cluster")
    monkeypatch.setattr(desktop, "require_cluster", Mock())
    ctl = Mock(side_effect=[3, 0])
    monkeypatch.setattr(desktop, "_ctl", ctl)
    desktop.start_cluster(55432)
    options = ctl.call_args.args
    assert options[options.index("-o") + 1].split() == [
        "-c",
        "listen_addresses=127.0.0.1",
        "-c",
        "unix_socket_directories=",
        "-p",
        "55432",
    ]


def test_native_access_reads_its_files_and_never_falls_back_to_managed_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    for name in ("LYCHD_LOCAL_ACCESS_PASSWORD", "LYCHD_LOCAL_ACCESS_PASSWORD_FILE"):
        monkeypatch.delenv(name, raising=False)
    mounts = tmp_path / "mounted"
    mounts.mkdir()
    (mounts / "lychd_local_access_password").write_text("managed-credential-" + "x" * 32)
    monkeypatch.setattr("lychd.config.settings.sources.MOUNTED_SECRETS_DIR", mounts)
    monkeypatch.setattr("lychd.config.settings.root.PATH_LYCHD_TOML", tmp_path / "settings.toml")
    monkeypatch.setattr("lychd.system.desktop.credentials.PATH_POSTGRES_ROOT_DIR", tmp_path / "postgres")
    monkeypatch.setattr(local_access, "get_settings", Settings)
    tool = mocker.patch("lychd.system.host_tools.trusted_host_tool")
    with pytest.raises(ValueError, match="unavailable"):
        local_access.load_local_access()
    private = tmp_path / "postgres" / "desktop-credentials"
    private.mkdir(parents=True, mode=0o700)
    (private / "lychd_local_access_password").write_text("native-credential-" + "x" * 32)
    assert local_access.load_local_access().password.get_secret_value() == "native-credential-" + "x" * 32
    tool.assert_not_called()
