from __future__ import annotations

import os
from pathlib import Path

import pytest

from lychd.config.settings.root import Settings
from lychd.system.services.binding_preflight import (
    BindingPreflightError,
    BindingPreflightService,
)


def _private_file(path: Path) -> None:
    path.write_text("[server]\n", encoding="utf-8")
    path.chmod(0o600)


def _private_reactor(settings: Settings, tmp_path: Path) -> None:
    inbox = tmp_path / "triggers" / "inbox"
    journal = inbox.parent / "journal"
    inbox.mkdir(parents=True, mode=0o700)
    journal.mkdir(mode=0o700)
    inbox.chmod(0o700)
    journal.chmod(0o700)
    settings.orchestration.switching.host_reactor_dir = inbox


def test_caged_preflight_accepts_private_roots_without_existing_unit_files(
    tmp_path: Path,
) -> None:
    codex = tmp_path / "lychd.toml"
    _private_file(codex)
    settings = Settings()
    _private_reactor(settings, tmp_path)

    report = BindingPreflightService(
        codex_path=codex,
        systemctl_lookup=lambda _name: "/usr/bin/systemctl",
    ).inspect(settings, uncaged=False)

    assert report.ready is True
    assert report.issues == ()
    assert report.require_ready() == "/usr/bin/systemctl"
    assert not tuple(tmp_path.rglob("*.service"))
    assert not tuple(tmp_path.rglob("*.path"))


def test_caged_preflight_returns_every_structured_host_issue(tmp_path: Path) -> None:
    codex = tmp_path / "lychd.toml"
    codex.write_text("", encoding="utf-8")
    codex.chmod(0o644)
    settings = Settings()
    settings.orchestration.switching.actuator = "systemd"
    settings.orchestration.switching.host_reactor_dir = tmp_path / "missing" / "inbox"

    report = BindingPreflightService(
        codex_path=codex,
        current_uid=os.getuid() + 1,
        systemctl_lookup=lambda _name: None,
    ).inspect(settings, uncaged=False)

    assert {issue.code for issue in report.issues} == {
        "codex-mode",
        "codex-owner",
        "systemctl-missing",
        "caged-actuator",
        "reactor-shape",
    }
    assert sum(issue.code == "reactor-shape" for issue in report.issues) == 2
    with pytest.raises(BindingPreflightError, match="Binding preflight failed"):
        report.require_ready()


def test_caged_preflight_rejects_symlinked_reactor_boundary(tmp_path: Path) -> None:
    codex = tmp_path / "lychd.toml"
    _private_file(codex)
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    inbox = tmp_path / "triggers" / "inbox"
    inbox.parent.mkdir()
    inbox.symlink_to(real, target_is_directory=True)
    journal = inbox.parent / "journal"
    journal.mkdir(mode=0o700)
    settings = Settings()
    settings.orchestration.switching.host_reactor_dir = inbox

    report = BindingPreflightService(
        codex_path=codex,
        systemctl_lookup=lambda _name: "/usr/bin/systemctl",
    ).inspect(settings, uncaged=False)

    assert [(issue.code, issue.target) for issue in report.issues] == [
        ("reactor-shape", str(inbox)),
    ]


def test_preflight_rejects_symlinked_codex_parent(tmp_path: Path) -> None:
    real = tmp_path / "real-codex"
    real.mkdir()
    codex = real / "lychd.toml"
    _private_file(codex)
    alias = tmp_path / "codex-alias"
    alias.symlink_to(real, target_is_directory=True)
    settings = Settings()

    report = BindingPreflightService(
        codex_path=alias / "lychd.toml",
        systemctl_lookup=lambda _name: "/usr/bin/systemctl",
    ).inspect(settings, uncaged=True)

    issue = next(issue for issue in report.issues if issue.code == "codex-shape")
    assert issue.target == str(alias / "lychd.toml")
    assert str(alias) in issue.detail


def test_preflight_rejects_symlinked_reactor_parent(tmp_path: Path) -> None:
    codex = tmp_path / "lychd.toml"
    _private_file(codex)
    real = tmp_path / "real-triggers"
    inbox = real / "inbox"
    journal = real / "journal"
    inbox.mkdir(parents=True, mode=0o700)
    journal.mkdir(mode=0o700)
    alias = tmp_path / "triggers"
    alias.symlink_to(real, target_is_directory=True)
    settings = Settings()
    settings.orchestration.switching.host_reactor_dir = alias / "inbox"

    report = BindingPreflightService(
        codex_path=codex,
        systemctl_lookup=lambda _name: "/usr/bin/systemctl",
    ).inspect(settings, uncaged=False)

    assert [(issue.code, issue.target) for issue in report.issues if issue.code == "reactor-shape"] == [
        ("reactor-shape", str(alias / "inbox")),
        ("reactor-shape", str(alias / "journal")),
    ]


def test_uncaged_preflight_uses_read_only_secret_resolvers_and_aggregates_failures(
    tmp_path: Path,
) -> None:
    codex = tmp_path / "lychd.toml"
    _private_file(codex)
    settings = Settings()
    calls: list[str] = []

    def resolve_web(_settings: object) -> str:
        calls.append("web")
        msg = "web secret unavailable"
        raise ValueError(msg)

    def resolve_database(_settings: object) -> str:
        calls.append("database")
        msg = "database secret unavailable"
        raise ValueError(msg)

    report = BindingPreflightService(
        codex_path=codex,
        systemctl_lookup=lambda _name: "/usr/bin/systemctl",
        web_secret_resolver=resolve_web,
        database_secret_resolver=resolve_database,
    ).inspect(
        settings,
        uncaged=True,
        uncaged_control_plane_secrets=("runtime_token",),
    )

    assert calls == ["web", "database"]
    assert [issue.code for issue in report.issues] == [
        "uncaged-control-secret",
        "uncaged-web-secret",
        "uncaged-database-secret",
    ]
