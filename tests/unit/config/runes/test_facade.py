"""Architecture tests for the Rune type facade."""

from __future__ import annotations

import subprocess
import sys


def test_rune_type_import_does_not_boot_the_effectful_writer() -> None:
    """Importing Rune types must not import the Codex filesystem writer."""
    script = """
import sys
from lychd.config.runes import RuneConfig
assert RuneConfig is not None
assert "lychd.config.runes.writer" not in sys.modules
assert "lychd.system.services.publication" not in sys.modules
from lychd.config.runes import ConfigLoader
assert ConfigLoader is not None
assert "lychd.config.runes.writer" not in sys.modules
assert "lychd.system.services.publication" not in sys.modules
from lychd.config.runes import ConfigWriter
assert ConfigWriter is not None
assert "lychd.config.runes.writer" in sys.modules
assert "lychd.system.services.publication" in sys.modules
"""

    subprocess.run(  # noqa: S603 - the interpreter and static script are repository-controlled
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
