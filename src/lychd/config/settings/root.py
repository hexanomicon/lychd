"""Root settings loading and composition."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import override

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, TomlConfigSettingsSource

from lychd.config.settings.extensions import ExtensionSettings
from lychd.config.settings.orchestration import OrchestrationSettings
from lychd.config.settings.section import SettingsSection
from lychd.config.settings.server import ServerSettings
from lychd.config.settings.sources import RuntimeSecretsSource
from lychd.config.settings.weaver import WeaverSettings
from lychd.system.constants import PATH_LYCHD_TOML


class _SettingsValues(SettingsSection):
    """Shared root schema for source loading and I/O-free snapshot validation."""

    server: ServerSettings = Field(default_factory=ServerSettings)
    """The one Vessel process and the services it operates."""
    orchestration: OrchestrationSettings = Field(default_factory=OrchestrationSettings)
    """Run routing and runtime-transition policy."""
    extensions: ExtensionSettings = Field(default_factory=ExtensionSettings)
    """Explicitly activated optional extensions."""
    weaver: WeaverSettings = Field(default_factory=WeaverSettings)
    """Exact source-registered Bridge casting selection."""


class Settings(_SettingsValues, BaseSettings):
    """Load one configuration generation, including runtime credentials, at construction."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid", hide_input_in_errors=True)

    @classmethod
    @override
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Select startup sources in priority order, excluding dotenv.

        Runtime credentials are loaded here too; consumers only read stored values.
        """
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls, toml_file=PATH_LYCHD_TOML),
            file_secret_settings,
            RuntimeSecretsSource(settings_cls, env_settings),
        )


@dataclass(frozen=True, slots=True)
class SettingsSnapshot:
    """Secret-free declaration JSON with separately retained, masked runtime values."""

    payload: str
    database_password: SecretStr | None = field(default=None, repr=False)
    web_secret_key: SecretStr | None = field(default=None, repr=False)

    @classmethod
    def capture(cls, settings: Settings) -> SettingsSnapshot:
        """Detach one validated Settings tree from its mutable Pydantic models."""
        return cls(
            payload=settings.model_dump_json(round_trip=True),
            database_password=settings.server.database.password,
            web_secret_key=settings.server.web.secret_key,
        )

    def materialize(self) -> Settings:
        """Revalidate the captured values without consulting any settings source."""
        values = _SettingsValues.model_validate(json.loads(self.payload))
        values.server.database = values.server.database.model_copy(update={"password": self.database_password})
        values.server.web = values.server.web.model_copy(update={"secret_key": self.web_secret_key})
        return Settings.model_construct(**dict(values))


@lru_cache(maxsize=1, typed=True)
def get_settings() -> Settings:
    """Load settings without writing files or inventing secrets."""
    return Settings()
