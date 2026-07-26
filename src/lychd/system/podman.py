"""Shared Podman and Quadlet compatibility law."""

from __future__ import annotations

import re
from typing import Final

MINIMUM_PODMAN_VERSION: Final[tuple[int, int]] = (5, 4)
_VERSION_PATTERN: Final = re.compile(r"\b(\d+)\.(\d+)(?:\.(\d+))?\b")

type PodmanVersion = tuple[int, int, int]


def parse_podman_version(value: str) -> PodmanVersion | None:
    """Return the first semantic Podman-style version in diagnostic text."""
    match = _VERSION_PATTERN.search(value)
    if match is None:
        return None
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch or 0))


def podman_version_supported(version: PodmanVersion) -> bool:
    """Return whether one parsed version satisfies LychD's Quadlet floor."""
    return version[:2] >= MINIMUM_PODMAN_VERSION


def format_podman_version(version: PodmanVersion) -> str:
    """Render one normalized three-component version."""
    return ".".join(str(part) for part in version)


def minimum_podman_version_text() -> str:
    """Render the compatibility floor for operator diagnostics."""
    return ".".join(str(part) for part in MINIMUM_PODMAN_VERSION)


__all__ = (
    "MINIMUM_PODMAN_VERSION",
    "PodmanVersion",
    "format_podman_version",
    "minimum_podman_version_text",
    "parse_podman_version",
    "podman_version_supported",
)
