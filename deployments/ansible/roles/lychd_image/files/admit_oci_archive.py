"""Controller-side admission of one OCI image archive for a campaign.

Verifies, without Podman, that an ``oci-archive`` produced by ``podman save --format oci-archive``
contains exactly one image whose every blob matches its content digest, whose config digest (the
Podman image ID) equals the expected ID when supplied, and whose revision label equals the pinned
source SHA. It then records the archive's SHA-256 and identity as private Ansible variables.

    python admit_oci_archive.py ARCHIVE REVISION OUTPUT_JSON [EXPECTED_IMAGE_ID]
"""

import hashlib
import json
import os
import re
import sys
import tarfile
from pathlib import Path

REVISION_LABEL = "org.opencontainers.image.revision"
MANIFEST_TYPES = {"application/vnd.oci.image.manifest.v1+json"}
CONFIG_TYPES = {"application/vnd.oci.image.config.v1+json"}
LAYER_TYPES = {
    "application/vnd.oci.image.layer.v1.tar",
    "application/vnd.oci.image.layer.v1.tar+gzip",
    "application/vnd.oci.image.layer.v1.tar+zstd",
}
CHUNK = 1 << 20


class ArchiveRefusal(Exception):
    """The archive cannot be admitted as the campaign image."""


def require(condition, message):
    if not condition:
        raise ArchiveRefusal(message)


def read_document(archive, name):
    """Read a bounded regular metadata file, never a tar link or duplicate member."""
    member = archive.getmember(name)
    require(member.isreg() and member.size <= 4 * CHUNK, f"invalid metadata file: {name}")
    return json.load(archive.extractfile(member))


def validate_descriptor(value, media_types):
    """Admit local content only: Podman may prefer descriptor URLs over archive bytes."""
    require(isinstance(value, dict), "descriptor must be an object")
    require("urls" not in value and "data" not in value, "external or embedded descriptor content refused")
    require(value.get("mediaType") in media_types, "unsupported descriptor media type")
    require(type(value.get("size")) is int and value["size"] >= 0, "descriptor size required")
    return value


def blob_member(archive, digest):
    match = re.fullmatch(r"sha256:([0-9a-f]{64})", digest or "")
    require(match, f"unsupported digest {digest!r}")
    try:
        member = archive.getmember(f"blobs/sha256/{match.group(1)}")
    except KeyError:
        raise ArchiveRefusal(f"missing blob {digest}") from None
    require(member.isreg(), f"blob is not a regular file: {digest}")
    return member, match.group(1)


def read_verified(archive, digest, *, keep=True, size=None):
    """Hash one blob completely; return its bytes only for small JSON documents."""
    member, expected = blob_member(archive, digest)
    if size is not None:
        require(member.size == size, f"blob size mismatch for {digest}")
    handle = archive.extractfile(member)
    hasher, kept = hashlib.sha256(), bytearray()
    while chunk := handle.read(CHUNK):
        hasher.update(chunk)
        if keep:
            kept.extend(chunk)
            require(len(kept) <= 4 * CHUNK, f"JSON blob too large: {digest}")
    require(hasher.hexdigest() == expected, f"blob digest mismatch for {digest}")
    return bytes(kept)


