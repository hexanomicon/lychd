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
    """Define a temporary Codex structure."""
    root = tmp_path / "config"
    runes = root / "runes"

    runes.mkdir(parents=True, exist_ok=True)

    return {
        "root": root,
        "toml": root / "lychd.toml",
        "runes": runes,
        "postgres": tmp_path / "postgres",
    }


@pytest.fixture
def codex_service(codex_paths: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> CodexService:
    """Instantiate CodexService with isolated paths."""
    monkeypatch.setattr("lychd.system.services.codex.PATH_POSTGRES_DIR", codex_paths["postgres"])

    return CodexService(
        toml_path=codex_paths["toml"],
        runes_path=codex_paths["runes"],
    )


def test_inscribe_structure(codex_service: CodexService, codex_paths: dict[str, Path]) -> None:
    """Verify codex initialization creates primary files and configurable samples."""
    codex_service.inscribe()

    assert codex_paths["root"].exists()
    assert codex_paths["runes"].exists()
    assert codex_paths["toml"].exists()
    assert (codex_paths["postgres"] / "init_db.sh").exists()
    assert codex_paths["toml"].stat().st_mode & 0o777 == 0o600

    # Built-in extension configurable sample should exist after discovery/import.
    assert (codex_paths["runes"] / "simulation" / "shadowsimulationconfig.toml").exists()


def test_lychd_toml_validity(codex_service: CodexService, codex_paths: dict[str, Path]) -> None:
    """Verify lychd.toml content matches Settings defaults."""
    codex_service.inscribe()

    content = tomllib.loads(codex_paths["toml"].read_text(encoding="utf-8"))
    settings = get_settings()

    assert "server" in content
    assert "db" in content
    assert content["server"]["port"] == settings.server.port
    assert content["app"]["name"] == "lychd"


def test_idempotency(codex_service: CodexService, codex_paths: dict[str, Path]) -> None:
    """Ensure running inscribe twice does not overwrite existing global config."""
    codex_service.inscribe()

    codex_paths["toml"].write_text("modified = true", encoding="utf-8")

    codex_service.inscribe()

    assert codex_paths["toml"].read_text(encoding="utf-8") == "modified = true"
