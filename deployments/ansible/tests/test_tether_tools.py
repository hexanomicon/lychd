"""Prove package preparation effects and independent read-only tool evidence."""

import importlib.util
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).parents[1]
TASKS = ROOT / "roles/lychd_app/tasks"
SPEC = importlib.util.spec_from_file_location("tether_tools", ROOT / "roles/lychd_app/files/tether_tools.py")
TOOLS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOLS)
ENV = Environment(undefined=StrictUndefined)


class ToolPrerequisiteTests(unittest.TestCase):
    def test_only_prepare_can_install_and_check_mode_only_predicts(self):
        rows = yaml.safe_load((TASKS / "tether_tools_prepare.yml").read_text())
        query, prediction, install, verification = rows
        self.assertEqual(query["ansible.builtin.command"]["argv"], ["/usr/bin/rpm", "-q", "wireguard-tools"])
        self.assertFalse(query["check_mode"])
        self.assertFalse(query["changed_when"])
        self.assertEqual(
            install["ansible.builtin.command"]["argv"],
            [
                "/usr/bin/zypper",
                "--non-interactive",
                "--no-refresh",
                "install",
                "--no-recommends",
                "--",
                "wireguard-tools",
            ],
        )
        self.assertTrue(install["changed_when"])
        self.assertNotIn("check_mode", install)
        self.assertEqual(verification["ansible.builtin.import_tasks"], "tether_tools_verify.yml")
        for check in (False, True):
            for code in (0, 1, 2):
                context = {"ansible_check_mode": check, "lychd_tether_tools_package": {"rc": code}}

                def evaluate(expression):
                    return ENV.compile_expression(expression)(**context)

                self.assertEqual(evaluate(query["failed_when"]), code not in (0, 1))
                self.assertEqual(evaluate(prediction["when"]), check and code == 1)
                self.assertEqual(evaluate(install["when"]), not check and code == 1)
                self.assertEqual(evaluate(verification["when"]), not check or code == 0)
        verify = yaml.safe_load((TASKS / "tether_tools_verify.yml").read_text())
        self.assertEqual(len(verify), 1)
        self.assertFalse(verify[0]["changed_when"])
        self.assertFalse(verify[0]["check_mode"])
        self.assertNotIn("when", verify[0])

    def test_kernel_preflight_precedes_package_effect_and_verify_import_is_literal(self):
        prepare = yaml.safe_load((TASKS / "tether_kernel_prepare.yml").read_text())
        self.assertEqual(prepare[0]["ansible.builtin.import_tasks"], "tether_kernel.yml")
        self.assertEqual(prepare[1]["ansible.builtin.import_tasks"], "tether_tools_prepare.yml")
        self.assertIn("modprobe", prepare[2]["ansible.builtin.command"]["argv"][0])
        verify = yaml.safe_load((TASKS / "tether_kernel_verify.yml").read_text())
        self.assertEqual(verify[-1]["ansible.builtin.import_tasks"], "tether_tools_verify.yml")
        self.assertNotIn("when", verify[-1])

    def test_actual_package_file_owner_and_executable_are_observed(self):
        calls = []
        resolved = []

        def resolve(path):
            resolved.append(path)
            return path

        def command(path, *arguments):
            calls.append((path, *arguments))
            return "wireguard-tools v1.0" if path.endswith("/wg") else "wireguard-tools"

        self.assertEqual(TOOLS.observe(command, resolve), {"package_installed": True, "executable_verified": True})
        self.assertEqual(resolved, ["/usr/bin/rpm", "/usr/bin/wg"])
        self.assertEqual(
            calls,
            [
                ("/usr/bin/rpm", "-q", "--qf", "%{NAME}", "wireguard-tools"),
                ("/usr/bin/rpm", "-qf", "--qf", "%{NAME}", "/usr/bin/wg"),
                ("/usr/bin/wg", "--version"),
            ],
        )

    def test_missing_package_foreign_file_owner_or_empty_tool_response_refuses(self):
        for position in range(3):
            responses = ["wireguard-tools", "wireguard-tools", "wireguard-tools v1.0"]
            responses[position] = ""
            with self.subTest(position=position):
                with self.assertRaises(TOOLS.PrerequisiteError):
                    TOOLS.observe(lambda *args: responses.pop(0), lambda path: path)
        with self.assertRaises(FileNotFoundError):
            TOOLS.observe(resolve=lambda path: (_ for _ in ()).throw(FileNotFoundError()))

    def test_command_is_readonly_bounded_and_never_uses_ambient_path(self):
        result = subprocess.CompletedProcess([], 0, "wireguard-tools\n", "")
        with patch.object(TOOLS.subprocess, "run", return_value=result) as called:
            self.assertEqual(TOOLS.run("/usr/bin/rpm", "-q", "wireguard-tools"), "wireguard-tools")
        self.assertEqual(called.call_args.args[0], ["/usr/bin/rpm", "-q", "wireguard-tools"])
        self.assertEqual(called.call_args.kwargs["env"], {"PATH": "/usr/sbin:/usr/bin", "LC_ALL": "C"})
        self.assertEqual(called.call_args.kwargs["timeout"], 20)
        for result in (subprocess.CompletedProcess([], 1, "", ""), subprocess.CompletedProcess([], 0, "x" * 65537, "")):
            with patch.object(TOOLS.subprocess, "run", return_value=result):
                with self.assertRaises(TOOLS.PrerequisiteError):
                    TOOLS.run("/usr/bin/rpm", "-q", "wireguard-tools")

    def test_trusted_executable_refuses_foreign_writable_or_unexecutable_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "wg"
            executable.write_text("fixture")
            for uid, mode, executable_bit, accepted in (
                (0, stat.S_IFREG | 0o755, True, True),
                (1000, stat.S_IFREG | 0o755, True, False),
                (0, stat.S_IFREG | 0o775, True, False),
                (0, stat.S_IFREG | 0o755, False, False),
                (0, stat.S_IFDIR | 0o755, True, False),
            ):
                with (
                    patch.object(Path, "stat", return_value=SimpleNamespace(st_uid=uid, st_mode=mode)),
                    patch.object(TOOLS.os, "access", return_value=executable_bit),
                ):
                    if accepted:
                        self.assertEqual(TOOLS.trusted_executable(str(executable)), str(executable))
                    else:
                        with self.assertRaises(TOOLS.PrerequisiteError):
                            TOOLS.trusted_executable(str(executable))


if __name__ == "__main__":
    unittest.main()
