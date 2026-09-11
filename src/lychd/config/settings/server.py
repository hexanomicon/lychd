"""Settings for the one LychD server process and services it operates."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit

from litestar.data_extractors import RequestExtractorField, ResponseExtractorField
from pydantic import Field, SecretStr, ValidationInfo, field_validator, model_validator

from lychd.config.settings.section import SettingsSection
from lychd.system.secret_names import validate_podman_secret_name

QUEUE_NAMES = frozenset({"runs", "rites"})
_ACCESS_PASSWORD_MIN = 32
_ACCESS_PASSWORD_MAX = 256
_POSTGRES_NAME_MAX_BYTES = 63


def validate_local_access_password(value: SecretStr) -> SecretStr:
    """Reject short or terminal-active local access credentials."""
    password = value.get_secret_value()
    if (
        not _ACCESS_PASSWORD_MIN <= len(password) <= _ACCESS_PASSWORD_MAX
        or not password.isascii()
        or not password.isprintable()
        or any(char.isspace() for char in password)
    ):
        msg = "Local access password must contain 32 to 256 printable non-space ASCII characters"
        raise ValueError(msg)
    return value


class DatabaseSettings(SettingsSection):
    """The database service operated by this server."""

    host: str = "localhost"
    port: int = Field(default=5432, ge=1, le=65535)
    user: str = "lich"
    database: str = "lychd"
    image: str = "docker.io/pgvector/pgvector:pg18-trixie"
    password_secret: str = "lychd_db_password"  # noqa: S105
    """Podman secret name holding the Postgres password, never the password itself."""
    password: SecretStr | None = Field(default=None, min_length=1, exclude=True, repr=False, frozen=True)
    """Password loaded with Settings; absent before provisioning and never exported."""
    runtime_user: str = "lychd_runtime"
    runtime_password_secret: str = "lychd_runtime_db_password"  # noqa: S105
    runtime_password: SecretStr | None = Field(default=None, min_length=1, exclude=True, repr=False, frozen=True)
    phoenix_user: str = "lychd_phoenix"
    phoenix_password_secret: str = "lychd_phoenix_db_password"  # noqa: S105
    phoenix_password: SecretStr | None = Field(default=None, min_length=1, exclude=True, repr=False, frozen=True)
    profile: Literal["memory", "postgres"] = "postgres"
    """Persistence backend: Postgres for normal operation; memory only for focused tests."""
    echo: bool = False
    """Log every SQL statement; useful for diagnosis but noisy and unsuitable for normal operation."""
    echo_pool: bool | str = False
    """Log SQLAlchemy connection-pool activity for database-pool diagnosis."""
    pool_size: int = Field(default=5, ge=0)
    """Persistent connections retained in the SQLAlchemy pool."""
    max_overflow: int = Field(default=10, ge=-1)
    """Temporary connections allowed above ``pool_size`` during demand spikes."""
    pool_timeout: float = Field(default=30.0, ge=0.0, allow_inf_nan=False)
    """Seconds to wait for a pool connection before failing a database operation."""
    pool_recycle: int = Field(default=300, ge=-1, allow_inf_nan=False)
    """Maximum connection age in seconds before pool replacement prevents stale connections."""
    pool_pre_ping: bool = True
    """Test a pooled connection before use and replace it if the database closed it."""
    pool_use_lifo: bool = True
    """Reuse the most recently active pooled connection first."""

    @field_validator("password_secret", "runtime_password_secret", "phoenix_password_secret")
    @classmethod
    def validate_password_secret(cls, value: str) -> str:
        """Reject absolute/traversal names before secret-path composition."""
        return validate_podman_secret_name(value, field_name="server.database.password_secret")

    @field_validator("user", "runtime_user", "phoenix_user", "database")
    @classmethod
    def validate_database_identity(cls, value: str, info: ValidationInfo) -> str:
        """Preserve quoted legacy names while preventing truncation or control bytes."""
        if not value or not value.isprintable() or len(value.encode("utf-8")) > _POSTGRES_NAME_MAX_BYTES:
            msg = "Database identities must be printable, nonempty PostgreSQL names of at most 63 UTF-8 bytes"
            raise ValueError(msg)
        if info.field_name in {"runtime_user", "phoenix_user"} and value.startswith("pg_"):
            msg = "LychD runtime roles cannot use PostgreSQL's reserved pg_ prefix"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def require_separate_roles(self) -> DatabaseSettings:
        """Preserve the bootstrap owner while keeping runtime identities disjoint."""
        roles = (self.user, self.runtime_user, self.phoenix_user)
        if len(set(roles)) != len(roles) or self.database == "phoenix":
            msg = "Bootstrap, runtime and Phoenix roles and application databases must be distinct"
            raise ValueError(msg)
        return self


class WebSettings(SettingsSection):
    """The web application the server exposes and packages into the Vessel."""

    secret_key_secret: str = "lychd_app_secret_key"  # noqa: S105
    """Podman secret name holding the application signing key, never the key itself."""
    secret_key: SecretStr | None = Field(default=None, min_length=1, exclude=True, repr=False, frozen=True)
    """Signing key loaded with Settings; absent before provisioning and never exported."""
    access_password_secret: str = "lychd_local_access_password"  # noqa: S105
    access_password: SecretStr | None = Field(
        default=None, min_length=32, max_length=256, exclude=True, repr=False, frozen=True
    )

    @field_validator("access_password")
    @classmethod
    def validate_access_password(cls, value: SecretStr | None) -> SecretStr | None:
        """Validate explicit, environment and mounted access credentials identically."""
        return validate_local_access_password(value) if value is not None else None

    debug: bool = False
    name: str = "lychd"
    image: str = "ghcr.io/hexanomicon/lychd:latest"
    allowed_cors_origins: list[str] = Field(default_factory=list)
    """Exact loopback browser origins admitted for cross-origin development requests."""
    csrf_cookie_name: str = "csrftoken"
    csrf_cookie_secure: bool = False
    """Require HTTPS when browsers send the CSRF cookie; enable behind an HTTPS Ward/Proxy."""

    @field_validator("secret_key_secret", "access_password_secret")
    @classmethod
    def validate_secret_key_secret(cls, value: str) -> str:
        """Reject absolute/traversal names before secret-path composition."""
        return validate_podman_secret_name(value, field_name="server.web.secret_key_secret")

    @field_validator("allowed_cors_origins")
    @classmethod
    def validate_allowed_cors_origins(cls, values: list[str]) -> list[str]:
        """Admit only explicit HTTP(S) loopback origins without path material."""
        for value in values:
            try:
                origin = urlsplit(value)
                port = origin.port
            except ValueError as exc:
                msg = f"Invalid CORS origin: {value!r}"
                raise ValueError(msg) from exc
            if (
                origin.scheme not in {"http", "https"}
                or origin.hostname not in {"127.0.0.1", "::1", "localhost"}
                or origin.username is not None
                or origin.password is not None
                or bool(origin.path)
                or origin.query
                or origin.fragment
                or (port is not None and port < 1)
            ):
                msg = (
                    "server.web.allowed_cors_origins accepts only exact HTTP(S) "
                    "loopback origins without credentials, paths, queries, or fragments"
                )
                raise ValueError(msg)
        return values


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

    port: int = Field(default=7134, ge=1, le=65535)
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
        if len(set(self.privileged_secret_names)) != len(self.privileged_secret_names):
            msg = "Core credentials must use distinct Podman secret names"
            raise ValueError(msg)
        return self

    @property
    def privileged_secret_names(self) -> tuple[str, ...]:
        """Every core credential forbidden to model-runtime declarations."""
        return (
            self.web.secret_key_secret,
            self.web.access_password_secret,
            self.database.password_secret,
            self.database.runtime_password_secret,
            self.database.phoenix_password_secret,
        )
