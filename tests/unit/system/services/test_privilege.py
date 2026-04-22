from __future__ import annotations

from pathlib import Path

from lychd.system.services.privilege import initialize_registry


def test_initialize_registry_creation(tmp_path: Path) -> None:
    """Verify that initialize_registry creates the intent registry."""
    signals_dir = tmp_path / "triggers"

    initialize_registry(signals_dir=signals_dir)
    assert signals_dir.exists()
    assert signals_dir.is_dir()


def test_initialize_registry_idempotency(tmp_path: Path) -> None:
    """Verify that initialize_registry identifies an existing registry."""
    signals_dir = tmp_path / "triggers"
    signals_dir.mkdir()

    initialize_registry(signals_dir=signals_dir)
    assert signals_dir.exists()
