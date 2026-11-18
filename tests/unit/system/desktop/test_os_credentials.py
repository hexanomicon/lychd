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
    root = tmp_path.resolve() / "installation"
    monkeypatch.setattr(credentials, "PATH_POSTGRES_ROOT_DIR", root)
    for name in _NAMES:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv(f"{name}_FILE", "")
    credentials.load_credentials(administrative=True, provision=True)
    backup = root.parent / "backup"
    private_directory(backup)
    for name in _NAMES:
        monkeypatch.delenv(f"{name}_FILE")
        publish_file(backup / name.lower(), (root / "desktop-credentials" / name.lower()).read_bytes())
    return backup


def test_recovery_validates_whole_set_and_resumes_partial_copy(recovery: Path) -> None:
    active = recovery.parent / "installation" / "desktop-credentials"
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
        for p in (recovery.parent / "installation" / "desktop-credentials").iterdir()
    )


@pytest.mark.skipif(sys.platform not in {"win32", "darwin"}, reason="requires the actual user's OS credential vault")
def test_os_vault_readback_and_runtime_settings(recovery: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lychd.config.settings import Settings

    credentials.use_os_vault(recovery)
    credentials.use_os_vault(recovery)
    active = recovery.parent / "installation" / "desktop-credentials"
    for name in _NAMES:
        path = active / name.lower()
        record = path.read_text("ascii")
        expected = (recovery / path.name).read_text("ascii")
        assert record.startswith(vault.PREFIX)
        assert expected not in record
        assert credentials.resolve_vault_reference(name, path, record) == expected
        with pytest.raises(ValueError, match="matching generated"):
            credentials.resolve_vault_reference(name, recovery / path.name, record)
    other = active / _NAMES[1].lower()
    with pytest.raises(ValueError, match=r"Keychain item is unavailable|DPAPI could not access"):
        credentials.resolve_vault_reference(_NAMES[1], other, (active / _NAMES[0].lower()).read_text("ascii"))
    for name in _NAMES:
        monkeypatch.setenv(f"{name}_FILE", str(active / name.lower()))
    settings = Settings()
    assert settings.server.web.access_password
    assert (
        settings.server.web.access_password.get_secret_value() == (recovery / "lychd_local_access_password").read_text()
    )

    # A restored installation has the originals' references but a new Keychain
    # lookup namespace or DPAPI entropy path, even under this same test account.
    new_root = recovery.parent / "restored-installation"
    restored = new_root / "desktop-credentials"
    private_directory(restored)
    for name in _NAMES:
        monkeypatch.delenv(f"{name}_FILE")
        publish_file(restored / name.lower(), (active / name.lower()).read_bytes())
    monkeypatch.setattr(credentials, "PATH_POSTGRES_ROOT_DIR", new_root)
    with pytest.raises(vault.VaultUnavailableError):
        credentials.restore_credentials(recovery)
    credentials.restore_credentials(recovery, rebind_vault=True)
    credentials.verify_credential_copy(recovery)


def test_recovery_refuses_managed_and_selected_volume_paths(recovery: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lychd.system.desktop import volume_storage

    managed = credentials.PATH_POSTGRES_ROOT_DIR
    private_directory(managed.parent)
    nested = managed / "desktop-credentials" / "backup"
    private_directory(nested)
    with pytest.raises(ValueError, match="outside the active"):
        credentials.verify_recovery_directory(nested)
    with pytest.raises(ValueError, match="outside the active"):
        credentials.verify_recovery_directory(managed.parent)
    volume = recovery.parent / "mounted"
    private_directory(volume)
    private_directory(volume_storage.authority(managed / "native-data"))

    def selected(_default: Path) -> tuple[Path, str]:
        return volume, "test-volume"

    monkeypatch.setattr(volume_storage, "selected", selected)
    outside_pgdata = volume / "private-backup"
    private_directory(outside_pgdata)
    with pytest.raises(ValueError, match="outside the active"):
        credentials.verify_recovery_directory(outside_pgdata)
    credentials.verify_recovery_directory(recovery)


def test_rebind_verifies_every_portable_value_before_resealing(recovery: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    monkeypatch.setattr(vault, "sys", SimpleNamespace(platform="darwin"))
    store: dict[tuple[Path, str], bytes] = {}

    def keychain(path: Path, token: str, value: bytes | None = None) -> bytes:
        if value is not None:
            store[path, token] = value
        if (path, token) not in store:
            msg = "Keychain item is unavailable"
            raise vault.VaultUnavailableError(msg)
        return store[path, token]

    monkeypatch.setattr(vault, "_mac_keychain", keychain)
    credentials.use_os_vault(recovery)
    active = credentials.PATH_POSTGRES_ROOT_DIR / "desktop-credentials"
    original = {p.name: p.read_bytes() for p in active.iterdir()}
    store.clear()  # The original account's Keychain is unavailable.
    with pytest.raises(vault.VaultUnavailableError):
        credentials.restore_credentials(recovery)
    last = recovery / _NAMES[-1].lower()
    saved = last.read_bytes()
    last.write_bytes(b"X" * 64)
    with pytest.raises(ValueError, match="replace an existing"):
        credentials.restore_credentials(recovery, rebind_vault=True)
    assert not store
    assert {p.name: p.read_bytes() for p in active.iterdir()} == original
    last.write_bytes(saved)

    # Retry across a publication interruption: some references now point to the
    # new vault while others still require its verified portable copy.
    first = active / _NAMES[0].lower()
    first.write_bytes(vault.seal_credential(first, (recovery / first.name).read_bytes()))
    credentials.restore_credentials(recovery, rebind_vault=True)
    credentials.verify_credential_copy(recovery)
    assert len(store) == len(_NAMES)
    assert all(p.read_bytes().startswith(f"{vault.PREFIX}2:".encode()) for p in active.iterdir())


def test_legacy_vault_requires_original_owner_for_conversion(recovery: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    monkeypatch.setattr(vault, "sys", SimpleNamespace(platform="darwin"))
    active = credentials.PATH_POSTGRES_ROOT_DIR / "desktop-credentials"
    path = active / _NAMES[0].lower()
    original = path.read_bytes()
    record = f"{vault.PREFIX}1:keychain:" + "a" * 64
    path.write_text(record, encoding="ascii")

    def legacy_item(_path: Path, _token: str) -> bytes:
        return original

    monkeypatch.setattr(vault, "_mac_keychain", legacy_item)
    assert credentials.generated_value(path, _NAMES[0]) == original
    assert not vault.matches_recovery(path, record, original)
    monkeypatch.setattr(vault, "sys", SimpleNamespace(platform="win32"))
    with pytest.raises(ValueError, match="replace an existing"):
        credentials.restore_credentials(recovery, rebind_vault=True)
    assert path.read_text("ascii") == record
