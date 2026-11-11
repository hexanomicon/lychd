"""Controller-only custody and compatibility tests for the native JSON shim."""

import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

PROBE_PATH = Path(__file__).parents[1] / "roles/lychd_app/files/app_probe.py"
SPEC = importlib.util.spec_from_file_location("app_probe", PROBE_PATH)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
REVISION = "a" * 40
IMAGE = "b" * 64


def response(state="running"):
    return {
        "schema": "lychd.deployment",
        "version": 1,
        "revision": REVISION,
        "state": state,
        "next_action": probe.ACTIONS.get(state, "refuse"),
        "ok": state == "running",
        "reasons": [],
        "checks": [],
    }


class NativeContractTests(unittest.TestCase):
    def test_fixed_cli_and_full_image_id_are_forwarded(self):
        source, argv = probe.native_command("verify", {"revision": REVISION, "image_id": IMAGE}, "/home/lychd")
        self.assertEqual(source, Path("/home/lychd/src") / f"lychd-{REVISION}")
        self.assertEqual(
            argv,
            [
                str(source / ".venv/bin/lychd"),
                "status",
                "--json",
                "--deployment-revision",
                REVISION,
                "--deployment-image-id",
                IMAGE,
                "--deployment-verify",
            ],
        )

    def test_protocol_two_requires_explicit_profile_and_full_tether_identity(self):
        request = {
            "revision": REVISION,
            "image_id": IMAGE,
            "profile": "tether-container-v1",
            "intent": "/secure/intent.json",
            "tether_image_id": "c" * 64,
        }
        _, argv = probe.native_command("classify", request, "/home/lychd")
        self.assertIn("--deployment-profile", argv)
        self.assertIn("--deployment-intent", argv)
        self.assertIn("--deployment-tether-image-id", argv)
        document = dict(response(), version=2, profile="tether-container-v1")
        self.assertIs(probe.validate_response(document, "tether-container-v1"), document)
        with self.assertRaises(probe.Refusal):
            probe.validate_response(document)
        with self.assertRaises(probe.Refusal):
            probe.validate_response(response(), "tether-container-v1")
        with self.assertRaises(probe.Refusal):
            probe.native_command("classify", dict(request, tether_image_id="moving"), "/home/lychd")

    def test_configure_and_arbitrary_commands_do_not_exist(self):
        for command in ("configure", "start", "shell"):
            with self.assertRaises(probe.Refusal):
                probe.native_command(command, {"revision": REVISION}, "/home/lychd")

    def test_version_mismatch_and_boolean_version_refuse(self):
        for version in (0, 2, True, "1"):
            with self.assertRaises(probe.Refusal):
                probe.validate_response(dict(response(), version=version))

    def test_native_active_decision_is_never_reinterpreted_as_mutable(self):
        document = response()
        self.assertIs(probe.validate_response(document), document)
        with self.assertRaises(probe.Refusal):
            probe.validate_response(dict(document, next_action="start"))

    def test_matching_native_json_is_forwarded(self):
        document = response()
        with (
            patch.object(probe.Path, "is_file", return_value=True),
            patch.object(
                probe.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, json.dumps(document), "private-tool-stderr"),
            ) as run,
        ):
            actual, status = probe.observe("classify", {"revision": REVISION}, "/home/lychd")
        self.assertEqual(actual, document)
        self.assertEqual(status, 0)
        self.assertNotIn("sudo", run.call_args.args[0])
        self.assertTrue(run.call_args.kwargs["capture_output"])

    def test_malformed_native_output_never_becomes_exception_text(self):
        secret = "private-credential-or-validation-input"
        with (
            patch.object(probe.Path, "is_file", return_value=True),
            patch.object(probe.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, secret, secret)),
            self.assertRaises(probe.Refusal) as caught,
        ):
            probe.observe("verify", {"revision": REVISION}, "/home/lychd")
        self.assertNotIn(secret, str(caught.exception))

    def test_unknown_native_json_never_invokes_or_admits_start(self):
        document = response("unknown")
        document["reasons"] = ["effective_binding_override_or_reload"]
        with (
            patch.object(probe.Path, "is_file", return_value=True),
            patch.object(
                probe.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, json.dumps(document), "")
            ) as run,
        ):
            actual, status = probe.observe("classify", {"revision": REVISION}, "/home/lychd")
        self.assertEqual(status, 1)
        self.assertEqual(actual["next_action"], "refuse")
        self.assertNotIn("start", run.call_args.args[0])
        with self.assertRaises(probe.Refusal):
            probe.validate_response(dict(document, next_action="start"))

    def test_no_core_or_human_render_parser_is_in_controller(self):
        source = PROBE_PATH.read_text()
        for obsolete in (
            "from lychd",
            "config_state",
            "LifecycleReceipt",
            "Initialization plan is safe",
            '"access"',
            "CORE_UNITS",
            "SUBVOL_INFO",
        ):
            self.assertNotIn(obsolete, source)


if __name__ == "__main__":
    unittest.main()


class TetherPreparationTests(unittest.TestCase):
    def test_waiting_keys_is_actionable_protocol_two(self):
        document = response("prepared_waiting_keys")
        document.update(version=2, profile="tether-container-v1")
        self.assertEqual(probe.validate_response(document, "tether-container-v1")["next_action"], "import-key")
