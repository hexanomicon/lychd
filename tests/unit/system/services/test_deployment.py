from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

from lychd.config.settings import SettingsSnapshot
from lychd.system.operator.process import ProcessResult
from lychd.system.schemas import QuadletContainer, QuadletPod
from lychd.system.services.deployment import (
    DeploymentInspectionService,
    DeploymentObservationError,
    DeploymentReport,
    DeploymentRequest,
)
from lychd.system.services.scribe import OwnedBindings

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from lychd.system.schemas import QuadletBase

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


@pytest.mark.parametrize("change", [None, "image", "listen_port", "private_key_ref"])
def test_tether_configuration_compares_public_fields_independently_of_source_binding(
    mocker: MockerFixture, tmp_path: Path, change: str | None
) -> None:
    from tomlkit import dumps

    from lychd.config.runes.loader import ConfigLoader
    from lychd.domain.tether.models import TetherRune
    from lychd.system.services.tether.models import TetherIntent

    runes_dir = tmp_path / "runes"
    rune_path = TetherRune.anchor_dir(runes_dir) / "default.toml"
    rune_path.parent.mkdir(parents=True)
    public: dict[str, dict[str, str | int]] = {
        "quadlet": {"image": "example/tether@sha256:" + "c" * 64},
        "offered": {
            "id": "home",
            "interface": "wg0",
            "address": "10.55.0.1/24",
            "listen_address": "192.0.2.10",
            "listen_port": 51820,
            "private_key_ref": "lychd-tether-home-private",
        },
    }
    rune_path.write_text(dumps(public))
    loaded = ConfigLoader(runes_dir=runes_dir).load_all([TetherRune])[0]
    assert isinstance(loaded, TetherRune)
    assert loaded.source_file == rune_path
    intent = TetherIntent(rune=loaded)
    if change == "image":
        public["quadlet"]["image"] = "example/changed@sha256:" + "d" * 64
    elif change == "listen_port":
        public["offered"]["listen_port"] = 51821
    elif change == "private_key_ref":
        public["offered"]["private_key_ref"] = "lychd-tether-changed-private"
    settings = SettingsSnapshot(payload="{}").materialize()
    settings.extensions.builtins = ("tether",)
    settings.server.web.image = DeploymentRequest(REVISION).image_ref
    settings.server.port = intent.web_port
    service: Any = object.__new__(DeploymentInspectionService)
    original_files = mocker.patch.object(service, "_require_original_files")
    service.receipt = mocker.Mock()
    service.receipt.read_original_file.side_effect = [
        dumps(settings.model_dump(mode="json", exclude_none=True)).encode(),
        dumps(public).encode(),
    ]
    mocker.patch("lychd.system.services.deployment.constants.PATH_RUNES_DIR", runes_dir)
    mocker.patch("lychd.system.services.deployment.get_settings", return_value=settings)
    mocker.patch("lychd.system.services.tether.models.load_intent", return_value=intent)
    request = DeploymentRequest(
        REVISION,
        IMAGE,
        profile="tether-container-v1",
        intent_path=tmp_path / "intent.json",
        tether_image_id="c" * 64,
    )
    if change is None:
        assert service._configuration(request).model_dump() == settings.model_dump()
    else:
        with pytest.raises(DeploymentObservationError, match="tether_original_intent_mismatch"):
            service._configuration(request)
    original_files.assert_called_once_with()
    service.receipt.read_original_file.assert_any_call(rune_path, expected_mode=0o600, max_bytes=1024 * 1024)


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


def test_tether_protocol_requires_explicit_pinned_inputs() -> None:
    with pytest.raises(ValueError, match="requires absolute intent"):
        DeploymentRequest(REVISION, IMAGE, profile="tether-container-v1")
    request = DeploymentRequest(
        REVISION,
        IMAGE,
        profile="tether-container-v1",
        intent_path=Path("/secure/intent.json"),
        tether_image_id="c" * 64,
    )
    document = DeploymentReport(request, state="initialized").as_dict()
    assert document["version"] == 2
    assert document["profile"] == "tether-container-v1"
    assert document["next_action"] == "bind"
    assert DeploymentReport(DeploymentRequest(REVISION, IMAGE)).as_dict()["version"] == 1


