"""Pure refusal oracles; never invoke provisioning or probe a target host."""

import base64
import importlib.util
import struct
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROBE = Path(__file__).parents[1] / "roles/tumbleweed_host/files/host_probe.py"
SPEC = importlib.util.spec_from_file_location("host_probe", PROBE)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def fixture_intent():
    raw = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32) + bytes(range(32))
    return {
        "name": "lychd",
        "uid": 1001,
        "gid": 1001,
        "subuid_start": 231072,
        "subgid_start": 231072,
        "count": 65536,
        "keys": ["ssh-ed25519 " + base64.b64encode(raw).decode()],
    }


def mounts():
    text = "\n".join(
        f"{i} 0 0:41 /@{suffix} {path} rw - btrfs /dev/vda2 rw"
        for i, (suffix, path) in enumerate((("", "/"), ("/home", "/home"), ("/var", "/var")), 20)
    )
    return probe.parse_mounts(text)


class IntentTests(unittest.TestCase):
    def test_valid_plain_public_key(self):
        self.assertEqual(probe.validate_intent(fixture_intent())["uid"], 1001)

    def test_empty_keys_fail_before_observation(self):
        value = fixture_intent()
        value["keys"] = []
        with self.assertRaisesRegex(probe.Refusal, "supply"):
            probe.validate_intent(value)

    def test_no_boolean_ids_or_variable_commands(self):
        for key, invalid in (("uid", True), ("subuid_start", "1; id"), ("name", "root"), ("count", 1)):
            value = fixture_intent()
            value[key] = invalid
            with self.subTest(key=key), self.assertRaises(probe.Refusal):
                probe.validate_intent(value)

    def test_reject_options_private_key_and_duplicate_identity(self):
        for keys in (
            ["command=whoami " + fixture_intent()["keys"][0]],
            ["-----BEGIN OPENSSH PRIVATE KEY-----"],
            fixture_intent()["keys"] * 2,
        ):
            value = fixture_intent()
            value["keys"] = keys
            with self.assertRaises(probe.Refusal):
                probe.validate_intent(value)

    def test_reject_bad_public_key_payload(self):
        value = fixture_intent()
        value["keys"] = ["ssh-ed25519 " + base64.b64encode(struct.pack(">I", 11) + b"ssh-ed25519").decode()]
        with self.assertRaisesRegex(probe.Refusal, "ssh-keygen"):
            probe.validate_intent(value)


class AllocationTests(unittest.TestCase):
    def check(self, text, real_ids=None):
        return probe.validate_ranges(text, "lychd", 1001, 231072, 65536, real_ids or {0, 1000, 1001})

    def test_first_run_and_exact_idempotent_mapping(self):
        self.assertFalse(self.check("alice:100000:65536\n"))
        self.assertTrue(self.check("alice:100000:65536\nlychd:231072:65536\n"))

    def test_no_remapping_multiple_own_maps_or_numeric_alias(self):
        for text in ("lychd:300000:65536", "lychd:231072:65536\nlychd:400000:65536", "1001:231072:65536"):
            with self.subTest(text=text), self.assertRaisesRegex(probe.Refusal, "never remap"):
                self.check(text)

    def test_refuse_existing_collisions_and_real_id_coverage(self):
        for text in ("alice:220000:65536", "a:100000:65536\nb:120000:65536", "a:1:65536", "malformed"):
            with self.subTest(text=text), self.assertRaises(probe.Refusal):
                self.check(text)
        with self.assertRaisesRegex(probe.Refusal, "real host ID"):
            self.check("", {250000})

    def test_adjacent_ranges_do_not_overlap(self):
        self.assertFalse(self.check("alice:165536:65536\nbob:296608:65536"))


class ReceiptTests(unittest.TestCase):
    def receipt(self, stage):
        return {
            "schema_version": 1,
            "stage": stage,
            "identity": {k: v for k, v in fixture_intent().items() if k != "keys"},
        }

    def test_fresh_identity_has_no_existing_authority(self):
        self.assertEqual(
            probe.validate_receipt(None, fixture_intent(), False, False, {"uid": False, "gid": False}, False), "absent"
        )
        for account, group, maps, linger in (
            (True, False, {"uid": False, "gid": False}, False),
            (False, True, {"uid": False, "gid": False}, False),
            (False, False, {"uid": True, "gid": False}, False),
            (False, False, {"uid": False, "gid": False}, True),
        ):
            with self.subTest(state=(account, group, maps, linger)), self.assertRaisesRegex(probe.Refusal, "adoption"):
                probe.validate_receipt(None, fixture_intent(), account, group, maps, linger)

    def test_interrupted_pre_map_creation_always_needs_manual_recovery(self):
        # No inferred safety from missing keys, linger, process lists or storage paths.
        for account in (False, True):
            for maps in ({"uid": False, "gid": False}, {"uid": True, "gid": True}):
                with self.subTest(account=account, maps=maps), self.assertRaisesRegex(probe.Refusal, "manual recovery"):
                    probe.validate_receipt(self.receipt("creating"), fixture_intent(), account, True, maps, False)

    def test_initialized_and_configured_missing_maps_refused_even_for_external_graphroot(self):
        # The decision has no graphroot input: default and custom stores cannot bypass it.
        for stage in ("maps_initialized", "configured"):
            for maps in ({"uid": False, "gid": False}, {"uid": True, "gid": False}, {"uid": False, "gid": True}):
                with (
                    self.subTest(stage=stage, maps=maps),
                    self.assertRaisesRegex(probe.Refusal, "regardless of container storage path"),
                ):
                    probe.validate_receipt(self.receipt(stage), fixture_intent(), True, True, maps, True)

    def test_post_map_interruption_can_resume_only_with_exact_retained_identity_and_maps(self):
        for stage in ("maps_initialized", "configured"):
            self.assertEqual(
                probe.validate_receipt(
                    self.receipt(stage), fixture_intent(), True, True, {"uid": True, "gid": True}, False
                ),
                stage,
            )
            with self.assertRaises(probe.Refusal):
                probe.validate_receipt(
                    self.receipt(stage), fixture_intent(), False, True, {"uid": True, "gid": True}, False
                )

    def test_legacy_receipt_and_changed_identity_never_license_remapping(self):
        legacy = {k: v for k, v in fixture_intent().items() if k != "keys"}
        changed = self.receipt("configured")
        changed["identity"]["uid"] += 1
        for value in (legacy, changed):
            with self.subTest(value=value), self.assertRaises(probe.Refusal):
                probe.validate_receipt(value, fixture_intent(), True, True, {"uid": True, "gid": True}, True)


