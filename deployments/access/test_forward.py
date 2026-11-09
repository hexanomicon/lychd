"""Client argv and credential-path boundary; no SSH or VPN operations."""

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("forward", Path(__file__).with_name("forward.py"))
forward = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(forward)


class ForwardTests(unittest.TestCase):
    def setUp(self):
        # The execution environment has a repository marker at /tmp itself. Only that
        # infrastructure marker is hidden; fixture checkout markers remain observable.
        original = Path.exists
        self.marker = patch.object(Path, "exists", lambda path: False if path == Path("/tmp/.git") else original(path))
        self.marker.start()
        self.addCleanup(self.marker.stop)

    def test_fixed_loopback_and_strict_host_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            files = [Path(directory) / name for name in ("identity", "known_hosts")]
            for path in files:
                path.touch(mode=0o600)
            argv = forward.command("10.203.71.1", *files)
            self.assertEqual(argv[argv.index("-L") + 1], "127.0.0.1:7134:127.0.0.1:7134")
            self.assertIn("StrictHostKeyChecking=yes", argv)
            self.assertIn("ExitOnForwardFailure=yes", argv)
            self.assertIn("IdentityAgent=none", argv)
            self.assertEqual(argv[-1], "lychd-forward@10.203.71.1")
            files[0].chmod(0o644)
            with self.assertRaises(ValueError):
                forward.command("10.203.71.1", *files)

    def test_public_and_loopback_peers_refused(self):
        for peer in ("8.8.8.8", "127.0.0.1", "::1"):
            with self.subTest(peer=peer), self.assertRaises(ValueError):
                forward.command(peer, "/does/not/exist", "/does/not/exist")

    def test_check_starts_no_ssh_and_reports_only_local_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            files = [Path(directory) / name for name in ("identity", "known_hosts")]
            for path in files:
                path.touch(mode=0o600)
            output = io.StringIO()
            with (
                patch(
                    "sys.argv",
                    [
                        "forward.py",
                        "--peer",
                        "10.203.71.1",
                        "--identity",
                        str(files[0]),
                        "--known-hosts",
                        str(files[1]),
                        "--interface",
                        "lychd-vps",
                        "--check",
                    ],
                ),
                patch.object(
                    forward, "wireguard_route", return_value={"peer": "10.203.71.1", "interface": "lychd-vps"}
                ),
                patch.object(forward.socket, "socket"),
                patch.object(forward.os, "execvp") as execute,
                contextlib.redirect_stdout(output),
            ):
                forward.main()
            execute.assert_not_called()
            self.assertEqual(json.loads(output.getvalue())["ssh_and_browser"], "not tested")

    def test_wrong_or_down_interface_and_fallback_route_refuse(self):
        good = {"flags": ["UP"], "linkinfo": {"info_kind": "wireguard"}}
        cases = [
            ([{"flags": ["UP"], "linkinfo": {"info_kind": "ether"}}], []),
            ([{"flags": [], "linkinfo": {"info_kind": "wireguard"}}], []),
            ([good], [{"dev": "eth0"}]),
            ([good], [{"dev": "lychd-vps", "type": "unreachable"}]),
        ]
        for link, route in cases:
            results = [SimpleNamespace(returncode=0, stdout=json.dumps(value)) for value in (link, route)]
            with (
                patch.object(forward.shutil, "which", return_value="/usr/bin/ip"),
                patch.object(forward.subprocess, "run", side_effect=results),
                self.assertRaises(ValueError),
            ):
                forward.wireguard_route("10.203.71.1", "lychd-vps")
        with (
            patch.object(forward.shutil, "which", return_value="/usr/bin/ip"),
            patch.object(
                forward.subprocess,
                "run",
                side_effect=[
                    SimpleNamespace(returncode=0, stdout=json.dumps(value))
                    for value in ([good], [{"dev": "lychd-vps"}])
                ],
            ),
        ):
            self.assertEqual(forward.wireguard_route("10.203.71.1", "lychd-vps")["interface"], "lychd-vps")

    @unittest.skipUnless(shutil.which("ssh"), "OpenSSH is not installed")
    def test_openssh_parses_private_known_hosts_path_containing_spaces(self):
        with tempfile.TemporaryDirectory(prefix="lychd client ") as directory:
            paths = [Path(directory) / name for name in ("identity", "known hosts")]
            for path in paths:
                path.touch(mode=0o600)
            argv = forward.command("10.203.71.1", *paths)
            result = subprocess.run([argv[0], "-G", *argv[1:]], capture_output=True, text=True, timeout=10, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                str(paths[1]),
                next(line for line in result.stdout.splitlines() if line.startswith("userknownhostsfile ")),
            )
            self.assertIn("passwordauthentication no", result.stdout)


if __name__ == "__main__":
    unittest.main()
