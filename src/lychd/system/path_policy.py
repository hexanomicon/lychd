"""Path predicates for configuration spelling and live filesystem identity."""

from __future__ import annotations

import os
from pathlib import Path


def paths_overlap(left: Path, right: Path) -> bool:
    """Return whether either normalized absolute path contains the other."""
    return left == right or left in right.parents or right in left.parents


def physically_contains(parent: Path, child: Path) -> bool:
    """Check parent identity across existing ancestry, including case-folded filesystem aliases."""
    try:
        identity = parent.stat()
    except FileNotFoundError:
        return False
    for ancestor in (child, *child.parents):
        try:
            if os.path.samestat(identity, ancestor.stat()):
                return True
        except FileNotFoundError:
            continue
    return False
