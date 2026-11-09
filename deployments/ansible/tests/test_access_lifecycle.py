"""Durable transport-only lifecycle; all service effects are fixture observations."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml
from jinja2 import Environment

SPEC = importlib.util.spec_from_file_location(
    "access_host", Path(__file__).parents[1] / "roles/host_access/files/access_host.py"
)
host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(host)
INTENT = {"fixture": "exact public intent"}


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.marker = root / "revoked.json"
        for name, value in (
            ("ROOT", root),
            ("REVOCATION", self.marker),
            ("validate", lambda intent: intent),
            ("load_owned_receipt", lambda intent: {}),
            ("verify_units_owned", lambda: None),
            ("digest", lambda path: "hash"),
        ):
            patcher = patch.object(host, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(host.os, "geteuid", return_value=0)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_revocation_fence_precedes_both_service_effects(self):
        def run(args, **kwargs):
            self.assertEqual(json.loads(self.marker.read_text()), {"revoked": True, "intent": INTENT})
            self.assertEqual(args, ["systemctl", "disable", "--now", host.UNITS[1], host.UNITS[0]])
            return SimpleNamespace(stdout="", returncode=0)

        with patch.object(host, "run", side_effect=run), patch.object(host, "verify_revoked") as verify:
            self.assertEqual(host.revoke(INTENT), {"changed": True, "state": "revoked"})
            verify.assert_called_once_with(INTENT)
        self.assertEqual(self.marker.stat().st_mode & 0o777, 0o600)

    def test_interrupt_leaves_intent_and_repeat_finishes_pending(self):
        with patch.object(host, "run", side_effect=host.Refusal("interrupted")), self.assertRaises(host.Refusal):
            host.revoke(INTENT)
        self.assertTrue(self.marker.exists())
        with (
            patch.object(host, "verify_revoked", side_effect=[host.Refusal("pending"), None]),
            patch.object(host, "run") as run,
        ):
            self.assertTrue(host.revoke(INTENT)["changed"])
            run.assert_called_once_with(["systemctl", "disable", "--now", host.UNITS[1], host.UNITS[0]])
        with patch.object(host, "verify_revoked"), patch.object(host, "run") as run:
            self.assertFalse(host.revoke(INTENT)["changed"])
            run.assert_not_called()

    def test_plan_has_no_marker_or_service_writes(self):
        with patch.object(host, "run") as run:
            self.assertTrue(host.revoke(INTENT, plan=True)["would_revoke"])
            run.assert_not_called()
        self.assertFalse(self.marker.exists())

    def test_modified_unit_refuses_before_tombstone(self):
        with (
            patch.object(host, "verify_units_owned", side_effect=host.Refusal("foreign unit")),
            patch.object(host, "run") as run,
            self.assertRaises(host.Refusal),
        ):
            host.revoke(INTENT)
        self.assertFalse(self.marker.exists())
        run.assert_not_called()

    def test_apply_never_resurrects_revoked_intent(self):
        self.marker.write_text(json.dumps({"revoked": True, "intent": INTENT}))
        with patch.object(host, "run") as run, self.assertRaises(host.Refusal):
            host.operate("apply", INTENT)
        run.assert_not_called()

    def test_verify_observes_revoked_without_mutation(self):
        self.marker.write_text(json.dumps({"revoked": True, "intent": INTENT}))
        with patch.object(host, "verify_revoked") as verify, patch.object(host, "run") as run:
            self.assertEqual(host.operate("verify", INTENT), {"changed": False, "state": "revoked"})
            verify.assert_called_once_with(INTENT)
            run.assert_not_called()

    def test_revocation_readback_requires_both_units_disabled_and_interface_absent(self):
        self.marker.write_text(json.dumps({"revoked": True, "intent": INTENT}))

        def observe(args, **kwargs):
            if args[0] == "ip":
                return SimpleNamespace(stdout='[{"ifname":"lo"}]', returncode=0)
            return SimpleNamespace(stdout="inactive" if args[1] == "is-active" else "disabled", returncode=3)

        with patch.object(host, "run", side_effect=observe) as run:
            host.verify_revoked(INTENT)
        self.assertEqual(len(run.call_args_list), 5)
        with (
            patch.object(host, "run", return_value=SimpleNamespace(stdout="active", returncode=0)),
            self.assertRaises(host.Refusal),
        ):
            host.verify_revoked(INTENT)

    def test_missing_installation_verification_refuses_without_probes(self):
        with (
            patch.object(host, "ROOT", Path(self.directory.name) / "missing"),
            patch.object(host, "run") as run,
            self.assertRaises(host.Refusal),
        ):
            host.operate("verify", INTENT)
        run.assert_not_called()

    def test_explicit_playbooks_refuse_disabled_or_wrong_action_instead_of_skipping(self):
        environment = Environment()
        environment.filters["bool"] = bool
        root = Path(__file__).parents[1]
        for action in ("verify", "revoke"):
            play = yaml.safe_load((root / f"playbooks/access-{action}.yml").read_text())[0]
            checks = [
                environment.compile_expression(expression)
                for expression in play["pre_tasks"][0]["ansible.builtin.assert"]["that"]
            ]
            values = {
                "lychd_access_enabled": True,
                "lychd_access_action": action,
                "lychd_access_target": "pilot",
                "inventory_hostname": "pilot",
            }
            self.assertTrue(all(check(**values) for check in checks))
            for change in (
                {"lychd_access_enabled": False},
                {"lychd_access_action": "apply"},
                {"lychd_access_target": "other"},
            ):
                self.assertFalse(all(check(**{**values, **change}) for check in checks))


class UnitOwnershipTests(unittest.TestCase):
    def observed(self, args, **kwargs):
        if "--property=DropInPaths" in args:
            value = str(host.WG_DROPIN) if args[2] == host.UNITS[0] else ""
        else:
            value = "/usr/lib/systemd/system/wg-quick@.service" if args[2] == host.UNITS[0] else str(host.UNIT)
        return SimpleNamespace(stdout=value, returncode=0)

    def test_only_exact_owned_instance_dropin_is_admitted(self):
        with patch.object(host, "WG_DROPIN_DIR") as directory, patch.object(host, "run", side_effect=self.observed):
            directory.lstat.return_value = SimpleNamespace(st_mode=0o40755, st_uid=0)
            host.verify_units_owned()

    def test_extra_or_missing_dropin_refuses(self):
        for value in ("", str(host.WG_DROPIN) + " /etc/systemd/system/wg-quick@.service.d/foreign.conf"):

            def observed(args, **kwargs):
                if "--property=DropInPaths" in args and args[2] == host.UNITS[0]:
                    return SimpleNamespace(stdout=value, returncode=0)
                return self.observed(args, **kwargs)

            with (
                self.subTest(value=value),
                patch.object(host, "WG_DROPIN_DIR") as directory,
                patch.object(host, "run", side_effect=observed),
                self.assertRaises(host.Refusal),
            ):
                directory.lstat.return_value = SimpleNamespace(st_mode=0o40755, st_uid=0)
                host.verify_units_owned()

    def test_fresh_partial_directory_refuses_before_unit_observations(self):
        with (
            patch.object(host.os.path, "lexists", return_value=True),
            patch.object(host, "run") as run,
            self.assertRaises(host.Refusal),
        ):
            host.verify_units_owned(fresh=True)
        run.assert_not_called()

    def test_symlink_or_writable_dropin_directory_refuses(self):
        for mode in (0o120755, 0o40777):
            with (
                self.subTest(mode=mode),
                patch.object(host, "WG_DROPIN_DIR") as directory,
                patch.object(host, "run") as run,
                self.assertRaises(host.Refusal),
            ):
                directory.lstat.return_value = SimpleNamespace(st_mode=mode, st_uid=0)
                host.verify_units_owned()
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