def test_public_owned_unit_observer_refuses_unowned_subset(mocker: MockerFixture) -> None:
    service = DeploymentInspectionService.__new__(DeploymentInspectionService)
    observe = mocker.patch.object(service, "observe_unit")
    owned = OwnedBindings(receipt_present=True, runtime_units=("lychd-vessel.service",))
    with pytest.raises(DeploymentObservationError, match="unowned_unit_selection"):
        service.observe_owned_units(owned, frozenset({"foreign.service"}))
    observe.assert_not_called()


def test_public_owned_unit_observer_attests_only_exact_sources(mocker: MockerFixture) -> None:
    service = DeploymentInspectionService.__new__(DeploymentInspectionService)
    owned = OwnedBindings(
        receipt_present=True,
        generation="generation",
        systemd_sources=(Path("/owned/lychd-one.service"), Path("/owned/lychd-two.service")),
        runtime_units=("lychd-one.service", "lychd-two.service"),
    )
    observe = mocker.patch.object(service, "observe_unit", return_value=unit(name="lychd-one.service"))
    attest = mocker.patch.object(service, "_require_effective_bindings")
    result = service.observe_owned_units(owned, frozenset({"lychd-one.service"}))
    observe.assert_called_once_with("lychd-one.service")
    assert set(result) == {"lychd-one.service"}
    subset = attest.call_args.args[0]
    assert subset.systemd_sources == (Path("/owned/lychd-one.service"),)
    assert subset.runtime_units == ("lychd-one.service",)


def test_tether_profile_refuses_wrong_runtime_image_before_binding(mocker: MockerFixture, tmp_path: Path) -> None:
    import json

    service = world(mocker, tmp_path, bound=False)
    mocker.patch.object(service, "_roots", return_value=(tmp_path,))
    native = mocker.patch("lychd.system.services.tether.service.NativeTetherService").return_value
    native.preparation_status.return_value = {
        "state": "prepared",
        "missing_secrets": [],
        "known_paths": [],
        "required_secrets": [],
        "owned_secrets": [],
    }
    native.inspect.return_value = {
        "schema": "lychd.tether.inspection",
        "version": 1,
        "state": "prepared",
        "image": "localhost/lychd-tether:" + REVISION,
    }
    mocker.patch.object(
        service,
        "run",
        return_value=json.dumps(
            [
                {
                    "Id": "d" * 64,
                    "Labels": {"org.opencontainers.image.revision": REVISION},
                }
            ]
        ),
    )
    request = DeploymentRequest(
        REVISION,
        IMAGE,
        profile="tether-container-v1",
        intent_path=Path("/secure/intent.json"),
        tether_image_id="c" * 64,
    )
    with pytest.raises(DeploymentObservationError, match="tether_image_identity_mismatch"):
        service.inspect(request)
    native.bind.assert_not_called()
    native.activate.assert_not_called()


@pytest.mark.parametrize(("state", "expected"), [("absent", "initialized"), ("waiting_keys", "prepared_waiting_keys")])
def test_original_tether_preparation_recovery_without_binding(
    mocker: MockerFixture, tmp_path: Path, state: str, expected: str
) -> None:
    service = world(mocker, tmp_path, bound=False)
    mocker.patch.object(service, "_roots", return_value=(tmp_path,))
    native = mocker.patch("lychd.system.services.tether.service.NativeTetherService").return_value
    native.preparation_status.return_value = {
        "state": state,
        "missing_secrets": ["client"] if state == "waiting_keys" else [],
        "known_paths": [],
        "required_secrets": [],
        "owned_secrets": [],
    }
    mocker.patch(
        "lychd.system.services.tether.models.load_intent",
        return_value=SimpleNamespace(rune=SimpleNamespace(quadlet=SimpleNamespace(image="pinned"))),
    )
    mocker.patch.object(service, "_require_tether_image")
    request = DeploymentRequest(
        REVISION,
        IMAGE,
        profile="tether-container-v1",
        intent_path=Path("/secure/intent.json"),
        tether_image_id="c" * 64,
    )
    report = service.inspect(request)
    assert report.state == expected
    assert report.as_dict()["next_action"] == ("bind" if state == "absent" else "import-key")
    native.inspect.assert_not_called()
    native.bind_request.assert_not_called()
    service.desired_bindings.assert_not_called()


