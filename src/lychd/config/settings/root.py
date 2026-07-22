"""Root settings loading and composition."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, TomlConfigSettingsSource

from lychd.config.settings.extensions import ExtensionSettings
from lychd.config.settings.orchestration import OrchestrationSettings
from lychd.config.settings.server import ServerSettings
from lychd.system.constants import PATH_LYCHD_TOML


class Settings(BaseSettings):
    """The complete operator-facing configuration composed from its owners."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    server: ServerSettings = Field(default_factory=ServerSettings)
    """The one Vessel process and the services it operates."""
    orchestration: OrchestrationSettings = Field(default_factory=OrchestrationSettings)
    """Run routing and runtime-transition policy."""
    extensions: ExtensionSettings = Field(default_factory=ExtensionSettings)
    """Explicitly activated optional extensions."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,  # noqa: ARG003 - required by Pydantic's override signature
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Return configuration sources from highest to lowest precedence.

        Tests and explicit construction win first, then operator environment
        overrides, then the operator baseline in ``lychd.toml``. This project
        intentionally does not load a ``.env`` file: deployment environment
        must be explicit. Pydantic's file-secret source remains last as its
        conventional fallback; LychD resolves Podman-injected runtime secrets
        separately from these non-secret settings.
        """
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls, toml_file=PATH_LYCHD_TOML),
            file_secret_settings,
        )


@lru_cache(maxsize=1, typed=True)
def get_settings() -> Settings:
    """Load settings without writing files or inventing secrets."""
    return Settings()
