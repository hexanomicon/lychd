"""Bounded path authority and read-only filesystem inspection."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

from lychd.system.path_safety import path_has_symlink_component
from lychd.system.services.lifecycle._authority import LifecycleAuthority, current_authority
from lychd.system.services.lifecycle.models import (
    LifecycleAction,
    LifecycleDisposition,
    LifecycleError,
    LifecycleResourceKind,
)

_SHA256_PREFIX = "sha256:"


def digest_file(path: Path) -> str:
    """Return the canonical digest of one regular file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"{_SHA256_PREFIX}{digest.hexdigest()}"


def lexically_normal(path: Path) -> bool:
    """Return whether an absolute path is already in normalized lexical form."""
    return path.is_absolute() and Path(os.path.normpath(os.fspath(path))) == path


def is_within(path: Path, root: Path) -> bool:
    """Return whether ``path`` is ``root`` or a lexical descendant."""
    return path == root or root in path.parents


def is_allowed_init_directory(
    path: Path,
    *,
    authority: LifecycleAuthority | None = None,
) -> bool:
    """Bound initialization deletion authority to dedicated roots/shared anchors."""
    current = authority or current_authority()
    return any(
        is_within(path, root) for root in (current.codex_root, current.crypt_root, current.cache_root)
    ) or path in {
        current.systemd_units.parent,
        current.systemd_units,
        current.systemd_user_units.parent,
        current.systemd_user_units,
    }


def is_allowed_init_file(
    path: Path,
    *,
    authority: LifecycleAuthority | None = None,
) -> bool:
    """Bound generated-file authority to the Codex and Crypt."""
    current = authority or current_authority()
    return any(is_within(path, root) for root in (current.codex_root, current.crypt_root))


def is_shared_xdg_root(
    path: Path,
    *,
    authority: LifecycleAuthority | None = None,
) -> bool:
    """Return whether a path is a shared XDG namespace LychD never owns."""
    current = authority or current_authority()
    return path in {
        current.codex_root.parent,
        current.crypt_root.parent,
        current.cache_root.parent,
    }


def is_persistent_directory(
    path: Path,
    *,
    authority: LifecycleAuthority | None = None,
) -> bool:
    """Return whether init may provision a directory but deletion must preserve it."""
    current = authority or current_authority()
    return path == current.postgres_data


def validate_receipt_path(
    path: Path,
    *,
    kind: LifecycleResourceKind,
    authority: LifecycleAuthority | None = None,
) -> None:
    """Validate one receipt path against current XDG authority."""
    current = authority or current_authority()
    allowed = (
        is_allowed_init_file(path, authority=current)
        if kind is LifecycleResourceKind.FILE
        else is_allowed_init_directory(path, authority=current)
    )
    if not lexically_normal(path) or not allowed or path in {Path("/"), Path.home()}:
        msg = f"Lifecycle receipt contains an unsafe {kind.value} path: {path}"
        raise LifecycleError(msg)


def unsafe_init_target(
    path: Path,
    *,
    kind: LifecycleResourceKind,
    authority: LifecycleAuthority,
) -> LifecycleAction | None:
    """Return a blocker when init would create a path outside lifecycle authority."""
    if kind is LifecycleResourceKind.FILE:
        allowed = is_allowed_init_file(path, authority=authority)
    else:
        allowed = is_allowed_init_directory(
            path,
            authority=authority,
        ) or is_shared_xdg_root(path, authority=authority)
    if lexically_normal(path) and allowed and path not in {Path("/"), Path.home()}:
        return None
    return LifecycleAction(
        LifecycleDisposition.BLOCKED,
        kind,
        str(path),
        "target is outside bounded initialization authority",
    )


def inspect_init_directory(
    path: Path,
    *,
    expected_mode: int | None = None,
    authority: LifecycleAuthority,
) -> LifecycleAction:
    """Inspect one directory and reject an absent out-of-bound creation target."""
    action = inspect_directory(path, expected_mode=expected_mode)
    if action.disposition is not LifecycleDisposition.WOULD_CREATE:
        return action
    unsafe = unsafe_init_target(
        path,
        kind=LifecycleResourceKind.DIRECTORY,
        authority=authority,
    )
    if unsafe is not None:
        return unsafe
    if is_shared_xdg_root(path, authority=authority):
        return LifecycleAction(
            LifecycleDisposition.WOULD_CREATE,
            LifecycleResourceKind.DIRECTORY,
            str(path),
            "shared XDG namespace is absent; init may create it but never owns it",
        )
    if is_persistent_directory(path, authority=authority):
        return LifecycleAction(
            LifecycleDisposition.WOULD_CREATE,
            LifecycleResourceKind.DIRECTORY,
            str(path),
            (
                "durable database path is absent; init may create a Btrfs/No-COW substrate "
                "or a directory fallback, and `lychd del` preserves it"
            ),
        )
    return action


