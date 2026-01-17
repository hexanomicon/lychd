from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from litestar.data_extractors import RequestExtractorField, ResponseExtractorField
from litestar.serialization import decode_json, encode_json  # msgspec
from pydantic import Field, PrivateAttr, SecretStr, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from lychd.config.constants import BASE_DIR, HOST_LYCHD_TOML


# --- 2. The Infrastructure (Server) ---
class ServerSettings(BaseSettings):
    """Configuration for Granian/Litestar."""

    model_config = SettingsConfigDict(env_prefix="SERVER_")

    host: str = "0.0.0.0"  # noqa: S104
    port: int = 7134  # LICH
    reload: bool = False
    workers: int = 1
    keep_alive: int = 65


class PhoenixSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PHOENIX_")

    # Port for the Web Interface (e.g. http://localhost:6006)
    ui_port: int = 6006

    # Port for receiving data via HTTP (Standard OTel port)
    otlp_port: int = 4318
    image: str = "docker.io/arizephoenix/phoenix:12"
    host: str = "localhost"
    admin_user: str = "admin"
    admin_password: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(16)),
    )

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.otlp_port}"


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
    password: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(16)),
    )

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

    # --- Evolution (Migrations) ---
    migration_config: str = f"{BASE_DIR}/db/migrations/alembic.ini"
    migration_path: str = f"{BASE_DIR}/db/migrations"
    migration_ddl_version_table: str = "lychd_db_version"

    # cached optimized engine retrieved by get_engine()
    _engine_instance: AsyncEngine | None = PrivateAttr(default=None)

    @property
    def url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    def get_engine(self, *, force_new: bool = False) -> AsyncEngine:
        """Create and cache a SQLAlchemy AsyncEngine instance."""
        if self._engine_instance is None or force_new:
            engine = create_async_engine(
                url=self.url,
                echo=self.echo,
                echo_pool=self.echo_pool,
                # --- POOLING OPTIMIZATIONS ---
                max_overflow=self.max_overflow,
                pool_size=self.pool_size,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=self.pool_pre_ping,
                # LIFO: Better for performance (reuses hot connections)
                pool_use_lifo=True,
                # --- SERIALIZATION via litestars msgspec ---
                json_serializer=encode_json,
                json_deserializer=decode_json,
            )

            @event.listens_for(engine.sync_engine, "connect")
            def _sqla_on_connect(dbapi_connection: Any, _: Any) -> Any:  # pyright: ignore [reportUnusedFunction]
                r"""Hooks into the DBAPI connection to enable direct binary JSON serialization.

                Standard SQLAlchemy dialects expect JSON serializers to return `str`.
                Since LychD uses `msgspec` for high-performance binary serialization (`bytes`),
                this hook configures `asyncpg` to bypass the standard string-conversion overhead.

                It injects a custom codec that:
                1. Accepts already-serialized `bytes` from msgspec (Zero-Copy).
                2. Prepends the PostgreSQL `\x01` version prefix for JSONB.
                3. Decodes raw binary responses directly via `msgspec`.

                Optimization:
                    Avoids the double-encoding redundancy (`bytes` -> `str` -> `bytes`)
                    found in standard implementations.

                Ref:
                    Adapted from connection hooks in `litestar-fullstack` (MIT). https://github.com/litestar-org/litestar-fullstack/blob/main/src/py/app/utils/engine_factory.py#L43
                    See Also https://github.com/sqlalchemy/sqlalchemy/blob/14bfbadfdf9260a1c40f63b31641b27fe9de12a0/lib/sqlalchemy/dialects/postgresql/asyncpg.py#L934
                """

                # The encoder receives the data that is ALREADY serialized to bytes.
                def encoder(already_serialized_bytes: bytes) -> bytes:
                    # Add the required binary prefix. DO NOT call encode_json again.
                    return b"\x01" + already_serialized_bytes

                def decoder(bytes_to_decode: bytes) -> Any:
                    # Strip the prefix and decode using msgspec.
                    return decode_json(bytes_to_decode[1:])

                # Register for both jsonb and json types for robustness.
                dbapi_connection.await_(
                    dbapi_connection.driver_connection.set_type_codec(
                        "jsonb",
                        encoder=encoder,
                        decoder=decoder,
                        schema="pg_catalog",
                        format="binary",
                    ),
                )

                dbapi_connection.await_(
                    dbapi_connection.driver_connection.set_type_codec(
                        "json",
                        encoder=encoder,
                        decoder=decoder,
                        schema="pg_catalog",
                        format="binary",
                    ),
                )

            self._engine_instance = engine
        return self._engine_instance


