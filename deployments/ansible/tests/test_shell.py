"""Ordinary-user shell refusal, preservation and convergence on disposable fixtures."""

import importlib.util
import json
import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml
from jinja2 import Environment, StrictUndefined
from jinja2.nativetypes import NativeEnvironment

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("user_config", ROOT / "files/user_config.py")
config = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(config)


class ShellFilesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        self.identity = {"name": "person", "uid": os.geteuid(), "gid": os.getegid(), "home": str(self.home)}
        self.intent = {
            "kind": "shell",
            "user": "person",
            "shell": "zsh",
            "set_login": True,
            "identity": self.identity,
            "files": {
                ".zshrc": config.SHELL_MARKER + config.ZSH_HOOK + "\n",
                ".config/lychd-shell/zshrc": config.SHELL_MARKER + "# fixture defaults\n",
            },
        }

        def open_fixture(path, uid):
            descriptor = os.open(path, config.DIRECTORY_FLAGS)
            try:
                config.safe_directory(descriptor, uid)
            except BaseException:
                os.close(descriptor)
                raise
            return descriptor

        for name, replacement in (
            ("open_root", open_fixture),
            ("shell_selection", lambda intent: (self.identity, "/bin/bash", "/usr/bin/" + intent["shell"])),
        ):
            current = patch.object(config, name, replacement)
            current.start()
            self.addCleanup(current.stop)

    def execute(self, mode, intent=None):
        return config.execute(mode, self.intent if intent is None else intent)

    def test_plan_verify_apply_and_second_apply_with_private_history(self):
        self.assertTrue(self.execute("plan")["changed"])
        self.assertEqual(list(self.home.iterdir()), [])
        with self.assertRaises(config.Refusal):
            self.execute("verify")
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertEqual(len(self.execute("apply")["changed"]), 3)
        history = self.home / ".local/state/lychd-shell/history"
        self.assertEqual(history.stat().st_mode & 0o777, 0o600)
        self.assertEqual(history.parent.stat().st_mode & 0o777, 0o700)
        history.write_text("existing personal history\n")
        history_before = history.stat()
        self.assertEqual(self.execute("apply")["changed"], [])
        self.assertEqual(self.execute("verify")["changed"], [])
        self.assertEqual(history.read_text(), "existing personal history\n")
        self.assertEqual(history.stat().st_mtime_ns, history_before.st_mtime_ns)

    def test_foreign_startup_refuses_before_any_file_or_history_creation(self):
        startup = self.home / ".zshrc"
        startup.write_text("# personal prompt and history settings\n")
        for mode in ("plan", "apply", "verify"):
            with self.subTest(mode=mode), self.assertRaisesRegex(config.Refusal, "source hook"):
                self.execute(mode)
            self.assertEqual(list(self.home.iterdir()), [startup])
        self.assertEqual(startup.read_text(), "# personal prompt and history settings\n")

    def test_manually_integrated_startup_preserves_every_byte_and_mode(self):
        startup = self.home / ".zshrc"
        text = "# personal defaults\n" + config.ZSH_HOOK + "\n# personal overrides\n"
        startup.write_text(text)
        startup.chmod(0o644)
        before = startup.stat()
        self.execute("apply")
        self.assertEqual(self.execute("verify")["changed"], [])
        self.assertEqual(startup.read_text(), text)
        self.assertEqual(startup.stat().st_mode & 0o777, 0o644)
        self.assertEqual(startup.stat().st_mtime_ns, before.st_mtime_ns)

    def test_foreign_reserved_fragment_refuses_even_with_valid_startup_hook(self):
        (self.home / ".zshrc").write_text(config.ZSH_HOOK + "\n")
        reserved = self.home / ".config/lychd-shell/zshrc"
        reserved.parent.mkdir(parents=True)
        reserved.write_text("# personal fragment\n")
        with self.assertRaisesRegex(config.Refusal, "foreign"):
            self.execute("apply")
        self.assertFalse((self.home / ".local").exists())
        self.assertEqual(reserved.read_text(), "# personal fragment\n")

    def test_unsafe_existing_history_refuses_before_startup_creation(self):
        history = self.home / ".local/state/lychd-shell/history"
        history.parent.mkdir(parents=True, mode=0o700)
        history.write_text("never truncate me\n")
        history.chmod(0o644)
        for mode in ("plan", "apply"):
            with self.subTest(mode=mode), self.assertRaisesRegex(config.Refusal, "private"):
                self.execute(mode)
            self.assertFalse((self.home / ".zshrc").exists())
            self.assertEqual(history.read_text(), "never truncate me\n")

    def test_history_symlink_and_nonprivate_state_refuse_without_config_writes(self):
        state = self.home / ".local/state/lychd-shell"
        state.mkdir(parents=True, mode=0o700)
        outside = self.home / "personal-history"
        outside.write_text("keep\n")
        (state / "history").symlink_to(outside)
        with self.assertRaises(OSError):
            self.execute("apply")
        (state / "history").unlink()
        state.chmod(0o755)
        with self.assertRaisesRegex(config.Refusal, "0700"):
            self.execute("apply")
        self.assertFalse((self.home / ".zshrc").exists())
        self.assertEqual(outside.read_text(), "keep\n")

    def test_switching_to_fish_and_back_retains_configuration_and_history(self):
        self.execute("apply")
        history = self.home / ".local/state/lychd-shell/history"
        history.write_text("previous zsh command\n")
        fish_config = self.home / ".config/fish/config.fish"
        fish_config.parent.mkdir()
        fish_config.write_text("# personal Fish configuration\n")
        snapshot = {str(path): path.read_bytes() for path in self.home.rglob("*") if path.is_file()}
        fish = {**self.intent, "shell": "fish", "files": {}}
        for mode in ("plan", "apply", "verify"):
            self.assertEqual(self.execute(mode, fish)["changed"], [])
        self.assertEqual(self.execute("apply")["changed"], [])
        self.assertEqual(snapshot, {str(path): path.read_bytes() for path in self.home.rglob("*") if path.is_file()})

    def test_workstation_zsh_preserves_unselected_foreign_fish_fragment(self):
        foreign = self.home / ".config/fish/conf.d/60-lychd-workstation.fish"
        foreign.parent.mkdir(parents=True)
        foreign.write_text("# personal Fish fragment\n")
        files = {
            name: config.MARKER + "# fixture\n"
            for name in config.USER_FILES
            if name != ".config/fish/conf.d/60-lychd-workstation.fish"
        }
        intent = {**self.intent, "kind": "user", "files": files}
        with patch.object(config, "account", return_value=self.identity):
            self.assertEqual(len(config.execute("apply", intent)["changed"]), 2)
            self.assertEqual(config.execute("verify", intent)["changed"], [])
            with self.assertRaisesRegex(config.Refusal, "foreign"):
                config.execute(
                    "apply",
                    {**intent, "shell": "fish", "files": {**files, str(foreign.relative_to(self.home)): config.MARKER}},
                )
        self.assertEqual(foreign.read_text(), "# personal Fish fragment\n")

    def test_home_file_authority_and_identity_must_remain_exact(self):
        with patch.object(config.os, "geteuid", return_value=self.identity["uid"] + 1):
            with self.assertRaisesRegex(config.Refusal, "own authority"):
                self.execute("apply")
        with self.assertRaisesRegex(config.Refusal, "unchanged"):
            self.execute("apply", {**self.intent, "identity": {**self.identity, "home": "/different"}})
        self.assertEqual(list(self.home.iterdir()), [])