def test_tether_preparation_does_not_hide_replaced_key(mocker: MockerFixture, tmp_path: Path) -> None:
    from lychd.system.services.tether.models import TetherError

    service = world(mocker, tmp_path, bound=False)
    mocker.patch.object(service, "_roots", return_value=(tmp_path,))
    native = mocker.patch("lychd.system.services.tether.service.NativeTetherService").return_value
    native.preparation_status.side_effect = TetherError("refused")
    request = DeploymentRequest(
        REVISION,
        IMAGE,
        profile="tether-container-v1",
        intent_path=Path("/secure/intent.json"),
        tether_image_id="c" * 64,
    )
    with pytest.raises(TetherError):
        service.inspect(request)
    native.inspect.assert_not_called()


@pytest.mark.parametrize("foreign", ["containers", "pods", "secrets", "foreign_sources"])
def test_preparation_recovery_refuses_foreign_runtime(mocker: MockerFixture, tmp_path: Path, foreign: str) -> None:
    service = world(mocker, tmp_path, bound=False)
    mocker.patch.object(service, "_roots", return_value=(tmp_path,))
    native = mocker.patch("lychd.system.services.tether.service.NativeTetherService").return_value
    native.preparation_status.return_value = {
        "state": "absent",
        "missing_secrets": [],
        "known_paths": [],
        "required_secrets": [],
        "owned_secrets": [],
    }
    mocker.patch(
        "lychd.system.services.tether.models.load_intent",
        return_value=SimpleNamespace(rune=SimpleNamespace(quadlet=SimpleNamespace(image="pinned"))),
    )
    mocker.patch.object(service, "_require_tether_image")
    service._footprint.return_value[foreign] = ["lychd-foreign"]
    request = DeploymentRequest(
        REVISION,
        IMAGE,
        profile="tether-container-v1",
        intent_path=Path("/secure/intent.json"),
        tether_image_id="c" * 64,
    )
    report = service.inspect(request)
    assert report.state == "unknown"
    assert report.reasons == ["runtime_material_before_tether_preparation"]
    native.inspect.assert_not_called()


@pytest.mark.parametrize("owned", [True, False])
def test_retired_receipted_tether_secret_is_owned_but_unknown_secret_refuses(
    mocker: MockerFixture, tmp_path: Path, *, owned: bool
) -> None:
    service = world(mocker, tmp_path, bound=True)
    native = mocker.patch("lychd.system.services.tether.service.NativeTetherService").return_value
    native.preparation_status.return_value = {"state": "prepared"}
    native.inspect.return_value = {
        "schema": "lychd.tether.inspection",
        "version": 1,
        "state": "bound",
        "known_paths": [],
        "required_secrets": [],
        "owned_secrets": ["lychd-tether-retired"] if owned else [],
    }
    service._footprint.return_value["secrets"] = ["lychd-tether-retired"]
    mocker.patch.object(service, "_require_tether_image")
    request = DeploymentRequest(
        REVISION,
        IMAGE,
        profile="tether-container-v1",
        intent_path=Path("/secure/intent.json"),
        tether_image_id="c" * 64,
    )
    report = service.inspect(request)
    assert report.state == ("bound_inactive" if owned else "unknown")
    if not owned:
        assert report.reasons == ["foreign_runtime_material"]


def test_tether_desired_bindings_use_effective_native_request(mocker: MockerFixture) -> None:
    from lychd.system.services.bind import BindRequest

    settings = SettingsSnapshot(payload="{}").materialize()
    settings.extensions.builtins = ("tether",)
    native = mocker.patch("lychd.system.services.tether.service.NativeTetherService").return_value
    request = BindRequest.compile(
        manifests=(),
        plain_units={"managed.service": "current topology"},
        core_secret_factories={},
        required_secret_names=(),
    )
    native.bind_request.return_value = request
    manifests, units = DeploymentInspectionService.desired_bindings(settings)
    assert manifests == []
    assert units == {"managed.service": "current topology"}
    native.bind_request.assert_called_once_with()


