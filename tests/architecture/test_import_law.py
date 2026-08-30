"""A3-U2: the domain-owns-contracts import law for the animation package.

Nothing under ``lychd/domain/animation`` may import from ``lychd/extensions``,
with two sanctioned structural exceptions: ``animation/extension.py`` (the
Soulstone/Portal stores) and ``animation/transmute.py`` (the ``TransmutationStore``
QuadletContributor seam) extend the ``lychd.extensions.base.ExtensionStore`` base.
This test locks the dependency inversion (concrete runtimes live behind
registered adapter/connector seams); only the marker base is imported.

"""

from __future__ import annotations

from pathlib import Path

from tests.architecture._python_imports import imported_modules, is_package

_ANIMATION_ROOT = Path(__file__).resolve().parents[2] / "src" / "lychd" / "domain" / "animation"
_LYCHD_ROOT = _ANIMATION_ROOT.parents[1]
_DOMAIN_WEB_ROOT = _LYCHD_ROOT / "domain" / "web"
# Sanctioned: these exact modules may use only the structural extension-store base.
_ALLOWED_EXTENSION_IMPORTS = {
    "extension.py": {"lychd.extensions.base"},
    "transmute.py": {"lychd.extensions.base"},
}
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


def test_animation_domain_does_not_import_extensions() -> None:
    offenders: dict[str, list[str]] = {}
    for path in _ANIMATION_ROOT.rglob("*.py"):
        allowed = _ALLOWED_EXTENSION_IMPORTS.get(str(path.relative_to(_ANIMATION_ROOT)), set())
        forbidden = sorted(
            ref.module
            for ref in imported_modules(path, package_root=_LYCHD_ROOT)
            if is_package(ref.module, "lychd.extensions")
            and ref.module not in allowed
            and ref.from_module not in allowed
        )
        if forbidden:
            offenders[str(path.relative_to(_ANIMATION_ROOT))] = forbidden
    assert offenders == {}, f"domain/animation must not import lychd.extensions: {offenders}"


def test_runtime_hydration_does_not_import_deployment_artifacts() -> None:
    """Keep live Animator construction independent of bind-time manifests."""
    paths = list(_RUNTIME_HANDLE_PATHS)
    for root in _RUNTIME_HANDLE_ROOTS:
        paths.extend(root.rglob("*.py"))

    offenders: dict[str, list[str]] = {}
    for path in paths:
        forbidden = sorted(
            ref.module for ref in imported_modules(path, package_root=_LYCHD_ROOT) if ref.module in _DEPLOYMENT_MODULES
        )
        if forbidden:
            offenders[str(path.relative_to(_ANIMATION_ROOT.parents[2]))] = forbidden
    assert offenders == {}, f"runtime hydration must not import deployment artifacts: {offenders}"


def test_web_domain_does_not_own_persistence_adapters() -> None:
    """Keep SQLAlchemy and concrete database adapters outside the web domain."""
    forbidden_prefixes = ("advanced_alchemy", "sqlalchemy", "lychd.db")
    offenders: dict[str, list[str]] = {}
    for path in _DOMAIN_WEB_ROOT.rglob("*.py"):
        forbidden = sorted(
            ref.module
            for ref in imported_modules(path, package_root=_LYCHD_ROOT)
            if any(is_package(ref.module, prefix) for prefix in forbidden_prefixes)
        )
        if forbidden:
            offenders[str(path.relative_to(_DOMAIN_WEB_ROOT))] = forbidden

    assert not (_DOMAIN_WEB_ROOT / "services.py").exists()
    assert offenders == {}, f"domain/web must not own persistence adapters: {offenders}"


def test_graph_runner_does_not_depend_on_extension_protocols() -> None:
    """Keep Graph checkpoint law inward of extension implementations."""
    imports = imported_modules(_ANIMATION_ROOT.parents[0] / "cortex" / "graph_runner.py", package_root=_LYCHD_ROOT)
    assert all(ref.module != "lychd.extensions.protocols" for ref in imports)
