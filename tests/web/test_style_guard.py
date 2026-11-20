"""Static-client architectural boundaries not covered by Svelte tooling."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FRONTEND = REPO / "clients" / "web" / "src"


def test_svelte_uses_no_raw_html_sink() -> None:
    offenders = [
        str(path.relative_to(REPO))
        for path in FRONTEND.rglob("*.svelte")
        if "{@html" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_static_client_has_no_sveltekit_server_modules() -> None:
    offenders = [
        str(path.relative_to(REPO))
        for path in FRONTEND.rglob("*")
        if path.is_file()
        and (
            path.name.startswith("+page.server")
            or path.name.startswith("+layout.server")
            or path.name.startswith("+server")
        )
    ]
    assert offenders == []


def test_frontend_styling_is_native_css() -> None:
    package = json.loads((REPO / "clients" / "web" / "package.json").read_text(encoding="utf-8"))
    declared = {*package.get("dependencies", {}), *package.get("devDependencies", {})}
    forbidden_dependencies = {
        "autoprefixer",
        "postcss",
        "sass",
        "tailwindcss",
        "@tailwindcss/postcss",
        "@tailwindcss/vite",
    }
    stylesheets = {path: path.read_text(encoding="utf-8").lower() for path in FRONTEND.rglob("*.css")}

    assert declared.isdisjoint(forbidden_dependencies)
    assert FRONTEND / "app.css" in stylesheets
    for text in stylesheets.values():
        assert '@import "tailwindcss"' not in text
        assert "@theme" not in text
    assert not (REPO / "postcss.config.js").exists()
    assert not (REPO / "tailwind.config.cjs").exists()


def test_runes_do_not_enter_framework_neutral_typescript() -> None:
    runes = ("$state", "$derived", "$effect", "$props", "$bindable", "$inspect")
    offenders = [
        str(path.relative_to(REPO))
        for path in FRONTEND.rglob("*.ts")
        if not path.name.endswith(".svelte.ts") and any(rune in path.read_text(encoding="utf-8") for rune in runes)
    ]
    assert offenders == []


THEMES = FRONTEND / "styles" / "themes"
# Persisted Canvas data keeps its recorded colours; the board maps the default ink at render time.
COLOUR_LITERAL_ALLOWLIST = {
    ("lib/pages/canvas/state/ink.ts", "#eef1f4"),
    ("lib/pages/canvas/components/CanvasSurface.svelte", "#000000"),
    ("lib/pages/canvas/state/engine.ts", "#b9cbd8"),  # portable shared example fixture
}
COLOUR_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\(|(?<![\w-])(?:black|white)(?![\w-])")
RETIRED_TOKENS = re.compile(
    r"--color-(?:void|obsidian(?:-2)?|engraving|primary(?:-deep)?|secondary(?:-deep)?|accent|tertiary(?:-edge)?"
    r"|control-border|heat(?:-deep)?|grimoire|rune(?:-dim)?|lich(?:-deep)?|frost(?:-deep)?|ash|ember|bone|parchment)(?![\w-])"
)


def _presentation_sources() -> list[Path]:
    return [
        path
        for path in FRONTEND.rglob("*")
        if path.suffix in {".css", ".svelte", ".ts"}
        and not path.name.endswith((".test.ts", ".d.ts", ".fixtures.ts"))
        and THEMES not in path.parents
    ]


def test_colours_are_declared_only_by_themes() -> None:
    offenders = []
    for path in _presentation_sources():
        relative = path.relative_to(FRONTEND).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = re.sub(r"white-space|/\*.*?\*/|^\s*(?://|\*).*", "", line)
            for match in COLOUR_LITERAL.finditer(stripped):
                if (relative, match.group(0).lower()) not in COLOUR_LITERAL_ALLOWLIST:
                    offenders.append(f"{relative}:{number}: {match.group(0)}")
    assert offenders == []


def test_colour_tokens_use_the_closed_role_vocabulary() -> None:
    retired = []
    built = []
    for path in _presentation_sources():
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(FRONTEND).as_posix()
        retired += [f"{relative}: {match.group(0)}" for match in RETIRED_TOKENS.finditer(text)]
        if re.search(r"--color-(?:\$\{|\{)", text):
            built.append(relative)
    assert retired == []
    assert built == [], "map projection vocabulary to a role explicitly instead of building token names"
