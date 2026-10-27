"""Explicit operator files; no ambient settings, credentials or application boot."""

from __future__ import annotations

import json
import os
import re
import stat
import tomllib
from pathlib import Path

from lychd.interface.discord.schemas import DiscordPolicy

MAX_POLICY_BYTES = 65_536
MAX_TOKEN_BYTES = 512


def load_policy(path: Path) -> DiscordPolicy:
    """Read a bounded non-secret TOML policy selected by the operator."""
    with path.open("rb") as source:
        raw = source.read(MAX_POLICY_BYTES + 1)
    if len(raw) > MAX_POLICY_BYTES:
        msg = "policy_too_large"
        raise ValueError(msg)
    return DiscordPolicy.model_validate_json(json.dumps(tomllib.loads(raw.decode("utf-8"))))


def read_token(path: Path) -> str:
    """Read one owner-only regular credential file without following symlinks."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
            msg = "credential_permissions"
            raise ValueError(msg)
        raw = source.read(MAX_TOKEN_BYTES + 1)
    token = raw.decode("ascii").strip()
    if len(raw) > MAX_TOKEN_BYTES or re.fullmatch(r"[A-Za-z0-9_.-]{20,512}", token) is None:
        msg = "credential_shape"
        raise ValueError(msg)
    return token
