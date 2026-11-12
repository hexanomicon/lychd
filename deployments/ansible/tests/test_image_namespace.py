"""Actual Ansible precedence regression for independent Core/Tether OCI admission."""

import json
import re
import unittest
from pathlib import Path

from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.loader import init_plugin_loader
from ansible.vars.manager import VariableManager
from jinja2 import StrictUndefined
from jinja2.nativetypes import NativeEnvironment

ROOT = Path(__file__).parents[1]
REVISION = "a" * 40


def render(value, context):
    environment = NativeEnvironment(undefined=StrictUndefined)
    environment.tests["match"] = lambda value, pattern: re.match(pattern, value) is not None
    environment.filters["bool"] = bool
    if isinstance(value, str):
        return environment.from_string(value).render(**context)
    if isinstance(value, list):
        return [render(item, context) for item in value]
    if isinstance(value, dict):
        return {key: render(item, context) for key, item in value.items()}
    return value


def tasks_in(blocks):
    for block in blocks:
        for task in block.block:
            if hasattr(task, "block"):
                yield from tasks_in([task])
            else:
                yield task


class ImageNamespaceTests(unittest.TestCase):
    def test_real_extra_vars_cannot_replace_tether_artifact_with_core_artifact(self):
        init_plugin_loader()
        receipts = {"lychd_source_revision": REVISION, "ansible_user": "lychd", "ansible_become": False}
        expected = {}
        for kind, prefix, repository, digit in [
            ("core", "lychd_image_", "lychd", "b"),
            ("tether", "lychd_tether_image_", "lychd-tether", "c"),
        ]:
            expected[kind] = {
                "archive": "/controller/" + kind + ".oci.tar",
                "archive_sha256": digit * 64,
                "id": ("d" if kind == "core" else "e") * 64,
                "ref": "localhost/" + repository + ":" + REVISION,
                "revision": REVISION,
            }
            receipts.update({prefix + field: value for field, value in expected[kind].items()})
        for kind in ("core", "tether", "core"):
            with self.subTest(kind=kind):
                loader = DataLoader()
                loader.set_basedir(str(ROOT))
                variables = VariableManager(loader=loader)
                # Exactly the values provided by -e @core-vars.json -e @tether-vars.json.
                variables._extra_vars = loader.load(json.dumps(receipts))
                role_vars = {"lychd_image_kind": kind}
                if kind == "tether":
                    # Reproduce the failing invocation: even attempted role aliases lose to -e.
                    role_vars.update({"lychd_image_" + field: value for field, value in expected["tether"].items()})
                play = Play.load(
                    {
                        "hosts": "localhost",
                        "gather_facts": False,
                        "roles": [{"role": "lychd_image", "vars": role_vars}],
                    },
                    loader=loader,
                    variable_manager=variables,
                )
                role = play.get_roles()[0]
                tasks = list(tasks_in(role.compile(play=play)))
                selection = next(task for task in tasks if task.name.startswith("Select the admitted artifact"))
                context = variables.get_vars(play=play, task=selection)
                self.assertEqual(context["lychd_image_ref"], expected["core"]["ref"])
                selected = render(selection.args["_lychd_selected_image"], context)
                self.assertEqual(selected, expected[kind])
                context["_lychd_selected_image"] = selected
                context.update(ansible_check_mode=False, lychd_image_existing={"rc": 1, "stdout": ""})
                by_name = {task.name: task for task in tasks}
                first = render(by_name["Observe whether the full-revision tag already exists"].args, context)
                self.assertEqual(first["argv"][3], expected[kind]["ref"])
                copied = render(by_name["Copy the archive under the runtime account"].args, context)
                self.assertEqual(copied["src"], expected[kind]["archive"])
                exact_id = render(by_name["Observe the loaded image by its exact ID"].args, context)
                self.assertEqual(exact_id["argv"][3], expected[kind]["id"])
                final = render(by_name["Read the final image identity and revision label"].args, context)
                self.assertEqual(final["argv"][3], expected[kind]["ref"])
                context.update(
                    lychd_image_remote_archive={"stat": {"checksum": expected[kind]["archive_sha256"]}},
                    lychd_image_final={"stdout": expected[kind]["id"] + " " + REVISION},
                )
                for name in (
                    "Validate the admitted image receipt and direct runtime SSH",
                    "Refuse a transferred archive whose SHA-256 differs",
                    "Require the exact admitted image identity",
                ):
                    checks = by_name[name].args["that"]
                    for expression in checks if isinstance(checks, list) else [checks]:
                        self.assertTrue(render("{{ " + expression + " }}", context), name)
                if kind == "tether":
                    context["lychd_image_remote_archive"]["stat"]["checksum"] = expected["core"]["archive_sha256"]
                    expression = by_name["Refuse a transferred archive whose SHA-256 differs"].args["that"]
                    self.assertFalse(render("{{ " + expression + " }}", context))
