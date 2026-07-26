"""The Altar's static Svelte shell and versioned semantic API controllers."""

from __future__ import annotations

from lychd.interface.web.altar import AltarController
from lychd.interface.web.bridge import BridgeController
from lychd.interface.web.loom import LoomController
from lychd.interface.web.nexus import NexusController

__all__ = ["AltarController", "BridgeController", "LoomController", "NexusController"]
