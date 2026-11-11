"""Stage a public intent once, mapping admitted OCI bytes to the imported digest.

No Core imports or secret handling. Existing campaign bytes are verified, never
rewritten. The installed native CLI still owns topology and lifecycle admission.
"""

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

LIMIT = 1024 * 1024
ROOT = Path("/home/lychd/.local/state/lychd-deploy")
REPOSITORY = "localhost/lychd-tether"


class Refusal(Exception):
    """A public campaign does not have exact admission evidence."""


def require(condition):
    if not condition:
        raise Refusal("Tether public intent admission refused")


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        metadata = os.fstat(fd)
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == os.getuid())
        require(stat.S_IMODE(metadata.st_mode) == 0o600 and metadata.st_nlink == 1)
        require(metadata.st_size <= LIMIT)
        raw = os.read(fd, LIMIT + 1)
        require(len(raw) <= LIMIT)
        current = os.stat(path, follow_symlinks=False)
        require(
            (current.st_dev, current.st_ino, current.st_mode, current.st_size, current.st_mtime_ns)
            == (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_size, metadata.st_mtime_ns)
        )
        return raw
    finally:
        os.close(fd)


def publish(path, raw):
    """Exclusive publication; interrupted writes are refused, never adopted."""
    if os.path.lexists(path):
        require(read(path) == raw)
        return False
    fd, temporary = tempfile.mkstemp(prefix=".tether-intent-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            require(read(path) == raw)
            return False
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        os.unlink(temporary)
    return True


def image(reference):
    result = subprocess.run(
        ["/usr/bin/podman", "image", "inspect", reference], capture_output=True, text=True, timeout=30, check=False
    )
    require(result.returncode == 0 and len(result.stdout) <= LIMIT)
    rows = json.loads(result.stdout, object_pairs_hook=unique)
    require(isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict))
    return rows[0]


def normalize(raw, request, inspect=image):
    """Only the image string changes; actual repository digest must resolve."""
    require(sha(raw) == request["source_sha256"])
    require(re.fullmatch("[0-9a-f]{64}", request["image_id"]) is not None)
    require(re.fullmatch("[0-9a-f]{40}", request["revision"]) is not None)
    require(re.fullmatch("sha256:[0-9a-f]{64}", request["archive_manifest_digest"]) is not None)
    require(re.fullmatch("[0-9a-f]{64}", request["archive_sha256"]) is not None)
    value = json.loads(raw, object_pairs_hook=unique)
    expected = REPOSITORY + "@" + request["archive_manifest_digest"]
    require(value["rune"]["quadlet"]["image"] == expected)
    imported = inspect(request["image_id"])
    require(imported.get("Id") == request["image_id"])
    require(imported.get("Labels", {}).get("org.opencontainers.image.revision") == request["revision"])
    digest = imported.get("Digest", "")
    require(re.fullmatch("sha256:[0-9a-f]{64}", digest) is not None)
    reference = REPOSITORY + "@" + digest
    resolved = inspect(reference)
    require(resolved.get("Id") == request["image_id"] and resolved.get("Digest") == digest)
    require(resolved.get("Labels", {}).get("org.opencontainers.image.revision") == request["revision"])
    value["rune"]["quadlet"]["image"] = reference
    normalized = encode(value)
    facts = {
        "schema": "lychd.tether.campaign",
        "version": 1,
        "source_sha256": sha(raw),
        "normalized_sha256": sha(normalized),
        "archive_sha256": request["archive_sha256"],
        "archive_manifest_digest": request["archive_manifest_digest"],
        "image_id": request["image_id"],
        "revision": request["revision"],
        "image": reference,
    }
    return normalized, facts


def operate(command, request, root=ROOT, inspect=image):
    require(command in {"stage", "verify"})
    if not os.path.lexists(root):
        require(command == "verify")
        return {"state": "absent", "changed": False}
    metadata = root.lstat()
    require(stat.S_ISDIR(metadata.st_mode) and metadata.st_uid == os.getuid())
    require(stat.S_IMODE(metadata.st_mode) == 0o700)
    target = root / "tether-intent.json"
    receipt = root / "tether-campaign.json"
    if command == "verify" and not os.path.lexists(target) and not os.path.lexists(receipt):
        return {"state": "absent", "changed": False}
    normalized, facts = normalize(read(root / "tether-intent.source.json"), request, inspect)
    offered = json.loads(normalized)["rune"].get("offered") is not None
    if command == "stage":
        changed = publish(target, normalized)
        changed = publish(receipt, encode(facts)) or changed
    else:
        require(read(target) == normalized)
        if not os.path.lexists(receipt):
            # Publication order is intent then receipt. A retry may finish only
            # the missing receipt after re-verifying all immutable input bytes.
            return {"state": "pending_receipt", "changed": False, "offered": offered, **facts}
        require(read(receipt) == encode(facts))
        changed = False
    return {"state": "staged", "changed": changed, "offered": offered, **facts}


if __name__ == "__main__":
    try:
        request = json.loads(sys.stdin.read(LIMIT + 1), object_pairs_hook=unique)
        print(json.dumps(operate(sys.argv[1], request), sort_keys=True))
    except (Refusal, OSError, ValueError, TypeError, KeyError, IndexError, subprocess.SubprocessError):
        sys.exit("Tether public intent admission refused; campaign bytes were not replaced")
