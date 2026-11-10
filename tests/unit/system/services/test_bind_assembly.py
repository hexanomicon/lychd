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
from lychd.system.services.scribe import ScribeService
from lychd.system.services.tether.models import TetherError
from tests.unit.system.services.test_tether_secrets import secret_stack

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lychd.domain.tether.models import CompiledTetherPlan
    from lychd.system.services.scribe.models import OwnedBindings
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
    monkeypatch.setattr(preflight, "inspect", lambda _: report)
    quadlet, systemd = tmp_path / "quadlet", tmp_path / "systemd"
    quadlet.mkdir()
    systemd.mkdir()
    scribe = ScribeService(output_dir=quadlet, systemd_dir=systemd)
    monkeypatch.setattr("lychd.system.services.scribe.facade.ScribeService", lambda **_: scribe)
    store = MagicMock()
    store.exists.return_value = True
    monkeypatch.setattr("lychd.system.services.secrets.PodmanSecretStore", lambda _: store)
    manager = MagicMock()
    monkeypatch.setattr("lychd.system.services.systemd.SystemdUserManager", lambda **_: manager)
    events: list[str] = []

    @contextmanager
    def lock() -> Iterator[None]:
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


@pytest.mark.parametrize("shadow", [None, "fragment", "dropin", "reload"])
def test_retained_revoke_checks_loaded_unit_provenance_with_unchanged_disk_generation(  # noqa: PLR0915 - one complete retained-ownership transaction
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
    committed = prepared.use_case.apply(prepared.request, prepared.plan)
    owned = scribe.inspect_owned_bindings()
    native.custody.write("private", "plan.json", native.plan, immutable=True)
    peer = make_peer()
    admit_peer(native.custody, peer)
    raw = native.custody.read("operations", f"{peer.operation_id}.json")
    assert raw is not None
    enrollment = OperationReceipt.model_validate_json(raw).model_copy(
        update={"binding_generation": committed.binding_generation}
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
    monkeypatch.setattr("lychd.system.services.tether.composition.TetherCustody", lambda *_: native.custody)
    monkeypatch.setattr("lychd.system.services.tether.composition.LifecycleLock", nullcontext)
    monkeypatch.setattr("lychd.system.services.tether.composition.os.geteuid", lambda: 1000)
    monkeypatch.setattr("lychd.system.services.tether.composition._tool", lambda name, *_: f"/usr/bin/{name}")
    monkeypatch.setattr(
        "lychd.system.services.lifecycle.receipt.LifecycleReceiptStore.require_dedicated_root_identities", lambda *_: ()
    )
    # Retained closure must not consult current Runes or unrelated configuration.
    monkeypatch.setattr(BindingCommandSession, "inspect", MagicMock(side_effect=ValueError("Rune removed")))
    monkeypatch.setattr(TetherStopAdapter, "observe", lambda _: closed())
    stop = MagicMock(return_value=closed())
    monkeypatch.setattr(TetherStopAdapter, "stop", stop)
    operations = build_tether_operations(for_closure=True)

    result = operations.revoke(revoke_request(peer))

    assert scribe.inspect_owned_bindings().generation == owned.generation
    assert set(observed) == selected
    assert native.custody.read("revocations", "1.json") is not None
    assert result.complete is (shadow is None)
    if shadow is None:
        assert native.custody.read("private", "closed.json") is not None
        stop.assert_called_once()
    else:
        assert "ownership-unconfirmed" in result.stages
        assert native.custody.read("private", "closed.json") is None
        stop.assert_not_called()
