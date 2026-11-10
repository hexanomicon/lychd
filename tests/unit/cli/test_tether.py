"""Bootstrap-safe closed native grammar, with no private-key option or callback."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from lychd.__main__ import cli
from lychd.cli.binding import BindingCommandSession
from lychd.cli.tether import tether
from lychd.config import QuadletConfig
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings import SettingsSnapshot
from lychd.config.settings.root import Settings
from lychd.domain.tether.models import CompiledTetherPlan
from lychd.extensions.builtin.tether.config import TetherSettings
from lychd.extensions.host import assemble_extensions
from lychd.system.services.binding_preflight import BindingPreflightReport, BindingPreflightService
from lychd.system.services.tether import composition
from tests.unit.system.services.test_tether_operations import make_plan

if TYPE_CHECKING:
    from lychd.system.services.tether.secrets import TetherSecrets


def test_closed_native_tether_grammar_and_no_extra_roots() -> None:
    runner = CliRunner()
    root = runner.invoke(cli, ["--help"])
    assert root.exit_code == 0
    assert "run" in root.output
    group = runner.invoke(cli, ["run", "tether", "--help"])
    assert group.exit_code == 0
    assert set(tether.commands) == {"prepare", "enroll", "inspect", "revoke"}
    for command in ("prepare", "enroll", "inspect", "revoke"):
        assert command in group.output
    assert runner.invoke(cli, ["run", "arbitrary"]).exit_code == 2
    assert runner.invoke(cli, ["tether-close"]).exit_code == 2
    assert runner.invoke(cli, ["run", "tether", "execute"]).exit_code == 2


def test_enrollment_accepts_only_public_client_keys_and_no_path_unit_or_argv() -> None:
    help_result = CliRunner().invoke(cli, ["run", "tether", "enroll", "--help"])
    assert help_result.exit_code == 0
    assert "--wireguard-public-key" in help_result.output
    assert "--ssh-public-key" in help_result.output
    assert "--private-key" not in help_result.output
    for forbidden in ("--command", "--unit", "--path", "--image"):
        assert forbidden not in help_result.output


def test_declared_inspection_compiles_before_required_metadata_or_native_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = make_plan()
    envelope = expected.envelope
    settings = Settings.model_validate({"extensions": {"builtins": ["tether"]}})
    rune = TetherSettings(
        installation_id=envelope.installation_id,
        interface=envelope.interface,
        server_address=str(envelope.server_address),
        udp_bind_address=str(envelope.udp_bind_address),
        udp_port=envelope.udp_port,
        advertised_endpoint=envelope.advertised_endpoint,
        quadlet=QuadletConfig(image=envelope.image),
        wireguard_secret=envelope.wireguard_secret,
        ssh_host_secret=envelope.ssh_host_secret,
        ssh_port=envelope.ssh_port,
    )
    session = BindingCommandSession(
        settings_snapshot=SettingsSnapshot.capture(settings),
        extensions=assemble_extensions(settings),
        runes=RuneRegistry((rune,)),
        soulstones=(),
        portals=(),
        preflight_service=BindingPreflightService(),
        preflight=BindingPreflightReport(issues=(), foundation=None),
    )
    inspect_session = MagicMock(return_value=session)
    monkeypatch.setattr(BindingCommandSession, "inspect", inspect_session)
    require_ready = MagicMock(side_effect=AssertionError("Host readiness is not needed for declared intent"))
    monkeypatch.setattr(BindingPreflightReport, "require_ready", require_ready)
    effects: list[MagicMock] = []
    for name in (
        "build_tether_operations",
        "preparation_service",
        "TetherCustody",
        "TetherSecrets",
        "LifecycleLock",
        "LifecycleReceiptStore",
        "SubprocessRunner",
    ):
        forbidden = MagicMock(
            side_effect=AssertionError("Declared inspection must not acquire native effect authority")
        )
        monkeypatch.setattr(composition, name, forbidden)
        effects.append(forbidden)
    monkeypatch.setattr(composition, "PATH_CODEX_ROOT", tmp_path / "absent-codex")
    monkeypatch.setattr(composition, "PATH_CRYPT_ROOT", tmp_path / "absent-crypt")
    monkeypatch.setattr(composition, "PATH_CACHE_ROOT", tmp_path / "absent-cache")
    application = ModuleType("lychd.app")
    create_app = MagicMock(side_effect=AssertionError("Declared inspection must not assemble ASGI"))
    monkeypatch.setattr(application, "create_app", create_app, raising=False)
    monkeypatch.setitem(sys.modules, "lychd.app", application)

    result = CliRunner().invoke(cli, ["run", "tether", "inspect", "--declared"])

    assert result.exit_code == 0, result.output
    assert CompiledTetherPlan.model_validate_json(result.output) == expected
    assert "SecretData" not in result.output
    assert "PrivateKey" not in result.output
    assert not list(tmp_path.iterdir())
    inspect_session.assert_called_once_with()
    require_ready.assert_not_called()
    create_app.assert_not_called()
    for effect in effects:
        effect.assert_not_called()


@pytest.mark.parametrize(
    "missing", ["--installation-id", "--operation-id", "--expected-generation", "--envelope-digest", "--intent-digest"]
)
def test_normal_inspection_still_requires_every_explicit_precondition(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    options = {
        "--installation-id": "00000000-0000-0000-0000-000000000001",
        "--operation-id": "00000000-0000-0000-0000-000000000002",
        "--expected-generation": "0",
        "--envelope-digest": "d" * 64,
        "--intent-digest": "d" * 64,
    }
    operations = MagicMock(side_effect=AssertionError("Missing preconditions must precede operations"))
    monkeypatch.setattr(composition, "build_tether_operations", operations)
    arguments = ["run", "tether", "inspect"]
    for option, value in options.items():
        if option != missing:
            arguments.extend((option, value))

    result = CliRunner().invoke(cli, arguments)

    assert result.exit_code == 2
    assert f"Missing option '{missing}'" in result.output
    operations.assert_not_called()


def test_declared_inspection_suppresses_invalid_configuration_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    private_validation_input = "synthetic-private-validation-value"
    monkeypatch.setattr(
        composition, "declared_tether_plan", MagicMock(side_effect=ValueError(private_validation_input))
    )

    result = CliRunner().invoke(cli, ["run", "tether", "inspect", "--declared"])

    assert result.exit_code == 1
    assert "Declared Tether plan is unavailable" in result.output
    assert private_validation_input not in result.output


def test_inspection_help_remains_bootstrap_safe_with_declared_option(monkeypatch: pytest.MonkeyPatch) -> None:
    declared = MagicMock(side_effect=AssertionError("Help must not load declaration"))
    monkeypatch.setattr(composition, "declared_tether_plan", declared)

    result = CliRunner().invoke(cli, ["run", "tether", "inspect", "--help"])

    assert result.exit_code == 0
    assert "--declared" in result.output
    declared.assert_not_called()


def test_prepared_inspection_is_metadata_only_before_binding_or_first_peer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lychd.system.services.tether.custody import PreparationStore, TetherCustody
    from lychd.system.services.tether.models import PreparedInspection, digest
    from tests.unit.system.services.test_tether_operations import FixtureTetherCustody, image_stack

    operations, original, _, created = image_stack(tmp_path)
    before = PreparationStore(operations.custody).selected()
    # Fresh CLI custody must attest with the same filesystem identity adapter as preparation.
    monkeypatch.setattr(composition, "TetherCustody", FixtureTetherCustody)
    monkeypatch.setattr(composition, "PATH_CODEX_ROOT", operations.custody.codex_root)
    monkeypatch.setattr(composition, "PATH_CRYPT_ROOT", operations.custody.crypt_root)
    monkeypatch.setattr(composition.os, "geteuid", lambda: 1000)

    def preparation(plan: CompiledTetherPlan, *, podman_bin: str | None = None) -> TetherSecrets:
        assert plan == original.plan
        assert podman_bin is None
        return original

    monkeypatch.setattr(composition, "preparation_service", preparation)
    initialize = MagicMock(side_effect=AssertionError("Metadata must not initialize custody"))
    assemble = MagicMock(side_effect=AssertionError("Metadata must not assemble native mutations"))
    monkeypatch.setattr(TetherCustody, "initialize", initialize)
    monkeypatch.setattr(composition, "build_tether_operations", assemble)
    result = CliRunner().invoke(cli, ["run", "tether", "inspect", "--prepared"])
    assert result.exit_code == 0, result.output
    view = PreparedInspection.model_validate_json(result.output)
    assert view.preparation_digest == digest(before.selection)
    assert view.envelope_digest == original.plan.envelope_digest
    assert view.peer_generation == 0
    assert view.preparation == before.preparation
    assert "synthetic-server-secret" not in result.output
    assert operations.custody.read("private", "current-preparation.json") is None
    assert created == ["test-wg", "test-ssh"]
    initialize.assert_not_called()
    assemble.assert_not_called()


def test_prepare_dispatch_keeps_original_request_hash_and_uses_distinct_image_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lychd.system.services.tether.models import PrepareImageRequest, PrepareRequest, digest
    from tests.unit.system.services.test_tether_operations import make_plan

    plan = make_plan()
    native = MagicMock()
    native.prepare.return_value = plan
    native.prepare_image.return_value = plan
    monkeypatch.setattr(composition, "build_tether_operations", MagicMock(return_value=native))
    arguments = [
        "run",
        "tether",
        "prepare",
        "--installation-id",
        "00000000-0000-0000-0000-000000000001",
        "--operation-id",
        "00000000-0000-0000-0000-000000000002",
        "--expected-generation",
        "0",
        "--envelope-digest",
        "a" * 64,
    ]
    assert CliRunner().invoke(cli, arguments).exit_code == 0
    original = native.prepare.call_args.args[0]
    assert isinstance(original, PrepareRequest)
    assert digest(original) == "9dc1ca3b0521e972d5911a5eb41f3ee204a94282bfb568569188685fa4bea197"
    assert "expected_preparation_digest" not in original.model_dump()
    assert CliRunner().invoke(cli, [*arguments, "--expected-preparation-digest", "b" * 64]).exit_code == 0
    image = native.prepare_image.call_args.args[0]
    assert isinstance(image, PrepareImageRequest)
    assert image.kind == "prepare-image"
    assert image.expected_preparation_digest == "b" * 64
    assert set(tether.commands) == {"prepare", "enroll", "inspect", "revoke"}


def test_prepared_inspection_never_exposes_invalid_custody_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        composition, "prepared_tether_inspection", MagicMock(side_effect=ValueError("synthetic-private-key"))
    )
    result = CliRunner().invoke(cli, ["run", "tether", "inspect", "--prepared"])
    assert result.exit_code == 1
    assert "Prepared Tether metadata is unavailable" in result.output
    assert "synthetic-private-key" not in result.output
