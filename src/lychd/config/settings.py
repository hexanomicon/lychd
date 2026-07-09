from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, cast

from litestar.data_extractors import RequestExtractorField, ResponseExtractorField
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from lychd.config.utils import read_secret_from_env_or_file
from lychd.system.constants import PATH_LYCHD_TOML, PATH_REACTOR_INBOX_DIR, PATH_STASIS_DIR

DEFAULT_BUILTIN_EXTENSION_IDS: tuple[str, ...] = (
    "animator",
    "animator/llamacpp",
    "animator/vllm",
    "animator/sglang",
    "observability/phoenix",
    "simulation",
)
"""Built-in extension ids written into a freshly generated lychd.toml."""


def _normalize_absolute_config_path(value: Path | str, *, field_name: str) -> Path:
    """Return a lexical, absolute control path without touching the filesystem."""
    try:
        candidate = Path(value).expanduser()
    except (TypeError, ValueError, RuntimeError) as exc:
        msg = f"{field_name} is not a valid filesystem path: {value}"
        raise ValueError(msg) from exc
    path_text = os.fspath(candidate)
    if "%" in path_text or "\\" in path_text or any(not char.isprintable() for char in path_text):
        msg = f"{field_name} contains characters that are unsafe in a systemd path"
        raise ValueError(msg)
    if not candidate.is_absolute():
        msg = f"{field_name} must be an absolute path: {value}"
        raise ValueError(msg)
    normalized = os.path.normpath(candidate)
    # POSIX permits implementation-defined ``//`` semantics, while Linux treats
    # it as ``/``. Collapse it so containment checks cannot see two spellings.
    if normalized.startswith("//"):
        normalized = f"/{normalized.lstrip('/')}"
    return Path(normalized)


def _paths_overlap(left: Path, right: Path) -> bool:
    """Return whether either lexical path contains the other (including equality)."""
    return left == right or left in right.parents or right in left.parents


# --- 2. The Infrastructure (Server) ---
class ServerSettings(BaseModel):
    """Configuration for the Bone-Sustenance (Granian/Litestar)."""

    host: str = "127.0.0.1"
    port: int = 7134  # LICH
    reload: bool = False
    # Topology A uses a process-local event bus and in-process SAQ workers.
    # More ASGI processes require a durable cross-process event plane first.
    workers: Literal[1] = 1
    keep_alive: int = 65


class DatabaseSettings(BaseModel):
    """Configuration for the Phylactery (Postgres)."""

    host: str = "localhost"
    port: int = 5432
    user: str = "lich"
    database: str = "lychd"
    image: str = "docker.io/pgvector/pgvector:pg18-trixie"
    password_secret: str = "lychd_db_password"  # noqa: S105 - Podman secret name, not secret value.

    # Persistence profile (F4/H5, S3): selects the RunLedger implementation. Default
    # is the durable Postgres substrate; tests set ``memory`` for the loop-confined,
    # DB-free `InMemoryRunLedger`. This is the SAME flag Wave 4 extends to the
    # ConsentLedger + SessionStore — one profile, never mixed.
    profile: Literal["memory", "postgres"] = "postgres"

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

    @property
    def password(self) -> str:
        """Resolve DB password from env override or mounted Podman secret file."""
        return read_secret_from_env_or_file(
            value_env_keys=("DB__PASSWORD", "DB_PASSWORD"),
            file_env_keys=("DB__PASSWORD_FILE", "DB_PASSWORD_FILE"),
            default_file=Path("/run/secrets") / self.password_secret,
            secret_label=self.password_secret,
        )

    @property
    def url(self) -> str:
        """Return an escaped SQLAlchemy URL without hand-built credential interpolation."""
        from sqlalchemy.engine import URL

        return URL.create(
            "postgresql+asyncpg",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        ).render_as_string(hide_password=False)

    @property
    def saq_dsn(self) -> str:
        """Driverless Postgres DSN for SAQ/psycopg (no ``+asyncpg`` driver suffix)."""
        from sqlalchemy.engine import URL

        return URL.create(
            "postgresql",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        ).render_as_string(hide_password=False)


class SigilSettings(BaseModel):
    """The Ward: the process identity + scope grammar (ADR-09, wave4-design §3.1).

    ``scopes=["*"]`` is the ADR-09 local-only Ward default: one settings-derived
    process identity on a single-user loopback surface, not caller authentication.
    ``enforce=False`` makes the scope guards no-op (tests/dev).
    """

    name: str = "magus"
    scopes: list[str] = Field(default_factory=lambda: ["*"])
    enforce: bool = True


