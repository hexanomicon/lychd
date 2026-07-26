"""Filename laws and runtime-name derivation for Scribe-owned units."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from lychd.system.services.scribe.errors import ScribeOwnershipError

QUADLET_SUFFIXES: frozenset[str] = frozenset({".container", ".pod", ".volume", ".network", ".kube", ".image", ".build"})
GENERATED_SYSTEMD_SUFFIXES: frozenset[str] = frozenset({".target"})
PLAIN_SYSTEMD_SUFFIXES: frozenset[str] = frozenset({".path", ".service"})
SYSTEMD_SUFFIXES = GENERATED_SYSTEMD_SUFFIXES | PLAIN_SYSTEMD_SUFFIXES

_SAFE_STEM = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.@-]*\Z")

type BindingSiteKind = Literal["quadlet", "systemd"]


def validate_owned_filename(
    filename: str,
    *,
    suffixes: frozenset[str],
    site: BindingSiteKind,
) -> None:
    """Reject traversal, foreign namespaces, and unsupported unit kinds."""
    path = Path(filename)
    if (
        not filename
        or path.is_absolute()
        or path.name != filename
        or "/" in filename
        or "\\" in filename
        or "\x00" in filename
    ):
        msg = f"Unsafe {site} ownership entry: {filename!r}."
        raise ValueError(msg)

    suffix = path.suffix
    stem = filename[: -len(suffix)] if suffix else filename
    if suffix not in suffixes or not _SAFE_STEM.fullmatch(stem) or ".." in stem:
        msg = f"Invalid LychD {site} unit filename: {filename!r}."
        raise ValueError(msg)

    if site == "quadlet":
        namespaced = stem == "lychd" or (stem.startswith("lychd-") and len(stem) > len("lychd-"))
    else:
        namespaced = stem.startswith("lychd-") and len(stem) > len("lychd-")
    if not namespaced:
        msg = f"Unit filename is outside the LychD namespace: {filename!r}."
        raise ValueError(msg)


def encode_plain_units(plain_units: Mapping[str, str]) -> dict[str, bytes]:
    """Validate and encode plain user units for the transaction boundary."""
    encoded: dict[str, bytes] = {}
    for filename, content in plain_units.items():
        validate_owned_filename(filename, suffixes=PLAIN_SYSTEMD_SUFFIXES, site="systemd")
        if "\x00" in content:
            msg = f"Systemd unit content cannot contain NUL bytes: {filename}."
            raise ValueError(msg)
        encoded[filename] = content.encode("utf-8")
    return encoded


def runtime_unit_for_source(filename: str) -> str:
    """Map one supported source filename to its generated runtime unit."""
    path = Path(filename)
    suffix = path.suffix
    stem = path.stem
    if suffix == ".container":
        return f"{stem}.service"
    if suffix == ".pod":
        return f"{stem}-pod.service"
    if suffix in {".target", ".service", ".path"}:
        return filename
    msg = f"Cannot derive a runtime unit for owned source: {filename}"
    raise ScribeOwnershipError(msg)
