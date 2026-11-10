"""Observe realistic policy answers without touching a firewall or inventory."""

import importlib.util
import subprocess
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


# Observed Tumbleweed/firewalld 2.5.2 fixture, independently checked against the
# five v2.5.2 config/policies/gateway-*.xml files and command.py's output format.
GATEWAYS = {
    "gateway-dmz-to-HOST": ("CONTINUE", "dmz", "HOST", "dhcp dns"),
    "gateway-lan-to-HOST": ("CONTINUE", "internal home trusted", "HOST", "dhcp dns ssh"),
    "gateway-lan-to-work": ("ACCEPT", "internal home trusted", "work", "ftp tftp"),
    "gateway-lan-to-world": ("ACCEPT", "internal home trusted", "external public", "ftp tftp"),
    "gateway-world-to-HOST": ("CONTINUE", "external public", "HOST", "dhcpv6-client"),
}
SUMMARY = """{name}{header}
  disable: yes
  priority: 1000
  target: {target}
  ingress-zones: {ingress}
  egress-zones: {egress}
  services: {services}
  ports:
  protocols:
  masquerade: no
  forward-ports:
  source-ports:
  icmp-blocks:
  rich rules:"""


def six_policy_fixture(*args, permanent=False):
    if args == ("--get-policies",):
        return "allow-host-ipv6 " + " ".join(GATEWAYS)
    if args[0].startswith("--path-policy="):
        return "/usr/lib/firewalld/policies/" + args[0].split("=", 1)[1] + ".xml"
    name = args[0].split("=", 1)[1]
    if name == "allow-host-ipv6":
        if args[-1] == "--list-all":
            return """allow-host-ipv6 (active)
  disable: no
  priority: -15000
  target: CONTINUE
  ingress-zones: ANY
  egress-zones: HOST
  services:
  ports:
  protocols:
  masquerade: no
  forward-ports:
  source-ports:
  icmp-blocks:
  rich rules:
""" + "\n".join("\t" + line for line in vendor("--list-rich-rules").splitlines())
        return vendor(args[-1])
    if args[-1] == "--query-disable":
        return "yes"
    if args[-1] == "--list-all":
        target, ingress, egress, services = GATEWAYS[name]
        return SUMMARY.format(
            name=name,
            header="" if permanent else " (disabled)",
            target=target,
            ingress=ingress,
            egress=egress,
            services=services,
        )
    raise AssertionError(f"Unexpected observation: {args}")


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


