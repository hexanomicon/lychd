from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from lychd.config.components import resolve_web_secret_key
from lychd.config.settings import Settings, SettingsSnapshot
from lychd.config.settings.extensions import ExtensionSettings
from lychd.config.settings.orchestration import SwitchingSettings
from lychd.config.settings.server import DatabaseSettings, ServerSettings, WebSettings
from lychd.db.factory import database_saq_dsn, database_url, resolve_database_password


def test_web_secret_key_resolves_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LYCHD_APP_SECRET_KEY", "app-secret")
    settings = WebSettings()
    assert resolve_web_secret_key(settings) == "app-secret"


def test_db_password_resolves_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LYCHD_DB_PASSWORD", "db-pass")
    settings = DatabaseSettings()
    assert resolve_database_password(settings) == "db-pass"


def test_database_urls_escape_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LYCHD_DB_PASSWORD", "a/b:c@d")
    settings = DatabaseSettings(user="lich@example")

    assert "lich%40example:a%2Fb%3Ac%40d@" in database_url(settings)
    assert database_url(settings).startswith("postgresql+asyncpg://")
    assert database_saq_dsn(settings).startswith("postgresql://")


def test_missing_secrets_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "LYCHD_APP_SECRET_KEY",
        "LYCHD_APP_SECRET_KEY_FILE",
        "LYCHD_DB_PASSWORD",
        "LYCHD_DB_PASSWORD_FILE",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings()
    with pytest.raises(ValueError, match="Required secret"):
        resolve_web_secret_key(settings.server.web)
    with pytest.raises(ValueError, match="Required secret"):
        resolve_database_password(settings.server.database)


def test_root_nested_environment_grammar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVER__PORT", "9011")
    monkeypatch.setenv("LYCHD_APP_SECRET_KEY", "explicit-app-secret")
    monkeypatch.setenv("LYCHD_DB_PASSWORD", "explicit-db-secret")
    settings = Settings()

    assert settings.server.port == 9011
    assert resolve_web_secret_key(settings.server.web) == "explicit-app-secret"
    assert resolve_database_password(settings.server.database) == "explicit-db-secret"


def test_only_the_three_declared_top_level_sections_are_accepted() -> None:
    with pytest.raises(ValueError, match="app"):
        Settings.model_validate({"app": {"debug": True}})

    with pytest.raises(ValueError, match="not_a_server_setting"):
        Settings.model_validate({"server": {"not_a_server_setting": True}})


def test_settings_snapshot_detaches_and_revalidates_the_mutable_settings_tree() -> None:
    settings = Settings()
    original_port = settings.server.port
    snapshot = SettingsSnapshot.capture(settings)

    settings.server.port = original_port + 1
    first_materialization = snapshot.materialize()
    first_materialization.server.port = original_port + 2

    assert snapshot.materialize().server.port == original_port


def test_optional_extensions_are_inert_until_explicitly_selected() -> None:
    settings = ExtensionSettings()

    assert settings.builtins == ()
    assert settings.crypt == ()


def test_extension_activation_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="animator/llamacpp"):
        ExtensionSettings(builtins=("animator/llamacpp", "animator/llamacpp"))


def test_extension_activation_rejects_unknown_builtin_ids() -> None:
    with pytest.raises(ValueError, match="animator/not-real"):
        ExtensionSettings(builtins=("animator/not-real",))


@pytest.mark.parametrize(
    "extension_id",
    ["", "/absolute", "alias//id", "alias/./id", "alias/../id", "trailing/", "control\nchar"],
)
def test_crypt_activation_requires_canonical_safe_ids(extension_id: str) -> None:
    with pytest.raises(ValueError, match="Invalid extension id"):
        ExtensionSettings(crypt=(extension_id,))


def test_cors_is_same_origin_by_default() -> None:
    assert WebSettings().allowed_cors_origins == []


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://example.com",
        "http://localhost:7134/",
        "http://localhost:7134/path",
        "http://user@localhost:7134",
        "http://localhost:7134?query=yes",
    ],
)
def test_cors_rejects_wildcard_remote_and_non_origin_values(origin: str) -> None:
    with pytest.raises(ValueError, match="loopback origins"):
        WebSettings(allowed_cors_origins=[origin])


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:5173", "http://127.0.0.1:7134", "https://[::1]:7443"],
)
def test_cors_accepts_exact_loopback_origins(origin: str) -> None:
    assert WebSettings(allowed_cors_origins=[origin]).allowed_cors_origins == [origin]


