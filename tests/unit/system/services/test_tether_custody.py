"""Filesystem adversaries and immutable evidence at the fixed custody boundary."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lychd.system.services.tether.custody import TetherCustody
from lychd.system.services.tether.models import TetherError
from tests.unit.system.services.test_tether_operations import make_custody


def test_immutable_history_disagrees_without_replacement(tmp_path: Path) -> None:
    custody = make_custody(tmp_path)
    custody.publish("revocations", "1.json", b"first", immutable=True)
    custody.publish("revocations", "1.json", b"first", immutable=True)
    with pytest.raises(TetherError, match="Immutable"):
        custody.publish("revocations", "1.json", b"second", immutable=True)
    assert custody.read("revocations", "1.json") == b"first"


def test_no_adoption_after_unreceipted_creation(tmp_path: Path) -> None:
    codex, crypt = tmp_path / "codex", tmp_path / "crypt"
    codex.mkdir(mode=0o700)
    crypt.mkdir(mode=0o700)
    (crypt / "tether").mkdir(mode=0o700)
    with pytest.raises(TetherError, match="creation receipt"):
        TetherCustody(codex, crypt).initialize()


def test_replaced_same_mode_directory_refuses(tmp_path: Path) -> None:
    custody = make_custody(tmp_path)
    target = custody.directories["wireguard"]
    target.rename(target.with_name("preserved"))
    target.mkdir(mode=0o755)
    with pytest.raises(TetherError, match="identity changed"):
        custody.attest()


def test_symlink_and_hardlink_records_refuse(tmp_path: Path) -> None:
    custody = make_custody(tmp_path)
    target = custody.directories["private"] / "closed.json"
    foreign = tmp_path / "foreign"
    foreign.write_bytes(b"preserve")
    foreign.chmod(0o600)
    target.symlink_to(foreign)
    with pytest.raises(OSError, match="Too many levels"):
        custody.read("private", "closed.json")
    target.unlink()
    os.link(foreign, target)
    with pytest.raises(TetherError, match="metadata"):
        custody.read("private", "closed.json")
    assert foreign.read_bytes() == b"preserve"


def test_public_forwarder_files_are_readable_after_ssh_uid_drop(tmp_path: Path) -> None:
    custody = make_custody(tmp_path)
    custody.publish("forwarder", "authorized_keys", b"public")
    assert custody.directories["public"].stat().st_mode & 0o777 == 0o700
    assert custody.directories["forwarder"].stat().st_mode & 0o777 == 0o755
    assert (custody.directories["forwarder"] / "authorized_keys").stat().st_mode & 0o777 == 0o644


def test_restrictive_operator_umask_still_creates_receipted_exact_modes(tmp_path: Path) -> None:
    previous = os.umask(0o077)
    try:
        custody = make_custody(tmp_path)
        custody.publish("forwarder", "authorized_keys", b"public")
        custody.attest()
        assert custody.directories["forwarder"].stat().st_mode & 0o777 == 0o755
        assert (custody.directories["forwarder"] / "authorized_keys").stat().st_mode & 0o777 == 0o644
    finally:
        os.umask(previous)
