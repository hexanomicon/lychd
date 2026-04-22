from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from litestar.data_extractors import RequestExtractorField, ResponseExtractorField
from pydantic import Field, PrivateAttr, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from lychd.config.utils import (
    codex_permission_issues,
    needs_generated_secret_fallback,
    read_secret_from_env_or_file,
)
from lychd.system.constants import PATH_LYCHD_TOML


# --- 2. The Infrastructure (Server) ---
class ServerSettings(BaseSettings):
    """Configuration for the Bone-Sustenance (Granian/Litestar)."""

    model_config = SettingsConfigDict(env_prefix="SERVER_")

    host: str = "0.0.0.0"  # noqa: S104
    port: int = 7134  # LICH
    reload: bool = False
    workers: int = 1
    keep_alive: int = 65


class DatabaseSettings(BaseSettings):
    """Configuration for the Phylactery (Postgres)."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        extra="ignore",
    )

    host: str = "localhost"
    port: int = 5432
    user: str = "lich"
    database: str = "lychd"
    image: str = "docker.io/pgvector/pgvector:pg18-trixie"
    password_secret: str = "lychd_db_password"  # noqa: S105 - Podman secret name, not secret value.

    # --- Logging ---
    echo: bool = False
    echo_pool: bool | str = False

    # --- Connection Pooling ---
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 300
    pool_pre_ping: bool = True
    pool_use_lifo: bool = True  # TCP should be still open

    _runtime_password_override: str | None = PrivateAttr(default=None)

    @property
    def password(self) -> str:
        """Resolve DB password from env override or mounted Podman secret file."""
        if self._runtime_password_override is not None:
            return self._runtime_password_override
        return read_secret_from_env_or_file(
            value_env_keys=("DB__PASSWORD", "DB_PASSWORD"),
            file_env_keys=("DB__PASSWORD_FILE", "DB_PASSWORD_FILE"),
            default_file=Path("/run/secrets") / self.password_secret,
            secret_label=self.password_secret,
        )

    def set_runtime_password_override(self, value: str) -> None:
        """Set an in-memory password fallback used when no configured source exists."""
        self._runtime_password_override = value

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class LogSettings(BaseSettings):
    """The Scrying Mirror: Configuration for Structlog and observability."""

    model_config = SettingsConfigDict(env_prefix="LOG_")

    # --- General ---
    # The minimum level for lychd's own logs.
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # Force JSON output (True) or Console output (False). If None (default), auto-detects based on TTY.
    json_format: bool | None = None

    # --- HTTP Middleware Logging ---
    # Which parts of the incoming request to include in logs.
    request_fields: list[RequestExtractorField] = ["path", "method", "query", "path_params"]
    # Which parts of the outgoing response to include in logs.
    response_fields: list[ResponseExtractorField] = ["status_code"]

    # --- Specific Logger Levels ---
    # These let you quiet down chatty libraries without hiding your own app's logs.
    # Use numeric levels here (e.g., INFO=20, WARNING=30, ERROR=40)
    sqlalchemy_level: int = 30  # WARNING
    saq_level: int = 30  # WARNING
    granian_level: int = 30  # WARNING (for the web server)
    pydantic_ai_level: int = 10  # DEBUG


class PhoenixSettings(BaseSettings):
    """Configuration for Arize Phoenix (The Oculus)."""

    model_config = SettingsConfigDict(env_prefix="PHOENIX_")

    image: str = "docker.io/arize-ai/phoenix:latest"
    ui_port: int = 6006
    otlp_port: int = 4317


# --- 6. The Worker ---
class SaqSettings(BaseSettings):
    """The Ghoul Labor: Configuration for the SAQ background worker swarm."""

    model_config = SettingsConfigDict(env_prefix="SAQ_")
    processes: int = 4
    web_enabled: bool = True
    concurrency: int = 10
    use_server_lifespan: bool = True


class LychdSettings(BaseSettings):
    """The Soulstone Protocols: Bindings for local and remote manifestations."""

    model_config = SettingsConfigDict(env_prefix="LYCHD_")

    # --- 1. Soulstone Defaults (Wild Bindings) ---
    # These containers are alien (vLLM, Llama.cpp). We must provide raw bind strings
    # because we cannot assume their internal directory structure.
    models_dir: Path = Field(
        default=Path.home() / "models",
        description="A helper path. Referenced by default_soulstone_mounts.",
    )

    default_soulstone_mounts: list[str] = Field(
        default_factory=lambda: [f"{Path.home()}/models:/models:ro,Z"],
        description="Volumes mounted into EVERY Soulstone. Format: host:container:opts",
    )

    # --- 2. Sphere IV: The Library (Read-Only Reference) ---
    # User provides: [Path("/home/lucy/books"), Path("/mnt/data/wiki")]
    # Binder maps to:
    #   - /home/lich/library/books (RO)
    #   - /home/lich/library/wiki  (RO)
    library_sources: list[Path] = Field(
        default_factory=list,
        description="Host directories to mount Read-Only (RO) for the Agent to read.",
    )

    # --- 3. Sphere II: The Outlands (Read-Write Labor) ---
    # User provides: [Path("/home/lucy/Projects/MyStartup")]
    # Binder maps to:
    #   - /home/lich/work/MyStartup (RW)
    #
    # WARNING: The Agent has Write Access here. Safety is guaranteed via Git only, no btrfs.
    work_sources: list[Path] = Field(
        default_factory=list,
        description="Host directories to mount Read-Write (RW) for the Agent to edit.",
    )


# This class will hold general app info.
class AppSettings(BaseSettings):
    """The Inscription Registry: Global identity and security markings."""

    model_config = SettingsConfigDict(env_prefix="APP_")

    # --- Core App Settings ---
    # Podman secret reference for the Litestar/CSRF signing key.
    secret_key_secret: str = "lychd_app_secret_key"  # noqa: S105 - Podman secret name, not secret value.

    # Enable/disable Litestar's debug mode.
    debug: bool = False

    # Application name.
    name: str = "lychd"
    image: str = "ghcr.io/hexanomicon/lychd:latest"

    # Frontend URL, useful for generating absolute links.
    url: str = "http://localhost:8000"

    # --- Security Settings ---
    # A list of allowed origins for CORS.
    # In .env: APP__ ALLOWED_CORS_ORIGINS="http://localhost:8000,https://my-app.com"
    allowed_cors_origins: list[str] = ["*"]

    # The name of the cookie used for CSRF protection.
    csrf_cookie_name: str = "csrftoken"

    # Set to True in production if you're using HTTPS.
    csrf_cookie_secure: bool = False
    _runtime_secret_key_override: str | None = PrivateAttr(default=None)

    @property
    def secret_key(self) -> str:
        """Resolve app signing key from env override or mounted Podman secret file."""
        if self._runtime_secret_key_override is not None:
            return self._runtime_secret_key_override
        return read_secret_from_env_or_file(
            value_env_keys=("APP__SECRET_KEY", "APP_SECRET_KEY"),
            file_env_keys=("APP__SECRET_KEY_FILE", "APP_SECRET_KEY_FILE"),
            default_file=Path("/run/secrets") / self.secret_key_secret,
            secret_label=self.secret_key_secret,
        )

    def set_runtime_secret_key_override(self, value: str) -> None:
        """Set an in-memory signing-key fallback when no configured source exists."""
        self._runtime_secret_key_override = value


class ViteSettings(BaseSettings):
    """The Altar Manifest: Configuration for the Vite frontend vessel."""

    model_config = SettingsConfigDict(env_prefix="VITE_")

    dev_mode: bool = Field(default=False, description="Start `vite` development server. Set with VITE_DEV_MODE=true")

    use_server_lifespan: bool = Field(
        default=True,
        description="Auto start and stop `vite` processes with the backend.",
    )

    host: str = Field(
        default="0.0.0.0",  # noqa: S104
        description="The host the `vite` process will listen on.",
    )

    port: int = Field(default=5173, description="The port to start vite on.")

    hot_reload: bool = Field(default=True, description="Enable Hot Module Replacement (HMR).")

    asset_url: str = Field(default="/static/", description="Base URL for serving assets.")

    @property
    def set_static_files(self) -> bool:
        """Serve static assets via Litestar if URL starts with /."""
        return self.asset_url.startswith("/")


# --- ROOT CONTAINER ---
class Settings(BaseSettings):
    """The Great Codex: The unified manifestation of all configuration layers.

    Loads from .env and maps nested environment variables.
    Example: SERVER__PORT=9000 overrides server.port
    """

    model_config = SettingsConfigDict(
        # 1. Load Secrets from the hidden .env
        env_nested_delimiter="__",
        extra="ignore",
        # 2. Load Logic from the user's TOML
    )
    lychd: LychdSettings = Field(default_factory=LychdSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    log: LogSettings = Field(default_factory=LogSettings)
    saq: SaqSettings = Field(default_factory=SaqSettings)
    vite: ViteSettings = Field(default_factory=ViteSettings)
    phoenix: PhoenixSettings = Field(default_factory=PhoenixSettings)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            # Load from the TOML file specified in constants.py
            TomlConfigSettingsSource(settings_cls, toml_file=PATH_LYCHD_TOML),
            file_secret_settings,
        )

    @property
    def reserved_ports_map(self) -> dict[str, int]:
        """Map of Service Name -> Port."""
        return {
            "LychD Server": self.server.port,
            "Phylactery (Postgres)": self.db.port,
            "Vite (Frontend)": self.vite.port,
            "Oculus (Phoenix)": self.phoenix.ui_port,
        }

    @model_validator(mode="after")
    def check_port_conflicts(self) -> Settings:
        """Ensure no critical system ports overlap."""
        # Invert to check for duplicates: {port: [names]}
        port_map: dict[int, list[str]] = {}
        for name, port in self.reserved_ports_map.items():
            port_map.setdefault(port, []).append(name)

        # Find collisions
        errors: list[str] = []
        for port, names in port_map.items():
            if len(names) > 1:
                errors.append(f"Port {port} is claimed by multiple services: {', '.join(names)}")

        if errors:
            _msg = f"Configuration Error: {'; '.join(errors)}"
            raise ValueError(_msg)

        codex_issues = codex_permission_issues(PATH_LYCHD_TOML)
        if codex_issues:
            import warnings
            warnings.warn(
                f"codex_permissions_policy_violation: path={PATH_LYCHD_TOML} issues={codex_issues}",
                UserWarning,
                stacklevel=2,
            )

        return self


def ensure_internal_secret_fallbacks(settings: Settings) -> list[str]:
    """Ensure app/db runtime secrets exist even before Podman bind.

    This is a startup safety-net for direct process execution (development,
    tests, or any flow that boots without mounted Podman secrets). It does not
    replace bind-time Podman secret provisioning.
    """
    created: list[str] = []

    if needs_generated_secret_fallback(
        value_env_keys=("APP__SECRET_KEY", "APP_SECRET_KEY"),
        file_env_keys=("APP__SECRET_KEY_FILE", "APP_SECRET_KEY_FILE"),
        default_file=Path("/run/secrets") / settings.app.secret_key_secret,
    ):
        settings.app.set_runtime_secret_key_override(secrets.token_hex(32))
        created.append(settings.app.secret_key_secret)

    if needs_generated_secret_fallback(
        value_env_keys=("DB__PASSWORD", "DB_PASSWORD"),
        file_env_keys=("DB__PASSWORD_FILE", "DB_PASSWORD_FILE"),
        default_file=Path("/run/secrets") / settings.db.password_secret,
    ):
        settings.db.set_runtime_password_override(secrets.token_urlsafe(16))
        created.append(settings.db.password_secret)

    return created


@lru_cache(maxsize=1, typed=True)
def get_settings() -> Settings:
    settings = Settings()
    ensure_internal_secret_fallbacks(settings)
    return settings
