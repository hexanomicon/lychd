"""Credential loading belongs to Settings construction, never to consumers."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from lychd.config.components import build_csrf_config, build_saq_config
from lychd.config.settings import DatabaseSettings, ServerSettings, Settings, SettingsSnapshot, get_settings
from lychd.db.factory import database_saq_dsn, database_url
from lychd.system.services.codex import CodexService


@pytest.fixture(autouse=True)
def isolated_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.setattr("lychd.config.settings.root.PATH_LYCHD_TOML", tmp_path / "lychd.toml")
    monkeypatch.setattr("lychd.config.settings.sources.MOUNTED_SECRETS_DIR", tmp_path / "mounts")
    for key in (
        "LYCHD_DB_PASSWORD",
        "LYCHD_DB_PASSWORD_FILE",
        "LYCHD_RUNTIME_DB_PASSWORD",
        "LYCHD_RUNTIME_DB_PASSWORD_FILE",
        "LYCHD_PHOENIX_DB_PASSWORD",
        "LYCHD_PHOENIX_DB_PASSWORD_FILE",
        "LYCHD_APP_SECRET_KEY",
        "LYCHD_APP_SECRET_KEY_FILE",
        "LYCHD_LOCAL_ACCESS_PASSWORD",
        "LYCHD_LOCAL_ACCESS_PASSWORD_FILE",
        "SERVER__DATABASE__PASSWORD",
        "SERVER__DATABASE__RUNTIME_PASSWORD",
        "SERVER__DATABASE__PHOENIX_PASSWORD",
        "SERVER__WEB__SECRET_KEY",
        "SERVER__WEB__ACCESS_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_file_is_read_once_and_shared_by_consumers_and_snapshots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    password_file = tmp_path / "password"
    password_file.write_text("first-password\n", encoding="utf-8")
    monkeypatch.setenv("LYCHD_DB_PASSWORD_FILE", str(password_file))
    monkeypatch.setenv("LYCHD_RUNTIME_DB_PASSWORD_FILE", str(password_file))
    monkeypatch.setenv("LYCHD_APP_SECRET_KEY", "first-signing-key")
    original_read = Path.read_text
    reads: list[Path] = []

    def read_text(path: Path, *args: Any, **kwargs: Any) -> str:
        reads.append(path)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    settings = get_settings()
    snapshot = SettingsSnapshot.capture(settings)
    reads_at_boot = list(reads)
    assert reads.count(password_file) == 2  # One read for each explicitly supplied credential field.

    password_file.write_text("second-password", encoding="utf-8")
    monkeypatch.setenv("LYCHD_APP_SECRET_KEY", "second-signing-key")
    monkeypatch.setenv("SERVER__PORT", "9876")
    with patch.object(Settings, "settings_customise_sources", side_effect=AssertionError("Unexpected source reload")):
        for generation in (settings, get_settings(), snapshot.materialize()):
            assert "first-password" in database_url(generation.server.database)
            assert "first-password" in database_saq_dsn(generation.server.database)
            assert build_csrf_config(generation).secret == "first-signing-key"  # noqa: S105 - fixture value
            assert generation.server.port == settings.server.port
        assert all(queue.dsn and "first-password" in queue.dsn for queue in build_saq_config(settings).queue_configs)
    assert reads == reads_at_boot

    fresh = Settings()
    assert fresh.server.database.password == SecretStr("second-password")
    assert fresh.server.web.secret_key == SecretStr("second-signing-key")
    assert fresh.server.port == 9876
    assert get_settings() is settings


def test_environment_priority_skips_an_invalid_file_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LYCHD_DB_PASSWORD", "legacy-value")
    monkeypatch.setenv("LYCHD_DB_PASSWORD_FILE", str(tmp_path / "missing"))
    assert Settings().server.database.password == SecretStr("legacy-value")
    monkeypatch.setenv("SERVER__DATABASE__PASSWORD", "nested-value")
    assert Settings().server.database.password == SecretStr("nested-value")
    explicit = Settings(server=ServerSettings(database=DatabaseSettings(password=SecretStr("explicit-value"))))
    assert explicit.server.database.password == SecretStr("explicit-value")


def test_declared_mount_names_are_resolved_at_construction(tmp_path: Path) -> None:
    mounts = tmp_path / "mounts"
    mounts.mkdir()
    (mounts / "custom-db").write_text("mounted-password", encoding="utf-8")
    (mounts / "custom-web").write_text("mounted-signing-key", encoding="utf-8")
    (tmp_path / "lychd.toml").write_text(
        '[server.database]\npassword_secret="custom-db"\n[server.web]\nsecret_key_secret="custom-web"\n',
        encoding="utf-8",
    )
    settings = Settings()
    assert settings.server.database.password == SecretStr("mounted-password")
    assert settings.server.web.secret_key == SecretStr("mounted-signing-key")


@pytest.mark.parametrize("content", [b"", b" \n", b"\xff", None])
def test_explicit_file_overrides_fail_during_settings_loading(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    content: bytes | None,
) -> None:
    path = tmp_path / "password"
    if content is not None:
        path.write_bytes(content)
    monkeypatch.setenv("LYCHD_DB_PASSWORD_FILE", str(path))
    with pytest.raises(ValueError, match="Secret file"):
        Settings()


def test_missing_mounts_allow_bootstrap_but_not_runtime_components() -> None:
    settings = Settings()
    assert settings.server.database.password is None
    assert settings.server.web.secret_key is None
    with pytest.raises(ValueError, match="Required database password"):
        database_url(settings.server.database)
    with pytest.raises(ValueError, match="Required application signing key"):
        build_csrf_config(settings)


def test_legacy_quoted_database_owner_names_remain_usable() -> None:
    settings = DatabaseSettings(user="My-Existing Owner", database="My.Database", password=SecretStr("synthetic"))
    assert settings.user == "My-Existing Owner"
    assert settings.database == "My.Database"


def test_credentials_are_excluded_from_exports_and_survive_in_memory_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LYCHD_DB_PASSWORD", "private-password")
    monkeypatch.setenv("LYCHD_APP_SECRET_KEY", "private-signing-key")
    settings = get_settings()
    snapshot = SettingsSnapshot.capture(settings)
    (tmp_path / "postgres").mkdir()
    service = CodexService(
        rune_schemas=[],
        toml_path=tmp_path / "export.toml",
        runes_path=tmp_path / "runes",
        postgres_root_path=tmp_path / "postgres",
    )
    service.inscribe()
    for output in (
        repr(settings),
        repr(snapshot),
        settings.model_dump_json(),
        snapshot.payload,
        service.toml_path.read_text(encoding="utf-8"),
    ):
        assert "private-password" not in output
        assert "private-signing-key" not in output
        assert "**********" not in output
    assert "password" not in settings.model_dump()["server"]["database"]
    assert "secret_key" not in settings.model_dump()["server"]["web"]
    assert snapshot.materialize().server.database.password == SecretStr("private-password")
    assert snapshot.materialize().server.web.secret_key == SecretStr("private-signing-key")
    invalid = replace(snapshot, payload='{"server":{"port":0}}')
    with pytest.raises(ValidationError):
        invalid.materialize()


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("database", "password"),
        ("database", "runtime_password"),
        ("database", "phoenix_password"),
        ("web", "secret_key"),
        ("web", "access_password"),
    ],
)
def test_toml_rejects_credential_values(tmp_path: Path, section: str, field: str) -> None:
    (tmp_path / "lychd.toml").write_text(f'[{"server"}.{section}]\n{field}="do-not-persist"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="TOML may contain only its secret reference") as error:
        Settings()
    assert "do-not-persist" not in str(error.value)
