"""Resolve a mounted APFS snapshot or a VSS shadow through current OS inventory."""

from __future__ import annotations

import ctypes
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from lychd.system.desktop.volume_storage import diskutil, powershell


@dataclass(frozen=True)
class Snapshot:
    root: Path
    snapshot: str
    provider: str


def snapshot_view(identity: str, identifier: str, cut: str) -> Snapshot:
    """Accept only a native snapshot UUID on the registered live volume."""
    identifier = str(UUID(identifier))
    if sys.platform == "darwin":
        devices = diskutil("list", "-plist")["AllDisksAndPartitions"]
        for device in devices:
            for volume in device.get("APFSVolumes", []):
                if volume.get("VolumeUUID", "").lower() == identity:
                    for view in volume.get("MountedSnapshots", []):
                        if view["SnapshotUUID"].lower() == identifier:
                            root = Path(view["SnapshotMountPoint"])
                            if (
                                root.is_absolute()
                                and root.is_mount()
                                and root == root.resolve(strict=True)
                                and os.statvfs(root).f_flag & os.ST_RDONLY
                            ):
                                return Snapshot(root, identifier, "apfs")
        msg = "Mount the specified APFS snapshot read-only on its registered volume."
        raise ValueError(msg)
    if sys.platform != "win32":
        msg = "Volume capture requires a native macOS or Windows host."
        raise ValueError(msg)
    data = windows_record(cut)
    device = data["DeviceObject"]
    drive = data["Drive"]
    if (
        str(UUID(data["Cut"])) != cut
        or data["VolumeName"].casefold() != ("\\\\?\\Volume{" + identity + "}\\").casefold()
        or str(UUID(data["ID"])) != identifier
        or not re.fullmatch(r"[D-Z]:", drive)
        or not re.fullmatch(r"\\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy[1-9][0-9]*", device, re.IGNORECASE)
    ):
        msg = "The VSS device does not belong to this cut, snapshot and registered volume."
        raise ValueError(msg)
    verify_exposure(drive, device)
    return Snapshot(Path(drive + "\\"), identifier, str(UUID(data["ProviderID"])))


def windows_record(cut: str) -> dict[str, str]:
    """Read OS requestor inventory from the protected, per-cut Program Files directory."""
    return json.loads(
        powershell(
            """
$p=[Environment]::GetFolderPath('ProgramFiles')
$d=[IO.Path]::Combine($p,('LychD-Volume-'+$env:LYCHD_CUT))
$f=[IO.Path]::Combine($d,'snapshot.json')
$trusted=@('S-1-5-18','S-1-5-32-544','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
foreach($item in @($p,$d,$f)) {
  if([IO.File]::GetAttributes($item) -band [IO.FileAttributes]::ReparsePoint){throw 'Redirected requestor receipt'}
  $acl=if([IO.Directory]::Exists($item)){[IO.Directory]::GetAccessControl($item)}else{[IO.File]::GetAccessControl($item)}
  if($trusted -notcontains $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value){throw 'Foreign requestor receipt owner'}
  foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
    $sid=$ace.IdentityReference.Value
    if($ace.AccessControlType -eq 'Allow' -and ([int]$ace.FileSystemRights -band 0xD0156) -and
       !($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -and $trusted -notcontains $sid){throw "Writable requestor receipt: $item; $sid; $($ace.FileSystemRights)"}
  }
}
[IO.File]::ReadAllText($f)
""",
            LYCHD_CUT=str(UUID(cut)),
        )
    )


def verify_exposure(drive: str, device: str) -> None:
    """Verify the local, read-only drive mapping using ordinary-user kernel calls."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    mapped = ctypes.create_unicode_buffer(32768)
    flags = ctypes.c_ulong()
    if (
        not kernel.QueryDosDeviceW(drive, mapped, len(mapped))
        or mapped.value.casefold() != device.removeprefix("\\\\?\\GLOBALROOT").casefold()
        or not kernel.GetVolumeInformationW(drive + "\\", None, 0, None, None, ctypes.byref(flags), None, 0)
        or not flags.value & 0x80000
    ):  # FILE_READ_ONLY_VOLUME
        msg = "The exposed drive no longer maps to the registered read-only VSS shadow."
        raise ValueError(msg)
