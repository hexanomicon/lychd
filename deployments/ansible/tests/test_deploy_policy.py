"""Offline authority checks for the deployment playbooks; requires controller PyYAML."""

import json
import re
import unittest
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined
from jinja2.nativetypes import NativeEnvironment

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
        context = {
            "lychd_app_cli": "{{ lychd_app_cli }}",
            "lychd_app_image_ref": "{{ lychd_app_image_ref }}",
            "lychd_source_revision": "{{ lychd_source_revision }}",
            "lychd_image_id": "{{ lychd_image_id }}",
            "lychd_app_init_profile_args": [],
            "lychd_app_bind_args": ["bind"],
            "lychd_app_status_args": [],
        }
        commands = []
        for task in walk(load("roles/lychd_app/tasks/apply.yml")):
            if "ansible.builtin.command" not in task or "lychd_app_profile == 'tether-container-v1'" in str(
                task.get("when", "")
            ):
                continue
            argv = task["ansible.builtin.command"]["argv"]
            if isinstance(argv, str):
                argv = NativeEnvironment(undefined=StrictUndefined).from_string(argv).render(**context)
            if argv[0] == "{{ lychd_app_cli }}":
                commands.append(argv[1:])
        self.assertEqual(
            commands,
            [
                ["init", "--web-image", "{{ lychd_app_image_ref }}", "--dry-run"],
                ["init", "--web-image", "{{ lychd_app_image_ref }}"],
                ["bind", "--dry-run"],
                ["bind"],
                ["start"],
                [
                    "status",
                    "--json",
                    "--deployment-revision",
                    "{{ lychd_source_revision }}",
                    "--deployment-image-id",
                    "{{ lychd_image_id }}",
                ],
            ],
        )
        self.assertLess(
            names.index("Refuse application effects outside the admitted chain"),
            names.index("Initialize the Codex and Crypt"),
        )

    def test_tether_stages_public_inputs_before_original_init_and_keeps_core_bootstrap(self):
        tasks = list(walk(load("roles/lychd_app/tasks/apply.yml")))
        names = [task.get("name") for task in tasks]
        self.assertLess(
            names.index("Stage public Tether intent and verified image before original initialization"),
            names.index("Preview initialization"),
        )
        self.assertLess(
            names.index("Start through the CLI's guarded inactive bootstrap"),
            names.index("Activate and verify Tether through native lifecycle after the guarded Core bootstrap"),
        )
        stage = list(walk(load("roles/lychd_app/tasks/tether_stage.yml")))
        self.assertTrue(
            any(task.get("ansible.builtin.include_role", {}).get("name") == "lychd_image" for task in stage)
        )
        commands = [task["ansible.builtin.command"]["argv"] for task in stage if "ansible.builtin.command" in task]
        self.assertEqual(len(commands), 2)
        self.assertIn("admit_oci_archive.py", commands[0][3])
        self.assertEqual(commands[0][4], "--verify-tether")
        self.assertIn("tether_intent.py", commands[1][3])
        self.assertEqual(commands[1][4], "stage")
        self.assertTrue(all(command[:3] == ["/usr/bin/python3", "-I", "-c"] for command in commands))
        copies = [task["ansible.builtin.copy"] for task in stage if "ansible.builtin.copy" in task]
        self.assertEqual(len(copies), 1)
        self.assertFalse(copies[0]["force"])
        self.assertEqual(copies[0]["src"], "{{ lychd_tether_intent }}")
        self.assertFalse(any("receipt" in str(task).lower() for task in stage))

    def test_tether_host_udp_prerequisite_precedes_native_apply(self):
        plays = load("playbooks/deploy.yml")
        names = [play["name"] for play in plays]
        stage = names.index("Stage the exact source CLI, image and application")
        firewall = names.index("Admit only the declared host UDP prerequisite before native initialization")
        apply = names.index("Apply native application lifecycle after host prerequisites")
        self.assertLess(stage, firewall)
        self.assertLess(firewall, apply)
        self.assertFalse(plays[stage]["become"])
        self.assertTrue(plays[firewall]["become"])
        self.assertFalse(plays[apply]["become"])
        task = load("roles/lychd_app/tasks/firewall.yml")[1]
        self.assertEqual(task["when"], "(lychd_tether_campaign.stdout | from_json).offered")
        self.assertFalse(task["check_mode"])
        self.assertIn("'plan' if ansible_check_mode", task["ansible.builtin.command"]["stdin"])
        self.assertIn("normalized_sha256", task["ansible.builtin.command"]["stdin"])
        self.assertNotIn("listen_port", task["ansible.builtin.command"]["stdin"])

    def test_deploy_requires_one_named_target_before_any_effect(self):
        plays = load("playbooks/deploy.yml")
        admission = plays[0]["tasks"][0]["ansible.builtin.assert"]["that"]
        self.assertIn("ansible_play_hosts_all | length == 1", admission)
        classify = plays[1]
        self.assertEqual(classify["vars"]["ansible_user"], "lychd")
        self.assertFalse(classify["become"])
        resolve = plays[4]
        self.assertFalse(resolve["become"])
        self.assertFalse(resolve["vars"]["ansible_become"])
        authorize = next(
            task
            for task in resolve["tasks"]
            if task["name"] == "Require explicit authorization for provisioning this host"
        )
        self.assertIn(
            "lychd_deploy_target | default('') == inventory_hostname", authorize["ansible.builtin.assert"]["that"]
        )
        for play in plays[5:]:
            for task in play["tasks"]:
                self.assertIn("lychd_deploy_mode", str(task.get("when", "")), task["name"])

    def test_unavailable_runtime_login_requires_an_absent_account_before_provisioning(self):
        plays = load("playbooks/deploy.yml")
        resolve = plays[4]
        tasks = resolve["tasks"]
        query, guard, record, decide = tasks[:4]
        environment = Environment(undefined=StrictUndefined)
        environment.filters["bool"] = bool
        unavailable = environment.from_string(resolve["vars"]["lychd_deploy_runtime_unavailable"])
        self.assertEqual(unavailable.render(lychd_deploy_login={"unreachable": True}), "True")
        self.assertEqual(unavailable.render(lychd_deploy_login={"stdout": "lychd"}), "False")
        self.assertEqual(query["ansible.builtin.command"]["argv"], ["/usr/bin/getent", "passwd", "lychd"])
        self.assertIs(query["changed_when"], False)
        self.assertIs(query["check_mode"], False)
        self.assertIn("lychd_deploy_runtime_unavailable", query["when"])
        self.assertIn("lychd_deploy_runtime_unavailable", guard["when"])
        self.assertIn("lychd_deploy_runtime_unavailable", record["when"])
        failed = environment.compile_expression(query["failed_when"])
        admitted = environment.compile_expression(guard["ansible.builtin.assert"]["that"])
        # Existing account, confirmed absence, and lookup failure must have distinct outcomes.
        for rc, may_provision in [(0, False), (2, True), (1, False), (127, False)]:
            context = {"lychd_deploy_runtime_account": {"rc": rc}}
            with self.subTest(rc=rc):
                self.assertEqual(not failed(**context) and admitted(**context), may_provision)
        state = record["ansible.builtin.set_fact"]["lychd_app_observed"]["state"]
        mode = environment.from_string(decide["ansible.builtin.set_fact"]["lychd_deploy_mode"])
        for observed, expected in [
            (state, "mutate"),
            ("running", "verify"),
            ("no_runtime_login", "refuse"),
            ("unknown", "refuse"),
            ("foreign_revision", "refuse"),
        ]:
            with self.subTest(state=observed):
                self.assertEqual(mode.render(lychd_app_observed={"state": observed}), expected)
        # The refusal and absence checkpoint precede the first effectful floor play.
        self.assertEqual(
            [task["ansible.builtin.include_role"]["name"] for task in plays[5]["tasks"]],
            ["tumbleweed_shell", "tumbleweed_host"],
        )
        staging = plays[6]
        ready = environment.from_string(staging["vars"]["lychd_deploy_runtime_ready"])
        self.assertEqual(ready.render(ansible_check_mode=True, lychd_app_observed={"state": state}), "False")
        self.assertEqual(ready.render(ansible_check_mode=False, lychd_app_observed={"state": state}), "True")

    def test_missing_source_bootstrap_requires_target_and_retains_native_classification(self):
        plays = load("playbooks/deploy.yml")
        inspect, floor, bootstrap = plays[1:4]
        tasks = inspect["tasks"]
        observation, decision, authorization, check_refusal = tasks[1:]
        self.assertEqual(observation["ansible.builtin.include_role"], {"name": "lychd_source", "tasks_from": "inspect"})
        environment = Environment(undefined=StrictUndefined)
        environment.filters["bool"] = bool
        needed = environment.from_string(decision["ansible.builtin.set_fact"]["lychd_deploy_source_bootstrap"])
        for complete, expected in [(True, "False"), (False, "True")]:
            self.assertEqual(needed.render(lychd_source_observed={"complete": complete}), expected)
        for target, skipped, admitted in [
            ("pilot", [], True),
            ("other", [], False),
            (None, [], False),
            ("pilot", ["floor"], False),
        ]:
            context = {"inventory_hostname": "pilot", "ansible_skip_tags": skipped}
            if target is not None:
                context["lychd_deploy_target"] = target
            checks = authorization["ansible.builtin.assert"]["that"]
            self.assertEqual(all(environment.compile_expression(check)(**context) for check in checks), admitted)
        refused = environment.compile_expression(check_refusal["when"])
        self.assertTrue(refused(ansible_check_mode=True, lychd_deploy_source_bootstrap=True))
        self.assertFalse(refused(ansible_check_mode=False, lychd_deploy_source_bootstrap=True))
        self.assertFalse(refused(ansible_check_mode=True, lychd_deploy_source_bootstrap=False))
        self.assertIn("cannot complete native", check_refusal["ansible.builtin.fail"]["msg"])
        self.assertTrue(floor["become"])
        verify = floor["tasks"][0]
        self.assertEqual(verify["ansible.builtin.include_role"]["tasks_from"], "verify")
        self.assertEqual(verify["ansible.builtin.include_role"]["name"], "tumbleweed_host")
        self.assertEqual(verify["when"], bootstrap["tasks"][0]["when"])
        self.assertEqual(bootstrap["tasks"][0]["ansible.builtin.include_role"], {"name": "lychd_source"})
        self.assertEqual(
            bootstrap["tasks"][1]["ansible.builtin.include_role"], {"name": "lychd_app", "tasks_from": "classify"}
        )
        # Failed floor observation aborts before source staging; there is no rescue or ignored failure.
        for play in [floor, bootstrap]:
            for task in play["tasks"]:
                self.assertNotIn("ignore_errors", task)
                self.assertNotIn("rescue", task)
        self.assertNotIn("lychd_app_observed", str(tasks))

    def test_complete_source_observation_needs_no_controller_binary_or_explicit_python(self):
        tasks = load("roles/lychd_source/tasks/inspect.yml")
        defaults = load("roles/lychd_source/defaults/main.yml")
        environment = Environment(undefined=StrictUndefined)
        environment.filters["bool"] = bool
        environment.tests["match"] = lambda value, pattern: re.match(pattern, value) is not None
        context = {
            "ansible_user": "lychd",
            "ansible_become": False,
            "lychd_source_revision": "a" * 40,
            "lychd_source_uv_sha256": "b" * 64,
            "lychd_source_python": defaults["lychd_source_python"],
        }
        for check in tasks[0]["ansible.builtin.assert"]["that"]:
            self.assertTrue(environment.compile_expression(check)(**context))
        self.assertNotIn("lychd_source_uv_local_binary", str(tasks))
        self.assertFalse(tasks[1]["changed_when"])
        self.assertFalse(tasks[1]["check_mode"])
        self.assertIn("source_guard.py", tasks[1]["ansible.builtin.command"]["argv"][3])
        source = load("roles/lychd_source/tasks/main.yml")
        self.assertEqual(source[0]["ansible.builtin.include_tasks"], "inspect.yml")

    def test_source_bootstrap_refuses_current_and_retired_running_or_unknown_bodies(self):
        tasks = load("roles/lychd_source/tasks/inactive.yml")
        query, refusal = tasks[-2:]
        self.assertEqual(query["loop"], ["lychd-vessel.service", "lychd-uncaged-vessel.service"])
        environment = Environment(undefined=StrictUndefined)
        checks = [environment.compile_expression(check) for check in refusal["ansible.builtin.assert"]["that"]]
        for unit in query["loop"]:
            cold = [
                f"Id={unit}",
                "LoadState=loaded",
                "ActiveState=inactive",
                "SubState=dead",
                "MainPID=0",
                "ControlPID=0",
                "Job=",
            ]
            for replaced in [
                None,
                ("ActiveState=inactive", "ActiveState=active"),
                ("MainPID=0", "MainPID=123"),
                ("Job=", "Job=9"),
                ("LoadState=loaded", "LoadState=error"),
            ]:
                lines = cold if replaced is None else [replaced[1] if line == replaced[0] else line for line in cold]
                self.assertEqual(
                    all(check(item={"item": unit, "stdout_lines": lines}) for check in checks), replaced is None
                )
        source = load("roles/lychd_source/tasks/main.yml")
        cold_check = next(
            i for i, task in enumerate(source) if task.get("ansible.builtin.include_tasks") == "inactive.yml"
        )
        first_write = next(
            i for i, task in enumerate(source) if "ansible.builtin.file" in task or "ansible.builtin.copy" in task
        )
        self.assertLess(cold_check, first_write)

    def test_running_verification_preserves_a_supplied_image_receipt(self):
        acceptance = load("playbooks/deploy.yml")[-1]
        receipt = Environment(undefined=StrictUndefined).from_string(acceptance["vars"]["lychd_app_expected_image_id"])
        for mode in ("mutate", "verify"):
            with self.subTest(mode=mode):
                self.assertEqual(receipt.render(lychd_deploy_mode=mode, lychd_image_id="a" * 64), "a" * 64)
                self.assertEqual(receipt.render(lychd_deploy_mode=mode), "")

    def test_runtime_plays_never_escalate(self):
        for path in ("playbooks/deploy.yml", "playbooks/app-verify.yml", "playbooks/source.yml"):
            for play in load(path):
                if play.get("vars", {}).get("ansible_user") == "lychd":
                    self.assertFalse(play["become"], path)
                    self.assertFalse(play["vars"]["ansible_become"], path)

    def test_image_namespace_renders_independent_receipts_with_extra_var_precedence(self):
        tasks = list(walk(load("roles/lychd_image/tasks/main.yml")))
        select = next(
            task["ansible.builtin.set_fact"]["_lychd_selected_image"]
            for task in tasks
            if "ansible.builtin.set_fact" in task
        )
        extra_vars = {}
        for prefix, label in [("lychd_image_", "core"), ("lychd_tether_image_", "tether")]:
            extra_vars.update(
                {prefix + name: label + "-" + name for name in ["archive", "archive_sha256", "id", "ref", "revision"]}
            )
        environment = NativeEnvironment(undefined=StrictUndefined)
        for kind in ["core", "tether", "core"]:
            role_vars = {"lychd_image_kind": kind, "lychd_image_ref": "attempted-role-override"}
            effective = {**role_vars, **extra_vars}
            selected = environment.from_string(select).render(**effective)
            self.assertEqual(
                selected, {name: kind + "-" + name for name in ["archive", "archive_sha256", "id", "ref", "revision"]}
            )
            effective["_lychd_selected_image"] = selected
            inspect = next(
                task["ansible.builtin.command"]["argv"]
                for task in tasks
                if task["name"] == "Observe whether the full-revision tag already exists"
            )
            self.assertEqual(environment.from_string(inspect[3]).render(**effective), kind + "-ref")
            copy = next(task["ansible.builtin.copy"] for task in tasks if "ansible.builtin.copy" in task)
            self.assertEqual(environment.from_string(copy["src"]).render(**effective), kind + "-archive")

    def test_image_role_verifies_checksum_and_identity(self):
        tasks = list(walk(load("roles/lychd_image/tasks/main.yml")))
        text = yaml.safe_dump(tasks)
        self.assertIn("lychd_image_remote_archive.stat.checksum == _lychd_selected_image.archive_sha256", text)
        self.assertIn(
            "lychd_image_final.stdout | trim == _lychd_selected_image.id + ' ' + _lychd_selected_image.revision", text
        )
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

    def test_start_wait_requires_successful_native_running_assessment(self):
        import json

        tasks = list(walk(load("roles/lychd_app/tasks/apply.yml")))
        wait = next(
            task
            for task in tasks
            if task.get("name") == "Wait read-only for the native deployment assessment to converge"
        )
        environment = Environment()
        environment.filters["from_json"] = json.loads
        raw_check = environment.compile_expression(wait["until"])

        def check(**kwargs):
            return raw_check(lychd_app_protocol=1, **kwargs)

        self.assertFalse(
            check(
                lychd_app_units={
                    "rc": 0,
                    "stdout": json.dumps({"schema": "lychd.deployment", "version": 1, "state": "unknown"}),
                }
            )
        )
        self.assertFalse(
            check(
                lychd_app_units={
                    "rc": 1,
                    "stdout": json.dumps({"schema": "lychd.deployment", "version": 1, "state": "running"}),
                }
            )
        )
        self.assertTrue(
            check(
                lychd_app_units={
                    "rc": 0,
                    "stdout": json.dumps({"schema": "lychd.deployment", "version": 1, "state": "running"}),
                }
            )
        )

        self.assertFalse(
            check(
                lychd_app_units={
                    "rc": 0,
                    "stdout": json.dumps({"schema": "lychd.deployment", "version": 0, "state": "running"}),
                }
            )
        )

    def test_read_only_classification_checks_source_before_running_cli(self):
        tasks = load("roles/lychd_app/tasks/classify.yml")
        commands = [task["ansible.builtin.command"]["argv"] for task in tasks if "ansible.builtin.command" in task]
        self.assertEqual(len(commands), 3)
        self.assertIn("source_guard.py", commands[0][3])
        self.assertIn("tether_intent.py", commands[1][3])
        self.assertEqual(commands[1][4], "verify")
        self.assertIn("app_probe.py", commands[2][3])

    def test_fresh_source_install_is_noneditable_and_completed_environments_are_preserved(self):
        tasks = load("roles/lychd_source/tasks/main.yml")
        install = next(
            task
            for task in tasks
            if task.get("name") == "Install the locked CLI once without replacing an existing environment"
        )
        argv = install["ansible.builtin.command"]["argv"]
        self.assertIn("--no-editable", argv)
        self.assertIn("--locked", argv)
        receipts = [
            task
            for task in tasks
            if task.get("ansible.builtin.copy", {}).get("dest", "").endswith("/.git/lychd-source.json")
        ]
        self.assertEqual(len(receipts), 2)
        environment = Environment(undefined=StrictUndefined)
        environment.filters["to_nice_json"] = json.dumps
        context = {
            "lychd_source_revision": "a" * 40,
            "lychd_source_uv_sha256": "b" * 64,
            "lychd_source_python": "3.14.8",
        }
        for receipt in receipts:
            rendered = environment.from_string(receipt["ansible.builtin.copy"]["content"]).render(**context)
            self.assertEqual(json.loads(rendered)["install_mode"], "non-editable")
        completed = receipts[-1]
        self.assertLess(tasks.index(install), tasks.index(completed))
        for is_complete, should_install in [(False, True), (True, False)]:
            state = {"exists": True, "complete": is_complete}
            self.assertEqual(
                environment.compile_expression(install["when"])(lychd_source_observed=state), should_install
            )
            self.assertEqual(
                environment.compile_expression(completed["when"])(
                    ansible_check_mode=False, lychd_source_observed=state
                ),
                should_install,
            )
            self.assertFalse(
                environment.compile_expression(completed["when"])(ansible_check_mode=True, lychd_source_observed=state)
            )
        self.assertFalse(receipts[0]["ansible.builtin.copy"]["force"])
        self.assertFalse(
            environment.compile_expression(receipts[0]["when"])(
                lychd_source_observed={"exists": True, "complete": True}
            )
        )

    def test_controller_uv_release_is_the_release_admitted_on_target(self):
        from jinja2 import Environment

        release = next(
            line.removeprefix("uv==")
            for line in (ROOT / "requirements-controller.txt").read_text().splitlines()
            if line.startswith("uv==")
        )
        tasks = load("roles/lychd_source/tasks/main.yml")
        validation = next(task for task in tasks if task["name"] == "Refuse another uv release")
        expression = validation["ansible.builtin.assert"]["that"]
        environment = Environment()
        environment.tests["match"] = lambda value, pattern: re.match(pattern, value) is not None
        self.assertTrue(environment.compile_expression(expression)(lychd_source_uv_version={"stdout": f"uv {release}"}))


if __name__ == "__main__":
    unittest.main()
