"""Offline refusal/process contracts; these tests never qualify a VM or snapshot."""

import copy
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

MODULE = Path(__file__).parents[1] / "qualify.py"
SPEC = importlib.util.spec_from_file_location("qualification", MODULE)
qualification = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qualification)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="qualification-contract-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.revision, self.image_id = "a" * 40, "b" * 64
        self.plan = {
            "schema": 1,
            "run_id": "9f9942a8-c93a-4eaf-8c89-7732d82a1932",
            "controller_source_sha256": qualification.source_digest(),
            "baseline": {
                "snapshot": "20261101",
                "baseline_id": "d7076f7b-b09e-4727-8ef8-5aef501cb30a",
                "machine_id": "c" * 32,
                "image": self.artifact("baseline.qcow2", b"not a real VM"),
                "provenance": {
                    "url": "https://download.opensuse.org/tumbleweed/appliances/baseline.qcow2",
                    "image_sha256": "d" * 64,
                    "checksum": self.artifact("image.sha256", b"test checksum"),
                    "signature": self.artifact("image.asc", b"not a signature"),
                    "keyring": self.artifact("keyring.gpg", b"not a keyring"),
                    "signer_fingerprint": "A" * 40,
                },
                "repositories": self.repos("20261101"),
            },
            "candidate": {"snapshot": "20261108", "repositories": self.repos("20261108")},
            "application": {"revision": self.revision, "image_id": self.image_id},
            "ssh": {
                "port": 22222,
                "host_key": "ssh-ed25519 AAAATEST",
                "admin_key": self.artifact("root key%fixture", b"disposable fake private key"),
                "runtime_key": self.artifact("runtime-key", b"disposable fake private key"),
            },
            "inputs": {
                "host_vars": self.json_artifact("host.json", {"lychd_runtime_name": "lychd"}),
                "source_vars": self.json_artifact("source.json", {"lychd_source_revision": self.revision}),
                "image_vars": self.json_artifact(
                    "image.json",
                    {
                        "lychd_image_id": self.image_id,
                        "lychd_image_revision": self.revision,
                        "lychd_image_ref": "localhost/lychd:" + self.revision,
                    },
                ),
            },
            "access": None,
        }

    def artifact(self, name, content):
        path = self.root / name
        path.write_bytes(content)
        path.chmod(0o600)
        return {"path": str(path), "sha256": qualification.digest(path)}

    def json_artifact(self, name, value):
        return self.artifact(name, json.dumps(value).encode())

    def repos(self, snapshot):
        return [
            {
                "name": "oss",
                "url": f"https://download.opensuse.org/history/{snapshot}/tumbleweed/repo/oss/",
                "repomd_sha256": "e" * 64,
                "key": self.artifact("key-" + snapshot, b"public key fixture"),
                "fingerprint": "B" * 40,
            }
        ]

    def test_shape_validation_is_explicitly_not_vm_or_signature_acceptance(self):
        self.assertIs(qualification.validate_plan(self.plan), self.plan)
        self.assertEqual(Path(self.plan["baseline"]["image"]["path"]).read_bytes(), b"not a real VM")

    def test_unknown_fields_and_moving_or_wrong_snapshot_repositories_refuse(self):
        for mutate in (
            lambda p: p.update(production_host="example.org"),
            lambda p: p["ssh"].update(host="192.0.2.10"),
            lambda p: p["candidate"]["repositories"][0].update(
                url="https://download.opensuse.org/tumbleweed/repo/oss/"
            ),
            lambda p: p["candidate"]["repositories"][0].update(
                url="https://download.opensuse.org/history/20261101/tumbleweed/repo/oss/"
            ),
            lambda p: p["candidate"].update(snapshot=p["baseline"]["snapshot"]),
            lambda p: p.update(controller_source_sha256="f" * 64),
            lambda p: p["application"].update(image_id="0" * 64),
        ):
            plan = copy.deepcopy(self.plan)
            mutate(plan)
            with self.subTest(plan=plan["candidate"]["snapshot"]), self.assertRaises(qualification.Refusal):
                qualification.validate_plan(plan)

    def test_altered_private_file_hardlink_symlink_and_public_mode_refuse(self):
        original = self.plan["ssh"]["runtime_key"]
        path = Path(original["path"])
        path.write_text("altered")
        with self.assertRaises(qualification.Refusal):
            qualification.validate_plan(self.plan)
        path.write_bytes(b"disposable fake private key")
        path.chmod(0o644)
        with self.assertRaises(qualification.Refusal):
            qualification.validate_plan(self.plan)
        path.chmod(0o600)
        link = self.root / "linked-key"
        link.symlink_to(path)
        with self.assertRaises(qualification.Refusal):
            qualification.trusted_file(str(link), private=True)
        link.unlink()
        os.link(path, link)
        with self.assertRaises(qualification.Refusal):
            qualification.trusted_file(str(path), private=True)

    def test_ansible_connection_override_template_and_mutation_authority_refuse(self):
        for value in (
            {"ansible_host": "192.0.2.10"},
            {"lychd_deploy_target": "pilot"},
            {"lychd_app_start_authorized": True},
            {"lychd_runtime_name": "{{ lookup('pipe', 'id') }}"},
        ):
            self.plan["inputs"]["host_vars"] = self.json_artifact("host.json", value)
            with self.subTest(value=value), self.assertRaises(qualification.Refusal):
                qualification.validate_plan(self.plan)

    def test_duplicate_json_fields_refuse(self):
        path = self.root / "duplicate.json"
        path.write_text('{"schema":1,"schema":2}')
        with self.assertRaises(qualification.Refusal):
            qualification.load_json(path)

    def test_access_lane_cannot_prepare_or_redirect_the_target(self):
        for value in (
            {"lychd_access_enabled": True, "lychd_access_prepare": True},
            {"lychd_access_enabled": True, "ansible_host": "192.0.2.10"},
        ):
            self.plan["access"] = {"profile": "host-access-v1", "variables": self.json_artifact("access.json", value)}
            with self.assertRaises(qualification.Refusal):
                qualification.validate_plan(self.plan)

    def test_missing_qemu_is_failure_not_skip(self):
        run = qualification.Qualification(self.plan, self.root, self.root)
        with patch.object(qualification.shutil, "which", return_value=None), self.assertRaises(qualification.Refusal):
            run.prepare()
        self.assertNotEqual(run.receipt["status"], "passed")

    def test_ssh_config_pins_host_key_and_selects_exact_user_keys_with_spaces(self):
        (self.root / "bin").mkdir()
        controller = self.root / "bin/ansible-playbook"
        controller.write_text("fixture")
        controller.chmod(0o700)
        run = qualification.Qualification(self.plan, self.root, self.root)

        def output(stage, argv, **options):
            if stage == "image-signature":
                return "[GNUPG:] VALIDSIG " + "A" * 40 + " 1 2\n"
            if stage.endswith("-key"):
                return "pub:fixture\nfpr:::::::::" + "B" * 40 + ":\n"
            return ""

        self.plan["baseline"]["provenance"]["checksum"] = self.artifact(
            "image.sha256", ("d" * 64 + "  baseline.qcow2\n").encode()
        )
        with (
            patch.object(qualification.shutil, "which", return_value=str(controller)),
            patch.object(run, "command", side_effect=output),
        ):
            run.prepare()
        for user, name in (("root", "admin_key"), ("lychd", "runtime_key")):
            observed = subprocess.run(
                ["ssh", "-G", "-F", str(self.root / "ssh_config"), "-l", user, "qualification"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            self.assertIn("hostname 127.0.0.1\n", observed)
            self.assertIn("stricthostkeychecking true\n", observed)
            # ssh -G prints token escapes; %% becomes a literal % when connecting.
            self.assertIn("identityfile " + self.plan["ssh"][name]["path"].replace("%", "%%") + "\n", observed)
        self.assertEqual(
            (self.root / "known_hosts").read_text(), "[127.0.0.1]:22222 " + self.plan["ssh"]["host_key"] + "\n"
        )

    def test_changed_or_missing_playbook_observations_cannot_pass(self):
        for output in ("pilot : ok=1 changed=1 failed=0", "", "pilot : ok=1 changed=0 failed=0"):
            run = qualification.Qualification(self.plan, self.root, self.root)
            run.ansible = "/not/executed"
            with (
                patch.object(run, "ssh", return_value=json.dumps({"boot_id": "test", "packages": {}})),
                patch.object(run, "command", return_value=output),
                self.assertRaises(qualification.Refusal),
            ):
                run.observe("baseline")

    def test_failed_command_preserves_private_log_and_sanitized_receipt(self):
        run = qualification.Qualification(self.plan, self.root, self.root)
        with self.assertRaises(qualification.Refusal):
            run.command("failure", [sys.executable, "-c", "print('PRIVATE-TEST-VALUE'); raise SystemExit(1)"])
        receipt = json.loads((self.root / "receipt.json").read_text())
        self.assertFalse(receipt["stages"][-1]["ok"])
        self.assertNotIn("PRIVATE-TEST-VALUE", json.dumps(receipt))
        self.assertIn("PRIVATE-TEST-VALUE", (self.root / "01-failure.log").read_text())

    def test_timeout_is_bounded_and_cannot_pass(self):
        run = qualification.Qualification(self.plan, self.root, self.root)
        with self.assertRaises(subprocess.TimeoutExpired):
            run.command("timeout", [sys.executable, "-c", "import time; time.sleep(60)"], timeout=0.02)
        self.assertFalse(run.receipt["stages"][-1]["ok"])

    def main_arguments(self, check=False):
        (self.root / "bin").mkdir()
        executable = self.root / "bin/ansible-playbook"
        executable.write_text("not executed")
        executable.chmod(0o700)
        path = self.json_artifact("plan.json", self.plan)["path"]
        args = [str(MODULE), "--plan", path, "--controller", str(self.root), "--work-dir", str(self.root / "new-run")]
        if check:
            args.append("--check")
        else:
            args.extend(["--authorize-upgrade", self.plan["run_id"] + ":20261101:20261108"])
        return args

    def test_offline_check_does_not_launch_or_write_a_passing_receipt(self):
        with (
            patch.object(sys, "argv", self.main_arguments(check=True)),
            patch.object(qualification.Qualification, "launch") as launch,
            patch.object(qualification.signal, "signal"),
        ):
            self.assertEqual(qualification.main(), 0)
        launch.assert_not_called()
        self.assertFalse((self.root / "new-run").exists())

    def test_real_run_missing_vm_tool_returns_failure_and_retains_nonpassing_receipt(self):
        with (
            patch.object(sys, "argv", self.main_arguments()),
            patch.object(qualification.shutil, "which", return_value=None),
            patch.object(qualification.signal, "signal"),
        ):
            self.assertEqual(qualification.main(), 1)
        receipt = json.loads((self.root / "new-run/receipt.json").read_text())
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["stages"], [])
        self.assertFalse((self.root / "new-run/overlay.qcow2").exists())

    def test_serial_output_is_bounded_and_overflow_refuses_further_stages(self):
        run = qualification.Qualification(self.plan, self.root, self.root)
        run.process = Mock(stdout=io.BufferedReader(io.BytesIO(b"x" * 128)))
        with patch.object(qualification, "MAX_LOG", 64):
            run.capture_serial()
        self.assertTrue(run.output_overflow)
        self.assertEqual((self.root / "serial.log").stat().st_size, 64)
        with patch.object(qualification.subprocess, "Popen") as command, self.assertRaises(qualification.Refusal):
            run.command("after-overflow", ["not-executed"])
        command.assert_not_called()


class ProcessTests(unittest.TestCase):
    def process(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)

        def cleanup():
            if process.poll() is None:
                process.kill()
            process.wait(timeout=2)

        self.addCleanup(cleanup)
        return process

    def test_only_exact_owned_process_identity_can_be_terminated(self):
        process = self.process()
        identity = qualification.process_identity(process.pid)
        with self.assertRaises(qualification.Refusal):
            qualification.terminate_owned(process, (identity[0], "different-start-time"))
        self.assertIsNone(process.poll())
        qualification.terminate_owned(process, identity)
        self.assertIsNotNone(process.returncode)

    def test_missing_vm_fails_before_any_ssh_attempt(self):
        run = qualification.Qualification.__new__(qualification.Qualification)
        run.deadline = qualification.time.monotonic() + 1
        run.process = Mock()
        run.process.poll.return_value = 1
        with patch.object(qualification.subprocess, "run") as ssh, self.assertRaises(qualification.Refusal):
            run.wait_ssh("baseline")
        ssh.assert_not_called()

    def test_unresponsive_owned_process_has_bounded_kill_fallback(self):
        process = Mock(pid=12345)
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("owned", 10), 0]
        identity = ("/explicit/qemu", "123456789")
        with patch.object(qualification, "process_identity", return_value=identity):
            qualification.terminate_owned(process, identity)
        process.terminate.assert_called_once_with()
        process.kill.assert_called_once_with()
        self.assertEqual(process.wait.call_count, 2)


if __name__ == "__main__":
    unittest.main()
