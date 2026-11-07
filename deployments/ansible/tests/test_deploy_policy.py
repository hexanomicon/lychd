"""Offline authority checks for the deployment playbooks; requires controller PyYAML."""

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
FORBIDDEN = re.compile(
    r"systemctl[^\n]*\b(restart|stop|kill|reset-failed|enable|disable)\b"
    r"|podman[^\n]*\b(kill|stop|rm|rmi|restart|system reset)\b"
    r"|\blychd\b[^\n]*\b(del|stop)\b",
)


def walk(tasks):
    for task in tasks or []:
        yield task
        for key in ("block", "rescue", "always", "tasks"):
            if key in task:
                yield from walk(task[key])


def load(path):
    return yaml.safe_load((ROOT / path).read_text())


class DeployPolicyTests(unittest.TestCase):
    def test_no_competing_lifecycle_or_destructive_commands(self):
        for path in [*ROOT.glob("playbooks/*.yml"), *ROOT.glob("roles/*/tasks/*.yml")]:
            for task in walk(yaml.safe_load(path.read_text())):
                command = task.get("ansible.builtin.command", {})
                argv = " ".join(map(str, command.get("argv", []))) if isinstance(command, dict) else str(command)
                self.assertIsNone(FORBIDDEN.search(argv), f"{path.name}: {task.get('name')}")
                self.assertNotIn("ansible.builtin.shell", task, f"{path.name}: {task.get('name')}")
                self.assertNotIn("ansible.builtin.systemd", task, f"{path.name}: {task.get('name')}")

    def test_credentials_are_never_requested_by_ansible(self):
        for path in ROOT.glob("roles/*/tasks/*.yml"):
            for task in walk(yaml.safe_load(path.read_text())):
                argv = (
                    task.get("ansible.builtin.command", {}).get("argv", []) if "ansible.builtin.command" in task else []
                )
                self.assertNotIn("access", argv, f"{path.name}: {task.get('name')}")

    def test_start_is_the_cli_and_requires_explicit_authorization(self):
        starts = [
            task
            for task in walk(load("roles/lychd_app/tasks/apply.yml"))
            if task.get("ansible.builtin.command", {}).get("argv", [None, None])[1:2] == ["start"]
        ]
        self.assertEqual(len(starts), 1)
        self.assertIn("lychd_app_start_authorized", starts[0]["when"])
        self.assertIs(load("roles/lychd_app/defaults/main.yml")["lychd_app_start_authorized"], False)

    def test_application_effects_follow_classification_and_dry_runs(self):
        names = [task.get("name", "") for task in walk(load("roles/lychd_app/tasks/apply.yml"))]
        commands = [
            task["ansible.builtin.command"]["argv"][1:]
            for task in walk(load("roles/lychd_app/tasks/apply.yml"))
            if "ansible.builtin.command" in task
            and str(task["ansible.builtin.command"]["argv"][0]).endswith("lychd_app_cli }}")
        ]
        self.assertEqual(commands, [["init", "--dry-run"], ["init"], ["bind", "--dry-run"], ["bind"], ["start"]])
        self.assertLess(
            names.index("Refuse application effects outside the admitted chain"),
            names.index("Initialize the Codex and Crypt"),
        )

    def test_deploy_requires_one_named_target_before_any_effect(self):
        plays = load("playbooks/deploy.yml")
        admission = plays[0]["tasks"][0]["ansible.builtin.assert"]["that"]
        self.assertIn("ansible_play_hosts_all | length == 1", admission)
        classify = plays[1]
        self.assertEqual(classify["vars"]["ansible_user"], "lychd")
        self.assertFalse(classify["become"])
        authorize = next(
            task
            for task in classify["tasks"]
            if task["name"] == "Require explicit authorization for provisioning this host"
        )
        self.assertIn(
            "lychd_deploy_target | default('') == inventory_hostname", authorize["ansible.builtin.assert"]["that"]
        )
        for play in plays[2:]:
            for task in play["tasks"]:
                self.assertIn("lychd_deploy_mode", str(task.get("when", "")), task["name"])

    def test_runtime_plays_never_escalate(self):
        for path in ("playbooks/deploy.yml", "playbooks/app-verify.yml", "playbooks/source.yml"):
            for play in load(path):
                if play.get("vars", {}).get("ansible_user") == "lychd":
                    self.assertFalse(play["become"], path)
                    self.assertFalse(play["vars"]["ansible_become"], path)

    def test_image_role_verifies_checksum_and_identity(self):
        tasks = list(walk(load("roles/lychd_image/tasks/main.yml")))
        text = yaml.safe_dump(tasks)
        self.assertIn("lychd_image_remote_archive.stat.checksum == lychd_image_archive_sha256", text)
        self.assertIn("lychd_image_final.stdout | trim == lychd_image_id + ' ' + lychd_image_revision", text)
        loads = [task for task in tasks if "load" in task.get("ansible.builtin.command", {}).get("argv", [])]
        checksum = next(
            i
            for i, task in enumerate(tasks)
            if task.get("name") == "Refuse a transferred archive whose SHA-256 differs"
        )
        self.assertEqual(len(loads), 1)
        self.assertLess(checksum, tasks.index(loads[0]))

    def test_network_online_activation_is_opt_in(self):
        tasks = list(walk(load("roles/tumbleweed_host/tasks/host.yml")))
        task = next(task for task in tasks if task.get("name") == "Activate network-online on the running system")
        self.assertEqual(task["ansible.builtin.systemd_service"], {"name": "network-online.target", "state": "started"})
        self.assertIn("lychd_floor_enable_network_online", task["when"])


if __name__ == "__main__":
    unittest.main()
