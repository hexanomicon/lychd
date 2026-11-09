"""Boundary tests for profile intent; these are not AutoYaST installation tests."""

from __future__ import annotations

import base64
import contextlib
import copy
import importlib.util
import io
import json
import os
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "generate.py"
SPEC = importlib.util.spec_from_file_location("autoyast_generate", MODULE)
generator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = generator
SPEC.loader.exec_module(generator)
NS = {"a": generator.NS}
TYPE = f"{{{generator.CONFIG_NS}}}type"
# Synthetic wire data, no usable private key; synthetic hash, no chosen password.
KEY_BLOB = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32) + bytes(range(32))
KEY = "ssh-ed25519 " + base64.b64encode(KEY_BLOB).decode() + " test<&>"
HASH = "$6$testfixture$" + "A" * 86


def intent():
    return {
        "schema_version": 1,
        "architecture": "x86_64",
        "role": "server",
        "firmware": "bios",
        "disk": {"device": "/dev/vda", "erase_all": True},
        "hostname": "pilot",
        "timezone": "UTC",
        "keyboard": "us",
        "swap_gib": 2,
        "admin": {"name": "operator", "public_key": KEY},
        "network": {"interface": "ens3", "mode": "dhcp"},
    }


def profile(data=None):
    return ET.fromstring(generator.render(generator.parse_config(data or intent()), HASH))


def content(root, path):
    return root.findtext("/".join("a:" + part for part in path.split("/")), namespaces=NS)


