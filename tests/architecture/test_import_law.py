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


def _extension_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("lychd.extensions"):
            hits.append(node.module)
        elif isinstance(node, ast.Import):
            hits.extend(alias.name for alias in node.names if alias.name.startswith("lychd.extensions"))
    return hits


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
    from lychd.extensions.builtin.animator.llamacpp import LlamacppConnector, LlamacppStone

    assert LlamacppConnector.__module__.startswith("lychd.extensions")
    assert LlamacppStone.__module__.startswith("lychd.extensions")

    surfaces = __import__(
        "lychd.domain.animation.services.adapters.surfaces",
        fromlist=["__all__"],
    )
    assert "LlamacppConnector" not in surfaces.__all__
    assert "SoulstoneAnimator" in surfaces.__all__
