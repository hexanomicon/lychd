"""Startup-only adaptation of the core credential environment and Podman mounts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast, override

from pydantic import BaseModel, SecretStr
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, EnvSettingsSource, PydanticBaseSettingsSource

from lychd.config.settings.server import ServerSettings

MOUNTED_SECRETS_DIR = Path("/run/secrets")


class RuntimeSecretsSource(PydanticBaseSettingsSource):
    """Fill runtime credentials from Pydantic's captured environment and mounted files."""

    def __init__(self, settings_cls: type[BaseSettings], environment: PydanticBaseSettingsSource) -> None:
        """Reuse the environment captured by Pydantic for this construction."""
        super().__init__(settings_cls)
        if not isinstance(environment, EnvSettingsSource):
            msg = "Runtime secrets require Pydantic's environment source."
            raise TypeError(msg)
        self._environment = environment.env_vars
        self._case_sensitive = environment.case_sensitive

    @override
    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    @override
    def __call__(self) -> dict[str, Any]:
        self._reject_toml_credentials()
        declared = self.current_state.get("server", {})
        server = ServerSettings.model_validate(declared)
        if isinstance(declared, BaseModel):
            return {}  # Explicit section instances already supply their complete values.

        credentials: dict[str, dict[str, SecretStr]] = {}
        for section, field, env_key, secret_name in (
            ("database", "password", "LYCHD_DB_PASSWORD", server.database.password_secret),
            ("web", "secret_key", "LYCHD_APP_SECRET_KEY", server.web.secret_key_secret),
        ):
            existing = declared.get(section, {})
            if isinstance(existing, BaseModel) or field in existing:
                continue
            key = env_key if self._case_sensitive else env_key.lower()
            value = self._environment.get(key)
            if not value:
                file_key = f"{key}_FILE" if self._case_sensitive else f"{key}_file"
                override_path = self._environment.get(file_key)
                path = Path(override_path) if override_path else MOUNTED_SECRETS_DIR / secret_name
                try:
                    value = path.read_text(encoding="utf-8").strip()
                except FileNotFoundError:
                    if not override_path:
                        continue  # Host bootstrap can precede secret provisioning.
                    msg = f"Secret file for {env_key} is unavailable: '{path}'."
                    raise ValueError(msg) from None
                except (OSError, UnicodeError):
                    msg = f"Secret file for {env_key} cannot be read: '{path}'."
                    raise ValueError(msg) from None
                if not value:
                    msg = f"Secret file for {env_key} is empty: '{path}'."
                    raise ValueError(msg)
            credentials[section] = {field: SecretStr(value)}
        return {"server": credentials}

    def _reject_toml_credentials(self) -> None:
        raw_server = self.settings_sources_data.get("TomlConfigSettingsSource", {}).get("server", {})
        if not isinstance(raw_server, dict):
            return  # Root validation reports malformed sections.
        toml_server = cast("dict[str, Any]", raw_server)
        for section, field in (("database", "password"), ("web", "secret_key")):
            section_values = toml_server.get(section)
            if isinstance(section_values, dict) and field in section_values:
                msg = f"server.{section}.{field} is a runtime credential; TOML may contain only its secret reference."
                raise ValueError(msg)
