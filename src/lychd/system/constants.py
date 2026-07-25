"""Canonical host addresses and internal container ports.

``HOST_LAYOUT`` describes initialization geography. It deliberately includes
shared XDG and Binding anchors plus persistent storage, so membership never
grants ownership or deletion authority.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from lychd.config.constants import BASE_DIR, DEFAULT_MODULE_NAME

# --- Core Network Blueprint (Internal Container Ports) ---
# The hardcoded ports the applications bind to INSIDE the container.
# Phoenix container ports are extension-private now: see
# extensions/builtin/observability/phoenix/config.py.
CONTAINER_LYCHD_PORT: Final[int] = 8000
CONTAINER_POSTGRES_PORT: Final[int] = 5432

# ==============================================================================
# I. THE PHYSICAL LAYER (XDG Standard Roots)
# ==============================================================================

_xdg_data = os.getenv("XDG_DATA_HOME")
PATH_XDG_DATA_HOME: Final[Path] = Path(_xdg_data) if _xdg_data else Path.home() / ".local" / "share"
"""Shared XDG root for the Crypt.

This shared parent is an anchor, never recursive LychD deletion authority.
"""

_xdg_config = os.getenv("XDG_CONFIG_HOME")
PATH_XDG_CONFIG_HOME: Final[Path] = Path(_xdg_config) if _xdg_config else Path.home() / ".config"
"""Shared XDG root for the Codex and Binding.

This shared parent is an anchor, never recursive LychD deletion authority.
"""

_xdg_cache = os.getenv("XDG_CACHE_HOME")
PATH_XDG_CACHE_HOME: Final[Path] = Path(_xdg_cache) if _xdg_cache else Path.home() / ".cache"
"""Shared XDG root for the Forge.

This shared parent is an anchor, never recursive LychD deletion authority.
"""


# ==============================================================================
# II. THE LYCH ANATOMY (Host Paths)
# ==============================================================================
# By prefixing all Path constants with `PATH_`, typing `PATH_` in an IDE will
# provide an exhaustive list of all defined filesystem locations.

# --- A. The Codex (The Mind: Configuration) ---

PATH_CODEX_ROOT: Final[Path] = PATH_XDG_CONFIG_HOME / DEFAULT_MODULE_NAME  # ~/.config/lychd
"""LychD settings and typed Runes."""

PATH_LYCHD_TOML: Final[Path] = PATH_CODEX_ROOT / "lychd.toml"  # ~/.config/lychd/lychd.toml
"""Primary settings loaded before Rune documents."""

PATH_LIFECYCLE_RECEIPT: Final[Path] = PATH_CODEX_ROOT / ".lychd-lifecycle.json"
"""Receipt governing later ``lychd del`` authority."""

PATH_RUNES_DIR: Final[Path] = PATH_CODEX_ROOT / "runes"  # ~/.config/lychd/runes
"""Typed TOML intent and inactive examples."""

PATH_ANIMATOR_DIR: Final[Path] = PATH_RUNES_DIR / "animator"  # ~/.config/lychd/runes/animator
"""Local and remote capability endpoints."""

PATH_SOULSTONES_DIR: Final[Path] = PATH_ANIMATOR_DIR / "soulstones"  # ~/.config/lychd/runes/animator/soulstones
"""Local container-backed capability runtimes."""

PATH_PORTALS_DIR: Final[Path] = PATH_ANIMATOR_DIR / "portals"  # ~/.config/lychd/runes/animator/portals
"""Remote capability endpoints."""


# --- B. The Crypt (The Body: Persistence) ---

PATH_CRYPT_ROOT: Final[Path] = PATH_XDG_DATA_HOME / DEFAULT_MODULE_NAME  # ~/.local/share/lychd
"""Persistent LychD data and workspaces."""

PATH_TRIGGERS_DIR: Final[Path] = PATH_CRYPT_ROOT / "triggers"  # ~/.local/share/lychd/triggers
"""Vessel-to-host Reactor exchange."""

PATH_REACTOR_INBOX_DIR: Final[Path] = PATH_TRIGGERS_DIR / "inbox"
"""Owner-only Host Reactor intent queue."""

PATH_REACTOR_JOURNAL_DIR: Final[Path] = PATH_TRIGGERS_DIR / "journal"
"""Host Reactor outcomes exposed read-only to the Vessel."""

PATH_POSTGRES_ROOT_DIR: Final[Path] = PATH_CRYPT_ROOT / "postgres"  # ~/.local/share/lychd/postgres
"""PostgreSQL bootstrap and live Phylactery storage."""

PATH_POSTGRES_INIT_SCRIPT: Final[Path] = PATH_POSTGRES_ROOT_DIR / "init_db.sh"
"""PostgreSQL bootstrap enabling pgvector and the current Phoenix compatibility database."""

PATH_POSTGRESS_DATA_DIR: Final[Path] = PATH_POSTGRES_ROOT_DIR / "data"
"""Live PostgreSQL data within the Phylactery."""

PATH_POSTGRESS_SNAPSHOTS_DIR: Final[Path] = PATH_CRYPT_ROOT / "snapshots"  # ~/.local/share/lychd/snapshots
"""Reserved recovery-snapshot shelf."""

PATH_LAB_DIR: Final[Path] = PATH_CRYPT_ROOT / "lab"  # ~/.local/share/lychd/lab
"""Operator workspace mounted read-write."""

PATH_EXTENSIONS_DIR: Final[Path] = PATH_CRYPT_ROOT / "extensions"  # ~/.local/share/lychd/extensions
"""Selected private extension source."""

PATH_CORE_DIR: Final[Path] = PATH_CRYPT_ROOT / "core"  # ~/.local/share/lychd/core
"""Reserved read-only core source."""


# --- C. The Assembly (The Forge: Cache) ---

PATH_CACHE_ROOT: Final[Path] = PATH_XDG_CACHE_HOME / DEFAULT_MODULE_NAME  # ~/.cache/lychd
"""Rebuildable LychD cache."""

PATH_ASSEMBLY_DIR: Final[Path] = PATH_CACHE_ROOT / "assembly"  # ~/.cache/lychd/assembly
"""Reserved disposable assembly staging."""


# --- D. The Binding (Host Integration) ---

PATH_CONTAINERS_CONFIG_DIR: Final[Path] = PATH_XDG_CONFIG_HOME / "containers"
"""Shared Podman configuration root; LychD only ensures the path to its Quadlet directory exists."""

PATH_SYSTEMD_UNITS_DIR: Final[Path] = PATH_CONTAINERS_CONFIG_DIR / "systemd"  # ~/.config/containers/systemd
"""Shared Quadlet source site.

