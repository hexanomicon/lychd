from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from lychd.system.schemas import QuadletContainer, QuadletPod, QuadletTarget, SystemdService
from lychd.system.services.scribe import (
    ScribeConflictError,
    ScribeOwnershipError,
    ScribeService,
)


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
    monkeypatch.setattr("lychd.system.services.scribe.os.getuid", lambda: actual_uid + 1)

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
    scribe.generate_all([_container(description="old container"), target])
    old_quadlet = (output_dir / "lychd-hermes.container").read_bytes()
    old_target = (systemd_dir / "lychd-coven-logic.target").read_bytes()
    old_ownership = (output_dir / ".lychd-owned.json").read_bytes()
    real_replace = os.replace
    failed = False

    def fail_second_site_once(source: str | Path, destination: str | Path) -> None:
        nonlocal failed
        destination_path = Path(destination)
        if destination_path == systemd_dir / "lychd-coven-logic.target" and not failed:
            failed = True
            message = "simulated systemd-site failure"
            raise OSError(message)
        real_replace(source, destination)

    monkeypatch.setattr("lychd.system.services.scribe.os.replace", fail_second_site_once)

    with pytest.raises(OSError, match="simulated systemd-site failure"):
        scribe.generate_all(
            [
                _container(description="new container"),
                QuadletTarget(name="logic", description="new target"),
            ]
        )

    assert (output_dir / "lychd-hermes.container").read_bytes() == old_quadlet
    assert (systemd_dir / "lychd-coven-logic.target").read_bytes() == old_target
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
    real_fsync = getattr(scribe, "_fsync_directory")  # noqa: B009 - inject private failure boundary
    calls = 0

    def fail_post_manifest_fsync_once(directory: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            message = "simulated post-manifest fsync failure"
            raise OSError(message)
        real_fsync(directory)

    monkeypatch.setattr(scribe, "_fsync_directory", fail_post_manifest_fsync_once)

    with pytest.raises(OSError, match="post-manifest fsync failure"):
        scribe.generate_all(
            [
                _container(description="new container"),
                QuadletTarget(name="logic", description="new target"),
            ]
        )

    assert (output_dir / "lychd-hermes.container").read_bytes() == old_quadlet
    assert (systemd_dir / "lychd-coven-logic.target").read_bytes() == old_target
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
    real_replace = os.replace
    failed = False

    def fail_plain_unit_once(source: str | Path, destination: str | Path) -> None:
        nonlocal failed
        if Path(destination) == systemd_dir / "lychd-reactor.service" and not failed:
            failed = True
            message = "simulated plain-unit failure"
            raise OSError(message)
        real_replace(source, destination)

    monkeypatch.setattr("lychd.system.services.scribe.os.replace", fail_plain_unit_once)

    with pytest.raises(OSError, match="plain-unit failure"):
        scribe.reconcile_all(
            [_container(description="new"), QuadletTarget(name="vision", description="new")],
            plain_units={"lychd-reactor.service": "new reactor"},
        )

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
