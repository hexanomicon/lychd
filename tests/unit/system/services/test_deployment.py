from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

from lychd.config.settings import SettingsSnapshot
from lychd.system.schemas import QuadletContainer
from lychd.system.services.deployment import (
    DeploymentInspectionService,
    DeploymentObservationError,
    DeploymentReport,
    DeploymentRequest,
)
from lychd.system.services.scribe import OwnedBindings

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

REVISION = "a" * 40
IMAGE = "b" * 64


def unit(
    state: str = "inactive", *, loaded: str = "loaded", sub: str = "dead", name: str = "lychd-vessel.service"
) -> dict[str, str]:
    return {
        "Id": name,
        "FragmentPath": "",
        "SourcePath": "",
        "DropInPaths": "",
        "NeedDaemonReload": "no",
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


def world(mocker: MockerFixture, tmp_path: Path, *, bound: bool = True) -> Any:
    service: Any = object.__new__(DeploymentInspectionService)
    names = {"lychd-vessel.service", "lychd-reactor.service"}
    quadlet = tmp_path / "quadlet" / "lychd-vessel.container"
    reactor = tmp_path / "user" / "lychd-reactor.service"
    generated = tmp_path / "runtime" / "systemd" / "generator" / "lychd-vessel.service"
    for path in (quadlet, reactor, generated):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("exact")
        path.chmod(0o600)
    mocker.patch("lychd.system.services.deployment.constants.PATH_SYSTEMD_USER_GENERATOR_DIR", generated.parent)
    bindings = OwnedBindings(
        receipt_present=bound,
        runtime_units=tuple(sorted(names)) if bound else (),
        generation="exact" if bound else None,
        systemd_sources=(reactor,) if bound else (),
        quadlet_sources=(quadlet,) if bound else (),
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

    def observe(name: str) -> dict[str, str]:
        result = unit(loaded="loaded" if bound else "not-found", name=name)
        if bound:
            result["FragmentPath"] = str(generated if name == "lychd-vessel.service" else reactor)
            result["SourcePath"] = str(quadlet) if name == "lychd-vessel.service" else ""
        return result

    mocker.patch.object(service, "observe_unit", side_effect=observe)
    mocker.patch.object(
        service,
        "_footprint",
        return_value={"foreign_sources": [], "containers": [], "pods": [], "secrets": [], "running_containers": []},
    )
    settings = SettingsSnapshot(payload="{}").materialize()
    settings.server.web.image = DeploymentRequest(REVISION).image_ref
    mocker.patch.object(service, "_configuration", return_value=settings)
    mocker.patch.object(
        service,
        "desired_bindings",
        return_value=(
            [QuadletContainer(description="Vessel", image=settings.server.web.image, container_name="lychd-vessel")],
            {"lychd-reactor.service": "exact"},
        ),
    )
    mocker.patch.object(service, "_require_original_files")
    mocker.patch.object(service, "_require_known_tree")
    mocker.patch.object(service, "_image", return_value={"id": IMAGE, "revision": REVISION})
    mocker.patch.object(service, "_source_bytes", return_value=b"exact")
    mocker.patch.object(service, "_data_empty", return_value=True)
    return service


def test_initialized_original_pinned_configuration_admits_binding(mocker: MockerFixture, tmp_path: Path) -> None:
    service = world(mocker, tmp_path, bound=False)
    # The canonical roots exist after init; there is no Scribe authority yet.
    mocker.patch.object(service, "_roots", return_value=(Path(__file__).parent,))
    assert service.inspect(DeploymentRequest(REVISION)).state == "initialized"


def test_fresh_absence_requires_no_material_and_exact_not_found_units(mocker: MockerFixture, tmp_path: Path) -> None:
    service = world(mocker, tmp_path, bound=False)
    assert service.inspect(DeploymentRequest(REVISION)).state == "absent"


def test_bound_inactive_admits_only_start(mocker: MockerFixture, tmp_path: Path) -> None:
    report = world(mocker, tmp_path).inspect(DeploymentRequest(REVISION, IMAGE))
    assert report.state == "bound_inactive"
    assert report.as_dict()["next_action"] == "start"


def test_active_body_is_observation_only(mocker: MockerFixture, tmp_path: Path) -> None:
    service = world(mocker, tmp_path)
    original = service.observe_unit.side_effect

    def active_observation(name: str) -> dict[str, str]:
        observed: dict[str, str] = original(name)
        if name == "lychd-vessel.service":
            observed.update(ActiveState="active", SubState="running", MainPID="42")
        return observed

    mocker.patch.object(
        service,
        "observe_unit",
        side_effect=active_observation,
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
def test_mixed_or_transitional_owned_units_refuse(
    mocker: MockerFixture, property_patch: dict[str, str], tmp_path: Path
) -> None:
    service = world(mocker, tmp_path)
    original = service.observe_unit.side_effect

    def transitional(name: str) -> dict[str, str]:
        return dict(original(name), **property_patch)

    mocker.patch.object(service, "observe_unit", side_effect=transitional)
    assert service.inspect(DeploymentRequest(REVISION)).as_dict()["next_action"] == "refuse"


def test_foreign_reactor_cli_binding_is_not_replaced(mocker: MockerFixture, tmp_path: Path) -> None:
    service = world(mocker, tmp_path)
    mocker.patch.object(service, "_source_bytes", return_value=b"foreign")
    report = service.inspect(DeploymentRequest(REVISION))
    assert report.state == "foreign_revision"
    service.scribe.plan_reconcile_all.assert_not_called()


def test_foreign_image_revision_refuses(mocker: MockerFixture, tmp_path: Path) -> None:
    service = world(mocker, tmp_path)
    mocker.patch.object(service, "_image", return_value={"id": IMAGE, "revision": "f" * 40})
    assert service.inspect(DeploymentRequest(REVISION)).state == "foreign_revision"


def test_same_revision_different_admitted_image_id_refuses(mocker: MockerFixture, tmp_path: Path) -> None:
    report = world(mocker, tmp_path).inspect(DeploymentRequest(REVISION, "c" * 64))
    assert report.reasons == ["admitted_image_id_mismatch"]


def test_changed_binding_generation_refuses_without_rebinding(mocker: MockerFixture, tmp_path: Path) -> None:
    service = world(mocker, tmp_path)
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
    from tomlkit import dumps

    path = tmp_path / "lychd.toml"
    path.write_text(dumps(SettingsSnapshot(payload="{}").materialize().model_dump(mode="json", exclude_none=True)))
    path.chmod(0o600)
    service: Any = object.__new__(DeploymentInspectionService)
    mocker.patch.object(service, "_require_original_files")
    service.receipt = mocker.Mock()
    service.receipt.read_original_file.return_value = path.read_bytes()
    metadata = path.stat()
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


def test_one_active_owned_unit_with_other_inactive_refuses(mocker: MockerFixture, tmp_path: Path) -> None:
    service = world(mocker, tmp_path)
    original = service.observe_unit.side_effect

    def one_active(name: str) -> dict[str, str]:
        observed: dict[str, str] = original(name)
        if name == "lychd-reactor.service":
            observed.update(ActiveState="active", SubState="running", MainPID="42")
        return observed

    mocker.patch.object(
        service,
        "observe_unit",
        side_effect=one_active,
    )
    assert service.inspect(DeploymentRequest(REVISION)).reasons == ["mixed_transitional_or_unknown_units"]


def test_nonempty_unbound_database_is_never_adopted(mocker: MockerFixture, tmp_path: Path) -> None:
    service = world(mocker, tmp_path, bound=False)
    mocker.patch.object(service, "_roots", return_value=(Path(__file__).parent,))
    mocker.patch.object(service, "_data_empty", return_value=False)
    assert service.inspect(DeploymentRequest(REVISION)).reasons == ["unbound_database_not_empty"]


def test_unreceipted_material_is_never_adopted(mocker: MockerFixture, tmp_path: Path) -> None:
    service = world(mocker, tmp_path)
    service.receipt.exists = False
    assert service.inspect(DeploymentRequest(REVISION)).reasons == ["material_without_initialization_authority"]


def test_foreign_binding_files_are_preserved_and_refused(mocker: MockerFixture, tmp_path: Path) -> None:
    service = world(mocker, tmp_path)
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
        service.observe_unit("lychd-vessel.service")


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
        return_value="Id=lychd-reactor.path\nLoadState=loaded\nActiveState=active\nSubState=waiting\nJob=\nFragmentPath=/owned/lychd-reactor.path\nSourcePath=\nDropInPaths=\nNeedDaemonReload=no\n",
    )
    observed = service.observe_unit("lychd-reactor.path")
    assert service.unit_active(observed)
    assert "--property=MainPID" not in probe.call_args.args
    assert "--property=ExecMainStatus" not in probe.call_args.args


@pytest.mark.parametrize(
    ("name", "changed"),
    [
        ("lychd-vessel.service", {"DropInPaths": "/run/user/1000/systemd/user/lychd-vessel.service.d/override.conf"}),
        ("lychd-vessel.service", {"DropInPaths": "/home/operator/.config/systemd/user/service.d/generic.conf"}),
        ("lychd-reactor.service", {"DropInPaths": "/run/user/1000/systemd/user/service.d/generic.conf"}),
        ("lychd-reactor.service", {"NeedDaemonReload": "yes"}),
        ("lychd-vessel.service", {"NeedDaemonReload": "unknown"}),
        ("lychd-reactor.service", {"FragmentPath": "/run/user/1000/systemd/user/lychd-reactor.service"}),
        ("lychd-reactor.service", {"SourcePath": "/foreign/lychd-reactor.service"}),
        ("lychd-vessel.service", {"SourcePath": "/foreign/lychd-vessel.container"}),
        ("lychd-vessel.service", {"FragmentPath": "/run/user/1000/systemd/generator.early/lychd-vessel.service"}),
        ("lychd-vessel.service", {"LoadState": "not-found"}),
    ],
)
def test_effective_unit_overrides_refuse_before_start_and_remain_json_read_only(
    mocker: MockerFixture, tmp_path: Path, name: str, changed: dict[str, str]
) -> None:
    import json

    from click.testing import CliRunner

    from lychd.cli.operator import status

    service = world(mocker, tmp_path)
    original = service.observe_unit.side_effect

    def observe(target: str) -> dict[str, str]:
        fields: dict[str, str] = original(target)
        return dict(fields, **changed) if target == name else fields

    def inspect(request: DeploymentRequest) -> DeploymentReport:
        return service.inspect(request)

    mocker.patch.object(service, "observe_unit", side_effect=observe)
    mocker.patch("lychd.system.services.deployment.inspect_deployment", side_effect=inspect)
    result = CliRunner().invoke(status, ["--json", "--deployment-revision", REVISION])
    document = json.loads(result.output)
    assert result.exit_code == 1
    assert document["state"] == "unknown"
    assert document["next_action"] == "refuse"
    service.scribe.plan_reconcile_all.assert_not_called()
    service.scribe.reconcile_all.assert_not_called()


def test_generated_fragment_symlink_is_never_admitted(mocker: MockerFixture, tmp_path: Path) -> None:
    service = world(mocker, tmp_path)
    generated = tmp_path / "runtime/systemd/generator/lychd-vessel.service"
    generated.unlink()
    replacement = tmp_path / "shadow.service"
    replacement.write_text("[Service]\nExecStartPre=/unowned/program\n")
    generated.symlink_to(replacement)
    with pytest.raises(DeploymentObservationError, match="effective_binding_definition_mismatch"):
        service.inspect(DeploymentRequest(REVISION))
    service.scribe.plan_reconcile_all.assert_not_called()


def test_group_writable_generated_fragment_is_never_admitted(mocker: MockerFixture, tmp_path: Path) -> None:
    service = world(mocker, tmp_path)
    generated = tmp_path / "runtime/systemd/generator/lychd-vessel.service"
    generated.chmod(0o660)
    with pytest.raises(DeploymentObservationError, match="effective_binding_definition_mismatch"):
        service.inspect(DeploymentRequest(REVISION))


def test_deployment_projection_matches_the_actual_complete_bind_compiler() -> None:
    from lychd.config.runes.registry import RuneRegistry
    from lychd.extensions.host import assemble_extensions
    from lychd.system.services.bind_compilation import compile_bind_request

    settings = SettingsSnapshot(payload="{}").materialize()
    settings.server.web.image = DeploymentRequest(REVISION).image_ref
    compiled = compile_bind_request(
        settings=settings, extensions=assemble_extensions(settings), runes=RuneRegistry(()), soulstones=(), portals=()
    )
    manifests, plain = DeploymentInspectionService.desired_bindings(settings)
    assert tuple(manifests) == compiled.manifests
    assert plain == compiled.plain_unit_mapping()
    assert plain["lychd-reactor.service"]
    assert "lychd-reactor.path" in plain


@pytest.mark.usefixtures("persistent_identity_observer")
@pytest.mark.parametrize("race", ["none", "replacement", "mutation", "parent_replacement"])
def test_configuration_accepts_device_renumbering_without_rebasing_creation_evidence(  # noqa: PLR0915 - full consumer and race witnesses
    mocker: MockerFixture,
    tmp_path: Path,
    race: str,
) -> None:
    """The actual configuration consumer must survive a different boot dev_t."""
    import json
    import os

    from tomlkit import dumps

    from lychd.system.services.lifecycle.models import CreatedResources
    from lychd.system.services.lifecycle.receipt import LifecycleReceiptStore

    root = tmp_path / "codex"
    root.mkdir()
    path = root / "lychd.toml"
    declared = SettingsSnapshot(payload="{}").materialize()
    declared.server.web.image = DeploymentRequest(REVISION).image_ref
    path.write_text(dumps(declared.model_dump(mode="json", exclude_none=True)))
    path.chmod(0o600)
    mocker.patch("lychd.system.constants.PATH_CODEX_ROOT", root)
    mocker.patch("lychd.system.constants.PATH_LYCHD_TOML", path)
    store = LifecycleReceiptStore(root / ".lychd-lifecycle.json")
    store.record(CreatedResources(files=(path,)))
    document = json.loads(store.path.read_bytes())
    document["files"][0]["device"] += 12345
    store.path.write_text(json.dumps(document))
    original = store.path.read_bytes()
    service: Any = object.__new__(DeploymentInspectionService)
    service.receipt = store
    mocker.patch.object(service, "_roots", return_value=())
    mocker.patch("lychd.system.services.deployment.get_settings", return_value=declared)

    original_check = service._require_original_files
    real_pread = os.pread
    observed_descriptors: list[int] = []
    identity_check = store.require_identity_fd

    def identity(descriptor: int, entry: Any) -> None:
        identity_check(descriptor, entry)
        observed_descriptors.append(descriptor)

    def read(descriptor: int, size: int, offset: int) -> bytes:
        assert observed_descriptors[-1] == descriptor
        content = real_pread(descriptor, size, offset)
        if race == "mutation":
            path.write_bytes(content + b"# raced\n")
        elif race == "parent_replacement":
            root.rename(tmp_path / "original-codex")
            root.mkdir()
            path.write_bytes(content)
            path.chmod(0o600)
            store.path.write_bytes(original)
            store.path.chmod(0o600)
        return content

    def precheck() -> None:
        original_check()
        if race == "replacement":
            contents = path.read_bytes()
            path.rename(root / "original-config")
            path.write_bytes(contents)
            path.chmod(0o600)
        mocker.patch.object(store, "require_identity_fd", side_effect=identity)
        mocker.patch("lychd.system.services.lifecycle.receipt.os.pread", side_effect=read)

    mocker.patch.object(service, "_require_original_files", side_effect=precheck)
    if race == "none":
        result = service._configuration(DeploymentRequest(REVISION))
        assert result.server.web.image == DeploymentRequest(REVISION).image_ref
        assert observed_descriptors
    else:
        with pytest.raises(DeploymentObservationError, match="configuration_changed_during_observation"):
            service._configuration(DeploymentRequest(REVISION))
    assert store.path.read_bytes() == original
