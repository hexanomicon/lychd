"""Exercise host record custody against actual Windows file sharing and ACLs."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from lychd.system.desktop import private

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Requires native Windows file handles and DACLs")


def test_windows_record_refuses_file_reparse_point(tmp_path: Path) -> None:
    directory = tmp_path.resolve() / "journal"
    private.private_directory(directory)
    target = directory / "target"
    target.write_bytes(b"ordinary")
    claim = directory / "claim"
    try:
        claim.symlink_to(target)
    except OSError as exc:
        if getattr(exc, "winerror", None) != 1314:  # ERROR_PRIVILEGE_NOT_HELD
            raise
        pytest.skip("Windows account cannot create a file symbolic link")
    with pytest.raises((OSError, ValueError)):
        private.open_windows_reactor_record(claim)


def test_windows_record_blocks_writers_and_survives_producer_unlink(tmp_path: Path) -> None:
    directory = tmp_path.resolve() / "journal"
    private.private_directory(directory)
    claimed = directory / "claimed"
    temporary = directory / "producer-temp"
    claimed.write_bytes(b"line\r\n\x1a")
    temporary.hardlink_to(claimed)
    with temporary.open("r+b"), pytest.raises(PermissionError):
        private.open_windows_reactor_record(claimed)
    descriptor = private.open_windows_reactor_record(claimed)
    try:
        temporary.unlink()
        assert not os.get_inheritable(descriptor)
        assert os.read(descriptor, 16) == b"line\r\n\x1a"
    finally:
        os.close(descriptor)


def test_windows_record_checks_held_object_acl_after_name_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path.resolve() / "journal"
    private.private_directory(directory)
    claimed = directory / "claimed"
    replacement = directory / "replacement"
    claimed.write_bytes(b"original")
    replacement.write_bytes(b"replacement")
    icacls = Path(os.environ["SYSTEMROOT"]) / "System32" / "icacls.exe"
    subprocess.run([icacls, claimed, "/grant", "*S-1-5-32-545:R"], check=True)  # noqa: S603
    original = claimed.stat()
    fstat = os.fstat

    def replace_name(fd: int) -> os.stat_result:
        opened = fstat(fd)
        if os.path.samestat(opened, original):
            monkeypatch.undo()
            claimed.rename(directory / "retired")
            replacement.rename(claimed)
        return opened

    monkeypatch.setattr(os, "fstat", replace_name)
    with pytest.raises(subprocess.CalledProcessError):
        private.open_windows_reactor_record(claimed)
    assert claimed.read_bytes() == b"replacement"
