"""Offline authority and admission-order checks; requires controller PyYAML."""

import unittest
from pathlib import Path

import yaml

TASKS = Path(__file__).parents[1] / "roles/tumbleweed_host/tasks/host.yml"


def flattened(tasks, user="root"):
    """Resolve the effective become user inherited through nested task blocks."""
    for task in tasks:
        effective_user = task.get("become_user", user)
        if "block" in task:
            yield from flattened(task["block"], effective_user)
        else:
            yield task, effective_user


class HostAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = list(flattened(yaml.safe_load(TASKS.read_text())))

    def test_all_home_writes_and_relabels_run_as_runtime_user(self):
        inspected = 0
        for task, user in self.tasks:
            action = next((k for k in task if k.startswith("ansible.builtin.")), "")
            args = task.get(action, {})
            path = args.get("path", args.get("dest", ""))
            argv = args.get("argv", [])
            home_write = action in {"ansible.builtin.file", "ansible.builtin.copy"} and path.startswith("/home/")
            relabel = isinstance(argv, list) and "/usr/sbin/restorecon" in argv
            if home_write or relabel:
                inspected += 1
                self.assertEqual(user, "lychd", task["name"])
        self.assertGreaterEqual(inspected, 5)

    def test_creation_is_gated_before_maps_and_runtime_access(self):
        useradd, identity, maps_check, initialized, runtime_files, linger = [], [], [], [], [], []
        for i, (task, user) in enumerate(self.tasks):
            argv = task.get("ansible.builtin.command", {}).get("argv", [])
            content = task.get("ansible.builtin.copy", {}).get("content", "")
            if isinstance(argv, list):
                if "/usr/sbin/useradd" in argv:
                    useradd.append(i)
                    self.assertIn("--skel", argv)
                    self.assertIn("/etc/lychd-host-floor-empty-skel", argv)
                if argv and argv[-1] == "identity":
                    identity.append(i)
                if argv and argv[-1] == "maps":
                    maps_check.append(i)
                if "enable-linger" in argv:
                    linger.append(i)
            if "'stage': 'maps_initialized'" in content:
                initialized.append(i)
            if user == "lychd":
                runtime_files.append(i)
        self.assertEqual(len(useradd), 1)
        self.assertEqual(len(identity), 1)
        self.assertEqual(len(maps_check), 1)
        self.assertEqual(len(initialized), 1)
        self.assertEqual(len(linger), 1)
        self.assertLess(useradd[0], identity[0])
        self.assertLess(identity[0], maps_check[0])
        self.assertLess(maps_check[0], initialized[0])
        self.assertLess(initialized[0], min(runtime_files))
        self.assertLess(max(runtime_files), linger[0])

    def test_network_online_dependency_is_explicitly_opt_in(self):
        matches = [
            task
            for task, _ in self.tasks
            if task.get("name") == "Ensure network-online target participates in system boot"
        ]

        self.assertEqual(len(matches), 1)

        task = matches[0]
        args = task["ansible.builtin.file"]

        self.assertEqual(args["src"], "/usr/lib/systemd/system/network-online.target")
        self.assertEqual(
            args["dest"],
            "/etc/systemd/system/multi-user.target.wants/network-online.target",
        )
        self.assertEqual(args["state"], "link")
        self.assertIn("default(false)", task["when"])
        self.assertIn("lychd_floor_enable_network_online", task["when"])


if __name__ == "__main__":
    unittest.main()
