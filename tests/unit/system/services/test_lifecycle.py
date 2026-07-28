from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

import pytest

from lychd.system.services import lifecycle
from lychd.system.services.lifecycle import (
    CreatedBtrfsSubvolume,
    CreatedDirectory,
    CreatedResources,
    InitializationPlanner,
    LifecycleDisposition,
    LifecycleError,
    LifecycleLock,
    LifecycleReceiptStore,
    LifecycleResourceKind,
)

_SUBVOLUME_UUID = "12345678-1234-5678-1234-567812345678"


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


def test_successful_init_seals_exact_dedicated_root_authority(
    isolated_roots: IsolatedRoots,
) -> None:
    """The final init seal binds all dedicated roots to their kernel identities."""
    roots = (
        isolated_roots["crypt"],
        isolated_roots["cache"],
        isolated_roots["codex"],
    )
    for root in roots:
        root.mkdir(parents=True)
    store = LifecycleReceiptStore(isolated_roots["receipt"])

    before = store.plan_dedicated_root_attestation()
    store.seal_dedicated_roots()
    identities = store.require_dedicated_root_identities(roots)
    after = store.plan_dedicated_root_attestation()

    assert before.disposition is LifecycleDisposition.WOULD_CREATE
    assert tuple(identity.path for identity in identities) == roots
    assert after.disposition is LifecycleDisposition.PRESERVE
    assert isolated_roots["receipt"].stat().st_mode & 0o777 == 0o600


def test_absent_receipt_and_missing_peer_never_mask_an_unsafe_existing_root(
    isolated_roots: IsolatedRoots,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Root adoption blocks before init can write through an existing mount."""
    crypt = isolated_roots["crypt"]
    crypt.mkdir(parents=True)

    def reject_mount_boundary(path: Path) -> os.stat_result:
        if path == crypt:
            msg = f"Lifecycle authority target is a mount boundary: {path}"
            raise LifecycleError(msg)
        return path.stat()

    monkeypatch.setattr(
        "lychd.system.services.lifecycle.receipt.directory_identity_on_parent_mount",
        reject_mount_boundary,
    )
    plan = InitializationPlanner(
        reactor_directories=(),
        anchor_paths=(),
        sample_paths=(),
        receipt_store=LifecycleReceiptStore(isolated_roots["receipt"]),
    ).plan()

    assert not isolated_roots["receipt"].exists()
    assert any(
        action.disposition is LifecycleDisposition.BLOCKED
        and action.kind is LifecycleResourceKind.RECEIPT
        and "mount boundary" in action.detail
        for action in plan.actions
    )


def test_directory_mount_identity_rejects_same_device_mount_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Distinct mount IDs block adoption even when both paths share st_dev."""
    from lychd.system.services.lifecycle import mount_identity

    root = tmp_path / "dedicated"
    root.mkdir()
    mount_ids = iter((41, 42))

    def next_mount_id(_descriptor: int) -> int:
        return next(mount_ids)

    monkeypatch.setattr(
        mount_identity,
        "mount_id_for_fd",
        next_mount_id,
    )

    assert root.stat().st_dev == root.parent.stat().st_dev
    with pytest.raises(LifecycleError, match="mount boundary"):
        mount_identity.directory_identity_on_parent_mount(root)


def test_dedicated_root_authority_detects_identity_drift(
    isolated_roots: IsolatedRoots,
) -> None:
    """Replacing an adopted root never inherits the prior init authority."""
    roots = (
        isolated_roots["crypt"],
        isolated_roots["cache"],
        isolated_roots["codex"],
    )
    for root in roots:
        root.mkdir(parents=True)
    store = LifecycleReceiptStore(isolated_roots["receipt"])
    store.seal_dedicated_roots()
    original = isolated_roots["cache"].with_name("lychd-original")
    isolated_roots["cache"].rename(original)
    isolated_roots["cache"].mkdir()

    with pytest.raises(LifecycleError, match="identity drifted"):
        store.require_dedicated_root_identities(roots)


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


def test_receipt_records_creation_identity_without_restatting_replacement(
    isolated_roots: IsolatedRoots,
) -> None:
    """A replaced public name never inherits a just-created directory receipt."""
    codex = isolated_roots["codex"]
    codex.mkdir(parents=True)
    created_metadata = codex.lstat()
    resources = CreatedResources(
        directories=(codex,),
        directory_identities=(
            CreatedDirectory(
                path=codex,
                device=created_metadata.st_dev,
                inode=created_metadata.st_ino,
            ),
        ),
    )
    displaced = codex.with_name("lychd-created-by-init")
    codex.rename(displaced)
    codex.mkdir()
    replacement_metadata = codex.lstat()
    store = LifecycleReceiptStore(isolated_roots["receipt"])

    store.record(resources)

    document = json.loads(isolated_roots["receipt"].read_text(encoding="utf-8"))
    assert document["directories"] == [
        {
            "path": str(codex),
            "device": created_metadata.st_dev,
            "inode": created_metadata.st_ino,
        }
    ]
    assert replacement_metadata.st_ino != created_metadata.st_ino
    plan = store.plan_destroy()
    assert any(
        action.disposition is LifecycleDisposition.BLOCKED
        and action.target == str(codex)
        and "identity changed" in action.detail
        for action in plan.actions
    )


def test_receipt_v2_round_trips_exact_created_subvolume_identity(
    isolated_roots: IsolatedRoots,
) -> None:
    """Version 2 preserves creation identity without mixing a replacement path."""
    postgres_data = isolated_roots["postgres_data"]
    postgres_data.mkdir(parents=True)
    isolated_roots["receipt"].parent.mkdir(parents=True)
    metadata = postgres_data.lstat()
    created = CreatedBtrfsSubvolume(
        path=postgres_data,
        device=metadata.st_dev,
        inode=metadata.st_ino,
        subvolume_uuid=_SUBVOLUME_UUID,
        subvolume_id=259,
    )
    displaced = postgres_data.with_name("data-created-by-init")
    postgres_data.rename(displaced)
    postgres_data.mkdir()
    store = LifecycleReceiptStore(isolated_roots["receipt"])

    store.record(CreatedResources(subvolumes=(created,)))

    document = json.loads(isolated_roots["receipt"].read_text(encoding="utf-8"))
    assert document["version"] == 2
    assert document["directories"] == []
    assert document["subvolumes"] == [
        {
            "path": str(postgres_data),
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "subvolume_uuid": _SUBVOLUME_UUID,
            "subvolume_id": 259,
        }
    ]
    assert store.created_subvolume(postgres_data) == created


def test_legacy_v1_receipt_loads_without_subvolume_authority(
    isolated_roots: IsolatedRoots,
) -> None:
    """A v1 receipt remains readable but cannot authorize Btrfs deletion."""
    receipt = isolated_roots["receipt"]
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        '{"version":1,"dedicated_roots":[],"directories":[],"files":[]}\n',
        encoding="utf-8",
    )
    receipt.chmod(0o600)
    store = LifecycleReceiptStore(receipt)

    assert store.created_subvolume(isolated_roots["postgres_data"]) is None
    assert store.plan_destroy().blockers == ()