@dataclass
class InfraEngine:
    pods: dict[str, list[object]] = field(default_factory=dict)
    containers: dict[str, list[object]] = field(default_factory=dict)
    invocations: dict[str, str] = field(default_factory=dict)
    calls: list[tuple[str, ...]] = field(default_factory=list)

    def run(self, tool: str, *arguments: str) -> str:
        self.calls.append((tool, *arguments))
        if tool == "systemctl":
            assert arguments[:2] == ("--user", "show")
            assert arguments[3:] == ("--property=InvocationID", "--value")
            return self.invocations[arguments[2]]
        assert tool == "podman"
        kind, verb, identity, flag, projection = arguments
        assert verb == "inspect"
        assert flag == "--format"
        assert "Env" not in projection
        assert "Secret" not in projection
        if identity == "lychd-vessel":
            assert projection == "{{.Image}}"
            return IMAGE
        if kind == "pod":
            assert projection == "[{{json .ID}},{{json .Name}},{{json .CreateInfra}},{{json .InfraContainerID}}]"
        else:
            assert projection == (
                "[{{json .ID}},{{json .Name}},{{json .Pod}},{{json .IsInfra}},"
                "{{json .State.Running}},{{json .State.ConmonPid}}]"
            )
        rows = self.pods if kind == "pod" else self.containers
        row = next((row for name, row in rows.items() if identity in (name, row[0])), None)
        if row is None:
            message = "Synthetic runtime object unavailable"
            raise DeploymentObservationError(message)
        return json.dumps(row)


@dataclass
class InfraWorld:
    service: DeploymentInspectionService
    engine: InfraEngine
    bindings: OwnedBindings
    observed: dict[str, dict[str, str]]
    footprint: dict[str, list[str]]
    request: DeploymentRequest


def infra_sources(tmp_path: Path, manifests: list[QuadletBase]) -> tuple[tuple[Path, ...], dict[str, dict[str, str]]]:
    sources: list[Path] = []
    observed: dict[str, dict[str, str]] = {}
    for index, manifest in enumerate(manifests):
        if isinstance(manifest, QuadletPod):
            stem, suffix = manifest.pod_name, ".pod"
            name = stem + "-pod.service"
        else:
            assert isinstance(manifest, QuadletContainer)
            stem, suffix = manifest.container_name, ".container"
            name = stem + ".service"
        source = tmp_path / "quadlet" / (stem + suffix)
        fragment = tmp_path / "runtime/systemd/generator" / name
        for path in (source, fragment):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("exact")
            path.chmod(0o600)
        sources.append(source)
        observed[name] = dict(
            unit("active", sub="running", name=name),
            FragmentPath=str(fragment),
            SourcePath=str(source),
            MainPID=str(100 + index),
        )
    return tuple(sources), observed


def infra_world(mocker: MockerFixture, tmp_path: Path, *, tether: bool = False) -> InfraWorld:
    service: DeploymentInspectionService = world(mocker, tmp_path)
    engine = InfraEngine()
    pod_names = ["lychd", *(["lychd-tether-" + "d" * 16] if tether else [])]
    manifests: list[QuadletBase] = [
        QuadletContainer(description="Core", image="example/core", container_name="lychd-vessel", pod="lychd.pod"),
    ]
    manifests.extend(QuadletPod(pod_name=name) for name in pod_names)
    if tether:
        manifests.append(
            QuadletContainer(
                description="Tether",
                image="example/tether",
                container_name=pod_names[1] + "-wg",
                pod=pod_names[1] + ".pod",
            )
        )
    sources, observed = infra_sources(tmp_path, manifests)
    reactor = tmp_path / "user/lychd-reactor.service"
    observed[reactor.name] = dict(unit("active", sub="running", name=reactor.name), FragmentPath=str(reactor))
    bindings = OwnedBindings(
        receipt_present=True,
        generation="exact",
        systemd_sources=(reactor,),
        quadlet_sources=sources,
        runtime_units=tuple(sorted(observed)),
    )
    for index, name in enumerate(pod_names):
        pod_id, infra_id = str(index + 1) * 64, str(index + 3) * 64
        # The arbitrary observed name deliberately does not use an infra suffix.
        infra_name = f"lychd-observed-{index}"
        engine.pods[name] = [pod_id, name, True, infra_id]
        unit_name = name + "-pod.service"
        engine.containers[infra_id] = [infra_id, infra_name, pod_id, True, True, int(observed[unit_name]["MainPID"])]
        engine.invocations[unit_name] = "a" * 32
    containers = [
        *(row.container_name for row in manifests if isinstance(row, QuadletContainer)),
        *(str(row[1]) for row in engine.containers.values()),
    ]
    footprint = {
        "foreign_sources": [],
        "containers": containers,
        "pods": pod_names,
        "secrets": [],
        "running_containers": list(containers),
    }
    mocker.patch.object(service.scribe, "inspect_owned_bindings", return_value=bindings)
    mocker.patch.object(service, "_unit_names", return_value=set(observed))

    def observe(name: str) -> dict[str, str]:
        return dict(observed[name])

    mocker.patch.object(service, "observe_unit", side_effect=observe)
    mocker.patch.object(service, "_footprint", return_value=footprint)
    mocker.patch.object(service, "desired_bindings", return_value=(manifests, {reactor.name: "exact"}))
    mocker.patch.object(service, "run", side_effect=engine.run)
    request = DeploymentRequest(REVISION, IMAGE)
    if tether:
        native = mocker.patch("lychd.system.services.tether.service.NativeTetherService").return_value
        native.preparation_status.return_value = {"state": "prepared"}
        native.inspect.return_value = {"schema": "lychd.tether.inspection", "version": 1, "state": "active"}
        mocker.patch.object(service, "_require_tether_image")
        request = DeploymentRequest(
            REVISION,
            IMAGE,
            profile="tether-container-v1",
            intent_path=tmp_path / "intent.json",
            tether_image_id="c" * 64,
        )
    return InfraWorld(service, engine, bindings, observed, footprint, request)


