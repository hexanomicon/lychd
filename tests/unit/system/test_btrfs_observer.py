"""Btrfs UAPI, fd authority and bounded observer transport without a host subvolume."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import ctypes
import errno
import json
import os
import stat
import struct
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock
from uuid import UUID

import pytest

from lychd.system import btrfs_identity, btrfs_observer
from lychd.system.btrfs_identity import BtrfsSubvolumeObservation, observe_subvolume_fd
from lychd.system.operator.process import ProcessInvocationError, ProcessResult

if TYPE_CHECKING:
    from lychd.system.operator.process import DescriptorProcessRunner

_UUID = "12345678-1234-5678-1234-567812345678"


def _metadata(inode: int = 256, mode: int = stat.S_IFDIR | 0o700) -> os.stat_result:
    return os.stat_result((mode, inode, 0, 1, 1000, 1000, 0, 0, 0, 0))


def _root(monkeypatch: pytest.MonkeyPatch, metadata: os.stat_result | None = None) -> None:
    monkeypatch.setattr(btrfs_observer, "_require_abi", Mock())
    monkeypatch.setattr(btrfs_observer.os, "fstat", Mock(return_value=metadata or _metadata()))
    monkeypatch.setattr(btrfs_observer, "_filesystem_type", Mock(return_value=0x9123683E))


def test_supported_uapi_buffer_has_the_header_verified_layout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(btrfs_observer.sys, "platform", "linux")
    monkeypatch.setattr(btrfs_observer.os, "uname", Mock(return_value=SimpleNamespace(machine="x86_64")))
    btrfs_observer._require_abi()
    assert ctypes.sizeof(btrfs_observer._SubvolumeInfo) == 504
    assert btrfs_observer._SubvolumeInfo.uuid.offset == 296
    assert ctypes.sizeof(btrfs_observer._StatFS) == 120


def test_descriptor_observer_reads_own_uuid_and_id_from_exact_ioctl(monkeypatch: pytest.MonkeyPatch) -> None:
    _root(monkeypatch)
    calls: list[tuple[int, int, int]] = []

    def ioctl(descriptor: int, request: int, buffer: bytearray, mutate: object) -> int:
        calls.append((descriptor, request, len(buffer)))
        assert mutate is True
        struct.pack_into("=Q", buffer, 0, 259)
        buffer[296:312] = UUID(_UUID).bytes
        return 0

    monkeypatch.setattr(btrfs_observer.fcntl, "ioctl", ioctl)
    assert btrfs_observer.observe(37) == {"uuid": _UUID, "subvolume_id": 259}
    assert calls == [(37, 0x81F8943C, 504)]


@pytest.mark.parametrize("inode", [2, 257, 123456])
def test_ordinary_directory_and_stub_cannot_borrow_containing_root_identity(
    monkeypatch: pytest.MonkeyPatch, inode: int
) -> None:
    _root(monkeypatch, _metadata(inode))
    ioctl = Mock()
    monkeypatch.setattr(btrfs_observer.fcntl, "ioctl", ioctl)
    with pytest.raises(OSError, match="not a Btrfs subvolume root"):
        btrfs_observer.observe(37)
    ioctl.assert_not_called()


@pytest.mark.parametrize("kind", ["foreign-filesystem", "regular-file"])
def test_inode_256_alone_cannot_attest_a_btrfs_root(monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    _root(monkeypatch, _metadata(mode=stat.S_IFREG | 0o600) if kind == "regular-file" else None)
    if kind == "foreign-filesystem":
        monkeypatch.setattr(btrfs_observer, "_filesystem_type", Mock(return_value=0xEF53))
    ioctl = Mock()
    monkeypatch.setattr(btrfs_observer.fcntl, "ioctl", ioctl)
    with pytest.raises(OSError, match="not a Btrfs subvolume root"):
        btrfs_observer.observe(37)
    ioctl.assert_not_called()


@pytest.mark.parametrize("root_id", [0, 5, 255])
def test_reserved_root_identity_remains_unverifiable(monkeypatch: pytest.MonkeyPatch, root_id: int) -> None:
    _root(monkeypatch)

    def ioctl(descriptor: int, request: int, buffer: bytearray, mutate: object) -> int:
        struct.pack_into("=Q", buffer, 0, root_id)
        buffer[296:312] = UUID(_UUID).bytes
        return 0

    monkeypatch.setattr(btrfs_observer.fcntl, "ioctl", ioctl)
    with pytest.raises(ValueError, match="ID is reserved"):
        btrfs_observer.observe(37)


def test_unknown_abi_refuses_before_descriptor_or_ioctl_access(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(btrfs_observer.os, "uname", Mock(return_value=SimpleNamespace(machine="unsupported")))
    access = Mock()
    monkeypatch.setattr(btrfs_observer.os, "fstat", access)
    with pytest.raises(OSError, match="Unsupported Btrfs observation ABI") as raised:
        btrfs_observer.observe(37)
    assert raised.value.errno == errno.ENOTSUP
    access.assert_not_called()


def test_observer_entrypoint_emits_only_bounded_identity(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(btrfs_observer, "observe", Mock(return_value={"uuid": _UUID, "subvolume_id": 259}))
    assert btrfs_observer.main(["37"]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == {"uuid": _UUID, "subvolume_id": 259}
    assert len(output.out.encode()) < 256
    assert output.err == ""


@pytest.mark.parametrize("failure", [errno.EPERM, errno.ENOTTY, errno.EBADF])
def test_observer_failure_returns_no_identity_or_private_diagnostic(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], failure: int
) -> None:
    monkeypatch.setattr(btrfs_observer, "observe", Mock(side_effect=OSError(failure, "private-input-marker")))
    assert btrfs_observer.main(["37"]) == 1
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("arguments", [[], ["bad"], ["-1"], ["٣٧"], ["/private"], ["37", "extra"]])
def test_observer_accepts_one_explicit_fd_only(monkeypatch: pytest.MonkeyPatch, arguments: list[str]) -> None:
    observe = Mock()
    monkeypatch.setattr(btrfs_observer, "observe", observe)
    assert btrfs_observer.main(arguments) == 1
    observe.assert_not_called()


def test_transport_uses_selected_source_script_isolated_interpreter_and_only_leaf_fd() -> None:
    runner = Mock()
    runner.run_with_fds.return_value = ProcessResult(
        argv=(), returncode=0, stdout=json.dumps({"uuid": _UUID, "subvolume_id": 259})
    )
    result = observe_subvolume_fd(37, runner=cast("DescriptorProcessRunner", runner), timeout_s=3)
    assert result == BtrfsSubvolumeObservation(uuid=_UUID, subvolume_id=259)
    runner.run_with_fds.assert_called_once_with(
        (str(Path(sys.executable).resolve()), "-I", "-S", str(Path(btrfs_observer.__file__).resolve()), "37"),
        timeout_s=3,
        pass_fds=(37,),
    )


@pytest.mark.parametrize(
    "payload",
    [
        "",
        "not-json",
        json.dumps({"uuid": _UUID, "subvolume_id": 1 << 64}),
        json.dumps({"uuid": _UUID, "subvolume_id": True}),
        "[]",
        " " * 257,
        "{}",
        '{"uuid": 1,"subvolume_id":259}',
        '{"uuid":"bad","subvolume_id":259}',
        '{"uuid":"' + _UUID + '","subvolume_id":"259"}',
        '{"uuid":"' + _UUID + '","subvolume_id":5}',
        '{"uuid":"' + _UUID + '","subvolume_id":259,"extra":true}',
    ],
)
def test_transport_rejects_missing_malformed_or_oversized_metadata(payload: str) -> None:
    runner = Mock()
    runner.run_with_fds.return_value = ProcessResult(argv=(), returncode=0, stdout=payload)
    assert observe_subvolume_fd(37, runner=cast("DescriptorProcessRunner", runner), timeout_s=5) is None


@pytest.mark.parametrize("failure", ["timeout", "nonzero"])
def test_transport_never_accepts_identity_from_failed_observation(failure: str) -> None:
    runner = Mock()
    if failure == "timeout":
        runner.run_with_fds.side_effect = ProcessInvocationError("timed out")
    else:
        runner.run_with_fds.return_value = ProcessResult(
            argv=(), returncode=1, stdout=json.dumps({"uuid": _UUID, "subvolume_id": 259})
        )
    assert observe_subvolume_fd(37, runner=cast("DescriptorProcessRunner", runner), timeout_s=5) is None
    assert runner.run_with_fds.call_args.kwargs["timeout_s"] == 5


def test_standalone_helper_ignores_ambient_python_module_resolution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    marker = tmp_path / "ambient-imported"
    (tmp_path / "sitecustomize.py").write_text(f"from pathlib import Path; Path({str(marker)!r}).touch()\n")
    (tmp_path / "btrfs_observer.py").write_text(f"from pathlib import Path; Path({str(marker)!r}).touch()\n")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    completed = subprocess.run(  # noqa: S603 - fixed interpreter, exact source helper and invalid inert input
        [str(Path(sys.executable).resolve()), "-I", "-S", str(Path(btrfs_observer.__file__).resolve()), "invalid-fd"],
        capture_output=True,
        check=False,
        timeout=3,
        text=True,
        cwd=tmp_path,
    )
    assert completed.returncode == 1
    assert completed.stdout == completed.stderr == ""
    assert not marker.exists()
    assert Path(btrfs_identity.__file__).parent == Path(btrfs_observer.__file__).parent


@pytest.mark.parametrize("kind", ["init", "deletion"])
@pytest.mark.parametrize("failure", ["access", "cleanup", "cancel"])
def test_public_probe_preserves_unverifiable_access_and_native_cleanup_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str, failure: str
) -> None:
    from lychd.system.services import btrfs as preparation
    from lychd.system.services.layout_directory_settlement import DirectoryRollbackError
    from lychd.system.services.lifecycle import deletion_storage

    target = tmp_path / "data"
    target.mkdir()
    runner = Mock()
    error: BaseException
    if failure == "cleanup":
        error = DirectoryRollbackError("uncertain descriptor settlement", outcome="unchanged", verified=True)
    elif failure == "cancel":
        error = KeyboardInterrupt()
    else:
        error = RuntimeError("ordinary inaccessible path")
    if kind == "init":
        monkeypatch.setattr(preparation, "open_directory_path", Mock(side_effect=error))
        inspect = preparation.Btrfs(runner=runner, tools=preparation.BtrfsTools(btrfs=None)).inspect_subvolume
    else:
        monkeypatch.setattr(deletion_storage, "open_directory_path", Mock(side_effect=error))
        inspect = deletion_storage.CommandBtrfsSubvolumeProbe(runner).inspect
    if failure == "access":
        assert inspect(target) is None
    else:
        with pytest.raises(type(error)) as raised:
            inspect(target)
        assert raised.value is error
    runner.run_with_fds.assert_not_called()
