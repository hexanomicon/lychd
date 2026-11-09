"""Controller-only refusal tests; these are not a live Ansible/VPS receipt."""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

GUARD_PATH = Path(__file__).parents[1] / "roles/lychd_source/files/source_guard.py"
SPEC = importlib.util.spec_from_file_location("source_guard", GUARD_PATH)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)
REVISION = "a" * 40
CHECKSUM = "b" * 64
PYTHON = "3.14.8"


class SourceGuardTests(unittest.TestCase):
    """Exercise preserved-environment and ownership refusal independently of SSH."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "home"
        self.home.mkdir(mode=0o700)
        self.checkout = self.home / "src" / f"lychd-{REVISION}"
        # /tmp is intentionally shared; skip only ancestor admission in the
        # checkout tests. The independent path tests below exercise lstat refusal.
        self.paths = patch.object(guard, "safe_path")
        self.paths.start()
        self.addCleanup(self.paths.stop)

    def inspect(self):
        return guard.inspect_source(self.home, REVISION, CHECKSUM, PYTHON, os.getuid())

    def checkout_receipt(self, complete=False):
        (self.checkout / ".git").mkdir(parents=True)
        receipt = {"revision": REVISION, "uv_sha256": CHECKSUM, "python": PYTHON, "complete": complete}
        (self.checkout / ".git/lychd-source.json").write_text(json.dumps(receipt))
        responses = {
            ("rev-parse", "--show-toplevel"): str(self.checkout),
            ("rev-parse", "HEAD"): REVISION,
            ("config", "--get", "remote.origin.url"): "https://github.com/hexanomicon/lychd.git",
            ("status", "--porcelain", "--untracked-files=all"): "",
            ("ls-files", "--others", "--ignored", "--exclude-standard"): "",
        }
        self.git = patch.object(guard, "git", side_effect=lambda path, *args: responses[args])
        self.git.start()
        self.addCleanup(self.git.stop)
        return responses

    def test_absent_source_is_the_only_new_checkout_shape(self):
        self.assertEqual(self.inspect(), {"exists": False, "complete": False})

    def test_unreceipted_workspace_refuses(self):
        (self.checkout / ".git").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "unreceipted"):
            self.inspect()

    def test_dirty_checkout_refuses(self):
        responses = self.checkout_receipt()
        responses[("status", "--porcelain", "--untracked-files=all")] = " M pyproject.toml"
        with self.assertRaisesRegex(ValueError, "dirty"):
            self.inspect()

    def test_wrong_source_sha_refuses(self):
        responses = self.checkout_receipt()
        responses[("rev-parse", "HEAD")] = "c" * 40
        with self.assertRaisesRegex(ValueError, "source SHA"):
            self.inspect()

    def test_private_ignored_material_refuses(self):
        responses = self.checkout_receipt()
        responses[("ls-files", "--others", "--ignored", "--exclude-standard")] = "private/customer.md"
        with self.assertRaisesRegex(ValueError, "foreign ignored"):
            self.inspect()

    def test_partial_environment_refuses_without_repair(self):
        self.checkout_receipt()
        (self.checkout / ".venv").mkdir()
        with self.assertRaisesRegex(ValueError, "partial environment"):
            self.inspect()

    def test_complete_environment_is_observed_and_not_resynced(self):
        self.checkout_receipt(complete=True)
        (self.checkout / ".venv/bin").mkdir(parents=True)
        (self.checkout / ".venv/bin/lychd").write_text("readonly CLI witness")
        self.assertEqual(self.inspect(), {"exists": True, "complete": True})

    def test_uv_empty_environment_lock_is_admitted(self):
        self.checkout_receipt(complete=True)
        (self.checkout / ".venv/bin").mkdir(parents=True)
        (self.checkout / ".venv/bin/lychd").write_text("readonly CLI witness")
        lock = self.checkout / ".venv/.lock"
        lock.touch()
        lock.chmod(0o666)
        self.assertEqual(self.inspect(), {"exists": True, "complete": True})

    def test_nonempty_or_other_shared_writable_file_refuses(self):
        self.checkout_receipt(complete=True)
        (self.checkout / ".venv/bin").mkdir(parents=True)
        (self.checkout / ".venv/bin/lychd").write_text("readonly CLI witness")
        lock = self.checkout / ".venv/.lock"
        lock.write_text("payload")
        lock.chmod(0o666)
        with self.assertRaisesRegex(ValueError, "shared-writable"):
            self.inspect()
        lock.write_text("")
        other = self.checkout / ".venv/bin/other"
        other.touch()
        other.chmod(0o666)
        with self.assertRaisesRegex(ValueError, "shared-writable"):
            self.inspect()

    def test_source_symlink_refuses(self):
        self.checkout_receipt()
        (self.checkout / "foreign").symlink_to(self.home)
        with self.assertRaisesRegex(ValueError, "source symlink"):
            self.inspect()

    def test_foreign_inode_refuses(self):
        self.checkout_receipt()
        with self.assertRaisesRegex(ValueError, "foreign inode"):
            guard.inspect_source(self.home, REVISION, CHECKSUM, PYTHON, os.getuid() + 1)

    def test_moving_revision_refuses(self):
        with self.assertRaisesRegex(ValueError, "exact source SHA"):
            guard.inspect_source(self.home, "main", CHECKSUM, PYTHON, os.getuid())

    def test_shared_parent_is_refused(self):
        self.paths.stop()
        original = Path.lstat

        def root_mapping(path):
            info = list(original(path))
            if path in (Path("/"), Path("/tmp")):
                info[4] = 0  # The sandbox can map real root to uid 65534.
            return os.stat_result(info)

        with patch.object(Path, "lstat", root_mapping):
            with self.assertRaisesRegex(ValueError, "writable shared path"):
                guard.safe_path(self.home, os.getuid())

    def test_symlink_ancestor_is_refused(self):
        link = self.home / "link"
        link.symlink_to(self.home, target_is_directory=True)
        self.paths.stop()
        # Test below /tmp through a lexical fixture whose parent observations are
        # immutable, so the symlink itself is the decisive failing component.
        original = Path.lstat

        def admitted_parent(path):
            info = list(original(path))
            if path in (Path("/"), Path("/tmp")):
                info[4] = 0
            if path in (Path("/tmp"), Path(self.temporary.name)):
                info[0] = 0o40700
            return os.stat_result(info)

        with patch.object(Path, "lstat", admitted_parent):
            with self.assertRaisesRegex(ValueError, "symlink refused"):
                guard.safe_path(link / "child", os.getuid())


if __name__ == "__main__":
    unittest.main()
