from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from lychd.system.atomic_paths import rename_noreplace_at
from lychd.system.services.lifecycle import CreatedResources
from lychd.system.services.privilege import PrivilegeService, initialize_registry


def test_initialize_registry_creation(tmp_path: Path) -> None:
    """Verify that initialize_registry creates the intent registry."""
    signals_dir = tmp_path / "triggers"

    initialize_registry(signals_dir=signals_dir)
    assert signals_dir.exists()
    assert signals_dir.is_dir()
    assert stat.S_IMODE(signals_dir.stat().st_mode) == 0o700


def test_initialize_registry_idempotency(tmp_path: Path) -> None:
    """Verify that initialize_registry identifies an existing registry."""
    signals_dir = tmp_path / "triggers"
    signals_dir.mkdir(mode=0o700)

    initialize_registry(signals_dir=signals_dir)
    assert signals_dir.exists()
    assert stat.S_IMODE(signals_dir.stat().st_mode) == 0o700


def test_initialize_registry_rejects_wrong_mode_without_changing_it(tmp_path: Path) -> None:
    """An existing operator path is never silently chmodded into ownership."""
    signals_dir = tmp_path / "triggers"
    signals_dir.mkdir(mode=0o755)

    with pytest.raises(RuntimeError, match="expected 0o700"):
        initialize_registry(signals_dir=signals_dir)

    assert stat.S_IMODE(signals_dir.stat().st_mode) == 0o755


def test_initialize_registry_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "real"
    target.mkdir()
    signals_dir = tmp_path / "triggers"
    signals_dir.symlink_to(target, target_is_directory=True)

    with pytest.raises(RuntimeError, match="Could not traverse managed layout directory"):
        initialize_registry(signals_dir=signals_dir)


def test_initialize_registry_rejects_foreign_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signals_dir = tmp_path / "triggers"
    signals_dir.mkdir()
    actual_uid = signals_dir.stat().st_uid
    monkeypatch.setattr("lychd.system.services.privilege.os.getuid", lambda: actual_uid + 1)

    with pytest.raises(RuntimeError, match="must be owned by uid"):
        initialize_registry(signals_dir=signals_dir)


def test_initialize_registry_journals_exact_chain_once(tmp_path: Path) -> None:
    """Every missing custom-layout component is reported with creation identity."""
    signals_dir = tmp_path / "reactor" / "inbox"
    journal: list[CreatedResources] = []
    service = PrivilegeService(signals_dir)

    created = service.initialize(on_created=journal.append)
    repeated = service.initialize(on_created=journal.append)

    assert created.directories == (
        tmp_path / "reactor",
        signals_dir,
    )
    assert {identity.path for identity in created.directory_identities} == set(created.directories)
    assert repeated == CreatedResources()
    assert journal == [created]


def test_initialize_registry_does_not_adopt_racer_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A peer-installed owner-only leaf is validated but never journaled."""
    signals_dir = tmp_path / "inbox"
    journal: list[CreatedResources] = []
    real_rename = rename_noreplace_at
    raced = False

    def install_peer_then_rename(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal raced
        if destination_name == signals_dir.name and not raced:
            raced = True
            os.mkdir(destination_name, 0o700, dir_fd=destination_dir_fd)
        real_rename(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.atomic_paths.rename_noreplace_at",
        install_peer_then_rename,
    )

    resources = PrivilegeService(signals_dir).initialize(on_created=journal.append)

    assert resources == CreatedResources()
    assert journal == []
    assert signals_dir.is_dir()
