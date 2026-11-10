"""Workstation filesystem refusal and convergence oracles on disposable fixtures only."""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PATH = Path(__file__).parents[1] / "files/user_config.py"
SPEC = importlib.util.spec_from_file_location("workstation", PATH)
workstation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workstation)


class FilesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.uid = os.geteuid()

        # Sandbox ancestors are remapped to nobody. Exercise fixture traversal from an
        # already opened trusted root; ancestor ownership is tested independently.
        def fixture_root(path, uid):
            fd = os.open(path, workstation.DIRECTORY_FLAGS)
            try:
                workstation.safe_directory(fd, uid)
            except BaseException:
                os.close(fd)
                raise
            return fd

        self.root_patch = patch.object(workstation, "open_root", side_effect=fixture_root)
        self.root_patch.start()
        self.files = {".config/fish/conf.d/baseline.fish": workstation.MARKER + "echo fixture\n"}

    def tearDown(self):
        self.root_patch.stop()
        self.temporary.cleanup()

    def run_files(self, mode, files=None, policy=False):
        return workstation.managed_files(
            str(self.root),
            self.uid,
            self.files if files is None else files,
            mode,
            policy=policy,
        )

    def test_check_is_read_only_then_first_and_second_apply(self):
        self.assertEqual(self.run_files("plan")["changed"], list(self.files))
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(self.run_files("apply")["changed"], list(self.files))
        self.assertEqual(self.run_files("apply")["changed"], [])
        self.assertEqual(self.run_files("verify")["changed"], [])
        self.assertEqual((self.root / next(iter(self.files))).stat().st_mode & 0o777, 0o600)

    def test_verify_missing_does_not_create(self):
        with self.assertRaisesRegex(workstation.Refusal, "Missing"):
            self.run_files("verify")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_preserves_foreign_content_before_any_file_creation(self):
        existing = self.root / "foreign"
        existing.write_text("personal settings\n")
        files = {"new/first": workstation.MARKER, "foreign": workstation.MARKER}
        for mode in ("plan", "apply", "verify"):
            with (
                self.subTest(mode=mode),
                self.assertRaisesRegex(workstation.Refusal, "foreign"),
            ):
                self.run_files(mode, files)
            self.assertFalse((self.root / "new").exists())
            self.assertEqual(existing.read_text(), "personal settings\n")

    def test_owned_fragment_can_update_without_touching_personal_config(self):
        self.run_files("apply")
        personal = self.root / ".config/fish/config.fish"
        personal.write_text("# my configuration\n")
        updated = {next(iter(self.files)): workstation.MARKER + "echo updated\n"}
        self.assertEqual(self.run_files("apply", updated)["changed"], list(updated))
        self.assertEqual(personal.read_text(), "# my configuration\n")

    def test_refuses_symlink_directory_and_leaf(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / ".config").symlink_to(outside, target_is_directory=True)
        for mode in ("plan", "apply"):
            with self.subTest(mode=mode), self.assertRaises(OSError):
                self.run_files(mode)
        self.assertEqual(list(outside.iterdir()), [])
        (self.root / ".config").unlink()
        target = self.root / "target"
        target.write_text("preserve")
        (self.root / "leaf").symlink_to(target)
        with self.assertRaises(OSError):
            self.run_files("apply", {"leaf": workstation.MARKER})
        self.assertEqual(target.read_text(), "preserve")

    def test_refuses_hardlinks_fifo_and_group_writable_parent(self):
        target = self.root / "target"
        target.write_text(workstation.MARKER)
        os.link(target, self.root / "hardlink")
        with self.assertRaises(workstation.Refusal):
            self.run_files("apply", {"hardlink": workstation.MARKER})
        os.mkfifo(self.root / "fifo")
        with self.assertRaises(workstation.Refusal):
            self.run_files("plan", {"fifo": workstation.MARKER})
        (self.root / ".config").mkdir(mode=0o700)
        (self.root / ".config").chmod(0o770)
        with self.assertRaisesRegex(workstation.Refusal, "write access"):
            self.run_files("apply")

    def test_refuses_unsafe_names_and_foreign_uid(self):
        for name in ("../outside", "/absolute", "a/../b", "a//b"):
            with self.subTest(name=name), self.assertRaises(workstation.Refusal):
                self.run_files("apply", {name: workstation.MARKER})
        with self.assertRaises(workstation.Refusal):
            workstation.managed_files(str(self.root), self.uid + 1, self.files, "apply")

    def test_policy_exact_preservation_conflict_and_mode_refusal(self):
        files = {"firefox/policies/policies.json": json.dumps(workstation.POLICY, indent=2) + "\n"}
        self.assertEqual(self.run_files("apply", files, policy=True)["changed"], list(files))
        self.assertEqual(self.run_files("apply", files, policy=True)["changed"], [])
        policy = self.root / next(iter(files))
        policy.write_text('{"policies": {"DisableTelemetry": true}}\n')
        with self.assertRaisesRegex(workstation.Refusal, "foreign"):
            self.run_files("apply", files, policy=True)
        self.assertIn("DisableTelemetry", policy.read_text())
        policy.write_text(next(iter(files.values())))
        policy.chmod(0o600)
        with self.assertRaisesRegex(workstation.Refusal, "mode differs"):
            self.run_files("plan", files, policy=True)