def inspect_init_file(
    path: Path,
    *,
    expected_mode: int | None = None,
    authority: LifecycleAuthority,
) -> LifecycleAction:
    """Inspect one generated file through the bounded init authority."""
    action = inspect_file(path, expected_mode=expected_mode)
    if action.disposition is not LifecycleDisposition.WOULD_CREATE:
        return action
    return unsafe_init_target(path, kind=LifecycleResourceKind.FILE, authority=authority) or action


def inspect_directory(  # noqa: PLR0911 - each unsafe filesystem shape has a distinct verdict
    path: Path,
    *,
    expected_mode: int | None = None,
) -> LifecycleAction:
    """Plan creation/preservation of one directory without mutating it."""
    symlink = path_has_symlink_component(path)
    if symlink is not None:
        return LifecycleAction(
            LifecycleDisposition.BLOCKED,
            LifecycleResourceKind.DIRECTORY,
            str(path),
            f"symlink component is not trusted: {symlink}",
        )
    if not path.exists():
        mode_detail = f" with mode {expected_mode:04o}" if expected_mode is not None else ""
        return LifecycleAction(
            LifecycleDisposition.WOULD_CREATE,
            LifecycleResourceKind.DIRECTORY,
            str(path),
            f"managed directory is absent{mode_detail}",
        )
    metadata = path.stat()
    if not stat.S_ISDIR(metadata.st_mode):
        return LifecycleAction(
            LifecycleDisposition.BLOCKED,
            LifecycleResourceKind.DIRECTORY,
            str(path),
            "managed path exists but is not a directory",
        )
    if metadata.st_uid != os.getuid():
        return LifecycleAction(
            LifecycleDisposition.BLOCKED,
            LifecycleResourceKind.DIRECTORY,
            str(path),
            f"directory is owned by uid {metadata.st_uid}, expected {os.getuid()}",
        )
    if expected_mode is not None and stat.S_IMODE(metadata.st_mode) != expected_mode:
        return LifecycleAction(
            LifecycleDisposition.BLOCKED,
            LifecycleResourceKind.DIRECTORY,
            str(path),
            f"mode is {stat.S_IMODE(metadata.st_mode):04o}, expected {expected_mode:04o}",
        )
    if path.is_mount():
        return LifecycleAction(
            LifecycleDisposition.PRESERVE,
            LifecycleResourceKind.MOUNT,
            str(path),
            "pre-existing mount is outside initialization ownership",
        )
    return LifecycleAction(
        LifecycleDisposition.PRESERVE,
        LifecycleResourceKind.DIRECTORY,
        str(path),
        "safe directory already exists",
    )


def inspect_file(path: Path, *, expected_mode: int | None = None) -> LifecycleAction:
    """Plan creation/preservation of one generated file without mutating it."""
    symlink = path_has_symlink_component(path)
    if symlink is not None:
        return LifecycleAction(
            LifecycleDisposition.BLOCKED,
            LifecycleResourceKind.FILE,
            str(path),
            f"symlink component is not trusted: {symlink}",
        )
    if not path.exists():
        mode_detail = f" with mode {expected_mode:04o}" if expected_mode is not None else ""
        return LifecycleAction(
            LifecycleDisposition.WOULD_CREATE,
            LifecycleResourceKind.FILE,
            str(path),
            f"generated file is absent{mode_detail}",
        )
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode):
        return LifecycleAction(
            LifecycleDisposition.BLOCKED,
            LifecycleResourceKind.FILE,
            str(path),
            "managed path exists but is not a regular file",
        )
    if metadata.st_uid != os.getuid():
        return LifecycleAction(
            LifecycleDisposition.BLOCKED,
            LifecycleResourceKind.FILE,
            str(path),
            f"file is owned by uid {metadata.st_uid}, expected {os.getuid()}",
        )
    if expected_mode is not None and stat.S_IMODE(metadata.st_mode) != expected_mode:
        return LifecycleAction(
            LifecycleDisposition.BLOCKED,
            LifecycleResourceKind.FILE,
            str(path),
            f"mode is {stat.S_IMODE(metadata.st_mode):04o}, expected {expected_mode:04o}",
        )
    return LifecycleAction(
        LifecycleDisposition.PRESERVE,
        LifecycleResourceKind.FILE,
        str(path),
        "operator or prior initialization file already exists",
    )
