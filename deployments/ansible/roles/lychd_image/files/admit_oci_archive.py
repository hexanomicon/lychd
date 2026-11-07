"""Controller-side admission of one OCI image archive for a campaign.

Verifies, without Podman, that an ``oci-archive`` produced by ``podman save --format oci-archive``
contains exactly one image whose every blob matches its content digest, whose config digest (the
Podman image ID) equals the expected ID when supplied, and whose revision label equals the pinned
source SHA. It then records the archive's SHA-256 and identity as private Ansible variables.

    python admit_oci_archive.py ARCHIVE REVISION OUTPUT_JSON [EXPECTED_IMAGE_ID]
"""

import hashlib
import json
import re
import sys
import tarfile
from pathlib import Path

REVISION_LABEL = "org.opencontainers.image.revision"
MANIFEST_TYPES = {"application/vnd.oci.image.manifest.v1+json"}
CHUNK = 1 << 20


class ArchiveRefusal(Exception):
    """The archive cannot be admitted as the campaign image."""


def require(condition, message):
    if not condition:
        raise ArchiveRefusal(message)


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


def inspect_archive(path, revision, expected_image_id=None):
    require(re.fullmatch(r"[0-9a-f]{40}", revision or ""), "exact source SHA required")
    if expected_image_id:
        require(re.fullmatch(r"[0-9a-f]{64}", expected_image_id), "expected image ID must be 64 hex characters")
    with tarfile.open(path, mode="r:") as archive:
        names = archive.getnames()
        require(all(not name.startswith("/") and ".." not in Path(name).parts for name in names), "unsafe member path")
        require("oci-layout" in names and "index.json" in names, "not an OCI layout archive")
        index = json.load(archive.extractfile("index.json"))
        manifests = index.get("manifests", [])
        require(len(manifests) == 1, f"archive must contain exactly one image, found {len(manifests)}")
        descriptor = manifests[0]
        require(descriptor.get("mediaType") in MANIFEST_TYPES, "unsupported manifest media type")
        manifest = json.loads(read_verified(archive, descriptor["digest"], size=descriptor.get("size")))
        config_descriptor = manifest["config"]
        config = json.loads(read_verified(archive, config_descriptor["digest"], size=config_descriptor.get("size")))
        layers = manifest.get("layers", [])
        require(layers, "image has no layers")
        for layer in layers:
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
        "ref_name": (descriptor.get("annotations") or {}).get("org.opencontainers.image.ref.name"),
        "layers": len(layers),
    }


def sha256_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(CHUNK):
            hasher.update(chunk)
    return hasher.hexdigest()


def main(argv):
    require(len(argv) in (3, 4), "usage: ARCHIVE REVISION OUTPUT_JSON [EXPECTED_IMAGE_ID]")
    archive = Path(argv[0]).resolve(strict=True)
    revision, output = argv[1], Path(argv[2])
    require(archive.is_file() and not Path(argv[0]).is_symlink(), "archive must be a regular file")
    before = sha256_file(archive)
    identity = inspect_archive(archive, revision, argv[3] if len(argv) == 4 else None)
    require(sha256_file(archive) == before, "archive changed during admission")
    variables = {
        "lychd_image_archive": str(archive),
        "lychd_image_archive_sha256": before,
        "lychd_image_id": identity["image_id"],
        "lychd_image_ref": f"localhost/lychd:{revision}",
        "lychd_image_revision": revision,
    }
    output.write_text(json.dumps(variables, indent=2) + "\n")
    output.chmod(0o600)
    print(json.dumps({**variables, **identity}, indent=2))


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (ArchiveRefusal, OSError, ValueError, KeyError, tarfile.TarError) as error:
        sys.exit(f"image archive refused: {error}")