class ShellSelectionTests(unittest.TestCase):
    def selection(self, **changes):
        return {"user": "person", "shell": "zsh", "set_login": True, **changes}

    def account(self, name):
        if name == "lychd":
            return SimpleNamespace(pw_uid=1001, pw_gid=1001, pw_dir="/home/lychd", pw_shell="/bin/bash")
        return SimpleNamespace(pw_uid=1000, pw_gid=1000, pw_dir="/home/person", pw_shell="/bin/bash")

    def test_unsupported_input_refused_without_account_or_process_access(self):
        with patch.object(config.pwd, "getpwnam") as lookup, patch.object(config.subprocess, "run") as run:
            for value in ("bash", "Zsh", "zsh;id", "", ["zsh"], None):
                with self.subTest(shell=value), self.assertRaisesRegex(config.Refusal, "zsh or fish"):
                    config.shell_selection(self.selection(shell=value))
            with self.assertRaisesRegex(config.Refusal, "boolean"):
                config.shell_selection(self.selection(set_login="true"))
            lookup.assert_not_called()
            run.assert_not_called()

    def test_ordinary_account_and_runtime_alias_boundary(self):
        with patch.object(config.pwd, "getpwnam", side_effect=self.account):
            self.assertEqual(config.shell_selection(self.selection())[2], "/usr/bin/zsh")
            self.assertEqual(config.shell_selection(self.selection(shell="fish"))[2], "/usr/bin/fish")
            for name in ("root", "lychd", "lychd-view"):
                with self.subTest(user=name), self.assertRaises(config.Refusal):
                    config.shell_selection(self.selection(user=name))
        for uid, shell in ((500, "/bin/bash"), (1001, "/bin/bash"), (1000, "/usr/sbin/nologin")):

            def entry(name):
                if name == "lychd":
                    return SimpleNamespace(pw_uid=1001)
                return SimpleNamespace(pw_uid=uid, pw_gid=uid, pw_dir="/home/person", pw_shell=shell)

            with patch.object(config.pwd, "getpwnam", side_effect=entry), self.assertRaises(config.Refusal):
                config.shell_selection(self.selection())

    def test_headless_preflight_does_not_query_kde_or_mutate(self):
        with (
            patch.object(config.pwd, "getpwnam", side_effect=self.account),
            patch("builtins.open", side_effect=lambda *args, **kwargs: StringIO('ID="opensuse-tumbleweed"\n')),
            patch.object(config, "open_root", return_value=7),
            patch.object(config.os, "close"),
            patch.object(config.subprocess, "run") as run,
        ):
            self.assertTrue(config.shell_preflight(self.selection())["login_change"])
            self.assertFalse(config.shell_preflight(self.selection(set_login=False))["login_change"])
            run.assert_not_called()

    def test_matching_login_refuses_missing_or_nonexecutable_selected_shell(self):
        identity = {"name": "person", "uid": 1000, "gid": 1000, "home": "/home/person"}
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "selected-shell"
            selected = str(executable)
            with (
                patch.object(config, "shell_selection", return_value=(identity, selected, selected)),
                patch.object(config.os, "geteuid", return_value=0),
                patch.object(config.subprocess, "run") as run,
            ):
                for present in (False, True):
                    if present:
                        executable.write_text("#!/bin/sh\n")
                        executable.chmod(0o600)
                    for mode in ("apply", "verify"):
                        for set_login in (False, True):
                            with self.subTest(present=present, mode=mode, set_login=set_login):
                                intent = {**self.selection(set_login=set_login), "identity": identity}
                                with self.assertRaisesRegex(config.Refusal, "executable"):
                                    config.shell_login(mode, intent)
                run.assert_not_called()

    def test_matching_login_refuses_deregistered_shell_without_usermod(self):
        identity = {"name": "person", "uid": 1000, "gid": 1000, "home": "/home/person"}
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "selected-shell"
            executable.write_text("#!/bin/sh\n")
            executable.chmod(0o755)
            selected = str(executable)
            with (
                patch.object(config, "shell_selection", return_value=(identity, selected, selected)),
                patch.object(config.os, "geteuid", return_value=0),
                patch("builtins.open", side_effect=lambda *args, **kwargs: StringIO("/bin/bash\n")),
                patch.object(config.subprocess, "run") as run,
            ):
                for mode in ("apply", "verify"):
                    with self.subTest(mode=mode), self.assertRaisesRegex(config.Refusal, "/etc/shells"):
                        config.shell_login(mode, {**self.selection(), "identity": identity})
                run.assert_not_called()

    def test_matching_login_checks_are_read_only_and_manual_selection_needs_no_registration(self):
        identity = {"name": "person", "uid": 1000, "gid": 1000, "home": "/home/person"}
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "selected-shell"
            executable.write_text("#!/bin/sh\n")
            executable.chmod(0o755)
            selected = str(executable)
            before = executable.stat()
            with (
                patch.object(config, "shell_selection", return_value=(identity, selected, selected)),
                patch.object(config.os, "geteuid", return_value=0),
                patch.object(config.subprocess, "run") as run,
            ):
                for mode in ("apply", "verify"):
                    with patch("builtins.open", return_value=StringIO(selected + "\n")):
                        self.assertFalse(
                            config.shell_login(mode, {**self.selection(), "identity": identity})["changed"]
                        )
                    with patch("builtins.open", side_effect=AssertionError("Manual shell needs no registration")):
                        intent = {**self.selection(set_login=False), "identity": identity}
                        self.assertFalse(config.shell_login(mode, intent)["changed"])
                run.assert_not_called()
            self.assertEqual(executable.stat().st_mtime_ns, before.st_mtime_ns)
            self.assertEqual(executable.stat().st_mode, before.st_mode)

    def test_plan_does_not_require_an_installed_or_registered_shell(self):
        identity = {"name": "person", "uid": 1000, "gid": 1000, "home": "/home/person"}
        with (
            patch.object(config, "shell_selection", return_value=(identity, "/bin/bash", "/usr/bin/zsh")),
            patch.object(config.os, "geteuid", return_value=0),
            patch.object(config.os.path, "isfile", side_effect=AssertionError("Package is not installed yet")),
            patch("builtins.open", side_effect=AssertionError("Package is not registered yet")),
            patch.object(config.subprocess, "run") as run,
        ):
            self.assertTrue(config.shell_login("plan", {**self.selection(), "identity": identity})["changed"])
            run.assert_not_called()

    def test_login_change_is_only_the_selected_account_and_requires_installed_shell(self):
        identity = {"name": "person", "uid": 1000, "gid": 1000, "home": "/home/person"}
        intent = {**self.selection(), "identity": identity}
        with (
            patch.object(config.pwd, "getpwnam", side_effect=self.account),
            patch.object(config.os, "geteuid", return_value=0),
            patch.object(config.subprocess, "run") as run,
        ):
            self.assertTrue(config.shell_login("plan", intent)["changed"])
            with (
                patch("builtins.open", return_value=StringIO("/usr/bin/zsh\n")),
                patch.object(config.os.path, "isfile", return_value=True),
                patch.object(config.os, "access", return_value=True),
                self.assertRaisesRegex(config.Refusal, "differs"),
            ):
                config.shell_login("verify", intent)
            run.assert_not_called()
            with (
                patch("builtins.open", return_value=StringIO("/bin/bash\n")),
                patch.object(config.os.path, "isfile", return_value=True),
                patch.object(config.os, "access", return_value=True),
                self.assertRaisesRegex(config.Refusal, "/etc/shells"),
            ):
                config.shell_login("apply", intent)
            run.assert_not_called()
            with (
                patch("builtins.open", return_value=StringIO("/usr/bin/zsh\n")),
                patch.object(config.os.path, "isfile", return_value=True),
                patch.object(config.os, "access", return_value=True),
            ):
                self.assertTrue(config.shell_login("apply", intent)["changed"])
                self.assertEqual(run.call_args.args[0], ["/usr/sbin/usermod", "--shell", "/usr/bin/zsh", "person"])
            run.reset_mock()
            with (
                patch.object(config, "shell_selection", return_value=(identity, "/usr/bin/zsh", "/usr/bin/zsh")),
                patch("builtins.open", return_value=StringIO("/usr/bin/zsh\n")),
                patch.object(config.os.path, "isfile", return_value=True),
                patch.object(config.os, "access", return_value=True),
            ):
                self.assertFalse(config.shell_login("apply", intent)["changed"])
                self.assertFalse(config.shell_login("apply", {**intent, "set_login": False})["changed"])
            run.assert_not_called()