@pytest.mark.parametrize("tether", [False, True])
def test_deployment_admits_only_proved_implicit_pod_infrastructure(
    mocker: MockerFixture, tmp_path: Path, *, tether: bool
) -> None:
    current = infra_world(mocker, tmp_path, tether=tether)
    effects = mocker.patch.object(current.service.scribe, "reconcile_all")
    for _ in range(2):
        report = current.service.inspect(current.request)
        assert report.state == "running"
        assert report.as_dict()["next_action"] == "observe"
        assert report.facts["footprint"] == current.footprint
    assert len([call for call in current.engine.calls if call[0:2] == ("podman", "pod")]) == 4 * (1 + tether)
    effects.assert_not_called()


@pytest.mark.parametrize(
    ("kind", "index", "value"),
    [
        ("pod", 0, "f" * 64),
        ("pod", 2, False),
        ("pod", 2, "true"),
        ("pod", 3, "short"),
        ("pod", 3, "f" * 64),
        ("container", 0, "f" * 64),
        ("container", 2, "f" * 64),
        ("container", 3, False),
        ("container", 3, "true"),
        ("container", 3, None),
        ("container", 4, False),
        ("container", 5, 999),
        ("container", 5, True),
        ("container", 5, "101"),
    ],
)
def test_deployment_refuses_wrong_infrastructure_identity_or_manager(
    mocker: MockerFixture, tmp_path: Path, kind: str, index: int, value: object
) -> None:
    current = infra_world(mocker, tmp_path)
    rows = current.engine.pods if kind == "pod" else current.engine.containers
    next(iter(rows.values()))[index] = value
    report = current.service.inspect(current.request)
    assert report.state == "unknown"
    assert report.reasons == ["foreign_runtime_material"]


@pytest.mark.parametrize("category", ["containers", "pods", "secrets"])
def test_infrastructure_exception_never_hides_foreign_material(
    mocker: MockerFixture, tmp_path: Path, category: str
) -> None:
    current = infra_world(mocker, tmp_path)
    current.footprint[category].append("lychd-foreign-infra")
    report = current.service.inspect(current.request)
    assert report.state == "unknown"
    assert report.reasons == ["foreign_runtime_material"]


@pytest.mark.parametrize("payload", ["not-json synthetic-sensitive-input", "{}", "[]", "[null]", "[]\n[]"])
def test_infrastructure_malformed_projection_is_a_content_free_refusal(
    mocker: MockerFixture, tmp_path: Path, payload: str
) -> None:
    current = infra_world(mocker, tmp_path)

    def malformed(tool: str, *arguments: str) -> str:
        if tool == "podman" and arguments[0] == "pod":
            return payload
        return current.engine.run(tool, *arguments)

    mocker.patch.object(current.service, "run", side_effect=malformed)
    report = current.service.inspect(current.request)
    assert report.state == "unknown"
    assert report.reasons == ["foreign_runtime_material"]
    assert "synthetic-sensitive-input" not in json.dumps(report.as_dict())


