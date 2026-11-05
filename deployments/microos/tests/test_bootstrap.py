"""Pure refusal tests. Never invoke provisioning or simulate a root filesystem."""

import base64
import copy
import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("host_bootstrap", ROOT / "combustion/host_bootstrap.py")
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


class BootstrapRefusals(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT / "combustion/host.example.json").read_text())
        self.facts = {
            "euid": 0,
            "offline": True,
            "firstboot": True,
            "combustion_directory": True,
            "microos": True,
            "completed": False,
            "root_btrfs": True,
            "home_btrfs_mount": True,
            "home_free": 25 * 1024**3,
            "account_collision": False,
            "home_exists": False,
            "custom_state": False,
            "selinux_configured": True,
        }

    def test_valid_config_and_fresh_facts(self):
        bootstrap.validate_config(self.cfg)
        bootstrap.validate_host_state(self.cfg, self.facts)

    def test_each_unsafe_host_fact_refuses_before_creation(self):
        for name in self.facts:
            with self.subTest(fact=name):
                facts = self.facts.copy()
                facts[name] = 1000 if name == "euid" else 0 if name == "home_free" else not facts[name]
                with self.assertRaises(bootstrap.Refusal):
                    bootstrap.validate_host_state(self.cfg, facts)

    def test_closed_schema_and_no_shell_or_path_injection(self):
        for field, value in (
            ("schema_version", True),
            ("schema_version", 2),
            ("hostname", "$(id)"),
            ("home_min_free_gib", 1),
        ):
            with self.subTest(field=field, value=value):
                cfg = copy.deepcopy(self.cfg)
                cfg[field] = value
                with self.assertRaises(bootstrap.Refusal):
                    bootstrap.validate_config(cfg)
        for field, value in (
            ("name", "--root"),
            ("uid", 0),
            ("gid", True),
            ("subuid_count", 2**32),
            ("ssh_public_keys", ["../../private_key"]),
            ("ssh_public_keys", ["keys/a.pub", "keys/a.pub"]),
        ):
            with self.subTest(field=field):
                cfg = copy.deepcopy(self.cfg)
                cfg["runtime_user"][field] = value
                with self.assertRaises(bootstrap.Refusal):
                    bootstrap.validate_config(cfg)
        self.cfg["unexpected_command"] = "true"
        with self.assertRaises(bootstrap.Refusal):
            bootstrap.validate_config(self.cfg)

    def test_duplicate_json_keys_refuse(self):
        with self.assertRaises(bootstrap.Refusal):
            json.loads('{"uid": 1000, "uid": 0}', object_pairs_hook=bootstrap.no_duplicates)

    def test_recovery_is_explicit(self):
        self.cfg["recovery_root_ssh"]["enabled"] = False
        with self.assertRaises(bootstrap.Refusal):
            bootstrap.validate_config(self.cfg)

    def test_public_key_bundle_and_separate_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            keys = directory / "keys"
            keys.mkdir()
            prefix = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32)
            runtime = "ssh-ed25519 " + base64.b64encode(prefix + bytes(32)).decode() + " public-fixture\n"
            recovery = "ssh-ed25519 " + base64.b64encode(prefix + bytes([1]) * 32).decode() + " public-fixture\n"
            (keys / "runtime.pub").write_text(runtime)
            (keys / "recovery.pub").write_text(recovery)
            config = directory / "host.json"
            config.write_text(json.dumps(self.cfg))
            cfg, normal, rescue = bootstrap.load_config(config)
            self.assertEqual(cfg, self.cfg)
            self.assertNotEqual(normal, rescue)
            (keys / "recovery.pub").write_text(runtime)
            with self.assertRaisesRegex(bootstrap.Refusal, "distinct"):
                bootstrap.load_config(config)
            (keys / "recovery.pub").unlink()
            (keys / "recovery.pub").symlink_to(keys / "runtime.pub")
            with self.assertRaisesRegex(bootstrap.Refusal, "symlink"):
                bootstrap.load_config(config)

    def test_public_key_rejects_private_material_options_and_malformed_encoding(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "key.pub"
            for text in (
                "-----BEGIN OPENSSH PRIVATE KEY-----\n",
                "command=evil ssh-ed25519 AAAA\n",
                "ssh-ed25519 invalid\n",
                "ssh-ed25519 AAAA\nsecond line\n",
                "ssh-rsa AAAA\n",
            ):
                with self.subTest(text=text):
                    path.write_text(text)
                    with self.assertRaises(bootstrap.Refusal):
                        bootstrap.public_key(path)

    def test_disjoint_and_adjacent_ranges(self):
        bootstrap.validate_ranges("other:100000:65536\n", "lychd", 1000, 165536, 65536, {0, 1000})

    def test_mapping_refusals(self):
        cases = [
            "bad",
            "other:1:0",
            "other:-1:65536",
            "other:١:65536",
            "other:4294967294:2",
            "other:231071:2",
            "other:231072:65536",
            "lychd:100000:65536",
            "1000:100000:65536",
            "a:100000:65536\nb:100001:1",
            "a:1000:1",
        ]
        for text in cases:
            with self.subTest(mapping=text), self.assertRaises(bootstrap.Refusal):
                bootstrap.validate_ranges(text, "lychd", 1000, 231072, 65536, {0, 1000})

    def test_proposed_range_real_id_collision_and_overflow(self):
        for start, count, real in (
            (231072, 65536, {231072}),
            (65535, 65536, set()),
            (231072, 1, set()),
            (2**32 - 2, 65536, set()),
        ):
            with self.subTest(start=start, count=count), self.assertRaises(bootstrap.Refusal):
                bootstrap.validate_ranges("", "lychd", 1000, start, count, real)


if __name__ == "__main__":
    unittest.main()