class GatewayPolicyTests(unittest.TestCase):
    def observe(self, change=None):
        def answer(*args, **kwargs):
            value = six_policy_fixture(*args, **kwargs)
            return change(args, kwargs["permanent"], value) if change else value

        return patch.object(host, "firewall", side_effect=answer)

    def test_complete_six_policy_fixture_is_read_only_and_bounded(self):
        with self.observe() as firewall, patch.object(host.os.path, "lexists", return_value=False):
            host.firewall_policy_prerequisites()
        self.assertLessEqual(firewall.call_count, 60)
        for call in firewall.call_args_list:
            self.assertTrue(
                all(
                    arg.startswith(("--get-", "--list-", "--query-", "--path-policy=", "--policy="))
                    for arg in call.args
                )
            )
            self.assertNotIn("--get-active-policies", call.args)
            self.assertNotIn("--get-target", call.args)
            self.assertNotIn("--get-priority", call.args)
        for name in GATEWAYS:
            for permanent in (False, True):
                self.assertIn(
                    ((f"--policy={name}", "--query-disable"), {"permanent": permanent}),
                    [(call.args, call.kwargs) for call in firewall.call_args_list],
                )

    def test_every_gateway_field_change_refuses_in_each_scope(self):
        changes = {
            "disable": "no",
            "priority": "999",
            "target": "DROP",
            "ingress-zones": "ANY",
            "egress-zones": "ANY",
            "services": "http",
            "ports": "2222/tcp",
            "protocols": "gre",
            "masquerade": "yes",
            "forward-ports": "port=80:proto=tcp:toport=7134:toaddr=127.0.0.1",
            "source-ports": "22/tcp",
            "icmp-blocks": "echo-request",
            "rich rules": 'rule family="ipv4" accept',
        }
        for name in GATEWAYS:
            for permanent in (False, True):
                for field, replacement in changes.items():

                    def change(args, scope, value):
                        if args == (f"--policy={name}", "--list-all") and scope == permanent:
                            return "\n".join(
                                f"  {field}: {replacement}" if line.startswith(f"  {field}:") else line
                                for line in value.splitlines()
                            )
                        return value

                    with (
                        self.subTest(name=name, permanent=permanent, field=field),
                        self.observe(change),
                        patch.object(host.os.path, "lexists", return_value=False),
                        self.assertRaises(host.Refusal),
                    ):
                        host.firewall_policy_prerequisites()

    def test_enabled_query_refuses_even_if_header_and_summary_say_disabled(self):
        for name in GATEWAYS:
            for permanent in (False, True):

                def change(args, scope, value):
                    return "no" if args == (f"--policy={name}", "--query-disable") and scope == permanent else value

                with (
                    self.subTest(name=name, permanent=permanent),
                    self.observe(change),
                    patch.object(host.os.path, "lexists", return_value=False),
                    self.assertRaises(host.Refusal),
                ):
                    host.firewall_policy_prerequisites()

    def test_local_override_and_nonvendor_path_refuse(self):
        for name in GATEWAYS:
            with (
                self.subTest(name=name, reason="override"),
                self.observe(),
                patch.object(host.os.path, "lexists", side_effect=lambda path: path.endswith(f"/{name}.xml")),
                self.assertRaises(host.Refusal),
            ):
                host.firewall_policy_prerequisites()

            def change(args, scope, value):
                return value.replace("/usr/lib/", "/etc/") if args == (f"--path-policy={name}",) else value

            with (
                self.subTest(name=name, reason="path"),
                self.observe(change),
                patch.object(host.os.path, "lexists", return_value=False),
                self.assertRaises(host.Refusal),
            ):
                host.firewall_policy_prerequisites()

    def test_unknown_dormant_or_mismatched_or_duplicate_inventory_refuses(self):
        for scope in (False, True):
            for suffix in (" dormant-trust", " gateway-lan-to-world", ""):

                def change(args, permanent, value):
                    if args == ("--get-policies",) and permanent == scope:
                        return value + suffix if suffix else value.replace("gateway-lan-to-world", "")
                    return value

                with self.subTest(scope=scope, suffix=suffix), self.observe(change), self.assertRaises(host.Refusal):
                    host.firewall_policy_prerequisites()

    def test_ambiguous_missing_extra_or_multiline_fields_refuse(self):
        name = "gateway-lan-to-world"
        transforms = (
            lambda value: value + "\n  priority: 1000",
            lambda value: value.replace("  disable: yes\n", ""),
            lambda value: value + "\n  future-permit: yes",
            lambda value: value + '\n\trule family="ipv4" accept',
            lambda value: value.replace("  ports:", "  ports"),
            lambda value: value.replace("internal home trusted", "internal home trusted home"),
            lambda value: value.replace(name + " (disabled)", name + " (active, disabled)"),
        )
        for transform in transforms:

            def change(args, scope, value):
                return transform(value) if args == (f"--policy={name}", "--list-all") and not scope else value

            with (
                self.observe(change),
                patch.object(host.os.path, "lexists", return_value=False),
                self.assertRaises(host.Refusal),
            ):
                host.firewall_policy_prerequisites()

    def test_set_order_does_not_matter_and_observations_are_not_cached(self):
        def change(args, scope, value):
            return value.replace("internal home trusted", "trusted internal home").replace("ftp tftp", "tftp ftp")

        with self.observe(change) as firewall, patch.object(host.os.path, "lexists", return_value=False):
            host.firewall_policy_prerequisites()
            count = firewall.call_count
            host.firewall_policy_prerequisites()
            self.assertEqual(firewall.call_count, 2 * count)

    def test_query_failure_refuses_instead_of_treating_error_as_disabled(self):
        with patch.object(host, "run", return_value=subprocess.CompletedProcess([], 2, "yes", "error")):
            with self.assertRaises(host.Refusal):
                host.firewall("--policy=gateway-lan-to-world", "--query-disable")

    def test_unsupported_or_missing_policy_observation_refuses(self):
        for observed in ("", "unknown", "yes\nno"):

            def change(args, scope, value):
                return observed if args == ("--policy=gateway-lan-to-world", "--query-disable") else value

            with (
                self.observe(change),
                patch.object(host.os.path, "lexists", return_value=False),
                self.assertRaises(host.Refusal),
            ):
                host.firewall_policy_prerequisites()


if __name__ == "__main__":
    unittest.main()
