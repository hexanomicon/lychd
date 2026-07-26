from __future__ import annotations

import os
from pathlib import Path

from lychd.system.readiness import ReadinessState
from lychd.system.readiness.sites import BindingSiteReadinessProbe


def _probe(*paths: Path) -> BindingSiteReadinessProbe:
    return BindingSiteReadinessProbe(
        sites=tuple((f"site-{index}", f"Site {index}", path) for index, path in enumerate(paths)),
        current_uid=os.getuid(),
    )


def test_absent_sites_are_safe_plans_then_verified_after_creation(tmp_path: Path) -> None:
    quadlet = tmp_path / "containers" / "systemd"
    systemd = tmp_path / "systemd" / "user"
    probe = _probe(quadlet, systemd)

    planned = probe.inspect()
    quadlet.mkdir(parents=True)
    systemd.mkdir(parents=True)
    prepared = probe.inspect()

    assert {item.state for item in planned} == {ReadinessState.PLANNED}
    assert all(item.detail == "will create shared directory" for item in planned)
    assert all(item.repairable_by_init for item in planned)
    assert {item.state for item in prepared} == {ReadinessState.VERIFIED}
    assert all(item.detail == "prepared" for item in prepared)


def test_symlinked_binding_site_is_blocked(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)

    item = _probe(linked).inspect()[0]

    assert item.state is ReadinessState.BLOCKED
    assert item.required_for_bind
    assert "symlink component" in item.detail


def test_non_directory_binding_site_is_blocked(tmp_path: Path) -> None:
    target = tmp_path / "systemd"
    target.write_text("not a directory", encoding="utf-8")

    item = _probe(target).inspect()[0]

    assert item.state is ReadinessState.BLOCKED
    assert item.detail == "target exists but is not a directory"


def test_world_writable_binding_site_is_blocked(tmp_path: Path) -> None:
    target = tmp_path / "systemd"
    target.mkdir()
    target.chmod(0o777)

    item = _probe(target).inspect()[0]

    assert item.state is ReadinessState.BLOCKED
    assert "permits another principal" in item.detail


def test_unreadable_binding_site_is_blocked(tmp_path: Path) -> None:
    target = tmp_path / "systemd"
    target.mkdir()
    target.chmod(0o300)

    try:
        item = _probe(target).inspect()[0]
    finally:
        target.chmod(0o700)

    assert item.state is ReadinessState.BLOCKED
    assert "not readable, writable, and searchable" in item.detail
