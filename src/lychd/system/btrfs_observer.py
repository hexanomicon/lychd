"""Fixed stdlib-only Btrfs fd observer, executed by absolute path with -I -S.

This module never resolves an operator pathname or mutates the filesystem.
Linux LP64 x86-64/AArch64 UAPI layout is checked before issuing either syscall.
The caller owns the process deadline and passes only the observed directory fd.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import json
import os
import stat
import sys
from uuid import UUID

_BTRFS_MAGIC = 0x9123683E
_GET_SUBVOL_INFO = 0x81F8943C
_LP64_WORD_BYTES = 8
_STATFS_BYTES = 120
_SUBVOLUME_INFO_BYTES = 504
_UUID_OFFSET = 296
_FIRST_FREE_OBJECTID = 256


class _StatFS(ctypes.Structure):
    _fields_ = (
        ("f_type", ctypes.c_long),
        ("f_bsize", ctypes.c_long),
        ("f_blocks", ctypes.c_ulong),
        ("f_bfree", ctypes.c_ulong),
        ("f_bavail", ctypes.c_ulong),
        ("f_files", ctypes.c_ulong),
        ("f_ffree", ctypes.c_ulong),
        ("f_fsid", ctypes.c_int * 2),
        ("f_namelen", ctypes.c_long),
        ("f_frsize", ctypes.c_long),
        ("f_flags", ctypes.c_long),
        ("f_spare", ctypes.c_long * 4),
    )


class _Timespec(ctypes.Structure):
    _fields_ = (("sec", ctypes.c_uint64), ("nsec", ctypes.c_uint32))


class _SubvolumeInfo(ctypes.Structure):
    _fields_ = (
        ("treeid", ctypes.c_uint64),
        ("name", ctypes.c_char * 256),
        ("parent_id", ctypes.c_uint64),
        ("dirid", ctypes.c_uint64),
        ("generation", ctypes.c_uint64),
        ("flags", ctypes.c_uint64),
        ("uuid", ctypes.c_ubyte * 16),
        ("parent_uuid", ctypes.c_ubyte * 16),
        ("received_uuid", ctypes.c_ubyte * 16),
        ("ctransid", ctypes.c_uint64),
        ("otransid", ctypes.c_uint64),
        ("stransid", ctypes.c_uint64),
        ("rtransid", ctypes.c_uint64),
        ("ctime", _Timespec),
        ("otime", _Timespec),
        ("stime", _Timespec),
        ("rtime", _Timespec),
        ("reserved", ctypes.c_uint64 * 8),
    )


def _require_abi() -> None:
    """Reject unknown ioctl/statfs layouts instead of reading the wrong buffer."""
    if (
        sys.platform != "linux"
        or os.uname().machine not in {"x86_64", "aarch64"}
        or ctypes.sizeof(ctypes.c_void_p) != _LP64_WORD_BYTES
        or ctypes.sizeof(ctypes.c_long) != _LP64_WORD_BYTES
        or ctypes.sizeof(_StatFS) != _STATFS_BYTES
        or ctypes.sizeof(_SubvolumeInfo) != _SUBVOLUME_INFO_BYTES
        or _SubvolumeInfo.treeid.offset != 0
        or _SubvolumeInfo.uuid.offset != _UUID_OFFSET
    ):
        message = "Unsupported Btrfs observation ABI."
        raise OSError(errno.ENOTSUP, message)


def _filesystem_type(descriptor: int) -> int:
    library = ctypes.CDLL(None, use_errno=True)
    function = library.fstatfs
    function.argtypes = (ctypes.c_int, ctypes.POINTER(_StatFS))
    function.restype = ctypes.c_int
    result = _StatFS()
    if function(descriptor, ctypes.byref(result)) != 0:
        message = "Cannot inspect descriptor filesystem."
        raise OSError(ctypes.get_errno(), message)
    return result.f_type


def observe(descriptor: int) -> dict[str, str | int]:
    """Read this root's own UUID/ID, never its path or containing-root identity."""
    _require_abi()
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_ino != _FIRST_FREE_OBJECTID
        or _filesystem_type(descriptor) != _BTRFS_MAGIC
    ):
        message = "Descriptor is not a Btrfs subvolume root."
        raise OSError(errno.EINVAL, message)
    buffer = bytearray(ctypes.sizeof(_SubvolumeInfo))
    fcntl.ioctl(descriptor, _GET_SUBVOL_INFO, buffer, True)  # noqa: FBT003 - positional-only mutate_flag
    info = _SubvolumeInfo.from_buffer(buffer)
    if info.treeid < _FIRST_FREE_OBJECTID:
        message = "Btrfs subvolume ID is reserved."
        raise ValueError(message)
    return {"uuid": str(UUID(bytes=bytes(info.uuid))), "subvolume_id": info.treeid}


def main(arguments: list[str]) -> int:
    """Emit one bounded identity or no stdout; failures expose no private paths."""
    if len(arguments) != 1 or not arguments[0].isascii() or not arguments[0].isdecimal():
        return 1
    try:
        result = observe(int(arguments[0]))
    except (OSError, ValueError, OverflowError):
        return 1
    sys.stdout.write(json.dumps(result, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