def test_legacy_v1_receipt_cannot_smuggle_v2_subvolume_authority(
    isolated_roots: IsolatedRoots,
) -> None:
    """The schema version, not merely field shape, gates deletion authority."""
    postgres_data = isolated_roots["postgres_data"]
    postgres_data.mkdir(parents=True)
    metadata = postgres_data.lstat()
    receipt = isolated_roots["receipt"]
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        json.dumps(
            {
                "version": 1,
                "dedicated_roots": [],
                "directories": [],
                "files": [],
                "subvolumes": [
                    {
                        "path": str(postgres_data),
                        "device": metadata.st_dev,
                        "inode": metadata.st_ino,
                        "subvolume_uuid": _SUBVOLUME_UUID,
                        "subvolume_id": 259,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    receipt.chmod(0o600)

    with pytest.raises(LifecycleError, match="version 1 cannot carry"):
        LifecycleReceiptStore(receipt).created_subvolume(postgres_data)


def test_recording_against_v1_never_adopts_existing_postgres_data(
    isolated_roots: IsolatedRoots,
) -> None:
    """Upgrading the receipt schema does not infer authority from live geography."""
    postgres_data = isolated_roots["postgres_data"]
    postgres_data.mkdir(parents=True)
    receipt = isolated_roots["receipt"]
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        '{"version":1,"dedicated_roots":[],"directories":[],"files":[]}\n',
        encoding="utf-8",
    )
    receipt.chmod(0o600)
    before = postgres_data.lstat()
    store = LifecycleReceiptStore(receipt)

    store.record(CreatedResources())

    document = json.loads(receipt.read_text(encoding="utf-8"))
    assert document["version"] == 2
    assert document["subvolumes"] == []
    assert store.created_subvolume(postgres_data) is None
    assert postgres_data.lstat().st_ino == before.st_ino


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


def test_default_lifecycle_lock_contends_across_different_tmpdir_environments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The generated Reactor and an operator CLI cannot select different locks."""
    codex_root = tmp_path / "codex"
    other_tmp = tmp_path / "other-tmp"
    other_tmp.mkdir()
    monkeypatch.setattr(lifecycle, "PATH_CODEX_ROOT", codex_root)
    lock = LifecycleLock()
    script = """
import os
from pathlib import Path
from lychd.system.services import lifecycle
from lychd.system.services.lifecycle import LifecycleError, LifecycleLock

lifecycle.PATH_CODEX_ROOT = Path(os.environ["LYCHD_TEST_CODEX_ROOT"])
try:
    with LifecycleLock():
        pass
except LifecycleError:
    raise SystemExit(0)
raise SystemExit(1)
"""
    environment = {
        **os.environ,
        "TMPDIR": str(other_tmp),
        "LYCHD_TEST_CODEX_ROOT": str(codex_root),
    }
    try:
        with lock:
            result = subprocess.run(  # noqa: S603 - fixed interpreter and repository-controlled script
                [sys.executable, "-c", script],
                check=False,
                capture_output=True,
                env=environment,
                text=True,
            )
        assert result.returncode == 0, result.stderr
        assert lock.path.parent == Path("/tmp")  # noqa: S108 - verifies the fixed host lock namespace
    finally:
        lock.path.unlink(missing_ok=True)


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
