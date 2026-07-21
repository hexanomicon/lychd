"""Secret-file contract shared by TabbyAPI and LychD's authenticated clients."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TypeGuard, cast

from lychd.system.secret_names import PODMAN_SECRET_NAME_PATTERN, is_valid_podman_secret_name

TABBY_AUTH_SECRET_NAME_PATTERN = PODMAN_SECRET_NAME_PATTERN
_MIN_KEY_LENGTH = 32


class TabbyAPIAuthSecretError(RuntimeError):
    """The mounted TabbyAPI auth document is missing or malformed."""


@dataclass(frozen=True, slots=True, repr=False)
class TabbyAPIAuthKeys:
    """Validated API/admin keys from TabbyAPI's JSON-as-YAML auth document."""

    api_key: str
    admin_key: str


def load_tabbyapi_auth_keys(secret_name: str) -> TabbyAPIAuthKeys:
    """Load one Podman secret that TabbyAPI also reads as ``api_tokens.yml``.

    JSON is deliberately required: it is valid YAML for TabbyAPI while the Vessel
    can validate it with the Python standard library and no second parser stack.
    """
    if not is_valid_tabby_auth_secret_name(secret_name):
        msg = "TabbyAPI auth secret name must be one Podman secret basename."
        raise TabbyAPIAuthSecretError(msg)

    root = Path(os.environ.get("LYCHD_SECRET_ROOT", "/run/secrets"))
    path = root / secret_name
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        msg = f"TabbyAPI auth secret '{secret_name}' is unavailable at its mounted secret path."
        raise TabbyAPIAuthSecretError(msg) from exc

    try:
        parsed: object = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        msg = f"TabbyAPI auth secret '{secret_name}' must contain a JSON object."
        raise TabbyAPIAuthSecretError(msg) from exc
    except ValueError as exc:
        msg = f"TabbyAPI auth secret '{secret_name}' is invalid: {exc}"
        raise TabbyAPIAuthSecretError(msg) from exc
    if not isinstance(parsed, dict):
        msg = f"TabbyAPI auth secret '{secret_name}' must contain a JSON object."
        raise TabbyAPIAuthSecretError(msg)

    payload = cast("dict[object, object]", parsed)
    admin_key = payload.get("admin_key")
    api_keys = _validated_api_keys(payload.get("api_key"))
    if not _valid_key(admin_key):
        msg = f"TabbyAPI auth secret '{secret_name}' has no valid admin_key."
        raise TabbyAPIAuthSecretError(msg)
    if api_keys is None:
        msg = f"TabbyAPI auth secret '{secret_name}' has no valid api_key."
        raise TabbyAPIAuthSecretError(msg)
    api_key = api_keys[0]
    if admin_key in api_keys:
        msg = f"TabbyAPI auth secret '{secret_name}' must use distinct API and admin keys."
        raise TabbyAPIAuthSecretError(msg)
    return TabbyAPIAuthKeys(api_key=api_key, admin_key=admin_key)


def is_valid_tabby_auth_secret_name(secret_name: str) -> bool:
    """Return whether a name is safe as the source segment of ``Secret=``."""
    return is_valid_podman_secret_name(secret_name)


def _validated_api_keys(value: object) -> list[str] | None:
    if isinstance(value, str):
        return [value] if _valid_key(value) else None
    if isinstance(value, list):
        candidates = cast("list[object]", value)
        if candidates and all(_valid_key(candidate) for candidate in candidates):
            return cast("list[str]", candidates)
    return None


def _valid_key(value: object) -> TypeGuard[str]:
    return (
        isinstance(value, str)
        and len(value) >= _MIN_KEY_LENGTH
        and value.isascii()
        and all("!" <= char <= "~" for char in value)
    )


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = f"Duplicate JSON key '{key}' is not allowed in a TabbyAPI auth secret."
            raise ValueError(msg)
        result[key] = value
    return result


__all__ = [
    "TABBY_AUTH_SECRET_NAME_PATTERN",
    "TabbyAPIAuthKeys",
    "TabbyAPIAuthSecretError",
    "is_valid_tabby_auth_secret_name",
    "load_tabbyapi_auth_keys",
]
