"""Typed snapshots of the canonical lifecycle path authority."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lychd.system import constants


@dataclass(frozen=True)
class LifecycleAuthority:
    """One typed snapshot of every path involved in lifecycle decisions."""

    host_layout: tuple[Path, ...]
    cache_root: Path
    codex_root: Path
    crypt_root: Path
    lifecycle_receipt: Path
    lychd_toml: Path
    postgres_root: Path
    postgres_data: Path
    postgres_snapshots: Path
    runes: Path
    systemd_units: Path
    systemd_user_units: Path


def current_authority() -> LifecycleAuthority:
    """Read one consistent snapshot from the sole constants owner."""
    return LifecycleAuthority(
        host_layout=constants.HOST_LAYOUT,
        cache_root=constants.PATH_CACHE_ROOT,
        codex_root=constants.PATH_CODEX_ROOT,
        crypt_root=constants.PATH_CRYPT_ROOT,
        lifecycle_receipt=constants.PATH_LIFECYCLE_RECEIPT,
        lychd_toml=constants.PATH_LYCHD_TOML,
        postgres_root=constants.PATH_POSTGRES_ROOT_DIR,
        postgres_data=constants.PATH_POSTGRESS_DATA_DIR,
        postgres_snapshots=constants.PATH_POSTGRESS_SNAPSHOTS_DIR,
        runes=constants.PATH_RUNES_DIR,
        systemd_units=constants.PATH_SYSTEMD_UNITS_DIR,
        systemd_user_units=constants.PATH_SYSTEMD_USER_UNITS_DIR,
    )
