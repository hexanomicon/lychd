"""Typed access to lifecycle path authority exposed by the public facade.

The public package intentionally re-exports the path constants used by the
former single-module implementation. Tests and operators may patch those
attributes to construct an isolated XDG topology; internal modules therefore
read one immutable snapshot from the facade at operation boundaries.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from lychd.system import constants

_FACADE_MODULE = "lychd.system.services.lifecycle"


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
    """Read one consistent authority snapshot from the public package facade."""
    facade = sys.modules.get(_FACADE_MODULE)

    def path(name: str, fallback: Path) -> Path:
        value = getattr(facade, name, fallback) if facade is not None else fallback
        if not isinstance(value, Path):
            msg = f"Lifecycle authority {name} must be a pathlib.Path."
            raise TypeError(msg)
        return value

    raw_layout: object = (
        getattr(facade, "HOST_LAYOUT", constants.HOST_LAYOUT)
        if facade is not None
        else constants.HOST_LAYOUT
    )
    if not isinstance(raw_layout, tuple):
        msg = "Lifecycle authority HOST_LAYOUT must be a tuple of pathlib.Path values."
        raise TypeError(msg)
    object_layout = cast("tuple[object, ...]", raw_layout)
    if not all(isinstance(item, Path) for item in object_layout):
        msg = "Lifecycle authority HOST_LAYOUT must be a tuple of pathlib.Path values."
        raise TypeError(msg)
    host_layout = cast("tuple[Path, ...]", object_layout)

    return LifecycleAuthority(
        host_layout=host_layout,
        cache_root=path("PATH_CACHE_ROOT", constants.PATH_CACHE_ROOT),
        codex_root=path("PATH_CODEX_ROOT", constants.PATH_CODEX_ROOT),
        crypt_root=path("PATH_CRYPT_ROOT", constants.PATH_CRYPT_ROOT),
        lifecycle_receipt=path("PATH_LIFECYCLE_RECEIPT", constants.PATH_LIFECYCLE_RECEIPT),
        lychd_toml=path("PATH_LYCHD_TOML", constants.PATH_LYCHD_TOML),
        postgres_root=path("PATH_POSTGRES_ROOT_DIR", constants.PATH_POSTGRES_ROOT_DIR),
        postgres_data=path("PATH_POSTGRESS_DATA_DIR", constants.PATH_POSTGRESS_DATA_DIR),
        postgres_snapshots=path(
            "PATH_POSTGRESS_SNAPSHOTS_DIR",
            constants.PATH_POSTGRESS_SNAPSHOTS_DIR,
        ),
        runes=path("PATH_RUNES_DIR", constants.PATH_RUNES_DIR),
        systemd_units=path("PATH_SYSTEMD_UNITS_DIR", constants.PATH_SYSTEMD_UNITS_DIR),
        systemd_user_units=path(
            "PATH_SYSTEMD_USER_UNITS_DIR",
            constants.PATH_SYSTEMD_USER_UNITS_DIR,
        ),
    )
