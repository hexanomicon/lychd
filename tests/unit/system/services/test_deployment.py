from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

from lychd.config.settings import SettingsSnapshot
from lychd.system.services.deployment import (
    DeploymentInspectionService,
    DeploymentObservationError,
    DeploymentReport,
    DeploymentRequest,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

REVISION = "a" * 40
IMAGE = "b" * 64


def unit(state: str = "inactive", *, loaded: str = "loaded", sub: str = "dead") -> dict[str, str]:
    return {
        "Id": "unit",
        "LoadState": loaded,
        "ActiveState": state,
        "SubState": sub,
        "MainPID": "42" if state == "active" and sub == "running" else "0",
        "ControlPID": "0",
        "Job": "",
        "Result": "success",
        "ExecMainStatus": "0",
    }


@pytest.mark.parametrize(("revision", "image"), [("moving", None), ("A" * 40, None), (REVISION, "unknown")])
def test_request_refuses_unpinned_identity(revision: str, image: str | None) -> None:
    with pytest.raises(ValueError, match="deployment"):
        DeploymentRequest(revision, image)


def test_request_owns_image_reference_and_normalizes_exact_id() -> None:
    request = DeploymentRequest(REVISION, "sha256:" + IMAGE)
    assert request.image_ref == "localhost/lychd:" + REVISION
    assert request.image_id == IMAGE


@pytest.mark.parametrize(
    "patch",
    [
        {"ActiveState": "activating"},
        {"ActiveState": "deactivating"},
        {"Job": "9"},
        {"ControlPID": "42"},
        {"MainPID": "42"},
        {"LoadState": "error"},
        {"SubState": "failed"},
    ],
)
def test_inactive_admission_refuses_every_ambiguous_property(patch: dict[str, str]) -> None:
    assert not DeploymentInspectionService.unit_quiescent(dict(unit(), **patch))


@pytest.mark.parametrize(
    "patch",
    [
        {"ActiveState": "reloading"},
        {"ActiveState": "activating"},
        {"Job": "9"},
        {"ControlPID": "42"},
        {"LoadState": "not-found"},
        {"SubState": "start"},
    ],
)
def test_running_admission_refuses_transitional_properties(patch: dict[str, str]) -> None:
    assert not DeploymentInspectionService.unit_active(dict(unit("active", sub="running"), **patch))


@pytest.mark.parametrize(
    ("state", "action"),
    [
        ("absent", "init"),
        ("initialized", "bind"),
        ("bound_inactive", "start"),
        ("running", "observe"),
        ("foreign_revision", "refuse"),
        ("unknown", "refuse"),
    ],
)
def test_projection_has_one_explicit_next_action(state: str, action: str) -> None:
    report = DeploymentReport(DeploymentRequest(REVISION), state=state).as_dict()
    assert report["next_action"] == action
    assert report["schema"] == "lychd.deployment"
    assert report["version"] == 1
    assert report["ok"] is (state == "running")


def world(mocker: MockerFixture, *, bound: bool = True) -> Any:
    service: Any = object.__new__(DeploymentInspectionService)
    names = {"lychd-vessel.service", "lychd-reactor.service"}
    bindings = SimpleNamespace(
        receipt_present=bound,
        runtime_units=tuple(names),
        generation="exact",
        systemd_sources=(Path("/owned/lychd-reactor.service"),),
        quadlet_sources=(),
    )
    service.scribe = mocker.Mock()
    service.scribe.inspect_owned_bindings.return_value = bindings
    service.scribe.plan_reconcile_all.return_value = SimpleNamespace(mutates=False)
    service.receipt = mocker.Mock(exists=True)
    service.operator = mocker.Mock()
    service.operator.inventory.inspect.return_value = SimpleNamespace(warnings=(), as_dict=dict)
    mocker.patch("lychd.system.services.deployment.os.geteuid", return_value=1000)
    mocker.patch.object(service, "_roots", return_value=())
    mocker.patch.object(service, "_unit_names", return_value=names)
    mocker.patch.object(service, "_unit", side_effect=lambda _name: unit() if bound else unit(loaded="not-found"))
    mocker.patch.object(
        service,
        "_footprint",
        return_value={"foreign_sources": [], "containers": [], "pods": [], "secrets": [], "running_containers": []},
    )
    settings = SettingsSnapshot(payload="{}").materialize()
    settings.server.web.image = DeploymentRequest(REVISION).image_ref
    mocker.patch.object(service, "_configuration", return_value=settings)
    mocker.patch.object(service, "_desired", return_value=([], {"lychd-reactor.service": "exact"}))
    mocker.patch.object(service, "_runtime_names", return_value=names)
    mocker.patch.object(service, "_active_names", return_value={"lychd-vessel.service"})
    mocker.patch.object(service, "_require_original_files")
    mocker.patch.object(service, "_require_known_tree")
    mocker.patch.object(service, "_image", return_value={"id": IMAGE, "revision": REVISION})
    mocker.patch.object(service, "_source_bytes", return_value=b"exact")
    mocker.patch.object(service, "_data_empty", return_value=True)
    return service


def test_initialized_original_pinned_configuration_admits_binding(mocker: MockerFixture) -> None:
    service = world(mocker, bound=False)
    # The canonical roots exist after init; there is no Scribe authority yet.
    mocker.patch.object(service, "_roots", return_value=(Path(__file__).parent,))
    assert service.inspect(DeploymentRequest(REVISION)).state == "initialized"


def test_fresh_absence_requires_no_material_and_exact_not_found_units(mocker: MockerFixture) -> None:
    service = world(mocker, bound=False)
    assert service.inspect(DeploymentRequest(REVISION)).state == "absent"


def test_bound_inactive_admits_only_start(mocker: MockerFixture) -> None:
    report = world(mocker).inspect(DeploymentRequest(REVISION, IMAGE))
    assert report.state == "bound_inactive"
    assert report.as_dict()["next_action"] == "start"


def test_active_body_is_observation_only(mocker: MockerFixture) -> None:
    service = world(mocker)
    mocker.patch.object(
        service,
        "_unit",
        side_effect=lambda name: unit("active", sub="running") if name == "lychd-vessel.service" else unit(),
    )
    mocker.patch.object(service, "run", return_value=IMAGE)
    report = service.inspect(DeploymentRequest(REVISION, IMAGE))
    assert report.state == "running"
    assert report.as_dict()["next_action"] == "observe"


@pytest.mark.parametrize(
    "property_patch",
    [
        {"ActiveState": "activating"},
        {"ActiveState": "deactivating"},
        {"ControlPID": "3"},
        {"MainPID": "3"},
        {"Job": "3"},
    ],
)
def test_mixed_or_transitional_owned_units_refuse(mocker: MockerFixture, property_patch: dict[str, str]) -> None:
    service = world(mocker)
    mocker.patch.object(service, "_unit", return_value=dict(unit(), **property_patch))
    assert service.inspect(DeploymentRequest(REVISION)).as_dict()["next_action"] == "refuse"


def test_foreign_reactor_cli_binding_is_not_replaced(mocker: MockerFixture) -> None:
    service = world(mocker)
    mocker.patch.object(service, "_source_bytes", return_value=b"foreign")
    report = service.inspect(DeploymentRequest(REVISION))
    assert report.state == "foreign_revision"
    service.scribe.plan_reconcile_all.assert_not_called()


def test_foreign_image_revision_refuses(mocker: MockerFixture) -> None:
    service = world(mocker)
    mocker.patch.object(service, "_image", return_value={"id": IMAGE, "revision": "f" * 40})
    assert service.inspect(DeploymentRequest(REVISION)).state == "foreign_revision"


def test_same_revision_different_admitted_image_id_refuses(mocker: MockerFixture) -> None:
    report = world(mocker).inspect(DeploymentRequest(REVISION, "c" * 64))
    assert report.reasons == ["admitted_image_id_mismatch"]


def test_changed_binding_generation_refuses_without_rebinding(mocker: MockerFixture) -> None:
    service = world(mocker)
    service.scribe.plan_reconcile_all.return_value = SimpleNamespace(mutates=True)
    assert service.inspect(DeploymentRequest(REVISION)).reasons == ["bindings_differ_from_declared_generation"]


def test_original_receipt_digest_is_never_rebased(mocker: MockerFixture, tmp_path: Path) -> None:
    path = tmp_path / "lychd.toml"
    path.write_text("original")
    path.chmod(0o600)
    metadata = path.stat()
    service: Any = object.__new__(DeploymentInspectionService)
    service.receipt = mocker.Mock()
    service.receipt.load.return_value = SimpleNamespace(
        files=(
            SimpleNamespace(
                path=str(path),
                device=metadata.st_dev,
                inode=metadata.st_ino,
                digest="sha256:" + hashlib.sha256(b"original").hexdigest(),
            ),
        )
    )
    mocker.patch("lychd.system.services.deployment.constants.PATH_LYCHD_TOML", path)
    mocker.patch.object(service, "_roots", return_value=())
    service._require_original_files()
    path.write_text("image-line-edited")
    with pytest.raises(DeploymentObservationError, match="created_file_digest_changed"):
        service._require_original_files()
    service.receipt.record.assert_not_called()


def test_old_default_image_configuration_refuses(mocker: MockerFixture, tmp_path: Path) -> None:
    from lychd.system.services.codex import _render_default_settings_toml

    path = tmp_path / "lychd.toml"
    path.write_text(_render_default_settings_toml(SettingsSnapshot(payload="{}").materialize()))
    path.chmod(0o600)
    service: Any = object.__new__(DeploymentInspectionService)
    mocker.patch.object(service, "_require_original_files")
    metadata = path.stat()
    service.receipt = mocker.Mock()
    service.receipt.load.return_value = SimpleNamespace(
        files=(
            SimpleNamespace(
                path=str(path),
                device=metadata.st_dev,
                inode=metadata.st_ino,
                digest="sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
            ),
        )
    )
    mocker.patch("lychd.system.services.deployment.constants.PATH_LYCHD_TOML", path)
    with pytest.raises(DeploymentObservationError, match="configuration_outside_deployment_profile"):
        service._configuration(DeploymentRequest(REVISION))


def test_one_active_owned_unit_with_other_inactive_refuses(mocker: MockerFixture) -> None:
    service = world(mocker)
    mocker.patch.object(
        service,
        "_unit",
        side_effect=lambda name: unit("active", sub="running") if name == "lychd-reactor.service" else unit(),
    )
    assert service.inspect(DeploymentRequest(REVISION)).reasons == ["mixed_transitional_or_unknown_units"]


def test_nonempty_unbound_database_is_never_adopted(mocker: MockerFixture) -> None:
    service = world(mocker, bound=False)
    mocker.patch.object(service, "_roots", return_value=(Path(__file__).parent,))
    mocker.patch.object(service, "_data_empty", return_value=False)
    assert service.inspect(DeploymentRequest(REVISION)).reasons == ["unbound_database_not_empty"]


def test_unreceipted_material_is_never_adopted(mocker: MockerFixture) -> None:
    service = world(mocker)
    service.receipt.exists = False
    assert service.inspect(DeploymentRequest(REVISION)).reasons == ["material_without_initialization_authority"]


def test_foreign_binding_files_are_preserved_and_refused(mocker: MockerFixture) -> None:
    service = world(mocker)
    mocker.patch.object(
        service,
        "_footprint",
        return_value={
            "foreign_sources": ["/shared/lychd-foreign.service"],
            "containers": [],
            "pods": [],
            "secrets": [],
            "running_containers": [],
        },
    )
    assert service.inspect(DeploymentRequest(REVISION)).reasons == ["foreign_binding_source"]
    service.scribe.plan_reconcile_all.assert_not_called()


def test_malformed_or_duplicate_unit_properties_refuse(mocker: MockerFixture) -> None:
    service = object.__new__(DeploymentInspectionService)
    mocker.patch.object(service, "run", return_value="Id=lychd-vessel.service\nId=lychd-vessel.service\n")
    with pytest.raises(DeploymentObservationError, match="malformed_unit_properties"):
        service._unit("lychd-vessel.service")


def test_native_acceptance_failure_is_nonzero_without_secret_output(mocker: MockerFixture) -> None:
    from click.testing import CliRunner

    from lychd.cli.operator import status

    report = DeploymentReport(
        DeploymentRequest(REVISION, verify=True),
        state="running",
        checks=[{"name": "api.access", "ok": False, "detail": "unavailable"}],
    )
    mocker.patch("lychd.system.services.deployment.inspect_deployment", return_value=report)
    result = CliRunner().invoke(status, ["--json", "--deployment-revision", REVISION, "--deployment-verify"])
    assert result.exit_code == 1
    assert '"ok": false' in result.output


def test_path_units_use_their_actual_waiting_state_and_common_properties(mocker: MockerFixture) -> None:
    service = object.__new__(DeploymentInspectionService)
    probe = mocker.patch.object(
        service,
        "run",
        return_value="Id=lychd-reactor.path\nLoadState=loaded\nActiveState=active\nSubState=waiting\nJob=\n",
    )
    observed = service._unit("lychd-reactor.path")
    assert service.unit_active(observed)
    assert "--property=MainPID" not in probe.call_args.args
    assert "--property=ExecMainStatus" not in probe.call_args.args
