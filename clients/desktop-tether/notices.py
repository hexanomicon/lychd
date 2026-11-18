#!/usr/bin/env python3
"""Collect notices for the selected platform's desktop Tether build."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from functools import cache
from pathlib import Path

_MODULE = Path(__file__).resolve().parent
_LEGAL_NAMES = {"COPYING", "LICENSE", "NOTICE", "PATENTS"}
_COPYRIGHT = re.compile(r"^\s*(?://|/\*|\*|#)\s*(Copyright[^\r\n]+)", re.IGNORECASE)


def _go(*args: str) -> str:
    binary = shutil.which("go")
    if binary is None:
        msg = "Go must be available in the target build environment"
        raise RuntimeError(msg)
    return subprocess.check_output([binary, *args], cwd=_MODULE, encoding="utf-8")  # noqa: S603


@cache
def _legal_files(directory: Path) -> tuple[Path, ...]:
    return tuple(p for p in directory.iterdir() if p.name.upper().split(".")[0] in _LEGAL_NAMES and p.is_file())


def _headers(directory: Path, files: list[str]) -> set[str]:
    lines: set[str] = set()
    for filename in files:
        with (directory / filename).open("rb") as source:
            for line in source.read(4096).decode("utf-8", errors="replace").splitlines():
                if match := _COPYRIGHT.match(line):
                    lines.add(match[1].removesuffix("*/").strip())
    return lines


def generate() -> str:
    """Record actual target packages, parent license files and source copyright notices."""
    environment = json.loads(_go("env", "-json", "GOVERSION", "GOROOT", "GOOS", "GOARCH"))
    packages = _go("list", "-mod=readonly", "-deps", "-json=Dir,Module,GoFiles,CgoFiles,SFiles,CFiles,HFiles", ".")
    decoder = json.JSONDecoder()
    copyrights: dict[str, set[str]] = {}
    notices: dict[str, dict[str, Path]] = {}
    while packages := packages.lstrip():
        package, end = decoder.raw_decode(packages)
        packages = packages[end:]
        module = package.get("Module") or {}
        if module.get("Main"):
            continue
        root = Path(module.get("Dir", environment["GOROOT"]))
        name = f"{module['Path']} {module['Version']}" if module else f"Go {environment['GOVERSION']}"
        paths = notices.setdefault(name, {})
        headers = copyrights.setdefault(name, set())
        directory = Path(package["Dir"])
        for parent in (directory, *directory.parents):
            if not parent.is_relative_to(root):
                break
            for path in _legal_files(parent):
                paths[path.relative_to(root).as_posix()] = path
        for kind in ("GoFiles", "CgoFiles", "SFiles", "CFiles", "HFiles"):
            headers.update(_headers(directory, package.get(kind, [])))
    result = [f"Desktop Tether dependency notices ({environment['GOOS']}/{environment['GOARCH']})"]
    for name, paths in sorted(notices.items()):
        if not any(Path(path).stem.upper() in {"LICENSE", "COPYING"} for path in paths):
            msg = f"Missing license material for {name}"
            raise ValueError(msg)
        result.extend([name, "\n".join(sorted(copyrights[name]))])
        for relative, path in sorted(paths.items()):
            result.extend([relative, path.read_text(encoding="utf-8").strip()])
    return "\n\n".join(result) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.parse_args().output.write_text(generate(), encoding="utf-8")
