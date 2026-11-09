"""Bootstrap refusal and already-completed decision checks; never contacts a host."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "access_host", Path(__file__).parents[1] / "roles/host_access/files/access_host.py"
)
host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(host)


class PreparationTests(unittest.TestCase):
    def test_custom_port_ranges_refuse_without_rejecting_vendor_generic_ranges(self):
        self.assertTrue(host.exact_port_conflict("other_port_t tcp 2222"))
        self.assertFalse(host.exact_port_conflict("unreserved_port_t tcp 1024-32767"))
        self.assertTrue(host.exact_port_conflict("custom_port_t tcp 2200-2300", include_ranges=True))
        self.assertFalse(host.exact_port_conflict("ssh_port_t tcp 2222", include_ranges=True))

    def test_foreign_exact_and_covering_custom_file_rules_refuse(self):
        path = "/etc/lychd-access/authorized_keys"
        self.assertTrue(
            host.custom_context_conflict(path + " all files system_u:object_r:wrong_t:s0", path, "ssh_home_t")
        )
        self.assertTrue(
            host.custom_context_conflict(
                "/etc/lychd-access(/.*)? all files system_u:object_r:wrong_t:s0", path, "ssh_home_t"
            )
        )
        self.assertFalse(
            host.custom_context_conflict(path + " all files system_u:object_r:ssh_home_t:s0", path, "ssh_home_t")
        )

    def test_completed_installation_uses_only_original_read_only_path(self):
        with (
            patch.object(host, "validate", return_value={"intent": "pinned"}),
            patch.object(host.os, "geteuid", return_value=0),
            patch.object(host, "ROOT") as root,
            patch.object(host, "operate", return_value={"changed": False}) as operate,
            patch.object(host, "run") as run,
            patch.object(host, "private_write") as write,
        ):
            root.exists.return_value = True
            self.assertEqual(host.prepare("prepare-apply", {}), {"changed": False})
            operate.assert_called_once_with("plan", {"intent": "pinned"})
            run.assert_not_called()
            write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
