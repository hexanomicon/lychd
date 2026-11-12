"""Evaluate the actual kernel-task admission and check/verify execution boundaries."""

import base64
import copy
import re
import unittest
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).parents[1]
DIRECTORY = ROOT / "roles/lychd_app/tasks"
COMMON = yaml.safe_load((DIRECTORY / "tether_kernel.yml").read_text())
PREPARE = yaml.safe_load((DIRECTORY / "tether_kernel_prepare.yml").read_text())
VERIFY = yaml.safe_load((DIRECTORY / "tether_kernel_verify.yml").read_text())
TASKS = COMMON + PREPARE[1:]
ENV = Environment(undefined=StrictUndefined)
ENV.filters["bool"] = bool
ENV.filters["b64decode"] = lambda value: base64.b64decode(value).decode()
ENV.tests["match"] = lambda value, pattern: re.match(pattern, value) is not None


def task(name, rows=TASKS):
    return next(row for row in rows if row["name"] == name)


def evaluate(expression, context):
    return expression if isinstance(expression, bool) else bool(ENV.compile_expression(expression)(**context))


def admitted(row, context):
    clauses = row["ansible.builtin.assert"]["that"]
    return all(evaluate(clause, context) for clause in (clauses if isinstance(clauses, list) else [clauses]))


def context(**updates):
    value = {
        "lychd_app_profile": "tether-container-v1",
        "ansible_check_mode": False,
        "lychd_tether_kernel_uid": {"stdout": "0\n"},
        "lychd_tether_kernel_module": {"rc": 0, "stdout": "/usr/lib/modules/running/kernel/wireguard.ko.zst"},
        "lychd_tether_module_directory": {"stat": {"isdir": True, "uid": 0, "mode": "0755"}},
        "lychd_tether_module_boot": {"stat": {"exists": False}},
        "lychd_tether_module_content": {"content": base64.b64encode(b"wireguard\n").decode()},
        "lychd_tether_kernel_loaded": {"stat": {"isdir": False}},
    }
    value.update(updates)
    return value


def existing_boot():
    return {"stat": {"exists": True, "isreg": True, "uid": 0, "gid": 0, "mode": "0644", "nlink": 1, "size": 10}}


