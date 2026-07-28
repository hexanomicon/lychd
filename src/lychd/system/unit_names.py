"""Canonical names for generated Animator and Coven systemd units."""

from __future__ import annotations

__all__ = [
    "animator_service_stem",
    "animator_service_unit",
    "animator_target_unit",
    "coven_target_unit",
]


def animator_service_stem(animator_name: str) -> str:
    """Return the Quadlet container/service stem for one Animator."""
    return f"lychd-{animator_name}"


def animator_service_unit(animator_name: str) -> str:
    """Return the generated Quadlet service unit for one Animator."""
    return f"{animator_service_stem(animator_name)}.service"


def animator_target_unit(animator_name: str) -> str:
    """Return the generated lifecycle-gate target for one Animator."""
    return f"lychd-animator-{animator_name}.target"


def coven_target_unit(coven_name: str) -> str:
    """Return the generated operator aggregate target for one Coven."""
    return f"lychd-coven-{coven_name}.target"
