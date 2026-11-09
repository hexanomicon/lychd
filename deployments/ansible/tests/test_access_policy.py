"""Observe realistic policy answers without touching a firewall or inventory."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "access_host", Path(__file__).parents[1] / "roles/host_access/files/access_host.py"
)
host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(host)

ICMP6 = (
    "neighbour-advertisement",
    "neighbour-solicitation",
    "router-advertisement",
    "redirect",
    "mld-listener-done",
    "mld-listener-query",
    "mld-listener-report",
    "mld2-listener-report",
)


def vendor(option):
    return {
        "--get-policies": "allow-host-ipv6",
        "--list-all": "allow-host-ipv6 (active)\n  target: CONTINUE\n  priority: -15000\n",
        "--list-ingress-zones": "ANY",
        "--list-egress-zones": "HOST",
        "--query-masquerade": "no",
        "--query-disable": "no",
        "--list-rich-rules": "\n".join(f'rule family="ipv6" icmp-type name="{name}" accept' for name in ICMP6),
    }.get(option, "")


class PolicyTests(unittest.TestCase):
    def test_vendor_ipv6_bootstrap_admitted_in_both_scopes(self):
        with patch.object(host, "firewall", side_effect=lambda *args, **kwargs: vendor(args[-1])) as firewall:
            host.firewall_policy_prerequisites()
        self.assertEqual({call.kwargs["permanent"] for call in firewall.call_args_list}, {False, True})
        self.assertTrue(
            all(not any("add" in arg or "remove" in arg for arg in call.args) for call in firewall.call_args_list)
        )

    def test_dormant_foreign_object_is_refused_without_using_active_list(self):
        for permanent in (False, True):

            def observe(*args, **kwargs):
                if args == ("--get-policies",) and kwargs["permanent"] == permanent:
                    return "allow-host-ipv6 dormant-trust"
                self.assertNotIn("--get-active-policies", args)
                self.assertNotIn("--get-target", args)
                self.assertNotIn("--get-priority", args)
                return vendor(args[-1])

            with (
                self.subTest(permanent=permanent),
                patch.object(host, "firewall", side_effect=observe),
                self.assertRaises(host.Refusal),
            ):
                host.firewall_policy_prerequisites()

    def test_changed_vendor_rules_or_target_never_allow_wider_access(self):
        for option, changed in (
            ("--list-all", vendor("--list-all").replace("CONTINUE", "ACCEPT")),
            ("--list-all", vendor("--list-all").replace("-15000", "-1")),
            ("--list-ports", "22/tcp"),
            ("--list-ingress-zones", "trusted"),
            ("--list-rich-rules", vendor("--list-rich-rules") + '\nrule family="ipv4" accept'),
            ("--list-rich-rules", vendor("--list-rich-rules") + '\nrule family="ipv6" accept'),
        ):
            with (
                self.subTest(option=option),
                patch.object(
                    host,
                    "firewall",
                    side_effect=lambda *args, **kwargs: changed if args[-1] == option else vendor(args[-1]),
                ),
                self.assertRaises(host.Refusal),
            ):
                host.firewall_policy_prerequisites()

    def test_no_policy_objects_is_also_safe(self):
        with patch.object(host, "firewall", return_value=""):
            host.firewall_policy_prerequisites()


if __name__ == "__main__":
    unittest.main()
