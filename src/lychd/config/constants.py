from __future__ import annotations

from pathlib import Path
from typing import Final

from litestar.utils.module_loader import module_to_os_path

DEFAULT_MODULE_NAME: Final[str] = "lychd"

BASE_DIR: Final[Path] = module_to_os_path(DEFAULT_MODULE_NAME)
"""Absolute path to the module root (src/lychd)."""

# --- Database Migrations ---
PATH_MIGRATION_DIR: Final[Path] = BASE_DIR / "db" / "migrations"
PATH_MIGRATION_CONFIG: Final[Path] = PATH_MIGRATION_DIR / "alembic.ini"
DB_MIGRATION_VERSION_TABLE: Final[str] = DEFAULT_MODULE_NAME + "_db_version"

# --- Static Svelte Altar ---
PATH_ALTAR_PUBLIC_DIR: Final[Path] = BASE_DIR / "public"
PATH_ALTAR_ASSET_DIR: Final[Path] = PATH_ALTAR_PUBLIC_DIR / "_app"
PATH_ALTAR_INDEX: Final[Path] = PATH_ALTAR_PUBLIC_DIR / "index.html"
PATH_ALTAR_LIGHTNING: Final[Path] = PATH_ALTAR_PUBLIC_DIR / "altar-lightning.svg"
PATH_ALTAR_NOTICES: Final[Path] = PATH_ALTAR_PUBLIC_DIR / "THIRD_PARTY_NOTICES.txt"

# APP SETTINGS

DB_SESSION_DEPENDENCY_KEY: Final[str] = "db_session"
DTO_INFO_KEY: Final[str] = "info"
DEFAULT_PAGINATION_SIZE: Final[int] = 20
CACHE_EXPIRATION: Final[int] = 60
HEALTH_ENDPOINT: Final[str] = "/health"
SITE_INDEX: Final[str] = "/"
OPENAPI_SCHEMA: Final[str] = "/schema"
ENCRYPTION_KEY_LENGTH: Final[int] = 32
