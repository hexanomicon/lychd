"""Validate local filesystem ancestry before desktop owner-only operations."""

from __future__ import annotations

import base64
import errno
import os
import stat
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from lychd.system.path_policy import physically_contains

_PRIVATE_DIRECTORY_MODE = 0o700


def overlaps(left: Path, right: Path) -> bool:
    """Compare physical directory ancestry, including aliases on case-insensitive volumes."""
    return physically_contains(left, right) or physically_contains(right, left)


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


def check_native_inputs(engine: Path, model: Path) -> None:
    """Verify canonical engine and GGUF paths. POSIX installations use a user- or root-owned shelf."""
    for path in (engine, model):
        if not path.is_absolute() or ".." in path.parts or (os.name == "nt" and path.drive.startswith("\\\\")):
            msg = f"Native runtime requires a canonical local path: {path}"
            raise ValueError(msg)
        for component in (*reversed(path.parents), path):
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                msg = f"Native runtime path is redirected: {component}"
                raise ValueError(msg)
            if os.name == "posix":
                _check_native_posix_mode(component, info, engine_path=path == engine)


def _check_native_posix_mode(component: Path, info: os.stat_result, *, engine_path: bool) -> None:
    if info.st_uid not in (0, os.getuid()):
        msg = f"Native input must be on a shelf owned by the desktop user or root: {component}"
        raise ValueError(msg)
    if not info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        return
    if stat.S_ISDIR(info.st_mode) and info.st_mode & stat.S_ISVTX:
        # Sticky directories permit only the trusted directory or entry owner to replace a binding.
        return
    if (
        engine_path
        and sys.platform == "darwin"
        and not info.st_mode & stat.S_IWOTH
        and (component.is_relative_to("/opt/homebrew") or component.is_relative_to("/usr/local"))
    ):
        import grp

        if info.st_gid == grp.getgrnam("admin").gr_gid:
            return
    msg = f"Native input path is group- or publicly writable: {component}"
    raise ValueError(msg)


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
        if sys.platform == "darwin":
            subprocess.run(["/bin/chmod", "-N", directory], check=True)  # noqa: S603 -- fixed macOS ACL operation.
            _verify_macos_directory_acl(directory)
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


