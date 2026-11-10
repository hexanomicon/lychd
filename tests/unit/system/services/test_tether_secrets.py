"""Absent-only secret creation, races and immutable-identity attestation."""

from __future__ import annotations

# Fault injection exercises the fixed private factory and attestation boundary.
# pyright: reportPrivateUsage=false
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import BaseModel

from lychd.system.operator.process import ProcessResult
from lychd.system.services.tether.custody import TetherCustody
from lychd.system.services.tether.models import TetherError
from lychd.system.services.tether.secrets import TetherSecrets
from tests.unit.system.services.test_tether_operations import make_custody, make_peer, make_plan

if TYPE_CHECKING:
    from lychd.domain.tether.models import CompiledTetherPlan
    from lychd.system.services.tether.models import ClosureObservation


def secret_stack(tmp_path: Path) -> tuple[TetherSecrets, TetherCustody, dict[str, dict[str, Any]], list[str]]:
    custody, plan, runner = make_custody(tmp_path), make_plan(), MagicMock()
    values: dict[str, dict[str, Any]] = {}
    created: list[str] = []

    def probe(argv: tuple[str, ...], **_: object) -> ProcessResult:
        if argv[1:3] == ("secret", "exists"):
            return ProcessResult(argv, 0 if argv[3] in values else 1)
        if argv[1:3] == ("secret", "inspect"):
            row = next((row for row in values.values() if row["ID"] == argv[-1]), None)
            return ProcessResult(argv, 0 if row else 125, json.dumps([row]) if row else "[]")
        return ProcessResult(argv, 0)

    def input_command(argv: tuple[str, ...], *, input_text: str, **_: object) -> ProcessResult:
        if argv[1:3] == ("secret", "create"):
            name = argv[3]
            if name in values:
                return ProcessResult(argv, 125, "", "sensitive diagnostic")
            identity = str(len(values) + 1) * 25
            values[name] = {"ID": identity, "Spec": {"Name": name}, "SecretData": input_text}
            created.append(name)
            return ProcessResult(argv, 0, identity)
        return ProcessResult(
            argv,
            0,
            make_peer().wireguard_public_key if argv[0].endswith("wg") else make_peer().ssh_authorized_public_key,
        )

    runner.run.side_effect = probe
    runner.run_with_input.side_effect = input_command
    service = TetherSecrets(
        plan, custody, runner, podman_bin="/usr/bin/podman", wg_bin="/usr/bin/wg", ssh_keygen_bin="/usr/bin/ssh-keygen"
    )

    def factory_result(purpose: str) -> tuple[str, str]:
        return (
            "synthetic-server-secret",
            make_peer().wireguard_public_key
            if purpose == "wireguard-server"
            else make_peer().ssh_authorized_public_key,
        )

    factory = MagicMock(side_effect=factory_result)
    service._factory = factory
    return service, custody, values, created


def test_preparation_creates_two_exact_ids_and_attests_fingerprints(tmp_path: Path) -> None:
    service, _, _, created = secret_stack(tmp_path)
    receipt = service.prepare(uuid4())
    assert created == ["test-wg", "test-ssh"]
    assert len({identity.podman_id for identity in receipt.secrets}) == 2
    assert all(identity.fingerprint.startswith("SHA256:") for identity in receipt.secrets)
    assert service.attest() == receipt
    assert "synthetic-server-secret" not in receipt.model_dump_json()


def test_existing_name_without_creation_authority_refuses(tmp_path: Path) -> None:
    service, _, values, created = secret_stack(tmp_path)
    values["test-wg"] = {"ID": "f" * 25}
    with pytest.raises(TetherError, match="refusing adoption"):
        service.prepare(uuid4())
    assert created == []
    cast("MagicMock", service._factory).assert_not_called()


def test_secret_identity_replacement_refuses_before_bind(tmp_path: Path) -> None:
    service, _, values, _ = secret_stack(tmp_path)
    service.prepare(uuid4())
    values["test-wg"]["ID"] = "f" * 25
    with pytest.raises(TetherError):
        service.attest()


def test_crash_between_create_and_receipt_cannot_adopt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service, custody, _, created = secret_stack(tmp_path)
    original = custody.write

    def crash(role: str, name: str, value: BaseModel, **kwargs: bool) -> None:
        if name == "secret-wireguard-server.json":
            raise KeyboardInterrupt
        original(role, name, value, **kwargs)

    monkeypatch.setattr(custody, "write", crash)
    with pytest.raises(KeyboardInterrupt):
        service.prepare(uuid4())
    monkeypatch.setattr(custody, "write", original)
    with pytest.raises(TetherError, match="Uncertain"):
        service.prepare(uuid4())
    assert created == ["test-wg"]
    assert custody.read("private", "secret-wireguard-server.pending.json")


def test_dry_run_applies_foreign_name_refusal_without_creation(tmp_path: Path) -> None:
    service, _, values, created = secret_stack(tmp_path)
    service.preview_prepare()
    assert created == []
    cast("MagicMock", service._factory).assert_not_called()
    values["test-ssh"] = {"ID": "f" * 25}
    with pytest.raises(TetherError, match="already exists"):
        service.preview_prepare()
    assert created == []


def test_image_preparation_rechecks_replaced_secret_after_cold_observation(tmp_path: Path) -> None:
    from tests.unit.system.services.test_tether_operations import closed, image_request, image_stack

    operations, _, values, created = image_stack(tmp_path)
    request = image_request(operations)

    def cold_probe(_plan: CompiledTetherPlan) -> ClosureObservation:
        values["test-wg"]["ID"] = "f" * 25
        return closed()

    operations.preparation_cold_probe = cold_probe
    with pytest.raises(TetherError):
        operations.prepare_image(request)
    assert operations.custody.read("private", "current-preparation.json") is None
    assert created == ["test-wg", "test-ssh"]


def test_returning_to_an_old_image_has_a_new_selection_identity_without_new_keys(tmp_path: Path) -> None:
    from lychd.system.services.tether.custody import PreparationStore
    from lychd.system.services.tether.models import digest
    from tests.unit.system.services.test_tether_operations import image_request, image_stack

    operations, original, _, created = image_stack(tmp_path)
    initial = PreparationStore(operations.custody).selected()
    operations.prepare_image(image_request(operations))
    operations.plan = original.plan
    operations.secrets = original
    request = image_request(operations)
    operations.prepare_image(request)
    selected = PreparationStore(operations.custody).selected()
    assert selected.plan == initial.plan
    assert selected.preparation.secrets == initial.preparation.secrets
    assert digest(selected.selection) != digest(initial.selection)
    assert selected.selection.operation_id == request.operation_id
    assert created == ["test-wg", "test-ssh"]