def inspect_archive(path, revision, expected_image_id=None, *, kind="core"):
    require(kind in {"core", "tether"}, "unsupported image kind")
    repository = "lychd-tether" if kind == "tether" else "lychd"
    require(re.fullmatch(r"[0-9a-f]{40}", revision or ""), "exact source SHA required")
    if expected_image_id:
        require(re.fullmatch(r"[0-9a-f]{64}", expected_image_id), "expected image ID must be 64 hex characters")
    with tarfile.open(path, mode="r:") as archive:
        names = archive.getnames()
        require(len(names) == len(set(names)), "duplicate archive member")
        require(all(not name.startswith("/") and ".." not in Path(name).parts for name in names), "unsafe member path")
        require(all(member.isreg() or member.isdir() for member in archive.getmembers()), "archive links refused")
        require(
            all(
                name in {"oci-layout", "index.json", "blobs", "blobs/sha256"}
                or re.fullmatch(r"blobs/sha256/[0-9a-f]{64}", name)
                for name in names
            ),
            "foreign archive metadata refused",
        )
        require("oci-layout" in names and "index.json" in names, "not an OCI layout archive")
        require(read_document(archive, "oci-layout") == {"imageLayoutVersion": "1.0.0"}, "unsupported OCI layout")
        index = read_document(archive, "index.json")
        require(index.get("schemaVersion") == 2, "unsupported index schema")
        manifests = index.get("manifests", [])
        require(len(manifests) == 1, f"archive must contain exactly one image, found {len(manifests)}")
        descriptor = validate_descriptor(manifests[0], MANIFEST_TYPES)
        reference = (descriptor.get("annotations") or {}).get("org.opencontainers.image.ref.name")
        require(
            reference in (None, f"localhost/{repository}:{revision}"), "archive tag must be absent or the campaign tag"
        )
        manifest = json.loads(read_verified(archive, descriptor["digest"], size=descriptor.get("size")))
        require(manifest.get("schemaVersion") == 2, "unsupported manifest schema")
        require(manifest.get("mediaType", next(iter(MANIFEST_TYPES))) in MANIFEST_TYPES, "unsupported manifest type")
        config_descriptor = validate_descriptor(manifest["config"], CONFIG_TYPES)
        config = json.loads(read_verified(archive, config_descriptor["digest"], size=config_descriptor.get("size")))
        layers = manifest.get("layers", [])
        require(layers, "image has no layers")
        for layer in layers:
            validate_descriptor(layer, LAYER_TYPES)
            read_verified(archive, layer["digest"], keep=False, size=layer.get("size"))
    image_id = config_descriptor["digest"].removeprefix("sha256:")
    label = (config.get("config") or {}).get("Labels", {}).get(REVISION_LABEL)
    require(label == revision, f"image revision label {label!r} differs from {revision}")
    if expected_image_id:
        require(image_id == expected_image_id, f"image ID {image_id} differs from expected {expected_image_id}")
    require(config.get("architecture") == "amd64" and config.get("os") == "linux", "linux/amd64 image required")
    return {
        "image_id": image_id,
        "manifest_digest": descriptor["digest"],
        "ref_name": reference,
        "layers": len(layers),
    }


def sha256_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(CHUNK):
            hasher.update(chunk)
    return hasher.hexdigest()


def main(argv):
    if argv and argv[0] == "--verify-tether":
        require(len(argv) == 6, "usage: --verify-tether ARCHIVE REVISION IMAGE_ID MANIFEST_DIGEST ARCHIVE_SHA256")
        _, raw_path, revision, image_id, manifest_digest, archive_sha256 = argv
        path = Path(raw_path)
        require(path.is_absolute() and path.is_file() and not path.is_symlink(), "ordinary absolute archive required")
        require(sha256_file(path) == archive_sha256, "archive checksum differs")
        identity = inspect_archive(path, revision, image_id, kind="tether")
        require(identity["manifest_digest"] == manifest_digest, "archive manifest differs")
        require(sha256_file(path) == archive_sha256, "archive changed during admission")
        print(json.dumps(identity, sort_keys=True))
        return
    kind = "tether" if argv and argv[0] == "--tether" else "core"
    argv = argv[1:] if kind == "tether" else argv
    require(len(argv) in (3, 4), "usage: [--tether] ARCHIVE REVISION OUTPUT_JSON [EXPECTED_IMAGE_ID]")
    archive = Path(argv[0]).resolve(strict=True)
    revision, output = argv[1], Path(argv[2])
    require(archive.is_file() and not Path(argv[0]).is_symlink(), "archive must be a regular file")
    before = sha256_file(archive)
    identity = inspect_archive(archive, revision, argv[3] if len(argv) == 4 else None, kind=kind)
    require(sha256_file(archive) == before, "archive changed during admission")
    variables = {
        "lychd_image_archive": str(archive),
        "lychd_image_archive_sha256": before,
        "lychd_image_id": identity["image_id"],
        "lychd_image_manifest_digest": identity["manifest_digest"],
        "lychd_image_ref": f"localhost/{'lychd-tether' if kind == 'tether' else 'lychd'}:{revision}",
        "lychd_image_revision": revision,
    }
    if kind == "tether":
        variables = {key.replace("lychd_image_", "lychd_tether_image_"): value for key, value in variables.items()}
    # Create privately before writing; never follow or replace an existing output path.
    with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as handle:
        handle.write(json.dumps(variables, indent=2) + "\n")
    print(json.dumps({**variables, **identity}, indent=2))


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (ArchiveRefusal, OSError, ValueError, KeyError, tarfile.TarError) as error:
        sys.exit(f"image archive refused: {error}")
