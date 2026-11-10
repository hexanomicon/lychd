"""Public deletion previews over real observation and retirement planning."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from lychd.cli.deletion import delete_installation
from lychd.system.operator.inventory import OperatorInventoryService
from lychd.system.operator.process import ProcessResult
from lychd.system.operator.retirement import OwnedUnitRetirementService
from lychd.system.operator.storage import MountTreeObservation, StorageInventoryService
from lychd.system.operator.units import OwnedUnitInventoryService
from lychd.system.services.lifecycle.bindings import BindingLifecycleService
from lychd.system.services.lifecycle.deletion_checkpoint import DeletionCheckpointStore
from lychd.system.services.lifecycle.deletion_composition import DeletionServices
from lychd.system.services.lifecycle.deletion_execution import DeletionExecutor
from lychd.system.services.lifecycle.deletion_models import DeletionPaths, DeletionStage
from lychd.system.services.lifecycle.deletion_planning import DeletionPlanner
from lychd.system.services.lifecycle.deletion_storage import CommandBtrfsSubvolumeProbe
from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore
from lychd.system.services.lifecycle.trees import ManagedTreeInspection, ManagedTreeService
from lychd.system.services.scribe import OwnedBindings, ScribeService
from lychd.system.services.scribe.authority import BindingAuthority
from lychd.system.services.scribe.models import OwnershipManifest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


@dataclass
class _ShowRunner:
    states: dict[str, tuple[str, str, str]]
    calls: list[tuple[tuple[str, ...], float]] = field(default_factory=list)

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        self.calls.append((argv, timeout_s))
        assert argv[:2] == ("/usr/bin/systemctl", "--user")
        action = argv[2]
        if action == "show":
            assert argv[4:] == (
                "--property=LoadState",
                "--property=ActiveState",
                "--property=UnitFileState",
            )
            assert timeout_s == 3.0
            load, active, unit_file = self.states[argv[3]]
            return ProcessResult(argv, 0, f"LoadState={load}\nActiveState={active}\nUnitFileState={unit_file}\n")
        assert action in {"stop", "disable"}
        assert timeout_s == 30.0
        for name in argv[3:]:
            load, active, unit_file = self.states[name]
            self.states[name] = (
                load,
                "inactive" if action == "stop" else active,
                "disabled" if action == "disable" else unit_file,
            )
        return ProcessResult(argv, 0)


@dataclass
class _PublicDeletion:
    services: DeletionServices
    runner: _ShowRunner
    scribe: MagicMock
    trees: MagicMock
    checkpoint: MagicMock

    def assert_no_effects(self) -> None:
        assert self.runner.calls
        assert [argv for argv, _ in self.runner.calls if argv[2] != "show"] == []
        self.scribe.clear_owned_bindings.assert_not_called()
        self.scribe.release_owned_binding_authority.assert_not_called()
        self.trees.remove.assert_not_called()
        self.checkpoint.record.assert_not_called()


def _absent_root(root: Path, **_: object) -> ManagedTreeInspection:
    return ManagedTreeInspection(root=root, exists=False, removable=True, detail="already absent")


def _public_deletion(
    tmp_path: Path,
    mocker: MockerFixture,
    *,
    states: dict[str, tuple[str, str, str]],
    owned_scribe: ScribeService | None = None,
) -> _PublicDeletion:
    """Observe exact units with inert manager, deletion, and absent-root ports."""
    paths = DeletionPaths(
        codex_root=tmp_path / "codex",
        crypt_root=tmp_path / "crypt",
        cache_root=tmp_path / "cache",
        postgres_data=tmp_path / "crypt" / "postgres" / "data",
        lifecycle_receipt=tmp_path / "codex" / ".lychd-lifecycle.json",
    )
    scribe = mocker.MagicMock(spec=ScribeService)
    if owned_scribe is None:
        scribe.ownership_path = tmp_path / "bindings" / ".lychd-owned.json"
        scribe.inspect_owned_bindings.return_value = OwnedBindings(
            receipt_present=True,
            generation="fixture-generation",
            systemd_sources=tuple(tmp_path / "bindings" / name for name in states),
            runtime_units=tuple(states),
        )
    else:
        scribe.ownership_path = owned_scribe.ownership_path
        scribe.inspect_owned_bindings.side_effect = owned_scribe.inspect_owned_bindings
    runner = _ShowRunner(states)
    units = OwnedUnitInventoryService(scribe, runner, systemctl_bin="/usr/bin/systemctl")
    inventory = mocker.MagicMock(spec=OperatorInventoryService)
    inventory.owned_units.side_effect = units.inspect
    retirement = OwnedUnitRetirementService(
        inventory=inventory,
        runner=runner,
        systemctl_bin="/usr/bin/systemctl",
    )
    storage = mocker.MagicMock(spec=StorageInventoryService)
    storage.observe_under.return_value = MountTreeObservation(roots=paths.dedicated_roots)
    root_authority = mocker.MagicMock(spec=LifecycleReceiptStore)
    root_authority.path = paths.lifecycle_receipt
    root_authority.created_subvolume.return_value = None
    checkpoint = mocker.MagicMock(spec=DeletionCheckpointStore)
    checkpoint.path = paths.codex_root / ".lychd-del-state.json"
    checkpoint.exists = False
    checkpoint.load.return_value = None
    trees = mocker.MagicMock(spec=ManagedTreeService)
    trees.inspect.side_effect = _absent_root
    planner = DeletionPlanner(
        paths=paths,
        retirement=retirement,
        scribe=scribe,
        storage=storage,
        subvolumes=mocker.MagicMock(spec=CommandBtrfsSubvolumeProbe),
        checkpoint=checkpoint,
        trees=trees,
        root_authority=root_authority,
        umount_bin=None,
        btrfs_bin=None,
        sudo_bin=None,
    )
    executor = DeletionExecutor(
        planner=planner,
        retirement=retirement,
        bindings=BindingLifecycleService(scribe, runner=runner, systemctl_bin="/usr/bin/systemctl"),
        checkpoint=checkpoint,
        trees=trees,
        lock_factory=nullcontext,
    )
    services = DeletionServices(planner, executor)
    mocker.patch("lychd.cli.deletion.build_deletion_services", return_value=services)
    return _PublicDeletion(services, runner, scribe, trees, checkpoint)


@pytest.mark.parametrize("option", ["--dry-run", "--yes"])
@pytest.mark.parametrize(
    ("load_state", "active_state", "unit_file_state", "reason"),
    [
        ("loaded", "failed", "disabled", "failed state"),
        ("masked", "inactive", "masked", "unsupported unit-file state"),
        ("masked", "inactive", "masked-runtime", "unsupported unit-file state"),
    ],
    ids=["failed", "masked", "masked-runtime"],
)
def test_del_refuses_failed_or_masked_unit_before_any_effect(
    tmp_path: Path,
    mocker: MockerFixture,
    option: str,
    load_state: str,
    active_state: str,
    unit_file_state: str,
    reason: str,
) -> None:
    fixture = _public_deletion(
        tmp_path,
        mocker,
        states={"lychd-probe.service": (load_state, active_state, unit_file_state)},
    )

    result = CliRunner().invoke(delete_installation, [option])

    assert result.exit_code == 2, result.output
    assert "QUIESCE" in result.output
    assert "BLOCKED" in result.output
    assert "lychd-probe.service" in result.output
    assert reason in result.output
    assert "unit is already inactive" not in result.output
    if unit_file_state.startswith("masked"):
        assert f"lychd-probe.service ({unit_file_state})" in result.output
    assert fixture.services.planner.plan().first_blocked_stage is DeletionStage.QUIESCE
    fixture.assert_no_effects()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("load_state", "unit_file_state"),
    [("loaded", "disabled"), ("loaded", "generated"), ("loaded", "static"), ("not-found", "")],
    ids=["disabled", "generated", "static", "absent"],
)
def test_del_inactive_supported_unit_has_unblocked_effect_free_preview(
    tmp_path: Path,
    mocker: MockerFixture,
    load_state: str,
    unit_file_state: str,
) -> None:
    fixture = _public_deletion(
        tmp_path,
        mocker,
        states={"lychd-probe.service": (load_state, "inactive", unit_file_state)},
    )

    result = CliRunner().invoke(delete_installation, ["--dry-run"])

    assert result.exit_code == 0, result.output
    assert "unit is already inactive" in result.output
    assert "No changes made." in result.output
    plan = fixture.services.planner.plan()
    assert plan.first_blocked_stage is None
    assert plan.unit_plan is not None
    assert plan.unit_plan.stop_units == plan.unit_plan.disable_units == ()
    fixture.assert_no_effects()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("option", ["--dry-run", "--yes"])
@pytest.mark.parametrize("active_peer", [False, True], ids=["indirect-only", "active-enabled-peer"])
def test_del_refuses_receipt_owned_indirect_unit_before_any_effect(
    tmp_path: Path,
    mocker: MockerFixture,
    option: str,
    *,
    active_peer: bool,
) -> None:
    quadlet = tmp_path / "quadlet"
    systemd = tmp_path / "systemd"
    quadlet.mkdir(mode=0o700)
    systemd.mkdir(mode=0o700)
    plain_units = {
        "lychd-indirect.service": (
            "[Unit]\nDescription=Indirect retirement fixture\n"
            "[Service]\nExecStart=/usr/bin/true\n"
            "[Install]\nAlso=lychd-unowned.service\n"
        ),
    }
    states = {"lychd-indirect.service": ("loaded", "inactive", "indirect")}
    if active_peer:
        plain_units["lychd-peer.service"] = (
            "[Unit]\nDescription=Active retirement peer\n"
            "[Service]\nExecStart=/usr/bin/true\n"
            "[Install]\nWantedBy=default.target\n"
        )
        states["lychd-peer.service"] = ("loaded", "active", "enabled")
    for name, content in plain_units.items():
        (systemd / name).write_text(content)
    owned_scribe = ScribeService(output_dir=quadlet, systemd_dir=systemd)
    owned_scribe.ownership_path.write_bytes(
        BindingAuthority.encode(OwnershipManifest(version=1, systemd=tuple(plain_units)))
    )
    owned_scribe.ownership_path.chmod(0o600)
    owned = owned_scribe.inspect_owned_bindings()
    assert owned.receipt_present
    assert owned.runtime_units == tuple(sorted(plain_units))
    assert not owned_scribe.plan_reconcile_all([], plain_units=plain_units).mutates
    original_files = {path: path.read_bytes() for path in (*owned.systemd_sources, owned_scribe.ownership_path)}
    fixture = _public_deletion(tmp_path, mocker, states=states, owned_scribe=owned_scribe)

    result = CliRunner().invoke(delete_installation, [option])

    assert result.exit_code == 2, result.output
    assert "QUIESCE" in result.output
    assert "BLOCKED" in result.output
    fixture.assert_no_effects()
    assert "unsupported unit-file state: lychd-indirect.service (indirect)" in result.output
    assert fixture.services.planner.plan().first_blocked_stage is DeletionStage.QUIESCE
    assert owned_scribe.inspect_owned_bindings() == owned
    assert {path: path.read_bytes() for path in original_files} == original_files
    assert not any(root.exists() for root in fixture.services.planner.paths.dedicated_roots)


@pytest.mark.parametrize("option", ["--dry-run", "--yes"])
@pytest.mark.parametrize("active_peer", [False, True], ids=["bad-setting-only", "active-enabled-peer"])
def test_del_refuses_receipt_owned_bad_setting_before_any_effect(
    tmp_path: Path,
    mocker: MockerFixture,
    option: str,
    *,
    active_peer: bool,
) -> None:
    quadlet = tmp_path / "quadlet"
    systemd = tmp_path / "systemd"
    quadlet.mkdir(mode=0o700)
    systemd.mkdir(mode=0o700)
    plain_units = {
        "lychd-badsetting.service": (
            "[Unit]\nDescription=Invalid service command fixture\n"
            "[Service]\nType=simple\n"
            "[Install]\nWantedBy=default.target\n"
        ),
    }
    states = {"lychd-badsetting.service": ("bad-setting", "inactive", "disabled")}
    if active_peer:
        plain_units["lychd-peer.service"] = (
            "[Unit]\nDescription=Active retirement peer\n"
            "[Service]\nExecStart=/usr/bin/true\n"
            "[Install]\nWantedBy=default.target\n"
        )
        states["lychd-peer.service"] = ("loaded", "active", "enabled")
    for name, content in plain_units.items():
        (systemd / name).write_text(content)
    owned_scribe = ScribeService(output_dir=quadlet, systemd_dir=systemd)
    owned_scribe.ownership_path.write_bytes(
        BindingAuthority.encode(OwnershipManifest(version=1, systemd=tuple(plain_units)))
    )
    owned_scribe.ownership_path.chmod(0o600)
    owned = owned_scribe.inspect_owned_bindings()
    assert owned.receipt_present
    assert owned.runtime_units == tuple(sorted(plain_units))
    assert not owned_scribe.plan_reconcile_all([], plain_units=plain_units).mutates
    original_files = {path: path.read_bytes() for path in (*owned.systemd_sources, owned_scribe.ownership_path)}
    fixture = _public_deletion(tmp_path, mocker, states=states, owned_scribe=owned_scribe)

    result = CliRunner().invoke(delete_installation, [option])

    assert result.exit_code == 2, result.output
    assert "QUIESCE" in result.output
    assert "BLOCKED" in result.output
    assert "load state: lychd-badsetting.service (bad-setting)" in result.output
    assert "unit is already inactive" not in result.output
    fixture.assert_no_effects()
    assert fixture.services.planner.plan().first_blocked_stage is DeletionStage.QUIESCE
    assert owned_scribe.inspect_owned_bindings() == owned
    assert {path: path.read_bytes() for path in original_files} == original_files
    assert not any(root.exists() for root in fixture.services.planner.paths.dedicated_roots)


pytestmark = pytest.mark.usefixtures("persistent_identity_observer")