def test_server_rejects_port_claim_conflicts() -> None:
    with pytest.raises(ValueError, match="Port 5432 is claimed by multiple services"):
        ServerSettings(port=5432)


@pytest.mark.parametrize("port", [0, 65536])
def test_server_and_database_ports_stay_within_tcp_range(port: int) -> None:
    with pytest.raises(ValidationError):
        ServerSettings(port=port)
    with pytest.raises(ValidationError):
        DatabaseSettings(port=port)


@pytest.mark.parametrize("port", [1, 65535])
def test_server_and_database_ports_accept_tcp_boundaries(port: int) -> None:
    assert ServerSettings(port=port).port == port
    assert DatabaseSettings(port=port).port == port


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("pool_size", -1),
        ("max_overflow", -2),
        ("pool_timeout", -0.1),
        ("pool_timeout", float("nan")),
        ("pool_timeout", float("inf")),
        ("pool_timeout", float("-inf")),
        ("pool_recycle", -2),
        ("pool_recycle", float("nan")),
        ("pool_recycle", float("inf")),
        ("pool_recycle", float("-inf")),
    ],
)
def test_database_pool_settings_reject_invalid_numeric_boundaries(field_name: str, value: float) -> None:
    with pytest.raises(ValidationError):
        DatabaseSettings.model_validate({field_name: value})


def test_database_pool_settings_accept_sqlalchemy_boundaries() -> None:
    settings = DatabaseSettings(
        pool_size=0,
        max_overflow=-1,
        pool_timeout=0.5,
        pool_recycle=-1,
    )

    assert settings.pool_size == 0
    assert settings.max_overflow == -1
    assert settings.pool_timeout == 0.5
    assert settings.pool_recycle == -1


@pytest.mark.parametrize(
    ("settings_type", "field_name", "value"),
    [
        (WebSettings, "secret_key_secret", "/absolute/stolen"),
        (WebSettings, "secret_key_secret", "../stolen"),
        (DatabaseSettings, "password_secret", "db,target=/run/stolen"),
        (DatabaseSettings, "password_secret", "db secret"),
    ],
)
def test_core_secret_names_are_option_free_podman_basenames(
    settings_type: type[WebSettings | DatabaseSettings],
    field_name: str,
    value: str,
) -> None:
    with pytest.raises(ValueError, match="option-free Podman secret name"):
        settings_type.model_validate({field_name: value})


def test_core_application_and_database_secrets_must_be_distinct() -> None:
    with pytest.raises(ValueError, match="must use distinct Podman secret names"):
        ServerSettings(
            web=WebSettings(secret_key_secret="shared_core_secret"),  # noqa: S106 - reference name
            database=DatabaseSettings(password_secret="shared_core_secret"),  # noqa: S106 - reference name
        )


def test_control_paths_are_absolute_and_normalized(tmp_path: Path) -> None:
    switching = SwitchingSettings(host_reactor_dir=tmp_path / "triggers" / "nested" / ".." / "inbox")

    assert switching.host_reactor_dir == tmp_path / "triggers" / "inbox"
    assert switching.host_reactor_journal_dir == tmp_path / "triggers" / "journal"

    with pytest.raises(ValueError, match="host_reactor_dir must be an absolute path"):
        SwitchingSettings(host_reactor_dir=Path("relative/inbox"))
    with pytest.raises(ValueError, match="must be an 'inbox' directory"):
        SwitchingSettings(host_reactor_dir=tmp_path / "reactor")

    with pytest.raises(ValueError, match="unsafe in a systemd path"):
        SwitchingSettings.model_validate({"host_reactor_dir": f"{tmp_path}/bad\n/inbox"})


def test_control_paths_load_through_nested_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inbox = tmp_path / "reactor" / "inbox"
    monkeypatch.setenv("ORCHESTRATION__SWITCHING__HOST_REACTOR_DIR", str(inbox))

    settings = Settings()

    assert settings.orchestration.switching.host_reactor_dir == inbox
    assert settings.orchestration.switching.host_reactor_journal_dir == tmp_path / "reactor" / "journal"
