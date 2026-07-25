from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

import pytest

from lychd.system.services import lifecycle
from lychd.system.services.lifecycle import (
    CreatedResources,
    InitializationPlanner,
    LifecycleDisposition,
    LifecycleError,
    LifecycleLock,
    LifecycleReceiptStore,
    LifecycleResourceKind,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class IsolatedRoots(TypedDict):
    base: Path
    config_home: Path
    data_home: Path
    cache_home: Path
    codex: Path
    runes: Path
    crypt: Path
    postgres: Path
    postgres_data: Path
    snapshots: Path
    cache: Path
    quadlets: Path
    user_units: Path
    receipt: Path
    host_layout: tuple[Path, ...]


@pytest.fixture
def isolated_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> IsolatedRoots:
    """Move every lifecycle authority root into one disposable XDG-shaped tree."""
    config_home = tmp_path / "config"
    data_home = tmp_path / "data"
    cache_home = tmp_path / "cache"
    codex = config_home / "lychd"
    runes = codex / "runes"
    crypt = data_home / "lychd"
    postgres = crypt / "postgres"
    postgres_data = postgres / "data"
    snapshots = crypt / "snapshots"
    cache = cache_home / "lychd"
    quadlets = config_home / "containers" / "systemd"
    user_units = config_home / "systemd" / "user"
    receipt = codex / ".lychd-lifecycle.json"
    host_layout = (
        codex,
        runes,
        quadlets,
        user_units,
        crypt,
        postgres,
        postgres_data,
        snapshots,
        cache,
    )

    replacements = {
        "PATH_CODEX_ROOT": codex,
        "PATH_RUNES_DIR": runes,
        "PATH_CRYPT_ROOT": crypt,
        "PATH_POSTGRES_ROOT_DIR": postgres,
        "PATH_POSTGRESS_DATA_DIR": postgres_data,
        "PATH_POSTGRESS_SNAPSHOTS_DIR": snapshots,
        "PATH_CACHE_ROOT": cache,
        "PATH_SYSTEMD_UNITS_DIR": quadlets,
        "PATH_SYSTEMD_USER_UNITS_DIR": user_units,
        "PATH_LYCHD_TOML": codex / "lychd.toml",
        "PATH_LIFECYCLE_RECEIPT": receipt,
        "HOST_LAYOUT": host_layout,
    }
    for name, value in replacements.items():
        monkeypatch.setattr(lifecycle, name, value)

    return {
        "base": tmp_path,
        "config_home": config_home,
        "data_home": data_home,
        "cache_home": cache_home,
        "codex": codex,
        "runes": runes,
        "crypt": crypt,
        "postgres": postgres,
        "postgres_data": postgres_data,
        "snapshots": snapshots,
        "cache": cache,
        "quadlets": quadlets,
        "user_units": user_units,
        "receipt": receipt,
        "host_layout": host_layout,
    }


def _tree_snapshot(root: Path) -> tuple[tuple[str, str, bytes | str], ...]:
    """Capture enough tree state to prove a preview made no filesystem changes."""
    if not root.exists():
        return ()
    entries: list[tuple[str, str, bytes | str]] = []
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            entries.append((relative, "symlink", str(path.readlink())))
        elif path.is_file():
            entries.append((relative, "file", path.read_bytes()))
        else:
            entries.append((relative, "directory", ""))
    return tuple(entries)


def test_init_dry_run_is_side_effect_free_on_fresh_xdg(
    isolated_roots: IsolatedRoots,
) -> None:
    """The real planner may inspect a fresh topology but must not create any part of it."""
    base = isolated_roots["base"]
    receipt = isolated_roots["receipt"]
    before = _tree_snapshot(base)

    plan = InitializationPlanner(
        reactor_directories=(),
        anchor_paths=(),
        sample_paths=(),
        receipt_store=LifecycleReceiptStore(receipt),
    ).plan()

    assert plan.mutates is True
    assert any(action.disposition is LifecycleDisposition.WOULD_CREATE for action in plan.actions)
    assert _tree_snapshot(base) == before


def test_init_blocks_absent_custom_reactor_outside_receipt_authority(
    isolated_roots: IsolatedRoots,
) -> None:
    """Init never creates a custom control tree it cannot safely receipt."""
    outside_inbox = isolated_roots["base"] / "operator-control" / "inbox"

    plan = InitializationPlanner(
        reactor_directories=(outside_inbox,),
        anchor_paths=(),
        sample_paths=(),
        receipt_store=LifecycleReceiptStore(isolated_roots["receipt"]),
    ).plan()

    assert any(
        action.disposition is LifecycleDisposition.BLOCKED
        and action.target == str(outside_inbox)
        and "outside bounded initialization authority" in action.detail
        for action in plan.actions
    )
    assert not outside_inbox.parent.exists()


def test_destroy_dry_run_is_side_effect_free(
    isolated_roots: IsolatedRoots,
) -> None:
    """Planning destruction reads receipt authority without consuming it."""
    codex = isolated_roots["codex"]
    receipt = isolated_roots["receipt"]
    codex.mkdir(parents=True)
    generated = codex / "lychd.toml"
    generated.write_text("generated = true\n", encoding="utf-8")
    store = LifecycleReceiptStore(receipt)
    store.record(CreatedResources(directories=(codex,), files=(generated,)))
    before = _tree_snapshot(isolated_roots["base"])

    plan = store.plan_destroy()

    assert plan.blockers == ()
    assert any(action.target == str(generated) for action in plan.actions)
    assert _tree_snapshot(isolated_roots["base"]) == before


def test_fresh_isolated_init_destroy_round_trip_and_destroy_is_idempotent(
    isolated_roots: IsolatedRoots,
    mocker: MockerFixture,
) -> None:
    """Resources reported by the init services return exactly to the empty baseline."""
    from lychd.config.settings.root import Settings
    from lychd.system.services.codex import CodexService
    from lychd.system.services.layout import LayoutService

    base = isolated_roots["base"]
    host_layout = isolated_roots["host_layout"]
    codex = isolated_roots["codex"]
    runes = isolated_roots["runes"]
    postgres = isolated_roots["postgres"]
    receipt = isolated_roots["receipt"]
    for shared_root in (
        isolated_roots["config_home"],
        isolated_roots["data_home"],
        isolated_roots["cache_home"],
    ):
        shared_root.mkdir()
    isolated_roots["postgres_data"].mkdir(parents=True)
    baseline = _tree_snapshot(base)

    layout = LayoutService(paths=host_layout)
    mocker.patch.object(layout.btrfs, "create_subvolume", return_value=False)
    mocker.patch("lychd.system.services.codex.get_settings", return_value=Settings())
    layout_resources = layout.initialize()
    codex_resources = CodexService(
        rune_schemas=(),
        toml_path=codex / "lychd.toml",
        runes_path=runes,
        postgres_root_path=postgres,
    ).inscribe()
    store = LifecycleReceiptStore(receipt)
    store.record(CreatedResources.combine(layout_resources, codex_resources))

    store.destroy()

    assert _tree_snapshot(base) == baseline
    store.destroy()
    assert _tree_snapshot(base) == baseline


def test_modified_owned_file_blocks_before_any_effect(
    isolated_roots: IsolatedRoots,
) -> None:
    """One changed generated file blocks removal of every other pristine resource."""
    codex = isolated_roots["codex"]
    receipt = isolated_roots["receipt"]
    codex.mkdir(parents=True)
    changed = codex / "lychd.toml"
    pristine = codex / "sample.toml"
    changed.write_text("original = true\n", encoding="utf-8")
    pristine.write_text("sample = true\n", encoding="utf-8")
    store = LifecycleReceiptStore(receipt)
    store.record(CreatedResources(directories=(codex,), files=(changed, pristine)))
    changed.write_text("operator = true\n", encoding="utf-8")
    before = _tree_snapshot(isolated_roots["base"])

    plan = store.plan_destroy()

    assert any(
        action.disposition is LifecycleDisposition.BLOCKED
        and action.target == str(changed)
        and "modified" in action.detail
        for action in plan.actions
    )
    with pytest.raises(LifecycleError, match="modified after initialization"):
        store.destroy()
    assert _tree_snapshot(isolated_roots["base"]) == before


def test_unowned_content_blocks_directory_removal_and_survives(
    isolated_roots: IsolatedRoots,
) -> None:
    """A receipt never turns an entire directory subtree into deletion authority."""
    codex = isolated_roots["codex"]
    receipt = isolated_roots["receipt"]
    codex.mkdir(parents=True)
    foreign = codex / "operator-notes.txt"
    foreign.write_text("preserve me", encoding="utf-8")
    store = LifecycleReceiptStore(receipt)
    store.record(CreatedResources(directories=(codex,)))

    plan = store.plan_destroy()

    assert any(
        action.disposition is LifecycleDisposition.BLOCKED
        and action.target == str(codex)
        and "unowned entries" in action.detail
        for action in plan.actions
    )
    with pytest.raises(LifecycleError, match="unowned entries"):
        store.destroy()
    assert foreign.read_text(encoding="utf-8") == "preserve me"
    assert receipt.exists()


@pytest.mark.parametrize("receipt_content", ["not-json", '{"version": 1, "directories": ["/"], "files": []}'])
def test_corrupt_or_unsafe_receipt_fails_closed(
    isolated_roots: IsolatedRoots,
    receipt_content: str,
) -> None:
    """Malformed data and authority outside XDG roots never become deletion authority."""
    receipt = isolated_roots["receipt"]
    receipt.parent.mkdir(parents=True)
    receipt.write_text(receipt_content, encoding="utf-8")
    receipt.chmod(0o600)
    before = _tree_snapshot(isolated_roots["base"])

    with pytest.raises(LifecycleError):
        LifecycleReceiptStore(receipt).plan_destroy()

    assert _tree_snapshot(isolated_roots["base"]) == before


def test_symlink_receipt_fails_closed_without_touching_target(
    isolated_roots: IsolatedRoots,
) -> None:
    """The ownership document is read through a no-follow authority boundary."""
    receipt = isolated_roots["receipt"]
    base = isolated_roots["base"]
    outside = base / "outside.json"
    outside.write_text('{"version": 1, "directories": [], "files": []}', encoding="utf-8")
    receipt.parent.mkdir(parents=True)
    receipt.symlink_to(outside)

    with pytest.raises(LifecycleError, match="Unsafe lifecycle receipt"):
        LifecycleReceiptStore(receipt).plan_destroy()

    assert receipt.is_symlink()
    assert outside.read_text(encoding="utf-8").startswith('{"version"')


def test_preexisting_external_data_mount_is_preserved(
    isolated_roots: IsolatedRoots,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pre-existing Phylactery mount remains outside receipt authority."""
    postgres_data = isolated_roots["postgres_data"]
    receipt = isolated_roots["receipt"]
    postgres_data.mkdir(parents=True)
    sentinel = postgres_data / "PG_VERSION"
    sentinel.write_text("17\n", encoding="utf-8")
    store = LifecycleReceiptStore(receipt)
    store.record(CreatedResources())
    real_is_mount = Path.is_mount

    def is_external_mount(path: Path) -> bool:
        return path == postgres_data or real_is_mount(path)

    monkeypatch.setattr(Path, "is_mount", is_external_mount)

    plan = store.plan_destroy()

    assert any(
        action.disposition is LifecycleDisposition.PRESERVE
        and action.kind is LifecycleResourceKind.MOUNT
        and action.target == str(postgres_data)
        for action in plan.actions
    )
    store.destroy()
    assert sentinel.read_text(encoding="utf-8") == "17\n"
    assert postgres_data.exists()


def test_lifecycle_lock_rejects_a_concurrent_real_operation(tmp_path: Path) -> None:
    """Real lifecycle commands share one fail-fast interprocess exclusion gate."""
    lock_path = tmp_path / "lifecycle.lock"

    with (
        LifecycleLock(lock_path),
        pytest.raises(LifecycleError, match="already in progress"),
        LifecycleLock(lock_path),
    ):
        pytest.fail("the second lifecycle operation acquired the same lock")

    assert lock_path.stat().st_mode & 0o777 == 0o600


def test_identical_file_replacement_does_not_inherit_deletion_authority(
    isolated_roots: IsolatedRoots,
) -> None:
    """Digest equality cannot hide replacement of an init-created inode."""
    codex = isolated_roots["codex"]
    receipt = isolated_roots["receipt"]
    codex.mkdir(parents=True)
    generated = codex / "lychd.toml"
    generated.write_text("same = true\n", encoding="utf-8")
    store = LifecycleReceiptStore(receipt)
    store.record(CreatedResources(directories=(codex,), files=(generated,)))
    replacement = codex / "replacement"
    replacement.write_text("same = true\n", encoding="utf-8")
    replacement.replace(generated)

    plan = store.plan_destroy()

    assert any(
        action.disposition is LifecycleDisposition.BLOCKED
        and action.target == str(generated)
        and "identity changed" in action.detail
        for action in plan.actions
    )
    with pytest.raises(LifecycleError, match="identity changed"):
        store.destroy()
    assert generated.read_text(encoding="utf-8") == "same = true\n"


def test_anticipated_scribe_removals_unblock_empty_only_binding_anchors(
    isolated_roots: IsolatedRoots,
) -> None:
    """The joined plan understands that exact Scribe sources disappear first."""
    quadlets = isolated_roots["quadlets"]
    receipt = isolated_roots["receipt"]
    quadlets.mkdir(parents=True)
    store = LifecycleReceiptStore(receipt)
    store.record(CreatedResources(directories=(quadlets.parent, quadlets)))
    source = quadlets / "lychd-vessel.container"
    authority = quadlets / ".lychd-owned.json"
    source.write_text("[Container]\n", encoding="utf-8")
    authority.write_text("{}\n", encoding="utf-8")

    blocked = store.plan_destroy()
    joined = store.plan_destroy(anticipated_removals=(source, authority))

    assert blocked.blockers
    assert joined.blockers == ()
    assert quadlets in joined.removal_paths
