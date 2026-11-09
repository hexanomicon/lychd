"""Stock sudo remediation must not discard custom administrator policy."""

import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).parents[1] / "roles/tumbleweed_admin/files/admin_probe.py"
SPEC = importlib.util.spec_from_file_location("admin_probe", PATH)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class AdminPolicyTests(unittest.TestCase):
    def test_named_policy_has_no_runtime_or_wildcard_grant(self):
        policy = probe.policy("operator")
        self.assertIn("operator ALL=(ALL:ALL) ALL", policy)
        self.assertNotIn("targetpw", policy)
        self.assertNotIn("\nALL ", policy)
        self.assertNotIn("lychd ALL", policy)

    def test_only_untouched_vendor_policy_can_be_replaced(self):
        desired = probe.policy("operator")
        self.assertEqual(probe.classify("vendor", "vendor", desired, []), "vendor")
        with self.assertRaisesRegex(ValueError, "custom"):
            probe.classify("custom", "vendor", desired, [])
        with self.assertRaisesRegex(ValueError, "drop-ins"):
            probe.classify("vendor", "vendor", desired, ["team-admins"])
        self.assertEqual(probe.classify(desired, "vendor", desired, []), "configured")

    def test_runtime_root_and_injected_names_are_refused(self):
        for name in ("root", "lychd", "lychd-view", "operator\nALL", "a b", "", None):
            with self.subTest(name=name), self.assertRaises(ValueError):
                probe.policy(name)
