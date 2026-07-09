from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest

import lychd.config.settings as settings_module
from lychd.config.settings import Settings, get_settings
from lychd.extensions.builtin.simulation.config import ShadowSimulationConfig
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
def codex_service(codex_paths: dict[str, Path]) -> CodexService:
    """Instantiate CodexService with isolated paths."""
    return CodexService(
        toml_path=codex_paths["toml"],
        runes_path=codex_paths["runes"],
        postgres_root_path=codex_paths["postgres"],
        rune_schemas=[ShadowSimulationConfig],
    )


def test_inscribe_structure(codex_service: CodexService, codex_paths: dict[str, Path]) -> None:
    """Verify codex initialization creates primary files and configurable samples."""
    codex_service.inscribe()

    assert codex_paths["root"].exists()
    assert codex_paths["runes"].exists()
    assert codex_paths["toml"].exists()
    assert (codex_paths["postgres"] / "init_db.sh").exists()
    assert codex_paths["toml"].stat().st_mode & 0o777 == 0o600

    # Runtime-supplied configurable sample should exist after inscription.
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
    assert content["orchestration"]["switching"]["policy"] == settings.orchestration.switching.policy
    assert content["orchestration"]["whim"]["idle_evict_after_s"] == settings.orchestration.whim.idle_evict_after_s
    assert content["orchestration"]["whim"]["preload"] == settings.orchestration.whim.preload


def test_lychd_toml_round_trips_through_settings(
    codex_service: CodexService,
    codex_paths: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The generated nested tables must survive a second Settings parse."""
    codex_service.inscribe()
    toml_path = codex_paths["toml"]
    content = tomllib.loads(toml_path.read_text(encoding="utf-8"))

    monkeypatch.setattr(settings_module, "PATH_LYCHD_TOML", toml_path)
    reparsed = Settings()

    assert reparsed.model_dump(mode="json", exclude_none=True) == content
    assert reparsed.orchestration.switching.policy == "evict-idle"
    assert reparsed.orchestration.whim.idle_evict_after_s == 0
    assert reparsed.orchestration.whim.preload == []


def test_init_db_script_creates_only_extension_database(
    codex_service: CodexService,
    codex_paths: dict[str, Path],
) -> None:
    """Postgres owns its configured DB; the hook creates only Phoenix."""
    codex_service.inscribe()
    script = (codex_paths["postgres"] / "init_db.sh").read_text(encoding="utf-8")

    assert "CREATE DATABASE phoenix" in script
    assert "CREATE DATABASE lychd" not in script
    assert script.count("CREATE EXTENSION IF NOT EXISTS vector;") == 2
    assert "\\connect phoenix" in script


def test_idempotency(codex_service: CodexService, codex_paths: dict[str, Path]) -> None:
    """Ensure running inscribe twice does not overwrite existing global config."""
    codex_service.inscribe()

    codex_paths["toml"].write_text("modified = true", encoding="utf-8")

    codex_service.inscribe()

    assert codex_paths["toml"].read_text(encoding="utf-8") == "modified = true"
