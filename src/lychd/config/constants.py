from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from litestar.utils.module_loader import module_to_os_path

# ==============================================================================
# I. INTERNAL IDENTITY & ASSETS
# ==============================================================================
# Core module identity and internal file paths.

DEFAULT_MODULE_NAME: Final[str] = "lychd"
"""The core name of the entity. Used for directory naming on the Host."""

BASE_DIR: Final[Path] = module_to_os_path(DEFAULT_MODULE_NAME)
"""Defines the absolute path to the module's root directory."""

RUNE_TEMPLATE_DIR: Final[Path] = BASE_DIR / "domain" / "runes" / "templates"
"""Points to the Jinja2 templates for Systemd units."""

HTML_TEMPLATE_DIR: Final[Path] = BASE_DIR / "domain" / "web" / "templates"
"""Points to the Jinja2 templates for the Web UI."""


# ==============================================================================
# II. THE SPHERES (Shared Nomenclature)
# ==============================================================================
# Directory names shared between Host logic and Container logic.

DIR_LAB: Final[str] = "lab"
"""The name of the Output Sphere (Agent Workspace)."""

DIR_EXTENSIONS: Final[str] = "extensions"
"""The name of the Living Tissue Sphere (Plugins)."""

DIR_LIBRARY: Final[str] = "library"
"""The name of the Reference Sphere (External Read-Only Mounts)."""


# ==============================================================================
# III. THE PHYSICAL LAYER (Host Paths)
# ==============================================================================
# These paths define where data lives on the HOST Operating System.
# Used by the CLI (`lychd`) to perform Rituals (Backup, Bind, Init).

# --- Base Resolvers ---
_xdg_data_home = os.getenv("XDG_DATA_HOME")
_data_root = Path(_xdg_data_home) if _xdg_data_home else Path.home() / ".local" / "share"

_xdg_config_home = os.getenv("XDG_CONFIG_HOME")
_config_root = Path(_xdg_config_home) if _xdg_config_home else Path.home() / ".config"


# --- A. The Crypt (Data Persistence) ---

HOST_CRYPT: Final[Path] = _data_root / DEFAULT_MODULE_NAME
"""The Root of the Crypt.
Defines the physical directory containing both the live data and the snapshots.
Respects `XDG_DATA_HOME`, defaulting to `~/.local/share/lychd`.
"""

HOST_ACTIVE_SUBVOLUME: Final[Path] = HOST_CRYPT / "active"
"""The Active Subvolume (Host View).
This is the Btrfs subvolume. It contains all state (DB, Lab, Extensions),
but is NEVER mounted wholly into the container.
"""

HOST_SNAPSHOTS: Final[Path] = HOST_CRYPT / "snapshots"
"""The Snapshots Store (Host View).
Contains atomic, read-only backups of the Active subvolume.
"""

HOST_POSTGRES_DATA: Final[Path] = HOST_ACTIVE_SUBVOLUME / "postgres"
"""The Postgres Data (Host View).
Used by `lychd init` to disable Copy-on-Write (CoW) (`chattr +C`) here.
"""

HOST_LAB: Final[Path] = HOST_ACTIVE_SUBVOLUME / DIR_LAB
"""The Lab (Host View).
Read-Write workspace. Used for Import/Export/Install operations.
"""

HOST_EXTENSIONS: Final[Path] = HOST_ACTIVE_SUBVOLUME / DIR_EXTENSIONS
"""The Extensions (Host View).
Read-Write storage. Used for promoting code from Lab to Live.
"""


# --- B. The Codex (Configuration) ---

HOST_CODEX: Final[Path] = _config_root / DEFAULT_MODULE_NAME
"""The Codex Root.
Defines the directory containing configuration files.
Respects `XDG_CONFIG_HOME`, defaulting to `~/.config/lychd`.
"""

HOST_LYCHD_TOML: Final[Path] = HOST_CODEX / "lychd.toml"
"""Points to the Prime Directive configuration file."""

HOST_SOULSTONES: Final[Path] = HOST_CODEX / "soulstones"
"""Points to the directory containing Soulstone TOML definitions."""

HOST_PORTALS: Final[Path] = HOST_CODEX / "portals"
"""Points to the directory containing Portal TOML definitions."""


# --- C. The Runes (Systemd Integration) ---

HOST_GENERATED_UNITS: Final[Path] = _config_root / "containers" / "systemd"
"""The Runes Binding Site.
Where the Scribe writes active Quadlet files (Systemd User Path).
"""


# ==============================================================================
# IV. THE VESSEL (Container Paths)
# ==============================================================================
# These paths define where data lives INSIDE the Container.
# Naming Convention: Explicitly states _RW_ (Read/Write) or _RO_ (Read-Only).

CONTAINER_ROOT: Final[Path] = Path("/app")
"""The Application Root inside the container."""

CONTAINER_RW_LAB: Final[Path] = CONTAINER_ROOT / DIR_LAB
"""The Laboratory (Read-Write).
Mapped from `HOST_LAB`.
The Agent has full write access here to generate artifacts and build plugins.
"""

CONTAINER_RO_EXTENSIONS: Final[Path] = CONTAINER_ROOT / DIR_EXTENSIONS
"""The Extensions (Read-Only).
Mapped from `HOST_EXTENSIONS`.
The Agent CANNOT modify these files. Updates must be promoted via CLI.
"""

CONTAINER_RO_LIBRARY: Final[Path] = CONTAINER_ROOT / DIR_LIBRARY
"""The Library (Read-Only).
This is where external user directories (configured in `lychd.toml`) are mounted.
"""


# ------------------------------------------------------------------------------
# REQUIRED CONTAINERFILE INSTRUCTION
# ------------------------------------------------------------------------------
# You MUST copy this command into your Containerfile *before* switching users.
#
# RUN mkdir -p /app/lab /app/extensions /app/library && \
#     chown appuser:appuser /app/lab /app/extensions /app/library
# ------------------------------------------------------------------------------


# ==============================================================================
# V. INFRASTRUCTURE CONSTANTS (Immutable Internal Ports)
# ==============================================================================
# These ports are hardcoded into the container images we use.
# We map User Settings (External Ports) to these Internal Ports via Quadlets.

CONTAINER_LYCHD_PORT: Final[int] = 8000
"""The internal port Granian listens on (LychD)."""

CONTAINER_POSTGRES_PORT: Final[int] = 5432
"""The standard internal PostgreSQL port."""

CONTAINER_PHOENIX_UI_PORT: Final[int] = 6006
"""The standard internal Arize Phoenix UI port."""

CONTAINER_PHOENIX_OTLP_PORT: Final[int] = 4318
"""The standard internal OTLP (OpenTelemetry) receiver port."""

# ==============================================================================
# VI. APPLICATION LAWS (Web/DB Constants)
# ==============================================================================

DB_SESSION_DEPENDENCY_KEY: Final[str] = "db_session"
"""The name of the key used for dependency injection of the database session."""

DTO_INFO_KEY: Final[str] = "info"
"""The name of the key used for storing DTO information."""

DEFAULT_PAGINATION_SIZE: Final[int] = 20
"""Default page size to use."""

CACHE_EXPIRATION: Final[int] = 60
"""Default cache key expiration in seconds."""

HEALTH_ENDPOINT: Final[str] = "/health"
"""The endpoint to use for the the service health check."""

SITE_INDEX: Final[str] = "/"
"""The site index URL."""

OPENAPI_SCHEMA: Final[str] = "/schema"
"""The URL path to use for the OpenAPI documentation."""

ENCRYPTION_KEY_LENGTH: Final[int] = 32
"""Length of the encryption keys."""
