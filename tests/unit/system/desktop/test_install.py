"""Desktop credentials, bootstrap refusal and native login boundaries."""

from __future__ import annotations

import os
import plistlib
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import click
import pytest

# pyright: reportPrivateUsage=false
from lychd.system import desktop
from lychd.system.desktop import credentials, login

if TYPE_CHECKING:
    from pathlib import Path


def test_runtime_loads_only_runtime_and_preserves_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(credentials, "PATH_POSTGRES_ROOT_DIR", tmp_path)
    names = (*credentials._RUNTIME, *credentials._ADMIN)
    for name in names:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(f"{name}_FILE", raising=False)
    credentials.load_credentials(administrative=True, provision=True)
    folder = tmp_path / "desktop-credentials"
    values = {path.name: path.read_text() for path in folder.iterdir()}
    assert len(values) == len(names)
    assert len(set(values.values())) == len(names)
    if os.name != "nt":
        assert folder.stat().st_mode & 0o777 == 0o700
    for name in names:
        monkeypatch.delenv(f"{name}_FILE")
    monkeypatch.setenv("LYCHD_APP_SECRET_KEY_FILE", str(tmp_path / "override"))
    credentials.load_credentials()
    assert os.environ["LYCHD_APP_SECRET_KEY_FILE"].endswith("override")
    assert all(f"{name}_FILE" not in os.environ for name in credentials._ADMIN)
    assert os.environ["LYCHD_RUNTIME_DB_PASSWORD_FILE"] == str(folder / "lychd_runtime_db_password")
    credentials.load_credentials(administrative=True, provision=True)
    assert {p.name: p.read_text() for p in folder.iterdir()} == values


