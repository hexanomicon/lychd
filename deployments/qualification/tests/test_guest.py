"""Offline guest action contracts; no real VM, package transaction or reboot occurs."""

import base64
import hashlib
import importlib.util
import io
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location("qualification_guest", Path(__file__).parents[1] / "guest.py")
guest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guest)


class GuestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="qualification-guest-contract-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        directory = patch.object(guest, "directory")
        directory.start()
        self.addCleanup(directory.stop)
        self.metadata = b"<repomd>admitted test metadata</repomd>"
        key = b"public key fixture"
        self.payload = {
            "run_id": "9f9942a8-c93a-4eaf-8c89-7732d82a1932",
            "snapshot": "20261101",
            "candidate_snapshot": "20261108",
            "repositories": [
                {
                    "name": "oss",
                    "url": "https://download.opensuse.org/history/20261108/tumbleweed/repo/oss/",
                    "repomd_sha256": hashlib.sha256(self.metadata).hexdigest(),
                    "key": {"sha256": hashlib.sha256(key).hexdigest()},
                    "key_data": base64.b64encode(key).decode(),
                }
            ],
        }

    def fake_transaction(self, argv, timeout=120):
        self.calls.append(argv)
        if "refresh" in argv:
            cached = self.root / self.payload["run_id"] / "raw/oss/repodata"
            cached.mkdir(parents=True)
            (cached / "repomd.xml").write_bytes(self.metadata)
        return "fixture transaction output"

    def test_upgrade_uses_only_isolated_dated_repositories_with_signatures_and_no_refresh(self):
        self.calls = []
        with (
            patch.object(guest, "guard"),
            patch.object(guest, "metadata"),
            patch.object(guest, "Path", return_value=self.root),
            patch.object(guest, "run", side_effect=self.fake_transaction),
        ):
            result = guest.upgrade(self.payload)
        self.assertTrue(result["upgrade_completed"])
        refresh, upgrade = self.calls[-2:]
        for command in (refresh, upgrade):
            self.assertIn("--reposd-dir", command)
            self.assertIn("--servicesd-dir", command)
            self.assertNotIn("--gpg-auto-import-keys", command)
            self.assertNotIn("--no-gpg-checks", command)
            self.assertNotIn("--releasever", command)
        self.assertEqual(upgrade[-3:], ["--no-refresh", "dup", "--no-allow-vendor-change"])
        config = (self.root / self.payload["run_id"] / "repos/oss.repo").read_text()
        self.assertIn("baseurl=" + self.payload["repositories"][0]["url"], config)
        for setting in ("gpgcheck=1", "repo_gpgcheck=1", "pkg_gpgcheck=1", "autorefresh=0"):
            self.assertIn(setting + "\n", config)

    def test_refreshed_metadata_drift_stops_before_dup(self):
        self.calls = []
        self.payload["repositories"][0]["repomd_sha256"] = "0" * 64
        with (
            patch.object(guest, "guard"),
            patch.object(guest, "metadata"),
            patch.object(guest, "Path", return_value=self.root),
            patch.object(guest, "run", side_effect=self.fake_transaction),
            self.assertRaises(ValueError),
        ):
            guest.upgrade(self.payload)
        self.assertFalse(any("dup" in command for command in self.calls))

    def test_repeated_or_interrupted_upgrade_occurrence_is_not_automatically_retried(self):
        (self.root / self.payload["run_id"]).mkdir()
        with (
            patch.object(guest, "guard"),
            patch.object(guest, "metadata"),
            patch.object(guest, "Path", return_value=self.root),
            patch.object(guest, "run") as command,
            self.assertRaises(ValueError),
        ):
            guest.upgrade(self.payload)
        command.assert_not_called()

    def test_failed_refresh_never_reaches_dup(self):
        calls = []

        def failed(argv, timeout=120):
            calls.append(argv)
            if "refresh" in argv:
                raise subprocess.CalledProcessError(1, argv)
            return ""

        with (
            patch.object(guest, "guard"),
            patch.object(guest, "metadata"),
            patch.object(guest, "Path", return_value=self.root),
            patch.object(guest, "run", side_effect=failed),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            guest.upgrade(self.payload)
        self.assertFalse(any("dup" in command for command in calls))

    def test_metadata_pin_and_https_are_required_before_any_transaction(self):
        for final_url, content in (
            ("http://mirror.invalid/repomd.xml", self.metadata),
            ("https://mirror.invalid/repomd.xml", b"different"),
        ):
            response = Mock()
            response.url = final_url
            response.read.return_value = content
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            with (
                patch.object(guest, "guard"),
                patch.object(guest, "urlopen", return_value=response),
                self.assertRaises(ValueError),
            ):
                guest.metadata(self.payload, "20261108")

    def test_privileged_guard_failure_precedes_network_and_all_mutation(self):
        with (
            patch.object(guest, "guard", side_effect=ValueError("foreign guest")),
            patch.object(guest, "urlopen") as network,
            patch.object(guest, "run") as command,
            self.assertRaises(ValueError),
        ):
            guest.upgrade(self.payload)
        network.assert_not_called()
        command.assert_not_called()

    def test_real_guard_rejects_wrong_marker_machine_and_qemu_before_transaction(self):
        baseline = "d7076f7b-b09e-4727-8ef8-5aef501cb30a"
        machine = "c" * 32
        payload = {**self.payload, "baseline_id": baseline, "machine_id": machine}
        correct = {
            "/etc/lychd-qualification.json": json.dumps({"schema": 1, "disposable": True, "baseline_id": baseline}),
            "/etc/machine-id": machine,
            "/sys/class/dmi/id/product_uuid": payload["run_id"],
        }
        for path, replacement in (
            ("/etc/lychd-qualification.json", '{"schema":1,"disposable":false}'),
            ("/etc/machine-id", "e" * 32),
            ("/sys/class/dmi/id/product_uuid", "d7076f7b-b09e-4727-8ef8-5aef501cb30a"),
        ):
            values = {**correct, path: replacement}

            def guest_path(name):
                result = Mock()
                result.read_text.return_value = values[name]
                result.lstat.return_value = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_uid=0, st_nlink=1)
                return result

            with (
                self.subTest(changed_identity=path),
                patch.object(guest.os, "geteuid", return_value=0),
                patch.object(guest, "Path", side_effect=guest_path),
                patch.object(guest, "urlopen") as network,
                patch.object(guest, "run") as command,
                self.assertRaises(ValueError),
            ):
                guest.upgrade(payload)
            network.assert_not_called()
            command.assert_not_called()

    def test_runtime_observation_refuses_root_and_nonrootless_podman(self):
        with (
            patch.object(guest.os, "geteuid", return_value=0),
            patch.object(guest, "run") as command,
            self.assertRaises(ValueError),
        ):
            guest.runtime()
        command.assert_not_called()
        identity = Mock(pw_name="lychd")
        with (
            patch.object(guest.os, "geteuid", return_value=1001),
            patch.object(guest.pwd, "getpwuid", return_value=identity),
            patch.object(
                guest, "run", side_effect=["systemd-version", json.dumps({"host": {"security": {"rootless": False}}})]
            ),
            self.assertRaises(ValueError),
        ):
            guest.runtime()

    def test_sudo_framing_requires_password_consumption_before_any_privileged_action(self):
        token = "f" * 64
        marker = "lychd-qualification-sudo-v1:" + token + "\n"
        for prefix in ("disposable-sudo-test\n", "", "wrong-marker\n"):
            # The empty prefix without its marker also models missing framing.
            data = prefix + (marker if prefix else "") + "{}\n"
            with (
                patch.object(sys, "argv", ["guest", "observe", token]),
                patch.object(sys, "stdin", io.StringIO(data)),
                patch.object(guest, "observe") as observation,
                self.assertRaisesRegex(ValueError, "password consumption"),
            ):
                guest.main()
            observation.assert_not_called()
        with (
            patch.object(sys, "argv", ["guest", "observe", token]),
            patch.object(sys, "stdin", io.StringIO(marker + '{"public":true}\n')),
            patch.object(sys, "stdout", io.StringIO()) as output,
            patch.object(guest, "observe", return_value={"ok": True}) as observation,
        ):
            guest.main()
        observation.assert_called_once_with({"public": True})
        self.assertNotIn("disposable-sudo-test", output.getvalue())

    def test_privileged_guest_action_without_sudo_marker_is_refused(self):
        with (
            patch.object(sys, "argv", ["guest", "observe"]),
            patch.object(sys, "stdin", io.StringIO("{}\n")),
            patch.object(guest, "observe") as observation,
            self.assertRaisesRegex(ValueError, "sudo input marker"),
        ):
            guest.main()
        observation.assert_not_called()

    def test_operator_profile_is_observed_as_an_ordinary_nonroot_identity(self):
        with patch.object(guest.os, "geteuid", return_value=0), self.assertRaises(ValueError):
            guest.administrator()
        with (
            patch.object(guest.os, "geteuid", return_value=1000),
            patch.object(guest.pwd, "getpwuid", return_value=Mock(pw_name="different")),
            self.assertRaises(ValueError),
        ):
            guest.administrator()
        with (
            patch.object(guest.os, "geteuid", return_value=1000),
            patch.object(guest.pwd, "getpwuid", return_value=Mock(pw_name="operator")),
        ):
            self.assertTrue(guest.administrator()["unprivileged"])


if __name__ == "__main__":
    unittest.main()
