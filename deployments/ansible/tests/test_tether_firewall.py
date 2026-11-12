"""Host-only UDP prerequisite tests; no host commands or Core imports."""

import importlib.util
import json
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "tether_firewall", Path(__file__).parents[1] / "roles/lychd_app/files/tether_firewall.py"
)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


class Firewall:
    def __init__(self):
        self.calls = []
        self.rows = [{"ifname": "eth0", "addr_info": [{"family": "inet", "local": "192.0.2.7"}]}]
        self.zone = "public"
        self.permanent_zone = "public"
        self.managed = "yes"
        self.saved_zone = "public"
        self.default = "public"
        self.ports = {True: set(), False: set()}

    def __call__(self, tool, *args):
        self.calls.append((tool, *args))
        if tool == "ip":
            assert args == ("-j", "-4", "address", "show")
            return 0, json.dumps(self.rows)
        if tool == "nmcli":
            if args == ("--get-values", "GENERAL.NM-MANAGED", "device", "show", "eth0"):
                return 0, self.managed
            if args == ("--get-values", "GENERAL.CON-UUID", "device", "show", "eth0"):
                return 0, "11111111-1111-1111-1111-111111111111"
            assert args == (
                "--get-values",
                "connection.zone",
                "connection",
                "show",
                "uuid",
                "11111111-1111-1111-1111-111111111111",
            )
            return 0, self.saved_zone
        assert tool == "firewall-cmd"
        permanent = "--permanent" in args
        if args[-1] == "--get-zones":
            return 0, "public internal"
        if args == ("--get-zone-of-interface=eth0",):
            return 0, self.zone
        if args == ("--permanent", "--get-zone-of-interface=eth0"):
            return 0, self.permanent_zone
        if args == ("--get-default-zone",):
            return 0, self.default
        if args[-1].startswith("--query-port="):
            assert "--zone=public" in args
            present = args[-1].split("=", 1)[1] in self.ports[permanent]
            return (0, "yes") if present else (1, "no")
        if args[-1].startswith("--add-port="):
            assert "--zone=public" in args
            self.ports[permanent].add(args[-1].split("=", 1)[1])
            return 0, "success"
        raise AssertionError(args)

    def mutations(self):
        return [row for row in self.calls if any("--add-port=" in word for word in row)]


