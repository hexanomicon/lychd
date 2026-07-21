"""One bounded grammar for Podman secret source names."""

from __future__ import annotations

import re
from typing import Final

PODMAN_SECRET_NAME_PATTERN: Final[str] = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,126}$"  # noqa: S105 - grammar, not a credential
_PODMAN_SECRET_NAME: Final[re.Pattern[str]] = re.compile(PODMAN_SECRET_NAME_PATTERN)


def is_valid_podman_secret_name(value: str) -> bool:
    """Return whether ``value`` is one option-free Podman secret basename."""
    return _PODMAN_SECRET_NAME.fullmatch(value) is not None


def validate_podman_secret_name(value: str, *, field_name: str = "Podman secret name") -> str:
    """Return one safe secret basename or fail before path/spec composition."""
    if not is_valid_podman_secret_name(value):
        msg = f"{field_name} must be one option-free Podman secret name"
        raise ValueError(msg)
    return value


__all__ = [
    "PODMAN_SECRET_NAME_PATTERN",
    "is_valid_podman_secret_name",
    "validate_podman_secret_name",
]
