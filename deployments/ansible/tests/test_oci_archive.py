"""Controller-only OCI archive admission tests using synthetic, Podman-free layouts."""

import contextlib
import hashlib
import importlib.util
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

ADMIT_PATH = Path(__file__).parents[1] / "roles/lychd_image/files/admit_oci_archive.py"
SPEC = importlib.util.spec_from_file_location("admit_oci_archive", ADMIT_PATH)
admit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(admit)
REVISION = "4" * 40


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def build(
        self, *, revision=REVISION, manifests=1, corrupt=False, architecture="amd64", reference=None, layer_options=None
    ):
        layer = b"layer-bytes"
        config = json.dumps(
            {"architecture": architecture, "os": "linux", "config": {"Labels": {admit.REVISION_LABEL: revision}}}
        ).encode()
        manifest = json.dumps(
            {
                "schemaVersion": 2,
                "config": {
                    "mediaType": "application/vnd.oci.image.config.v1+json",
                    "digest": f"sha256:{sha(config)}",
                    "size": len(config),
                },
                "layers": [
                    {
                        "mediaType": "application/vnd.oci.image.layer.v1.tar",
                        "digest": f"sha256:{sha(layer)}",
                        "size": len(layer),
                        **(layer_options or {}),
                    }
                ],
            }
        ).encode()
        descriptor = {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "digest": f"sha256:{sha(manifest)}",
            "size": len(manifest),
            "annotations": {"org.opencontainers.image.ref.name": reference or f"localhost/lychd:{revision}"},
        }
        index = json.dumps({"schemaVersion": 2, "manifests": [descriptor] * manifests}).encode()
        members = {
            "oci-layout": b'{"imageLayoutVersion": "1.0.0"}',
            "index.json": index,
            f"blobs/sha256/{sha(config)}": config,
            f"blobs/sha256/{sha(manifest)}": manifest,
            f"blobs/sha256/{sha(layer)}": b"tampered!!!" if corrupt else layer,
        }
        path = self.root / "image.oci.tar"
        with tarfile.open(path, "w") as archive:
            for name, data in members.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        return path, sha(config)

    def test_exact_archive_is_admitted_with_its_image_id(self):
        path, image_id = self.build()
        identity = admit.inspect_archive(path, REVISION, image_id)
        self.assertEqual(identity["image_id"], image_id)

    def test_tether_archive_has_a_separate_explicit_receipt(self):
        path, image_id = self.build(reference=f"localhost/lychd-tether:{REVISION}")
        with self.assertRaises(admit.ArchiveRefusal):
            admit.inspect_archive(path, REVISION)
        self.assertEqual(admit.inspect_archive(path, REVISION, kind="tether")["image_id"], image_id)
        output = self.root / "tether-vars.json"
        with contextlib.redirect_stdout(io.StringIO()):
            admit.main(["--tether", str(path), REVISION, str(output), image_id])
        document = json.loads(output.read_text())
        self.assertEqual(document["lychd_tether_image_id"], image_id)
        self.assertNotIn("lychd_image_id", document)

    def test_manifest_receipt_is_reverified_without_writing(self):
        path, image_id = self.build(reference=f"localhost/lychd-tether:{REVISION}")
        identity = admit.inspect_archive(path, REVISION, kind="tether")
        arguments = [
            "--verify-tether",
            str(path),
            REVISION,
            image_id,
            identity["manifest_digest"],
            admit.sha256_file(path),
        ]
        with contextlib.redirect_stdout(io.StringIO()):
            admit.main(arguments)
        arguments[4] = "sha256:" + "f" * 64
        with self.assertRaisesRegex(admit.ArchiveRefusal, "manifest differs"):
            admit.main(arguments)

    def test_tampered_layer_is_refused(self):
        path, _ = self.build(corrupt=True)
        with self.assertRaisesRegex(admit.ArchiveRefusal, "digest mismatch"):
            admit.inspect_archive(path, REVISION)

    def test_other_revision_label_is_refused(self):
        path, _ = self.build(revision="5" * 40, reference=f"localhost/lychd:{REVISION}")
        with self.assertRaisesRegex(admit.ArchiveRefusal, "revision label"):
            admit.inspect_archive(path, REVISION)

    def test_unexpected_image_id_is_refused(self):
        path, _ = self.build()
        with self.assertRaisesRegex(admit.ArchiveRefusal, "differs from expected"):
            admit.inspect_archive(path, REVISION, "0" * 64)

    def test_multi_image_archive_is_refused(self):
        path, _ = self.build(manifests=2)
        with self.assertRaisesRegex(admit.ArchiveRefusal, "exactly one image"):
            admit.inspect_archive(path, REVISION)

    def test_foreign_architecture_is_refused(self):
        path, _ = self.build(architecture="arm64")
        with self.assertRaisesRegex(admit.ArchiveRefusal, "linux/amd64"):
            admit.inspect_archive(path, REVISION)

    def test_unrelated_tag_is_refused_before_podman_can_import_it(self):
        path, _ = self.build(reference="localhost/unrelated:important")
        with self.assertRaisesRegex(admit.ArchiveRefusal, "archive tag"):
            admit.inspect_archive(path, REVISION)

    def test_duplicate_member_is_refused(self):
        path, _ = self.build()
        with tarfile.open(path, "a") as archive:
            info = tarfile.TarInfo("index.json")
            info.size = 2
            archive.addfile(info, io.BytesIO(b"{}"))
        with self.assertRaisesRegex(admit.ArchiveRefusal, "duplicate"):
            admit.inspect_archive(path, REVISION)

    def test_docker_metadata_cannot_override_oci_admission(self):
        path, _ = self.build()
        with tarfile.open(path, "a") as archive:
            info = tarfile.TarInfo("manifest.json")
            info.size = 2
            archive.addfile(info, io.BytesIO(b"[]"))
        with self.assertRaisesRegex(admit.ArchiveRefusal, "foreign archive metadata"):
            admit.inspect_archive(path, REVISION)

    def test_output_symlink_is_never_followed(self):
        path, _ = self.build()
        victim = self.root / "private.json"
        victim.write_text("keep")
        output = self.root / "image-vars.json"
        output.symlink_to(victim)
        with self.assertRaises(FileExistsError):
            admit.main([str(path), REVISION, str(output)])
        self.assertEqual(victim.read_text(), "keep")

    def test_descriptor_urls_data_and_foreign_media_cannot_trigger_fetches(self):
        for types in (admit.MANIFEST_TYPES, admit.CONFIG_TYPES, admit.LAYER_TYPES):
            descriptor = {"mediaType": next(iter(types)), "size": 1, "digest": "sha256:" + "0" * 64}
            self.assertEqual(admit.validate_descriptor(descriptor, types), descriptor)
            for injected in ({"urls": ["http://127.0.0.1:9999/unadmitted-fetch"]}, {"data": "eA=="}):
                with (
                    self.subTest(injected=injected),
                    self.assertRaisesRegex(admit.ArchiveRefusal, "descriptor content"),
                ):
                    admit.validate_descriptor({**descriptor, **injected}, types)
            with self.assertRaisesRegex(admit.ArchiveRefusal, "media type"):
                admit.validate_descriptor(
                    {**descriptor, "mediaType": "application/vnd.oci.image.layer.nondistributable.v1.tar"}, types
                )

    def test_fully_hashed_archive_with_remote_layer_still_refuses(self):
        for injected in ({"urls": ["http://127.0.0.1:9999/unadmitted-fetch"]}, {"data": "eA=="}):
            path, _ = self.build(layer_options=injected)
            with self.subTest(injected=injected), self.assertRaisesRegex(admit.ArchiveRefusal, "descriptor content"):
                admit.inspect_archive(path, REVISION)

    def test_main_records_private_variables(self):
        path, image_id = self.build()
        output = self.root / "image-vars.json"
        with contextlib.redirect_stdout(io.StringIO()):
            admit.main([str(path), REVISION, str(output), image_id])
        variables = json.loads(output.read_text())
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertEqual(variables["lychd_image_id"], image_id)
        self.assertEqual(variables["lychd_image_ref"], f"localhost/lychd:{REVISION}")
        self.assertEqual(variables["lychd_image_archive_sha256"], sha(path.read_bytes()))


if __name__ == "__main__":
    unittest.main()
