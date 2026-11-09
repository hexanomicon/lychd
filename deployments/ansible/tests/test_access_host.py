"""Offline refusal/render contracts, not installed-host acceptance."""

import base64
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PATH = Path(__file__).parents[1] / "roles/host_access/files/access_host.py"
SPEC = importlib.util.spec_from_file_location("access_host", PATH)
host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(host)


def intent():
    return {
        "server_address": "10.203.71.1/32",
        "peer_address": "10.203.71.2/32",
        "peer_public_key": base64.b64encode(bytes(range(32))).decode(),
        "ssh_public_key": "ssh-ed25519 "
        + base64.b64encode(b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + bytes(range(32))).decode(),
        "external_interface": "eth0",
        "external_zone": "public",
        "udp_port": 51820,
    }


class HostAccessTests(unittest.TestCase):
    def test_exact_public_intent(self):
        self.assertEqual(host.validate(intent()), intent())

    def test_broad_routes_and_public_or_loopback_addresses_refuse(self):
        for address in ("0.0.0.0/0", "10.203.71.0/24", "127.0.0.1/32", "8.8.8.8/32", "::1/128"):
            with self.subTest(address=address), self.assertRaises(host.Refusal):
                host.validate({**intent(), "peer_address": address})

    def test_duplicate_address_and_injected_fields_refuse(self):
        for change in (
            {"peer_address": "10.203.71.1/32"},
            {"external_zone": "public\ntrusted"},
            {"ssh_public_key": 'command="sh" ssh-ed25519 AAAA'},
            {"udp_port": True},
            {"peer_public_key": "invalid"},
            {"private_key": "secret"},
        ):
            with self.subTest(change=change), self.assertRaises(host.Refusal):
                host.validate({**intent(), **change})

    def test_render_has_exact_routes_and_no_extra_effects(self):
        files = host.render(intent(), "HOST_ONLY_SECRET")
        wg = files[host.WG]
        self.assertIn("AllowedIPs = 10.203.71.2/32\n", wg)
        for forbidden in ("PostUp", "PreUp", "SaveConfig", "DNS", "0.0.0.0/0", "Endpoint"):
            self.assertNotIn(forbidden, wg)
        ssh = files[host.ROOT / "sshd_config"]
        for required in (
            "MaxSessions 0",
            "PermitOpen 127.0.0.1:7134",
            "PermitListen none",
            "AllowStreamLocalForwarding no",
            "ListenAddress 10.203.71.1",
            "AllowTcpForwarding local",
            "AllowAgentForwarding no",
        ):
            self.assertIn(required + "\n", ssh)
        self.assertNotIn("HOST_ONLY_SECRET", ssh)
        self.assertIn("KillMode=control-group", files[host.UNIT])
        self.assertIn("BindsTo=firewalld.service\n", files[host.WG_DROPIN])
        self.assertIn("After=firewalld.service\n", files[host.WG_DROPIN])
        self.assertIn("BindsTo=wg-quick@lychd-wg.service firewalld.service\n", files[host.UNIT])
        for unit_text in (files[host.UNIT], files[host.WG_DROPIN]):
            self.assertIn("ConditionPathExists=!/etc/lychd-access/revoked.json\n", unit_text)

    def test_key_wire_format_refuses_before_any_command(self):
        valid = base64.b64decode(intent()["ssh_public_key"].split()[1])
        invalid = [
            valid[:-1],
            valid + b"x",
            b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + bytes(32),
            valid.replace(b"ssh-ed25519", b"ssh-rsa0000"),
        ]
        for blob in invalid:
            with self.subTest(blob=blob), patch.object(host, "run") as run, self.assertRaises(host.Refusal):
                host.validate({**intent(), "ssh_public_key": "ssh-ed25519 " + base64.b64encode(blob).decode()})
            run.assert_not_called()
        with self.assertRaises(host.Refusal):
            host.validate({**intent(), "peer_public_key": base64.b64encode(bytes(32)).decode()})

    def test_selinux_port_type_requires_explicit_exact_port(self):
        self.assertTrue(host.ssh_port_admitted("ssh_port_t tcp 22, 2222\n"))
        self.assertFalse(host.ssh_port_admitted("ssh_port_t tcp 2200-2300\n"))
        self.assertFalse(host.ssh_port_admitted("ssh_port_t tcp 22, 12222\n"))
        self.assertFalse(host.ssh_port_admitted("other_port_t tcp 2222\nssh_port_t udp 2222\n"))

    def test_selinux_preflight_refuses_unadmitted_port_without_changes(self):
        def response(args):
            return SimpleNamespace(stdout="Enforcing\n" if args[0] == "getenforce" else "ssh_port_t tcp 22\n")

        with (
            patch.object(host.shutil, "which", return_value="/usr/bin/tool"),
            patch.object(host, "run", side_effect=response) as run,
            self.assertRaises(host.Refusal),
        ):
            host.selinux_prerequisites(False)
        self.assertEqual([call.args[0] for call in run.call_args_list], [["getenforce"], ["semanage", "port", "-l"]])

    def test_firewall_is_exact_peer_destination_and_transport(self):
        udp, ssh = host.rules(intent())
        self.assertIn('port="51820" protocol="udp"', udp)
        self.assertIn('source address="10.203.71.2/32"', ssh)
        self.assertIn('destination address="10.203.71.1/32"', ssh)
        self.assertIn('port="2222" protocol="tcp"', ssh)

    def test_partial_and_changed_intent_refuse_before_commands(self):
        for receipt in (
            {"complete": False, "intent": intent()},
            {"complete": True, "intent": {**intent(), "udp_port": 51821}},
        ):
            with patch.object(host, "run") as run, self.assertRaises(host.Refusal):
                host.verify(intent(), receipt)
            run.assert_not_called()

    def test_disabled_owned_service_is_never_restarted(self):
        receipt = {"complete": True, "intent": intent(), "files": {}, "uid": 1234}

        def observed(args, **kwargs):
            if args[0] == "sudo":
                return SimpleNamespace(stdout="User lychd-forward is not allowed to run sudo on test.\n", stderr="")
            return SimpleNamespace(stdout="inactive\n", stderr="")

        with (
            patch.object(host, "prerequisites"),
            patch.object(host, "effective_ssh"),
            patch.object(host, "verify_units_owned"),
            patch.object(host.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=1234, pw_shell="/usr/sbin/nologin")),
            patch.object(host, "run", side_effect=observed) as run,
            self.assertRaises(host.Refusal),
        ):
            host.verify(intent(), receipt)
        self.assertEqual(run.call_args_list[-1].args[0], ["systemctl", "is-active", host.UNITS[0]])
        self.assertFalse(any("start" in call.args[0] or "enable" in call.args[0] for call in run.call_args_list))

    def test_negative_firewall_query_is_an_observation(self):
        with patch.object(host, "run", return_value=SimpleNamespace(returncode=1, stdout="no\n")):
            self.assertEqual(host.firewall("--zone=lychd-access", "--query-masquerade"), "no")

    def test_completed_intent_uses_read_only_verification(self):
        receipt = {"complete": True, "intent": intent(), "public": {"wireguard_public_key": "PUBLIC"}}
        with (
            patch.object(host, "ROOT") as root,
            patch.object(host, "RECEIPT") as path,
            patch.object(host, "load_owned_receipt", return_value=receipt),
            patch.object(host.os.path, "lexists", return_value=False),
            patch.object(host, "verify") as verify,
            patch.object(host, "run") as run,
        ):
            root.exists.return_value = True
            root.lstat.return_value = SimpleNamespace(st_mode=0o40711, st_uid=0)
            path.is_file.return_value = True
            path.read_text.return_value = host.json.dumps(receipt)
            result = host.operate("apply", intent())
            verify.assert_called_once_with(intent(), receipt)
            run.assert_not_called()
            self.assertFalse(result["changed"])
            self.assertEqual(result["state"], "verified")


if __name__ == "__main__":
    unittest.main()
