"""Small, pure path predicates shared by configuration and binding policy."""

from __future__ import annotations

from pathlib import Path


def paths_overlap(left: Path, right: Path) -> bool:
    """Return whether either normalized absolute path contains the other."""
    return left == right or left in right.parents or right in left.parents
