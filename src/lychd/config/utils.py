from __future__ import annotations

import os
import stat
from pathlib import Path


def read_secret_from_env_or_file(
    *,
    value_env_keys: tuple[str, ...],
    file_env_keys: tuple[str, ...],
    default_file: Path,
    secret_label: str,
) -> str:
    """Resolve a secret from explicit environment overrides or a mounted secret file.

    This prioritizes explicit environment variable values over file paths, and falls
    back to the specified default secret file if none are provided.
    """
    for env_key in value_env_keys:
        value = os.environ.get(env_key)
        if value:
            return value

    secret_path_raw = next((os.environ.get(env_key) for env_key in file_env_keys if os.environ.get(env_key)), None)
    secret_path = Path(secret_path_raw) if secret_path_raw else default_file

    try:
        value = secret_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        msg = (
            f"Required secret '{secret_label}' is unavailable. "
            f"Set one of {value_env_keys} or mount secret file at '{secret_path}'."
        )
        raise ValueError(msg) from exc

    if not value:
        msg = f"Secret file '{secret_path}' for '{secret_label}' is empty."
        raise ValueError(msg)

    return value


def _first_non_empty_env(key_names: tuple[str, ...]) -> str | None:
    for key in key_names:
        value = os.environ.get(key)
        if value:
            return value
    return None


def _secret_file_has_content(path: Path) -> bool:
    try:
        return bool(path.read_text(encoding="utf-8").strip())
    except OSError:
        return False


def needs_generated_secret_fallback(
    *,
    value_env_keys: tuple[str, ...],
    file_env_keys: tuple[str, ...],
    default_file: Path,
) -> bool:
    """Determine if a runtime-generated fallback is needed for a missing secret.

    Returns True when neither environment values nor file contents exist to satisfy
    the requirement. This is typically used to safely boot environments like testing
    without needing explicit secret configuration.
    """
    if _first_non_empty_env(value_env_keys) is not None:
        return False

    explicit_file_path = _first_non_empty_env(file_env_keys)
    if explicit_file_path is not None:
        return False

    return not _secret_file_has_content(default_file)


def codex_permission_issues(path: Path, *, expected_mode: int = 0o600) -> dict[str, str]:
    """Return codex permission or ownership policy violations for a file.

    This ensures configuration files maintain strict permissions,
    preventing unintended access or modification.

    Policy requirements:
    - Group and other permission bits must be closed (`0600` or stricter).
    - File should be owned by the current user.
    """
    try:
        metadata = path.stat()
    except OSError:
        return {}

    issues: dict[str, str] = {}
    mode = stat.S_IMODE(metadata.st_mode)
    if mode & 0o077:
        issues["mode"] = oct(mode)
        issues["expected_max_mode"] = oct(expected_mode)

    if hasattr(os, "getuid"):
        current_uid = os.getuid()
        if metadata.st_uid != current_uid:
            issues["owner_uid"] = str(metadata.st_uid)
            issues["expected_uid"] = str(current_uid)

    return issues
