from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Protocol, cast
from unittest.mock import MagicMock

import pytest

from lychd.system.atomic_paths import rename_exchange_at, rename_noreplace_at
from lychd.system.binding_sites import AttestedBindingSite, AttestedBindingSites
from lychd.system.interruptions import (
    find_terminal_interruption,
    iter_exception_graph,
)
from lychd.system.schemas import QuadletContainer, QuadletPod, QuadletTarget, SystemdService
from lychd.system.services.scribe import (
    ScribeConflictError,
    ScribeGenerationError,
    ScribeOwnershipError,
    ScribeService,
    ScribeTransactionError,
    ScribeTransactionState,
)
from lychd.system.services.scribe import storage as storage_module
from lychd.system.services.scribe.models import (
    BindingBase,
    BindingWriteSet,
    OwnershipManifest,
)
from lychd.system.services.scribe.storage import (
    AtomicMutation,
    AtomicOutcome,
    AttestedPath,
    PathState,
    PathStateIndeterminateError,
    PinnedPath,
)
from lychd.system.services.scribe.transaction import BindingTransaction
from lychd.system.services.scribe.workspace import (
    TransactionWorkspace,
    WorkspaceSettlementError,
)


class _MutableProgress(Protocol):
    mutations: list[AtomicMutation]


@pytest.fixture
def templates_dir(tmp_path: Path) -> Path:
    """Create mock templates."""
    directory = tmp_path / "templates"
    directory.mkdir()
    (directory / "container.jinja").write_text(
        "ContainerName={{ container_name }} Description={{ description }}", encoding="utf-8"
    )
    (directory / "pod.jinja").write_text("PodName={{ pod_name }}", encoding="utf-8")
    (directory / "target.jinja").write_text("Description={{ description }}", encoding="utf-8")
    return directory


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "output"
    directory.mkdir()
    return directory


@pytest.fixture
def systemd_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "systemd"
    directory.mkdir()
    return directory


@pytest.fixture
def scribe(templates_dir: Path, output_dir: Path, systemd_dir: Path) -> ScribeService:
    return ScribeService(templates_dir=templates_dir, output_dir=output_dir, systemd_dir=systemd_dir)


def _container(*, description: str = "desc") -> QuadletContainer:
    return QuadletContainer(
        container_name="lychd-hermes",
        image="ollama/ollama",
        description=description,
    )


def test_scribe_requires_initialization_prepared_binding_sites(
    templates_dir: Path,
    tmp_path: Path,
) -> None:
    """Binding compilation never recreates shared host directories."""
    scribe = ScribeService(
        templates_dir=templates_dir,
        output_dir=tmp_path / "containers" / "systemd",
        systemd_dir=tmp_path / "systemd" / "user",
    )

    with pytest.raises(ScribeOwnershipError, match=r"run `lychd init` first"):
        scribe.plan_reconcile_all([_container()], plain_units={})

    assert not (tmp_path / "containers").exists()
    assert not (tmp_path / "systemd").exists()


def _ownership(output_dir: Path) -> dict[str, object]:
    return json.loads((output_dir / ".lychd-owned.json").read_text(encoding="utf-8"))


