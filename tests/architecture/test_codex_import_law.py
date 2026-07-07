"""Codex import law (wave4-design §3): the identity floor stays a floor.

- `domain/codex` imports only `lychd.db.models` + `lychd.config` (never agents,
  cortex, orchestration, interface, animation, ghouls).
- `domain/cortex` MUST NOT import `lychd.domain.codex` — the engine sees consent
  only through the ledger port's opaque string ids.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src" / "lychd"
_CODEX_ROOT = _SRC / "domain" / "codex"
_CORTEX_ROOT = _SRC / "domain" / "cortex"

# The only in-repo packages the codex floor may import.
_CODEX_ALLOWED_PREFIXES = ("lychd.db", "lychd.config")


def _lychd_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("lychd."):
            hits.append(node.module)
        elif isinstance(node, ast.Import):
            hits.extend(alias.name for alias in node.names if alias.name.startswith("lychd."))
    return hits


def test_codex_imports_only_db_and_config() -> None:
    offenders: dict[str, list[str]] = {}
    for path in _CODEX_ROOT.rglob("*.py"):
        bad = [
            mod
            for mod in _lychd_imports(path)
            if not mod.startswith(_CODEX_ALLOWED_PREFIXES) and not mod.startswith("lychd.domain.codex")
        ]
        if bad:
            offenders[str(path.relative_to(_CODEX_ROOT))] = bad
    assert offenders == {}, f"domain/codex may import only db.models + config: {offenders}"


def test_cortex_does_not_import_codex() -> None:
    offenders: dict[str, list[str]] = {}
    for path in _CORTEX_ROOT.rglob("*.py"):
        bad = [mod for mod in _lychd_imports(path) if mod.startswith("lychd.domain.codex")]
        if bad:
            offenders[str(path.relative_to(_CORTEX_ROOT))] = bad
    assert offenders == {}, f"domain/cortex must not import domain/codex: {offenders}"
