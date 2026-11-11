"""Native preparation failures retain command diagnostics without parsing failure output."""

import json
import unittest
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined, UndefinedError

ROOT = Path(__file__).parents[1]


def prepare_task():
    tasks = yaml.safe_load((ROOT / "roles/lychd_app/tasks/apply.yml").read_text())
    block = next(row for row in tasks if row["name"].startswith("Prepare or resume preparation"))
    return next(row for row in block["block"] if row.get("register") == "lychd_tether_preparation")


class PreparationReportingTests(unittest.TestCase):
    def evaluate(self, rc, stdout):
        self.parses = 0
        environment = Environment(undefined=StrictUndefined)

        def from_json(value):
            self.parses += 1
            return json.loads(value)

        environment.filters["from_json"] = from_json
        return environment.compile_expression(prepare_task()["changed_when"], undefined_to_none=False)(
            lychd_tether_preparation={"rc": rc, "stdout": stdout}
        )

    def test_failed_command_never_parses_empty_non_json_or_apparent_success_output(self):
        for rc in (1, 2):
            for stdout in ("", "native command refused", '{"changed":true}'):
                with self.subTest(rc=rc, stdout=stdout):
                    self.assertIs(self.evaluate(rc, stdout), False)
                    self.assertEqual(self.parses, 0)
        task = prepare_task()
        self.assertNotIn("failed_when", task)
        self.assertNotIn("ignore_errors", task)
        self.assertNotIn("ignore_unreachable", task)

    def test_success_reports_the_native_changed_boolean(self):
        for changed in (False, True):
            with self.subTest(changed=changed):
                self.assertIs(self.evaluate(0, json.dumps({"state": "prepared", "changed": changed})), changed)
                self.assertEqual(self.parses, 1)

    def test_successful_malformed_or_missing_receipt_does_not_silently_become_unchanged(self):
        for stdout in ("", "not-json"):
            with self.subTest(stdout=stdout), self.assertRaises(json.JSONDecodeError):
                self.evaluate(0, stdout)
        with self.assertRaises(UndefinedError):
            bool(self.evaluate(0, '{"state":"prepared"}'))


if __name__ == "__main__":
    unittest.main()
