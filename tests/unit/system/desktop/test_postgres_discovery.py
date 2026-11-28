"""Select a single native PostgreSQL installation on macOS."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import click
import pytest

from lychd.system import desktop


@pytest.fixture
def macos_tools(monkeypatch: pytest.MonkeyPatch) -> dict[tuple[str, str | None], str]:
    tools: dict[tuple[str, str | None], str] = {}

    def which(name: str, path: str | None = None) -> str | None:
        return tools.get((name, path))

    monkeypatch.delenv("LYCHD_PG_BIN", raising=False)
    monkeypatch.setattr(desktop, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(desktop.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(desktop.shutil, "which", which)
    return tools


@pytest.mark.parametrize(("machine", "prefix"), [("arm64", "/opt/homebrew"), ("x86_64", "/usr/local")])
def test_macos_finds_versioned_homebrew_without_shell_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    macos_tools: dict[tuple[str, str | None], str],
    machine: str,
    prefix: str,
) -> None:
    monkeypatch.setattr(desktop.platform, "machine", lambda: machine)
    bin_dir = tmp_path.resolve() / "Cellar" / "postgresql@18" / "18.7" / "bin"
    macos_tools.update(
        {
            ("initdb", f"{prefix}/opt/postgresql@18/bin"): str(bin_dir / "initdb"),
            ("pg_ctl", str(bin_dir)): str(bin_dir / "pg_ctl"),
            ("pg_ctl", None): "/another-installation/pg_ctl",
        }
    )
    probe = Mock(return_value="initdb (PostgreSQL) 18.7\n")
    monkeypatch.setattr(desktop.subprocess, "check_output", probe)
    assert desktop.postgres_program("pg_ctl") == str(bin_dir / "pg_ctl")
    probe.assert_called_once_with([str(bin_dir / "initdb"), "--version"], text=True)


@pytest.mark.parametrize("on_path", ["18.6", "17.8"])
def test_macos_prefers_compatible_path_installation_and_keeps_its_tools_together(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, macos_tools: dict[tuple[str, str | None], str], on_path: str
) -> None:
    custom = tmp_path.resolve() / "custom"
    brew = tmp_path.resolve() / "brew"
    macos_tools.update(
        {
            ("initdb", None): str(custom / "initdb"),
            ("initdb", "/opt/homebrew/opt/postgresql@18/bin"): str(brew / "initdb"),
            ("pg_ctl", str(custom)): str(custom / "pg_ctl"),
            ("pg_ctl", str(brew)): str(brew / "pg_ctl"),
            ("pg_controldata", None): "/unrelated/pg_controldata",
        }
    )
    versions = [on_path] if on_path == "18.6" else [on_path, "18.7"]
    probe = Mock(side_effect=[f"initdb (PostgreSQL) {v}\n" for v in versions])
    monkeypatch.setattr(desktop.subprocess, "check_output", probe)

    selected = custom if on_path == "18.6" else brew
    with click.Context(desktop.desktop):
        assert desktop.postgres_program("pg_ctl") == str(selected / "pg_ctl")
        with pytest.raises(click.ClickException, match="pg_controldata is unavailable"):
            desktop.postgres_program("pg_controldata")
    assert probe.call_count == len(versions)


def test_incompatible_path_installation_cannot_supply_management_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, macos_tools: dict[tuple[str, str | None], str]
) -> None:
    macos_tools.update({("initdb", None): str(tmp_path / "initdb"), ("pg_ctl", None): str(tmp_path / "pg_ctl")})
    monkeypatch.setattr(desktop.subprocess, "check_output", Mock(return_value="initdb (PostgreSQL) 17.8\n"))
    with pytest.raises(click.ClickException, match=r"Expected PostgreSQL 18, found initdb \(PostgreSQL\) 17.8"):
        desktop.postgres_program("pg_ctl")


def test_explicit_pg_bin_is_authoritative_even_when_the_tool_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LYCHD_PG_BIN", "/selected/bin")
    monkeypatch.setattr(desktop, "sys", SimpleNamespace(platform="darwin"))
    lookup = Mock(return_value=None)
    monkeypatch.setattr(desktop.shutil, "which", lookup)
    with pytest.raises(click.ClickException, match="pg_ctl is unavailable"):
        desktop.postgres_program("pg_ctl")
    lookup.assert_called_once_with("pg_ctl", path="/selected/bin")
