"""Validate local filesystem ancestry before desktop owner-only operations."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

_PRIVATE_DIRECTORY_MODE = 0o700


def check_path(path: Path) -> None:
    """Refuse redirected paths and foreign-owned objects inside the user's home."""
    if not path.is_absolute() or ".." in path.parts:
        msg = f"Expected an absolute desktop path: {path}"
        raise ValueError(msg)
    if os.name == "nt" and path.anchor.startswith("\\\\"):
        msg = f"Desktop services require a local filesystem path: {path}"
        raise ValueError(msg)
    for component in (*reversed(path.parents), path):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            msg = f"Refusing redirected desktop path: {component}"
            raise ValueError(msg)
        if (
            os.name != "nt"
            and component.is_relative_to(Path.home())
            and (info.st_uid != os.getuid() or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH))
        ):
            msg = f"Refusing foreign-owned or shared-writable desktop path: {component}"
            raise ValueError(msg)
        if component == path and stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            msg = f"Refusing multiply linked desktop file: {component}"
            raise ValueError(msg)

    if os.name == "nt":
        _check_windows_ancestry(path)


def _check_windows_ancestry(path: Path) -> None:
    """Find cross-account mutation authority on existing directories within the user profile."""
    binary = Path(os.environ["SYSTEMROOT"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    script = """
$ErrorActionPreference='Stop'
$u=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$owners=@($u,'S-1-5-18','S-1-5-32-544')
# CREATOR OWNER and OWNER RIGHTS are ACE trustees, never acceptable object owners.
$trustees=$owners+@('S-1-3-0','S-1-3-4')
$homeDir=[IO.Path]::GetFullPath($env:USERPROFILE)
$p=[IO.Path]::GetFullPath($env:LYCHD_DESKTOP_CHECK_PATH)
while($p -and ($p -eq $homeDir -or $p.StartsWith($homeDir+'\\',[StringComparison]::OrdinalIgnoreCase))) {
    if([IO.Directory]::Exists($p) -or [IO.File]::Exists($p)) {
        $a=if([IO.Directory]::Exists($p)){[IO.Directory]::GetAccessControl($p)}else{[IO.File]::GetAccessControl($p)}
        if($owners -notcontains $a.GetOwner([Security.Principal.SecurityIdentifier]).Value) {throw 'Foreign path owner'}
        foreach($r in $a.Access) {
            if($r.AccessControlType -eq 'Allow' -and ([int]$r.FileSystemRights -band 0xD0156) -and
               $trustees -notcontains $r.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value) {
                $sid=$r.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
                throw "Desktop path writable by another account: $p; SID=$sid; rights=$($r.FileSystemRights); propagation=$($r.PropagationFlags)"
            }
        }
    }
    $p=[IO.Path]::GetDirectoryName($p)
}
"""
    subprocess.run(  # noqa: S603 -- fixed command and path provided separately.
        [binary, "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, "LYCHD_DESKTOP_CHECK_PATH": str(path)},
        check=True,
    )


def private_directory(directory: Path) -> None:
    """Ensure this directory is owned and accessible only by the current user."""
    check_path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        if directory.stat().st_uid != os.getuid():
            msg = f"Refusing foreign-owned private directory: {directory}"
            raise ValueError(msg)
        directory.chmod(0o700)
        return
    powershell = Path(os.environ["SYSTEMROOT"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    script = (
        "$ErrorActionPreference='Stop';"
        "$u=[Security.Principal.WindowsIdentity]::GetCurrent().User;"
        "$p=$env:LYCHD_PRIVATE_DIR;"
        "$acl=[IO.Directory]::GetAccessControl($p);"
        "if($acl.GetOwner([Security.Principal.SecurityIdentifier]) -ne $u){throw 'Foreign directory owner'};"
        "$acl.SetAccessRuleProtection($true,$false);"
        "foreach($r in @($acl.Access)){$acl.RemoveAccessRuleSpecific($r)};"
        "$rule=[Security.AccessControl.FileSystemAccessRule]::new($u,'FullControl',"
        "'ContainerInherit,ObjectInherit','None','Allow');"
        "$acl.AddAccessRule($rule);[IO.Directory]::SetAccessControl($p,$acl);"
        "$result=[IO.Directory]::GetAccessControl($p);"
        "if(!$result.AreAccessRulesProtected -or @($result.Access).Count -ne 1 -or "
        "$result.Access[0].IdentityReference.Translate([Security.Principal.SecurityIdentifier]) -ne $u)"
        "{throw 'Directory ACL verification failed'}"
    )
    subprocess.run(  # noqa: S603 -- fixed script, path conveyed separately.
        [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, "LYCHD_PRIVATE_DIR": str(directory)},
        check=True,
    )


def _verify_windows_acl(path: Path) -> None:
    powershell = Path(os.environ["SYSTEMROOT"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    script = (
        "$ErrorActionPreference='Stop';$u=[Security.Principal.WindowsIdentity]::GetCurrent().User;"
        "$p=$env:LYCHD_PRIVATE_FILE;"
        "$a=if([IO.Directory]::Exists($p)){[IO.Directory]::GetAccessControl($p)}else{[IO.File]::GetAccessControl($p)};"
        "if($a.GetOwner([Security.Principal.SecurityIdentifier]) -ne $u -or @($a.Access).Count -eq 0)"
        "{throw 'Unverified file owner or ACL'};"
        "foreach($r in $a.Access){$sid=$r.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value;"
        "if($sid -ne $u.Value -and $sid -ne 'S-1-3-4')"
        "{throw 'Unexpected file permissions'}}"
    )
    subprocess.run(  # noqa: S603 -- fixed script, path conveyed separately.
        [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, "LYCHD_PRIVATE_FILE": str(path)},
        check=True,
    )


def verify_private_directory(directory: Path) -> None:
    """Validate an existing operator-selected directory without changing permissions."""
    check_path(directory)
    if not directory.is_dir():
        msg = f"Native journal path must be a directory: {directory}"
        raise ValueError(msg)
    if os.name == "nt":
        _verify_windows_acl(directory)
    elif directory.stat().st_uid != os.getuid() or stat.S_IMODE(directory.stat().st_mode) != _PRIVATE_DIRECTORY_MODE:
        msg = f"Native journal requires an owner-only directory: {directory}"
        raise ValueError(msg)


def verify_private_file(path: Path) -> None:
    """Verify an owner-only credential file without modifying the recovery media."""
    check_path(path)
    if not path.is_file():
        msg = f"Expected a regular credential file: {path}"
        raise ValueError(msg)
    info = path.stat()
    if os.name == "nt":
        _verify_windows_acl(path)
    elif info.st_uid != os.getuid() or info.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        msg = f"Expected an owner-only credential file: {path}"
        raise ValueError(msg)


def private_file(path: Path) -> None:
    """Check file ownership and restrict access before reading credentials."""
    check_path(path)
    if os.name == "nt":
        _verify_windows_acl(path)
    elif path.stat().st_uid != os.getuid():
        msg = f"Refusing foreign-owned credential file: {path}"
        raise ValueError(msg)
    else:
        path.chmod(0o600)


def publish_file(path: Path, content: bytes) -> None:
    """Publish complete content within the serialized desktop management operation."""
    check_path(path)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            if path.exists():
                raise FileExistsError(path)
            temporary.replace(path)
        finally:
            stream.close()
            temporary.unlink(missing_ok=True)
