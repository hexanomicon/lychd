"""Template discipline guards: no inline styles, no hardcoded instrument paths."""

from __future__ import annotations

import re
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "src" / "lychd" / "domain" / "web" / "templates"

_STYLE = re.compile(r'style="([^"]*)"')
_HARDCODED_PATH = re.compile(
    r'(?:href|hx-get|hx-post|hx-push-url|hx-put|hx-delete|sse-connect|action)="/(?:bridge|nexus|loom|scrying|reliquary|bindings)'
)


def _templates() -> list[Path]:
    return sorted(TEMPLATES_DIR.rglob("*.j2"))


def test_templates_exist() -> None:
    """Sanity: the template tree is discoverable."""
    assert _templates(), "no templates found — check TEMPLATES_DIR"


def test_no_inline_styles() -> None:
    """`style=` is banned unless every declaration sets a `--custom-property`."""
    offenders: list[tuple[str, str]] = []
    for path in _templates():
        for match in _STYLE.finditer(path.read_text(encoding="utf-8")):
            declarations = [d.strip() for d in match.group(1).split(";") if d.strip()]
            if any(not decl.startswith("--") for decl in declarations):
                offenders.append((path.name, match.group(1)))
    assert offenders == [], f"inline styles found: {offenders}"


def test_no_hardcoded_instrument_paths() -> None:
    """Instrument routes go through `route_path`, never hardcoded literals."""
    offenders = [path.name for path in _templates() if _HARDCODED_PATH.search(path.read_text(encoding="utf-8"))]
    assert offenders == [], f"hardcoded instrument paths found in: {offenders}"