class StasisSettings(BaseModel):
    """Durable Stasis checkpoint root (wave4-design §2.3)."""

    dir: Path = PATH_STASIS_DIR

    @field_validator("dir", mode="before")
    @classmethod
    def validate_dir(cls, value: Path | str) -> Path:
        """Keep the durable checkpoint root absolute and lexically normalized."""
        return _normalize_absolute_config_path(value, field_name="stasis.dir")


class LogSettings(BaseModel):
    """The Scrying Mirror: Configuration for Structlog and observability."""

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


class ExtensionSettings(BaseModel):
    """Extension activation lists for the composed runtime image.

    Extensions are inert unless named here. Their own RuneConfig classes become
    loadable only after the extension assembly step imports the selected organ.
    """

    builtins: list[str] = Field(
        default_factory=lambda: list(DEFAULT_BUILTIN_EXTENSION_IDS),
        description=(
            "Built-in extension ids to activate. Fresh configs enable the known built-ins explicitly; "
            "remove an id to deactivate that organ."
        ),
    )
    crypt: list[str] = Field(
        default_factory=list,
        description="Crypt extension ids to activate from the local extension root.",
    )


# --- 6. The Worker ---
class SaqSettings(BaseModel):
    """The Ghoul Labor: Configuration for the SAQ background worker swarm.

    Topology A (F1/S7): workers run in-process on the web loop
    (`QueueConfig.separate_process=False`), so there are no forked processes to
    size — the old ``processes`` and ``use_server_lifespan`` knobs are gone.
    ``concurrency`` bounds per-queue in-loop job concurrency (aligns early with
    Wave-3's `[orchestration.queues]`).
    """

    web_enabled: bool = True


# --- 6b. The Orchestration Doctrine ([orchestration]) ---
class QueueSettings(BaseModel):
    """Per-queue in-loop job concurrency (sizes SAQ's `QueueConfig.concurrency`)."""

    concurrency: int = Field(default=2, ge=1, le=128)


class RoutingRule(BaseModel):
    """One `[orchestration.routing]` entry: which physical queue, at what priority."""

    queue: str = "runs"
    priority: int = Field(default=50, ge=0, le=100)


class SwitchingSettings(BaseModel):
    """`[orchestration.switching]`: the honest hard-swap gate + lease-drain timeout."""

    policy: str = "evict-idle"
    # The normal deployment is caged and has no host user-bus socket. Direct
    # Systemd actuation is an explicit uncaged/development choice.
    actuator: Literal["systemd", "host-reactor"] = "host-reactor"
    host_reactor_dir: Path = PATH_REACTOR_INBOX_DIR
    min_priority_for_hard_swap: int = Field(default=40, ge=0, le=100)
    drain_timeout_s: float = Field(default=120.0, gt=0)
    # Model warm-up is different physics from draining old work (a 70B load can exceed
    # the drain budget); `await_warm` gets its own ceiling instead of borrowing drain's.
    warmup_timeout_s: float = Field(default=180.0, gt=0)
    reactor_ack_timeout_s: float = Field(default=120.0, gt=0)

    @field_validator("host_reactor_dir", mode="before")
    @classmethod
    def validate_host_reactor_dir(cls, value: Path | str) -> Path:
        """Require a distinct, conventionally named Host Reactor inbox."""
        inbox = _normalize_absolute_config_path(
            value,
            field_name="orchestration.switching.host_reactor_dir",
        )
        if inbox.name != "inbox":
            msg = "orchestration.switching.host_reactor_dir must be an 'inbox' directory"
            raise ValueError(msg)
        return inbox

    @property
    def host_reactor_journal_dir(self) -> Path:
        """Return the host-owned, Vessel-read-only journal paired with the inbox."""
        return self.host_reactor_dir.parent / "journal"


class WhimSettings(BaseModel):
    """`[orchestration.whim]`: idle-eviction + preload shape (consumers land Wave 6)."""

    idle_evict_after_s: int = 0  # 0 = disabled; whim RITES land Wave 6 (A4-U8)
    preload: list[str] = Field(default_factory=list)


def _default_queue_settings() -> dict[str, QueueSettings]:
    return {
        "runs": QueueSettings(concurrency=2),
        "rites": QueueSettings(concurrency=4),
    }


