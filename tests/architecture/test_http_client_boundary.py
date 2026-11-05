"""Keep owned outbound clients on HTTPX2 and legacy HTTPX at its testing boundary."""

from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.requirements import Requirement

from tests.architecture._python_imports import imported_modules, is_package

_ROOT = Path(__file__).resolve().parents[2]


def test_owned_http_clients_do_not_import_the_legacy_stack() -> None:
    offenders: dict[str, list[str]] = {}
    for package_root in (_ROOT / "src", _ROOT / "scripts"):
        for path in package_root.rglob("*.py"):
            forbidden = sorted(
                ref.module
                for ref in imported_modules(path, package_root=package_root)
                if any(is_package(ref.module, package) for package in ("httpx", "httpcore"))
            )
            if forbidden:
                offenders[str(path.relative_to(_ROOT))] = forbidden
    assert offenders == {}, f"Owned HTTP clients must use HTTPX2: {offenders}"


def test_legacy_httpx_is_declared_only_for_testing() -> None:
    metadata = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = {Requirement(value).name for value in metadata["project"]["dependencies"]}
    testing = {Requirement(value).name for value in metadata["dependency-groups"]["test"]}
    assert "httpx2" in runtime
    assert not runtime.intersection({"httpx", "httpcore"})
    assert {"httpx", "pytest-httpx2", "respx"} <= testing