@pytest.mark.parametrize("drift", ["pod", "container", "invocation", "generation"])
def test_infrastructure_observation_refuses_replacement_between_reads(
    mocker: MockerFixture, tmp_path: Path, drift: str
) -> None:
    current = infra_world(mocker, tmp_path)
    reads = 0

    def changing(tool: str, *arguments: str) -> str:
        nonlocal reads
        result = current.engine.run(tool, *arguments)
        if tool == "podman" and arguments[0] == "container" and arguments[2] != "lychd-vessel":
            reads += 1
            if reads == 1:
                if drift == "pod":
                    current.engine.pods["lychd"][3] = "f" * 64
                elif drift == "container":
                    next(iter(current.engine.containers.values()))[1] = "lychd-replaced"
                elif drift == "invocation":
                    current.engine.invocations["lychd-pod.service"] = "b" * 32
                else:
                    mocker.patch.object(
                        current.service.scribe,
                        "inspect_owned_bindings",
                        return_value=replace(current.bindings, generation="changed"),
                    )
        return result

    mocker.patch.object(current.service, "run", side_effect=changing)
    report = current.service.inspect(current.request)
    assert report.state == "unknown"
    assert report.reasons == ["foreign_runtime_material"]


@pytest.mark.parametrize("authority", ["receipt", "source", "inactive", "shadow", "generation"])
def test_infrastructure_requires_complete_current_binding_authority(
    mocker: MockerFixture, tmp_path: Path, authority: str
) -> None:
    current = infra_world(mocker, tmp_path)
    if authority in {"receipt", "source"}:
        bindings = (
            replace(current.bindings, receipt_present=False)
            if authority == "receipt"
            else replace(
                current.bindings,
                quadlet_sources=tuple(path for path in current.bindings.quadlet_sources if path.suffix != ".pod"),
            )
        )
        mocker.patch.object(current.service.scribe, "inspect_owned_bindings", return_value=bindings)
    elif authority == "inactive":
        current.observed["lychd-pod.service"].update(ActiveState="inactive", SubState="dead", MainPID="0")
    elif authority == "shadow":
        current.observed["lychd-pod.service"]["DropInPaths"] = "/foreign/override.conf"
    else:
        mocker.patch.object(current.service.scribe, "plan_reconcile_all", return_value=SimpleNamespace(mutates=True))
    if authority == "shadow":
        with pytest.raises(DeploymentObservationError, match="effective_binding_override"):
            current.service.inspect(current.request)
    else:
        report = current.service.inspect(current.request)
        assert report.state == "unknown"
        assert report.as_dict()["next_action"] == "refuse"
    assert not current.engine.calls or all(call[0] == "systemctl" for call in current.engine.calls)


def test_deployment_observations_pin_local_podman_despite_ambient_remote(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONTAINER_HOST", "ssh://foreign.invalid/run/podman.sock")
    monkeypatch.setenv("CONTAINER_CONNECTION", "foreign-engine")
    service = DeploymentInspectionService.__new__(DeploymentInspectionService)
    runner = mocker.Mock()
    service.runner = runner
    runner.run.return_value = ProcessResult(("/tools/podman",), 0, "observed")

    def trusted(name: str) -> str:
        return "/tools/" + name

    mocker.patch("lychd.system.services.deployment.trusted_host_tool", side_effect=trusted)
    for arguments in (
        ("ps", "--all"),
        ("pod", "inspect", "1" * 64),
        ("container", "inspect", "2" * 64),
        ("secret", "ls"),
        ("image", "inspect", "pinned"),
    ):
        assert service.run("podman", *arguments) == "observed"
        runner.run.assert_called_with(("/tools/podman", "--remote=false", *arguments), timeout_s=20.0)
    service.run("systemctl", "--user", "show", "lychd-pod.service")
    runner.run.assert_called_with(("/tools/systemctl", "--user", "show", "lychd-pod.service"), timeout_s=20.0)
