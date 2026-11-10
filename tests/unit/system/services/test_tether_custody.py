"""Filesystem adversaries and immutable evidence at the fixed custody boundary."""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

import pytest

from lychd.system import path_identity
from lychd.system.services.tether.custody import CustodyReceipt, TetherCustody
from lychd.system.services.tether.models import TetherError
from tests.unit.system.services.test_tether_operations import make_custody


def observe_fixture_identity(descriptor: int) -> path_identity.PersistentPathIdentity:
    """Model stable filesystem authority independently of host test storage."""
    return path_identity.PersistentPathIdentity(
        filesystem="btrfs",
        filesystem_uuid=str(UUID(int=100)),
        inode=os.fstat(descriptor).st_ino,
        generation=1,
        subvolume_id=256,
        subvolume_uuid=str(UUID(int=101)),
    )


@pytest.fixture
def persistent_custody(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TetherCustody:
    monkeypatch.setattr(path_identity, "observe_identity_fd", observe_fixture_identity)
    codex, crypt = tmp_path / "codex", tmp_path / "crypt"
    codex.mkdir(mode=0o700)
    crypt.mkdir(mode=0o700)
    custody = TetherCustody(codex, crypt)
    custody.initialize()
    return custody


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


def test_versioned_receipt_contains_persistent_identities_for_all_fixed_roots(
    persistent_custody: TetherCustody,
) -> None:
    receipt_path = persistent_custody.directories["private"] / ".custody.json"
    receipt = CustodyReceipt.model_validate_json(receipt_path.read_bytes())
    assert receipt.version == 1
    assert set(receipt.identities) == {*persistent_custody.directories, "codex", "crypt"}
    assert all(identity.filesystem == "btrfs" for identity in receipt.identities.values())
    assert all(identity.subvolume_id == 256 for identity in receipt.identities.values())
    assert all(identity.subvolume_uuid == str(UUID(int=101)) for identity in receipt.identities.values())
    assert all(identity.filesystem_uuid == str(UUID(int=100)) for identity in receipt.identities.values())
    assert all(identity.generation == 1 for identity in receipt.identities.values())
    assert all("st_dev" not in identity.model_dump() for identity in receipt.identities.values())


def test_reboot_device_number_change_preserves_exact_persistent_custody(
    persistent_custody: TetherCustody, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt_path = persistent_custody.directories["private"] / ".custody.json"
    before = receipt_path.read_bytes()
    real_fstat = os.fstat

    def rebooted_fstat(descriptor: int) -> os.stat_result:
        values = list(real_fstat(descriptor))
        values[2] += 1000
        return os.stat_result(values)

    monkeypatch.setattr(os, "fstat", rebooted_fstat)
    persistent_custody.attest()
    persistent_custody.publish("public", "post-reboot.json", b"public")
    assert receipt_path.read_bytes() == before


@pytest.mark.parametrize("changed", ["filesystem-uuid", "inode-generation", "inode", "subvolume-id", "subvolume-uuid"])
def test_same_path_cannot_rebind_a_changed_persistent_identity(
    persistent_custody: TetherCustody, monkeypatch: pytest.MonkeyPatch, changed: str
) -> None:
    before = (persistent_custody.directories["private"] / ".custody.json").read_bytes()

    def substituted(descriptor: int) -> path_identity.PersistentPathIdentity:
        original = observe_fixture_identity(descriptor)
        if changed == "filesystem-uuid":
            return original.model_copy(update={"filesystem_uuid": str(UUID(int=102))})
        if changed == "inode-generation":
            return original.model_copy(update={"generation": original.generation + 1})
        if changed == "inode":
            return original.model_copy(update={"inode": original.inode + 1})
        if changed == "subvolume-id":
            return original.model_copy(update={"subvolume_id": 257})
        return original.model_copy(update={"subvolume_uuid": str(UUID(int=102))})

    monkeypatch.setattr(path_identity, "observe_identity_fd", substituted)
    with pytest.raises(TetherError, match="identity changed"):
        persistent_custody.attest()
    assert (persistent_custody.directories["private"] / ".custody.json").read_bytes() == before


@pytest.mark.parametrize(
    "shape",
    [
        "legacy",
        "version-missing",
        "version-unsupported",
        "version-bool",
        "version-float",
        "version-string",
        "missing-role",
        "extra-role",
    ],
)
def test_custody_receipt_refuses_legacy_or_unsupported_authority(persistent_custody: TetherCustody, shape: str) -> None:
    receipt_path = persistent_custody.directories["private"] / ".custody.json"
    typed = CustodyReceipt.model_validate_json(receipt_path.read_bytes())
    identities = {role: identity.model_dump(mode="json") for role, identity in typed.identities.items()}
    receipt: dict[str, object] = {"version": 1, "identities": identities}
    if shape == "legacy":
        receipt = {role: [1, 2] for role in (*persistent_custody.directories, "codex", "crypt")}
    elif shape == "version-missing":
        del receipt["version"]
    elif shape == "version-unsupported":
        receipt["version"] = 2
    elif shape == "version-bool":
        receipt["version"] = True
    elif shape == "version-float":
        receipt["version"] = 1.0
    elif shape == "version-string":
        receipt["version"] = "1"
    elif shape == "missing-role":
        del identities["codex"]
    else:
        identities["foreign"] = identities["codex"]
    original = json.dumps(receipt).encode()
    receipt_path.write_bytes(original)
    with pytest.raises(TetherError, match="receipt"):
        persistent_custody.attest()
    with pytest.raises(TetherError, match="receipt"):
        persistent_custody.initialize()
    assert receipt_path.read_bytes() == original


def test_provider_refusal_preserves_existing_custody_evidence(
    persistent_custody: TetherCustody, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = (persistent_custody.directories["private"] / ".custody.json").read_bytes()

    def unavailable(_descriptor: int) -> path_identity.PersistentPathIdentity:
        msg = "unsupported filesystem"
        raise path_identity.PathIdentityError(msg)

    monkeypatch.setattr(path_identity, "observe_identity_fd", unavailable)
    with pytest.raises(TetherError, match="persistent filesystem identity is unavailable"):
        persistent_custody.attest()
    assert (persistent_custody.directories["private"] / ".custody.json").read_bytes() == before


def test_initial_provider_refusal_never_adopts_partially_created_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(_descriptor: int) -> path_identity.PersistentPathIdentity:
        msg = "unsupported filesystem"
        raise path_identity.PathIdentityError(msg)

    monkeypatch.setattr(path_identity, "observe_identity_fd", unavailable)
    codex, crypt = tmp_path / "codex", tmp_path / "crypt"
    codex.mkdir(mode=0o700)
    crypt.mkdir(mode=0o700)
    custody = TetherCustody(codex, crypt)
    with pytest.raises(TetherError, match="persistent filesystem identity is unavailable"):
        custody.initialize()
    assert not (custody.directories["private"] / ".custody.json").exists()
    monkeypatch.setattr(path_identity, "observe_identity_fd", observe_fixture_identity)
    with pytest.raises(TetherError, match="Unreceipted"):
        custody.initialize()
