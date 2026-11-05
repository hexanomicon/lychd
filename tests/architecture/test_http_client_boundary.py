"""Keep owned outbound clients on HTTPX2 and legacy HTTPX at its testing boundary."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

from packaging.requirements import Requirement

from tests.architecture._python_imports import imported_modules, is_package

_ROOT = Path(__file__).resolve().parents[2]


def _raw_http_construction_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        root, *rest = ast.unparse(node.func).split(".")
        qualified = ".".join([aliases.get(root, root), *rest])
        if qualified.startswith("httpx2.") and qualified.rsplit(".", 1)[-1] in {
            "AsyncClient",
            "AsyncHTTPTransport",
            "Client",
            "HTTPTransport",
        }:
            lines.append(node.lineno)
    return lines


def test_owned_clients_and_network_transports_use_shared_construction() -> None:
    offenders: dict[str, list[int]] = {}
    for package_root in (_ROOT / "src", _ROOT / "scripts"):
        for path in package_root.rglob("*.py"):
            if path != _ROOT / "src/lychd/lib/http.py" and (lines := _raw_http_construction_lines(path)):
                offenders[str(path.relative_to(_ROOT))] = lines
    assert offenders == {}, f"Construct owned HTTP clients/transports in lychd.lib.http: {offenders}"


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
