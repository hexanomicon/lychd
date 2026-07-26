"""One authority law for shared Quadlet and systemd binding sites."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from lychd.system.constants import (
    PATH_SYSTEMD_UNITS_DIR,
    PATH_SYSTEMD_USER_UNITS_DIR,
)
from lychd.system.path_safety import (
    filesystem_is_read_only,
    path_has_symlink_component,
)

PRIVATE_BINDING_SITE_MODE = 0o700


@dataclass(frozen=True, slots=True)
class BindingSites:
    """Exact shared directories used by one binding generation."""

    quadlet: Path
    systemd_user: Path

    @property
    def paths(self) -> tuple[Path, Path]:
        """Return both sites in stable generation order."""
        return (self.quadlet, self.systemd_user)


DEFAULT_BINDING_SITES = BindingSites(
    quadlet=PATH_SYSTEMD_UNITS_DIR,
    systemd_user=PATH_SYSTEMD_USER_UNITS_DIR,
)


@dataclass(frozen=True, slots=True)
class AttestedBindingSite:
    """One prepared binding directory's immutable kernel identity."""

    path: Path
    device: int
    inode: int

    def __post_init__(self) -> None:
        """Reject incomplete evidence before it can become binding authority."""
        if not self.path.is_absolute() or self.device < 0 or self.inode <= 0:
            message = f"Binding-site identity is incomplete: {self.path}"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class AttestedBindingSites:
    """Both shared binding sites refined into exact effect capabilities."""

    quadlet: AttestedBindingSite
    systemd_user: AttestedBindingSite

    @property
    def paths(self) -> BindingSites:
        """Project exact identities into the paths used by renderers and adapters."""
        return BindingSites(
            quadlet=self.quadlet.path,
            systemd_user=self.systemd_user.path,
        )

    @property
    def identities(self) -> tuple[AttestedBindingSite, AttestedBindingSite]:
        """Return both identities in stable binding-generation order."""
        return (self.quadlet, self.systemd_user)


class BindingSiteState(StrEnum):
    """A binding directory's exact relationship to initialization."""

    PREPARED = "prepared"
    CREATABLE = "creatable"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class BindingSiteInspection:
    """Typed evidence consumed by readiness and Scribe enforcement."""

    path: Path
    state: BindingSiteState
    detail: str
    identity: AttestedBindingSite | None = None

    @property
    def prepared(self) -> bool:
        """Return whether authority-bearing writes may use this site now."""
        return self.state is BindingSiteState.PREPARED


def inspect_binding_site(
    path: Path,
    *,
    current_uid: int,
) -> BindingSiteInspection:
    """Inspect one shared site without creating it or granting tree ownership."""
    if symlink := path_has_symlink_component(path):
        return _blocked(path, f"symlink component is not trusted: {symlink}")
    if os.path.lexists(path):
        return _inspect_existing_site(path, current_uid=current_uid)
    return _inspect_creatable_site(path, current_uid=current_uid)


def _inspect_existing_site(
    path: Path,
    *,
    current_uid: int,
) -> BindingSiteInspection:
    """Validate one present binding directory and its ancestor chain."""
    try:
        metadata = path.lstat()
    except OSError as exc:
        return _blocked(path, f"cannot inspect target: {_brief(exc)}")
    if problem := _existing_site_problem(
        path,
        metadata=metadata,
        current_uid=current_uid,
    ):
        return _blocked(path, problem)
    unsafe_ancestor = _unsafe_writable_ancestor(
        path.parent,
        current_uid=current_uid,
    )
    if unsafe_ancestor is not None:
        return _blocked(
            path,
            f"writable ancestor is not trusted: {unsafe_ancestor}",
        )
    return BindingSiteInspection(
        path=path,
        state=BindingSiteState.PREPARED,
        detail="prepared",
        identity=AttestedBindingSite(
            path=path,
            device=metadata.st_dev,
            inode=metadata.st_ino,
        ),
    )


def _existing_site_problem(
    path: Path,
    *,
    metadata: os.stat_result,
    current_uid: int,
) -> str | None:
    """Return the first local target violation, excluding ancestor policy."""
    if not stat.S_ISDIR(metadata.st_mode):
        return "target exists but is not a directory"
    if metadata.st_uid != current_uid:
        return f"owned by uid {metadata.st_uid}, expected {current_uid}"
    mode = stat.S_IMODE(metadata.st_mode)
    if mode & (stat.S_IWGRP | stat.S_IWOTH):
        return f"mode {mode:04o} permits another principal to alter bindings"
    owner_has_rwx = mode & stat.S_IRWXU == stat.S_IRWXU
    if not owner_has_rwx or not os.access(path, os.R_OK | os.W_OK | os.X_OK):
        return "present but not readable, writable, and searchable"
    return None


def _inspect_creatable_site(
    path: Path,
    *,
    current_uid: int,
) -> BindingSiteInspection:
    """Validate the nearest parent from which init may create the site."""
    parent = _nearest_existing(path.parent)
    try:
        metadata = parent.stat()
    except OSError as exc:
        return _blocked(path, f"cannot inspect creation parent: {_brief(exc)}")
    if not stat.S_ISDIR(metadata.st_mode):
        return _blocked(path, f"creation parent is not a directory: {parent}")
    if not os.access(parent, os.W_OK | os.X_OK):
        return _blocked(
            path,
            f"creation parent is not writable and searchable: {parent}",
        )
    unsafe_ancestor = _unsafe_writable_ancestor(
        parent,
        current_uid=current_uid,
    )
    if unsafe_ancestor is not None:
        return _blocked(
            path,
            f"writable ancestor is not trusted: {unsafe_ancestor}",
        )
    return BindingSiteInspection(
        path=path,
        state=BindingSiteState.CREATABLE,
        detail="will create shared directory",
    )


def _unsafe_writable_ancestor(
    start: Path,
    *,
    current_uid: int,
) -> Path | None:
    """Return an ancestor mutable by other users without sticky protection."""
    candidate = start
    while True:
        try:
            metadata = candidate.lstat()
        except OSError:
            return candidate
        mode = stat.S_IMODE(metadata.st_mode)
        owner_is_authority = metadata.st_uid in {0, current_uid}
        if not owner_is_authority and not filesystem_is_read_only(candidate):
            return candidate
        writable_by_others = bool(mode & (stat.S_IWGRP | stat.S_IWOTH))
        sticky_protected = bool(mode & stat.S_ISVTX) and metadata.st_uid in {
            0,
            current_uid,
        }
        if writable_by_others and not sticky_protected:
            return candidate
        if candidate == candidate.parent:
            return None
        candidate = candidate.parent


def _nearest_existing(path: Path) -> Path:
    candidate = path
    while not os.path.lexists(candidate) and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def _blocked(path: Path, detail: str) -> BindingSiteInspection:
    return BindingSiteInspection(
        path=path,
        state=BindingSiteState.BLOCKED,
        detail=detail,
    )


def _brief(exc: OSError) -> str:
    return " ".join(str(exc).split())[:240]


__all__ = (
    "DEFAULT_BINDING_SITES",
    "PRIVATE_BINDING_SITE_MODE",
    "AttestedBindingSite",
    "AttestedBindingSites",
    "BindingSiteInspection",
    "BindingSiteState",
    "BindingSites",
    "inspect_binding_site",
)