class RoleBoundaryTests(unittest.TestCase):
    def test_server_shell_effects_only_follow_the_authorized_mutation_branch(self):
        plays = yaml.safe_load((ROOT / "playbooks/deploy.yml").read_text())
        inclusions = [
            (play, task)
            for play in plays
            for task in play["tasks"]
            if task.get("ansible.builtin.include_role", {}).get("name") == "tumbleweed_shell"
        ]
        self.assertEqual(len(inclusions), 1)
        play, task = inclusions[0]
        # No host-floor effect may precede shell identity/configuration refusal.
        self.assertIs(task, play["tasks"][0])
        self.assertNotEqual(play.get("vars", {}).get("ansible_user"), "lychd")
        condition = Environment(undefined=StrictUndefined).compile_expression(task["when"])
        for state, allowed in (("mutate", True), ("verify", False), ("refuse", False)):
            self.assertEqual(condition(lychd_deploy_mode=state), allowed)

    def test_complete_read_only_shell_preflight_precedes_first_provisioning_effect(self):
        tasks = yaml.safe_load((ROOT / "roles/tumbleweed_shell/tasks/main.yml").read_text())
        self.assertEqual(tasks[0].get("ansible.builtin.import_tasks"), "preflight.yml")
        preflight = yaml.safe_load((ROOT / "roles/tumbleweed_shell/tasks/preflight.yml").read_text())
        operations = set()
        for task in preflight:
            command = task.get("ansible.builtin.command")
            if command is not None:
                self.assertIs(task["changed_when"], False)
                self.assertIs(task["check_mode"], False)
                argv = command["argv"]
                if argv[0] == "/usr/bin/python3":
                    operations.add(argv[-1])
                    self.assertIn(argv[-1], {"shell-preflight", "plan"})
                else:
                    self.assertEqual(argv[:2], ["/usr/bin/rpm", "-q"])
            else:
                self.assertTrue("ansible.builtin.assert" in task or "ansible.builtin.set_fact" in task)
        self.assertEqual(operations, {"shell-preflight", "plan"})

    def test_workstation_files_follow_selected_shell(self):
        environment = NativeEnvironment(undefined=StrictUndefined)
        environment.filters["combine"] = lambda left, right: {**left, **right}
        environment.globals["lookup"] = lambda kind, name: config.MARKER + name + "\n"
        tasks = yaml.safe_load((ROOT / "roles/tumbleweed_workstation/tasks/preflight.yml").read_text())
        template = next(
            task["ansible.builtin.set_fact"]["lychd_workstation_files"]
            for task in tasks
            if "ansible.builtin.set_fact" in task
        )
        for selected in ("zsh", "fish"):
            files = environment.from_string(template).render(lychd_shell=selected)
            self.assertEqual(".config/fish/conf.d/60-lychd-workstation.fish" in files, selected == "fish")

    def test_ansible_shell_payload_survives_serialization_and_marker_admission(self):
        role = ROOT / "roles/tumbleweed_shell"
        tasks = yaml.safe_load((role / "tasks/preflight.yml").read_text())
        retain = next(task for task in tasks if "ansible.builtin.set_fact" in task)
        plan = next(task for task in tasks if task.get("become_user") == "{{ lychd_shell_user }}")
        identity = {"name": "fixture", "uid": 1000, "gid": 1000, "home": "/fixture/home"}
        with tempfile.TemporaryDirectory() as temporary:
            controller = Path(temporary)
            (controller / "ansible.cfg").write_text("[defaults]\n")
            with patch.dict(
                os.environ,
                {
                    "ANSIBLE_HOME": str(controller / "ansible"),
                    "ANSIBLE_LOCAL_TEMP": str(controller / "local"),
                    "ANSIBLE_CONFIG": str(controller / "ansible.cfg"),
                },
            ):
                # Plain Jinja does not reproduce Ansible's backslash-preserving lexer.
                from ansible.parsing.dataloader import DataLoader
                from ansible.plugins.loader import init_plugin_loader
                from ansible.template import Templar, trust_as_template

                init_plugin_loader()
                loader = DataLoader()
                loader.set_basedir(str(role))
                for selected in ("zsh", "fish"):
                    with self.subTest(shell=selected):
                        variables = {
                            **retain.get("vars", {}),
                            "ansible_search_path": [str(role)],
                            "lychd_shell": selected,
                            "lychd_shell_user": "fixture",
                            "lychd_shell_set_login": True,
                            "lychd_shell_observation": {"stdout": json.dumps({"identity": identity})},
                        }
                        templar = Templar(loader=loader, variables=variables)
                        values = retain["ansible.builtin.set_fact"]
                        files = templar.template(trust_as_template(values["lychd_shell_files"]))
                        observed = templar.template(trust_as_template(values["lychd_shell_identity"]))
                        templar.available_variables = {
                            **variables,
                            "lychd_shell_files": files,
                            "lychd_shell_identity": observed,
                        }
                        serialized = templar.template(trust_as_template(plan["ansible.builtin.command"]["stdin"]))
                        payload = json.loads(serialized)
                        self.assertEqual(payload["identity"], identity)
                        self.assertEqual(payload["files"], files)
                        if selected == "zsh":
                            self.assertEqual(set(payload["files"]), config.ZSH_FILES)
                            self.assertEqual(payload["files"][".zshrc"], config.SHELL_MARKER + config.ZSH_HOOK + "\n")
                            self.assertEqual(
                                payload["files"][".zshrc"].splitlines(),
                                [config.SHELL_MARKER.rstrip("\n"), config.ZSH_HOOK],
                            )
                            self.assertTrue(
                                all(value.startswith(config.SHELL_MARKER) for value in payload["files"].values())
                            )
                        else:
                            self.assertEqual(payload["files"], {})
                        with (
                            patch.object(
                                config, "shell_selection", return_value=(identity, "/bin/bash", "/usr/bin/" + selected)
                            ),
                            patch.object(config.os, "geteuid", return_value=identity["uid"]),
                            patch.object(
                                config, "managed_files", return_value={"changed": [], "operation": "plan"}
                            ) as publish,
                            patch.object(config, "history_state", return_value=[]),
                        ):
                            self.assertEqual(config.shell_files("plan", payload)["changed"], [])
                            publish.assert_called_once()
                            if selected == "zsh":
                                publish.reset_mock()
                                escaped = {
                                    **payload,
                                    "files": {
                                        **payload["files"],
                                        ".zshrc": payload["files"][".zshrc"].replace("\n", "\\n"),
                                    },
                                }
                                with self.assertRaisesRegex(config.Refusal, "marked defaults"):
                                    config.shell_files("plan", escaped)
                                publish.assert_not_called()

    def test_shell_package_and_konsole_command_follow_selection(self):
        defaults = yaml.safe_load((ROOT / "roles/tumbleweed_shell/defaults/main.yml").read_text())
        self.assertEqual(defaults["lychd_shell"], "zsh")
        self.assertIs(defaults["lychd_shell_set_login"], True)
        tasks = yaml.safe_load((ROOT / "roles/tumbleweed_shell/tasks/main.yml").read_text())
        install = next(
            task["ansible.builtin.command"]["argv"]
            for task in tasks
            if task.get("ansible.builtin.command", {}).get("argv", [None])[0] == "/usr/bin/zypper"
        )
        profile = Environment().from_string(
            (ROOT / "roles/tumbleweed_workstation/templates/LychD-Workstation.profile.j2").read_text()
        )
        for shell in ("zsh", "fish"):
            selected = [Environment().from_string(argument).render(lychd_shell=shell) for argument in install]
            self.assertEqual(selected[selected.index("--") + 1 :], [shell])
            self.assertIn("Command=/usr/bin/" + shell, profile.render(lychd_shell=shell))
        self.assertIn("Command=/usr/bin/zsh", profile.render())


if __name__ == "__main__":
    unittest.main()
