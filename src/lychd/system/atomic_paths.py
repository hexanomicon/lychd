"""Linux-native atomic pathname operations without check-then-rename fallbacks."""

from __future__ import annotations

import ctypes
import errno
import os
from pathlib import Path
from typing import Protocol, cast

_AT_FDCWD = -100
_RENAME_NOREPLACE = 1
_RENAME_EXCHANGE = 2


class _RenameAt2(Protocol):
    """Typed shape of libc's ``renameat2`` symbol."""

    argtypes: object
    restype: object

    def __call__(
        self,
        source_dir_fd: int,
        source: bytes,
        destination_dir_fd: int,
        destination: bytes,
        flags: int,
        /,
    ) -> int: ...


_LIBC = ctypes.CDLL(None, use_errno=True)


def _load_renameat2() -> _RenameAt2 | None:
    """Load and type the libc symbol without inventing a weaker fallback."""
    try:
        function = cast("_RenameAt2", _LIBC.renameat2)
    except AttributeError:
        return None
    function.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    function.restype = ctypes.c_int
    return function


_RENAMEAT2 = _load_renameat2()


def rename_exchange(source: Path, destination: Path) -> None:
    """Atomically exchange two absolute pathnames."""
    source_bytes = _absolute_path(source, parameter="source")
    destination_bytes = _absolute_path(destination, parameter="destination")
    _invoke_renameat2(
        source_dir_fd=_AT_FDCWD,
        source=source_bytes,
        destination_dir_fd=_AT_FDCWD,
        destination=destination_bytes,
        flags=_RENAME_EXCHANGE,
        source_display=str(source),
        destination_display=str(destination),
    )


def rename_noreplace(source: Path, destination: Path) -> None:
    """Atomically rename an absolute pathname only when the target is absent."""
    source_bytes = _absolute_path(source, parameter="source")
    destination_bytes = _absolute_path(destination, parameter="destination")
    _invoke_renameat2(
        source_dir_fd=_AT_FDCWD,
        source=source_bytes,
        destination_dir_fd=_AT_FDCWD,
        destination=destination_bytes,
        flags=_RENAME_NOREPLACE,
        source_display=str(source),
        destination_display=str(destination),
    )


def rename_exchange_at(
    source_name: str,
    destination_name: str,
    *,
    source_dir_fd: int,
    destination_dir_fd: int,
) -> None:
    """Atomically exchange names relative to two pinned directory descriptors."""
    source = _relative_name(source_name, parameter="source_name")
    destination = _relative_name(destination_name, parameter="destination_name")
    _invoke_renameat2(
        source_dir_fd=source_dir_fd,
        source=source,
        destination_dir_fd=destination_dir_fd,
        destination=destination,
        flags=_RENAME_EXCHANGE,
        source_display=source_name,
        destination_display=destination_name,
    )


def rename_noreplace_at(
    source_name: str,
    destination_name: str,
    *,
    source_dir_fd: int,
    destination_dir_fd: int,
) -> None:
    """Rename between pinned directories only when the target name is absent."""
    source = _relative_name(source_name, parameter="source_name")
    destination = _relative_name(destination_name, parameter="destination_name")
    _invoke_renameat2(
        source_dir_fd=source_dir_fd,
        source=source,
        destination_dir_fd=destination_dir_fd,
        destination=destination,
        flags=_RENAME_NOREPLACE,
        source_display=source_name,
        destination_display=destination_name,
    )


def _absolute_path(path: Path, *, parameter: str) -> bytes:
    """Encode one absolute ``Path`` without resolving or following it."""
    if not path.is_absolute():
        message = f"{parameter} must be absolute."
        raise ValueError(message)
    encoded = os.fsencode(path)
    if b"\0" in encoded:
        message = f"{parameter} cannot contain a null byte."
        raise ValueError(message)
    return encoded


def _relative_name(name: str, *, parameter: str) -> bytes:
    """Encode one safe descriptor-relative filename component."""
    if not name or name in {".", ".."} or "/" in name:
        message = f"{parameter} must be one relative filename component."
        raise ValueError(message)
    encoded = os.fsencode(name)
    if b"\0" in encoded:
        message = f"{parameter} cannot contain a null byte."
        raise ValueError(message)
    return encoded


def _invoke_renameat2(
    *,
    source_dir_fd: int,
    source: bytes,
    destination_dir_fd: int,
    destination: bytes,
    flags: int,
    source_display: str,
    destination_display: str,
) -> None:
    """Invoke libc and preserve its errno plus both pathname operands."""
    if _RENAMEAT2 is None:
        raise OSError(
            errno.ENOSYS,
            os.strerror(errno.ENOSYS),
            source_display,
            None,
            destination_display,
        )
    ctypes.set_errno(0)
    result = _RENAMEAT2(
        source_dir_fd,
        source,
        destination_dir_fd,
        destination,
        flags,
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number == 0:
        error_number = errno.EIO
    raise OSError(
        error_number,
        os.strerror(error_number),
        source_display,
        None,
        destination_display,
    )


__all__ = (
    "rename_exchange",
    "rename_exchange_at",
    "rename_noreplace",
    "rename_noreplace_at",
)
