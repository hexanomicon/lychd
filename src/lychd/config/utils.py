from __future__ import annotations

import os
from pathlib import Path


def read_secret_from_env_or_file(
    *,
    value_env_keys: tuple[str, ...],
    file_env_keys: tuple[str, ...],
    default_file: Path,
    secret_label: str,
) -> str:
    """Resolve a secret from explicit environment overrides or a mounted secret file.

    A direct value environment variable is an explicit local/test override, kept for
    the ADR 12 contract and never emitted by LychD's generated Quadlets. Production
    deployments should supply only a ``*_FILE`` path to a Podman-mounted secret; a
    value environment variable wins if an operator or image injects one.
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