class InputTests(unittest.TestCase):
    def test_examples_are_deliberately_not_deployable(self):
        for path in (MODULE.parent / "examples").glob("*.json"):
            with self.subTest(example=path.name), self.assertRaises(generator.Refusal):
                generator.parse_config(json.loads(path.read_text()))

    def test_unknown_fields_cannot_enable_unattended_or_scripts(self):
        for field in ("confirm", "scripts", "packages", "root_password", "encryption"):
            data = intent()
            data[field] = False
            with self.subTest(field=field), self.assertRaises(generator.Refusal):
                generator.parse_config(data)

    def test_types_architecture_and_firmware_refuse(self):
        for field, value in (
            ("schema_version", True),
            ("schema_version", 2),
            ("architecture", "aarch64"),
            ("swap_gib", True),
            ("swap_gib", -1),
            ("swap_gib", 33),
            ("firmware", "auto"),
            ("role", "minimal"),
            ("hostname", "a\nb"),
        ):
            data = intent()
            data[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(generator.Refusal):
                generator.parse_config(data)

    def test_disk_must_be_explicit_whole_device(self):
        for value in (
            "auto",
            "/dev/sda1",
            "/dev/nvme0n1p1",
            "/dev/disk/by-id/ata-disk-part1",
            "/dev/disk/by-id/../sda",
            "/dev/null",
            "/dev/sr0",
            "/dev/vda;reboot",
        ):
            data = intent()
            data["disk"]["device"] = value
            with self.subTest(value=value), self.assertRaises(generator.Refusal):
                generator.parse_config(data)
        for value in (False, "true", 1):
            data = intent()
            data["disk"]["erase_all"] = value
            with self.subTest(erase=value), self.assertRaises(generator.Refusal):
                generator.parse_config(data)

    def test_realistic_explicit_disk_shapes(self):
        for value in ("/dev/sda", "/dev/vda", "/dev/nvme0n1", "/dev/disk/by-id/virtio-pilot_disk"):
            data = intent()
            data["disk"]["device"] = value
            self.assertEqual(generator.parse_config(data).disk, value)

    def test_admin_is_not_runtime_or_root_and_cannot_inject_sudo(self):
        for value in ("lychd", "root", "operator ALL=(ALL) NOPASSWD:ALL", "user\nroot"):
            data = intent()
            data["admin"]["name"] = value
            with self.subTest(value=value), self.assertRaises(generator.Refusal):
                generator.parse_config(data)

    def test_private_keys_options_and_corrupt_wire_keys_refuse(self):
        for value in (
            "-----BEGIN OPENSSH PRIVATE KEY-----",
            'command="x" ' + KEY,
            "ssh-ed25519 AAAA",
            KEY + "\n" + KEY,
            "ssh-ed25519 " + base64.b64encode(KEY_BLOB + b"extra").decode(),
        ):
            with self.subTest(value=value[:30]), self.assertRaises(generator.Refusal):
                generator.public_key(value)

    def test_password_plaintext_locks_and_multiline_refuse(self):
        for value in ("password", "!", "REPLACE", HASH + "\nmore", "$6$salt$short"):
            with self.subTest(value=value[:15]), self.assertRaises(generator.Refusal):
                generator.password_hash(value)

    def test_duplicate_json_refuses(self):
        with self.assertRaises(generator.Refusal):
            json.loads('{"schema_version":1,"schema_version":2}', object_pairs_hook=generator.unique_object)

    def test_static_ipv4_and_negative_cases(self):
        data = intent()
        data["network"] = {
            "mode": "static",
            "interface": "ens3",
            "address": "192.0.2.10/24",
            "gateway": "192.0.2.1",
            "nameservers": ["192.0.2.53"],
        }
        self.assertEqual(generator.parse_config(data).network.gateway, "192.0.2.1")
        cases = [
            ("gateway", 3221225985),
            ("gateway", "198.51.100.1"),
            ("gateway", "192.0.2.10"),
            ("gateway", "192.0.2.255"),
            ("address", "192.0.2.10/32"),
            ("address", "2001:db8::1/64"),
            ("address", "192.0.2.10"),
            ("nameservers", []),
            ("nameservers", [123]),
            ("nameservers", ["127.0.0.1"]),
        ]
        for field, value in cases:
            invalid = copy.deepcopy(data)
            invalid["network"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(generator.Refusal):
                generator.parse_config(invalid)

    def test_dhcp_cannot_silently_discard_static_fields_or_wifi(self):
        data = intent()
        data["network"]["gateway"] = "192.0.2.1"
        with self.assertRaises(generator.Refusal):
            generator.parse_config(data)
        data = intent()
        data["network"]["interface"] = "wlan0"
        with self.assertRaises(generator.Refusal):
            generator.parse_config(data)


class OutputTests(unittest.TestCase):
    def setUp(self):
        # Some test hosts make /tmp itself a repository. Simulate a non-repository
        # temporary root, while retaining real marker checks inside every fixture.
        original_exists = Path.exists
        root_marker = Path(tempfile.gettempdir()) / ".git"

        def exists(path):
            return False if path == root_marker else original_exists(path)

        patcher = patch.object(Path, "exists", exists)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_confirmation_no_scripts_and_shared_pool(self):
        root = profile()
        self.assertEqual(content(root, "general/mode/confirm"), "true")
        self.assertIsNone(root.find("a:scripts", NS))
        self.assertEqual(content(root, "partitioning/drive/device"), "/dev/vda")
        self.assertEqual(content(root, "partitioning/drive/enable_snapshots"), "true")
        parts = root.findall("a:partitioning/a:drive/a:partitions/a:partition", NS)
        btrfs = [p for p in parts if content(p, "filesystem") == "btrfs"]
        self.assertEqual(len(btrfs), 1)
        self.assertEqual(content(btrfs[0], "size"), "max")
        paths = {p.text for p in btrfs[0].findall("a:subvolumes/a:subvolume", NS)}
        self.assertTrue({"home", "var"}.issubset(paths))
        self.assertEqual(content(root, "services-manager/default_target"), "multi-user")

    def test_bios_boot_partition_and_string_boolean(self):
        root = profile()
        self.assertEqual(content(root, "bootloader/loader_type"), "grub2")
        self.assertEqual(content(root, "partitioning/drive/partitions/partition/partition_id"), "263")
        flag = root.find("a:bootloader/a:global/a:boot_mbr", NS)
        self.assertEqual(flag.text, "true")
        self.assertNotIn(TYPE, flag.attrib)

    def test_uefi_kde_and_secure_boot(self):
        data = intent()
        data.update(role="workstation", firmware="uefi")
        root = profile(data)
        self.assertEqual(content(root, "bootloader/loader_type"), "grub2-efi")
        self.assertEqual(content(root, "bootloader/global/secure_boot"), "true")
        self.assertEqual(content(root, "partitioning/drive/partitions/partition/mount"), "/boot/efi")
        self.assertEqual(content(root, "partitioning/drive/partitions/partition/size"), "1GiB")
        self.assertEqual(content(root, "services-manager/default_target"), "graphical")
        self.assertIn("kde", [x.text for x in root.findall("a:software/a:patterns/a:pattern", NS)])
        self.assertIn("sddm", [x.text for x in root.findall("a:services-manager/a:services/a:enable/a:service", NS)])

    def test_network_security_and_privilege_contract(self):
        root = profile()
        self.assertEqual(content(root, "networking/backend"), "network_manager")
        self.assertEqual(content(root, "security/selinux_mode"), "enforcing")
        users = root.findall("a:users/a:user", NS)
        self.assertEqual(content(users[0], "user_password"), "!")
        self.assertEqual(content(users[1], "username"), "operator")
        self.assertEqual(content(users[1], "authorized_keys/listentry"), KEY)
        files = {content(f, "file_path"): content(f, "file_contents") for f in root.findall("a:files/a:file", NS)}
        sudo = files["/etc/sudoers"]
        self.assertNotIn("targetpw", sudo)
        self.assertNotIn("NOPASSWD", sudo)
        self.assertNotIn("lychd", sudo)
        self.assertEqual([line.split()[0] for line in sudo.splitlines() if "ALL=" in line], ["root", "operator"])
        ssh = files["/etc/ssh/sshd_config"]
        self.assertIn("PasswordAuthentication no\n", ssh)
        self.assertIn("PermitRootLogin no\n", ssh)

    def test_deterministic_serialization_escapes_text(self):
        data = intent()
        output = generator.render(generator.parse_config(data), HASH)
        self.assertEqual(output, generator.render(generator.parse_config(data), HASH))
        self.assertIn(b"test&lt;&amp;&gt;", output)
        self.assertNotIn(b"<!ENTITY", output)

    def test_cli_private_output_and_refusal_to_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            config = directory / "host.json"
            secret = directory / "admin.hash"
            output = directory / "autoinst.xml"
            config.write_text(json.dumps(intent()))
            secret.write_text(HASH)
            secret.chmod(0o600)
            argv = ["--config", str(config), "--password-hash-file", str(secret), "--output", str(output)]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(generator.main(argv), 0)
                before = output.read_bytes()
                self.assertEqual(generator.main(argv), 2)
            self.assertEqual(output.read_bytes(), before)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(os.listdir(directory).count("autoinst.xml"), 1)

    def test_secret_public_mode_and_symlink_refuse_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            secret = directory / "admin.hash"
            secret.write_text(HASH)
            secret.chmod(0o644)
            with self.assertRaises(generator.Refusal):
                generator.read_private_hash(secret)
            secret.chmod(0o600)
            link = directory / "link"
            link.symlink_to(secret)
            with self.assertRaises(OSError):
                generator.read_private_hash(link)

    def test_cli_refuses_repository_or_relative_paths(self):
        for output in ("relative.xml", str(MODULE.parent / "private.xml")):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(
                    generator.main(
                        [
                            "--config",
                            "/tmp/unused-host.json",
                            "--password-hash-file",
                            "/tmp/unused.hash",
                            "--output",
                            output,
                        ]
                    ),
                    2,
                )
            self.assertFalse((MODULE.parent / "private.xml").exists())

    def test_other_checkout_and_worktree_markers_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for kind in ("checkout", "worktree"):
                repo = root / kind
                nested = repo / "nested" / "private"
                nested.mkdir(parents=True)
                marker = repo / ".git"
                if kind == "checkout":
                    marker.mkdir()
                else:
                    marker.write_text("gitdir: /unused/metadata\n")
                with self.subTest(kind=kind), self.assertRaises(generator.Refusal):
                    generator.require_private_path(nested / "autoinst.xml")
            generator.require_private_path(root / "outside.xml")


if __name__ == "__main__":
    unittest.main()
