"""Build one explicit Scout image from pinned Core and a dedicated public Python tree."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from hashlib import sha256
from pathlib import Path

MAX_RUNTIME_ENTRIES = 20_000

if __package__:
    from scripts.reach_operator import ROOT, command, external_path, read_regular, write_private
else:
    from reach_operator import ROOT, command, external_path, read_regular, write_private


def runtime_digest(root: Path) -> str:
    """Bound and identify an explicitly declared public interpreter closure."""
    external_path(root)
    if root in {Path("/"), Path("/usr"), Path("/usr/local"), Path.home()} or not (root / "bin/python3.15").is_file():
        msg = "research_python_root"
        raise ValueError(msg)
    digest = sha256()
    total = 0
    for count, path in enumerate(sorted(root.rglob("*")), start=1):
        if count > MAX_RUNTIME_ENTRIES:
            msg = "research_runtime_limit"
            raise ValueError(msg)
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            if not path.resolve(strict=True).is_relative_to(root):
                msg = "research_runtime_symlink"
                raise ValueError(msg)
            record = [relative, "link", str(path.readlink())]
        elif path.is_dir():
            record = [relative, "directory"]
        elif path.is_file():
            total += path.stat().st_size
            if total > 512 * 1024 * 1024:
                msg = "research_runtime_limit"
                raise ValueError(msg)
            record = [relative, "file", sha256(path.read_bytes()).hexdigest()]
        else:
            msg = "research_runtime_file"
            raise ValueError(msg)
        digest.update((json.dumps(record, separators=(",", ":")) + "\n").encode())
    return digest.hexdigest()


def build(images: Path, python_root: Path, output: Path) -> None:
    """Copy only the public runtime and tracked recipe; never mount the checkout at runtime."""
    external_path(output)
    if output.exists():
        msg = "research_output_exists"
        raise ValueError(msg)
    image_record = json.loads(read_regular(images, 4096, private=True))
    core = image_record.get("core")
    if not isinstance(core, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", core) is None:
        msg = "research_core_image"
        raise ValueError(msg)
    core_tag = f"localhost/lychd-reach-core:{core.removeprefix('sha256:')}"
    observed = command(["docker", "image", "inspect", "--format", "{{.Id}}", core_tag], root=ROOT, engine="docker")
    expected = command(["docker", "image", "inspect", "--format", "{{.Id}}", core], root=ROOT, engine="docker")
    if observed != expected:
        msg = "research_core_image"
        raise ValueError(msg)
    before = runtime_digest(python_root)
    with tempfile.TemporaryDirectory(prefix="reach-research-build-") as temporary:
        context = Path(temporary)
        copied = context / "python-root"
        shutil.copytree(python_root, copied, symlinks=True)
        if runtime_digest(copied) != before:
            msg = "research_runtime_changed"
            raise ValueError(msg)
        shutil.copyfile(ROOT / "clients/research/Containerfile", context / "Containerfile")
        identity = context / "image.id"
        build_arguments = ["docker", "build", "--pull=false"]
        if os.environ.get("DOCKER_BUILDKIT", "1") == "0":
            build_arguments += ["--memory", "2g", "--cpu-period", "100000", "--cpu-quota", "100000"]
        else:
            build_arguments += [
                "--resource",
                "memory=2g",
                "--resource",
                "cpu-period=100000",
                "--resource",
                "cpu-quota=100000",
            ]
        command(
            [
                *build_arguments,
                "--iidfile",
                str(identity),
                "--build-arg",
                f"CORE_IMAGE={core_tag}",
                "--file",
                str(context / "Containerfile"),
                str(context),
            ],
            root=ROOT,
            engine="docker",
            capture=False,
        )
        research = identity.read_text().strip()
        if re.fullmatch(r"sha256:[0-9a-f]{64}", research) is None:
            msg = "research_image_identity"
            raise ValueError(msg)
        command(
            ["docker", "image", "tag", research, f"localhost/lychd-reach-research:{research[7:]}"],
            root=ROOT,
            engine="docker",
        )
    write_private(
        output,
        (
            json.dumps({"schema_version": 1, "core": core, "research": research, "runtime_tree_digest": before}) + "\n"
        ).encode(),
    )


def main(argv: list[str] | None = None) -> int:
    """Require explicit image, public-runtime and private output selections."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-images", required=True, type=Path)
    parser.add_argument("--python-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        build(args.core_images, args.python_root, args.output)
    except (OSError, ValueError):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
