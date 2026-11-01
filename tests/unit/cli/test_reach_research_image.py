"""The source-image recipe retains finite build limits in both supported Docker modes."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from scripts import reach_research_image as image


@pytest.mark.parametrize("buildkit", [None, "1", "0"])
def test_research_build_respects_selected_docker_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, buildkit: str | None
) -> None:
    if buildkit is None:
        monkeypatch.delenv("DOCKER_BUILDKIT", raising=False)
    else:
        monkeypatch.setenv("DOCKER_BUILDKIT", buildkit)
    runtime = tmp_path / "public-python"
    (runtime / "bin").mkdir(parents=True)
    (runtime / "bin/python3.15").write_bytes(b"inert public interpreter fixture")
    images, output = tmp_path / "core.json", tmp_path / "result.json"
    core, research = "sha256:" + "a" * 64, "sha256:" + "b" * 64
    image.write_private(images, json.dumps({"core": core}).encode())
    builds: list[list[str]] = []
    tags: list[list[str]] = []

    def command(arguments: Sequence[str], **_kwargs: object) -> bytes:
        args = list(arguments)
        assert not output.exists()
        if args[1:3] == ["image", "inspect"]:
            return core.encode() + b"\n"
        if args[1:3] == ["image", "tag"]:
            tags.append(args)
            return b""
        assert args[:2] == ["docker", "build"]
        builds.append(args)
        if buildkit == "0" and "--resource" in args:
            message = "legacy Docker rejects the BuildKit resource option"
            raise ValueError(message)
        copied = Path(args[-1]) / "python-root"
        assert image.runtime_digest(copied) == image.runtime_digest(runtime)
        assert Path(args[args.index("--file") + 1]).is_file()
        Path(args[args.index("--iidfile") + 1]).write_text(research)
        return b""

    monkeypatch.setattr(image, "command", command)
    image.build(images, runtime, output)
    assert len(builds) == 1
    argv = builds[0]
    assert "--pull=false" in argv
    if buildkit == "0":
        assert argv[argv.index("--memory") + 1] == "2g"
        assert argv[argv.index("--cpu-period") + 1] == "100000"
        assert argv[argv.index("--cpu-quota") + 1] == "100000"
        assert "--resource" not in argv
    else:
        assert [argv[i + 1] for i, value in enumerate(argv) if value == "--resource"] == [
            "memory=2g",
            "cpu-period=100000",
            "cpu-quota=100000",
        ]
        assert "--memory" not in argv
    assert tags == [["docker", "image", "tag", research, "localhost/lychd-reach-research:" + "b" * 64]]
    assert json.loads(output.read_bytes()) == {
        "schema_version": 1,
        "core": core,
        "research": research,
        "runtime_tree_digest": image.runtime_digest(runtime),
    }
    assert output.stat().st_mode & 0o777 == 0o600
