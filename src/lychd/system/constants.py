"""Defines the application's *Runtime Blueprint*.

This module contains constants that describe the physical and network footprint
of the LychD application on the end-user's host system. These values define
"where the application lives" in the wild.

Think of this as the application's "Address Book" and "Physical Manifest":
- It defines the runtime paths based on XDG standards (`PATH_CODEX_ROOT`).
- It declares the core network ports for container exposure (`PORT_LYCHD`).
- It provides a comprehensive list (`HOST_LAYOUT`) of all files and directories
  the application owns on the host.

This module is the single source of truth for any component that needs to
interact with the host filesystem or network, such as the settings loader
or the rune baker.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from lychd.config.constants import BASE_DIR, DEFAULT_MODULE_NAME

# --- Core Network Blueprint (Internal Container Ports) ---
# The hardcoded ports the applications bind to INSIDE the container.
CONTAINER_LYCHD_PORT: Final[int] = 8000
CONTAINER_POSTGRES_PORT: Final[int] = 5432
CONTAINER_PHOENIX_UI_PORT: Final[int] = 6006
CONTAINER_PHOENIX_OTLP_PORT: Final[int] = 4317


# ==============================================================================
# I. THE PHYSICAL LAYER (XDG Standard Roots)
# ==============================================================================

_xdg_data = os.getenv("XDG_DATA_HOME")
_data_root = Path(_xdg_data) if _xdg_data else Path.home() / ".local" / "share"

_xdg_config = os.getenv("XDG_CONFIG_HOME")
_config_root = Path(_xdg_config) if _xdg_config else Path.home() / ".config"

_xdg_cache = os.getenv("XDG_CACHE_HOME")
_cache_root = Path(_xdg_cache) if _xdg_cache else Path.home() / ".cache"


# ==============================================================================
# II. THE LYCH ANATOMY (Host Paths)
# ==============================================================================
# By prefixing all Path constants with `PATH_`, typing `PATH_` in an IDE will
# provide an exhaustive list of all defined filesystem locations.

# --- A. The Codex (The Mind: Configuration) ---

PATH_CODEX_ROOT: Final[Path] = _config_root / DEFAULT_MODULE_NAME  # ~/.config/lychd
"""The Root of all configuration."""

PATH_LYCHD_TOML: Final[Path] = PATH_CODEX_ROOT / "lychd.toml"  # ~/.config/lychd/lychd.toml
"""The Prime Directive configuration file."""

PATH_RUNES_DIR: Final[Path] = PATH_CODEX_ROOT / "runes"  # ~/.config/lychd/runes
"""The Runic Manifest (Service definitions)."""

PATH_SOULSTONES_DIR: Final[Path] = PATH_RUNES_DIR / "soulstones"  # ~/.config/lychd/runes/soulstones
"""Local Soulstone definitions."""

PATH_PORTALS_DIR: Final[Path] = PATH_CODEX_ROOT / "portals"  # ~/.config/lychd/portals
"""Network Portal definitions."""


# --- B. The Crypt (The Body: Persistence) ---

PATH_CRYPT_ROOT: Final[Path] = _data_root / DEFAULT_MODULE_NAME  # ~/.local/share/lychd
"""The Root of persistent data."""

PATH_TRIGGERS_DIR: Final[Path] = PATH_CRYPT_ROOT / "triggers"  # ~/.local/share/lychd/triggers
"""The Nervous System. Host-watched folder for privilege escalation (ADR 10)."""

PATH_POSTGRES_DIR: Final[Path] = PATH_CRYPT_ROOT / "postgres"  # ~/.local/share/lychd/postgres
"""Live Database Storage."""

PATH_SNAPSHOTS_DIR: Final[Path] = PATH_CRYPT_ROOT / "snapshots"  # ~/.local/share/lychd/snapshots
"""Database Btrfs snapshots."""

PATH_LAB_DIR: Final[Path] = PATH_CRYPT_ROOT / "lab"  # ~/.local/share/lychd/lab
"""The Internal Workspace."""

PATH_EXTENSIONS_DIR: Final[Path] = PATH_CRYPT_ROOT / "extensions"  # ~/.local/share/lychd/extensions
"""Living Tissue (Third-party extensions)."""

PATH_CORE_DIR: Final[Path] = PATH_CRYPT_ROOT / "core"  # ~/.local/share/lychd/core
"""The LychD Source Mirror."""


# --- C. The Assembly (The Forge: Cache) ---

PATH_CACHE_ROOT: Final[Path] = _cache_root / DEFAULT_MODULE_NAME  # ~/.cache/lychd
"""The disposable cache root."""

PATH_ASSEMBLY_DIR: Final[Path] = PATH_CACHE_ROOT / "assembly"  # ~/.cache/lychd/assembly
"""The build area for transient assets."""


# --- D. The Binding (Host Integration) ---

PATH_SYSTEMD_UNITS_DIR: Final[Path] = _config_root / "containers" / "systemd"  # ~/.config/containers/systemd
"""The anchor where Quadlets are inscribed to interface with the Host OS."""

PATH_RUNE_TEMPLATES_DIR: Final[Path] = BASE_DIR / "system" / "templates"
"""Jinja2 source templates used to generate Systemd Quadlet files."""

# ==============================================================================
# III. HOST LAYOUT (The Physical Manifest)
# ==============================================================================
# A comprehensive list of all directories and key files the application owns.
# The `fmt: off/on` directives prevent auto-formatters like Black or Ruff
# from destroying the visual layout of the comments below.

# fmt: off
HOST_LAYOUT: Final[list[Path]] = [
    # --- The Mind ---
    PATH_CODEX_ROOT,           # ~/.config/lychd/
    PATH_LYCHD_TOML,           # ├── lychd.toml
    PATH_PORTALS_DIR,          # ├── portals/
    PATH_RUNES_DIR,            # └── runes/
    PATH_SOULSTONES_DIR,       #     └── soulstones/

    # --- The Binding ---
    PATH_SYSTEMD_UNITS_DIR,    # ~/.config/containers/systemd/ (The Anchor)

    # --- The Body ---
    PATH_CRYPT_ROOT,           # ~/.local/share/lychd/
    PATH_TRIGGERS_DIR,         # ├── triggers/        <-- The Signal (Nervous System)
    PATH_POSTGRES_DIR,         # ├── postgres/        <-- The Memory
    PATH_SNAPSHOTS_DIR,        # ├── snapshots/
    PATH_LAB_DIR,              # ├── lab/             <-- The Workspace
    PATH_EXTENSIONS_DIR,       # ├── extensions/      <-- The Tissue
    PATH_CORE_DIR,             # └── core/            <-- The Self

    # --- The Forge ---
    PATH_CACHE_ROOT,           # ~/.cache/lychd/
    PATH_ASSEMBLY_DIR,         # └── assembly/
]
# fmt: on

# ==============================================================================
# IV. CONTAINERS CONSTANTS
# ==============================================================================

# --- The Outlands (Container Mount Target) ---

PATH_CONTAINER_WORK: Final[Path] = Path.home() / "work"
"""The mount point inside the container for work files."""


# --- Volume Parsing Constants ---

MIN_VOLUME_PARTS: Final[int] = 2
"""Minimum number of parts in a volume string (host:container)."""

INDEX_HOST: Final[int] = 0
"""Index of the host path in a colon-separated volume string."""

INDEX_CONTAINER: Final[int] = 1
"""Index of the container path in a colon-separated volume string."""

INDEX_OPTIONS: Final[int] = 2
"""Index of the options string in a colon-separated volume string."""
