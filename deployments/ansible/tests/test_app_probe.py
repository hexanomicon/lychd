"""Controller-only classification, configuration and credential-custody tests for app_probe."""

import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import urllib.request
import urllib.response
from email.message import Message
from pathlib import Path
from unittest.mock import patch

PROBE_PATH = Path(__file__).parents[1] / "roles/lychd_app/files/app_probe.py"
SPEC = importlib.util.spec_from_file_location("app_probe", PROBE_PATH)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
REVISION = "4" * 40
REF = f"localhost/lychd:{REVISION}"
SETTINGS = f"""[server]
name = "lychd"

[server.database]
image = "docker.io/pgvector/pgvector:pg18-trixie"

[server.web]
port = 8000
image = "{probe.DEFAULT_IMAGE}"

[extensions]
builtins = []
crypt = []
"""


class RedirectCustodyTests(unittest.TestCase):
    def test_redirect_never_transmits_basic_credential_to_another_listener(self):
        visits = []

        class Fixture(urllib.request.HTTPHandler):
            def http_open(self, request):
                visits.append(request.full_url)
                headers = Message()
                headers["Location"] = "http://unadmitted.example/credential-sink"
                result = urllib.response.addinfourl(
                    io.BytesIO(b""), headers, request.full_url, 302 if len(visits) == 1 else 200
                )
                result.msg = "Fixture"
                return result

        build = urllib.request.build_opener
        with patch.object(
            probe.urllib.request, "build_opener", side_effect=lambda *handlers: build(*handlers, Fixture())
        ):
            status, _ = probe.http_get("http://127.0.0.1:7134/api/v1/altar/status", "synthetic-basic-token")
        self.assertEqual(status, 302)
        self.assertEqual(visits, ["http://127.0.0.1:7134/api/v1/altar/status"])


def digest(text):
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


class ConfigStateTests(unittest.TestCase):
    def test_pristine_settings_match_their_creation_digest(self):
        state = probe.config_state(SETTINGS, digest(SETTINGS))
        self.assertEqual(state["state"], "pristine")
        self.assertEqual(state["line"], 9)

    def test_single_image_edit_is_recognized(self):
        edited = SETTINGS.replace(probe.DEFAULT_IMAGE, REF)
        self.assertEqual(probe.config_state(edited, digest(SETTINGS)), {"state": "image_edit", "image": REF, "line": 9})

    def test_database_image_is_not_the_web_image(self):
        edited = SETTINGS.replace("pgvector:pg18-trixie", "pgvector:other")
        self.assertEqual(probe.config_state(edited, digest(SETTINGS))["state"], "unknown_changes")

    def test_any_other_change_is_unknown(self):
        edited = SETTINGS.replace(probe.DEFAULT_IMAGE, REF).replace("port = 8000", "port = 9000")
        self.assertEqual(probe.config_state(edited, digest(SETTINGS))["state"], "unknown_changes")

    def test_duplicate_image_keys_are_unknown(self):
        edited = SETTINGS.replace("port = 8000", f'image = "{REF}"')
        self.assertIn("2 [server.web]", probe.config_state(edited, digest(SETTINGS))["detail"])

    def test_array_table_ends_the_web_section(self):
        lines = ["[server.web]", 'image = "a"', "[[models]]", 'image = "b"']
        self.assertEqual(probe.server_web_image_lines(lines), [1])


class ConfigureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.layout = probe.Layout(self.temporary.name, REVISION)
        self.layout.codex.mkdir(parents=True)
        self.layout.settings.write_text(SETTINGS)
        self.layout.settings.chmod(0o600)
        self.write_receipt(SETTINGS)

    def write_receipt(self, text, version=2):
        receipt = {"version": version, "files": [{"path": str(self.layout.settings), "digest": digest(text)}]}
        self.layout.receipt.write_text(json.dumps(receipt))

    def configure(self, ref=REF):
        return probe.configure(self.layout, {"revision": REVISION, "image_ref": ref})

    def test_edits_only_the_image_line_in_place(self):
        inode = self.layout.settings.stat().st_ino
        result = self.configure()
        self.assertTrue(result["changed"])
        self.assertEqual(self.layout.settings.read_text(), SETTINGS.replace(probe.DEFAULT_IMAGE, REF))
        self.assertEqual(self.layout.settings.stat().st_ino, inode)
        self.assertEqual(self.layout.settings.stat().st_mode & 0o777, 0o600)

    def test_rerun_is_a_no_op(self):
        self.configure()
        self.assertFalse(self.configure()["changed"])

    def test_unknown_operator_change_is_never_overwritten(self):
        changed = SETTINGS.replace("port = 8000", "port = 9000")
        self.layout.settings.write_text(changed)
        with self.assertRaisesRegex(probe.Refusal, "unknown_changes"):
            self.configure()
        self.assertEqual(self.layout.settings.read_text(), changed)

    def test_short_or_foreign_tag_is_refused(self):
        with self.assertRaisesRegex(probe.Refusal, "full-revision"):
            self.configure("localhost/lychd:444444")

    def test_other_image_already_configured_is_refused(self):
        self.layout.settings.write_text(SETTINGS.replace(probe.DEFAULT_IMAGE, "localhost/lychd:other"))
        with self.assertRaisesRegex(probe.Refusal, "image_edit"):
            self.configure()

    def test_shared_readable_settings_are_refused(self):
        self.layout.settings.chmod(0o644)
        with self.assertRaisesRegex(probe.Refusal, "0600"):
            self.configure()

    def test_selected_extensions_are_refused(self):
        text = SETTINGS.replace("builtins = []", 'builtins = ["animator/llamacpp"]')
        self.layout.settings.write_text(text)
        self.write_receipt(text)
        with self.assertRaisesRegex(probe.Refusal, "empty builtins"):
            self.configure()

    def test_old_receipt_version_is_refused(self):
        self.write_receipt(SETTINGS, version=1)
        with self.assertRaisesRegex(probe.Refusal, "receipt version"):
            self.configure()


class ClassifyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.layout = probe.Layout(self.temporary.name, REVISION)
        self.units = {unit: {"LoadState": "not-found", "ActiveState": "inactive"} for unit in probe.OWNED_UNITS}
        for target, value in (("unit_states", lambda: self.units), ("podman_lines", lambda *args: [])):
            patcher = patch.object(probe, target, side_effect=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def classify(self):
        return probe.classify(self.layout, {"revision": REVISION})

    def bind(self, image=REF, reactor_revision=REVISION):
        self.layout.codex.mkdir(parents=True)
        text = SETTINGS.replace(probe.DEFAULT_IMAGE, image)
        self.layout.settings.write_text(text)
        receipt = {"version": 2, "files": [{"path": str(self.layout.settings), "digest": digest(SETTINGS)}]}
        self.layout.receipt.write_text(json.dumps(receipt))
        self.layout.quadlets.mkdir(parents=True)
        (self.layout.quadlets / "lychd-vessel.container").write_text(f"[Container]\nImage={image}\n")
        self.layout.user_units.mkdir(parents=True)
        (self.layout.user_units / "lychd-reactor.service").write_text(
            f'ExecStart="/home/lychd/src/lychd-{reactor_revision}/.venv/bin/lychd" reactor consume\n'
        )
        for unit in self.units:
            self.units[unit] = {"LoadState": "loaded", "ActiveState": "active"}

    def status(self, services="active", warnings=()):
        items = {
            "installation": {"state": "present"},
            "bindings": {"state": "present"},
            "services": {"state": services},
        }
        return patch.object(probe, "cli_status", return_value={"warnings": list(warnings), "items": items})

    def identity(self, revision=REVISION):
        return patch.object(probe, "image_identity", return_value={"id": "f" * 64, "revision": revision})

    def test_empty_account_is_absent(self):
        self.assertEqual(self.classify()["state"], "absent")

    def test_untracked_material_without_receipt_is_unknown(self):
        self.layout.codex.mkdir(parents=True)
        result = self.classify()
        self.assertEqual(result["state"], "unknown")
        self.assertIn("without a lifecycle receipt", result["reasons"][0])

    def test_healthy_pinned_body_is_running(self):
        self.bind()
        with self.status(), self.identity():
            self.assertEqual(self.classify()["state"], "running")

    def test_running_short_tag_with_pinned_label_is_running(self):
        self.bind(image="localhost/lychd:44444444")
        with self.status(), self.identity():
            self.assertEqual(self.classify()["state"], "running")

    def test_other_revision_in_reactor_is_refused(self):
        self.bind(reactor_revision="5" * 40)
        self.assertEqual(self.classify()["state"], "foreign_revision")

    def test_other_revision_image_label_is_refused(self):
        self.bind()
        with self.status(), self.identity(revision="5" * 40):
            self.assertEqual(self.classify()["state"], "foreign_revision")

    def test_status_warnings_are_unknown(self):
        self.bind()
        with self.status(warnings=["ambiguous"]), self.identity():
            self.assertEqual(self.classify()["state"], "unknown")

    def test_stale_binding_is_unknown(self):
        self.bind()
        (self.layout.quadlets / "lychd-vessel.container").write_text("Image=localhost/lychd:other\n")
        with self.status(), self.identity():
            self.assertIn("rebinding", self.classify()["reasons"][0])

    def test_mixed_units_are_unknown(self):
        self.bind()
        self.units["lychd-vessel.service"]["ActiveState"] = "activating"
        with self.status(), self.identity():
            self.assertEqual(self.classify()["state"], "unknown")

    def test_inactive_full_tag_binding_may_start(self):
        self.bind()
        for unit in self.units:
            self.units[unit]["ActiveState"] = "inactive"
        with self.status(services="inactive"), self.identity():
            self.assertEqual(self.classify()["state"], "bound_inactive")


class AcceptanceTests(unittest.TestCase):
    def test_listener_parser_detects_public_binding(self):
        output = "LISTEN 0 4096 127.0.0.1:7134 0.0.0.0:*\nLISTEN 0 4096 0.0.0.0:7134 0.0.0.0:*\n"
        self.assertEqual(probe.listener_addresses(output), ["0.0.0.0", "127.0.0.1"])
        self.assertEqual(probe.listener_addresses("LISTEN 0 1 [::1]:7134 [::]:*\n"), ["::1"])

    def access(self, url="http://127.0.0.1:7134"):
        stdout = f"Altar: {url}\nUsername: magus\nPassword: s3cret-value\n"
        return patch.object(probe, "run", return_value=probe.subprocess.CompletedProcess([], 0, stdout, ""))

    def http(self, url, token=None):
        if token is None:
            return 401, b""
        if "s3cret-value" not in __import__("base64").b64decode(token).decode():
            return 401, b""
        bodies = {
            "/api/v1/altar/status": {"pending_consents": 0},
            "/orchestrator/status": {"active_capabilities": [], "all_capabilities": [], "mutation_containment": None},
            "/orchestrator/queues": {
                "queues": [{"name": "runs", "active": 0, "depth": 0}, {"name": "rites", "active": 0}]
            },
        }
        return 200, json.dumps(bodies[url.removeprefix("http://127.0.0.1:7134")]).encode()

    def test_api_checks_pass_without_exposing_the_credential(self):
        with self.access():
            checks = probe.api_checks(probe.Layout("/home/lychd", REVISION), http=self.http)
        self.assertTrue(all(check["ok"] for check in checks), checks)
        self.assertNotIn("s3cret-value", json.dumps(checks))

    def test_open_protected_route_fails(self):
        def permissive(url, token=None):
            return self.http(url, token or __import__("base64").b64encode(b"magus:s3cret-value").decode())

        with self.access():
            checks = probe.api_checks(probe.Layout("/home/lychd", REVISION), http=permissive)
        self.assertFalse(checks[0]["ok"])

    def test_non_loopback_altar_is_refused_before_sending_credentials(self):
        sent = []
        with self.access("http://203.0.113.5:7134"):
            checks = probe.api_checks(probe.Layout("/home/lychd", REVISION), http=lambda *a: sent.append(a))
        self.assertEqual(sent, [])
        self.assertFalse(checks[0]["ok"])
        self.assertNotIn("s3cret-value", json.dumps(checks))


if __name__ == "__main__":
    unittest.main()
