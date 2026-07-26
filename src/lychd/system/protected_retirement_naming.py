"""Private-name policy for protected-root authority recovery."""

from __future__ import annotations

from uuid import uuid4

_AUTHORITY_PREFIX = ".lychd-retire-authority-"
_UUID_HEX_LENGTH = 32


def is_protected_authority_name(name: str) -> bool:
    """Return whether one leaf carries the private authority-backup marker."""
    if not name.startswith(_AUTHORITY_PREFIX):
        return False
    suffix = name.removeprefix(_AUTHORITY_PREFIX)
    if len(suffix) != _UUID_HEX_LENGTH:
        return False
    try:
        int(suffix, 16)
    except ValueError:
        return False
    return True


def new_protected_authority_name() -> str:
    """Allocate one authority-backup leaf recognized by lifecycle recovery."""
    return f"{_AUTHORITY_PREFIX}{uuid4().hex}"


__all__ = (
    "is_protected_authority_name",
    "new_protected_authority_name",
)
