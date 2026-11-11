"""Real filesystem custody operations with an explicit persistent-identity test observer.

The production ioctl/subprocess observer has its own focused tests. These tests
exercise no-follow paths, actual modes, replacements and crash residue inside OCI.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from lychd.system.path_identity import PathIdentityError, PersistentPathIdentity
from lychd.system.services.tether import custody
from lychd.system.services.tether.models import TetherError, TetherIntent, digest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize("count", [1, 4])
def test_record_snapshot_scans_twice_and_expires(
    store: custody.TetherCustody, mocker: MockerFixture, count: int
) -> None:
    store.initialize()
    for index in range(count):
        store.write(f"key-{index}.json", {"index": index, "nested": {"enabled": True}})
    scans = mocker.spy(store, "_attest")
    with store.records_snapshot() as view:
        assert view.names == tuple(f"key-{index}.json" for index in range(count))
        for index, name in enumerate(view.names):
            assert view.read(name) == {"index": index, "nested": {"enabled": True}}
        assert scans.call_count == 1
        detached = view.read("key-0.json")
        assert detached is not None
        detached["nested"] = {}
        assert view.read("key-0.json") == {"index": 0, "nested": {"enabled": True}}
    assert scans.call_count == 2
    with pytest.raises(TetherError, match="ownership"):
        view.read("key-0.json")
    with pytest.raises(TetherError, match="ownership"):
        _ = view.names


@pytest.mark.parametrize("tamper", ["foreign", "replacement", "receipt", "receipt_identity", "mode", "directory"])
def test_record_snapshot_exit_rejects_drift_after_read(store: custody.TetherCustody, tamper: str) -> None:
    store.initialize()
    store.write("state.json", {"generation": 1})
    store.directory("runtime")
    views: list[custody.CustodyRecords] = []

    def observe_with_tamper() -> None:
        with store.records_snapshot() as view:
            views.append(view)
            assert view.read("state.json") == {"generation": 1}
            path = store.root / "state.json"
            if tamper == "foreign":
                (store.root / "foreign.json").write_text("{}")
            elif tamper == "replacement":
                replacement = store.root.parent / "replacement.json"
                replacement.write_bytes(path.read_bytes())
                replacement.chmod(0o600)
                replacement.replace(path)
            elif tamper == "receipt":
                receipt_path = store.root / ".custody.json"
                receipt = json.loads(receipt_path.read_bytes())
                receipt["revision"] += 1
                receipt_path.write_bytes(custody.canonical_bytes(receipt))
            elif tamper == "receipt_identity":
                receipt_path = store.root / ".custody.json"
                replacement = store.root.parent / "replacement-receipt.json"
                replacement.write_bytes(receipt_path.read_bytes())
                replacement.chmod(0o600)
                replacement.replace(receipt_path)
            elif tamper == "mode":
                path.chmod(0o644)
            else:
                directory = store.root / "runtime"
                retired = store.root.parent / "retired-runtime"
                directory.rename(retired)
                directory.symlink_to(retired, target_is_directory=True)

    with pytest.raises(TetherError, match="ownership"):
        observe_with_tamper()
    with pytest.raises(TetherError, match="ownership"):
        views[0].read("state.json")


def test_record_snapshot_bounds_reads_and_bytes(store: custody.TetherCustody, monkeypatch: pytest.MonkeyPatch) -> None:
    store.initialize()
    store.write("state.json", {"generation": 1})
    monkeypatch.setattr(custody, "_MAX_PATHS", 1)
    with store.records_snapshot() as view:
        assert view.read("state.json") == {"generation": 1}
        with pytest.raises(TetherError, match="ownership"):
            view.read("state.json")
    monkeypatch.setattr(custody, "_MAX_SNAPSHOT_BYTES", 1)
    with store.records_snapshot() as view, pytest.raises(TetherError, match="ownership"):
        view.read("state.json")


def test_record_snapshot_exception_expires_view(store: custody.TetherCustody, mocker: MockerFixture) -> None:
    store.initialize()
    scans = mocker.spy(store, "_attest")
    views: list[custody.CustodyRecords] = []

    def interrupt() -> None:
        with store.records_snapshot() as view:
            views.append(view)
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="interrupted"):
        interrupt()
    assert scans.call_count == 2
    with pytest.raises(TetherError, match="ownership"):
        _ = views[0].names


@pytest.fixture
def identity_observer(monkeypatch: pytest.MonkeyPatch) -> None:
    def observe(descriptor: int) -> PersistentPathIdentity:
        return PersistentPathIdentity(
            filesystem="ext4",
            filesystem_uuid="12345678-1234-5678-9234-567812345678",
            inode=os.fstat(descriptor).st_ino,
            generation=17,
        )

    monkeypatch.setattr(custody, "observe_identity_fd", observe)


@pytest.fixture
def store(tmp_path: Path, identity_observer: None) -> custody.TetherCustody:
    parent = tmp_path / "crypt"
    parent.mkdir(mode=0o755)
    parent.chmod(0o755)
    return custody.TetherCustody(parent / "tether")


def test_initialize_preserves_real_lifecycle_755_parent(store: custody.TetherCustody) -> None:
    before = store.root.parent.stat()
    assert store.initialize()
    assert not store.initialize()
    after = store.root.parent.stat()
    assert stat.S_IMODE(after.st_mode) == 0o755
    assert (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
    assert stat.S_IMODE(store.root.stat().st_mode) == 0o700
    assert stat.S_IMODE((store.root / ".custody.json").stat().st_mode) == 0o600
    store.attest()


def test_existing_unreceipted_root_is_never_adopted_or_chmodded(store: custody.TetherCustody) -> None:
    store.root.mkdir(mode=0o755)
    store.root.chmod(0o755)
    with pytest.raises(TetherError, match="ownership"):
        store.initialize()
    assert stat.S_IMODE(store.root.stat().st_mode) == 0o755
    assert list(store.root.iterdir()) == []


def test_private_record_repeat_is_noop_and_changed_write_is_owned(store: custody.TetherCustody) -> None:
    store.initialize()
    assert store.read("state.json") is None
    assert store.write("state.json", {"generation": 1})
    original = (store.root / "state.json").stat().st_ino
    assert not store.write("state.json", {"generation": 1})
    assert (store.root / "state.json").stat().st_ino == original
    assert store.write("state.json", {"generation": 2})
    assert store.read("state.json") == {"generation": 2}
    assert set(store.known_paths()) == {store.root, store.root / ".custody.json", store.root / "state.json"}


def test_immutable_record_repetition_is_allowed_but_replacement_is_not(store: custody.TetherCustody) -> None:
    store.initialize()
    assert store.write("key-abc.json", {"purpose": "wg-private"}, immutable=True)
    assert not store.write("key-abc.json", {"purpose": "wg-private"}, immutable=True)
    with pytest.raises(TetherError, match="ownership"):
        store.write("key-abc.json", {"purpose": "ssh-host"})
    assert store.read("key-abc.json") == {"purpose": "wg-private"}


def test_public_role_projection_modes_and_exact_inventory(store: custody.TetherCustody) -> None:
    store.initialize()
    role = store.directory("runtime/lychd-tether-wg", public=True)
    assert stat.S_IMODE(role.stat().st_mode) == 0o755
    assert store.publish(Path("runtime/lychd-tether-wg/config.json"), {"version": 1}, public=True)
    assert stat.S_IMODE((role / "config.json").stat().st_mode) == 0o444
    assert not store.publish(Path("runtime/lychd-tether-wg/config.json"), {"version": 1}, public=True)
    assert store.publish(Path("runtime/lychd-tether-wg/config.json"), {"version": 2}, public=True)
    assert role / "config.json" in store.known_paths()
    with pytest.raises(TetherError, match="ownership"):
        store.publish(Path("runtime/unknown/config.json"), {}, public=True)


@pytest.mark.parametrize("name", ["../outside.json", "/outside.json", "runtime/../state.json", ".custody.json"])
def test_traversal_and_receipt_names_are_refused(store: custody.TetherCustody, name: str) -> None:
    store.initialize()
    with pytest.raises(TetherError, match="ownership"):
        store.write(name, {})


def test_foreign_file_prevents_all_adoption(store: custody.TetherCustody) -> None:
    store.initialize()
    unknown = store.root / "foreign.json"
    unknown.write_text("{}")
    unknown.chmod(0o600)
    with pytest.raises(TetherError, match="ownership"):
        store.write("foreign.json", {})
    with pytest.raises(TetherError, match="ownership"):
        store.known_paths()


def test_same_bytes_with_different_inode_are_refused(store: custody.TetherCustody, tmp_path: Path) -> None:
    store.initialize()
    store.write("state.json", {"generation": 1})
    replacement = tmp_path / "replacement.json"
    replacement.write_bytes((store.root / "state.json").read_bytes())
    replacement.chmod(0o600)
    replacement.replace(store.root / "state.json")
    with pytest.raises(TetherError, match="ownership"):
        store.read("state.json")


def test_hardlinked_record_is_refused(store: custody.TetherCustody, tmp_path: Path) -> None:
    store.initialize()
    store.write("state.json", {})
    os.link(store.root / "state.json", tmp_path / "alias")
    with pytest.raises(TetherError, match="ownership"):
        store.attest()


def test_symlinked_owned_directory_is_refused(store: custody.TetherCustody, tmp_path: Path) -> None:
    store.initialize()
    directory = store.directory("runtime")
    directory.rename(tmp_path / "old-runtime")
    directory.symlink_to(tmp_path / "old-runtime", target_is_directory=True)
    with pytest.raises(TetherError, match="ownership"):
        store.publish(Path("runtime/config.json"), {})


def test_parent_permission_drift_is_refused(store: custody.TetherCustody) -> None:
    store.initialize()
    store.root.parent.chmod(0o775)
    with pytest.raises(TetherError, match="ownership"):
        store.attest()
    assert stat.S_IMODE(store.root.parent.stat().st_mode) == 0o775


def test_interrupted_record_receipt_commit_is_not_adopted(
    store: custody.TetherCustody, monkeypatch: pytest.MonkeyPatch
) -> None:
    store.initialize()
    store.write("state.json", {"generation": 1})

    def fail(*_arguments: object) -> None:
        message = "injected commit failure"
        raise OSError(message)

    monkeypatch.setattr(store, "_commit", fail)
    with pytest.raises(TetherError, match="ownership"):
        store.write("state.json", {"generation": 2})
    with pytest.raises(TetherError, match="ownership"):
        store.attest()


def test_unsupported_persistent_identity_refuses_without_adoption(
    store: custody.TetherCustody, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(_descriptor: int) -> PersistentPathIdentity:
        message = "unsupported filesystem"
        raise PathIdentityError(message)

    monkeypatch.setattr(custody, "observe_identity_fd", fail)
    with pytest.raises(TetherError, match="ownership"):
        store.initialize()
    assert store.root.is_dir()
    assert not (store.root / ".custody.json").exists()


def intent_bytes() -> bytes:
    return json.dumps(
        {
            "schema": "lychd.tether.intent",
            "version": 1,
            "rune": {"quadlet": {"image": "example/tether@sha256:" + "a" * 64}},
            "offered_peers": [],
            "attachments": [],
            "web_port": 7134,
        }
    ).encode()


def test_load_intent_uses_private_file_without_persistent_filesystem_requirement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "intent.json"
    path.write_bytes(intent_bytes())
    path.chmod(0o600)

    def fail(_descriptor: int) -> PersistentPathIdentity:
        message = "ordinary input must not invoke persistent observer"
        raise AssertionError(message)

    monkeypatch.setattr(custody, "observe_identity_fd", fail)
    intent = custody.load_intent(path)
    assert isinstance(intent, TetherIntent)
    assert intent.web_port == 7134
    assert digest(intent) == digest(intent.model_dump(mode="json", by_alias=True))
    path.chmod(0o644)
    with pytest.raises(TetherError, match="intent was refused"):
        custody.load_intent(path)


@pytest.mark.parametrize("payload", [b'{"version":1,"version":1}', b'{"secret":"DO_NOT_RENDER",', b'{"number":NaN}'])
def test_malformed_intent_is_bounded_and_redacted(tmp_path: Path, payload: bytes) -> None:
    path = tmp_path / "intent.json"
    path.write_bytes(payload)
    path.chmod(0o600)
    with pytest.raises(TetherError, match="intent was refused") as caught:
        custody.load_intent(path)
    assert "DO_NOT_RENDER" not in str(caught.value)


def test_intent_rejects_boolean_protocol_and_private_key_fields(tmp_path: Path) -> None:
    path = tmp_path / "intent.json"
    value = json.loads(intent_bytes())
    value["version"] = True
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    with pytest.raises(TetherError, match="intent was refused"):
        custody.load_intent(path)
    value = json.loads(intent_bytes())
    value["private_key"] = "DO_NOT_RENDER"
    path.write_text(json.dumps(value))
    with pytest.raises(TetherError, match="intent was refused"):
        custody.load_intent(path)


def test_load_intent_rejects_cross_object_admission_before_initialization(tmp_path: Path) -> None:
    path = tmp_path / "intent.json"
    value = json.loads(intent_bytes())
    value["attachments"] = [{"attachment_id": "undeclared", "generation": 1, "enabled": True}]
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    with pytest.raises(TetherError, match="intent was refused"):
        custody.load_intent(path)


def test_load_intent_refuses_a_moving_image_before_initialization(tmp_path: Path) -> None:
    path = tmp_path / "intent.json"
    value = json.loads(intent_bytes())
    value["rune"]["quadlet"]["image"] = "example/tether:latest"
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    with pytest.raises(TetherError, match="intent was refused"):
        custody.load_intent(path)
