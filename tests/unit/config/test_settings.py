from __future__ import annotations

import os
from pathlib import Path

import pytest

from lychd.config.settings import (
    AppSettings,
    DatabaseSettings,
    Settings,
    ensure_internal_secret_fallbacks,
)
from lychd.config.utils import codex_permission_issues


def test_codex_permission_issues_returns_empty_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    assert codex_permission_issues(missing) == {}


def test_codex_permission_issues_flags_broad_mode(tmp_path: Path) -> None:
    target = tmp_path / "lychd.toml"
    target.write_text('name = "lychd"\n', encoding="utf-8")
    target.chmod(0o644)

    issues = codex_permission_issues(target)
    assert issues.get("mode") == "0o644"
    assert issues.get("expected_max_mode") == "0o600"


def test_codex_permission_issues_accepts_restricted_mode(tmp_path: Path) -> None:
    target = tmp_path / "lychd.toml"
    target.write_text('name = "lychd"\n', encoding="utf-8")
    target.chmod(0o600)

    issues = codex_permission_issues(target)
    assert "mode" not in issues


def test_app_secret_key_resolves_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP__SECRET_KEY", "app-secret")
    settings = AppSettings()
    assert settings.secret_key == "app-secret"  # noqa: S105 - test fixture value


def test_db_password_resolves_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB__PASSWORD", "db-pass")
    settings = DatabaseSettings()
    assert settings.password == "db-pass"  # noqa: S105 - test fixture value


def test_internal_secret_fallbacks_generate_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "APP__SECRET_KEY",
        "APP_SECRET_KEY",
        "APP__SECRET_KEY_FILE",
        "APP_SECRET_KEY_FILE",
        "DB__PASSWORD",
        "DB_PASSWORD",
        "DB__PASSWORD_FILE",
        "DB_PASSWORD_FILE",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings()
    created = ensure_internal_secret_fallbacks(settings)

    assert settings.app.secret_key_secret in created
    assert settings.db.password_secret in created
    assert settings.app.secret_key
    assert settings.db.password


def test_internal_secret_fallbacks_keep_explicit_values(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings()
    monkeypatch.setenv("APP__SECRET_KEY", "explicit-app-secret")
    monkeypatch.setenv("DB__PASSWORD", "explicit-db-secret")
    created = ensure_internal_secret_fallbacks(settings)

    assert created == []
    assert os.environ.get("APP__SECRET_KEY") == "explicit-app-secret"
    assert os.environ.get("DB__PASSWORD") == "explicit-db-secret"
