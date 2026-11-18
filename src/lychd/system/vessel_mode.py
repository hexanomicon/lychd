"""Choose Vessel placement before loading deployment-specific paths or settings."""

from __future__ import annotations

import os
import sys
from typing import Literal


def vessel_mode() -> Literal["container", "native", "unsupported"]:
    """Resolve an explicit operator choice or the established default for this host."""
    selected = os.environ.get("LYCHD_VESSEL_MODE", "auto")
    if selected not in {"auto", "container", "native"}:
        msg = "LYCHD_VESSEL_MODE must be auto, container or native."
        raise ValueError(msg)
    if sys.platform not in {"linux", "darwin", "win32"}:
        return "unsupported"
    if selected == "native" or (selected == "auto" and sys.platform != "linux"):
        return "native"
    return "container"


def _windows_process_elevated() -> bool:
    """Read TokenElevation from the primary process token before native effects."""
    import ctypes

    # Windows SDK GetCurrentProcessToken() expands to this query-only pseudo-handle.
    process_token = ctypes.c_void_p(-4)
    token_elevation = 20
    elevated = ctypes.c_uint32()
    returned = ctypes.c_uint32()
    try:
        query = ctypes.WinDLL("advapi32").GetTokenInformation
        query.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
        ]
        query.restype = ctypes.c_int
        observed = query(
            process_token, token_elevation, ctypes.byref(elevated), ctypes.sizeof(elevated), ctypes.byref(returned)
        )
    except (AttributeError, OSError):
        observed = False
    if not observed or returned.value != ctypes.sizeof(elevated):
        msg = "Cannot verify the elevation of the native Vessel process token."
        raise ValueError(msg)
    return bool(elevated.value)


def require_native_user() -> None:
    """Refuse native lifecycle effects outside the selected ordinary-user deployment."""
    if vessel_mode() != "native":
        msg = "Native Vessel requires LYCHD_VESSEL_MODE=native on this host."
        raise ValueError(msg)
    elevated = _windows_process_elevated() if os.name == "nt" else os.geteuid() == 0
    if elevated:
        msg = "Run native Vessel as the ordinary installation user."
        raise ValueError(msg)
