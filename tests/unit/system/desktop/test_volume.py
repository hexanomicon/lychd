"""Cold-cut, volume identity and revocation refusals independent of native host qualification."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from lychd.system.desktop import volume_commands as commands
from lychd.system.desktop import volume_native as native
from lychd.system.desktop import volume_storage as storage
from lychd.system.desktop.private import private_directory
from lychd.system.desktop.volume_cluster import cold_control, inventory


def test_exact_generation_and_offvolume_revocation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    default = tmp_path / "native-data"
    monkeypatch.setattr(commands, "_DEFAULT", default)
    directory = storage.authority(default)
    private_directory(directory)
    generation, volume = str(uuid4()), str(uuid4())
    grant = {"generation": generation, "volume": volume, "system_identifier": "3456"}
    path = directory / "grant.json"
    storage.write_record(path, **grant)
    assert commands._grant(volume) == grant
    with pytest.raises(ValueError, match="stale"):
        commands._grant(str(uuid4()))
    path.rename(directory / f"revoked-{generation}.json")
    # Even restoring the old grant file beside the surviving tombstone must fail.
    storage.write_record(path, **grant)
    with pytest.raises(ValueError, match="revoked"):
        commands._grant(volume)


def test_dedicated_cut_refuses_personal_files_and_linked_database_files(tmp_path: Path) -> None:
    source = tmp_path / storage.STORAGE
    source.mkdir()
    storage.dedicated_contents(tmp_path)
    (tmp_path / "unrelated").mkdir()
    with pytest.raises(ValueError, match="outside"):
        storage.dedicated_contents(tmp_path)
    (tmp_path / "unrelated" / "file").touch()
    (source / "linked").hardlink_to(tmp_path / "unrelated" / "file")
    with pytest.raises(ValueError, match="linked"):
        inventory(source, digest=False)


def test_restored_file_content_and_empty_directories_are_covered(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir()
    (root / "pg_tblspc").mkdir()
    (root / "relation").write_bytes(b"committed")
    before = inventory(root, digest=True)
    (root / "relation").write_bytes(b"altered")
    assert inventory(root, digest=True) != before
    assert before["pg_tblspc"] == "directory"


def test_cold_control_requires_shutdown_and_same_identifier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lychd.system.desktop import volume_cluster

    (tmp_path / "PG_VERSION").write_text("18")
    (tmp_path / "pg_wal").mkdir()
    (tmp_path / "pg_tblspc").mkdir()
    for state, identifier in [("in production", "42"), ("shut down", "24"), ("shut down", "42")]:
        output = f"Database system identifier: {identifier}\nDatabase cluster state: {state}\n"
        monkeypatch.setattr(volume_cluster.subprocess, "check_output", lambda *_args, value=output, **_kwargs: value)
        if state == "shut down" and identifier == "42":
            cold_control(tmp_path, "pg_controldata", "42")
        else:
            with pytest.raises(ValueError, match="shutdown"):
                cold_control(tmp_path, "pg_controldata", "42")
    (tmp_path / "pg_tblspc" / "123").mkdir()
    with pytest.raises(ValueError, match="tablespaces"):
        cold_control(tmp_path, "pg_controldata", "42")


def test_native_vss_refuses_shadow_of_another_volume(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    volume, shadow, provider, cut = (str(uuid4()) for _ in range(4))
    data = {
        "VolumeName": "\\\\?\\Volume{" + volume + "}\\",
        "ID": shadow,
        "Cut": cut,
        "Drive": "R:",
        "ProviderID": provider,
        "DeviceObject": r"\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy7",
    }
    monkeypatch.setattr(native.sys, "platform", "win32")
    monkeypatch.setattr(native, "windows_record", lambda _cut: data)
    monkeypatch.setattr(native, "verify_exposure", lambda _drive, _device: None)
    assert native.snapshot_view(volume, shadow, cut).provider == provider
    with pytest.raises(ValueError, match="registered volume"):
        native.snapshot_view(str(uuid4()), shadow, cut)
    data["DeviceObject"] = str(tmp_path)
    with pytest.raises(ValueError, match="device"):
        native.snapshot_view(volume, shadow, cut)


def test_native_apfs_requires_mounted_snapshot_of_exact_volume(monkeypatch: pytest.MonkeyPatch) -> None:
    volume, shadow, cut = str(uuid4()), str(uuid4()), str(uuid4())
    inventory_result = {"AllDisksAndPartitions": [{"APFSVolumes": [{"VolumeUUID": volume, "MountedSnapshots": []}]}]}
    monkeypatch.setattr(native.sys, "platform", "darwin")
    monkeypatch.setattr(native, "diskutil", lambda *_args: inventory_result)
    with pytest.raises(ValueError, match="read-only"):
        native.snapshot_view(volume, shadow, cut)