def test_scribe_inscribes_split_sites_and_exact_ownership(
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    pod = QuadletPod(pod_name="lychd")
    target = QuadletTarget(name="logic", description="Logic Coven")

    scribe.generate_all([pod, _container(), target])

    assert "PodName=lychd" in (output_dir / "lychd.pod").read_text()
    assert "ContainerName=lychd-hermes" in (output_dir / "lychd-hermes.container").read_text()
    assert not (output_dir / "lychd-coven-logic.target").exists()
    assert "Description=Logic Coven" in (systemd_dir / "lychd-coven-logic.target").read_text()
    assert _ownership(output_dir) == {
        "quadlet": ["lychd-hermes.container", "lychd.pod"],
        "systemd": ["lychd-coven-logic.target"],
        "version": 1,
    }
    ownership_path = output_dir / ".lychd-owned.json"
    assert ownership_path.stat().st_uid == os.getuid()
    assert ownership_path.stat().st_mode & 0o777 == 0o600
    assert not (output_dir / ".git").exists()


def test_scribe_reconcile_plan_is_effect_free_and_matches_execution(
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """Bind preview classifies the same desired files without creating them."""
    initial = scribe.plan_reconcile_all([_container()], plain_units={})

    assert {change.kind for change in initial.changes} == {"create"}
    assert not (output_dir / "lychd-hermes.container").exists()
    assert not (output_dir / ".lychd-owned.json").exists()

    scribe.reconcile_all([_container()], plain_units={})
    settled = scribe.plan_reconcile_all([_container()], plain_units={})
    assert not settled.mutates
    assert {change.kind for change in settled.changes} == {"preserve"}
    source = output_dir / "lychd-hermes.container"
    authority = output_dir / ".lychd-owned.json"
    before = {
        path: (path.stat().st_ino, path.stat().st_mtime_ns) for path in (output_dir, systemd_dir, source, authority)
    }

    committed_generation = scribe.reconcile_all(
        [_container()],
        plain_units={},
        expected_generation=settled.observed_generation,
        expected_desired_generation=settled.desired_generation,
    )

    after = {
        path: (path.stat().st_ino, path.stat().st_mtime_ns) for path in (output_dir, systemd_dir, source, authority)
    }
    assert after == before
    assert committed_generation == settled.observed_generation

    changed = scribe.plan_reconcile_all([_container(description="new")], plain_units={})
    assert any(change.kind == "update" and change.path.name == "lychd-hermes.container" for change in changed.changes)

    empty = scribe.plan_reconcile_all([], plain_units={})
    assert any(change.kind == "remove" and change.path.name == "lychd-hermes.container" for change in empty.changes)


def test_reconcile_plan_generation_distinguishes_same_disposition_content_drift(
    scribe: ScribeService,
    systemd_dir: Path,
) -> None:
    """An update-to-update drift changes the plan precondition fingerprint."""
    filename = "lychd-reactor.service"
    target = systemd_dir / filename
    desired = {filename: "desired\n"}
    scribe.reconcile_all([], plain_units=desired)

    target.write_text("drift-a\n", encoding="utf-8")
    first = scribe.plan_reconcile_all([], plain_units=desired)
    target.write_text("drift-b\n", encoding="utf-8")
    second = scribe.plan_reconcile_all([], plain_units=desired)

    assert first.changes == second.changes
    assert first.observed_generation != second.observed_generation
    assert first != second


def test_reconcile_all_rejects_generation_drift_at_commit(
    scribe: ScribeService,
    systemd_dir: Path,
) -> None:
    """The approved observation remains a compare-and-swap precondition."""
    filename = "lychd-reactor.service"
    target = systemd_dir / filename
    scribe.reconcile_all([], plain_units={filename: "old\n"})
    approved = scribe.plan_reconcile_all([], plain_units={filename: "desired\n"})
    target.write_text("operator drift\n", encoding="utf-8")

    with pytest.raises(ScribeGenerationError, match="changed after planning"):
        scribe.reconcile_all(
            [],
            plain_units={filename: "desired\n"},
            expected_generation=approved.observed_generation,
        )

    assert target.read_text(encoding="utf-8") == "operator drift\n"


def test_reconcile_all_rejects_unapproved_desired_bytes_at_commit(
    scribe: ScribeService,
    systemd_dir: Path,
) -> None:
    """The CAS binds both observed state and the exact approved desired bytes."""
    filename = "lychd-reactor.service"
    approved = scribe.plan_reconcile_all([], plain_units={filename: "approved\n"})

    with pytest.raises(ScribeGenerationError, match="Desired binding bytes changed"):
        scribe.reconcile_all(
            [],
            plain_units={filename: "different\n"},
            expected_generation=approved.observed_generation,
            expected_desired_generation=approved.desired_generation,
        )

    assert not (systemd_dir / filename).exists()


def test_reconcile_all_never_adopts_target_created_after_final_cas(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """Atomic no-overwrite installation preserves a last-moment creator."""
    scribe.reconcile_all([], plain_units={})
    filename = "lychd-reactor.service"
    target = systemd_dir / filename
    approved = scribe.plan_reconcile_all([], plain_units={filename: "desired\n"})
    old_ownership = (output_dir / ".lychd-owned.json").read_bytes()
    raced = False

    def create_target_before_install(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal raced
        if destination_name == target.name and not raced:
            raced = True
            target.write_text("concurrent creator\n", encoding="utf-8")
        rename_noreplace_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.services.scribe.storage.rename_noreplace_at",
        create_target_before_install,
    )

    with pytest.raises(ScribeGenerationError, match="preserved it"):
        scribe.reconcile_all(
            [],
            plain_units={filename: "desired\n"},
            expected_generation=approved.observed_generation,
            expected_desired_generation=approved.desired_generation,
        )

    assert target.read_text(encoding="utf-8") == "concurrent creator\n"
    assert (output_dir / ".lychd-owned.json").read_bytes() == old_ownership


def test_reconcile_all_rejects_owned_edit_after_final_cas_without_stale_restore(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """A per-path precondition protects edits made after backup preparation."""
    old_target = QuadletTarget(name="logic", description="old target")
    scribe.reconcile_all(
        [_container(description="old container"), old_target],
        plain_units={},
    )
    quadlet = output_dir / "lychd-hermes.container"
    target = systemd_dir / "lychd-coven-logic.target"
    old_quadlet = quadlet.read_bytes()
    old_ownership = (output_dir / ".lychd-owned.json").read_bytes()
    approved = scribe.plan_reconcile_all(
        [
            _container(description="new container"),
            QuadletTarget(name="logic", description="new target"),
        ],
        plain_units={},
    )
    transaction = getattr(scribe, "_transaction")  # noqa: B009 - inject race boundary
    real_require = getattr(transaction, "_require_generation")  # noqa: B009
    checks = 0

    def edit_after_generation_check(
        write_set: BindingWriteSet,
        *,
        expected: str | None,
        expected_desired: str | None,
    ) -> None:
        nonlocal checks
        checks += 1
        real_require(
            write_set,
            expected=expected,
            expected_desired=expected_desired,
        )
        if checks == 2:
            target.write_text("concurrent operator edit", encoding="utf-8")

    monkeypatch.setattr(transaction, "_require_generation", edit_after_generation_check)

    with pytest.raises(
        ScribeTransactionError,
        match="exact mutations were rolled back",
    ) as failure:
        scribe.reconcile_all(
            [
                _container(description="new container"),
                QuadletTarget(name="logic", description="new target"),
            ],
            plain_units={},
            expected_generation=approved.observed_generation,
            expected_desired_generation=approved.desired_generation,
        )

    assert failure.value.state is ScribeTransactionState.ROLLED_BACK
    assert quadlet.read_bytes() == old_quadlet
    assert target.read_text(encoding="utf-8") == "concurrent operator edit"
    assert (output_dir / ".lychd-owned.json").read_bytes() == old_ownership


def test_scribe_preserves_every_unowned_file_even_with_managed_suffix(
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    foreign_quadlet = output_dir / "foreign.container"
    foreign_target = systemd_dir / "foreign.target"
    unrelated = output_dir / "important.txt"
    foreign_quadlet.write_text("foreign", encoding="utf-8")
    foreign_target.write_text("foreign", encoding="utf-8")
    unrelated.write_text("operator", encoding="utf-8")

    scribe.generate_all([])

    assert foreign_quadlet.read_text(encoding="utf-8") == "foreign"
    assert foreign_target.read_text(encoding="utf-8") == "foreign"
    assert unrelated.read_text(encoding="utf-8") == "operator"


def test_scribe_removes_only_stale_exactly_owned_files(
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    scribe.generate_all([_container(), QuadletTarget(name="logic", description="old")])
    scribe.generate_all([])

    assert not (output_dir / "lychd-hermes.container").exists()
    assert not (systemd_dir / "lychd-coven-logic.target").exists()
    assert _ownership(output_dir) == {"quadlet": [], "systemd": [], "version": 1}


@pytest.mark.parametrize(
    ("site", "filename"),
    [
        ("quadlet", "lychd-hermes.container"),
        ("systemd", "lychd-coven-logic.target"),
    ],
)
def test_scribe_rejects_conflicting_unowned_target_names(
    site: str,
    filename: str,
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    directory = output_dir if site == "quadlet" else systemd_dir
    occupied = directory / filename
    occupied.write_text("operator-owned", encoding="utf-8")
    manifests = [_container()] if site == "quadlet" else [QuadletTarget(name="logic", description="new")]

    with pytest.raises(ScribeConflictError, match="unowned"):
        scribe.generate_all(manifests)

    assert occupied.read_text(encoding="utf-8") == "operator-owned"
    assert not (output_dir / ".lychd-owned.json").exists()


@pytest.mark.parametrize(
    "manifest",
    [
        "not-json",
        json.dumps({"version": 1, "quadlet": ["../foreign.container"], "systemd": []}),
        json.dumps({"version": 1, "quadlet": ["foreign.container"], "systemd": []}),
        json.dumps({"version": 1, "quadlet": [], "systemd": [], "unexpected": True}),
        '{"version": 1, "quadlet": [], "quadlet": [], "systemd": []}',
    ],
)
def test_scribe_rejects_corrupt_or_unsafe_ownership_manifest(
    manifest: str,
    scribe: ScribeService,
    output_dir: Path,
) -> None:
    ownership_path = output_dir / ".lychd-owned.json"
    ownership_path.write_text(manifest, encoding="utf-8")
    ownership_path.chmod(0o600)

    with pytest.raises(ScribeOwnershipError, match="Invalid Scribe ownership manifest"):
        scribe.generate_all([])


def test_scribe_rejects_authority_manifest_with_permissive_mode(
    scribe: ScribeService,
    output_dir: Path,
) -> None:
    scribe.generate_all([])
    (output_dir / ".lychd-owned.json").chmod(0o640)

    with pytest.raises(ScribeOwnershipError, match="must have mode 0600"):
        scribe.generate_all([])


def test_scribe_rejects_authority_manifest_owned_by_another_uid(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
) -> None:
    scribe.generate_all([])
    actual_uid = os.getuid()
    monkeypatch.setattr("lychd.system.services.scribe.authority.os.getuid", lambda: actual_uid + 1)

    with pytest.raises(ScribeOwnershipError, match="must be owned by uid"):
        scribe.generate_all([])


def test_scribe_rejects_symlink_ownership_manifest(
    scribe: ScribeService,
    output_dir: Path,
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text('{"version": 1, "quadlet": [], "systemd": []}', encoding="utf-8")
    (output_dir / ".lychd-owned.json").symlink_to(outside)

    with pytest.raises(ScribeOwnershipError, match="Unsafe Scribe ownership manifest path"):
        scribe.generate_all([])


def test_scribe_rejects_symlink_at_an_owned_unit_path(
    scribe: ScribeService,
    output_dir: Path,
    tmp_path: Path,
) -> None:
    scribe.generate_all([_container()])
    target = output_dir / "lychd-hermes.container"
    target.unlink()
    outside = tmp_path / "outside.container"
    outside.write_text("operator", encoding="utf-8")
    target.symlink_to(outside)

    with pytest.raises(ScribeOwnershipError, match="not a regular file"):
        scribe.generate_all([])

    assert target.is_symlink()
    assert outside.read_text(encoding="utf-8") == "operator"


def test_scribe_rolls_back_both_binding_sites_when_second_site_fails(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    target = QuadletTarget(name="logic", description="old target")
    pod = QuadletPod(pod_name="lychd")
    scribe.generate_all([pod, _container(description="old container"), target])
    old_quadlet = (output_dir / "lychd-hermes.container").read_bytes()
    old_target = (systemd_dir / "lychd-coven-logic.target").read_bytes()
    old_ownership = (output_dir / ".lychd-owned.json").read_bytes()
    preserved = output_dir / "lychd.pod"
    preserved_identity = (preserved.stat().st_ino, preserved.stat().st_mtime_ns)
    failed = False

    def fail_second_site_once(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal failed
        if destination_name == "lychd-coven-logic.target" and not failed:
            failed = True
            message = "simulated systemd-site failure"
            raise OSError(message)
        rename_exchange_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.services.scribe.storage.rename_exchange_at",
        fail_second_site_once,
    )

    with pytest.raises(ScribeTransactionError, match="simulated systemd-site failure") as failure:
        scribe.generate_all(
            [
                pod,
                _container(description="new container"),
                QuadletTarget(name="logic", description="new target"),
            ]
        )

    assert failure.value.state is ScribeTransactionState.ROLLED_BACK
    assert (output_dir / "lychd-hermes.container").read_bytes() == old_quadlet
    assert (systemd_dir / "lychd-coven-logic.target").read_bytes() == old_target
    assert (output_dir / ".lychd-owned.json").read_bytes() == old_ownership
    assert (preserved.stat().st_ino, preserved.stat().st_mtime_ns) == preserved_identity


def test_scribe_rollback_refuses_to_clobber_concurrent_edit(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """Rollback is a per-path CAS, not authority to overwrite a later writer."""
    target = QuadletTarget(name="logic", description="old target")
    scribe.generate_all([_container(description="old container"), target])
    quadlet = output_dir / "lychd-hermes.container"
    systemd_target = systemd_dir / "lychd-coven-logic.target"
    old_target = systemd_target.read_bytes()
    old_ownership = (output_dir / ".lychd-owned.json").read_bytes()
    failed = False

    def edit_first_path_then_fail(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal failed
        if destination_name == systemd_target.name and not failed:
            failed = True
            quadlet.write_text("concurrent operator edit", encoding="utf-8")
            message = "simulated failure after concurrent edit"
            raise OSError(message)
        rename_exchange_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.services.scribe.storage.rename_exchange_at",
        edit_first_path_then_fail,
    )

    with pytest.raises(
        ScribeTransactionError,
        match="rollback failed",
    ) as failure:
        scribe.generate_all(
            [
                _container(description="new container"),
                QuadletTarget(name="logic", description="new target"),
            ]
        )

    assert failure.value.state is ScribeTransactionState.INDETERMINATE
    assert quadlet.read_text(encoding="utf-8") == "concurrent operator edit"
    assert systemd_target.read_bytes() == old_target
    assert (output_dir / ".lychd-owned.json").read_bytes() == old_ownership


def test_scribe_rollback_restores_a_valid_authority_manifest_after_commit_failure(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    target = QuadletTarget(name="logic", description="old target")
    scribe.generate_all([_container(description="old container"), target])
    ownership_path = output_dir / ".lychd-owned.json"
    old_ownership = ownership_path.read_bytes()
    old_quadlet = (output_dir / "lychd-hermes.container").read_bytes()
    old_target = (systemd_dir / "lychd-coven-logic.target").read_bytes()
    transaction = getattr(scribe, "_transaction")  # noqa: B009 - inject private failure boundary
    real_fsync = getattr(transaction, "_fsync_directory")  # noqa: B009 - inject private failure boundary
    calls = 0

    def fail_post_manifest_fsync_once(directory: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            message = "simulated post-manifest fsync failure"
            raise OSError(message)
        real_fsync(directory)

    monkeypatch.setattr(transaction, "_fsync_directory", fail_post_manifest_fsync_once)

    with pytest.raises(ScribeTransactionError, match="post-manifest fsync failure") as failure:
        scribe.generate_all(
            [
                _container(description="new container"),
                QuadletTarget(name="logic", description="new target"),
                QuadletTarget(name="extra", description="new authority member"),
            ]
        )

    assert failure.value.state is ScribeTransactionState.ROLLED_BACK
    assert (output_dir / "lychd-hermes.container").read_bytes() == old_quadlet
    assert (systemd_dir / "lychd-coven-logic.target").read_bytes() == old_target
    assert not (systemd_dir / "lychd-coven-extra.target").exists()
    assert ownership_path.read_bytes() == old_ownership
    assert ownership_path.stat().st_uid == os.getuid()
    assert ownership_path.stat().st_mode & 0o777 == 0o600


def test_write_plain_unit_is_owned_and_atomic(
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    path = scribe.write_plain_unit("lychd-reactor.path", "[Path]\nPathChanged=/run/lychd\n")
    rewritten = scribe.write_plain_unit("lychd-reactor.path", "[Path]\nPathChanged=/run/lychd/new\n")

    assert path == rewritten == systemd_dir / "lychd-reactor.path"
    assert "new" in path.read_text(encoding="utf-8")
    assert _ownership(output_dir)["systemd"] == ["lychd-reactor.path"]


def test_generated_and_plain_unit_ownership_are_reconciled_independently(
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    scribe.generate_all([QuadletTarget(name="logic", description="first")])
    scribe.write_plain_unit("lychd-reactor.path", "[Path]\nPathChanged=/run/lychd\n")

    scribe.generate_all([QuadletTarget(name="vision", description="second")])

    assert not (systemd_dir / "lychd-coven-logic.target").exists()
    assert (systemd_dir / "lychd-coven-vision.target").exists()
    assert (systemd_dir / "lychd-reactor.path").exists()
    assert _ownership(output_dir)["systemd"] == [
        "lychd-coven-vision.target",
        "lychd-reactor.path",
    ]


def test_reconcile_all_removes_stale_owned_plain_units_and_preserves_unowned(
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    scribe.reconcile_all(
        [_container(), QuadletTarget(name="logic", description="first")],
        plain_units={
            "lychd-old.service": "old service",
            "lychd-reactor.path": "old path",
        },
    )
    unowned = systemd_dir / "lychd-operator.service"
    unowned.write_text("operator", encoding="utf-8")

    scribe.reconcile_all(
        [QuadletTarget(name="vision", description="second")],
        plain_units={"lychd-reactor.path": "new path"},
    )

    assert not (output_dir / "lychd-hermes.container").exists()
    assert not (systemd_dir / "lychd-coven-logic.target").exists()
    assert not (systemd_dir / "lychd-old.service").exists()
    assert (systemd_dir / "lychd-coven-vision.target").exists()
    assert (systemd_dir / "lychd-reactor.path").read_text(encoding="utf-8") == "new path"
    assert unowned.read_text(encoding="utf-8") == "operator"
    assert _ownership(output_dir) == {
        "quadlet": [],
        "systemd": ["lychd-coven-vision.target", "lychd-reactor.path"],
        "version": 1,
    }


def test_reconcile_all_rolls_back_generated_and_plain_units_together(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    scribe.reconcile_all(
        [_container(description="old"), QuadletTarget(name="logic", description="old")],
        plain_units={"lychd-reactor.service": "old reactor"},
    )
    tracked_paths = (
        output_dir / "lychd-hermes.container",
        systemd_dir / "lychd-coven-logic.target",
        systemd_dir / "lychd-reactor.service",
        output_dir / ".lychd-owned.json",
    )
    old_state = {path: path.read_bytes() for path in tracked_paths}
    failed = False

    def fail_plain_unit_once(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal failed
        if destination_name == "lychd-reactor.service" and not failed:
            failed = True
            message = "simulated plain-unit failure"
            raise OSError(message)
        rename_exchange_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.services.scribe.storage.rename_exchange_at",
        fail_plain_unit_once,
    )

    with pytest.raises(ScribeTransactionError, match="plain-unit failure") as failure:
        scribe.reconcile_all(
            [_container(description="new"), QuadletTarget(name="vision", description="new")],
            plain_units={"lychd-reactor.service": "new reactor"},
        )

    assert failure.value.state is ScribeTransactionState.ROLLED_BACK
    for path, content in old_state.items():
        assert path.read_bytes() == content
    assert not (systemd_dir / "lychd-coven-vision.target").exists()


def test_write_plain_unit_rejects_path_traversal(
    scribe: ScribeService,
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside.service"

    with pytest.raises(ValueError, match="Unsafe systemd ownership entry"):
        scribe.write_plain_unit("../outside.service", "malicious")

    assert not outside.exists()


def test_write_plain_unit_rejects_unowned_same_name(
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    unit = systemd_dir / "lychd-reactor.service"
    unit.write_text("operator-owned", encoding="utf-8")

    with pytest.raises(ScribeConflictError, match="unowned"):
        scribe.write_plain_unit("lychd-reactor.service", "LychD")

    assert unit.read_text(encoding="utf-8") == "operator-owned"
    assert not (output_dir / ".lychd-owned.json").exists()


def test_write_user_unit_uses_the_owned_plain_unit_path(
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    service = SystemdService(exec_start="/opt/lychd/bin/lychd serve")

    path = scribe.write_user_unit(service)

    assert path == systemd_dir / "lychd-vessel.service"
    assert "ExecStart=/opt/lychd/bin/lychd serve" in path.read_text(encoding="utf-8")
    assert _ownership(output_dir)["systemd"] == ["lychd-vessel.service"]


def test_clear_owned_bindings_rejects_generation_drift(
    scribe: ScribeService,
    output_dir: Path,
) -> None:
    """Destroy cannot clear sources that changed after its ownership snapshot."""
    scribe.reconcile_all([_container(description="old")], plain_units={})
    snapshot = scribe.inspect_owned_bindings()
    scribe.reconcile_all([_container(description="new")], plain_units={})

    with pytest.raises(ScribeOwnershipError, match="changed after lifecycle planning"):
        scribe.clear_owned_bindings(expected_generation=snapshot.generation)

    assert "Description=new" in (output_dir / "lychd-hermes.container").read_text(encoding="utf-8")


def test_clear_owned_bindings_never_recreates_a_missing_systemd_site(
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """Dissolution removes sources but retains exact authority through reload."""
    scribe.reconcile_all([_container()], plain_units={})
    snapshot = scribe.inspect_owned_bindings()
    systemd_dir.rmdir()

    scribe.clear_owned_bindings(expected_generation=snapshot.generation)

    assert not systemd_dir.exists()
    assert not (output_dir / "lychd-hermes.container").exists()
    assert _ownership(output_dir) == {
        "quadlet": ["lychd-hermes.container"],
        "systemd": [],
        "version": 1,
    }


def test_release_owned_binding_authority_requires_absent_sources(
    scribe: ScribeService,
    output_dir: Path,
) -> None:
    scribe.reconcile_all([_container()], plain_units={})
    snapshot = scribe.inspect_owned_bindings()

    with pytest.raises(ScribeOwnershipError, match="binding sources remain"):
        scribe.release_owned_binding_authority(
            expected_generation=snapshot.generation or "",
        )

    assert (output_dir / ".lychd-owned.json").exists()
    assert (output_dir / "lychd-hermes.container").exists()


def test_existing_replace_restores_generation_raced_inside_atomic_exchange(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
) -> None:
    """A writer in the final exchange gap keeps its bytes and authority generation."""
    scribe.reconcile_all([_container(description="old")], plain_units={})
    target = output_dir / "lychd-hermes.container"
    authority = output_dir / ".lychd-owned.json"
    old_authority = authority.read_bytes()
    raced = False

    def race_exchange(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal raced
        if destination_name == target.name and not raced:
            raced = True
            target.write_text("concurrent exchange writer\n", encoding="utf-8")
        rename_exchange_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.services.scribe.storage.rename_exchange_at",
        race_exchange,
    )

    with pytest.raises(ScribeGenerationError, match="restored the concurrent generation"):
        scribe.reconcile_all([_container(description="new")], plain_units={})

    assert target.read_text(encoding="utf-8") == "concurrent exchange writer\n"
    assert authority.read_bytes() == old_authority


def test_existing_removal_restores_generation_raced_inside_quarantine_move(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
) -> None:
    """A writer in the final removal gap is moved back rather than deleted."""
    scribe.reconcile_all([_container(description="old")], plain_units={})
    target = output_dir / "lychd-hermes.container"
    authority = output_dir / ".lychd-owned.json"
    old_authority = authority.read_bytes()
    raced = False

    def race_removal(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal raced
        if source_name == target.name and not raced:
            raced = True
            target.write_text("concurrent removal writer\n", encoding="utf-8")
        rename_noreplace_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.services.scribe.storage.rename_noreplace_at",
        race_removal,
    )

    with pytest.raises(ScribeGenerationError, match="restored the concurrent generation"):
        scribe.reconcile_all([], plain_units={})

    assert target.read_text(encoding="utf-8") == "concurrent removal writer\n"
    assert authority.read_bytes() == old_authority


def test_rollback_exchange_restores_writer_raced_after_rollback_precheck(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """Rollback atomically reverses its own exchange when a writer wins its last gap."""
    scribe.reconcile_all(
        [
            _container(description="old"),
            QuadletTarget(name="logic", description="old"),
        ],
        plain_units={},
    )
    quadlet = output_dir / "lychd-hermes.container"
    systemd_target = systemd_dir / "lychd-coven-logic.target"
    quadlet_exchanges = 0

    def race_rollback_then_fail(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal quadlet_exchanges
        if destination_name == quadlet.name:
            quadlet_exchanges += 1
            if quadlet_exchanges == 2:
                quadlet.write_text("concurrent rollback writer\n", encoding="utf-8")
        if destination_name == systemd_target.name:
            message = "force rollback after first site"
            raise OSError(message)
        rename_exchange_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    monkeypatch.setattr(
        "lychd.system.services.scribe.storage.rename_exchange_at",
        race_rollback_then_fail,
    )

    with pytest.raises(ScribeTransactionError, match="rollback failed") as failure:
        scribe.reconcile_all(
            [
                _container(description="new"),
                QuadletTarget(name="logic", description="new"),
            ],
            plain_units={},
        )

    assert failure.value.state is ScribeTransactionState.INDETERMINATE
    assert quadlet.read_text(encoding="utf-8") == "concurrent rollback writer\n"
    assert tuple(output_dir.glob(".lychd-transaction-*"))
    assert tuple(systemd_dir.glob(".lychd-transaction-*"))


def test_indeterminate_exchange_retains_quarantined_recovery_evidence(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
) -> None:
    """Unclassifiable post-exchange state leaves the old generation recoverable."""
    scribe.reconcile_all([_container(description="old")], plain_units={})
    target = output_dir / "lychd-hermes.container"
    sabotaged = False

    def make_exchange_indeterminate(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal sabotaged
        rename_exchange_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )
        if destination_name == target.name and not sabotaged:
            sabotaged = True
            target.write_text("unclassified live generation\n", encoding="utf-8")

    monkeypatch.setattr(
        "lychd.system.services.scribe.storage.rename_exchange_at",
        make_exchange_indeterminate,
    )

    with pytest.raises(ScribeTransactionError, match="Recovery evidence was retained") as failure:
        scribe.reconcile_all([_container(description="new")], plain_units={})

    assert failure.value.state is ScribeTransactionState.INDETERMINATE
    recovery_dirs = tuple(output_dir.glob(".lychd-transaction-*"))
    assert recovery_dirs
    assert any(
        entry.read_bytes().find(b"Description=old") >= 0
        for directory in recovery_dirs
        for entry in directory.iterdir()
        if entry.is_file()
    )


def test_post_exchange_observation_failure_retains_recovery_evidence(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
) -> None:
    """An observation exception after rename cannot trigger evidence cleanup."""
    scribe.reconcile_all([_container(description="old")], plain_units={})
    target = output_dir / "lychd-hermes.container"

    real_capture = storage_module.capture_pinned_path_state
    exchange_completed = False

    def exchange_then_mark(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        nonlocal exchange_completed
        rename_exchange_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )
        if destination_name == target.name:
            exchange_completed = True

    def fail_post_exchange_capture(path: PinnedPath) -> PathState | None:
        if exchange_completed and path.display == target:
            message = "simulated post-exchange observation failure"
            raise OSError(message)
        return real_capture(path)

    monkeypatch.setattr(storage_module, "rename_exchange_at", exchange_then_mark)
    monkeypatch.setattr(
        storage_module,
        "capture_pinned_path_state",
        fail_post_exchange_capture,
    )

    with pytest.raises(ScribeTransactionError, match="Recovery evidence was retained") as failure:
        scribe.reconcile_all([_container(description="new")], plain_units={})

    assert failure.value.state is ScribeTransactionState.INDETERMINATE
    recovery_dirs = tuple(output_dir.glob(".lychd-transaction-*"))
    assert recovery_dirs
    assert any(
        b"Description=old" in entry.read_bytes()
        for directory in recovery_dirs
        for entry in directory.iterdir()
        if entry.is_file()
    )


def test_transaction_cleanup_preserves_replacement_at_workspace_path(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
) -> None:
    """Cleanup follows its pinned inode and never recursively deletes a replacement."""
    real_cleanup = TransactionWorkspace.cleanup
    replacement_paths: list[Path] = []
    retained_paths: list[Path] = []
    intercepted = False

    def replace_workspace_before_cleanup(workspace: TransactionWorkspace) -> None:
        nonlocal intercepted
        if not intercepted:
            intercepted = True
            relocated = workspace.path.with_name(f"{workspace.path.name}-relocated")
            workspace.path.rename(relocated)
            retained_paths.append(relocated)
            workspace.path.mkdir()
            (workspace.path / "operator-marker").write_text("preserve me", encoding="utf-8")
            replacement_paths.append(workspace.path)
        real_cleanup(workspace)

    monkeypatch.setattr(TransactionWorkspace, "cleanup", replace_workspace_before_cleanup)

    with pytest.raises(ScribeTransactionError) as raised:
        scribe.reconcile_all([_container()], plain_units={})

    assert replacement_paths
    assert retained_paths
    assert raised.value.state is ScribeTransactionState.COMMITTED
    assert retained_paths[0] in raised.value.recovery_paths
    assert (replacement_paths[0] / "operator-marker").read_text(encoding="utf-8") == "preserve me"


def test_workspace_creation_failure_never_deletes_unattested_replacement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A child-open failure has no identity authority to clean its pathname."""
    parent = tmp_path / "binding-site"
    parent.mkdir()
    real_open = os.open
    replacement: Path | None = None

    def replace_before_child_open(
        path: str | bytes | Path,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal replacement
        if dir_fd is not None and replacement is None:
            original = parent / os.fsdecode(path)
            original.rename(original.with_name(f"{original.name}-unattested"))
            original.mkdir()
            (original / "operator-marker").write_text("preserve me", encoding="utf-8")
            replacement = original
            message = "simulated child descriptor failure"
            raise OSError(message)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(
        "lychd.system.services.scribe.workspace.os.open",
        replace_before_child_open,
    )

    with pytest.raises(WorkspaceSettlementError, match="retained exact recovery") as raised:
        TransactionWorkspace.create(parent)

    assert replacement is not None
    assert raised.value.outcome == "workspace_retained"
    assert raised.value.outcome_verified
    assert parent / replacement.name.removesuffix("-unattested") in raised.value.recovery_paths
    assert (replacement / "operator-marker").read_text(encoding="utf-8") == "preserve me"


def test_clear_does_not_expand_deletion_when_authority_changes_after_inspection(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
) -> None:
    """The facade's inspected generation remains the transaction's deletion bound."""
    scribe.reconcile_all([_container()], plain_units={})
    original = output_dir / "lychd-hermes.container"
    raced = output_dir / "lychd-raced.container"
    authority = output_dir / ".lychd-owned.json"
    authority_port = getattr(scribe, "_authority")  # noqa: B009 - inject authority race
    real_snapshot = authority_port.snapshot
    expanded = False

    def expand_authority_before_snapshot() -> tuple[bytes, OwnershipManifest]:
        nonlocal expanded
        if not expanded:
            expanded = True
            raced.write_text("operator generation\n", encoding="utf-8")
            authority.write_bytes(
                authority_port.encode(
                    OwnershipManifest(
                        version=1,
                        quadlet=("lychd-hermes.container", "lychd-raced.container"),
                    )
                )
            )
            authority.chmod(0o600)
        return real_snapshot()

    monkeypatch.setattr(
        authority_port,
        "snapshot",
        expand_authority_before_snapshot,
    )

    with pytest.raises(ScribeGenerationError, match="changed after planning"):
        scribe.clear_owned_bindings()

    assert original.exists()
    assert raced.read_text(encoding="utf-8") == "operator generation\n"


def test_release_does_not_delete_authority_expanded_after_inspection(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
) -> None:
    """Receipt deletion is guarded inside the transaction by the inspected generation."""
    scribe.reconcile_all([], plain_units={})
    snapshot = scribe.inspect_owned_bindings()
    raced = output_dir / "lychd-raced.container"
    authority = output_dir / ".lychd-owned.json"
    authority_port = getattr(scribe, "_authority")  # noqa: B009 - inject authority race
    real_snapshot = authority_port.snapshot
    expanded = False

    def expand_authority_before_snapshot() -> tuple[bytes, OwnershipManifest]:
        nonlocal expanded
        if not expanded:
            expanded = True
            raced.write_text("operator generation\n", encoding="utf-8")
            authority.write_bytes(
                authority_port.encode(
                    OwnershipManifest(
                        version=1,
                        quadlet=("lychd-raced.container",),
                    )
                )
            )
            authority.chmod(0o600)
        return real_snapshot()

    monkeypatch.setattr(
        authority_port,
        "snapshot",
        expand_authority_before_snapshot,
    )

    with pytest.raises(ScribeGenerationError, match="changed after planning"):
        scribe.release_owned_binding_authority(
            expected_generation=snapshot.generation or "",
        )

    assert authority.exists()
    assert raced.read_text(encoding="utf-8") == "operator generation\n"


def test_release_removes_empty_authority_inside_binding_transaction(
    scribe: ScribeService,
    output_dir: Path,
) -> None:
    """The empty receipt is a quarantined transaction mutation, not facade cleanup."""
    scribe.reconcile_all([], plain_units={})
    snapshot = scribe.inspect_owned_bindings()

    scribe.release_owned_binding_authority(
        expected_generation=snapshot.generation or "",
    )

    assert not (output_dir / ".lychd-owned.json").exists()


def test_stale_planner_write_set_cannot_reacquire_relinquished_authority(
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """Every write set CASes the full receipt generation read by its planner."""
    planner = getattr(scribe, "_planner")  # noqa: B009 - verify internal CAS boundary
    transaction = getattr(scribe, "_transaction")  # noqa: B009 - verify internal CAS boundary
    stale = planner.plain_unit(
        "lychd-stale.service",
        {"lychd-stale.service": b"stale\n"},
    )
    scribe.write_plain_unit("lychd-current.service", "current\n")

    with pytest.raises(ScribeGenerationError, match="authority changed after planning"):
        transaction.commit(stale)

    assert (systemd_dir / "lychd-current.service").read_text(encoding="utf-8") == "current\n"
    assert not (systemd_dir / "lychd-stale.service").exists()
    assert _ownership(output_dir)["systemd"] == ["lychd-current.service"]


def test_clear_accepts_recorded_missing_systemd_source_without_recreating_site(
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """The full receipt guard includes missing sources omitted from the mutation plan."""
    target = systemd_dir / "lychd-coven-logic.target"
    scribe.reconcile_all(
        [QuadletTarget(name="logic", description="logic")],
        plain_units={},
    )
    target.unlink()
    systemd_dir.rmdir()
    snapshot = scribe.inspect_owned_bindings()

    scribe.clear_owned_bindings(expected_generation=snapshot.generation)

    assert not systemd_dir.exists()
    assert _ownership(output_dir)["systemd"] == ["lychd-coven-logic.target"]


def test_release_accepts_recorded_missing_systemd_source_without_recreating_site(
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """Authority retirement compares the same full missing-source observation."""
    target = systemd_dir / "lychd-coven-logic.target"
    scribe.reconcile_all(
        [QuadletTarget(name="logic", description="logic")],
        plain_units={},
    )
    target.unlink()
    systemd_dir.rmdir()
    snapshot = scribe.inspect_owned_bindings()

    scribe.release_owned_binding_authority(
        expected_generation=snapshot.generation or "",
    )

    assert not systemd_dir.exists()
    assert not (output_dir / ".lychd-owned.json").exists()


def test_release_restores_authority_when_missing_systemd_source_reappears(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """A source created in the final release gap remains owned and untouched."""
    target = systemd_dir / "lychd-coven-logic.target"
    scribe.reconcile_all(
        [QuadletTarget(name="logic", description="logic")],
        plain_units={},
    )
    target.unlink()
    systemd_dir.rmdir()
    snapshot = scribe.inspect_owned_bindings()
    transaction = getattr(scribe, "_transaction")  # noqa: B009 - exact release race
    authority = getattr(transaction, "_authority")  # noqa: B009 - exact release race
    real_observed_generation = authority.observed_generation

    def observe_then_recreate_source(*args: object, **kwargs: object) -> str:
        generation = real_observed_generation(*args, **kwargs)
        systemd_dir.mkdir()
        target.write_text("concurrent source\n", encoding="utf-8")
        return generation

    monkeypatch.setattr(
        authority,
        "observed_generation",
        observe_then_recreate_source,
    )

    with pytest.raises(
        ScribeTransactionError,
        match="exact mutations were rolled back",
    ) as failure:
        scribe.release_owned_binding_authority(
            expected_generation=snapshot.generation or "",
        )

    assert failure.value.state is ScribeTransactionState.ROLLED_BACK
    assert target.read_text(encoding="utf-8") == "concurrent source\n"
    assert _ownership(output_dir)["systemd"] == ["lychd-coven-logic.target"]


def test_staged_bytes_changed_after_prepare_are_never_installed(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    systemd_dir: Path,
) -> None:
    """Commit re-attests staged identity and content through the pinned workspace."""
    transaction = getattr(scribe, "_transaction")  # noqa: B009 - adversarial boundary
    storage = getattr(transaction, "_storage")  # noqa: B009 - adversarial boundary
    real_replace = storage.replace
    target = systemd_dir / "lychd-reactor.service"
    sabotaged = False

    def replace_changed_staging(
        staged: AttestedPath,
        pinned_target: PinnedPath,
        **kwargs: object,
    ) -> AtomicOutcome:
        nonlocal sabotaged
        if pinned_target.display == target and not sabotaged:
            sabotaged = True
            staged_path = staged.path
            descriptor = os.open(
                staged_path.name,
                os.O_WRONLY | os.O_TRUNC,
                dir_fd=staged_path.directory_fd,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(b"unapproved\n")
                stream.flush()
                os.fsync(stream.fileno())
        return real_replace(staged, pinned_target, **kwargs)

    monkeypatch.setattr(storage, "replace", replace_changed_staging)

    with pytest.raises(ScribeGenerationError, match="replacement changed"):
        scribe.write_plain_unit("lychd-reactor.service", "approved\n")

    assert not target.exists()


def test_planner_generation_never_follows_source_swapped_to_symlink(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    systemd_dir: Path,
    tmp_path: Path,
) -> None:
    """Receipt generation fails closed when a source changes during no-follow open."""
    target = scribe.write_plain_unit("lychd-reactor.service", "owned\n")
    outside = tmp_path / "outside.service"
    outside.write_text("operator\n", encoding="utf-8")
    real_open = storage_module.os.open
    swapped = False

    def swap_before_source_open(
        path: str | bytes | Path,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if dir_fd is not None and os.fsdecode(path) == target.name and not swapped:
            swapped = True
            target.unlink()
            target.symlink_to(outside)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(storage_module.os, "open", swap_before_source_open)

    with pytest.raises(ScribeOwnershipError, match="safely observe"):
        scribe.plan_reconcile_all([], plain_units={})

    assert target.is_symlink()
    assert outside.read_text(encoding="utf-8") == "operator\n"
    assert systemd_dir.exists()


def test_planner_generation_never_blocks_on_source_swapped_to_fifo(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
) -> None:
    """A regular-to-FIFO race is opened nonblocking and fails observation."""
    target = scribe.write_plain_unit("lychd-reactor.service", "owned\n")
    real_open = storage_module.os.open
    swapped = False

    def swap_before_source_open(
        path: str | bytes | Path,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if dir_fd is not None and os.fsdecode(path) == target.name and not swapped:
            swapped = True
            assert flags & os.O_NONBLOCK
            target.unlink()
            os.mkfifo(target)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(storage_module.os, "open", swap_before_source_open)

    with pytest.raises(ScribeOwnershipError, match="safely observe"):
        scribe.plan_reconcile_all([], plain_units={})

    assert target.is_fifo()


def test_workspace_namespace_substitution_cannot_install_foreign_staging(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    systemd_dir: Path,
) -> None:
    """A replacement at the public workspace name is never a rename operand."""
    transaction = getattr(scribe, "_transaction")  # noqa: B009 - adversarial boundary
    storage = getattr(transaction, "_storage")  # noqa: B009 - adversarial boundary
    real_replace = storage.replace
    target = systemd_dir / "lychd-reactor.service"
    replacement_workspace: Path | None = None

    def substitute_workspace(
        staged: AttestedPath,
        pinned_target: PinnedPath,
        **kwargs: object,
    ) -> AtomicOutcome:
        nonlocal replacement_workspace
        if pinned_target.display == target and replacement_workspace is None:
            staged_path = staged.path
            public_workspace = staged_path.display.parent
            relocated = public_workspace.with_name(f"{public_workspace.name}-relocated")
            public_workspace.rename(relocated)
            public_workspace.mkdir()
            (public_workspace / staged_path.name).write_bytes(b"foreign staged bytes\n")
            replacement_workspace = public_workspace
        return real_replace(staged, pinned_target, **kwargs)

    monkeypatch.setattr(storage, "replace", substitute_workspace)

    with pytest.raises(ScribeTransactionError, match="directory identity changed") as failure:
        scribe.write_plain_unit("lychd-reactor.service", "approved\n")

    assert failure.value.state is ScribeTransactionState.INDETERMINATE
    assert not target.exists()
    assert replacement_workspace is not None
    assert any(entry.read_bytes() == b"foreign staged bytes\n" for entry in replacement_workspace.iterdir())


def test_binding_site_namespace_substitution_never_mutates_replacement_site(
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    systemd_dir: Path,
) -> None:
    """Live transitions stay bound to the exact site descriptor opened at prepare."""
    transaction = getattr(scribe, "_transaction")  # noqa: B009 - adversarial boundary
    storage = getattr(transaction, "_storage")  # noqa: B009 - adversarial boundary
    real_replace = storage.replace
    target = systemd_dir / "lychd-reactor.service"
    relocated_site = systemd_dir.with_name("systemd-relocated")
    substituted = False

    def substitute_site(
        staged: AttestedPath,
        pinned_target: PinnedPath,
        **kwargs: object,
    ) -> AtomicOutcome:
        nonlocal substituted
        if pinned_target.display == target and not substituted:
            substituted = True
            systemd_dir.rename(relocated_site)
            systemd_dir.mkdir()
            target.write_text("operator replacement\n", encoding="utf-8")
        return real_replace(staged, pinned_target, **kwargs)

    monkeypatch.setattr(storage, "replace", substitute_site)

    with pytest.raises(ScribeTransactionError, match="directory identity changed") as failure:
        scribe.write_plain_unit("lychd-reactor.service", "approved\n")

    assert failure.value.state is ScribeTransactionState.INDETERMINATE
    assert target.read_text(encoding="utf-8") == "operator replacement\n"
    assert not (relocated_site / target.name).exists()


def test_expected_binding_site_identity_closes_foundation_to_commit_gap(
    templates_dir: Path,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """Scribe rejects a site replaced after foundation approval but before prepare."""
    output_metadata = output_dir.stat()
    systemd_metadata = systemd_dir.stat()
    expected_sites = AttestedBindingSites(
        quadlet=AttestedBindingSite(
            path=output_dir,
            device=output_metadata.st_dev,
            inode=output_metadata.st_ino,
        ),
        systemd_user=AttestedBindingSite(
            path=systemd_dir,
            device=systemd_metadata.st_dev,
            inode=systemd_metadata.st_ino,
        ),
    )
    scribe = ScribeService(
        templates_dir=templates_dir,
        expected_sites=expected_sites,
    )
    relocated = systemd_dir.with_name("approved-systemd-site")
    systemd_dir.rename(relocated)
    systemd_dir.mkdir()
    marker = systemd_dir / "operator-marker"
    marker.write_text("preserve\n", encoding="utf-8")

    with pytest.raises(ScribeGenerationError, match="foundation approval"):
        scribe.write_plain_unit("lychd-reactor.service", "approved\n")

    assert marker.read_text(encoding="utf-8") == "preserve\n"
    assert not (systemd_dir / "lychd-reactor.service").exists()
    assert not tuple(output_dir.glob(".lychd-transaction-*"))
    assert not tuple(systemd_dir.glob(".lychd-transaction-*"))


def test_expected_binding_site_identity_is_checked_before_noop_return(
    templates_dir: Path,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """A content-identical replacement site cannot pass as an approved no-op."""
    output_metadata = output_dir.stat()
    systemd_metadata = systemd_dir.stat()
    scribe = ScribeService(
        templates_dir=templates_dir,
        expected_sites=AttestedBindingSites(
            quadlet=AttestedBindingSite(
                path=output_dir,
                device=output_metadata.st_dev,
                inode=output_metadata.st_ino,
            ),
            systemd_user=AttestedBindingSite(
                path=systemd_dir,
                device=systemd_metadata.st_dev,
                inode=systemd_metadata.st_ino,
            ),
        ),
    )
    target = scribe.write_plain_unit("lychd-reactor.service", "approved\n")
    relocated = systemd_dir.with_name("approved-systemd-noop-site")
    systemd_dir.rename(relocated)
    systemd_dir.mkdir()
    target.write_text("approved\n", encoding="utf-8")

    with pytest.raises(ScribeGenerationError, match="foundation approval"):
        scribe.write_plain_unit("lychd-reactor.service", "approved\n")

    assert target.read_text(encoding="utf-8") == "approved\n"
    assert (relocated / target.name).read_text(encoding="utf-8") == "approved\n"
    assert not tuple(output_dir.glob(".lychd-transaction-*"))
    assert not tuple(systemd_dir.glob(".lychd-transaction-*"))


def test_final_expected_site_drift_after_mutation_is_indeterminate(
    monkeypatch: pytest.MonkeyPatch,
    templates_dir: Path,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """A post-mutation namespace substitution can never claim clean rollback."""
    output_metadata = output_dir.stat()
    systemd_metadata = systemd_dir.stat()
    scribe = ScribeService(
        templates_dir=templates_dir,
        expected_sites=AttestedBindingSites(
            quadlet=AttestedBindingSite(
                path=output_dir,
                device=output_metadata.st_dev,
                inode=output_metadata.st_ino,
            ),
            systemd_user=AttestedBindingSite(
                path=systemd_dir,
                device=systemd_metadata.st_dev,
                inode=systemd_metadata.st_ino,
            ),
        ),
    )
    transaction = getattr(scribe, "_transaction")  # noqa: B009 - exact final-check race
    real_require = getattr(transaction, "_require_expected_sites_now")  # noqa: B009
    relocated = systemd_dir.with_name("systemd-final-check-relocated")
    marker = systemd_dir / "operator-marker"
    checks = 0

    def substitute_before_final_check(*, indeterminate: bool = False) -> None:
        nonlocal checks
        checks += 1
        if checks == 2:
            systemd_dir.rename(relocated)
            systemd_dir.mkdir()
            marker.write_text("preserve\n", encoding="utf-8")
        real_require(indeterminate=indeterminate)

    monkeypatch.setattr(
        transaction,
        "_require_expected_sites_now",
        substitute_before_final_check,
    )

    with pytest.raises(
        ScribeTransactionError,
        match="Recovery evidence was retained",
    ) as failure:
        scribe.write_plain_unit("lychd-reactor.service", "approved\n")

    assert failure.value.state is ScribeTransactionState.INDETERMINATE
    assert marker.read_text(encoding="utf-8") == "preserve\n"
    assert not (relocated / "lychd-reactor.service").exists()
    assert tuple(relocated.glob(".lychd-transaction-*"))


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, SystemExit])
def test_rollback_interruption_retains_every_recovery_workspace(
    interruption: type[BaseException],
    monkeypatch: pytest.MonkeyPatch,
    scribe: ScribeService,
    output_dir: Path,
    systemd_dir: Path,
) -> None:
    """Rollback interruption is typed indeterminate and cannot trigger cleanup."""
    scribe.reconcile_all(
        [
            _container(description="old"),
            QuadletTarget(name="logic", description="old"),
        ],
        plain_units={},
    )
    transaction = getattr(scribe, "_transaction")  # noqa: B009 - adversarial boundary
    storage = getattr(transaction, "_storage")  # noqa: B009 - adversarial boundary
    systemd_target = systemd_dir / "lychd-coven-logic.target"

    def fail_second_site(
        source_name: str,
        destination_name: str,
        *,
        source_dir_fd: int,
        destination_dir_fd: int,
    ) -> None:
        if destination_name == systemd_target.name:
            message = "force rollback"
            raise OSError(message)
        rename_exchange_at(
            source_name,
            destination_name,
            source_dir_fd=source_dir_fd,
            destination_dir_fd=destination_dir_fd,
        )

    def interrupt_rollback(_mutation: object) -> None:
        raise interruption()

    monkeypatch.setattr(storage_module, "rename_exchange_at", fail_second_site)
    monkeypatch.setattr(storage, "restore", interrupt_rollback)

    with pytest.raises(ScribeTransactionError, match="rollback failed or was interrupted") as failure:
        scribe.reconcile_all(
            [
                _container(description="new"),
                QuadletTarget(name="logic", description="new"),
            ],
            plain_units={},
        )

    assert failure.value.state is ScribeTransactionState.INDETERMINATE
    assert isinstance(failure.value.__cause__, interruption)
    assert isinstance(failure.value.rollback_error, interruption)
    assert isinstance(failure.value.forward_error, OSError)
    output_recovery = tuple(output_dir.glob(".lychd-transaction-*"))
    systemd_recovery = tuple(systemd_dir.glob(".lychd-transaction-*"))
    assert output_recovery
    assert systemd_recovery
    assert any(
        b"Description=old" in entry.read_bytes()
        for directory in output_recovery
        for entry in directory.iterdir()
        if entry.is_file()
    )


def _cleanup_transaction(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    first_cleanup: BaseException,
    fail_forward: bool,
) -> tuple[BindingTransaction, MagicMock, MagicMock]:
    authority = MagicMock()
    authority.observed_generation.return_value = "committed-generation"
    transaction = BindingTransaction(authority)
    first = MagicMock(path=tmp_path / "first-workspace")
    first.cleanup.side_effect = first_cleanup
    second = MagicMock(path=tmp_path / "second-workspace")
    second.cleanup.return_value = None
    prepared = SimpleNamespace(
        workspaces={tmp_path / "first": first, tmp_path / "second": second},
        sites={},
        authority=None,
    )

    def prepared_commit(*_args: object, **_kwargs: object) -> object:
        return prepared

    def mutates(*_args: object, **_kwargs: object) -> bool:
        return True

    def no_op(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(transaction, "_prepare_commit", prepared_commit)
    monkeypatch.setattr(transaction, "_mutates", mutates)
    monkeypatch.setattr(transaction, "_require_generation", no_op)
    monkeypatch.setattr(transaction, "_require_expected_sites_now", no_op)
    monkeypatch.setattr(transaction, "_require_namespaces", no_op)
    monkeypatch.setattr(transaction, "_apply_authority", no_op)
    monkeypatch.setattr(transaction, "_rollback", no_op)

    if fail_forward:

        def fail_after_proven_mutation(
            _plans: object,
            *,
            prepared: object,
            progress: _MutableProgress,
        ) -> None:
            del prepared
            progress.mutations.append(cast("AtomicMutation", object()))
            message = "forward failure"
            raise OSError(message)

        monkeypatch.setattr(transaction, "_apply_sites", fail_after_proven_mutation)
    else:
        monkeypatch.setattr(transaction, "_apply_sites", no_op)
    return transaction, first, second


def _empty_write_set() -> BindingWriteSet:
    ownership = OwnershipManifest(version=1)
    return BindingWriteSet(
        plans=(),
        ownership=ownership,
        base=BindingBase(
            authority=b"",
            ownership=ownership,
            sources=(),
            generation="base-generation",
        ),
    )


def test_cleanup_terminal_after_commit_keeps_native_signal_and_committed_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = KeyboardInterrupt()
    transaction, first, second = _cleanup_transaction(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        first_cleanup=terminal,
        fail_forward=False,
    )

    with pytest.raises(KeyboardInterrupt) as raised:
        transaction.commit(_empty_write_set())

    assert raised.value is terminal
    outcome = raised.value.__cause__
    assert isinstance(outcome, ScribeTransactionError)
    assert outcome.state is ScribeTransactionState.COMMITTED
    assert outcome.generation == "committed-generation"
    assert terminal in outcome.cleanup_errors
    first.cleanup.assert_called_once()
    second.cleanup.assert_called_once()


def test_ordinary_cleanup_failure_after_commit_surfaces_committed_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-terminal cleanup failure cannot be logged and dropped."""
    cleanup_failure = OSError("workspace cleanup failed")
    transaction, first, second = _cleanup_transaction(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        first_cleanup=cleanup_failure,
        fail_forward=False,
    )

    with pytest.raises(ScribeTransactionError) as raised:
        transaction.commit(_empty_write_set())

    assert raised.value.state is ScribeTransactionState.COMMITTED
    assert raised.value.generation == "committed-generation"
    assert cleanup_failure in raised.value.cleanup_errors
    assert raised.value.__cause__ is cleanup_failure
    first.cleanup.assert_called_once()
    second.cleanup.assert_called_once()


def test_cleanup_terminal_after_exact_rollback_settles_peers_and_attaches_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = SystemExit(71)
    transaction, first, second = _cleanup_transaction(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        first_cleanup=terminal,
        fail_forward=True,
    )

    with pytest.raises(SystemExit) as raised:
        transaction.commit(_empty_write_set())

    assert raised.value is terminal
    outcome = raised.value.__cause__
    assert isinstance(outcome, ScribeTransactionError)
    assert outcome.state is ScribeTransactionState.ROLLED_BACK
    assert isinstance(outcome.forward_error, OSError)
    assert terminal in outcome.cleanup_errors
    first.cleanup.assert_called_once()
    second.cleanup.assert_called_once()


@pytest.mark.parametrize("terminal", [KeyboardInterrupt(), SystemExit(147)])
def test_nested_terminal_resurfaces_after_exact_rollback_and_workspace_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    terminal: BaseException,
) -> None:
    """A nested terminal remains native after proven rollback and clean close."""
    transaction, first, second = _cleanup_transaction(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        first_cleanup=OSError("unused cleanup failure"),
        fail_forward=False,
    )
    indeterminate_path = tmp_path / "indeterminate-target"

    def fail_after_proven_mutation(
        _plans: object,
        *,
        prepared: object,
        progress: _MutableProgress,
    ) -> None:
        del prepared
        progress.mutations.append(cast("AtomicMutation", object()))
        message = "post-mutation observation interrupted"
        raise PathStateIndeterminateError(
            message,
            paths=frozenset({indeterminate_path}),
            cause=terminal,
        ) from terminal

    monkeypatch.setattr(
        transaction,
        "_apply_sites",
        fail_after_proven_mutation,
    )

    with pytest.raises(type(terminal)) as raised:
        transaction.commit(_empty_write_set())

    assert raised.value is terminal
    outcome = raised.value.__cause__
    assert isinstance(outcome, ScribeTransactionError)
    assert outcome.state is ScribeTransactionState.INDETERMINATE
    assert isinstance(outcome.forward_error, PathStateIndeterminateError)
    assert outcome.forward_error.cause is terminal
    assert outcome.rollback_error is None
    first.close.assert_called_once()
    second.close.assert_called_once()
    first.cleanup.assert_not_called()
    second.cleanup.assert_not_called()


@pytest.mark.parametrize(
    "recovery_failure",
    [OSError("recovery path failed"), KeyboardInterrupt(), SystemExit(153)],
)
def test_recovery_path_observation_is_total_transaction_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    recovery_failure: BaseException,
) -> None:
    """Recovery rendering cannot replace the classified forward failure."""
    transaction, first, second = _cleanup_transaction(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        first_cleanup=OSError("unused cleanup failure"),
        fail_forward=False,
    )
    first.recovery_path.side_effect = recovery_failure
    second.recovery_path.return_value = second.path
    indeterminate_path = tmp_path / "indeterminate-target"

    def fail_after_proven_mutation(
        _plans: object,
        *,
        prepared: object,
        progress: _MutableProgress,
    ) -> None:
        del prepared
        progress.mutations.append(cast("AtomicMutation", object()))
        message = "post-mutation state is indeterminate"
        raise PathStateIndeterminateError(
            message,
            paths=frozenset({indeterminate_path}),
        )

    monkeypatch.setattr(
        transaction,
        "_apply_sites",
        fail_after_proven_mutation,
    )

    expected = ScribeTransactionError if isinstance(recovery_failure, Exception) else type(recovery_failure)
    with pytest.raises(expected) as raised:
        transaction.commit(_empty_write_set())

    outcome = raised.value if isinstance(raised.value, ScribeTransactionError) else raised.value.__cause__
    assert isinstance(outcome, ScribeTransactionError)
    assert outcome.state is ScribeTransactionState.INDETERMINATE
    assert isinstance(outcome.forward_error, PathStateIndeterminateError)
    assert recovery_failure in tuple(iter_exception_graph(outcome))
    assert first.path in outcome.recovery_paths
    assert second.path in outcome.recovery_paths
    first.recovery_path.assert_called_once()
    second.recovery_path.assert_called_once()
    first.close.assert_called_once()
    second.close.assert_called_once()


@pytest.mark.parametrize("rollback_terminal", [KeyboardInterrupt(), SystemExit(155)])
def test_ordinary_close_error_does_not_promote_rollback_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rollback_terminal: BaseException,
) -> None:
    """An earlier rollback terminal stays typed when final close is ordinary."""
    transaction, first, second = _cleanup_transaction(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        first_cleanup=OSError("unused cleanup failure"),
        fail_forward=True,
    )
    close_error = OSError("workspace close failed")
    rollback = MagicMock(side_effect=rollback_terminal)
    monkeypatch.setattr(transaction, "_rollback", rollback)
    first.close.side_effect = close_error

    with pytest.raises(ScribeTransactionError) as raised:
        transaction.commit(_empty_write_set())

    assert raised.value.state is ScribeTransactionState.INDETERMINATE
    assert raised.value.rollback_error is rollback_terminal
    assert close_error in raised.value.cleanup_errors
    assert find_terminal_interruption(raised.value) is rollback_terminal
    rollback.assert_called_once()
    first.close.assert_called_once()
    second.close.assert_called_once()


def test_new_cleanup_terminal_wins_after_interrupted_rollback_settlement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A genuinely new close terminal surfaces after every retained workspace."""
    rollback_terminal = KeyboardInterrupt()
    cleanup_terminal = SystemExit(157)
    transaction, first, second = _cleanup_transaction(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        first_cleanup=OSError("unused cleanup failure"),
        fail_forward=True,
    )
    monkeypatch.setattr(
        transaction,
        "_rollback",
        MagicMock(side_effect=rollback_terminal),
    )
    first.close.side_effect = cleanup_terminal

    with pytest.raises(SystemExit) as raised:
        transaction.commit(_empty_write_set())

    assert raised.value is cleanup_terminal
    outcome = raised.value.__cause__
    assert isinstance(outcome, ScribeTransactionError)
    assert outcome.rollback_error is rollback_terminal
    assert cleanup_terminal in outcome.cleanup_errors
    first.close.assert_called_once()
    second.close.assert_called_once()


@pytest.mark.parametrize(
    ("rollback_terminal", "recovery_terminal"),
    [
        (KeyboardInterrupt(), SystemExit(159)),
        (SystemExit(161), KeyboardInterrupt()),
    ],
)
def test_recovery_observation_terminal_wins_over_rollback_and_ordinary_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rollback_terminal: BaseException,
    recovery_terminal: BaseException,
) -> None:
    """A new recovery-observation terminal survives later ordinary close failure."""
    transaction, first, second = _cleanup_transaction(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        first_cleanup=OSError("unused cleanup failure"),
        fail_forward=True,
    )
    monkeypatch.setattr(
        transaction,
        "_rollback",
        MagicMock(side_effect=rollback_terminal),
    )
    first.recovery_path.side_effect = recovery_terminal
    second.recovery_path.return_value = second.path
    close_error = OSError("ordinary close failure")
    first.close.side_effect = close_error

    with pytest.raises(type(recovery_terminal)) as raised:
        transaction.commit(_empty_write_set())

    assert raised.value is recovery_terminal
    outcome = raised.value.__cause__
    assert isinstance(outcome, ScribeTransactionError)
    assert outcome.state is ScribeTransactionState.INDETERMINATE
    assert outcome.rollback_error is rollback_terminal
    assert recovery_terminal in outcome.cleanup_errors
    assert close_error in outcome.cleanup_errors
    assert first.path in outcome.recovery_paths
    assert second.path in outcome.recovery_paths
    first.recovery_path.assert_called_once()
    second.recovery_path.assert_called_once()
    first.close.assert_called_once()
    second.close.assert_called_once()


def test_preparation_primary_and_ordinary_cleanup_failure_are_both_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Private preparation cleanup retains both peers before live mutation."""
    site = tmp_path / "binding-site"
    authority = MagicMock(path=site / ".lychd-owned.json")
    transaction = BindingTransaction(authority)
    workspace = MagicMock(path=site / ".lychd-transaction-test")
    cleanup_failure = OSError("preparation cleanup failed")
    workspace.cleanup.side_effect = cleanup_failure
    primary = ValueError("preparation failed")
    monkeypatch.setattr(
        transaction,
        "_create_workspace",
        MagicMock(return_value=workspace),
    )
    monkeypatch.setattr(
        transaction,
        "_prepare_site_files",
        MagicMock(side_effect=primary),
    )
    prepare = getattr(transaction, "_prepare_commit")  # noqa: B009 - adversarial private boundary

    with pytest.raises(ScribeTransactionError) as raised:
        prepare(
            _empty_write_set(),
            release_empty_authority=False,
        )

    assert raised.value.state is ScribeTransactionState.ROLLED_BACK
    assert raised.value.forward_error is primary
    assert cleanup_failure in raised.value.cleanup_errors
    assert raised.value.__cause__ is primary
    workspace.cleanup.assert_called_once()
