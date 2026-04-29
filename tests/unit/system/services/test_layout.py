from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

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


@patch("lychd.system.services.layout.shutil.which")
@patch("lychd.system.services.layout.subprocess.run")
@patch("lychd.system.services.layout.subprocess.check_output")
def test_initialize_layout_genesis(
    mock_check_output: MagicMock,
    mock_run: MagicMock,
    mock_which: MagicMock,
    test_layout: list[Path],
) -> None:
    """Verify that initialize_layout creates the directory structure and handles Btrfs."""
    # Mock non-btrfs first
    mock_which.return_value = "/usr/bin/df"
    mock_check_output.return_value = (
        "Filesystem      1K-blocks   Used Available Use% Mounted on\n/dev/sda1       1024000 512000    512000  50% /"
    )

    service = LayoutService(layout=test_layout)
    service.initialize()

    # Verify results via side effects
    for path in test_layout:
        assert path.exists()
        assert path.is_dir()

    # Ensure no btrfs commands were run
    assert mock_run.call_count == 0


@patch("lychd.system.services.layout.shutil.which")
@patch("lychd.system.services.layout.subprocess.run")
@patch("lychd.system.services.layout.subprocess.check_output")
def test_initialize_layout_btrfs(
    mock_check_output: MagicMock,
    mock_run: MagicMock,
    mock_which: MagicMock,
    tmp_path: Path,
) -> None:
    """Verify that LayoutService applies Btrfs rituals when detected."""
    crypt_root = tmp_path / "crypt"
    postgres_dir = crypt_root / "postgres"
    layout = [crypt_root, postgres_dir]

    def _which(binary: str) -> str:
        return f"/usr/bin/{binary}"

    mock_which.side_effect = _which
    mock_check_output.return_value = "Filesystem      Type\n/dev/sda1       btrfs"

    # We need to mock lychd.system.services.layout.PATH_CRYPT_ROOT and PATH_POSTGRES_DIR
    with (
        patch("lychd.system.services.layout.PATH_CRYPT_ROOT", crypt_root),
        patch("lychd.system.services.layout.PATH_POSTGRES_DIR", postgres_dir),
    ):
        service = LayoutService(layout=layout)
        service.initialize()

    # Should have run btrfs subvolume create AND chattr +C
    mock_run.assert_any_call(
        ["/usr/bin/btrfs", "subvolume", "create", str(postgres_dir)], check=True, capture_output=True
    )
    mock_run.assert_any_call(["/usr/bin/chattr", "+C", str(postgres_dir)], check=False)
