"""Startup-only adaptation of core credentials from environment and mounted files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast, override

from pydantic import BaseModel, SecretStr
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, EnvSettingsSource, PydanticBaseSettingsSource

from lychd.config.settings.server import ServerSettings
from lychd.system.vessel_mode import vessel_mode

MOUNTED_SECRETS_DIR = Path("/run/secrets")


class RuntimeSecretsSource(PydanticBaseSettingsSource):
    """Capture credentials once through the ordinary environment and file precedence."""

    def __init__(self, settings_cls: type[BaseSettings], environment: PydanticBaseSettingsSource) -> None:
        """Reuse the environment captured by Pydantic for this construction."""
        super().__init__(settings_cls)
        if not isinstance(environment, EnvSettingsSource):
            msg = "Runtime secrets require Pydantic's environment source."
            raise TypeError(msg)
        self._environment = environment.env_vars
        self._case_sensitive = environment.case_sensitive
        self._use_mounts = vessel_mode() == "container"

    @override
    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    @override
    def __call__(self) -> dict[str, Any]:
        key = "LYCHD_RUNTIME_SECRETS" if self._case_sensitive else "lychd_runtime_secrets"
        if key in self._environment:
            msg = "LYCHD_RUNTIME_SECRETS is retired; use the container credential mounts."
            raise ValueError(msg)
        return self._credentials()

    def _credentials(self) -> dict[str, Any]:
        """Retain the established explicit, environment and mounted-file precedence."""
        self._reject_toml_credentials()
        declared = self.current_state.get("server", {})
        server = ServerSettings.model_validate(declared)
        if isinstance(declared, BaseModel):
            return {}  # Explicit section instances already supply their complete values.

        credentials: dict[str, dict[str, SecretStr]] = {}
        for section, field, env_key, secret_name in (
            ("database", "password", "LYCHD_DB_PASSWORD", server.database.password_secret),
            ("database", "runtime_password", "LYCHD_RUNTIME_DB_PASSWORD", server.database.runtime_password_secret),
            ("database", "phoenix_password", "LYCHD_PHOENIX_DB_PASSWORD", server.database.phoenix_password_secret),
            ("web", "secret_key", "LYCHD_APP_SECRET_KEY", server.web.secret_key_secret),
            ("web", "access_password", "LYCHD_LOCAL_ACCESS_PASSWORD", server.web.access_password_secret),
        ):
            existing = declared.get(section, {})
            if isinstance(existing, BaseModel) or field in existing:
                continue
            key = env_key if self._case_sensitive else env_key.lower()
            value = self._environment.get(key)
            if not value:
                file_key = f"{key}_FILE" if self._case_sensitive else f"{key}_file"
                override_path = self._environment.get(file_key)
                value = self._read_file(env_key, override_path, secret_name)
                if value is None:
                    continue
            credentials.setdefault(section, {})[field] = SecretStr(value)
        return {"server": credentials}

    def _read_file(self, env_key: str, override_path: str | None, secret_name: str) -> str | None:
        """Only the container deployment uses an implicit secret mount."""
        if not override_path and not self._use_mounts:
            return None
        path = Path(override_path) if override_path else MOUNTED_SECRETS_DIR / secret_name
        try:
            value = path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            if not override_path:
                return None  # Host bootstrap can precede secret provisioning.
            msg = f"Secret file for {env_key} is unavailable: '{path}'."
            raise ValueError(msg) from None
        except (OSError, UnicodeError):
            msg = f"Secret file for {env_key} cannot be read: '{path}'."
            raise ValueError(msg) from None
        if override_path and value.startswith("lychd-desktop-vault:"):
            from lychd.system.desktop.credentials import resolve_vault_reference

            value = resolve_vault_reference(env_key, path, value)
        if not value:
            msg = f"Secret file for {env_key} is empty: '{path}'."
            raise ValueError(msg)
        return value

    def _reject_toml_credentials(self) -> None:
        raw_server = self.settings_sources_data.get("TomlConfigSettingsSource", {}).get("server", {})
        if not isinstance(raw_server, dict):
            return  # Root validation reports malformed sections.
        toml_server = cast("dict[str, Any]", raw_server)
        for section, field in (
            ("database", "password"),
            ("database", "runtime_password"),
            ("database", "phoenix_password"),
            ("web", "secret_key"),
            ("web", "access_password"),
        ):
            section_values = toml_server.get(section)
            if isinstance(section_values, dict) and field in section_values:
                msg = f"server.{section}.{field} is a runtime credential; TOML may contain only its secret reference."
                raise ValueError(msg)