def _default_routing_settings() -> dict[str, RoutingRule]:
    return {
        "default": RoutingRule(queue="runs", priority=50),
        "cli": RoutingRule(queue="runs", priority=50),
        "bridge": RoutingRule(queue="runs", priority=70),
        "rite": RoutingRule(queue="rites", priority=20),
    }


class OrchestrationSettings(BaseModel):
    """The `[orchestration]` doctrine: queues, routing, switching, and whim."""

    queues: dict[str, QueueSettings] = Field(default_factory=_default_queue_settings)
    routing: dict[str, RoutingRule] = Field(default_factory=_default_routing_settings)
    switching: SwitchingSettings = Field(default_factory=SwitchingSettings)
    whim: WhimSettings = Field(default_factory=WhimSettings)  # shape now; consumers Wave 6

    @model_validator(mode="before")
    @classmethod
    def merge_required_topology(cls, value: object) -> object:
        """Deep-merge partial TOML/env tables onto the fixed v1 queue topology."""
        if not isinstance(value, dict):
            return value
        data = dict(cast("dict[str, object]", value))
        configured_queues = data.get("queues")
        if isinstance(configured_queues, dict):
            configured_queue_map = cast("dict[str, object]", configured_queues)
            unknown = sorted(set(configured_queue_map).difference(_default_queue_settings()))
            if unknown:
                msg = f"Unknown physical orchestration queues: {', '.join(unknown)}"
                raise ValueError(msg)
            queues: dict[str, object] = dict(_default_queue_settings())
            queues.update(configured_queue_map)
            data["queues"] = queues
        configured_routing = data.get("routing")
        if isinstance(configured_routing, dict):
            configured_routing_map = cast("dict[str, object]", configured_routing)
            routing: dict[str, object] = dict(_default_routing_settings())
            routing.update(configured_routing_map)
            data["routing"] = routing
        return data

    @model_validator(mode="after")
    def validate_routing_topology(self) -> OrchestrationSettings:
        """Every semantic route must land on one configured, implemented queue."""
        missing = sorted({rule.queue for rule in self.routing.values()}.difference(self.queues))
        if missing:
            msg = f"Orchestration routing references unknown queues: {', '.join(missing)}"
            raise ValueError(msg)
        return self


class LychdSettings(BaseModel):
    """The Soulstone Protocols: Bindings for local and remote manifestations."""

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

    alliances: list[list[str]] = Field(
        default_factory=list,
        description="Explicit coven alliances that relax implicit conflict generation between soulstone groups.",
    )


# This class will hold general app info.
class AppSettings(BaseModel):
    """The Inscription Registry: Global identity and security markings."""

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

    @property
    def secret_key(self) -> str:
        """Resolve app signing key from env override or mounted Podman secret file."""
        return read_secret_from_env_or_file(
            value_env_keys=("APP__SECRET_KEY", "APP_SECRET_KEY"),
            file_env_keys=("APP__SECRET_KEY_FILE", "APP_SECRET_KEY_FILE"),
            default_file=Path("/run/secrets") / self.secret_key_secret,
            secret_label=self.secret_key_secret,
        )


class ViteSettings(BaseModel):
    """The Altar Manifest: Configuration for the Vite frontend vessel."""

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
    extensions: ExtensionSettings = Field(default_factory=ExtensionSettings)
    orchestration: OrchestrationSettings = Field(default_factory=OrchestrationSettings)
    sigil: SigilSettings = Field(default_factory=SigilSettings)
    stasis: StasisSettings = Field(default_factory=StasisSettings)

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

    @model_validator(mode="after")
    def check_control_path_boundaries(self) -> Settings:
        """Keep checkpoints separate from the Vessel-writable Reactor channel."""
        stasis_dir = self.stasis.dir
        switching = self.orchestration.switching
        inbox_dir = switching.host_reactor_dir
        journal_dir = switching.host_reactor_journal_dir

        for label, reactor_dir in (("inbox", inbox_dir), ("journal", journal_dir)):
            if _paths_overlap(stasis_dir, reactor_dir):
                msg = f"stasis.dir must not overlap the Host Reactor {label}: {reactor_dir}"
                raise ValueError(msg)
        return self


@lru_cache(maxsize=1, typed=True)
def get_settings() -> Settings:
    """Load immutable-by-convention settings without I/O side effects or invented secrets."""
    return Settings()
