"""Architecture tests for the lazy lifecycle compatibility surface."""

from __future__ import annotations

import subprocess
import sys


def test_leaf_model_import_does_not_boot_the_deletion_graph() -> None:
    """A model dependency must not eagerly import mutation subsystems."""
    script = """
import sys
from lychd.system.services.lifecycle.models import CreatedResources
assert CreatedResources is not None
assert "lychd.system.services.lifecycle.deletion" not in sys.modules
from lychd.system.services.lifecycle import LifecyclePlan
assert LifecyclePlan is not None
assert "lychd.system.services.lifecycle.deletion" not in sys.modules
"""

    subprocess.run(  # noqa: S603 - the interpreter and static script are repository-controlled
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
