"""Settings for the one LychD server process and services it operates."""

from __future__ import annotations

from typing import Literal

from litestar.data_extractors import RequestExtractorField, ResponseExtractorField
from pydantic import Field, field_validator, model_validator

from lychd.config.settings.section import SettingsSection
from lychd.system.secret_names import validate_podman_secret_name

QUEUE_NAMES = frozenset({"runs", "rites"})


class DatabaseSettings(SettingsSection):
    """The database service operated by this server."""

    host: str = "localhost"
    port: int = 5432
    user: str = "lich"
    database: str = "lychd"
    image: str = "docker.io/pgvector/pgvector:pg18-trixie"
    password_secret: str = "lychd_db_password"  # noqa: S105
    """Podman secret name holding the Postgres password, never the password itself."""
    profile: Literal["memory", "postgres"] = "postgres"
    """Persistence backend: Postgres for normal operation; memory only for focused tests."""
    echo: bool = False
    """Log every SQL statement; useful for diagnosis but noisy and unsuitable for normal operation."""
    echo_pool: bool | str = False
    """Log SQLAlchemy connection-pool activity for database-pool diagnosis."""
    pool_size: int = 5
    """Persistent connections retained in the SQLAlchemy pool."""
    max_overflow: int = 10
    """Temporary connections allowed above ``pool_size`` during demand spikes."""
    pool_timeout: int = 30
    """Seconds to wait for a pool connection before failing a database operation."""
    pool_recycle: int = 300
    """Maximum connection age in seconds before pool replacement prevents stale connections."""
    pool_pre_ping: bool = True
    """Test a pooled connection before use and replace it if the database closed it."""
    pool_use_lifo: bool = True
    """Reuse the most recently active pooled connection first."""

    @field_validator("password_secret")
    @classmethod
    def validate_password_secret(cls, value: str) -> str:
        """Reject absolute/traversal names before secret-path composition."""
        return validate_podman_secret_name(value, field_name="server.database.password_secret")


class WebSettings(SettingsSection):
    """The web application the server exposes and packages into the Vessel."""

    secret_key_secret: str = "lychd_app_secret_key"  # noqa: S105
    """Podman secret name holding the application signing key, never the key itself."""
    debug: bool = False
    name: str = "lychd"
    image: str = "ghcr.io/hexanomicon/lychd:latest"
    url: str = "http://localhost:8000"
    allowed_cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    """Browser origins allowed to make cross-origin requests to the loopback Vessel."""
    csrf_cookie_name: str = "csrftoken"
    csrf_cookie_secure: bool = False
    """Require HTTPS when browsers send the CSRF cookie; enable behind an HTTPS Ward/Proxy."""

    @field_validator("secret_key_secret")
    @classmethod
    def validate_secret_key_secret(cls, value: str) -> str:
        """Reject absolute/traversal names before secret-path composition."""
        return validate_podman_secret_name(value, field_name="server.web.secret_key_secret")


class LoggingSettings(SettingsSection):
    """Structured logging owned by the running server process."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    json_format: bool | None = None
    """Force JSON logs on or off; ``null`` selects JSON only when output is not a terminal."""
    request_fields: list[RequestExtractorField] = Field(
        default_factory=lambda: ["path", "method", "query", "path_params"]
    )
    response_fields: list[ResponseExtractorField] = Field(default_factory=lambda: ["status_code"])
    sqlalchemy_level: int = 30
    saq_level: int = 30
    granian_level: int = 30
    pydantic_ai_level: int = 10


class ServerJobsSettings(SettingsSection):
    """Concurrency and optional inspection UI for the Vessel's fixed job system."""

    admin_ui_enabled: bool = False
    """Mount SAQ's diagnostic UI on this Vessel's existing HTTP server; it starts no process or port and has no LychD-specific guard."""
    admin_ui_path: str = "/saq"
    """Absolute path on the Vessel's existing HTTP address where the optional SAQ diagnostic UI is mounted."""
    interactive_concurrency: int = Field(default=2, ge=1, le=128)
    """Maximum simultaneous interactive workflow jobs on this one Vessel event loop."""
    background_concurrency: int = Field(default=4, ge=1, le=128)
    """Maximum simultaneous background rite jobs on this one Vessel event loop."""

    @field_validator("admin_ui_path")
    @classmethod
    def validate_admin_ui_path(cls, value: str) -> str:
        if not value.startswith("/"):
            msg = "server.jobs.admin_ui_path must start with '/'."
            raise ValueError(msg)
        return value.rstrip("/") or "/"


class ServerSettings(SettingsSection):
    """Everything this one LychD server process runs or exposes."""

    host: Literal["127.0.0.1", "::1"] = "127.0.0.1"
    port: int = 7134
    reload: bool = False
    """Restart the development server when Python source files change."""
    keep_alive: int = 65
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    web: WebSettings = Field(default_factory=WebSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    jobs: ServerJobsSettings = Field(default_factory=ServerJobsSettings)
    """Concurrency and inspection settings for jobs running inside this Vessel process."""

    @property
    def reserved_ports_map(self) -> dict[str, int]:
        """Return the host ports claimed by services this server operates."""
        return {
            "LychD Server": self.port,
            "Phylactery (Postgres)": self.database.port,
        }

    @model_validator(mode="after")
    def validate_port_assignments(self) -> ServerSettings:
        """Reject two services operated by one server claiming one host port."""
        claims: dict[int, list[str]] = {}
        for name, port in self.reserved_ports_map.items():
            claims.setdefault(port, []).append(name)
        conflicts = [
            f"Port {port} is claimed by multiple services: {', '.join(names)}"
            for port, names in claims.items()
            if len(names) > 1
        ]
        if conflicts:
            msg = f"Configuration Error: {'; '.join(conflicts)}"
            raise ValueError(msg)
        if self.web.secret_key_secret == self.database.password_secret:
            msg = "Core application-signing and database-password secrets must use distinct Podman secret names"
            raise ValueError(msg)
        return self
