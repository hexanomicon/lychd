"""Exercise the real CLI bind factory with exact native preparation evidence."""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from lychd.cli.binding import BindingCommandSession
from lychd.config import QuadletConfig
from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings import SettingsSnapshot
from lychd.config.settings.root import Settings
from lychd.extensions.builtin.tether.config import TetherSettings
from lychd.extensions.host import assemble_extensions
from lychd.system.binding_sites import AttestedBindingSite, AttestedBindingSites
from lychd.system.host_tools import TrustedExecutable
from lychd.system.readiness import BindingFoundation
from lychd.system.services.bind import BindingPlanDriftError
from lychd.system.services.binding_preflight import BindingPreflightReport, BindingPreflightService
from lychd.system.services.scribe import ScribeOwnershipError, ScribeService
from lychd.system.services.tether.models import TetherError
from tests.unit.system.services.test_tether_secrets import secret_stack

if TYPE_CHECKING:
    from collections.abc import Generator

    from lychd.domain.tether.models import CompiledTetherPlan
    from lychd.system.services.scribe.models import OwnedBindings
    from lychd.system.services.tether.custody import TetherCustody
    from lychd.system.services.tether.models import ClosureObservation
    from lychd.system.services.tether.operations import TetherOperations
    from lychd.system.services.tether.secrets import TetherSecrets


def _foundation() -> BindingFoundation:
    return BindingFoundation(
        systemctl=TrustedExecutable(path="/usr/bin/systemctl", device=1, inode=1),
        podman=TrustedExecutable(path="/usr/bin/podman", device=1, inode=2),
        quadlet_user_generator=TrustedExecutable(
            path="/usr/lib/systemd/user-generators/podman-user-generator", device=1, inode=3
        ),
        sites=AttestedBindingSites(
            quadlet=AttestedBindingSite(path=Path("/bindings/quadlet"), device=1, inode=4),
            systemd_user=AttestedBindingSite(path=Path("/bindings/systemd"), device=1, inode=5),
        ),
    )


def _session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    tether: bool = True,
) -> tuple[BindingCommandSession, ScribeService, TetherSecrets, dict[str, dict[str, Any]], MagicMock, list[str]]:
    native, _, identities, _ = secret_stack(tmp_path)
    envelope = native.plan.envelope
    settings = Settings.model_validate({"extensions": {"builtins": ["tether"] if tether else []}})
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
    extensions = assemble_extensions(settings)
    foundation = _foundation()
    report = BindingPreflightReport(issues=(), foundation=foundation)
    preflight = BindingPreflightService()

    def inspect_settings(_settings: Settings) -> BindingPreflightReport:
        return report

    monkeypatch.setattr(preflight, "inspect", inspect_settings)
    quadlet, systemd = tmp_path / "quadlet", tmp_path / "systemd"
    quadlet.mkdir()
    systemd.mkdir()
    scribe = ScribeService(output_dir=quadlet, systemd_dir=systemd)

    def scribe_factory(**_: object) -> ScribeService:
        return scribe

    monkeypatch.setattr("lychd.system.services.scribe.facade.ScribeService", scribe_factory)
    store = MagicMock()
    store.exists.return_value = True

    def secret_store_factory(_podman_bin: str) -> MagicMock:
        return store

    monkeypatch.setattr("lychd.system.services.secrets.PodmanSecretStore", secret_store_factory)
    manager = MagicMock()

    def manager_factory(**_: object) -> MagicMock:
        return manager

    monkeypatch.setattr("lychd.system.services.systemd.SystemdUserManager", manager_factory)
    events: list[str] = []

    @contextmanager
    def lock() -> Generator[None]:
        events.append("locked")
        try:
            yield
        finally:
            events.append("unlocked")

    monkeypatch.setattr("lychd.system.services.lifecycle.lock.LifecycleLock", lock)

    def preparation(plan: object, *, podman_bin: str) -> TetherSecrets:
        assert plan == native.plan
        assert podman_bin == foundation.podman_bin
        events.append("attest")
        return native

    monkeypatch.setattr("lychd.system.services.tether.composition.preparation_service", preparation)
    return (
        BindingCommandSession(
            settings_snapshot=SettingsSnapshot.capture(settings),
            extensions=extensions,
            runes=RuneRegistry((rune,) if tether else ()),
            soulstones=(),
            portals=(),
            preflight_service=preflight,
            preflight=report,
        ),
        scribe,
        native,
        identities,
        store,
        events,
    )


