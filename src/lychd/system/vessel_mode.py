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


def require_native_user() -> None:
    """Refuse native lifecycle effects outside the selected ordinary-user deployment."""
    if vessel_mode() != "native":
        msg = "Native Vessel requires LYCHD_VESSEL_MODE=native on this host."
        raise ValueError(msg)
    if os.name == "posix" and os.geteuid() == 0:
        msg = "Run native Vessel as the ordinary installation user."
        raise ValueError(msg)