def _verify_windows_acl(path: Path, *, security_descriptor: bytes | None = None) -> None:
    powershell = Path(os.environ["SYSTEMROOT"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    read_acl = (
        "$a=if([IO.Directory]::Exists($p)){[IO.Directory]::GetAccessControl($p)}else{[IO.File]::GetAccessControl($p)};"
        if security_descriptor is None
        else "$a=[Security.AccessControl.FileSecurity]::new();"
        "$a.SetSecurityDescriptorBinaryForm([Convert]::FromBase64String([Console]::In.ReadToEnd()),"
        "[Security.AccessControl.AccessControlSections]'Owner,Access');"
    )
    script = (
        "$ErrorActionPreference='Stop';$u=[Security.Principal.WindowsIdentity]::GetCurrent().User;"
        "$p=$env:LYCHD_PRIVATE_FILE;"
        f"{read_acl}"
        "if($a.GetOwner([Security.Principal.SecurityIdentifier]) -ne $u -or @($a.Access).Count -eq 0)"
        "{throw 'Unverified file owner or ACL'};"
        "foreach($r in $a.Access){$sid=$r.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value;"
        "if($sid -ne $u.Value -and $sid -ne 'S-1-3-4')"
        "{throw 'Unexpected file permissions'}}"
    )
    subprocess.run(  # noqa: S603 -- fixed script, path conveyed separately.
        [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, "LYCHD_PRIVATE_FILE": str(path)},
        input=base64.b64encode(security_descriptor) if security_descriptor is not None else None,
        check=True,
    )


def _windows_record_security_descriptor(fd: int) -> bytes:
    """Check the opened object's type and retrieve its owner and DACL."""
    if sys.platform != "win32":
        msg = "Windows file handles are required"
        raise OSError(msg)
    import ctypes
    import msvcrt
    from ctypes import wintypes

    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        msg = "Reactor record must be a regular file without a reparse point"
        raise ValueError(msg)
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    descriptor = ctypes.c_void_p()
    get_security = advapi.GetSecurityInfo
    get_security.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.DWORD, *([ctypes.POINTER(ctypes.c_void_p)] * 5)]
    get_security.restype = wintypes.DWORD
    # SE_FILE_OBJECT, OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION
    error = get_security(msvcrt.get_osfhandle(fd), 1, 5, None, None, None, None, ctypes.byref(descriptor))
    if error:
        raise ctypes.WinError(error)
    length = advapi.GetSecurityDescriptorLength
    length.argtypes = [ctypes.c_void_p]
    length.restype = wintypes.DWORD
    free = kernel.LocalFree
    free.argtypes = [ctypes.c_void_p]
    free.restype = ctypes.c_void_p
    try:
        return ctypes.string_at(descriptor, length(descriptor))
    finally:
        free(descriptor)


def open_windows_reactor_record(path: Path) -> int:
    """Return a non-inheritable read descriptor for a private record in the verified journal."""
    if sys.platform != "win32":
        msg = "Windows file handles are required"
        raise OSError(msg)
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create.restype = wintypes.HANDLE
    # GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_DELETE, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT.
    # The producer may retire its temporary hard link while the host reads the pinned object.
    handle = create(str(path), 0x80000000, 5, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_NOINHERIT)
    except BaseException:
        close = kernel.CloseHandle
        close.argtypes = [wintypes.HANDLE]
        close.restype = wintypes.BOOL
        close(handle)
        raise
    try:
        msvcrt.setmode(descriptor, os.O_BINARY)
        _verify_windows_acl(path, security_descriptor=_windows_record_security_descriptor(descriptor))
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _verify_macos_directory_acl(directory: Path) -> None:
    """Require Darwin to report an absent extended ACL on the opened directory."""
    import ctypes

    libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    libc.acl_get_fd.argtypes = [ctypes.c_int]
    libc.acl_get_fd.restype = ctypes.c_void_p
    libc.acl_free.argtypes = [ctypes.c_void_p]
    libc.acl_free.restype = ctypes.c_int
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        ctypes.set_errno(0)
        acl = libc.acl_get_fd(fd)
        if acl:
            libc.acl_free(acl)
            msg = f"Expected an owner-only directory without an extended ACL: {directory}"
            raise ValueError(msg)
        # Darwin's filesec_get_property reports ENOENT for the absent FILESEC_ACL property.
        if (error := ctypes.get_errno()) != errno.ENOENT:
            msg = f"Cannot verify the extended ACL on {directory} (errno {error})."
            raise ValueError(msg)
    finally:
        os.close(fd)


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
    elif sys.platform == "darwin":
        _verify_macos_directory_acl(directory)


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


def commit_file(source: Path, target: Path, *, replace: bool) -> None:
    """Request durable publication of a complete file on the same local filesystem."""
    if os.name == "nt":
        import ctypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        move = kernel.MoveFileExW
        move.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
        move.restype = ctypes.c_int
        # MOVEFILE_WRITE_THROUGH, plus MOVEFILE_REPLACE_EXISTING only for an owned replacement.
        if not move(str(source), str(target), 8 | int(replace)):
            raise ctypes.WinError(ctypes.get_last_error())
    else:
        source.replace(target)
        directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def publish_file(path: Path, content: bytes, *, replace: bool = False) -> None:
    """Publish complete content within the serialized desktop management operation."""
    check_path(path)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            if replace:
                verify_private_file(path)
            elif path.exists():
                raise FileExistsError(path)
            commit_file(temporary, path, replace=replace)
        finally:
            stream.close()
            temporary.unlink(missing_ok=True)
