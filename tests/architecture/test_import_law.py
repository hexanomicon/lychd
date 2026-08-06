"""A3-U2: the domain-owns-contracts import law for the animation package.

Nothing under ``lychd/domain/animation`` may import from ``lychd/extensions``,
with two sanctioned structural exceptions: ``animation/extension.py`` (the
Soulstone/Portal stores) and ``animation/transmute.py`` (the ``TransmutationStore``
QuadletContributor seam) extend the ``lychd.extensions.base.ExtensionStore`` base.
This test locks the dependency inversion (concrete runtimes live behind
registered adapter/connector seams); only the marker base is imported.
"""

from __future__ import annotations

import ast
from pathlib import Path

_ANIMATION_ROOT = Path(__file__).resolve().parents[2] / "src" / "lychd" / "domain" / "animation"
# Sanctioned: the structural extension-store base only (not a concrete runtime).
_ALLOWED = {"extension.py", "transmute.py"}
_RUNTIME_HANDLE_PATHS = (
    _ANIMATION_ROOT / "animators.py",
    _ANIMATION_ROOT.parents[1] / "extensions" / "builtin" / "animator" / "llamacpp" / "connector.py",
    _ANIMATION_ROOT.parents[1] / "extensions" / "builtin" / "animator" / "exllamav3" / "connector.py",
)
_RUNTIME_HANDLE_ROOTS = (
    _ANIMATION_ROOT / "services",
    _ANIMATION_ROOT.parents[1] / "extensions" / "builtin" / "animator" / "runtimes",
)
_DEPLOYMENT_MODULES = {
    "lychd.domain.animation.transmute",
    "lychd.system.schemas",
}


def _extension_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("lychd.extensions"):
            hits.append(node.module)
        elif isinstance(node, ast.Import):
            hits.extend(alias.name for alias in node.names if alias.name.startswith("lychd.extensions"))
    return hits


def _imports(path: Path) -> set[str]:
    """Return imported module names without executing the inspected module."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def test_animation_domain_does_not_import_extensions() -> None:
    offenders: dict[str, list[str]] = {}
    for path in _ANIMATION_ROOT.rglob("*.py"):
        if path.name in _ALLOWED:
            continue
        hits = _extension_imports(path)
        if hits:
            offenders[str(path.relative_to(_ANIMATION_ROOT))] = hits
    assert offenders == {}, f"domain/animation must not import lychd.extensions: {offenders}"


def test_llamacpp_connector_lives_in_extension_not_domain() -> None:
    from lychd.extensions.builtin.animator.llamacpp import LlamacppConnector, LlamacppSoulstone

    assert LlamacppConnector.__module__.startswith("lychd.extensions")
    assert LlamacppSoulstone.__module__.startswith("lychd.extensions")

    surfaces = __import__(
        "lychd.domain.animation.services.adapters.surfaces",
        fromlist=["__all__"],
    )
    assert "LlamacppConnector" not in surfaces.__all__
    assert "SoulstoneAnimator" in surfaces.__all__


def test_runtime_hydration_does_not_import_deployment_artifacts() -> None:
    """Keep live Animator construction independent of bind-time manifests."""
    paths = list(_RUNTIME_HANDLE_PATHS)
    for root in _RUNTIME_HANDLE_ROOTS:
        paths.extend(root.rglob("*.py"))

    offenders: dict[str, list[str]] = {}
    for path in paths:
        forbidden = sorted(_imports(path) & _DEPLOYMENT_MODULES)
        if forbidden:
            offenders[str(path.relative_to(_ANIMATION_ROOT.parents[2]))] = forbidden
    assert offenders == {}, f"runtime hydration must not import deployment artifacts: {offenders}"
