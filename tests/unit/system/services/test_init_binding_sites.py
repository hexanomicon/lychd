"""Real filesystem evidence for initialization's shared binding-site admission."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

import pytest

from lychd.system import constants
from lychd.system.binding_sites import BindingSites, BindingSiteState, inspect_binding_site
from lychd.system.services import layout
from lychd.system.services.lifecycle.initialization import (
    InitializationExecutor,
    InitializationPlanner,
    InitializationRecorder,
)
from lychd.system.services.lifecycle.models import CreatedResources, LifecycleDisposition, LifecycleError
from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore

_COMPONENTS = ("containers", "containers/systemd", "systemd", "systemd/user")


@dataclass(frozen=True)
class InitSites:
    root: Path
    config: Path
    sites: BindingSites
    receipt: LifecycleReceiptStore

    def planner(self) -> InitializationPlanner:
        return InitializationPlanner(
            reactor_directories=(), anchor_paths=(), sample_paths=(), receipt_store=self.receipt
        )


@pytest.fixture
def init_sites(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> InitSites:
    """Redirect path authorities only; all permissions and verdicts remain real."""
    root = tmp_path.resolve()
    config, data, cache = (root / name for name in ("config", "data", "cache"))
    for path in (config, data, cache):
        path.mkdir(mode=0o700)
    codex, crypt, forge = config / "lychd", data / "lychd", cache / "lychd"
    sites = BindingSites(quadlet=config / "containers/systemd", systemd_user=config / "systemd/user")
    receipt = codex / ".lychd-lifecycle.json"
    replacements = {
        "PATH_CODEX_ROOT": codex,
        "PATH_RUNES_DIR": codex / "runes",
        "PATH_CRYPT_ROOT": crypt,
        "PATH_POSTGRES_ROOT_DIR": crypt / "postgres",
        "PATH_POSTGRESS_DATA_DIR": crypt / "postgres/data",
        "PATH_POSTGRESS_SNAPSHOTS_DIR": crypt / "snapshots",
        "PATH_CACHE_ROOT": forge,
        "PATH_SYSTEMD_UNITS_DIR": sites.quadlet,
        "PATH_SYSTEMD_USER_UNITS_DIR": sites.systemd_user,
        "PATH_LYCHD_TOML": codex / "lychd.toml",
        "PATH_LIFECYCLE_RECEIPT": receipt,
        "HOST_LAYOUT": (codex, crypt, forge, *sites.paths),
    }
    for name, value in replacements.items():
        monkeypatch.setattr(constants, name, value)
    monkeypatch.setattr(layout, "DEFAULT_BINDING_SITES", sites)
    return InitSites(root=root, config=config, sites=sites, receipt=LifecycleReceiptStore(receipt))


@pytest.mark.parametrize("component", _COMPONENTS)
@pytest.mark.parametrize("mode", [0o777, 0o770, 0o500])
def test_planner_blocks_unsafe_existing_binding_component(init_sites: InitSites, component: str, mode: int) -> None:
    path = init_sites.config / component
    path.mkdir(parents=True)
    path.chmod(mode)
    try:
        verdict = inspect_binding_site(path, current_uid=os.getuid())
        assert verdict.state is BindingSiteState.BLOCKED
        plan = init_sites.planner().plan()
        action = next(action for action in plan.actions if action.target == str(path))
        assert action.disposition is LifecycleDisposition.BLOCKED
        assert verdict.detail in action.detail
        with pytest.raises(LifecycleError, match="blocked"):
            plan.require_executable()
        assert not init_sites.receipt.exists
        assert stat.S_IMODE(path.stat().st_mode) == mode
    finally:
        path.chmod(0o700)


@pytest.mark.parametrize("component", _COMPONENTS)
@pytest.mark.parametrize("mode", [0o777, 0o500])
def test_apply_independently_refuses_unsafe_existing_binding_component(
    init_sites: InitSites, component: str, mode: int
) -> None:
    path = init_sites.config / component
    path.mkdir(parents=True)
    path.chmod(mode)
    before = path.stat()
    try:
        with pytest.raises(RuntimeError, match=r"[Bb]inding"):
            layout.LayoutService(paths=(path,)).initialize()
        assert path.stat() == before
        assert not init_sites.receipt.exists
    finally:
        path.chmod(0o700)


@pytest.mark.parametrize("site_name", ["quadlet", "systemd_user"])
@pytest.mark.parametrize("present", [False, True])
def test_unsafe_ancestor_blocks_planning_and_apply_before_creation(
    init_sites: InitSites, site_name: str, *, present: bool
) -> None:
    site = init_sites.sites.quadlet if site_name == "quadlet" else init_sites.sites.systemd_user
    if present:
        site.mkdir(parents=True)
    init_sites.config.chmod(0o777)
    before = tuple(init_sites.root.rglob("*"))
    try:
        plan = init_sites.planner().plan()
        action = next(action for action in plan.actions if action.target == str(site))
        assert action.disposition is LifecycleDisposition.BLOCKED
        assert "ancestor" in action.detail
        with pytest.raises(RuntimeError, match="ancestor"):
            layout.LayoutService(paths=(site,)).initialize()
        assert tuple(init_sites.root.rglob("*")) == before
    finally:
        init_sites.config.chmod(0o700)


@pytest.mark.parametrize("component", _COMPONENTS)
def test_safe_existing_binding_modes_and_contents_are_preserved(init_sites: InitSites, component: str) -> None:
    path = init_sites.config / component
    path.mkdir(parents=True)
    path.chmod(0o755)
    sentinel = path / "operator-owned"
    sentinel.write_bytes(b"preserve me\n")
    before = path.stat()
    plan = init_sites.planner().plan()
    plan.require_executable()
    action = next(action for action in plan.actions if action.target == str(path))
    assert action.disposition is LifecycleDisposition.PRESERVE
    assert layout.LayoutService(paths=(path,)).initialize() == CreatedResources()
    assert path.stat() == before
    assert sentinel.read_bytes() == b"preserve me\n"
    assert not init_sites.receipt.exists


def test_executor_rejects_real_binding_mode_drift_before_effect(init_sites: InitSites) -> None:
    site = init_sites.sites.quadlet
    site.mkdir(parents=True)
    approved = init_sites.planner().plan()
    approved.require_executable()
    site.chmod(0o777)
    called = False

    def effect(_record: InitializationRecorder) -> CreatedResources:
        nonlocal called
        called = True
        return CreatedResources()

    with pytest.raises(LifecycleError, match="state changed after planning"):
        InitializationExecutor(planner=init_sites.planner(), receipt=init_sites.receipt).execute(
            approved, effects=(effect,)
        )
    assert not called
    assert stat.S_IMODE(site.stat().st_mode) == 0o777
    assert not init_sites.receipt.exists


def test_late_unsafe_binding_site_refuses_before_earlier_layout_creation(init_sites: InitSites) -> None:
    site = init_sites.sites.quadlet
    site.mkdir(parents=True)
    site.chmod(0o777)
    earlier = init_sites.root / "ordinary"
    with pytest.raises(RuntimeError, match="binding"):
        layout.LayoutService(paths=(earlier, site)).initialize()
    assert not earlier.exists()
    assert stat.S_IMODE(site.stat().st_mode) == 0o777


@pytest.mark.parametrize("present", [False, True])
def test_binding_leaf_also_requires_usable_shared_parent(init_sites: InitSites, *, present: bool) -> None:
    site = init_sites.sites.quadlet
    site.parent.mkdir()
    if present:
        site.mkdir(mode=0o755)
    site.parent.chmod(0o500)
    try:
        with pytest.raises(RuntimeError, match="readable, writable, and searchable"):
            layout.LayoutService(paths=(site,)).initialize()
        assert site.exists() is present
        assert stat.S_IMODE(site.parent.stat().st_mode) == 0o500
    finally:
        site.parent.chmod(0o700)


@pytest.mark.parametrize("linked_component", ["parent", "leaf"])
def test_symlink_binding_component_never_admits_init(init_sites: InitSites, linked_component: str) -> None:
    site = init_sites.sites.quadlet
    actual = init_sites.root / "operator-directory"
    actual.mkdir(mode=0o755)
    if linked_component == "parent":
        site.parent.symlink_to(actual, target_is_directory=True)
    else:
        site.parent.mkdir()
        site.symlink_to(actual, target_is_directory=True)
    before = actual.stat()
    plan = init_sites.planner().plan()
    with pytest.raises(LifecycleError, match="symlink"):
        plan.require_executable()
    with pytest.raises(RuntimeError, match="symlink"):
        layout.LayoutService(paths=(site,)).initialize()
    assert actual.stat() == before


@pytest.mark.parametrize("race_mode", [0o755, 0o777])
def test_binding_race_winner_is_reinspected_before_journaling(
    init_sites: InitSites, monkeypatch: pytest.MonkeyPatch, race_mode: int
) -> None:
    """A real concurrent directory is never repaired or adopted by init."""
    site = init_sites.sites.quadlet
    site.parent.mkdir()
    original_create = layout.DirectoryProvisioning.create
    journaled: list[CreatedResources] = []

    def race_create(self: layout.DirectoryProvisioning, path: Path, *, mode: int | None = None) -> None:
        if path == site:
            site.mkdir()
            site.chmod(race_mode)
        original_create(self, path, mode=mode)

    monkeypatch.setattr(layout.DirectoryProvisioning, "create", race_create)
    service = layout.LayoutService(paths=(site,))
    if race_mode == 0o777:
        with pytest.raises(RuntimeError, match="binding"):
            service.initialize(on_created=journaled.append)
        assert journaled == []
    else:
        assert service.initialize(on_created=journaled.append) == CreatedResources()
        assert journaled == [CreatedResources()]
    assert stat.S_IMODE(site.stat().st_mode) == race_mode
    assert not init_sites.receipt.exists


pytestmark = pytest.mark.usefixtures("persistent_identity_observer")