def test_database_refuses_unmarked_and_wrong_major(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(desktop, "_DATA", tmp_path)
    (tmp_path / "PG_VERSION").write_text("18")
    with pytest.raises(click.ClickException, match="Unrecognized"):
        desktop._require_cluster()
    (tmp_path / ".lychd-desktop").write_text(desktop._OWNER)
    desktop._require_cluster()
    (tmp_path / "PG_VERSION").write_text("17")
    with pytest.raises(click.ClickException, match="PostgreSQL 18"):
        desktop._require_cluster()


def test_launch_agent_uses_interpreter_and_retains_user_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(login, "sys", SimpleNamespace(platform="darwin", executable=login.sys.executable))
    uid = getattr(os, "getuid", lambda: 0)()
    monkeypatch.setattr(login, "os", SimpleNamespace(environ=os.environ, getuid=lambda: uid))
    monkeypatch.setattr(login, "_PROFILE", tmp_path / "login.json")
    path = tmp_path / "agent.plist"
    monkeypatch.setattr(login, "_plist", lambda: path)
    monkeypatch.setattr(desktop, "postgres_program", Mock(return_value="/opt/Postgres 18/bin/pg_ctl"))
    for name in credentials._RUNTIME:
        monkeypatch.delenv(name, raising=False)
    calls: list[list[str]] = []

    def run(args: list[str], **_: object) -> object:
        from subprocess import CompletedProcess

        calls.append(args)
        return CompletedProcess[str](args, 1 if "print" in args else 0, stdout="")

    monkeypatch.setattr(login, "subprocess", SimpleNamespace(run=run))
    login.enable()
    payload = plistlib.loads(path.read_bytes())
    assert payload["ProgramArguments"] == [login.sys.executable, "-m", "lychd.system.desktop", "session"]
    assert calls[-1][1:3] == ["bootstrap", f"gui/{uid}"]
    path.write_bytes(plistlib.dumps({"Label": "another-user"}))
    with pytest.raises(click.ClickException, match="unrecognized"):
        login.enable()


def test_configure_model_binds_typed_chat_and_preserves_extensions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tomllib

    from lychd.system.desktop import model

    config = tmp_path / "lychd.toml"
    config.write_text('[orchestration.switching]\nactuator = "native-process"\n[extensions]\nbuiltins=["tether"]\n')
    monkeypatch.setattr(model, "PATH_LYCHD_TOML", config)
    monkeypatch.setattr(model, "PATH_SOULSTONES_DIR", tmp_path / "runes")
    engine = tmp_path / "llama-server"
    engine.touch()
    engine.chmod(0o700)
    weights = tmp_path / "weights.gguf"
    weights.write_bytes(b"GGUF")
    for _ in range(2):
        model.configure(engine, weights, 8081)
    result = tomllib.loads(config.read_text())
    assert result["extensions"]["builtins"] == ["tether", "animator/llamacpp"]
    assert result["weaver"]["bridge"] == {"revision": "2", "capability_key": "personal:chat:personal-model"}
    assert result["orchestration"]["switching"]["native_model_root"] == str(tmp_path)
    rune = tomllib.loads((tmp_path / "runes/llamacpp/personal.toml").read_text())
    assert rune["structured_output"] == "json-schema"
    assert rune["cache_type_k"] == rune["cache_type_v"] == "f16"
    assert rune["model_path"] == str(weights)
    assert rune["base_url"] == "http://127.0.0.1:8081/v1"


def test_windows_login_task_uses_interactive_limited_principal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(login, "os", SimpleNamespace(environ={**os.environ, "SYSTEMROOT": str(tmp_path / "Windows")}))
    monkeypatch.setattr(login, "sys", SimpleNamespace(platform="win32", executable=login.sys.executable))
    monkeypatch.setattr(login, "_PROFILE", tmp_path / "login.json")
    monkeypatch.setattr(desktop, "postgres_program", Mock(return_value=str(tmp_path / "pg_ctl.exe")))
    for name in credentials._RUNTIME:
        monkeypatch.delenv(name, raising=False)
    calls: list[list[str]] = []

    def run(args: list[str], **_: object) -> None:
        calls.append(args)

    monkeypatch.setattr(login, "subprocess", SimpleNamespace(run=run))
    login.enable()
    script = calls[-1][-1]
    assert "-LogonType Interactive -RunLevel Limited" in script
    assert "-AtLogOn -User $u.Name" in script
    assert "-Principal $p" in script
    assert "-Force" not in script
    assert "Check $existing[0]" in script
    assert "LYCHD_LOGIN_IDENTIFIER" in script
    login.disable()
    assert not login._PROFILE.exists()


def test_private_credential_path_refuses_redirected_ancestry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "redirect"
    if os.name == "nt":
        import _winapi  # Windows junction creation also works without symbolic-link privilege.

        _winapi.CreateJunction(str(target), str(link))
    else:
        link.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(credentials, "PATH_POSTGRES_ROOT_DIR", link / "postgres")
    with pytest.raises(ValueError, match="redirected"):
        credentials.load_credentials(provision=True)
    assert list(target.iterdir()) == []


def test_fresh_install_prepares_journal_used_by_native_actuator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lychd.config.settings import root
    from lychd.system.services.native_runtime import NativeRuntimeActuator

    root_path = tmp_path / "new-account"
    settings_file = root_path / "config" / "lychd.toml"
    postgres = root_path / "data" / "postgres"
    monkeypatch.setattr(root, "PATH_LYCHD_TOML", settings_file)
    monkeypatch.setattr(desktop, "PATH_LYCHD_TOML", settings_file)
    monkeypatch.setattr(desktop, "PATH_POSTGRES_ROOT_DIR", postgres)
    monkeypatch.setattr(desktop, "_DATA", postgres / "native-data")
    monkeypatch.setattr(credentials, "PATH_POSTGRES_ROOT_DIR", postgres)
    for name in (*credentials._RUNTIME, *credentials._ADMIN):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(f"{name}_FILE", raising=False)
    assert not root_path.exists()
    settings = desktop._prepare_installation()
    directory = settings.orchestration.switching.native_state_dir
    assert directory is not None
    assert directory == postgres.parent / "native-runtimes"
    assert directory.is_dir()
    NativeRuntimeActuator(Mock(), settings.orchestration.switching)
    assert (directory / "native.sqlite3").is_file()


def test_cluster_publish_recovers_partial_initialization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    final = tmp_path / "native-data"
    monkeypatch.setattr(desktop, "_DATA", final)
    monkeypatch.setattr(desktop, "PATH_POSTGRES_ROOT_DIR", tmp_path)
    attempts: list[Path] = []

    def initdb(args: list[str], *, check: bool) -> None:
        assert check
        staged = Path(args[2])
        staged.mkdir()
        (staged / "PG_VERSION").write_text("18")
        assert not final.exists()
        attempts.append(staged)
        if len(attempts) == 1:
            raise InterruptedError

    monkeypatch.setattr(desktop, "subprocess", SimpleNamespace(run=initdb))
    with pytest.raises(InterruptedError):
        desktop._initialize_cluster("initdb", "user", "temporary")
    assert not final.exists()
    desktop._initialize_cluster("initdb", "user", "temporary")
    desktop._require_cluster()


def test_management_lock_releases_after_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(desktop, "PATH_POSTGRES_ROOT_DIR", tmp_path)

    def interrupted() -> None:
        with desktop._management_lock():
            with pytest.raises(click.ClickException, match="management operation"), desktop._management_lock():
                pytest.fail("overlapping desktop operations")
            raise InterruptedError

    with pytest.raises(InterruptedError):
        interrupted()
    with desktop._management_lock():
        assert tmp_path.is_dir()


def test_publication_preserves_existing_files_and_recovers_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lychd.system.desktop import private

    target = tmp_path / "credential"
    with monkeypatch.context() as faults:

        def interrupted(_fd: int) -> None:
            raise InterruptedError

        faults.setattr(private.os, "fsync", interrupted)
        with pytest.raises(InterruptedError):
            private.publish_file(target, b"partial")
    assert not target.exists()
    private.publish_file(target, b"retained")
    with pytest.raises(FileExistsError):
        private.publish_file(target, b"replacement")
    assert target.read_bytes() == b"retained"


def test_reinstall_refuses_lost_generated_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cluster = tmp_path / "native-data"
    cluster.mkdir()
    monkeypatch.setattr(desktop, "_DATA", cluster)
    monkeypatch.setattr(credentials, "PATH_POSTGRES_ROOT_DIR", tmp_path)
    monkeypatch.setenv("LYCHD_RUNTIME_DB_PASSWORD", "external")
    monkeypatch.delenv("LYCHD_APP_SECRET_KEY", raising=False)
    monkeypatch.delenv("LYCHD_APP_SECRET_KEY_FILE", raising=False)
    with pytest.raises(click.ClickException, match="Restore its original file"):
        desktop._settings(install=True, admin=True)
    assert not (tmp_path / "desktop-credentials").exists()


def test_verify_recovered_credential_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from click.testing import CliRunner

    from lychd.system.desktop.private import private_directory, publish_file

    monkeypatch.setattr(desktop, "PATH_POSTGRES_ROOT_DIR", tmp_path)
    monkeypatch.setattr(credentials, "PATH_POSTGRES_ROOT_DIR", tmp_path)
    names = (*credentials._RUNTIME, *credentials._ADMIN)
    for name in names:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv(f"{name}_FILE", "")
    credentials.load_credentials(administrative=True, provision=True)
    original = tmp_path / "desktop-credentials"
    backup = tmp_path / "recovered"
    private_directory(backup)
    for name in names:
        publish_file(backup / name.lower(), (original / name.lower()).read_bytes())
    runner = CliRunner()
    verify = desktop.verify_credential_backup
    assert runner.invoke(verify, [str(backup)]).exit_code == 0
    assert runner.invoke(verify, [str(original)]).exit_code != 0
    selected = backup / names[-1].lower()
    selected.write_text("different-backup-value")
    mismatch = runner.invoke(verify, [str(backup)])
    assert mismatch.exit_code != 0
    assert names[-1] in mismatch.output
    assert selected.read_text() not in mismatch.output
    monkeypatch.setenv(f"{names[-1]}_FILE", str(selected))
    assert "explicit override" in runner.invoke(verify, [str(backup)]).output


def test_desktop_libpq_pins_registered_address(monkeypatch: pytest.MonkeyPatch) -> None:
    from psycopg.conninfo import conninfo_to_dict
    from pydantic import SecretStr

    from lychd.config.settings.server import DatabaseSettings
    from lychd.db import factory

    monkeypatch.setattr(factory, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setenv("PGHOSTADDR", "127.0.0.2")
    db = DatabaseSettings(host="localhost", password=SecretStr("local"), runtime_password=SecretStr("runtime"))
    for host, address in (("localhost", "127.0.0.1"), ("127.0.0.1", "127.0.0.1"), ("::1", "::1")):
        local = db.model_copy(update={"host": host})
        for runtime in (True, False):
            assert conninfo_to_dict(factory.database_saq_dsn(local, runtime=runtime))["hostaddr"] == address
    assert "hostaddr" not in conninfo_to_dict(factory.database_saq_dsn(db, libpq=False))
    assert "hostaddr" not in conninfo_to_dict(factory.database_saq_dsn(db.model_copy(update={"host": "private-db"})))


def test_installer_and_shutdown_pin_admin_connections(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import psycopg
    from click.testing import CliRunner
    from pydantic import SecretStr

    from lychd.config.settings.server import DatabaseSettings

    db = DatabaseSettings(host="localhost", password=SecretStr("temporary"))
    monkeypatch.setenv("PGHOSTADDR", "127.0.0.2")
    monkeypatch.setattr(desktop, "_DATA", tmp_path)
    monkeypatch.setattr(desktop, "PATH_POSTGRES_ROOT_DIR", tmp_path)
    monkeypatch.setattr(desktop, "postgres_program", Mock(return_value="initdb"))
    monkeypatch.setattr(
        desktop, "subprocess", SimpleNamespace(check_output=Mock(return_value="initdb (PostgreSQL) 18.0"))
    )
    monkeypatch.setattr(
        desktop, "_prepare_installation", Mock(return_value=SimpleNamespace(server=SimpleNamespace(database=db)))
    )
    monkeypatch.setattr(desktop, "_start", Mock())
    connect = Mock(side_effect=ConnectionRefusedError)
    monkeypatch.setattr(psycopg, "connect", connect)

    assert isinstance(CliRunner().invoke(desktop.install).exception, ConnectionRefusedError)
    with pytest.raises(ConnectionRefusedError), desktop._exclusive_cluster(db):
        pytest.fail("management proceeded without a verified database")
    assert len(connect.call_args_list) == 2
    assert all(call.kwargs["hostaddr"] == "127.0.0.1" for call in connect.call_args_list)


@pytest.mark.skipif(os.name != "nt", reason="Uses the real Windows DACL")
def test_windows_refuses_foreign_write_on_ancestry(tmp_path: Path) -> None:
    import subprocess
    from pathlib import Path

    from lychd.system.desktop.private import (
        check_path,
        private_directory,
        verify_private_directory,
        verify_private_file,
    )

    directory = tmp_path / "acl-trial"
    private_directory(directory)
    target = directory / "unpublished"
    check_path(target)
    icacls = Path(os.environ["SYSTEMROOT"]) / "System32" / "icacls.exe"
    subprocess.run([icacls, directory, "/grant", "*S-1-3-4:(OI)(CI)F"], check=True)  # noqa: S603
    inherited = directory / "credential"
    inherited.write_bytes(b"test")
    verify_private_directory(directory)
    verify_private_file(inherited)
    check_path(target)
    subprocess.run([icacls, directory, "/grant", "*S-1-5-32-545:(OI)(CI)M"], check=True)  # noqa: S603
    try:
        with pytest.raises(subprocess.CalledProcessError):
            check_path(target)
        with pytest.raises(subprocess.CalledProcessError):
            verify_private_file(inherited)
        assert not target.exists()
    finally:
        subprocess.run([icacls, directory, "/remove:g", "*S-1-5-32-545"], check=True)  # noqa: S603
