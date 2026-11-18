"""OS custody for one generated personal desktop credential, bound to its installation path."""

from __future__ import annotations

import base64
import ctypes
import hashlib
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

PREFIX = "lychd-desktop-vault:"
_SERVICE = b"org.lychd.desktop.credentials.v1"


def _dpapi(path: Path, value: bytes, *, seal: bool) -> bytes:
    """Use the current user's DPAPI profile. Input and output use private pipes."""
    binary = Path(os.environ["SYSTEMROOT"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    operation = "Protect" if seal else "Unprotect"
    script = (
        "$ErrorActionPreference='Stop';Add-Type -AssemblyName System.Security;"
        "$data=[Convert]::FromBase64String([Console]::ReadLine());"
        "$entropy=[Convert]::FromBase64String([Console]::ReadLine());"
        f"$out=[Security.Cryptography.ProtectedData]::{operation}($data,$entropy,'CurrentUser');"
        "[Console]::Write([Convert]::ToBase64String($out))"
    )
    context = b"org.lychd.desktop.v1:" + os.path.normcase(str(path)).encode("utf-8")
    request = base64.b64encode(value) + b"\n" + base64.b64encode(context) + b"\n"
    result = subprocess.run(  # noqa: S603 -- fixed Windows system binary and script, secrets supplied on stdin
        [binary, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
        input=request,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode:
        msg = "Current-user DPAPI could not access the desktop credential."
        raise ValueError(msg)
    return base64.b64decode(result.stdout, validate=True)


def _mac_keychain(path: Path, token: str, value: bytes | None = None) -> bytes:
    """Create or read a generic password without prompting a background login session."""
    lib = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
    account = hashlib.sha256(os.fsencode(path)).hexdigest().encode("ascii") + b":" + token.encode("ascii")
    key = (None, len(_SERVICE), _SERVICE, len(account), account)
    prefix = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p]
    lib.SecKeychainAddGenericPassword.argtypes = [*prefix, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_void_p]
    lib.SecKeychainFindGenericPassword.argtypes = [
        *prefix,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
    ]
    lib.SecKeychainItemFreeContent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    allowed = ctypes.c_ubyte()
    if lib.SecKeychainGetUserInteractionAllowed(ctypes.byref(allowed)) or lib.SecKeychainSetUserInteractionAllowed(0):
        msg = "Unable to select noninteractive Keychain access."
        raise ValueError(msg)
    try:
        if value is not None:
            status = lib.SecKeychainAddGenericPassword(*key, len(value), value, None)
            if status not in {0, -25299}:  # errSecDuplicateItem is reconciled by the readback below.
                msg = f"Cannot store the desktop credential in the login Keychain (OSStatus {status})."
                raise ValueError(msg)
        size = ctypes.c_uint32()
        pointer = ctypes.c_void_p()
        status = lib.SecKeychainFindGenericPassword(*key, ctypes.byref(size), ctypes.byref(pointer), None)
        if status:
            msg = f"Desktop Keychain item is unavailable (OSStatus {status}). Unlock the owning Keychain."
            raise ValueError(msg)
        try:
            return ctypes.string_at(pointer, size.value)
        finally:
            lib.SecKeychainItemFreeContent(None, pointer)
    finally:
        lib.SecKeychainSetUserInteractionAllowed(allowed.value)


def seal_credential(path: Path, value: bytes) -> bytes:
    """Read back every sealed credential before the caller replaces a working file."""
    if sys.platform == "darwin":
        # Generated passwords have 384 bits of entropy. A retry addresses the same Keychain item.
        token = hashlib.sha256(value).hexdigest()
        recovered = _mac_keychain(path, token, value)
        record = f"{PREFIX}1:keychain:{token}"
    elif sys.platform == "win32":
        ciphertext = _dpapi(path, value, seal=True)
        recovered = _dpapi(path, ciphertext, seal=False)
        record = f"{PREFIX}1:dpapi:{base64.b64encode(ciphertext).decode('ascii')}"
    else:
        msg = "The desktop credential vault requires macOS or Windows."
        raise ValueError(msg)
    if not secrets.compare_digest(value, recovered):
        msg = "The OS vault did not return the original credential."
        raise ValueError(msg)
    return record.encode("ascii")


def open_credential(path: Path, record: str) -> str:
    """Resolve a versioned local vault record or fail closed under the wrong OS or account."""
    if sys.platform == "darwin" and record.startswith(f"{PREFIX}1:keychain:"):
        token = record.removeprefix(f"{PREFIX}1:keychain:")
        if re.fullmatch("[a-f0-9]{64}", token):
            return _mac_keychain(path, token).decode("ascii")
    elif sys.platform == "win32" and record.startswith(f"{PREFIX}1:dpapi:"):
        data = base64.b64decode(record.removeprefix(f"{PREFIX}1:dpapi:"), validate=True)
        return _dpapi(path, data, seal=False).decode("ascii")
    msg = "Unrecognized or incompatible desktop credential vault record."
    raise ValueError(msg)