def test_cli_factory_refuses_missing_preparation_before_preview_or_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, scribe, _, _, store, events = _session(tmp_path, monkeypatch)
    preview = MagicMock(wraps=scribe.plan_reconcile_all)
    monkeypatch.setattr(scribe, "plan_reconcile_all", preview)

    with pytest.raises(TetherError, match=r"prepare.*before binding"):
        session.prepare()

    assert events == ["attest"]
    preview.assert_not_called()
    store.exists.assert_not_called()
    store.ensure_present.assert_not_called()
    assert not scribe.inspect_owned_bindings().receipt_present


def test_cli_factory_commits_complete_core_tether_and_both_plain_units(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from uuid import uuid4

    session, scribe, native, _, store, events = _session(tmp_path, monkeypatch)
    receipt = native.prepare(uuid4())
    prepared = session.prepare()
    assert prepared.request.tether_plans == (native.plan,)
    assert prepared.plan.tether_preparation == (receipt,)
    assert set(prepared.request.plain_unit_mapping()) == {
        "lychd-reactor.path",
        "lychd-reactor.service",
        *native.plan.plain_unit_names,
    }
    commit = MagicMock(wraps=scribe.reconcile_all)
    monkeypatch.setattr(scribe, "reconcile_all", commit)

    result = prepared.use_case.apply(prepared.request, prepared.plan)

    commit.assert_called_once()
    assert commit.call_args.kwargs["plain_units"] == prepared.request.plain_unit_mapping()
    assert commit.call_args.args[0] == prepared.request.manifests
    owned = scribe.inspect_owned_bindings()
    assert owned.generation == result.binding_generation
    assert {
        "lychd-vessel.service",
        "lychd-phylactery.service",
        *native.plan.transport_units,
        *native.plan.plain_unit_names,
    } <= set(owned.runtime_units)
    assert events == ["attest", "locked", "attest", "attest", "unlocked"]
    store.ensure_present.assert_not_called()


def test_cli_factory_refuses_replaced_secret_between_preview_and_apply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from uuid import uuid4

    session, scribe, native, identities, store, _ = _session(tmp_path, monkeypatch)
    native.prepare(uuid4())
    prepared = session.prepare()
    identities["test-wg"]["ID"] = "f" * 25

    with pytest.raises(TetherError, match=r"command failed|foreign or replaced"):
        prepared.use_case.apply(prepared.request, prepared.plan)

    store.ensure_present.assert_not_called()
    assert not scribe.inspect_owned_bindings().receipt_present


def test_cli_factory_refuses_changed_receipt_immediately_before_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from uuid import uuid4

    session, scribe, native, _, store, events = _session(tmp_path, monkeypatch)
    original = native.prepare(uuid4())
    prepared = session.prepare()
    changed = original.model_copy(update={"operation_id": uuid4()})
    attest = MagicMock(side_effect=(original, changed))
    monkeypatch.setattr(native, "attest", attest)

    with pytest.raises(BindingPlanDriftError, match="preparation changed"):
        prepared.use_case.apply(prepared.request, prepared.plan)

    assert events == ["attest", "locked", "attest", "attest", "unlocked"]
    store.ensure_present.assert_not_called()
    assert not scribe.inspect_owned_bindings().receipt_present


def test_cli_factory_without_tether_preserves_existing_bind_behavior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, scribe, _, _, store, events = _session(tmp_path, monkeypatch, tether=False)
    prepared = session.prepare()
    assert prepared.request.tether_plans == ()
    assert prepared.plan.tether_preparation == ()

    result = prepared.use_case.apply(prepared.request, prepared.plan)

    assert scribe.inspect_owned_bindings().generation == result.binding_generation
    assert events == ["locked", "unlocked"]
    store.ensure_present.assert_not_called()


def _effective_tether_rows(
    owned: OwnedBindings,
    plan: CompiledTetherPlan,
    generator: Path,
) -> dict[str, dict[str, str]]:
    from lychd.system.services.scribe.naming import runtime_unit_for_source

    selected = {*plan.transport_units, *plan.plain_unit_names}
    rows: dict[str, dict[str, str]] = {}
    for source in (*owned.quadlet_sources, *owned.systemd_sources):
        name = runtime_unit_for_source(source.name)
        if name not in selected:
            continue
        fragment = source if source in owned.systemd_sources else generator / name
        if fragment != source:
            fragment.write_text("[Unit]\n", encoding="utf-8")
            fragment.chmod(0o600)
        rows[name] = {
            "Id": name,
            "LoadState": "loaded",
            "FragmentPath": str(fragment),
            "SourcePath": "" if source in owned.systemd_sources else str(source),
            "DropInPaths": "",
            "NeedDaemonReload": "no",
        }
    return rows


@pytest.mark.parametrize("shadow", [None, "fragment", "dropin", "reload", "device-renumber", "persistent-proof"])
def test_retained_revoke_checks_loaded_provenance_and_persistent_binding(  # noqa: C901, PLR0915 - one complete retained-ownership transaction
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    shadow: str | None,
) -> None:
    from uuid import uuid4

    from lychd.system.services.deployment import DeploymentInspectionService
    from lychd.system.services.tether.closure import TetherStopAdapter
    from lychd.system.services.tether.composition import build_tether_operations
    from lychd.system.services.tether.models import OperationReceipt
    from tests.unit.system.services.test_tether_operations import admit_peer, closed, make_peer, revoke_request

    session, scribe, native, _, _, _ = _session(tmp_path, monkeypatch)
    native.prepare(uuid4())
    prepared = session.prepare()
    prepared.use_case.apply(prepared.request, prepared.plan)
    owned = scribe.inspect_owned_bindings()
    assert owned.generation is not None
    native.custody.write("private", "plan.json", native.plan, immutable=True)
    peer = make_peer()
    admit_peer(native.custody, peer)
    raw = native.custody.read("operations", f"{peer.operation_id}.json")
    assert raw is not None
    enrollment = OperationReceipt.model_validate_json(raw).model_copy(
        update={
            "binding_identity": scribe.inspect_persistent_binding_identity(expected_generation=owned.generation),
            "stages": ("prepared", "generation-published", "forwarder-active"),
        }
    )
    native.custody.write("operations", f"{peer.operation_id}.json", enrollment)
    generator = tmp_path / "generator"
    generator.mkdir(mode=0o700)
    monkeypatch.setattr("lychd.system.services.deployment.constants.PATH_SYSTEMD_USER_GENERATOR_DIR", generator)
    selected = {*native.plan.transport_units, *native.plan.plain_unit_names}
    rows = _effective_tether_rows(owned, native.plan, generator)
    if shadow == "fragment":
        rows[native.plan.wireguard_unit]["FragmentPath"] = "/foreign/tether.service"
    elif shadow == "dropin":
        rows[native.plan.wireguard_unit]["DropInPaths"] = "/foreign/tether.service.d/override.conf"
    elif shadow == "reload":
        rows[native.plan.wireguard_unit]["NeedDaemonReload"] = "yes"
    observed: list[str] = []

    def observe(_: DeploymentInspectionService, name: str) -> dict[str, str]:
        observed.append(name)
        return rows[name]

    monkeypatch.setattr(DeploymentInspectionService, "observe_unit", observe)

    def custody_factory(*_roots: Path) -> TetherCustody:
        return native.custody

    monkeypatch.setattr("lychd.system.services.tether.composition.TetherCustody", custody_factory)
    monkeypatch.setattr("lychd.system.services.tether.composition.LifecycleLock", nullcontext)
    monkeypatch.setattr("lychd.system.services.tether.composition.os.geteuid", lambda: 1000)

    def host_tool(name: str, *_locations: str) -> str:
        return f"/usr/bin/{name}"

    monkeypatch.setattr("lychd.system.services.tether.composition._tool", host_tool)

    def attest_roots(*_arguments: object) -> tuple[()]:
        return ()

    monkeypatch.setattr(
        "lychd.system.services.lifecycle.receipt.LifecycleReceiptStore.require_dedicated_root_identities", attest_roots
    )
    # Retained closure must not consult current Runes or unrelated configuration.
    monkeypatch.setattr(BindingCommandSession, "inspect", MagicMock(side_effect=ValueError("Rune removed")))

    def observe_transport(_adapter: TetherStopAdapter) -> ClosureObservation:
        return closed()

    monkeypatch.setattr(TetherStopAdapter, "observe", observe_transport)
    stop = MagicMock(return_value=closed())
    monkeypatch.setattr(TetherStopAdapter, "stop", stop)
    if shadow == "persistent-proof":
        monkeypatch.setattr(
            scribe, "inspect_persistent_binding_identity", MagicMock(side_effect=ScribeOwnershipError("unavailable"))
        )
    if shadow == "device-renumber":
        from tests.unit.system.services.test_scribe import renumbered_device_numbers

        with renumbered_device_numbers(monkeypatch):
            assert scribe.inspect_owned_bindings().generation != owned.generation
            operations = build_tether_operations(for_closure=True)
            enrollment.require_enrollment_startup(
                peer,
                envelope_digest=native.plan.envelope_digest,
                binding_identity=operations.binding_probe(),
                boot_id=uuid4(),
            )
            result = operations.revoke(revoke_request(peer))
    else:
        operations = build_tether_operations(for_closure=True)
        result = operations.revoke(revoke_request(peer))

    assert scribe.inspect_owned_bindings().generation == owned.generation
    assert set(observed) == selected
    assert native.custody.read("revocations", "1.json") is not None
    assert result.complete is (shadow in (None, "device-renumber"))
    if shadow in (None, "device-renumber"):
        assert native.custody.read("private", "closed.json") is not None
        stop.assert_called_once()
    else:
        assert "ownership-unconfirmed" in result.stages
        assert native.custody.read("private", "closed.json") is None
        stop.assert_not_called()


def _image_transition(native: TetherSecrets, target: CompiledTetherPlan) -> TetherOperations:
    from lychd.system.services.tether.operations import TetherOperations
    from lychd.system.services.tether.secrets import TetherSecrets
    from tests.unit.system.services.test_tether_operations import closed

    gateway = TetherSecrets(
        target,
        native.custody,
        native.runner,
        podman_bin=native.podman,
        wg_bin=native.wg,
        ssh_keygen_bin=native.ssh_keygen,
    )
    return TetherOperations(
        target,
        native.custody,
        gateway,
        MagicMock(),
        MagicMock(),
        systemctl_bin="/usr/bin/systemctl",
        binding_probe=MagicMock(side_effect=AssertionError("Preparation cannot require the new binding")),
        lock_factory=nullcontext,
        preparation_cold_probe=MagicMock(return_value=closed()),
    )


def test_image_preparation_is_required_before_normal_complete_bind_and_preserves_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace
    from uuid import uuid4

    from lychd.domain.tether.models import compile_tether_plan
    from lychd.system.services.tether.secrets import TetherSecrets
    from tests.unit.system.services.test_tether_operations import image_request

    session, scribe, native, identities, store, _ = _session(tmp_path, monkeypatch)
    original = native.prepare(uuid4())
    target = compile_tether_plan(
        native.plan.envelope.model_copy(update={"image": "localhost/tether@sha256:" + "b" * 64})
    )

    def preparation(plan: CompiledTetherPlan, *, podman_bin: str) -> TetherSecrets:
        return TetherSecrets(
            plan,
            native.custody,
            native.runner,
            podman_bin=podman_bin,
            wg_bin=native.wg,
            ssh_keygen_bin=native.ssh_keygen,
        )

    monkeypatch.setattr("lychd.system.services.tether.composition.preparation_service", preparation)
    rune = session.runes.one(TetherSettings).model_copy(update={"quadlet": QuadletConfig(image=target.envelope.image)})
    updated = replace(session, runes=RuneRegistry((rune,)))
    with pytest.raises(TetherError, match="another installation or envelope"):
        updated.prepare()
    transition = _image_transition(native, target)
    prepared_receipt = transition.prepare_image(image_request(transition))
    approved = updated.prepare()
    approved.use_case.apply(approved.request, approved.plan)
    assert approved.plan.tether_preparation == (prepared_receipt,)
    assert scribe.inspect_owned_bindings().source_count > 5
    assert any(
        f"Image={target.envelope.image}" in path.read_text() for path in scribe.inspect_owned_bindings().quadlet_sources
    )
    assert native.custody.read("private", "preparation.json") == original.model_dump_json().encode()
    assert {row["ID"] for row in identities.values()} == {secret.podman_id for secret in original.secrets}
    store.ensure_present.assert_not_called()


def test_changed_image_selection_after_preview_refuses_locked_full_bind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace
    from uuid import uuid4

    from lychd.domain.tether.models import compile_tether_plan
    from lychd.system.services.tether.secrets import TetherSecrets
    from tests.unit.system.services.test_tether_operations import image_request

    session, scribe, native, _, store, _ = _session(tmp_path, monkeypatch)
    native.prepare(uuid4())
    target = compile_tether_plan(
        native.plan.envelope.model_copy(update={"image": "localhost/tether@sha256:" + "b" * 64})
    )

    def preparation(plan: CompiledTetherPlan, *, podman_bin: str) -> TetherSecrets:
        return TetherSecrets(
            plan,
            native.custody,
            native.runner,
            podman_bin=podman_bin,
            wg_bin=native.wg,
            ssh_keygen_bin=native.ssh_keygen,
        )

    monkeypatch.setattr("lychd.system.services.tether.composition.preparation_service", preparation)
    transition = _image_transition(native, target)
    transition.prepare_image(image_request(transition))
    rune = session.runes.one(TetherSettings).model_copy(update={"quadlet": QuadletConfig(image=target.envelope.image)})
    approved = replace(session, runes=RuneRegistry((rune,))).prepare()
    later = compile_tether_plan(target.envelope.model_copy(update={"image": "localhost/tether@sha256:" + "c" * 64}))
    next_transition = _image_transition(native, later)
    next_transition.prepare_image(image_request(next_transition))
    with pytest.raises(TetherError, match="another installation or envelope"):
        approved.use_case.apply(approved.request, approved.plan)
    assert not scribe.inspect_owned_bindings().receipt_present
    store.ensure_present.assert_not_called()


@pytest.mark.parametrize("bound", [False, True])
def test_real_image_prepare_assembly_handles_never_bound_and_bound_no_peer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, bound: bool
) -> None:
    from dataclasses import replace
    from uuid import uuid4

    from lychd.domain.tether.models import compile_tether_plan
    from lychd.system.operator.process import ProcessResult
    from lychd.system.services.deployment import DeploymentInspectionService
    from lychd.system.services.tether.composition import build_tether_operations
    from lychd.system.services.tether.secrets import TetherSecrets
    from tests.unit.system.services.test_tether_operations import image_request

    session, scribe, native, _, _, _ = _session(tmp_path, monkeypatch)
    native.prepare(uuid4())
    if bound:
        initial = session.prepare()
        initial.use_case.apply(initial.request, initial.plan)
    target = compile_tether_plan(
        native.plan.envelope.model_copy(update={"image": "localhost/tether@sha256:" + "b" * 64})
    )
    rune = session.runes.one(TetherSettings).model_copy(update={"quadlet": QuadletConfig(image=target.envelope.image)})
    current = replace(session, runes=RuneRegistry((rune,)))
    monkeypatch.setattr(BindingCommandSession, "inspect", MagicMock(return_value=current))

    def preparation(plan: CompiledTetherPlan, *, podman_bin: str | None = None) -> TetherSecrets:
        return TetherSecrets(
            plan,
            native.custody,
            native.runner,
            podman_bin=podman_bin or native.podman,
            wg_bin=native.wg,
            ssh_keygen_bin=native.ssh_keygen,
        )

    def custody_factory(*_paths: Path) -> TetherCustody:
        return native.custody

    monkeypatch.setattr("lychd.system.services.tether.composition.preparation_service", preparation)
    monkeypatch.setattr("lychd.system.services.tether.composition.TetherCustody", custody_factory)
    monkeypatch.setattr("lychd.system.services.tether.composition.os.geteuid", lambda: 1000)
    monkeypatch.setattr("lychd.system.services.tether.composition.LifecycleReceiptStore", MagicMock())
    monkeypatch.setattr("lychd.system.services.tether.composition.LifecycleLock", nullcontext)
    process = MagicMock()

    def probe(argv: tuple[str, ...], **_: object) -> ProcessResult:
        if "show" in argv:
            unit = argv[3]
            fields = {
                "Id": unit,
                "LoadState": "loaded" if bound else "not-found",
                "ActiveState": "inactive",
                "SubState": "dead",
                "FragmentPath": "",
                "SourcePath": "",
                "DropInPaths": "",
                "Job": "",
                "NeedDaemonReload": "no",
            }
            if unit.endswith(".service"):
                fields.update({"MainPID": "0", "ControlPID": "0", "ControlGroup": ""})
            return ProcessResult(argv, 0, "\n".join(f"{key}={value}" for key, value in fields.items()))
        if "list-jobs" in argv:
            return ProcessResult(argv, 0)
        if argv[1] == "ps":
            return ProcessResult(argv, 0, "[]")
        return ProcessResult(argv, 1)

    process.run.side_effect = probe
    monkeypatch.setattr("lychd.system.services.tether.composition.SubprocessRunner", MagicMock(return_value=process))
    effective = MagicMock(return_value={})
    monkeypatch.setattr(DeploymentInspectionService, "observe_owned_units", effective)
    operations = build_tether_operations()
    operations.prepare_image(image_request(operations))
    assert effective.call_count == int(bound)
    assert native.custody.read("public", "peer.json") is None
    assert all("start" not in call.args[0] and "stop" not in call.args[0] for call in process.run.call_args_list)
    assert scribe.inspect_owned_bindings().receipt_present is bound