class HostUDPTests(unittest.TestCase):
    def setUp(self):
        self.firewall = Firewall()
        self.intent = {"rune": {"offered": {"listen_address": "192.0.2.7", "listen_port": 51820}}}

    def test_first_apply_adds_only_exact_missing_entries_second_is_noop(self):
        self.firewall.ports[True].add("22/tcp")
        self.firewall.ports[False].add("22/tcp")
        first = helper.reconcile(self.intent, "public", "prepare", self.firewall)
        self.assertTrue(first["changed"])
        self.assertEqual(
            self.firewall.mutations(),
            [
                ("firewall-cmd", "--permanent", "--zone=public", "--add-port=51820/udp"),
                ("firewall-cmd", "--zone=public", "--add-port=51820/udp"),
            ],
        )
        second = helper.reconcile(self.intent, "public", "prepare", self.firewall)
        self.assertFalse(second["changed"])
        self.assertEqual(len(self.firewall.mutations()), 2)
        self.assertEqual(self.firewall.ports, {True: {"22/tcp", "51820/udp"}, False: {"22/tcp", "51820/udp"}})
        self.assertEqual(second["provider_firewall"], "not_observed")

    def test_check_mode_plans_both_without_effects(self):
        report = helper.reconcile(self.intent, "public", "plan", self.firewall)
        self.assertEqual(report["planned"], ["permanent", "runtime"])
        self.assertFalse(report["changed"])
        self.assertEqual(self.firewall.mutations(), [])

    def test_verification_refuses_missing_rule_without_repair(self):
        with self.assertRaisesRegex(helper.PrerequisiteError, "missing"):
            helper.reconcile(self.intent, "public", "verify", self.firewall)
        self.assertEqual(self.firewall.mutations(), [])

    def test_unbound_interface_uses_explicit_default_zone_observation(self):
        for unbound in ("", "no zone"):
            with self.subTest(unbound=unbound):
                self.firewall.zone = unbound
                helper.reconcile(self.intent, "public", "plan", self.firewall)
                self.assertIn(("firewall-cmd", "--get-default-zone"), self.firewall.calls)

    def test_zone_mismatch_never_mutates(self):
        self.firewall.zone = "internal"
        with self.assertRaisesRegex(helper.PrerequisiteError, "differs"):
            helper.reconcile(self.intent, "public", "prepare", self.firewall)
        self.assertEqual(self.firewall.mutations(), [])

    def test_missing_or_duplicate_address_is_refused(self):
        for rows in (
            [],
            self.firewall.rows * 2,
            self.firewall.rows + [{"ifname": "eth1", "addr_info": self.firewall.rows[0]["addr_info"]}],
        ):
            with self.subTest(rows=rows), self.assertRaisesRegex(helper.PrerequisiteError, "exactly once"):
                self.firewall.rows = rows
                helper.reconcile(self.intent, "public", "prepare", self.firewall)
        self.assertEqual(self.firewall.mutations(), [])

    def test_wildcard_or_missing_explicit_zone_is_refused_before_commands(self):
        for address, zone in [("0.0.0.0", "public"), ("127.0.0.1", "public"), ("192.0.2.7", "")]:
            self.intent["rune"]["offered"]["listen_address"] = address
            with self.assertRaises(helper.PrerequisiteError):
                helper.reconcile(self.intent, zone, "prepare", self.firewall)
        self.assertEqual(self.firewall.calls, [])

    def test_no_offered_network_does_not_touch_firewall(self):
        result = helper.reconcile({"rune": {"offered": None}}, "", "prepare", self.firewall)
        self.assertEqual(result["state"], "not_required")
        self.assertEqual(self.firewall.calls, [])

    def test_unknown_query_exit_is_not_treated_as_missing(self):
        def command(tool, *args):
            if args[-1].startswith("--query-port="):
                return 252, "error"
            return self.firewall(tool, *args)

        with self.assertRaisesRegex(helper.PrerequisiteError, "query"):
            helper.reconcile(self.intent, "public", "prepare", command)
        self.assertEqual(self.firewall.mutations(), [])

    def test_already_permanent_adds_runtime_only(self):
        self.firewall.ports[True].add("51820/udp")
        helper.reconcile(self.intent, "public", "prepare", self.firewall)
        self.assertEqual(self.firewall.mutations(), [("firewall-cmd", "--zone=public", "--add-port=51820/udp")])

    def test_zone_drift_between_observation_and_addition_refuses_effect(self):
        observations = 0

        def command(tool, *args):
            nonlocal observations
            if args == ("--get-zone-of-interface=eth0",):
                observations += 1
                if observations > 1:
                    return 0, "internal"
            return self.firewall(tool, *args)

        with self.assertRaisesRegex(helper.PrerequisiteError, "differs"):
            helper.reconcile(self.intent, "public", "prepare", command)
        self.assertEqual(self.firewall.mutations(), [])

    def test_permanent_interface_zone_mismatch_refuses_all_additions(self):
        self.firewall.permanent_zone = "drop"
        with self.assertRaisesRegex(helper.PrerequisiteError, "permanent zone differs"):
            helper.reconcile(self.intent, "public", "prepare", self.firewall)
        self.assertEqual(self.firewall.mutations(), [])

    def test_networkmanager_saved_zone_mismatch_refuses_all_additions(self):
        self.firewall.saved_zone = "internal"
        with self.assertRaisesRegex(helper.PrerequisiteError, "NetworkManager connection zone differs"):
            helper.reconcile(self.intent, "public", "prepare", self.firewall)
        self.assertEqual(self.firewall.mutations(), [])

    def test_networkmanager_default_and_permanent_default_are_observed(self):
        self.firewall.permanent_zone = "no zone"
        self.firewall.saved_zone = ""
        helper.reconcile(self.intent, "public", "plan", self.firewall)
        self.assertIn(("firewall-cmd", "--permanent", "--get-zone-of-interface=eth0"), self.firewall.calls)
        self.assertEqual(self.firewall.calls.count(("firewall-cmd", "--get-default-zone")), 2)
        self.assertEqual(self.firewall.mutations(), [])

    def test_unmanaged_interface_refuses_unknown_persistent_ownership(self):
        self.firewall.managed = "no"
        with self.assertRaisesRegex(helper.PrerequisiteError, "NetworkManager-managed"):
            helper.reconcile(self.intent, "public", "prepare", self.firewall)
        self.assertEqual(self.firewall.mutations(), [])
