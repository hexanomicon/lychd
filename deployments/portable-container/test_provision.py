# ruff: noqa: INP001, PT009, PT027 -- deployment checks use the standard library alone
"""Exercise initial provisioning, retries, and mismatched-volume recovery."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from provision import ROLES, provision


class CredentialTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        for name in ("seed", *ROLES):
            (self.root / name).mkdir()

    def test_repeated_and_interrupted_provisioning(self) -> None:
        provision(self.root)
        values = {(self.root / role / "value").read_bytes() for role in ROLES}
        self.assertEqual(len(values), len(ROLES))
        path = self.root / "runtime" / "value"
        original = path.read_bytes()
        path.unlink()
        provision(self.root)
        provision(self.root)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(path.stat().st_mode & 0o777, 0o444)
        self.assertEqual((self.root / "seed/key").stat().st_mode & 0o777, 0o400)

    def test_missing_seed_and_mismatch_preserve_existing_authority(self) -> None:
        provision(self.root)
        missing = self.root / "access/value"
        missing.unlink()
        secret = self.root / "app/value"
        secret.unlink()
        secret.write_text("different")
        with self.assertRaisesRegex(ValueError, "differs"):
            provision(self.root)
        self.assertFalse(missing.exists())
        (self.root / "seed/key").unlink()
        with self.assertRaisesRegex(ValueError, "original seed"):
            provision(self.root)
        self.assertEqual(secret.read_text(), "different")
