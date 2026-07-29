from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path

REVISION_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
DIRTY_PATH_LIMIT = 20


class ReleaseSourceError(RuntimeError):
    """Raised when a release cannot be tied to one clean immutable source revision."""


def _git(root: Path, *arguments: str) -> str:
    git = shutil.which("git")
    if git is None:
        message = "git is required to verify release source identity"
        raise ReleaseSourceError(message)
    result = subprocess.run(  # noqa: S603
        [git, "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.rstrip()


def verify_release_source(root: Path, revision: str) -> None:
    """Require an exact clean Git revision before generating distributable artifacts."""
    normalized = revision.strip().lower()
    if REVISION_PATTERN.fullmatch(normalized) is None:
        message = "RELEASE_REVISION must be a full 40- or 64-character lowercase Git object id"
        raise ReleaseSourceError(message)

    head = _git(root, "rev-parse", "HEAD").lower()
    if normalized != head:
        message = f"RELEASE_REVISION {normalized} does not match checked-out HEAD {head}"
        raise ReleaseSourceError(message)

    dirty = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if dirty:
        paths = "\n".join(line[3:] for line in dirty.splitlines()[:DIRTY_PATH_LIMIT])
        suffix = "\n…" if len(dirty.splitlines()) > DIRTY_PATH_LIMIT else ""
        message = f"release source is not clean; commit the reviewed change before building:\n{paths}{suffix}"
        raise ReleaseSourceError(message)


def main() -> None:
    """Validate the release revision supplied by the operator or CI."""
    parser = argparse.ArgumentParser(
        description="Require a clean checkout at one full immutable Git revision.",
    )
    parser.add_argument("revision", help="Full Git object id expected at HEAD")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (defaults to this script's checkout)",
    )
    arguments = parser.parse_args()
    verify_release_source(arguments.root.resolve(), arguments.revision)
    print(f"release source verified: {arguments.revision}")  # noqa: T201


if __name__ == "__main__":
    main()
