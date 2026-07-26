"""Descriptor-relative observations for protected-root retirement."""

from __future__ import annotations

import os

from lychd.system.atomic_retirement import RetirementIdentity


def observe_retirement_name(
    *,
    parent_fd: int,
    name: str,
) -> RetirementIdentity | None:
    """Observe one descriptor-relative name without following it."""
    try:
        metadata = os.stat(
            name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None
    return RetirementIdentity.from_stat(metadata)


__all__ = ("observe_retirement_name",)