def test_historical_peer_closure_reconciles_after_new_image_full_bind_without_relabeling(  # noqa: PLR0915 - one complete old-peer/new-Scribe reconciliation
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace
    from uuid import uuid4

    from lychd.domain.tether.models import compile_tether_plan
    from lychd.system.operator.process import ProcessResult
    from lychd.system.services.deployment import DeploymentInspectionService
    from lychd.system.services.tether.closure import TetherStopAdapter
    from lychd.system.services.tether.composition import build_tether_operations
    from lychd.system.services.tether.models import ClosureLatch, OperationReceipt
    from lychd.system.services.tether.operations import TetherOperations
    from lychd.system.services.tether.secrets import TetherSecrets
    from tests.unit.system.services.test_tether_operations import (
        closed,
        enroll_request,
        image_request,
        make_peer,
        revoke_request,
    )

    session, scribe, native, _, _, _ = _session(tmp_path, monkeypatch)
    native.prepare(uuid4())
    initial = session.prepare()
    committed = initial.use_case.apply(initial.request, initial.plan)
    assert committed.binding_generation is not None
    original_binding = scribe.inspect_persistent_binding_identity(expected_generation=committed.binding_generation)
    process, stop = MagicMock(), MagicMock()

    def probe(argv: tuple[str, ...], **_: object) -> ProcessResult:
        return ProcessResult(argv, 0, "active\n" if "show" in argv else "")

    process.run.side_effect = probe
    stop.boot_id.return_value = TetherStopAdapter.boot_id()
    stop.observe.return_value = closed()
    stop.stop.return_value = closed()
    old = TetherOperations(
        native.plan,
        native.custody,
        native,
        stop,
        process,
        systemctl_bin="/usr/bin/systemctl",
        binding_probe=lambda: original_binding,
        lock_factory=nullcontext,
    )
    peer = make_peer()
    old.enroll(enroll_request(peer))
    revoke = revoke_request(peer)
    assert old.revoke(revoke).complete
    latch_bytes = native.custody.read("private", "closed.json")
    revocation_bytes = native.custody.read("revocations", "1.json")
    target = compile_tether_plan(
        native.plan.envelope.model_copy(update={"image": "localhost/tether@sha256:" + "b" * 64})
    )
    transition = _image_transition(native, target)
    transition.prepare_image(image_request(transition, generation=1))

    def preparation(plan: CompiledTetherPlan, *, podman_bin: str) -> TetherSecrets:
        return TetherSecrets(
            plan,
            native.custody,
            native.runner,
            podman_bin=podman_bin,
            wg_bin=native.wg,
            ssh_keygen_bin=native.ssh_keygen,
        )

    monkeypatch.setattr("lychd.system.services.tether.composition.preparation_service", preparation)
    rune = session.runes.one(TetherSettings).model_copy(update={"quadlet": QuadletConfig(image=target.envelope.image)})
    updated = replace(session, runes=RuneRegistry((rune,))).prepare()
    updated.use_case.apply(updated.request, updated.plan)
    current_owned = scribe.inspect_owned_bindings()
    assert current_owned.generation is not None
    current_binding = scribe.inspect_persistent_binding_identity(expected_generation=current_owned.generation)
    assert current_binding != original_binding

    def custody_factory(*_paths: Path) -> TetherCustody:
        return native.custody

    def tool(name: str, *_locations: str) -> str:
        return f"/usr/bin/{name}"

    monkeypatch.setattr("lychd.system.services.tether.composition.TetherCustody", custody_factory)
    monkeypatch.setattr("lychd.system.services.tether.composition._tool", tool)
    monkeypatch.setattr("lychd.system.services.tether.composition.os.geteuid", lambda: 1000)
    monkeypatch.setattr("lychd.system.services.tether.composition.LifecycleLock", nullcontext)
    monkeypatch.setattr("lychd.system.services.tether.composition.LifecycleReceiptStore", MagicMock())
    monkeypatch.setattr(DeploymentInspectionService, "observe_owned_units", MagicMock(return_value={}))
    monkeypatch.setattr(TetherStopAdapter, "observe", MagicMock(return_value=closed()))
    retained = build_tether_operations(for_closure=True)
    assert retained.plan == native.plan
    result = retained.handle_closure()
    assert result.complete
    assert result.binding_identity == original_binding
    assert native.custody.read("private", "closed.json") == latch_bytes
    assert native.custody.read("revocations", "1.json") == revocation_bytes
    assert latch_bytes is not None
    assert ClosureLatch.model_validate_json(latch_bytes).envelope_digest == native.plan.envelope_digest
    raw = native.custody.read("operations", f"{revoke.operation_id}.json")
    assert raw is not None
    assert OperationReceipt.model_validate_json(raw).binding_identity == original_binding


pytestmark = pytest.mark.usefixtures("persistent_identity_observer")
