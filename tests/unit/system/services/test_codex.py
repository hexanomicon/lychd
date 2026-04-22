from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest

from lychd.config.settings import get_settings
from lychd.system.services.codex import CodexService

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def codex_paths(tmp_path: Path) -> dict[str, Path]:
    """Define the Codex structure in a temp directory."""
    root = tmp_path / "config"
    souls = root / "soulstones"
    portals = root / "portals"

    # Create them to simulate LayoutService results
    souls.mkdir(parents=True, exist_ok=True)
    portals.mkdir(parents=True, exist_ok=True)

    return {
        "root": root,
        "toml": root / "lychd.toml",
        "soulstones": souls,
        "portals": portals,
    }


@pytest.fixture
def codex_service(codex_paths: dict[str, Path]) -> CodexService:
    """Instantiate the Codex Scribe."""
    return CodexService(
        toml_path=codex_paths["toml"],
        soulstones_path=codex_paths["soulstones"],
        portals_path=codex_paths["portals"],
    )


def test_inscribe_structure(codex_service: CodexService, codex_paths: dict[str, Path]) -> None:
    """Verify that directories and files are created."""
    codex_service.inscribe()

    assert codex_paths["root"].exists()
    assert codex_paths["soulstones"].exists()
    assert codex_paths["portals"].exists()
    assert codex_paths["toml"].exists()
    assert (codex_paths["soulstones"] / "hermes.toml").exists()
    assert (codex_paths["portals"] / "openai.toml").exists()


def test_lychd_toml_validity(codex_service: CodexService, codex_paths: dict[str, Path]) -> None:
    """Verify lychd.toml content matches Settings defaults."""
    codex_service.inscribe()

    content = tomllib.loads(codex_paths["toml"].read_text(encoding="utf-8"))
    settings = get_settings()

    # Check sections
    assert "server" in content
    assert "db" in content

    # Check values
    assert content["server"]["port"] == settings.server.port
    assert content["app"]["name"] == "lychd"


def test_idempotency(codex_service: CodexService, codex_paths: dict[str, Path]) -> None:
    """Ensure running inscribe twice doesn't overwrite existing configs."""
    codex_service.inscribe()

    # Modify the file
    codex_paths["toml"].write_text("modified = true", encoding="utf-8")

    # Run again
    codex_service.inscribe()

    # Should still be modified
    assert codex_paths["toml"].read_text() == "modified = true"
