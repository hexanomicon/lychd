"""Admission of explicit Soulstone data sources outside host authority surfaces."""

from __future__ import annotations

import os
import stat
from collections.abc import Sequence
from pathlib import Path

from lychd.system.constants import PATH_XDG_CONFIG_HOME, PATH_XDG_DATA_HOME
from lychd.system.path_policy import paths_overlap


def validate_soulstone_data_mount(host_path: Path, options: Sequence[str], *, stone_name: str) -> None:
    """Reject known host authority and ownership mutation even on read-only mounts.

    The caller supplies a canonical host path. This is compile-time observation,
    not inspection of descendants or a runtime grant against a pinned inode.
    """
    if "U" in options:
        message = f"Soulstone '{stone_name}' data mounts cannot change host ownership with :U"
        raise ValueError(message)
    for root in _host_authority_roots():
        try:
            canonical = root.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            message = f"Soulstone '{stone_name}' host authority boundary cannot be resolved safely: {root}"
            raise ValueError(message) from exc
        if paths_overlap(host_path, canonical):
            message = f"Soulstone '{stone_name}' host mount {host_path} overlaps protected host authority {root}"
            raise ValueError(message)
    try:
        metadata = host_path.stat(follow_symlinks=False)
    except FileNotFoundError:
        # A deployment may provision an ordinary data source after compilation.
        return
    except OSError as exc:
        message = f"Soulstone '{stone_name}' host mount type cannot be inspected: {host_path}"
        raise ValueError(message) from exc
    if not (stat.S_ISREG(metadata.st_mode) or stat.S_ISDIR(metadata.st_mode)):
        message = f"Soulstone '{stone_name}' host mount must be a regular data file or directory: {host_path}"
        raise ValueError(message)


def _host_authority_roots() -> tuple[Path, ...]:
    """Bound common host identity, configuration, kernel, and runtime namespaces."""
    home = Path.home()
    roots = [
        *(Path(value) for value in ("/etc", "/run", "/proc", "/sys", "/dev")),
        PATH_XDG_CONFIG_HOME,
        PATH_XDG_DATA_HOME / "containers",
        PATH_XDG_DATA_HOME / "keyrings",
        *(
            home / name
            for name in (
                ".ssh",
                ".gnupg",
                ".aws",
                ".azure",
                ".kube",
                ".docker",
                ".codex",
                ".claude",
                ".password-store",
                ".pki",
                ".mozilla",
                ".netrc",
                ".git-credentials",
                ".gitconfig",
                ".bashrc",
                ".profile",
                ".bash_profile",
                ".bash_login",
                ".zshrc",
                ".zshenv",
                ".zprofile",
                ".config",
            )
        ),
    ]
    for variable in ("XDG_RUNTIME_DIR", "SSH_AUTH_SOCK", "GPG_AGENT_INFO"):
        value = os.environ.get(variable)
        if value:
            # Legacy GPG_AGENT_INFO also includes process/protocol fields.
            path = Path(value.split(":", 1)[0] if variable == "GPG_AGENT_INFO" else value)
            if path.is_absolute():
                roots.append(path)
    return tuple(dict.fromkeys(roots))
