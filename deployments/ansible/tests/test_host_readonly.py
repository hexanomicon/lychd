"""Actual Ansible precedence cannot promote host-prerequisite verification."""

import json
import unittest
from pathlib import Path

import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.loader import init_plugin_loader
from ansible.vars.manager import VariableManager
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).parents[1]
ENV = Environment(undefined=StrictUndefined)
ENV.filters["from_json"] = json.loads
ENV.filters["to_json"] = json.dumps


def tasks_in(blocks):
    for block in blocks:
        for task in block.block:
            if hasattr(task, "block"):
                yield from tasks_in([task])
            else:
                yield task


def compiled(entries, obsolete_action):
    loader = DataLoader()
    loader.set_basedir(str(ROOT))
    variables = VariableManager(loader=loader)
    # The obsolete action names intentionally remain higher-precedence -e input.
    variables._extra_vars = loader.load(
        json.dumps(
            {
                "lychd_app_profile": "tether-container-v1",
                "lychd_tether_kernel_action": obsolete_action,
                "lychd_tether_firewall_action": obsolete_action,
                "lychd_tether_firewall_zone": "public",
                "lychd_tether_campaign": {
                    "stdout": json.dumps({"state": "staged", "offered": True, "normalized_sha256": "a" * 64})
                },
            }
        )
    )
    play = Play.load(
        {
            "hosts": "localhost",
            "gather_facts": False,
            # Static imports compile the same literal role entry points without executing a task.
            "tasks": [{"ansible.builtin.import_role": {"name": "lychd_app", "tasks_from": entry}} for entry in entries],
        },
        loader=loader,
        variable_manager=variables,
    )
    return play, variables, list(tasks_in(play.compile()))


def firewall_request(task, context):
    return json.loads(ENV.from_string(task.args["stdin"]).render(**context))


class HostReadOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_plugin_loader()

    def test_extra_actions_cannot_add_mutators_to_actual_verification_entrypoints(self):
        plays = yaml.safe_load((ROOT / "playbooks/app-verify.yml").read_text())
        entries = [row["ansible.builtin.include_role"]["tasks_from"] for row in plays[1]["tasks"]]
        self.assertEqual(entries, ["tether_kernel_verify", "firewall_verify"])
        self.assertTrue(plays[1]["become"])
        for obsolete_action in ("prepare", "verify", "unknown"):
            for check in (False, True):
                with self.subTest(action=obsolete_action, check=check):
                    play, variables, tasks = compiled(entries, obsolete_action)
                    actions = {task.action.removeprefix("ansible.builtin.") for task in tasks}
                    self.assertLessEqual(actions, {"assert", "command", "stat", "slurp", "debug", "meta"})
                    commands = [task for task in tasks if task.action.removeprefix("ansible.builtin.") == "command"]
                    self.assertEqual(len(commands), 5)
                    self.assertEqual(commands[0].args["argv"], ["/usr/bin/id", "-u"])
                    self.assertEqual(commands[1].args["argv"], ["/usr/bin/uname", "-r"])
                    self.assertEqual(
                        commands[2].args["argv"],
                        [
                            "/usr/sbin/modinfo",
                            "-k",
                            "{{ lychd_tether_kernel_release.stdout | trim }}",
                            "-F",
                            "filename",
                            "wireguard",
                        ],
                    )
                    for task in commands[:-1]:
                        self.assertFalse(task.check_mode)
                        self.assertIs(task.get_ds()["changed_when"], False)
                    for task in commands:
                        context = variables.get_vars(play=play, task=task)
                        self.assertEqual(context["lychd_tether_kernel_action"], obsolete_action)
                        self.assertEqual(context["lychd_tether_firewall_action"], obsolete_action)
                    tools = commands[-2]
                    self.assertEqual(tools.args["argv"][:3], ["/usr/bin/python3", "-I", "-c"])
                    self.assertEqual(
                        tools.args["argv"][3],
                        "{{ lookup('ansible.builtin.file', role_path + '/files/tether_tools.py') }}",
                    )
                    self.assertEqual(tools.when, [])
                    firewall = commands[-1]
                    context = variables.get_vars(play=play, task=firewall)
                    context["ansible_check_mode"] = check
                    self.assertEqual(
                        firewall_request(firewall, context),
                        {"mode": "verify", "zone": "public", "normalized_sha256": "a" * 64},
                    )
                    self.assertEqual(firewall.args["argv"][:3], ["/usr/bin/python3", "-I", "-c"])
                    self.assertEqual(
                        firewall.args["argv"][3],
                        "{{ lookup('ansible.builtin.file', role_path + '/files/tether_firewall.py') }}",
                    )
                    self.assertFalse(firewall.check_mode)
                    checks = {
                        task.name: task for task in tasks if task.action.removeprefix("ansible.builtin.") == "assert"
                    }
                    for name in (
                        "Require the persistent Tether entry during read-only verification",
                        "Require observed WireGuard during read-only verification",
                    ):
                        self.assertEqual(checks[name].when, [])

    def test_preparation_retains_effects_and_check_prediction_despite_obsolete_verify_variable(self):
        play, variables, tasks = compiled(["tether_kernel_prepare", "firewall"], "verify")
        commands = [task for task in tasks if task.action.removeprefix("ansible.builtin.") == "command"]
        self.assertEqual(len(commands), 8)
        package = commands[3]
        self.assertEqual(package.args["argv"], ["/usr/bin/rpm", "-q", "wireguard-tools"])
        install = commands[4]
        self.assertEqual(
            install.args["argv"],
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
        self.assertEqual(install.when, ["not ansible_check_mode and lychd_tether_tools_package.rc == 1"])
        tools = commands[5]
        self.assertEqual(tools.when, ["not ansible_check_mode or lychd_tether_tools_package.rc == 0"])
        load = commands[6]
        self.assertEqual(load.args["argv"], ["/usr/sbin/modprobe", "--use-blacklist", "wireguard"])
        self.assertEqual(load.args["creates"], "/sys/module/wireguard")
        self.assertNotIn("check_mode", load.get_ds())
        self.assertEqual(load.changed_when, [])
        self.assertEqual(load.when, [])
        copies = [task for task in tasks if task.action.removeprefix("ansible.builtin.") == "copy"]
        self.assertEqual(len(copies), 1)
        self.assertEqual(copies[0].args["dest"], "/etc/modules-load.d/lychd-tether.conf")
        self.assertFalse(copies[0].args["force"])
        firewall = commands[-1]
        context = variables.get_vars(play=play, task=firewall)
        for check in (False, True):
            context["ansible_check_mode"] = check
            self.assertEqual(firewall_request(firewall, context)["mode"], "plan" if check else "prepare")

    def test_deploy_uses_literal_entrypoints_and_no_action_aliases(self):
        plays = yaml.safe_load((ROOT / "playbooks/deploy.yml").read_text())
        entries = []
        for play in plays:
            for task in play.get("tasks", []):
                entry = task.get("ansible.builtin.include_role", {}).get("tasks_from")
                if entry in {"tether_kernel_prepare", "tether_kernel_verify", "firewall", "firewall_verify"}:
                    entries.append(entry)
                    self.assertNotIn("vars", task)
        self.assertEqual(entries, ["tether_kernel_prepare", "firewall", "tether_kernel_verify", "firewall_verify"])


if __name__ == "__main__":
    unittest.main()
