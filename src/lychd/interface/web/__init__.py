"""The Altar's static Svelte shell and versioned semantic API controllers."""

from __future__ import annotations

from lychd.interface.web.altar import AltarController
from lychd.interface.web.archive import ArchiveController
from lychd.interface.web.archive_derivation import ArchiveDerivationController
from lychd.interface.web.archive_semantic import ArchiveSemanticController
from lychd.interface.web.atlas import AtlasController
from lychd.interface.web.bridge import BridgeController
from lychd.interface.web.canvas import CanvasController
from lychd.interface.web.dictation import DictationController
from lychd.interface.web.dictation_lexicon import DictationLexiconController
from lychd.interface.web.loom import LoomController
from lychd.interface.web.naming import NamingController
from lychd.interface.web.nexus import NexusController
from lychd.interface.web.orb import OrbController

__all__ = [
    "AltarController",
    "ArchiveController",
    "ArchiveDerivationController",
    "ArchiveSemanticController",
    "AtlasController",
    "BridgeController",
    "CanvasController",
    "DictationController",
    "DictationLexiconController",
    "LoomController",
    "NamingController",
    "NexusController",
    "OrbController",
]
