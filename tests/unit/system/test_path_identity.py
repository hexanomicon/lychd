"""Persistent identity providers and transport fail closed without kernel guesses."""

from __future__ import annotations

import json
import os
import struct
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from lychd.system import path_identity
from lychd.system import path_identity_observer as observer
from lychd.system.operator.process import ProcessResult

FS_UUID = "87654321-4321-8765-4321-876543218765"
SUBVOL_UUID = "12345678-1234-5678-1234-567812345678"


def payload(inode: int = 256) -> dict[str, object]:
    return {
        "version": 1,
        "filesystem": "btrfs",
        "filesystem_uuid": FS_UUID,
        "inode": inode,
        "generation": 7,
        "subvolume_id": 259,
        "subvolume_uuid": SUBVOL_UUID,
    }


@pytest.mark.parametrize(
    "changed",
    [
        {"version": True},
        {"filesystem": "overlay"},
        {"filesystem_uuid": "0" * 32},
        {"generation": -1},
        {"generation": 2**32},
        {"inode": True},
        {"inode": 0},
        {"subvolume_id": 6},
        {"subvolume_uuid": None},
        {"filesystem": "ext4"},
        {"unexpected": 1},
    ],
)
def test_identity_model_rejects_incomplete_or_ambiguous_authority(changed: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        path_identity.PersistentPathIdentity.model_validate(payload() | changed)


def test_top_level_and_ext4_scopes_are_explicit() -> None:
    top = path_identity.PersistentPathIdentity.model_validate(payload() | {"subvolume_id": 5, "subvolume_uuid": None})
    ext4 = path_identity.PersistentPathIdentity.model_validate(
        payload() | {"filesystem": "ext4", "subvolume_id": None, "subvolume_uuid": None}
    )
    assert top != ext4


def test_native_btrfs_provider_never_calls_generic_uuid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "file"
    path.write_bytes(b"data")
    fd = os.open(path, os.O_RDONLY)
    commands: list[int] = []
    permanent: list[str] = []
    monkeypatch.setattr(observer, "_filesystem_type", lambda _: observer._BTRFS_MAGIC)
    monkeypatch.setattr(observer, "_require_permanent_btrfs", permanent.append)

    def ioctl(_fd: int, command: int, size: int) -> bytes:
        commands.append(command)
        result = bytearray(size)
        if command == observer._BTRFS_FS_INFO:
            result[16:32] = UUID(FS_UUID).bytes
        elif command == observer._BTRFS_SUBVOL_INFO:
            struct.pack_into("<Q", result, 0, 259)
            result[296:312] = UUID(SUBVOL_UUID).bytes
        elif command == observer._INODE_GENERATION:
            struct.pack_into("<I", result, 0, 7)
        else:
            pytest.fail("Btrfs must not require unsupported generic UUID ioctl")
        return bytes(result)

    monkeypatch.setattr(observer, "_ioctl", ioctl)
    try:
        first = observer.observe(fd)
        path.write_bytes(b"changed content")
        assert observer.observe(fd) == first == payload(os.fstat(fd).st_ino)
    finally:
        os.close(fd)
    assert observer._FS_UUID not in commands
    assert permanent == [FS_UUID] * 4


def test_unknown_filesystem_refuses_before_any_ioctl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(observer, "_filesystem_type", lambda _: 0x794C7630)
    monkeypatch.setattr(observer, "_ioctl", lambda *_: pytest.fail("unsupported provider must not issue ioctls"))
    fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(OSError, match="Unsupported persistent"):
            observer.observe(fd)
    finally:
        os.close(fd)


def test_ext4_unavailable_uuid_refuses_without_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(observer, "_filesystem_type", lambda _: observer._EXT4_MAGIC)

    def unavailable(_fd: int, command: int, _size: int) -> bytes:
        assert command == observer._FS_UUID
        raise OSError(25, "unsupported ioctl")

    monkeypatch.setattr(observer, "_ioctl", unavailable)
    fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(OSError, match="unsupported ioctl"):
            observer.observe(fd)
    finally:
        os.close(fd)


class Runner:
    def __init__(self, content: str, returncode: int = 0) -> None:
        self.content = content
        self.returncode = returncode
        self.calls: list[tuple[tuple[str, ...], tuple[int, ...]]] = []

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        del argv, timeout_s
        pytest.fail("Observer must use only the explicit inherited-descriptor port")

    def run_with_fds(self, argv: tuple[str, ...], *, timeout_s: float, pass_fds: tuple[int, ...]) -> ProcessResult:
        assert timeout_s == 5.0
        self.calls.append((argv, pass_fds))
        return ProcessResult(argv=argv, returncode=self.returncode, stdout=self.content)


def test_transport_pins_only_supplied_fd_and_strictly_parses(tmp_path: Path) -> None:
    fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        runner = Runner(json.dumps(payload(os.fstat(fd).st_ino)))
        result = path_identity.observe_identity_fd(fd, runner=runner)
        assert result.filesystem_uuid == FS_UUID
        argv, passed = runner.calls[0]
        assert argv[1:3] == ("-I", "-S")
        assert argv[-1] == str(fd)
        assert passed == (fd,)
        for content in ("{}", '{"version":1,"version":1}', json.dumps(payload(1)), "x" * 1025):
            with pytest.raises(path_identity.PathIdentityError):
                path_identity.observe_identity_fd(fd, runner=Runner(content))
        with pytest.raises(path_identity.PathIdentityError):
            path_identity.observe_identity_fd(fd, runner=Runner("", returncode=1))
    finally:
        os.close(fd)


@pytest.mark.parametrize("value", [b"1\n", b"", b"0", b"0\nextra"])
def test_temporary_or_uncertain_btrfs_fsid_is_refused(value: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    with monkeypatch.context() as patch:
        patch.setattr(observer.os, "open", lambda *_args, **_kwargs: 9)
        patch.setattr(observer.os, "close", lambda _fd: None)
        patch.setattr(observer.os, "fstat", lambda _fd: SimpleNamespace(st_mode=0o100444))
        patch.setattr(observer.os, "read", lambda *_args: value)
        patch.setattr(observer, "_filesystem_type", lambda _fd: observer._SYSFS_MAGIC)
        with pytest.raises(OSError, match="Temporary or unknown"):
            observer._require_permanent_btrfs(FS_UUID)


def test_non_sysfs_identity_attribute_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as patch:
        patch.setattr(observer.os, "open", lambda *_args, **_kwargs: 9)
        patch.setattr(observer.os, "close", lambda _fd: None)
        patch.setattr(observer, "_filesystem_type", lambda _fd: observer._EXT4_MAGIC)
        with pytest.raises(OSError, match="Kernel sysfs"):
            observer._require_permanent_btrfs(FS_UUID)
