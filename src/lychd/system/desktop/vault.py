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


class VaultUnavailableError(ValueError):
    """An intact vault envelope cannot be opened in the current OS or user profile."""


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
        raise VaultUnavailableError(msg)
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
            raise VaultUnavailableError(msg)
        try:
            return ctypes.string_at(pointer, size.value)
        finally:
            lib.SecKeychainItemFreeContent(None, pointer)
    finally:
        lib.SecKeychainSetUserInteractionAllowed(allowed.value)


def _verifier(path: Path, value: bytes) -> str:
    """Bind a high-entropy generated credential to its purpose across account and path changes."""
    if not re.fullmatch(rb"[A-Za-z0-9_-]{64}", value):
        msg = "Expected a high-entropy generated desktop recovery credential."
        raise ValueError(msg)
    return hashlib.sha256(b"lychd-vault-recovery-v2\0" + path.name.encode("ascii") + b"\0" + value).hexdigest()


def matches_recovery(path: Path, record: str, value: bytes) -> bool:
    """Only a v2 envelope can verify a portable backup while its original vault is unavailable."""
    _, _, verifier = _envelope(record)
    return verifier is not None and secrets.compare_digest(verifier, _verifier(path, value))


def seal_credential(path: Path, value: bytes) -> bytes:
    """Read back every sealed credential before the caller replaces a working file."""
    verifier = _verifier(path, value)
    if sys.platform == "darwin":
        recovered = _mac_keychain(path, verifier, value)
        record = f"{PREFIX}2:keychain:{verifier}"
    elif sys.platform == "win32":
        ciphertext = _dpapi(path, value, seal=True)
        recovered = _dpapi(path, ciphertext, seal=False)
        record = f"{PREFIX}2:dpapi:{verifier}:{base64.b64encode(ciphertext).decode('ascii')}"
    else:
        msg = "The desktop credential vault requires macOS or Windows."
        raise ValueError(msg)
    if not secrets.compare_digest(value, recovered):
        msg = "The OS vault did not return the original credential."
        raise ValueError(msg)
    return record.encode("ascii")


def _envelope(record: str) -> tuple[str, str, str | None]:
    if not record.startswith(PREFIX):
        msg = "Unrecognized desktop credential vault record."
        raise ValueError(msg)
    fields = record.removeprefix(PREFIX).split(":")
    verifier = None
    match fields:
        case ["1", "keychain", token]:
            kind, payload = "keychain", token
        case ["2", "keychain", token]:
            kind, payload, verifier = "keychain", token, token
        case ["1", "dpapi", ciphertext]:
            kind, payload = "dpapi", ciphertext
        case ["2", "dpapi", token, ciphertext]:
            kind, payload, verifier = "dpapi", ciphertext, token
        case _:
            msg = "Unrecognized desktop credential vault record."
            raise ValueError(msg)
    if verifier is not None and not re.fullmatch("[a-f0-9]{64}", verifier):
        msg = "Invalid vault recovery verifier."
        raise ValueError(msg)
    return kind, payload, verifier


def open_credential(path: Path, record: str) -> str:
    """Read both envelope generations and validate v2's portable, purpose-specific verifier."""
    kind, payload, verifier = _envelope(record)
    if kind == "keychain":
        if not re.fullmatch("[a-f0-9]{64}", payload):
            msg = "Invalid desktop Keychain item reference."
            raise ValueError(msg)
        if sys.platform != "darwin":
            msg = "Desktop Keychain item is unavailable on this platform."
            raise VaultUnavailableError(msg)
        value = _mac_keychain(path, payload)
    else:
        data = base64.b64decode(payload, validate=True)
        if not data:
            msg = "Empty desktop DPAPI envelope."
            raise ValueError(msg)
        if sys.platform != "win32":
            msg = "Current-user DPAPI is unavailable on this platform."
            raise VaultUnavailableError(msg)
        value = _dpapi(path, data, seal=False)
    if verifier is not None and not secrets.compare_digest(verifier, _verifier(path, value)):
        msg = "The OS vault returned a credential with a different recovery verifier."
        raise ValueError(msg)
    return value.decode("ascii")
