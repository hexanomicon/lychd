"""Private client material and idempotence contracts; never configure a network interface."""

import base64
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import client

SSH_KEY = "ssh-ed25519 " + base64.b64encode(b"\0\0\0\x0bssh-ed25519\0\0\0\x20" + bytes(range(32))).decode()
PRIVATE = base64.b64encode(b"S" * 32).decode()


class ClientTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        original = Path.exists
        marker = patch.object(Path, "exists", lambda path: False if path == Path("/tmp/.git") else original(path))
        marker.start()
        self.addCleanup(marker.stop)
        self.identity, self.key = self.root / "identity", self.root / "wireguard.key"
        for path, contents in (
            (self.identity, "synthetic encrypted SSH private key fixture"),
            (self.key, PRIVATE + "\n"),
        ):
            path.write_text(contents)
            path.chmod(0o600)
        self.config = {
            "schema_version": 1,
            "interface": "lychd-vps",
            "server_address": "10.203.71.1",
            "client_address": "10.203.71.2",
            "endpoint": "vps.example.test:51820",
            "server_wireguard_public_key": base64.b64encode(bytes(range(32))).decode(),
            "server_ssh_host_key": SSH_KEY,
            "ssh_identity": str(self.identity),
            "wireguard_private_key_file": str(self.key),
        }
        self.input = self.root / "client.json"
        self.output = self.root / "generated"
        self.write_input()

    def write_input(self):
        self.input.write_text(json.dumps(self.config))
        self.input.chmod(0o600)

    def test_create_check_and_second_apply_preserve_private_material(self):
        self.assertEqual(client.prepare(self.input, self.output, check=True)["state"], "would_create")
        self.assertFalse(self.output.exists())
        self.assertTrue(client.prepare(self.input, self.output)["changed"])
        before = {p.name: p.stat().st_mtime_ns for p in self.output.iterdir()}
        self.assertFalse(client.prepare(self.input, self.output)["changed"])
        self.assertEqual(before, {p.name: p.stat().st_mtime_ns for p in self.output.iterdir()})
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in self.output.iterdir()))
        contents = (self.output / "lychd-vps.conf").read_text()
        self.assertIn("AllowedIPs = 10.203.71.1/32\n", contents)
        self.assertIn(PRIVATE, contents)
        for forbidden in ("DNS", "SaveConfig", "PostUp", "0.0.0.0/0"):
            self.assertNotIn(forbidden, contents)
        self.assertEqual((self.output / "known_hosts").read_text(), f"[10.203.71.1]:2222 {SSH_KEY}\n")
        self.assertEqual(client.load_connection(self.output / "connection.json")["interface"], "lychd-vps")

    def test_changed_or_incomplete_output_never_overwrites(self):
        client.prepare(self.input, self.output)
        path = self.output / "known_hosts"
        path.write_text("preserve foreign material")
        with self.assertRaises(ValueError):
            client.prepare(self.input, self.output)
        self.assertEqual(path.read_text(), "preserve foreign material")

    def test_unsafe_private_key_and_output_links_refuse(self):
        self.key.chmod(0o644)
        with self.assertRaises(ValueError):
            client.prepare(self.input, self.output)
        self.assertFalse(self.output.exists())
        self.key.chmod(0o600)
        link = self.root / "link"
        link.symlink_to(self.key)
        self.config["wireguard_private_key_file"] = str(link)
        self.write_input()
        with self.assertRaises(OSError):
            client.prepare(self.input, self.output)

    def test_invalid_or_injected_public_input_refuses_before_output(self):
        for field, value in [
            ("interface", "../escape"),
            ("endpoint", "host:51820\nPostUp = bad"),
            ("server_address", "127.0.0.1"),
            ("client_address", "10.203.71.1"),
            ("server_ssh_host_key", "ssh-ed25519 AAAA"),
            ("schema_version", True),
        ]:
            with self.subTest(field=field):
                data = dict(self.config)
                data[field] = value
                with self.assertRaises(ValueError):
                    client.render(data, self.output)
                self.assertFalse(self.output.exists())

    def test_real_checkout_markers_and_duplicate_json_refuse(self):
        (self.root / ".git").write_text("gitdir: private worktree fixture")
        with self.assertRaises(ValueError):
            client.private_path(self.root / "secret")
        with self.assertRaises(ValueError):
            client.unique_object([("name", "a"), ("name", "b")])

    def test_cli_never_prints_wireguard_private_key(self):
        output = io.StringIO()
        with (
            patch("sys.argv", ["client.py", "--config", str(self.input), "--output-directory", str(self.output)]),
            contextlib.redirect_stdout(output),
        ):
            client.main()
        self.assertNotIn(PRIVATE, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["state"], "created")
