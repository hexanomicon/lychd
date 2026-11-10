"""Filesystem adversaries and immutable evidence at the fixed custody boundary."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lychd.system.services.tether.custody import TetherCustody
from lychd.system.services.tether.models import TetherError
from tests.unit.system.services.test_tether_operations import make_custody


def test_immutable_history_disagrees_without_replacement(tmp_path: Path) -> None:
    custody = make_custody(tmp_path)
    custody.publish("revocations", "1.json", b"first", immutable=True)
    custody.publish("revocations", "1.json", b"first", immutable=True)
    with pytest.raises(TetherError, match="Immutable"):
        custody.publish("revocations", "1.json", b"second", immutable=True)
    assert custody.read("revocations", "1.json") == b"first"


def test_no_adoption_after_unreceipted_creation(tmp_path: Path) -> None:
    codex, crypt = tmp_path / "codex", tmp_path / "crypt"
    codex.mkdir(mode=0o700)
    crypt.mkdir(mode=0o700)
    (crypt / "tether").mkdir(mode=0o700)
    with pytest.raises(TetherError, match="creation receipt"):
        TetherCustody(codex, crypt).initialize()


def test_replaced_same_mode_directory_refuses(tmp_path: Path) -> None:
    custody = make_custody(tmp_path)
    target = custody.directories["wireguard"]
    target.rename(target.with_name("preserved"))
    target.mkdir(mode=0o755)
    with pytest.raises(TetherError, match="identity changed"):
        custody.attest()


def test_symlink_and_hardlink_records_refuse(tmp_path: Path) -> None:
    custody = make_custody(tmp_path)
    target = custody.directories["private"] / "closed.json"
    foreign = tmp_path / "foreign"
    foreign.write_bytes(b"preserve")
    foreign.chmod(0o600)
    target.symlink_to(foreign)
    with pytest.raises(OSError, match="Too many levels"):
        custody.read("private", "closed.json")
    target.unlink()
    os.link(foreign, target)
    with pytest.raises(TetherError, match="metadata"):
        custody.read("private", "closed.json")
    assert foreign.read_bytes() == b"preserve"


def test_public_forwarder_files_are_readable_after_ssh_uid_drop(tmp_path: Path) -> None:
    custody = make_custody(tmp_path)
    custody.publish("forwarder", "authorized_keys", b"public")
    assert custody.directories["public"].stat().st_mode & 0o777 == 0o700
    assert custody.directories["forwarder"].stat().st_mode & 0o777 == 0o755
    assert (custody.directories["forwarder"] / "authorized_keys").stat().st_mode & 0o777 == 0o644


def test_restrictive_operator_umask_still_creates_receipted_exact_modes(tmp_path: Path) -> None:
    previous = os.umask(0o077)
    try:
        custody = make_custody(tmp_path)
        custody.publish("forwarder", "authorized_keys", b"public")
        custody.attest()
        assert custody.directories["forwarder"].stat().st_mode & 0o777 == 0o755
        assert (custody.directories["forwarder"] / "authorized_keys").stat().st_mode & 0o777 == 0o644
    finally:
        os.umask(previous)


def test_initial_virtual_selection_matches_the_first_persisted_parent(tmp_path: Path) -> None:
    from lychd.system.services.tether.custody import PreparationStore
    from lychd.system.services.tether.models import ImagePreparationBundle, digest
    from tests.unit.system.services.test_tether_operations import image_request, image_stack

    operations, _, _, _ = image_stack(tmp_path)
    store = PreparationStore(operations.custody)
    initial = store.selected()
    assert initial.selection.parent_preparation_digest is None
    assert operations.custody.read("private", "current-preparation.json") is None
    request = image_request(operations)
    operations.prepare_image(request)
    raw = operations.custody.read("private", f"image-preparation-{request.operation_id}.json")
    assert raw is not None
    bundle = ImagePreparationBundle.model_validate_json(raw)
    assert bundle.parent_selection == initial.selection
    assert digest(bundle.parent_selection) == request.expected_preparation_digest
    assert store.selected().selection.parent_preparation_digest == digest(initial.selection)


@pytest.mark.parametrize("fault", ["missing-selector", "missing-bundle", "bundle-digest", "selector-version"])
def test_selected_preparation_corruption_never_falls_back_to_original(tmp_path: Path, fault: str) -> None:
    import json

    from lychd.system.services.tether.custody import PreparationStore
    from tests.unit.system.services.test_tether_operations import image_request, image_stack

    operations, _, _, _ = image_stack(tmp_path)
    request = image_request(operations)
    operations.prepare_image(request)
    private = operations.custody.directories["private"]
    selector = private / "current-preparation.json"
    bundle = private / f"image-preparation-{request.operation_id}.json"
    if fault == "missing-selector":
        selector.unlink()
    elif fault == "missing-bundle":
        bundle.unlink()
    elif fault == "bundle-digest":
        raw = json.loads(bundle.read_text())
        raw["request_digest"] = "f" * 64
        operations.custody.publish("private", bundle.name, json.dumps(raw).encode())
    else:
        raw = json.loads(selector.read_text())
        raw["version"] = 99
        operations.custody.publish("private", selector.name, json.dumps(raw).encode())
    assert operations.custody.read("private", "plan.json") is not None
    assert operations.custody.read("private", "preparation.json") is not None
    with pytest.raises((TetherError, ValueError)):
        PreparationStore(operations.custody).selected()


def test_preparation_selector_cas_refuses_changed_bytes_without_replacement(tmp_path: Path) -> None:
    from lychd.system.services.tether.custody import PreparationStore
    from tests.unit.system.services.test_tether_operations import image_stack

    operations, _, _, _ = image_stack(tmp_path)
    selected = PreparationStore(operations.custody).selected().selection
    operations.custody.select_preparation(None, selected)
    raw = operations.custody.read("private", "current-preparation.json")
    with pytest.raises(TetherError, match="selector changed"):
        operations.custody.select_preparation(None, selected)
    assert operations.custody.read("private", "current-preparation.json") == raw


def test_completed_unselected_bundle_refuses_partial_selector_rollback(tmp_path: Path) -> None:
    from lychd.system.services.tether.custody import PreparationStore
    from tests.unit.system.services.test_tether_operations import image_request, image_stack

    operations, _, _, _ = image_stack(tmp_path)
    store = PreparationStore(operations.custody)
    initial = store.selected()
    operations.prepare_image(image_request(operations))
    operations.custody.write("private", "current-preparation.json", initial.selection)
    with pytest.raises(TetherError, match="outside current selected ancestry"):
        store.selected()
