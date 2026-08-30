from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest

import lychd.config.settings.root as settings_module
from lychd.config.settings.root import Settings, get_settings
from lychd.system.services.codex import CodexService
from lychd.system.services.lifecycle.models import CreatedResources

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def codex_paths(tmp_path: Path) -> dict[str, Path]:
    """Define a temporary Codex structure."""
    root = tmp_path / "config"
    runes = root / "runes"
    postgres = tmp_path / "postgres"

    runes.mkdir(parents=True, exist_ok=True)
    postgres.mkdir()

    return {
        "root": root,
        "toml": root / "lychd.toml",
        "runes": runes,
        "postgres": postgres,
    }


@pytest.fixture
def codex_service(codex_paths: dict[str, Path]) -> CodexService:
    """Instantiate CodexService with isolated paths."""
    return CodexService(
        toml_path=codex_paths["toml"],
        runes_path=codex_paths["runes"],
        postgres_root_path=codex_paths["postgres"],
        rune_schemas=[],
    )


def test_lychd_toml_is_valid_and_round_trips_through_settings(
    codex_service: CodexService,
    codex_paths: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_service.inscribe()

    toml_path = codex_paths["toml"]
    assert toml_path.stat().st_mode & 0o777 == 0o600
    content = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    settings = get_settings()

    assert "server" in content
    assert content["server"]["port"] == settings.server.port
    assert content["server"]["web"]["name"] == "lychd"
    assert "host" not in content["server"]
    assert "reload" not in content["server"]
    assert "keep_alive" not in content["server"]
    assert "url" not in content["server"]["web"]
    assert content["server"]["database"]["database"] == settings.server.database.database
    assert content["orchestration"]["switching"]["policy"] == settings.orchestration.switching.policy
    assert content["extensions"]["builtins"] == []

    rendered = toml_path.read_text(encoding="utf-8")
    assert "# Local llama.cpp:" in rendered
    assert "# Other choices:" in rendered

    monkeypatch.setattr(settings_module, "PATH_LYCHD_TOML", toml_path)
    reparsed = Settings()

    assert reparsed.model_dump(mode="json", exclude_none=True) == content
    assert reparsed.orchestration.switching.policy == "declared-conflicts"


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

    repeated = codex_service.inscribe()

    assert codex_paths["toml"].read_text(encoding="utf-8") == "modified = true"
    assert repeated == CreatedResources()


def test_inscribe_returns_the_same_exact_batches_sent_to_the_journal(
    codex_service: CodexService,
) -> None:
    """Codex never reconstructs exact creation truth from replaceable paths."""
    journal: list[CreatedResources] = []

    resources = codex_service.inscribe(on_created=journal.append)

    assert resources == CreatedResources.combine(*journal)
    assert resources.files
    assert {identity.path for identity in resources.directory_identities} == set(resources.directories)
