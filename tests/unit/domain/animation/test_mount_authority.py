"""Explicit data mounts cannot expose known host credentials or control edges."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lychd.config.settings.root import Settings
from lychd.domain.animation.mounts import validate_soulstone_data_mount
from lychd.domain.animation.schemas import GenericSoulstoneConfig
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import Transmuter


@pytest.mark.parametrize(
    "relative",
    [".ssh/id_ed25519", ".codex/auth.json", ".aws/credentials", ".netrc", ".bashrc", ".zshenv", ".gitconfig"],
)
def test_read_only_credentials_are_not_data_mounts(relative: str) -> None:
    with pytest.raises(ValueError, match="protected host authority"):
        validate_soulstone_data_mount(Path.home() / relative, ["ro"], stone_name="model")


@pytest.mark.parametrize("source", ["/run/user/1000/podman/podman.sock", "/etc/shadow", "/proc/1/root", "/dev/kvm"])
def test_host_control_filesystems_are_not_data_mounts(source: str) -> None:
    with pytest.raises(ValueError, match="protected host authority"):
        validate_soulstone_data_mount(Path(source), ["ro"], stone_name="model")


def test_external_auth_socket_and_ancestor_are_protected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    socket = tmp_path / "agent" / "socket"
    monkeypatch.setenv("SSH_AUTH_SOCK", str(socket))
    for source in (socket, socket.parent):
        with pytest.raises(ValueError, match="protected host authority"):
            validate_soulstone_data_mount(source, ["ro"], stone_name="model")


def test_special_file_outside_known_roots_is_not_a_data_mount(tmp_path: Path) -> None:
    fifo = tmp_path / "data"
    os.mkfifo(fifo, mode=0o600)
    with pytest.raises(ValueError, match="regular data file or directory"):
        validate_soulstone_data_mount(fifo, ["ro"], stone_name="model")


def test_ordinary_data_mount_cannot_chown_the_host(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot change host ownership"):
        validate_soulstone_data_mount(tmp_path / "models", ["rw", "U"], stone_name="model")


def test_compiler_resolves_credential_alias_before_admitting_mount(tmp_path: Path) -> None:
    alias = tmp_path / "model"
    alias.symlink_to(Path.home() / ".ssh", target_is_directory=True)
    stone = GenericSoulstoneConfig.model_validate(
        {
            "name": "unsafe-model",
            "quadlet": {"image": "example/model"},
            "volumes": [f"{alias}:/models:ro"],
        }
    )
    with pytest.raises(ValueError, match="protected host authority"):
        Transmuter(settings=Settings(), runtime_planner=RuntimeAdapterRegistry()).transmute_all([stone])


@pytest.mark.parametrize("kind", ["file", "directory", "absent"])
def test_ordinary_declared_data_keeps_its_permissions(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "models"
    if kind == "file":
        path.write_bytes(b"model")
    elif kind == "directory":
        path.mkdir(mode=0o700)
    before = path.stat() if path.exists() else None
    validate_soulstone_data_mount(path, ["rw", "Z"], stone_name="model")
    assert (path.stat() if path.exists() else None) == before