class IdentityTests(unittest.TestCase):
    def test_ancestor_ownership_and_sticky_exception(self):
        for owner, mode, accepted in (
            (0, 0o755, True),
            (1000, 0o700, True),
            (65534, 0o755, False),
            (0, 0o777, False),
            (0, 0o1777, True),
            (1000, 0o1777, False),
        ):
            with (
                self.subTest(owner=owner, mode=mode),
                patch.object(workstation.os, "fstat", return_value=SimpleNamespace(st_uid=owner, st_mode=mode)),
            ):
                if accepted:
                    workstation.safe_directory(3, 1000, ancestor=True)
                else:
                    with self.assertRaises(workstation.Refusal):
                        workstation.safe_directory(3, 1000, ancestor=True)

    def test_root_missing_and_invalid_users_refused(self):
        for name in ("", "root; id", "../user", 10):
            with self.subTest(name=name), self.assertRaises(workstation.Refusal):
                workstation.account(name)
        with patch.object(workstation.pwd, "getpwnam", side_effect=KeyError):
            with self.assertRaisesRegex(workstation.Refusal, "does not exist"):
                workstation.account("missing")
        with patch.object(
            workstation.pwd,
            "getpwnam",
            return_value=SimpleNamespace(pw_uid=0, pw_dir="/root"),
        ):
            with self.assertRaisesRegex(workstation.Refusal, "non-root"):
                workstation.account("root")

    def test_execution_requires_exact_account_and_personal_authority(self):
        identity = {"name": "person", "uid": 1000, "gid": 1000, "home": "/home/person"}
        intent = {"kind": "user", "shell": "zsh", "user": "person", "identity": identity, "files": {}}
        with (
            patch.object(workstation, "account", return_value=identity),
            patch.object(workstation.os, "geteuid", return_value=0),
        ):
            with self.assertRaisesRegex(workstation.Refusal, "own authority"):
                workstation.execute("apply", intent)
        with (
            patch.object(workstation, "account", return_value={**identity, "home": "/new/home"}),
            patch.object(workstation.os, "geteuid", return_value=1000),
        ):
            with self.assertRaisesRegex(workstation.Refusal, "unchanged"):
                workstation.execute("apply", intent)
        with (
            patch.object(workstation, "account", return_value=identity),
            patch.object(workstation.os, "geteuid", return_value=1000),
        ):
            with self.assertRaisesRegex(workstation.Refusal, "selected marked"):
                workstation.execute("apply", intent)

    def test_wrong_distro_and_missing_kde_fail_before_user_lookup(self):
        from io import StringIO

        with patch("builtins.open", return_value=StringIO('ID="opensuse-leap"\n')):
            with self.assertRaisesRegex(workstation.Refusal, "Tumbleweed"):
                workstation.preflight("person")
        with (
            patch("builtins.open", return_value=StringIO('ID="opensuse-tumbleweed"\n')),
            patch.object(
                workstation.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=1),
            ),
        ):
            with self.assertRaisesRegex(workstation.Refusal, "KDE"):
                workstation.preflight("person")


if __name__ == "__main__":
    unittest.main()
