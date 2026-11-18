"""Desktop credentials, bootstrap refusal and native login boundaries."""

from __future__ import annotations

import os
import plistlib
from typing import TYPE_CHECKING

import click
import pytest

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
    monkeypatch.setattr(login.sys, "platform", "darwin")
    uid = getattr(os, "getuid", lambda: 0)()
    monkeypatch.setattr(login.os, "getuid", lambda: uid, raising=False)
    monkeypatch.setattr(login, "_PROFILE", tmp_path / "login.json")
    path = tmp_path / "agent.plist"
    monkeypatch.setattr(login, "_plist", lambda: path)
    monkeypatch.setattr(desktop, "_program", lambda _: "/opt/Postgres 18/bin/pg_ctl")
    for name in credentials._RUNTIME:
        monkeypatch.delenv(name, raising=False)
    calls: list[list[str]] = []

    def run(args: list[str], **_: object) -> object:
        from subprocess import CompletedProcess

        calls.append(args)
        return CompletedProcess(args, 1 if "print" in args else 0)

    monkeypatch.setattr(login.subprocess, "run", run)
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
    assert rune["model_path"] == str(weights)
    assert rune["base_url"] == "http://127.0.0.1:8081/v1"


def test_windows_login_task_uses_interactive_limited_principal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lychd.system.desktop import private

    monkeypatch.setenv("SYSTEMROOT", str(tmp_path / "Windows"))
    monkeypatch.setattr(login.sys, "platform", "win32")
    monkeypatch.setattr(login, "_PROFILE", tmp_path / "login.json")
    monkeypatch.setattr(desktop, "_program", lambda _: str(tmp_path / "pg_ctl.exe"))
    for name in credentials._RUNTIME:
        monkeypatch.delenv(name, raising=False)
    calls: list[list[str]] = []

    def run(args: list[str], **_: object) -> None:
        calls.append(args)

    monkeypatch.setattr(private.subprocess, "run", run)
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
    link.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(credentials, "PATH_POSTGRES_ROOT_DIR", link / "postgres")
    with pytest.raises(ValueError, match="redirected"):
        credentials.load_credentials(provision=True)
    assert list(target.iterdir()) == []


def test_fresh_install_prepares_journal_used_by_native_actuator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import Mock

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
    assert directory == postgres.parent / "native-runtimes"
    assert directory.is_dir()
    NativeRuntimeActuator(Mock(), settings.orchestration.switching)
    assert (directory / "native.sqlite3").is_file()


def test_cluster_publish_recovers_partial_initialization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    final = tmp_path / "native-data"
    monkeypatch.setattr(desktop, "_DATA", final)
    monkeypatch.setattr(desktop, "PATH_POSTGRES_ROOT_DIR", tmp_path)
    attempts = []

    def initdb(args: list[str], *, check: bool) -> None:
        assert check
        staged = Path(args[2])
        staged.mkdir()
        (staged / "PG_VERSION").write_text("18")
        assert not final.exists()
        attempts.append(staged)
        if len(attempts) == 1:
            raise InterruptedError

    monkeypatch.setattr(desktop.subprocess, "run", initdb)
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
