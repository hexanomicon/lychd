"""Recovery, interruption and real OS custody through the desktop credential entry points."""

from __future__ import annotations

import sys
from pathlib import Path

import click
import pytest

from lychd.system.desktop import credentials, vault
from lychd.system.desktop.private import private_directory, publish_file

# pyright: reportPrivateUsage=false

_NAMES = (*credentials._RUNTIME, *credentials._ADMIN)


@pytest.fixture
def recovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path.resolve()
    monkeypatch.setattr(credentials, "PATH_POSTGRES_ROOT_DIR", root)
    for name in _NAMES:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv(f"{name}_FILE", "")
    credentials.load_credentials(administrative=True, provision=True)
    backup = root / "backup"
    private_directory(backup)
    for name in _NAMES:
        monkeypatch.delenv(f"{name}_FILE")
        publish_file(backup / name.lower(), (root / "desktop-credentials" / name.lower()).read_bytes())
    return backup


def test_recovery_validates_whole_set_and_resumes_partial_copy(recovery: Path) -> None:
    active = recovery.parent / "desktop-credentials"
    missing = active / _NAMES[0].lower()
    missing.unlink()
    mismatch = recovery / _NAMES[-1].lower()
    original = mismatch.read_bytes()
    mismatch.write_bytes(b"X" * len(original))
    with pytest.raises(ValueError, match="replace an existing"):
        credentials.restore_credentials(recovery)
    assert not missing.exists()
    mismatch.write_bytes(original)
    credentials.restore_credentials(recovery)
    credentials.restore_credentials(recovery)
    assert missing.read_bytes() == (recovery / missing.name).read_bytes()


def test_vault_refuses_unverified_backup_before_any_write(recovery: Path) -> None:
    selected = recovery / _NAMES[-1].lower()
    selected.write_text("corrupt")
    with pytest.raises(click.ClickException, match="does not match"):
        credentials.use_os_vault(recovery)
    assert all(
        not p.read_bytes().startswith(vault.PREFIX.encode())
        for p in (recovery.parent / "desktop-credentials").iterdir()
    )


@pytest.mark.skipif(sys.platform not in {"win32", "darwin"}, reason="requires the actual user's OS credential vault")
def test_os_vault_readback_and_runtime_settings(recovery: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lychd.config.settings import Settings

    credentials.use_os_vault(recovery)
    credentials.use_os_vault(recovery)
    active = recovery.parent / "desktop-credentials"
    for name in _NAMES:
        path = active / name.lower()
        record = path.read_text("ascii")
        expected = (recovery / path.name).read_text("ascii")
        assert record.startswith(vault.PREFIX)
        assert expected not in record
        assert credentials.resolve_vault_reference(name, path, record) == expected
        with pytest.raises(ValueError, match="matching generated"):
            credentials.resolve_vault_reference(name, recovery / path.name, record)
    for name in _NAMES:
        monkeypatch.setenv(f"{name}_FILE", str(active / name.lower()))
    settings = Settings()
    assert settings.server.web.access_password
    assert (
        settings.server.web.access_password.get_secret_value() == (recovery / "lychd_local_access_password").read_text()
    )
