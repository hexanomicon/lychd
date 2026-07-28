"""Static-client architectural boundaries not covered by Svelte tooling."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FRONTEND = REPO / "frontend" / "src"


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
    package = json.loads((REPO / "frontend" / "package.json").read_text(encoding="utf-8"))
    declared = {*package.get("dependencies", {}), *package.get("devDependencies", {})}
    forbidden_dependencies = {
        "autoprefixer",
        "postcss",
        "sass",
        "tailwindcss",
        "@tailwindcss/postcss",
        "@tailwindcss/vite",
    }
    app_css = (FRONTEND / "app.css").read_text(encoding="utf-8").lower()

    assert declared.isdisjoint(forbidden_dependencies)
    assert '@import "tailwindcss"' not in app_css
    assert "@theme" not in app_css
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
