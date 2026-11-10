"""Fixed stdlib-only persisted-identity observer for an inherited descriptor.

Run by absolute path with -I -S. No operator path, mutation or Core import is
accepted. Linux little-endian LP64 x86-64/AArch64 layouts are checked explicitly.
The kernel UUID, inode generation and Btrfs containing root are persistent;
st_dev and mount IDs remain separate, live-operation race guards.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import json
import os
import stat
import struct
import sys
from uuid import UUID

_WORD_BYTES = 8
_STATFS_BYTES = 120
_UUID_BYTES = 16
_TOP_LEVEL_ID = 5
_FIRST_SUBVOLUME_ID = 256
_BTRFS_MAGIC = 0x9123683E
_EXT4_MAGIC = 0xEF53
_SYSFS_MAGIC = 0x62656572
_FS_UUID = 0x80111500
_INODE_GENERATION = 0x80087601
_BTRFS_FS_INFO = 0x8400941F
_BTRFS_SUBVOL_INFO = 0x81F8943C
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


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


def _require(condition: bool, message: str) -> None:  # noqa: FBT001 - internal assertion predicate
    if not condition:
        raise OSError(errno.ENOTSUP, message)


def _require_abi() -> None:
    _require(
        sys.platform == "linux"
        and sys.byteorder == "little"
        and os.uname().machine in {"x86_64", "aarch64"}
        and ctypes.sizeof(ctypes.c_void_p) == _WORD_BYTES
        and ctypes.sizeof(ctypes.c_long) == _WORD_BYTES
        and ctypes.sizeof(_StatFS) == _STATFS_BYTES,
        "Unsupported persistent identity ABI",
    )


def _filesystem_type(descriptor: int) -> int:
    library = ctypes.CDLL(None, use_errno=True)
    function = library.fstatfs
    function.argtypes = (ctypes.c_int, ctypes.POINTER(_StatFS))
    function.restype = ctypes.c_int
    result = _StatFS()
    if function(descriptor, ctypes.byref(result)) != 0:
        message = "Descriptor filesystem unavailable"
        raise OSError(ctypes.get_errno(), message)
    return result.f_type


def _ioctl(descriptor: int, command: int, size: int) -> bytes:
    buffer = bytearray(size)
    fcntl.ioctl(descriptor, command, buffer, True)  # noqa: FBT003 - positional-only mutate_flag
    return bytes(buffer)


def _filesystem_uuid(descriptor: int, filesystem: int) -> str:
    if filesystem == _BTRFS_MAGIC:
        data = _ioctl(descriptor, _BTRFS_FS_INFO, 1024)
        value = UUID(bytes=data[16:32])
        _require(value.int != 0, "A nonzero Btrfs filesystem UUID is required")
        _require_permanent_btrfs(str(value))
        return str(value)
    data = _ioctl(descriptor, _FS_UUID, 17)
    _require(data[0] == _UUID_BYTES, "A 128-bit filesystem UUID is required")
    value = UUID(bytes=data[1:17])
    _require(value.int != 0, "A nonzero filesystem UUID is required")
    return str(value)


def _require_permanent_btrfs(fsid: str) -> None:
    """Refuse clone mounts through the kernel's own per-filesystem attribute."""
    descriptor = os.open("/sys", _DIRECTORY_FLAGS)
    try:
        _require(_filesystem_type(descriptor) == _SYSFS_MAGIC, "Kernel sysfs is required")
        for part in ("fs", "btrfs", fsid):
            child = os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            _require(_filesystem_type(descriptor) == _SYSFS_MAGIC, "Unexpected sysfs boundary")
        attribute = os.open("temp_fsid", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        try:
            _require(
                stat.S_ISREG(os.fstat(attribute).st_mode) and _filesystem_type(attribute) == _SYSFS_MAGIC,
                "Invalid kernel identity attribute",
            )
            _require(os.read(attribute, 8) == b"0\n", "Temporary or unknown Btrfs FSID refused")
        finally:
            os.close(attribute)
    finally:
        os.close(descriptor)


def observe(descriptor: int) -> dict[str, str | int | None]:
    """Observe a regular file or directory through its exact already-open fd."""
    _require_abi()
    before = os.fstat(descriptor)
    _require(stat.S_ISREG(before.st_mode) or stat.S_ISDIR(before.st_mode), "Unsupported object kind")
    filesystem = _filesystem_type(descriptor)
    _require(filesystem in {_BTRFS_MAGIC, _EXT4_MAGIC}, "Unsupported persistent identity filesystem")
    filesystem_uuid = _filesystem_uuid(descriptor, filesystem)
    generation = struct.unpack_from("<I", _ioctl(descriptor, _INODE_GENERATION, 8))[0]
    subvolume_id = None
    subvolume_uuid = None
    if filesystem == _BTRFS_MAGIC:
        subvolume = _ioctl(descriptor, _BTRFS_SUBVOL_INFO, 504)
        subvolume_id = struct.unpack_from("<Q", subvolume)[0]
        uuid = UUID(bytes=subvolume[296:312])
        if subvolume_id == _TOP_LEVEL_ID:
            _require(uuid.int == 0, "Unexpected top-level Btrfs UUID")
        else:
            _require(subvolume_id >= _FIRST_SUBVOLUME_ID and uuid.int != 0, "Incomplete Btrfs containing-root identity")
            subvolume_uuid = str(uuid)
    after = os.fstat(descriptor)
    _require(
        (before.st_dev, before.st_ino, stat.S_IFMT(before.st_mode))
        == (after.st_dev, after.st_ino, stat.S_IFMT(after.st_mode))
        and _filesystem_uuid(descriptor, filesystem) == filesystem_uuid
        and struct.unpack_from("<I", _ioctl(descriptor, _INODE_GENERATION, 8))[0] == generation,
        "Object identity changed during observation",
    )
    return {
        "version": 1,
        "filesystem": "btrfs" if filesystem == _BTRFS_MAGIC else "ext4",
        "filesystem_uuid": filesystem_uuid,
        "inode": before.st_ino,
        "generation": generation,
        "subvolume_id": subvolume_id,
        "subvolume_uuid": subvolume_uuid,
    }


def main(arguments: list[str]) -> int:
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
