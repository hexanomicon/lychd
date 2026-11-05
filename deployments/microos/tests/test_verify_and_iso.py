"""Small pure negative controls for verification and packaging boundaries."""

import argparse
import base64
import importlib.util
import json
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


verify = module("verify_host", ROOT / "verify_host.py")
iso = module("build_config_iso", ROOT / "build_config_iso.py")


class VerificationRefusals(unittest.TestCase):
    def test_private_iso_roundtrip_preserves_names_and_excludes_unlisted_files(self):
        with tempfile.TemporaryDirectory() as temp:
            private = Path(temp)
            private.chmod(0o700)
            (private / "keys").mkdir()
            prefix = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32)
            for name, byte in (("runtime", 0), ("recovery", 1)):
                public = "ssh-ed25519 " + base64.b64encode(prefix + bytes([byte]) * 32).decode()
                (private / "keys" / f"{name}.pub").write_text(public + "\n")
            (private / "unlisted-private-file").write_text("must never enter configuration media")
            config = private / "host.json"
            config.write_text((ROOT / "combustion/host.example.json").read_text())
            output = private / "combustion.iso"
            iso.build(config, output)
            with output.open("rb") as image:
                image.seek(16 * 2048)
                descriptor = image.read(2048)
            self.assertEqual(descriptor[1:6], b"CD001")
            self.assertEqual(descriptor[40:72].rstrip(b" "), b"combustion")
            expected = {
                "/combustion/script",
                "/combustion/host_bootstrap.py",
                "/combustion/host.json",
                "/combustion/keys/runtime.pub",
                "/combustion/keys/recovery.pub",
            }
            if shutil.which("xorriso"):
                extracted = private / "extracted"
                subprocess.run(
                    ["xorriso", "-osirrox", "on", "-indev", str(output), "-extract", "/", str(extracted)],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                names = {"/" + str(path.relative_to(extracted)) for path in extracted.rglob("*") if path.is_file()}
                self.assertEqual(
                    json.loads((extracted / "combustion/host.json").read_text()), json.loads(config.read_text())
                )
                self.assertTrue((extracted / "combustion/script").stat().st_mode & 0o111)
            else:
                listing = subprocess.run(
                    ["isoinfo", "-R", "-f", "-i", str(output)], check=True, capture_output=True, text=True, timeout=30
                ).stdout.splitlines()
                names = set(listing) - {"/", "/combustion", "/combustion/keys"}
            self.assertEqual(names, expected)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_container_probe_requires_immutable_id_not_flags_or_tags(self):
        self.assertEqual(verify.local_image_id("sha256:" + "a" * 64), "sha256:" + "a" * 64)
        for value in ("--privileged", "python:latest", "a" * 64, "sha256:" + "A" * 64):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                verify.local_image_id(value)

    def test_effective_storage_cannot_escape_home_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            home.mkdir()
            inside = home / ".local/share/containers/storage"
            self.assertEqual(verify.home_storage_path(home, str(inside), "graphRoot"), inside)
            outside = Path(temp) / "outside"
            outside.mkdir()
            (home / "escape").symlink_to(outside, target_is_directory=True)
            for value in ("relative", str(outside), str(home), str(home / "escape/images")):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    verify.home_storage_path(home, value, "graphRoot")

    def test_versions_require_both_major_and_minor(self):
        for text in ("podman version 5.4.0", "quadlet version 6.0.2"):
            self.assertTrue(verify.version_at_least_54(text))
        for text in ("podman 5.3.9", "4.99", "unknown"):
            self.assertFalse(verify.version_at_least_54(text))

    def test_effective_generator_mask_does_not_fall_through(self):
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp) / "first", Path(temp) / "second"
            first.mkdir()
            second.mkdir()
            (first / "podman-user-generator").symlink_to("/dev/null")
            (second / "podman-user-generator").write_text("#!/bin/sh\nexit 0\n")
            with self.assertRaisesRegex(ValueError, "masked"):
                verify.effective_generator([first, second])

    def test_no_in_repository_private_config_or_iso(self):
        self.assertFalse(iso.outside_checkout(ROOT / "host.json"))
        self.assertFalse(iso.outside_checkout(ROOT / "config.iso"))

    def test_existing_iso_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "config.iso"
            output.write_bytes(b"preserve fixture")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                iso.build(Path(temp) / "host.json", output)
            self.assertEqual(output.read_bytes(), b"preserve fixture")


if __name__ == "__main__":
    unittest.main()
