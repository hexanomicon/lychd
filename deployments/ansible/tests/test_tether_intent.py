"""Controller-only imported digest and immutable campaign tests."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "tether_intent", Path(__file__).parents[1] / "roles/lychd_app/files/tether_intent.py"
)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


class IntentTests(unittest.TestCase):
    def setUp(self):
        self.document = {
            "rune": {"quadlet": {"image": helper.REPOSITORY + "@sha256:" + "a" * 64}, "other": {"unchanged": [1, 2]}},
            "version": 1,
        }
        self.raw = json.dumps(self.document).encode()
        self.request = {
            "source_sha256": helper.sha(self.raw),
            "archive_sha256": "b" * 64,
            "archive_manifest_digest": "sha256:" + "a" * 64,
            "image_id": "c" * 64,
            "revision": "d" * 40,
        }
        self.row = {
            "Id": "c" * 64,
            "Digest": "sha256:" + "e" * 64,
            "Labels": {"org.opencontainers.image.revision": "d" * 40},
        }
        self.calls = []

    def inspect(self, reference):
        self.calls.append(reference)
        return self.row

    def test_import_conversion_changes_only_image_and_retains_both_hashes(self):
        raw, facts = helper.normalize(self.raw, self.request, self.inspect)
        normalized = json.loads(raw)
        image = normalized["rune"]["quadlet"].pop("image")
        original = json.loads(self.raw)
        original["rune"]["quadlet"].pop("image")
        self.assertEqual(normalized, original)
        self.assertEqual(image, helper.REPOSITORY + "@" + self.row["Digest"])
        self.assertEqual(self.calls, ["c" * 64, image])
        self.assertEqual(facts["source_sha256"], helper.sha(self.raw))
        self.assertEqual(facts["normalized_sha256"], helper.sha(raw))

    def test_wrong_artifact_is_refused_before_image_lookup(self):
        self.document["rune"]["quadlet"]["image"] = helper.REPOSITORY + "@sha256:" + "f" * 64
        raw = json.dumps(self.document).encode()
        self.request["source_sha256"] = helper.sha(raw)
        with self.assertRaises(helper.Refusal):
            helper.normalize(raw, self.request, self.inspect)
        self.assertEqual(self.calls, [])

    def test_resolved_digest_must_name_same_image(self):
        count = 0

        def inspect(_reference):
            nonlocal count
            count += 1
            return self.row if count == 1 else {**self.row, "Id": "f" * 64}

        with self.assertRaises(helper.Refusal):
            helper.normalize(self.raw, self.request, inspect)

    def test_changed_revision_or_id_refused(self):
        for field, value in [("Id", "f" * 64), ("Labels", {})]:
            with self.subTest(field=field), self.assertRaises(helper.Refusal):
                helper.normalize(self.raw, self.request, lambda _ref: {**self.row, field: value})

    def test_campaign_is_idempotent_and_drift_never_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "tether-intent.source.json"
            source.write_bytes(self.raw)
            source.chmod(0o600)
            first = helper.operate("stage", self.request, root, self.inspect)
            self.assertTrue(first["changed"])
            self.assertFalse(helper.operate("stage", self.request, root, self.inspect)["changed"])
            self.assertFalse(helper.operate("verify", self.request, root, self.inspect)["changed"])
            target = root / "tether-intent.json"
            original = target.read_bytes()
            self.row["Digest"] = "sha256:" + "f" * 64
            with self.assertRaises(helper.Refusal):
                helper.operate("stage", self.request, root, self.inspect)
            self.assertEqual(target.read_bytes(), original)

    def test_truncated_existing_campaign_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "tether-intent.source.json"
            source.write_bytes(self.raw)
            source.chmod(0o600)
            target = root / "tether-intent.json"
            target.write_bytes(b"{")
            target.chmod(0o600)
            with self.assertRaises(helper.Refusal):
                helper.operate("stage", self.request, root, self.inspect)
            self.assertEqual(target.read_bytes(), b"{")

    def test_retry_finishes_only_missing_campaign_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "tether-intent.source.json"
            source.write_bytes(self.raw)
            source.chmod(0o600)
            normalized, _facts = helper.normalize(self.raw, self.request, self.inspect)
            helper.publish(root / "tether-intent.json", normalized)
            observed = helper.operate("verify", self.request, root, self.inspect)
            self.assertEqual(observed["state"], "pending_receipt")
            self.assertTrue(helper.operate("stage", self.request, root, self.inspect)["changed"])
            self.assertEqual((root / "tether-intent.json").read_bytes(), normalized)
            self.assertEqual(helper.operate("verify", self.request, root, self.inspect)["state"], "staged")
