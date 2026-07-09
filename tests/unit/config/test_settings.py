from __future__ import annotations

from pathlib import Path

import pytest

from lychd.config.settings import (
    AppSettings,
    DatabaseSettings,
    OrchestrationSettings,
    Settings,
    StasisSettings,
    SwitchingSettings,
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


def test_database_urls_escape_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB__PASSWORD", "a/b:c@d")
    settings = DatabaseSettings(user="lich@example")

    assert "lich%40example:a%2Fb%3Ac%40d@" in settings.url
    assert settings.url.startswith("postgresql+asyncpg://")
    assert settings.saq_dsn.startswith("postgresql://")


def test_missing_secrets_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
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
    with pytest.raises(ValueError, match="Required secret"):
        _ = settings.app.secret_key
    with pytest.raises(ValueError, match="Required secret"):
        _ = settings.db.password


def test_root_nested_environment_grammar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVER__PORT", "9011")
    monkeypatch.setenv("APP__SECRET_KEY", "explicit-app-secret")
    monkeypatch.setenv("DB__PASSWORD", "explicit-db-secret")
    settings = Settings()

    assert settings.server.port == 9011
    assert settings.app.secret_key == "explicit-app-secret"  # noqa: S105 - fixture secret
    assert settings.db.password == "explicit-db-secret"  # noqa: S105 - fixture secret


def test_topology_a_rejects_multiple_server_processes() -> None:
    with pytest.raises(ValueError, match="workers"):
        Settings.model_validate({"server": {"workers": 2}})


def test_control_paths_are_absolute_and_normalized(tmp_path: Path) -> None:
    stasis = StasisSettings(dir=tmp_path / "checkpoint" / ".." / "stasis")
    switching = SwitchingSettings(host_reactor_dir=tmp_path / "triggers" / "nested" / ".." / "inbox")

    assert stasis.dir == tmp_path / "stasis"
    assert switching.host_reactor_dir == tmp_path / "triggers" / "inbox"
    assert switching.host_reactor_journal_dir == tmp_path / "triggers" / "journal"

    with pytest.raises(ValueError, match="stasis.dir must be an absolute path"):
        StasisSettings(dir=Path("relative/stasis"))
    with pytest.raises(ValueError, match="host_reactor_dir must be an absolute path"):
        SwitchingSettings(host_reactor_dir=Path("relative/inbox"))
    with pytest.raises(ValueError, match="must be an 'inbox' directory"):
        SwitchingSettings(host_reactor_dir=tmp_path / "reactor")

    double_slash_stasis = StasisSettings.model_validate({"dir": f"/{tmp_path}/stasis"})
    assert double_slash_stasis.dir == tmp_path / "stasis"

    with pytest.raises(ValueError, match="unsafe in a systemd path"):
        StasisSettings.model_validate({"dir": f"{tmp_path}/%h/stasis"})
    with pytest.raises(ValueError, match="unsafe in a systemd path"):
        SwitchingSettings.model_validate({"host_reactor_dir": f"{tmp_path}/bad\n/inbox"})


@pytest.mark.parametrize(
    "stasis_path",
    [
        "triggers",
        "triggers/inbox",
        "triggers/inbox/run-checkpoints",
        "triggers/journal",
        "triggers/journal/archive",
    ],
)
def test_stasis_must_not_overlap_reactor_channels(tmp_path: Path, stasis_path: str) -> None:
    inbox = tmp_path / "triggers" / "inbox"

    with pytest.raises(ValueError, match="stasis.dir must not overlap"):
        Settings(
            stasis=StasisSettings(dir=tmp_path / stasis_path),
            orchestration=OrchestrationSettings(
                switching=SwitchingSettings(host_reactor_dir=inbox),
            ),
        )


def test_stasis_may_be_a_reactor_sibling(tmp_path: Path) -> None:
    inbox = tmp_path / "triggers" / "inbox"
    settings = Settings(
        stasis=StasisSettings(dir=tmp_path / "stasis"),
        orchestration=OrchestrationSettings(
            switching=SwitchingSettings(host_reactor_dir=inbox),
        ),
    )

    assert settings.stasis.dir == tmp_path / "stasis"


def test_control_paths_load_through_nested_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inbox = tmp_path / "reactor" / "inbox"
    stasis = tmp_path / "checkpoints"
    monkeypatch.setenv("ORCHESTRATION__SWITCHING__HOST_REACTOR_DIR", str(inbox))
    monkeypatch.setenv("STASIS__DIR", str(stasis))

    settings = Settings()

    assert settings.orchestration.switching.host_reactor_dir == inbox
    assert settings.orchestration.switching.host_reactor_journal_dir == tmp_path / "reactor" / "journal"
    assert settings.stasis.dir == stasis
