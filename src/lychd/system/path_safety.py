"""Small path-shape checks shared by bootstrap and lifecycle boundaries."""

from __future__ import annotations

import os
from pathlib import Path


def filesystem_is_read_only(path: Path) -> bool:
    """Return positive kernel evidence that a mounted substrate is read-only."""
    try:
        return bool(os.statvfs(path).f_flag & os.ST_RDONLY)
    except OSError:
        return False


def path_has_symlink_component(path: Path) -> Path | None:
    """Return the first existing symlink component between root/home and ``path``."""
    home = Path.home()
    current = path
    candidates: list[Path] = []
    while current != current.parent:
        candidates.append(current)
        if current == home:
            break
        current = current.parent
    for candidate in reversed(candidates):
        if os.path.lexists(candidate) and candidate.is_symlink():
            return candidate
    return None


__all__ = (
    "filesystem_is_read_only",
    "path_has_symlink_component",
)
