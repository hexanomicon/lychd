from __future__ import annotations

import stat
from pathlib import Path

import pytest

from lychd.system.services.privilege import initialize_registry


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

    with pytest.raises(RuntimeError, match="must not be a symlink"):
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
