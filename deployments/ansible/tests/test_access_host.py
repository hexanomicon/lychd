"""Offline refusal/render contracts, not installed-host acceptance."""

import base64
import importlib.util
import subprocess
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


SSH_RESTRICTIONS = {
    "MaxSessions": "0",
    "AllowTcpForwarding": "local",
    "PermitOpen": "127.0.0.1:7134",
    "PermitListen": "none",
    "AllowStreamLocalForwarding": "no",
    "PasswordAuthentication": "no",
    "KbdInteractiveAuthentication": "no",
    "AllowAgentForwarding": "no",
    "X11Forwarding": "no",
    "PermitTTY": "no",
    "PermitTunnel": "no",
    "AllowUsers": "lychd-forward",
}


def ssh_transcript(*, lowercase=False, changes=None, omitted=None):
    settings = {**SSH_RESTRICTIONS, **(changes or {})}
    # dump_config emits these unrelated list directives on multiple lines.
    extra = "HostKey /test/key-one\nHostKey /test/key-two\nAcceptEnv LANG\nAcceptEnv LC_*\n"
    if lowercase:
        extra = extra.replace("HostKey", "hostkey").replace("AcceptEnv", "acceptenv")
    return (
        extra
        + "\n".join(f"{key.lower() if lowercase else key} {value}" for key, value in settings.items() if key != omitted)
        + "\n"
    )


class EffectiveSSHTests(unittest.TestCase):
    def observe(self, output):
        def response(args):
            return SimpleNamespace(stdout=output if "-T" in args else "")

        return patch.object(host, "run", side_effect=response)

    def test_lowercase_and_camelcase_equivalent_with_legitimate_repeated_lists(self):
        for lowercase in (False, True):
            with self.subTest(lowercase=lowercase), self.observe(ssh_transcript(lowercase=lowercase)) as run:
                host.effective_ssh()
            self.assertEqual(
                [call.args[0] for call in run.call_args_list],
                [["sshd", flag, "-f", str(host.ROOT / "sshd_config")] for flag in ("-t", "-T")],
            )

    def test_every_restriction_mismatch_refuses_in_both_output_styles(self):
        changes = {
            "MaxSessions": "1",
            "AllowTcpForwarding": "yes",
            "PermitOpen": "any",
            "PermitListen": "any",
            "AllowStreamLocalForwarding": "yes",
            "PasswordAuthentication": "yes",
            "KbdInteractiveAuthentication": "yes",
            "AllowAgentForwarding": "yes",
            "X11Forwarding": "yes",
            "PermitTTY": "yes",
            "PermitTunnel": "yes",
            "AllowUsers": "root",
        }
        for lowercase in (False, True):
            for key, value in changes.items():
                with (
                    self.subTest(lowercase=lowercase, key=key),
                    self.observe(ssh_transcript(lowercase=lowercase, changes={key: value})),
                    self.assertRaises(host.Refusal),
                ):
                    host.effective_ssh()

    def test_every_missing_restriction_refuses(self):
        for key in SSH_RESTRICTIONS:
            with self.subTest(key=key), self.observe(ssh_transcript(omitted=key)), self.assertRaises(host.Refusal):
                host.effective_ssh()

    def test_case_insensitive_duplicates_of_checked_settings_refuse_even_if_equal(self):
        for key, value in SSH_RESTRICTIONS.items():
            for duplicate in (value, "foreign"):
                output = ssh_transcript() + f"{key.lower()} {duplicate}\n"
                with self.subTest(key=key, duplicate=duplicate), self.observe(output), self.assertRaises(host.Refusal):
                    host.effective_ssh()

    def test_malformed_required_values_refuse(self):
        for key in SSH_RESTRICTIONS:
            for malformed in (key, key + " \t", key + "=no"):
                output = ssh_transcript(omitted=key) + malformed + "\n"
                with self.subTest(key=key, malformed=malformed), self.observe(output), self.assertRaises(host.Refusal):
                    host.effective_ssh()

    def test_values_keep_exact_case_and_destination_semantics(self):
        for changes in (
            {"AllowUsers": "LYCHD-FORWARD"},
            {"AllowUsers": "lychd-forward root"},
            {"AllowTcpForwarding": "LOCAL"},
            {"PermitOpen": "localhost:7134"},
            {"PermitOpen": "127.0.0.1:7134 127.0.0.1:22"},
        ):
            with (
                self.subTest(changes=changes),
                self.observe(ssh_transcript(changes=changes)),
                self.assertRaises(host.Refusal),
            ):
                host.effective_ssh()

    def test_mixed_case_keys_and_whitespace_keep_the_same_restrictions(self):
        output = "\n" + "\n".join(f"\t{key.swapcase()}\t{value}  " for key, value in SSH_RESTRICTIONS.items()) + "\n"
        with self.observe(output):
            host.effective_ssh()


class CommandObservationTests(unittest.TestCase):
    def test_single_argument_success_returns_the_subprocess_result(self):
        result = subprocess.CompletedProcess(["getenforce"], 0, "Enforcing\n", "")
        with patch.object(host.subprocess, "run", return_value=result) as execute:
            self.assertIs(host.run(["getenforce"]), result)
        execute.assert_called_once_with(
            ["getenforce"],
            input=None,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
        )

    def test_single_argument_failure_is_a_refusal_not_an_index_error(self):
        result = subprocess.CompletedProcess(["getenforce"], 1, "PRIVATE_STDOUT", "PRIVATE_STDERR")
        with patch.object(host.subprocess, "run", return_value=result), self.assertRaises(host.Refusal) as caught:
            host.run(["getenforce"])
        self.assertEqual(str(caught.exception), "command refused: getenforce")

    def test_allowed_failure_preserves_the_original_result(self):
        result = subprocess.CompletedProcess(["getenforce"], 1, "observation", "diagnostic")
        with patch.object(host.subprocess, "run", return_value=result):
            self.assertIs(host.run(["getenforce"], allow_failure=True), result)

    def test_failure_diagnostic_never_contains_arguments_input_or_captured_output(self):
        args = ["tool", "PRIVATE_ARGUMENT", "--private=VALUE"]
        result = subprocess.CompletedProcess(args, 2, "PRIVATE_STDOUT", "PRIVATE_STDERR")
        with patch.object(host.subprocess, "run", return_value=result), self.assertRaises(host.Refusal) as caught:
            host.run(args, data="PRIVATE_STDIN")
        self.assertEqual(str(caught.exception), "command refused: tool")


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
