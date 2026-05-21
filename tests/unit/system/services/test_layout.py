from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from lychd.system.services.layout import LayoutService


@pytest.fixture
def test_layout(tmp_path: Path) -> list[Path]:
    """Create a temporary set of directories for testing LayoutService."""
    return [
        tmp_path / "codex",
        tmp_path / "crypt",
        tmp_path / "forge",
    ]


def test_initialize_layout_genesis(
    test_layout: list[Path],
) -> None:
    """Verify that initialize_layout creates the directory structure and handles Btrfs."""
    with patch("lychd.system.services.layout.Btrfs") as mock_btrfs_cls:
        service = LayoutService(paths=test_layout)
        service.initialize()

    # Verify results via side effects
    for path in test_layout:
        assert path.exists()
        assert path.is_dir()

    # Ensure no btrfs commands were run
    mock_btrfs_cls.return_value.create_subvolume.assert_not_called()


def test_initialize_layout_btrfs(
    tmp_path: Path,
) -> None:
    """Verify that LayoutService applies Btrfs rituals when detected."""
    crypt_root = tmp_path / "crypt"
    postgres_data_dir = crypt_root / "postgres" / "data"
    layout = [crypt_root, postgres_data_dir]

    with (
        patch("lychd.system.services.layout.PATH_POSTGRESS_DATA_DIR", postgres_data_dir),
        patch("lychd.system.services.layout.Btrfs") as mock_btrfs_cls,
    ):
        mock_btrfs = mock_btrfs_cls.return_value
        mock_btrfs.create_subvolume.return_value = True
        mock_btrfs.apply_no_cow.return_value = True

        service = LayoutService(paths=layout)
        service.initialize()

    # Should have run btrfs subvolume create AND chattr +C
    mock_btrfs.create_subvolume.assert_called_once_with(postgres_data_dir)
    mock_btrfs.apply_no_cow.assert_called_once_with(postgres_data_dir)