class AuthorityTests(unittest.TestCase):
    def test_home_parent_must_not_allow_runtime_replacement(self):
        probe.validate_mount_parent(SimpleNamespace(st_mode=0o40755, st_uid=0))
        for mode, uid in ((0o40777, 0), (0o40775, 0), (0o40755, 1001), (0o100644, 0)):
            with self.subTest(mode=mode, uid=uid), self.assertRaises(probe.Refusal):
                probe.validate_mount_parent(SimpleNamespace(st_mode=mode, st_uid=uid))

    def test_sudo_policy_accepts_only_explicit_denial(self):
        for code, output, accepted in (
            (1, "User lychd is not allowed to run sudo on pilot.", True),
            (0, "(ALL) ALL", False),
            (1, "policy plugin failure", False),
            (2, "unknown user", False),
        ):
            with (
                self.subTest(code=code, output=output),
                patch.object(probe.shutil, "which", return_value="/usr/bin/sudo"),
                patch.object(
                    probe.subprocess, "run", return_value=SimpleNamespace(returncode=code, stdout=output, stderr="")
                ),
            ):
                if accepted:
                    probe.require_no_sudo()
                else:
                    with self.assertRaisesRegex(probe.Refusal, "runtime sudo grants or indeterminate"):
                        probe.require_no_sudo()

    def test_new_identity_gate_checks_effective_sudo_policy(self):
        account = SimpleNamespace(pw_uid=1001, pw_gid=1001, pw_dir="/home/lychd", pw_shell="/bin/bash")
        group = SimpleNamespace(gr_gid=1001, gr_mem=[])
        with (
            patch.object(probe.os, "geteuid", return_value=0),
            patch.dict(probe.os.environ, {"SUDO_USER": "admin"}),
            patch.object(probe.pwd, "getpwnam", return_value=account),
            patch.object(probe.grp, "getgrnam", return_value=group),
            patch.object(probe.grp, "getgrall", return_value=[group]),
            patch.object(probe, "require_no_sudo", side_effect=probe.Refusal("runtime sudo grants")) as policy,
        ):
            with self.assertRaisesRegex(probe.Refusal, "runtime sudo"):
                probe.observe_identity(fixture_intent())
            policy.assert_called_once_with()


class MountTests(unittest.TestCase):
    def test_distinct_mounted_subvolumes_on_one_filesystem(self):
        probe.validate_mounts(mounts(), {"/": 256, "/home": 256, "/var": 256})

    def test_reject_parent_mount_bind_dir_second_filesystem_readonly_and_duplicate_root(self):
        for change in ("missing", "bind", "device", "readonly", "root"):
            value, inodes = mounts(), {"/": 256, "/home": 256, "/var": 256}
            if change == "missing":
                del value["/var"]
            elif change == "bind":
                inodes["/home"] = 4242
            elif change == "device":
                value["/var"]["device"] = "0:42"
            elif change == "readonly":
                value["/"]["options"] = ["ro"]
            else:
                value["/home"]["root"] = value["/"]["root"]
            with self.subTest(change=change), self.assertRaises(probe.Refusal):
                probe.validate_mounts(value, inodes)

    def test_version_comparison_is_numeric(self):
        for text, expected in (("podman version 5.4.0", True), ("5.10.1", True), ("5.3.9", False), ("invalid", False)):
            self.assertEqual(probe.version_at_least_54(text), expected)


class CliTests(unittest.TestCase):
    def test_malformed_intent_fails_without_host_probe(self):
        with (
            patch("sys.stdin", __import__("io").StringIO("{}")),
            patch("sys.argv", ["host_probe.py", "preflight"]),
            patch.object(probe, "observe") as observe,
            patch("sys.stderr", __import__("io").StringIO()),
        ):
            self.assertEqual(probe.main(), 2)
            observe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