class LogSettings(BaseSettings):
    """Configuration for Structlog, giving fine-grained control over logging."""

    model_config = SettingsConfigDict(env_prefix="LOG_")

    # --- General ---
    # The minimum level for lychd's own logs.
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # Set to True in production for structured, machine-readable JSON logs.
    json_format: bool = True

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


# --- 6. The Worker ---
class SaqSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAQ_")
    processes: int = 4
    web_enabled: bool = True
    concurrency: int = 10
    use_server_lifespan: bool = True


# This class will hold general app info.
class LychdSettings(BaseSettings):
    """Application configuration using Pydantic for robust validation."""

    model_config = SettingsConfigDict(env_prefix="LYCHD_")

    models_dir: Path = Field(
        default=Path.home() / "models",
        description="The default directory where the models directories are located.",
    )

    mount_read_only_volumes: list[str] = Field(
        default_factory=list,
        description="The additional mounts to give to lych vessel for READ ONLY",
    )


# This class will hold general app info.
class AppSettings(BaseSettings):
    """Application configuration using Pydantic for robust validation."""

    model_config = SettingsConfigDict(env_prefix="APP_")

    # --- Core App Settings ---
    # A random key for signing cookies and other secrets.
    # Set APP__SECRET_KEY in your .env for production.
    secret_key: SecretStr = Field(default_factory=lambda: SecretStr(secrets.token_hex(32)))

    # Enable/disable Litestar's debug mode.
    debug: bool = False

    # Application name.
    name: str = "lychd"

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


class ViteSettings(BaseSettings):
    """Configuration for the Vite plugin."""

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

    # --- Paths ---

    bundle_dir: Path = Field(
        default=BASE_DIR / "public",
        description="Output directory for built assets (matches vite.config.ts: bundleDirectory).",
    )

    resource_dir: Path = Field(
        default=Path("resources"),
        description="Source directory for JS/CSS (matches vite.config.ts: resourceDirectory).",
    )

    html_template_dir: Path = Field(
        default=BASE_DIR / "templates" / "html",
        description="Directory with Jinja templates. Vite watches this for HMR triggers.",
    )

    asset_url: str = Field(default="/static/", description="Base URL for serving assets.")

    @property
    def set_static_files(self) -> bool:
        """Serve static assets via Litestar if URL starts with /."""
        return self.asset_url.startswith("/")


# --- ROOT CONTAINER ---
class Settings(BaseSettings):
    """The Master Configuration.

    Loads from .env and maps nested environment variables.
    Example: SERVER__PORT=9000 overrides server.port
    """

    model_config = SettingsConfigDict(
        # 1. Load Secrets from the hidden .env
        env_nested_delimiter="__",
        extra="ignore",
        # 2. Load Logic from the user's TOML
    )
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
            TomlConfigSettingsSource(settings_cls, toml_file=HOST_LYCHD_TOML),
            file_secret_settings,
        )

    @property
    def reserved_ports_map(self) -> dict[str, int]:
        """Map of Service Name -> Port."""
        return {
            "LychD Server": self.server.port,
            "Phylactery (Postgres)": self.db.port,
            "Oculus (Phoenix UI)": self.phoenix.ui_port,
            "Oculus (Phoenix OTLP)": self.phoenix.otlp_port,
            "Vite (Frontend)": self.vite.port,
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

        return self


@lru_cache(maxsize=1, typed=True)
def get_settings() -> Settings:
    return Settings()