class KernelPrerequisiteTests(unittest.TestCase):
    def test_effect_inventory_contains_only_one_fixed_load_and_boot_file(self):
        commands = [row for row in TASKS if "ansible.builtin.command" in row]
        self.assertEqual(len(commands), 4)
        self.assertEqual(commands[0]["ansible.builtin.command"]["argv"], ["/usr/bin/id", "-u"])
        self.assertEqual(commands[1]["ansible.builtin.command"]["argv"], ["/usr/bin/uname", "-r"])
        for row in commands[:3]:
            self.assertFalse(row["changed_when"])
            self.assertFalse(row["check_mode"])
        self.assertEqual(len([row for row in TASKS if "ansible.builtin.copy" in row]), 1)
        modules = {key for row in TASKS for key in row if key.startswith("ansible.builtin.")}
        self.assertEqual(
            modules,
            {
                "ansible.builtin.assert",
                "ansible.builtin.command",
                "ansible.builtin.stat",
                "ansible.builtin.slurp",
                "ansible.builtin.copy",
                "ansible.builtin.debug",
                "ansible.builtin.import_tasks",
            },
        )

    def test_profile_and_effective_root_are_required(self):
        gate = task("Require the explicit Tether profile")
        self.assertTrue(admitted(gate, context()))
        self.assertFalse(admitted(gate, context(lychd_app_profile="empty-extensions-container")))
        root = task("Require administrator authority for the host prerequisite")
        self.assertFalse(admitted(root, context(lychd_tether_kernel_uid={"stdout": "1000"})))
        for wrapper in (PREPARE, VERIFY):
            self.assertEqual(wrapper[0]["ansible.builtin.import_tasks"], "tether_kernel.yml")

    def test_matching_running_kernel_and_reserved_file_checks_precede_all_effects(self):
        load = task("Load only an absent WireGuard module with administrator policy intact")
        publish = task("Persist only an absent Tether module-load entry after observed loading")
        for name in (
            "Require matching running-kernel WireGuard support before any effect",
            "Require a safe existing administrator-owned module-load directory",
            "Refuse unsafe existing Tether boot entries before loading",
            "Refuse different reserved boot bytes before loading",
        ):
            self.assertLess(TASKS.index(task(name)), TASKS.index(load))
            self.assertLess(TASKS.index(task(name)), TASKS.index(publish))
        guard = task("Require matching running-kernel WireGuard support before any effect")
        for result in ({"rc": 1, "stdout": ""}, {"rc": 0, "stdout": ""}, {"rc": 2, "stdout": "unknown"}):
            self.assertFalse(admitted(guard, context(lychd_tether_kernel_module=result)))
        query = task("Observe WireGuard availability for this running kernel")
        self.assertEqual(
            query["ansible.builtin.command"]["argv"],
            [
                "/usr/sbin/modinfo",
                "-k",
                "{{ lychd_tether_kernel_release.stdout | trim }}",
                "-F",
                "filename",
                "wireguard",
            ],
        )
        self.assertFalse(query["check_mode"])
        self.assertFalse(query["changed_when"])

    def test_foreign_boot_metadata_or_bytes_cannot_reach_load(self):
        metadata = task("Refuse unsafe existing Tether boot entries before loading")
        content = task("Refuse different reserved boot bytes before loading")
        good = context(lychd_tether_module_boot=existing_boot())
        self.assertTrue(admitted(metadata, good))
        self.assertTrue(admitted(content, good))
        for key, value in [
            ("isreg", False),
            ("uid", 1000),
            ("gid", 1000),
            ("mode", "0664"),
            ("nlink", 2),
            ("size", 11),
        ]:
            bad = copy.deepcopy(good)
            bad["lychd_tether_module_boot"]["stat"][key] = value
            self.assertFalse(admitted(metadata, bad), key)
        unknown = {"stat": {"exists": True}}
        self.assertFalse(admitted(metadata, context(lychd_tether_module_boot=unknown)))
        good["lychd_tether_module_content"]["content"] = base64.b64encode(b"foreign!!\n").decode()
        self.assertFalse(admitted(content, good))
        self.assertTrue(admitted(metadata, context()))
        self.assertTrue(admitted(content, context()))

    def test_unsafe_module_directory_is_not_repaired(self):
        guard = task("Require a safe existing administrator-owned module-load directory")
        for record in (
            {},
            {"isdir": False},
            {"isdir": True, "uid": 1000, "mode": "0755"},
            {"isdir": True, "uid": 0, "mode": "0775"},
            {"isdir": True, "uid": 0, "mode": "0757"},
        ):
            self.assertFalse(admitted(guard, context(lychd_tether_module_directory={"stat": record})))
        self.assertTrue(admitted(guard, context()))
        self.assertFalse(any("ansible.builtin.file" in row for row in TASKS))

    def test_load_uses_builtin_absence_and_check_mode_semantics_without_hiding_changes(self):
        load = task("Load only an absent WireGuard module with administrator policy intact")
        self.assertEqual(
            load["ansible.builtin.command"],
            {"argv": ["/usr/sbin/modprobe", "--use-blacklist", "wireguard"], "creates": "/sys/module/wireguard"},
        )
        # command.creates skips an already loaded module and predicts an absent load in check mode.
        self.assertNotIn("changed_when", load)
        self.assertNotIn("check_mode", load)
        self.assertNotIn("when", load)
        self.assertNotIn(load, COMMON + VERIFY)

    def test_exit_zero_without_loaded_module_stops_before_boot_publication(self):
        observed = task("Observe actual WireGuard presence after preparation or during verification")
        self.assertEqual(observed["ansible.builtin.stat"], {"path": "/sys/module/wireguard", "follow": False})
        guard = task("Require observed WireGuard before boot publication or native lifecycle")
        publish = task("Persist only an absent Tether module-load entry after observed loading")
        self.assertLess(TASKS.index(observed), TASKS.index(guard))
        self.assertLess(TASKS.index(guard), TASKS.index(publish))
        for check in (False, True):
            current = context(ansible_check_mode=check)
            self.assertEqual(evaluate(guard["when"], current), not check)
            self.assertFalse(admitted(guard, current))
            current["lychd_tether_kernel_loaded"] = {"stat": {"isdir": True}}
            self.assertTrue(admitted(guard, current))
        verify = task("Require observed WireGuard during read-only verification", VERIFY)
        self.assertNotIn("when", verify)
        self.assertFalse(admitted(verify, context(ansible_check_mode=True)))
        self.assertTrue(admitted(verify, context(lychd_tether_kernel_loaded={"stat": {"isdir": True}})))

    def test_boot_entry_is_absent_only_and_verification_never_repairs_it(self):
        publish = task("Persist only an absent Tether module-load entry after observed loading")
        self.assertEqual(
            publish["ansible.builtin.copy"],
            {
                "dest": "/etc/modules-load.d/lychd-tether.conf",
                "content": "wireguard\n",
                "owner": "root",
                "group": "root",
                "mode": "0644",
                "force": False,
            },
        )
        self.assertNotIn("check_mode", publish)
        self.assertNotIn("changed_when", publish)
        self.assertNotIn(publish, COMMON + VERIFY)
        for check in (False, True):
            for exists in (False, True):
                current = context(ansible_check_mode=check, lychd_tether_module_boot={"stat": {"exists": exists}})
                self.assertEqual(evaluate(publish["when"], current), not exists)
        verify = task("Require the persistent Tether entry during read-only verification", VERIFY)
        self.assertNotIn("when", verify)
        self.assertFalse(admitted(verify, context(ansible_check_mode=True)))

    def test_only_root_plays_select_kernel_prepare_or_verify_for_tether(self):
        calls = []
        for filename in ("deploy.yml", "app-verify.yml"):
            plays = yaml.safe_load((ROOT / "playbooks" / filename).read_text())
            for index, play in enumerate(plays):
                for row in play.get("tasks", []):
                    entry = row.get("ansible.builtin.include_role", {}).get("tasks_from", "")
                    if entry not in ("tether_kernel_prepare", "tether_kernel_verify"):
                        continue
                    self.assertTrue(play["become"])
                    self.assertNotIn("vars", row)
                    action = entry.removeprefix("tether_kernel_")
                    calls.append((filename, action))
                    for profile in ("empty-extensions-container", "tether-container-v1"):
                        for mode in ("mutate", "verify", "refuse"):
                            current = context(
                                lychd_app_profile=profile,
                                lychd_deploy_mode=mode,
                                lychd_app_observed={"state": "initialized"},
                            )
                            expected = profile == "tether-container-v1" and (
                                filename == "app-verify.yml" or mode == ("mutate" if action == "prepare" else "verify")
                            )
                            self.assertEqual(evaluate(row["when"], current), expected)
                    self.assertNotIn("offered", row["when"])
                    if action == "prepare":
                        native = next(
                            i
                            for i, item in enumerate(plays)
                            if item["name"] == "Apply native application lifecycle after host prerequisites"
                        )
                        self.assertLess(index, native)
                        self.assertFalse(plays[native]["become"])
                        self.assertEqual(play["tasks"][0], row)
                        self.assertEqual(play["tasks"][1]["ansible.builtin.include_role"]["tasks_from"], "firewall")
                        self.assertFalse(
                            evaluate(
                                row["when"],
                                context(
                                    ansible_check_mode=True,
                                    lychd_deploy_mode="mutate",
                                    lychd_app_observed={"state": "no_runtime_account"},
                                ),
                            )
                        )
        self.assertEqual(calls, [("deploy.yml", "prepare"), ("deploy.yml", "verify"), ("app-verify.yml", "verify")])


if __name__ == "__main__":
    unittest.main()
