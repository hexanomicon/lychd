"""Absent-only key creation, crash recovery, import custody and secret quarantine."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import struct
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from lychd.system.operator.process import ProcessResult
from lychd.system.services.tether import keys
from lychd.system.services.tether.models import TetherError

if TYPE_CHECKING:
    from lychd.system.services.tether.custody import TetherCustody

EPOCH = "e" * 32
REFERENCE = "lychd-tether-local"
PRIVATE = bytes([8]) + b"a" * 30 + bytes([64])


def encoded(value: bytes) -> str:
    return base64.b64encode(value).decode() + "\n"


def ssh_fixture(seed: bytes) -> tuple[str, str]:
    def field(value: bytes) -> bytes:
        return struct.pack(">I", len(value)) + value

    public = hashlib.sha256(seed).digest()
    public_blob = field(b"ssh-ed25519") + field(public)
    private_blob = struct.pack(">II", 7, 7) + field(b"ssh-ed25519") + field(public) + field(seed + public) + field(b"")
    padding = 8 - len(private_blob) % 8
    private_blob += bytes(range(1, padding + 1))
    wire = (
        b"openssh-key-v1\0"
        + field(b"none")
        + field(b"none")
        + field(b"")
        + struct.pack(">I", 1)
        + field(public_blob)
        + field(private_blob)
    )
    private = (
        "-----BEGIN OPENSSH PRIVATE KEY-----\n"
        + base64.b64encode(wire).decode()
        + "\n-----END OPENSSH PRIVATE KEY-----\n"
    )
    return private, "ssh-ed25519 " + base64.b64encode(public_blob).decode()


class Custody:
    def __init__(self, root: Path) -> None:
        """Keep test receipts separate from private input files."""
        self.root = root
        root.mkdir(mode=0o700)
        self.records: dict[str, dict[str, Any]] = {}
        self.directories: set[str] = set()

    def attest(self) -> None:
        for name in self.directories:
            assert list((self.root / name).iterdir()) == []

    def read(self, name: str) -> dict[str, Any] | None:
        self.attest()
        return copy.deepcopy(self.records.get(name))

    def write(self, name: str, record: dict[str, Any], *, immutable: bool = False) -> bool:
        self.attest()
        assert immutable
        if name in self.records:
            assert self.records[name] == record
            return False
        self.records[name] = copy.deepcopy(record)
        return True

    def directory(self, name: str, *, public: bool = False) -> Path:
        assert not public
        path = self.root / name
        path.mkdir(mode=0o700, exist_ok=True)
        self.directories.add(name)
        return path

    def known_paths(self) -> tuple[Path, ...]:
        return tuple(self.root / name for name in sorted(self.records))


class Runner:
    def __init__(self) -> None:
        """Model an exact secret store and tools without running host commands."""
        self.secrets: dict[str, dict[str, Any]] = {}
        self.commands: list[tuple[str, ...]] = []
        self.generated = 0
        self.fail_create: str | None = None
        self.private = PRIVATE
        self.ssh_private, self.ssh_public = ssh_fixture(b"s" * 32)

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        return self._run(argv, timeout_s=timeout_s, value=None)

    def run_with_input(self, argv: tuple[str, ...], *, timeout_s: float, input_text: str) -> ProcessResult:
        return self._run(argv, timeout_s=timeout_s, value=input_text)

    def _run(self, argv: tuple[str, ...], *, timeout_s: float, value: str | None) -> ProcessResult:  # noqa: PLR0911 - explicit tool-result fixtures
        assert timeout_s > 0
        self.commands.append(argv)
        command = argv[1:]
        if argv[0] == "/tools/wg":
            if command == ("genkey",):
                self.generated += 1
                return ProcessResult(argv, 0, encoded(self.private))
            assert command == ("pubkey",)
            assert value is not None
            return ProcessResult(argv, 0, encoded(hashlib.sha256(base64.b64decode(value)).digest()))
        if argv[0] == "/tools/ssh-keygen":
            if command[0] == "-q":
                target = Path(command[-1])
                target.write_text(self.ssh_private)
                target.chmod(0o600)
                target.with_suffix(".pub").write_text(self.ssh_public)
                self.generated += 1
                return ProcessResult(argv, 0)
            assert command == ("-y", "-P", "", "-f", "/dev/stdin")
            assert value == self.ssh_private
            return ProcessResult(argv, 0, self.ssh_public + "\n")
        assert argv[0] == "/tools/podman"
        assert command[0] == "secret"
        if command[1] == "exists":
            return ProcessResult(argv, 0 if command[2] in self.secrets else 1)
        if command[1] == "inspect":
            assert command[2] == "--showsecret"
            target = command[3]
            row = next((row for name, row in self.secrets.items() if target in {name, row["ID"]}), None)
            return ProcessResult(argv, 1) if row is None else ProcessResult(argv, 0, json.dumps([row]))
        assert command[1] == "create"
        assert command[2:4] == ("--driver", "file")
        assert command[-1] == "-"
        assert "--replace" not in command
        assert "--ignore" not in command
        if self.fail_create == "before":
            raise RuntimeError("secret diagnostic " + str(value))
        reference = command[-2]
        labels = dict(command[index + 1].split("=", 1) for index, item in enumerate(command) if item == "--label")
        if reference in self.secrets:
            return ProcessResult(argv, 125, stderr="secret conflict " + str(value))
        secret_id = f"{len(self.secrets) + 1:032x}"
        self.secrets[reference] = {
            "ID": secret_id,
            "Spec": {"Name": reference, "Labels": labels, "Driver": {"Name": "file", "Options": {}}},
            "SecretData": value,
        }
        if self.fail_create == "after":
            raise RuntimeError("secret diagnostic " + str(value))
        return ProcessResult(argv, 0, secret_id + "\n")


@pytest.fixture
def gateway(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[keys.TetherKeys, Custody, Runner]:
    custody, runner = Custody(tmp_path / "custody"), Runner()
    monkeypatch.setattr(keys, "trusted_host_tool", lambda name, **_kwargs: "/tools/" + name)
    return keys.TetherKeys(cast("TetherCustody", custody), EPOCH, runner), custody, runner


def test_ensure_is_absent_only_and_public_receipts_exclude_private(
    gateway: tuple[keys.TetherKeys, Custody, Runner],
) -> None:
    service, custody, runner = gateway
    first = service.ensure(REFERENCE, "wireguard")
    assert service.ensure(REFERENCE, "wireguard") == first
    assert service.attest(REFERENCE) == first
    assert runner.generated == 1
    assert service.known_references() == (REFERENCE,)
    private = encoded(PRIVATE).strip()
    assert private not in json.dumps(custody.records)
    assert private not in json.dumps(first)
    assert all(private not in " ".join(argv) for argv in runner.commands)


def test_foreign_existing_name_is_never_adopted(gateway: tuple[keys.TetherKeys, Custody, Runner]) -> None:
    service, _custody, runner = gateway
    runner.secrets[REFERENCE] = {"ID": "f" * 32, "SecretData": "foreign"}
    with pytest.raises(TetherError, match="refused"):
        service.ensure(REFERENCE, "wireguard")
    assert runner.generated == 0
    assert not any("inspect" in command for command in runner.commands)


def test_pending_exact_labeled_creation_recovers_without_regeneration(
    gateway: tuple[keys.TetherKeys, Custody, Runner],
) -> None:
    service, custody, runner = gateway
    runner.fail_create = "after"
    with pytest.raises(TetherError, match="refused") as failure:
        service.ensure(REFERENCE, "wireguard")
    assert encoded(PRIVATE).strip() not in str(failure.value)
    assert failure.value.__cause__ is None
    assert len(custody.records) == 1
    runner.fail_create = None
    recovered = service.ensure(REFERENCE, "wireguard")
    assert recovered["secret_id"] == runner.secrets[REFERENCE]["ID"]
    assert runner.generated == 1
    assert len(custody.records) == 2


def test_pending_without_secret_refuses_uncertain_regeneration(
    gateway: tuple[keys.TetherKeys, Custody, Runner],
) -> None:
    service, _custody, runner = gateway
    runner.fail_create = "before"
    with pytest.raises(TetherError, match="refused"):
        service.ensure(REFERENCE, "wireguard")
    runner.fail_create = None
    with pytest.raises(TetherError, match="refused"):
        service.ensure(REFERENCE, "wireguard")
    assert runner.generated == 1
    assert not runner.secrets


@pytest.mark.parametrize("tamper", ["id", "labels", "value", "driver"])
def test_attestation_refuses_replacement_or_policy_drift(
    gateway: tuple[keys.TetherKeys, Custody, Runner], tamper: str
) -> None:
    service, _custody, runner = gateway
    service.ensure(REFERENCE, "wireguard")
    secret = runner.secrets[REFERENCE]
    if tamper == "id":
        secret["ID"] = "f" * 32
    elif tamper == "labels":
        secret["Spec"]["Labels"]["io.lychd.tether.epoch"] = "f" * 32
    elif tamper == "driver":
        secret["Spec"]["Driver"] = {"Name": "shell", "Options": {"lookup": "foreign"}}
    else:
        secret["SecretData"] = encoded(b"z" * 32)
    with pytest.raises(TetherError, match="refused"):
        service.attest(REFERENCE)
    assert runner.generated == 1


def test_pending_wrong_operation_is_not_adopted(gateway: tuple[keys.TetherKeys, Custody, Runner]) -> None:
    service, _custody, runner = gateway
    runner.fail_create = "after"
    with pytest.raises(TetherError, match="refused"):
        service.ensure(REFERENCE, "wireguard")
    runner.fail_create = None
    runner.secrets[REFERENCE]["Spec"]["Labels"]["io.lychd.tether.operation"] = "f" * 32
    with pytest.raises(TetherError, match="refused"):
        service.ensure(REFERENCE, "wireguard")
    assert runner.generated == 1


def private_input(tmp_path: Path, value: bytes) -> Path:
    directory = tmp_path / "import"
    directory.mkdir(mode=0o700)
    path = directory / "key"
    path.write_text(encoded(value))
    path.chmod(0o600)
    return path


def test_psk_import_is_idempotent_but_cannot_reuse_tunnel_private_material(
    gateway: tuple[keys.TetherKeys, Custody, Runner], tmp_path: Path
) -> None:
    service, _custody, runner = gateway
    service.ensure(REFERENCE, "wireguard")
    path = private_input(tmp_path, PRIVATE)
    with pytest.raises(TetherError, match="refused"):
        service.import_key("lychd-tether-psk", path, "preshared")
    assert len(runner.secrets) == 1
    path.write_text(encoded(b"p" * 32))
    first = service.import_key("lychd-tether-psk", path, "preshared")
    assert first["public_key"] is None
    assert service.import_key("lychd-tether-psk", path, "preshared") == first
    path.write_text(encoded(b"q" * 32))
    with pytest.raises(TetherError, match="refused"):
        service.import_key("lychd-tether-psk", path, "preshared")


@pytest.mark.parametrize("unsafe", ["mode", "parent", "symlink", "hardlink"])
def test_import_requires_private_owned_single_link_file(
    gateway: tuple[keys.TetherKeys, Custody, Runner], tmp_path: Path, unsafe: str
) -> None:
    service, _custody, runner = gateway
    path = private_input(tmp_path, PRIVATE)
    if unsafe == "mode":
        path.chmod(0o644)
    elif unsafe == "parent":
        path.parent.chmod(0o755)
    elif unsafe == "symlink":
        link = path.parent / "alias"
        link.symlink_to(path)
        path = link
    else:
        os.link(path, path.parent / "alias")
    with pytest.raises(TetherError, match="refused"):
        service.import_key(REFERENCE, path, "wireguard")
    assert not runner.secrets
    assert not runner.commands


def test_ssh_generation_cleans_private_staging_before_receipt(gateway: tuple[keys.TetherKeys, Custody, Runner]) -> None:
    service, custody, runner = gateway
    result = service.ensure("lychd-tether-ssh", "ssh-host")
    assert result["public_key"] == runner.ssh_public
    custody.attest()
    assert list((custody.root / "key-staging").iterdir()) == []
    assert runner.ssh_private not in json.dumps(custody.records)
    assert service.attest("lychd-tether-ssh") == result


def test_ssh_seed_cannot_be_reused_as_preshared_material(
    gateway: tuple[keys.TetherKeys, Custody, Runner], tmp_path: Path
) -> None:
    service, _custody, runner = gateway
    service.ensure("lychd-tether-ssh", "ssh-host")
    path = private_input(tmp_path, b"s" * 32)
    with pytest.raises(TetherError, match="refused"):
        service.import_key("lychd-tether-psk", path, "preshared")
    assert len(runner.secrets) == 1


def test_inventory_never_discovers_unreceipted_podman_names(
    gateway: tuple[keys.TetherKeys, Custody, Runner],
) -> None:
    service, _custody, runner = gateway
    runner.secrets[REFERENCE] = {"ID": "f" * 32, "SecretData": "foreign"}
    assert service.known_references() == ()
    assert not runner.commands


def test_pending_inventory_is_known_but_not_attested(
    gateway: tuple[keys.TetherKeys, Custody, Runner],
) -> None:
    service, _custody, runner = gateway
    runner.fail_create = "before"
    with pytest.raises(TetherError):
        service.ensure(REFERENCE, "wireguard")
    previous_commands = list(runner.commands)
    assert service.known_references() == (REFERENCE,)
    assert runner.commands == previous_commands
    with pytest.raises(TetherError):
        service.attest(REFERENCE)


@pytest.mark.parametrize("tamper", ["reference", "epoch", "filename"])
def test_inventory_refuses_malformed_receipted_identity(
    gateway: tuple[keys.TetherKeys, Custody, Runner],
    tamper: str,
) -> None:
    service, custody, runner = gateway
    service.ensure(REFERENCE, "wireguard")
    name = next(iter(custody.records))
    if tamper == "filename":
        custody.records["key-" + "0" * 64 + "-pending.json"] = custody.records.pop(name)
    elif tamper == "epoch":
        custody.records[name]["installation_epoch"] = "0" * 32
    else:
        custody.records[name]["reference"] = "lychd-tether-other"
    previous_commands = list(runner.commands)
    with pytest.raises(TetherError):
        service.known_references()
    assert runner.commands == previous_commands


def test_preparation_state_is_receipt_only_and_distinguishes_pending(
    gateway: tuple[keys.TetherKeys, Custody, Runner],
) -> None:
    service, _custody, runner = gateway
    assert service.preparation_state(REFERENCE) == "absent"
    assert not runner.commands
    runner.fail_create = "after"
    with pytest.raises(TetherError):
        service.ensure(REFERENCE, "wireguard")
    commands = list(runner.commands)
    assert service.preparation_state(REFERENCE) == "pending"
    assert runner.commands == commands
    runner.fail_create = None
    service.ensure(REFERENCE, "wireguard")
    commands = list(runner.commands)
    assert service.preparation_state(REFERENCE) == "ready"
    assert runner.commands == commands
    runner.secrets.clear()
    assert service.preparation_state(REFERENCE) == "ready"
    with pytest.raises(TetherError):
        service.attest(REFERENCE)


@pytest.mark.parametrize("tamper", ["missing-pending", "mismatched-operation", "epoch", "filename"])
def test_preparation_state_refuses_inconsistent_receipts(
    gateway: tuple[keys.TetherKeys, Custody, Runner],
    tamper: str,
) -> None:
    service, custody, runner = gateway
    service.ensure(REFERENCE, "wireguard")
    pending = next(name for name in custody.records if name.endswith("-pending.json"))
    if tamper == "missing-pending":
        del custody.records[pending]
    elif tamper == "filename":
        custody.records["key-" + "0" * 64 + "-pending.json"] = custody.records.pop(pending)
    elif tamper == "epoch":
        custody.records[pending]["installation_epoch"] = "0" * 32
    else:
        custody.records[pending]["operation_id"] = "0" * 32
    commands = list(runner.commands)
    with pytest.raises(TetherError):
        service.preparation_state(REFERENCE)
    assert runner.commands == commands


@pytest.mark.parametrize("failure", ["before", "after"])
def test_owned_inventory_handles_pending_without_effects(
    gateway: tuple[keys.TetherKeys, Custody, Runner],
    failure: str,
) -> None:
    service, custody, runner = gateway
    runner.fail_create = failure
    with pytest.raises(TetherError):
        service.ensure(REFERENCE, "wireguard")
    records = copy.deepcopy(custody.records)
    generated = runner.generated
    assert service.owned_references() == ((REFERENCE,) if failure == "after" else ())
    assert custody.records == records
    assert runner.generated == generated


def test_owned_inventory_rejects_replaced_final_and_pending(
    gateway: tuple[keys.TetherKeys, Custody, Runner],
) -> None:
    service, custody, runner = gateway
    service.ensure(REFERENCE, "wireguard")
    assert service.owned_references() == (REFERENCE,)
    runner.secrets[REFERENCE]["Spec"]["Labels"] = {}
    with pytest.raises(TetherError):
        service.owned_references()
    final = next(name for name in custody.records if not name.endswith("-pending.json"))
    del custody.records[final]
    with pytest.raises(TetherError):
        service.owned_references()


def test_owned_inventory_refuses_missing_final_backend(
    gateway: tuple[keys.TetherKeys, Custody, Runner],
) -> None:
    service, _custody, runner = gateway
    service.ensure(REFERENCE, "wireguard")
    runner.secrets.clear()
    with pytest.raises(TetherError):
        service.owned_references()


def test_failed_unrelated_creation_does_not_block_existing_key_attestation(
    gateway: tuple[keys.TetherKeys, Custody, Runner],
) -> None:
    service, custody, runner = gateway
    identity = service.ensure(REFERENCE, "wireguard")
    runner.fail_create = "before"
    other = "lychd-tether-next-owner"
    with pytest.raises(TetherError):
        service.ensure(other, "ssh-host")
    assert service.preparation_state(other) == "pending"
    assert other not in runner.secrets
    records = copy.deepcopy(custody.records)
    generated = runner.generated
    runner.fail_create = None
    assert service.attest(REFERENCE) == identity
    assert service.ensure(REFERENCE, "wireguard") == identity
    assert service.owned_references() == (REFERENCE,)
    assert custody.records == records
    assert runner.generated == generated
    with pytest.raises(TetherError):
        service.ensure(other, "ssh-host")
    assert runner.generated == generated


@pytest.mark.parametrize("phase", ["pending", "final"])
@pytest.mark.parametrize("tamper", ["missing", "labels"])
def test_unrelated_existing_custody_still_blocks_attestation_on_drift(
    gateway: tuple[keys.TetherKeys, Custody, Runner], phase: str, tamper: str
) -> None:
    service, _custody, runner = gateway
    service.ensure(REFERENCE, "wireguard")
    other = "lychd-tether-next-owner"
    if phase == "pending":
        runner.fail_create = "after"
        with pytest.raises(TetherError):
            service.ensure(other, "ssh-host")
    else:
        service.ensure(other, "ssh-host")
    if tamper == "missing":
        del runner.secrets[other]
    else:
        runner.secrets[other]["Spec"]["Labels"] = {}
    if phase == "pending" and tamper == "missing":
        assert service.attest(REFERENCE)["reference"] == REFERENCE
    else:
        with pytest.raises(TetherError):
            service.attest(REFERENCE)