Binding writes only Scribe-owned LychD sources here. Quadlet's generator
processes ``.container/.volume/.network/.kube/.image/
.build/.pod`` files here. Plain systemd units (e.g. ``.target``) dropped in this
directory are silently ignored, so they must live in ``PATH_SYSTEMD_USER_UNITS_DIR``.
"""

PATH_SYSTEMD_CONFIG_DIR: Final[Path] = PATH_XDG_CONFIG_HOME / "systemd"
"""Shared systemd user-configuration root; never a LychD-owned tree."""

PATH_SYSTEMD_USER_UNITS_DIR: Final[Path] = PATH_SYSTEMD_CONFIG_DIR / "user"  # ~/.config/systemd/user
"""Shared plain user-unit site.

LychD owns only Scribe-recorded non-Quadlet units here. The Coven ``.target``
files live here so systemd can load them and resolve the
``WantedBy=``/``Conflicts=`` edges that reference them (the Law of Exclusivity)."""

PATH_RUNE_TEMPLATES_DIR: Final[Path] = BASE_DIR / "system" / "templates"
"""Jinja2 templates for generated Quadlets, units, and database bootstrap."""

# ==============================================================================
# III. HOST LAYOUT (The Physical Manifest)
# ==============================================================================
# Required initialization geography. This includes shared host anchors and a
# mounted storage target, so membership never proves deletion ownership.
# The `fmt: off/on` directives prevent auto-formatters like Black or Ruff
# from destroying the visual layout of the comments below.

# fmt: off
HOST_LAYOUT: Final[tuple[Path,...]] = (
    # --- The Mind ---
    PATH_CODEX_ROOT,           # ~/.config/lychd/
    # PATH_LYCHD_TOML,           |         # ── lychd.toml - DIRS ONLY this is handled by CODEX
    PATH_RUNES_DIR,            # └── runes/
    PATH_ANIMATOR_DIR,         #     └── animator/
    PATH_SOULSTONES_DIR,       #         ├── soulstones/
    PATH_PORTALS_DIR,          #         └── portals/

    # --- The Binding ---
    PATH_SYSTEMD_UNITS_DIR,    # ~/.config/containers/systemd/ (The Anchor)
    PATH_SYSTEMD_USER_UNITS_DIR, # ~/.config/systemd/user/ (Coven .target units)

    # --- The Body ---
    PATH_CRYPT_ROOT,           # ~/.local/share/lychd/
    PATH_TRIGGERS_DIR,         # ├── triggers/        <-- The Signal (Nervous System)
    PATH_LAB_DIR,              # ├── lab/             <-- The Workspace
    PATH_EXTENSIONS_DIR,       # ├── extensions/      <-- The Tissue
    PATH_CORE_DIR,             # ├── core/            <-- The lychd source dir
    PATH_POSTGRES_ROOT_DIR,    # ├── postgres/        <-- The Memory
    PATH_POSTGRESS_DATA_DIR,   # │   └── data/        <-- Live DB Data
    PATH_POSTGRESS_SNAPSHOTS_DIR, # └── snapshots/    <-- Future recovery shelf

    # --- The Forge ---
    PATH_CACHE_ROOT,           # ~/.cache/lychd/
    PATH_ASSEMBLY_DIR,         # └── assembly/
)
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
