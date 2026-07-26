"""Private evidence records shared by directory provisioning layers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from lychd.system.services.lifecycle.models import CreatedDirectory


@dataclass(frozen=True, slots=True)
class CreatedDirectoryEntry:
    """One exact creation plus rollback authority pinned to its parent."""

    resource: CreatedDirectory
    parent_fd: int
    name: str
    published: bool


@dataclass(frozen=True, slots=True)
class OpenedDirectory:
    """One safely opened path component and its creation disposition."""

    descriptor: int
    metadata: os.stat_result
    creation: CreatedDirectoryEntry | None
    raced: bool


@dataclass(frozen=True, slots=True)
class ObservedDirectory:
    """One final path identity observed by a provisioning transaction."""

    path: Path
    device: int
    inode: int


@dataclass(frozen=True, slots=True)
class QuarantinedName:
    """One quarantine name plus a signal observed after its rename effect."""

    name: str
    interruption: BaseException | None = None


__all__ = (
    "CreatedDirectoryEntry",
    "ObservedDirectory",
    "OpenedDirectory",
    "QuarantinedName",
)
