"""Codex import law (wave4-design §3): the identity floor stays a floor.

- `domain/codex` imports only `lychd.db.models` + `lychd.config` (never agents,
  cortex, orchestration, interface, animation, ghouls).
- `domain/cortex` MUST NOT import `lychd.domain.codex` — the engine sees consent
  only through the ledger port's opaque string ids.
"""

from __future__ import annotations

from pathlib import Path

from tests.architecture._python_imports import ImportRef, imported_modules, is_package

_SRC = Path(__file__).resolve().parents[2] / "src" / "lychd"
_CODEX_ROOT = _SRC / "domain" / "codex"
_CORTEX_ROOT = _SRC / "domain" / "cortex"

# The only outer modules the codex floor may import.
_CODEX_ALLOWED_EXACT = {"lychd.db.models"}
_CODEX_ALLOWED_PREFIXES = ("lychd.config",)


def _lychd_imports(path: Path) -> list[ImportRef]:
    return [ref for ref in imported_modules(path, package_root=_SRC) if ref.module.startswith("lychd.")]


def test_codex_imports_only_db_and_config() -> None:
    offenders: dict[str, list[str]] = {}
    for path in _CODEX_ROOT.rglob("*.py"):
        bad = [
            ref.module
            for ref in _lychd_imports(path)
            if ref.module not in _CODEX_ALLOWED_EXACT
            and ref.from_module not in _CODEX_ALLOWED_EXACT
            and not any(is_package(ref.module, prefix) for prefix in _CODEX_ALLOWED_PREFIXES)
            and not is_package(ref.module, "lychd.domain.codex")
        ]
        if bad:
            offenders[str(path.relative_to(_CODEX_ROOT))] = bad
    assert offenders == {}, f"domain/codex may import only db.models + config: {offenders}"


def test_cortex_does_not_import_codex() -> None:
    offenders: dict[str, list[str]] = {}
    for path in _CORTEX_ROOT.rglob("*.py"):
        bad = [ref.module for ref in _lychd_imports(path) if is_package(ref.module, "lychd.domain.codex")]
        if bad:
            offenders[str(path.relative_to(_CORTEX_ROOT))] = bad
    assert offenders == {}, f"domain/cortex must not import domain/codex: {offenders}"
