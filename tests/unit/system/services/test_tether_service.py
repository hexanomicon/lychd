"""Lifecycle regressions with real multi-attachment compilation and effect ports.

Run in the repository's admitted OCI test environment; these tests do not invoke
Podman, systemd, the actual Crypt, or a live application.
"""

from __future__ import annotations

import base64
import json
from contextlib import nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import pytest

from lychd.config.quadlet import QuadletConfig
from lychd.domain.tether.models import (
    AttachmentAdmission,
    ImportedAttachment,
    ImportedService,
    TetherRune,
    TetherSnapshot,
)
from lychd.system.services.tether import service as native
from lychd.system.services.tether.models import TetherError, TetherIntent
from lychd.system.services.tether.service import NativeState, NativeTetherService

if TYPE_CHECKING:
    from lychd.domain.tether.compiler import TetherDeployment
    from lychd.system.services.tether.custody import TetherCustody
    from lychd.system.services.tether.host import TetherHost


class MemoryCustody:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.records: dict[str, dict[str, Any]] = {}
        self.modes: dict[str, bool] = {}

    def attest(self) -> None:
        pass

    def read(self, name: str) -> dict[str, Any] | None:
        value = self.records.get(name)
        return None if value is None else json.loads(json.dumps(value))

    def write(self, name: str, value: dict[str, Any], **_kwargs: Any) -> bool:
        changed = self.records.get(name) != value
        self.records[name] = json.loads(json.dumps(value))
        return changed

    def directory(self, name: str, *, public: bool = False) -> Path:
        for part in (Path(name), *Path(name).parents):
            if str(part) == ".":
                continue
            previous = self.modes.setdefault(str(part), public)
            if previous != public:
                msg = "Directory mode differs from custody"
                raise TetherError(msg)
        return self.root / name

    def publish(self, name: Path, value: dict[str, Any], **_kwargs: Any) -> bool:
        return self.write(str(name), value)

    def known_paths(self) -> tuple[Path, ...]:
        return (self.root, self.root / ".custody.json", *(self.root / name for name in sorted(self.records)))


class HostPort:
    runner = None

    def __init__(self) -> None:
        self.containers: dict[str, dict[str, Any]] = {}
        self.pods: dict[str, dict[str, Any]] = {}
        self.invocations: dict[str, int] = {}
        self.starts: list[str] = []
        self.stops: list[str] = []
        self.failed_observation: str | None = None
        self.pending_restarts: set[str] = set()
        self.refuse_quiescence = False

    def image(self, _reference: str) -> dict[str, str]:
        return {"id": "a" * 64, "digest": "sha256:" + "a" * 64}

    def host_addresses(self) -> tuple[str, ...]:
        return ()

    def runtime_directories(self, root: Path, directories: tuple[Path, ...]) -> None:
        root.mkdir(mode=0o700, exist_ok=True)
        for path in directories:
            path.mkdir(mode=0o700, exist_ok=True)

    def exists(self, _kind: str, name: str) -> bool:
        return name in (self.pods if _kind == "pod" else self.containers)

    def row(self, _kind: str, name: str) -> dict[str, Any]:
        return (self.pods if _kind == "pod" else self.containers)[name]

    def command(self, *args: str) -> str:
        assert args[:3] == ("systemctl", "--user", "start")
        name = args[3].removesuffix(".service")
        self.starts.append(name)
        self.invocations[name] = self.invocations.get(name, 0) + 1
        pod_name = "-".join(name.split("-")[:3])
        if pod_name not in self.pods:
            self.invocations[pod_name + "-pod"] = self.invocations.get(pod_name + "-pod", 0) + 1
            self.pods[pod_name] = {"Id": pod_name}
        self.containers[name] = {"Id": name, "State": {"Running": True}}
        return ""

    def capture(self, config: Any, _image: dict[str, str]) -> dict[str, Any]:
        if not self.containers.get(config.name, {}).get("State", {}).get("Running"):
            msg = "Not running"
            raise TetherError(msg)
        return {
            "container_id": config.name,
            "container_name": config.name,
            "cgroup": config.name,
            "invocation_id": str(self.invocations[config.name]),
            "unit_cgroup": config.name,
            "pod_id": "-".join(config.name.split("-")[:3]),
            "netns": "-".join(config.name.split("-")[:3]),
        }

    def unit_incarnation(self, name: str) -> dict[str, str]:
        container = name.removesuffix(".service")
        return {"InvocationID": str(self.invocations.get(container, 0)), "ControlGroup": container}

    def capture_pod(self, name: str) -> dict[str, str]:
        assert name in self.pods
        return {
            "pod_id": name,
            "infra_cgroup": name,
            "netns": name,
            "invocation_id": str(self.invocations[name + "-pod"]),
        }

    def stop_pod(self, retained: dict[str, Any]) -> None:
        self.pods.pop(retained["pod_id"], None)

    def observe(self, config: Any) -> dict[str, Any]:
        if config.network_id == self.failed_observation:
            msg = "Readiness failed"
            raise TetherError(msg)
        return {"enabled": True}

    def cgroup_empty(self, name: str) -> bool:
        return not self.containers.get(name, {}).get("State", {}).get("Running", False)

    def stop_unretained(self, name: str) -> None:
        if name in self.containers or self.refuse_quiescence:
            message = "Unit closure remains uncertain"
            raise TetherError(message)
        self.pending_restarts.discard(name)
        self.stops.append(name)

    def stop(self, retained: dict[str, Any]) -> None:
        name = retained["container_id"]
        self.stops.append(name)
        self.containers.pop(name, None)


class ServiceHarness(NativeTetherService):
    core_ready = True
    rune: TetherRune

    def load_state(self) -> NativeState:
        """Read the real persisted state through the test harness."""
        return self._load()

    def save_state(self, state: NativeState) -> bool:
        """Seed the real persistence boundary without widening its production API."""
        return self._save(state)

    def _load_retained(self) -> NativeState:
        # The Lifecycle foundation is an explicit test port; retain the actual
        # strict persisted DTO roundtrip independently of fresh grant checks.
        self.custody.attest()
        return NativeState.model_validate_json(json.dumps(self.custody.read("state.json")))

    def _retained_projection(self, state: NativeState) -> Any:
        return self._projection(state)

    def _require_core(self) -> None:
        if not self.core_ready:
            message = "Core bootstrap required"
            raise TetherError(message)

    def _declared(self) -> tuple[Any, Any, Any, TetherRune]:
        return SimpleNamespace(server=SimpleNamespace(port=7134)), None, None, self.rune

    def _attest_keys(self, state: NativeState, deployment: Any) -> None:
        pass

    def observe_real_keys(self, state: NativeState, deployment: TetherDeployment) -> None:
        """Exercise the production batch boundary when a test supplies its key port."""
        super()._attest_keys(state, deployment)

    def bind_request(self, state_override: NativeState | None = None) -> Any:
        return SimpleNamespace(tether=self._projection(state_override or self._load()))

    def _bound(self, request: Any) -> dict[str, dict[str, str]]:
        del request
        return {}

    def _bind(self, state: NativeState) -> dict[str, Any]:
        self._materialize(state)
        return {"state": "bound", "changed": False}


@pytest.fixture
def lifecycle(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(native.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(native, "LifecycleLock", nullcontext)
    # Deadline advancement bounds expected readiness failures without sleeping.
    tick = iter(range(0, 100000, 20))
    monkeypatch.setattr(native.time, "monotonic", lambda: next(tick))

    def skip_sleep(_seconds: float) -> None:
        pass

    monkeypatch.setattr(native.time, "sleep", skip_sleep)
    key = base64.b64encode(bytes(range(32))).decode()
    attachments = tuple(
        ImportedAttachment(
            id=name,
            remote_lich_id=name,
            interface="wg0",
            address="10.77.0.1/32",
            private_key_ref=f"lychd-tether-{name}-private",
            remote_public_key=key,
            endpoint_address="198.51.100.10",
            endpoint_port=51820,
            services=(
                ImportedService(
                    id="intercom",
                    address="10.77.0.2",
                    port=443,
                    hostname=f"{name}.example",
                    application_identity_ref=name,
                ),
            ),
            allowed_callers=("intercom",),
        )
        for name in ("b", "c")
    )
    rune = TetherRune(quadlet=QuadletConfig(image="example/tether@sha256:" + "a" * 64), attachments=attachments)
    admissions = tuple(AttachmentAdmission(attachment_id=name, generation=1) for name in ("b", "c"))
    intent = TetherIntent(rune=rune, attachments=admissions)
    with TemporaryDirectory(prefix="tv-") as temporary:
        root = Path(temporary)
        host = HostPort()
        # Doubles implement the custody/host operations exercised by this service harness.
        service = ServiceHarness(
            custody=cast("TetherCustody", MemoryCustody(root / "custody")),
            host=cast("TetherHost", host),
            runtime_root=root / "run",
        )
        service.rune = TetherRune.model_validate_json(rune.model_dump_json()).bind_source_file(root / "tether.toml")
        service.save_state(
            NativeState(
                intent=intent,
                snapshot=TetherSnapshot(
                    installation_epoch="ab" * 16,
                    attachments=admissions,
                ),
                image=host.image(rune.quadlet.image),
            )
        )
        yield service, host


def test_json_reload_and_materialization_preserve_admission(lifecycle: Any) -> None:
    service, _ = lifecycle
    state = service._load()
    assert service.rune.source_file is not None
    assert state.intent.rune.source_file is None
    assert service.rune != state.intent.rune
    service._materialize(state)
    service._materialize(state)
    assert service._load() == state
    assert service.custody.modes["runtime"] is True
    assert len(service._projection(state).networks) == 2


@pytest.mark.parametrize("prepared", [False, True])
def test_prepare_accepts_loader_bound_rune_and_public_json_intent(
    lifecycle: Any, monkeypatch: pytest.MonkeyPatch, *, prepared: bool
) -> None:
    service, host = lifecycle
    before = service._load()
    intent_path = service.custody.root.parent / "intent.json"
    intent_path.write_text(before.intent.model_dump_json(by_alias=True))
    intent_path.chmod(0o600)
    monkeypatch.setattr(service, "_empty_preparation", lambda: not prepared)
    result = service.prepare(intent_path, dry_run=True)
    assert result == {"state": "prepared" if prepared else "absent", "changed": not prepared, "dry_run": True}
    assert service._load() == before
    assert not host.starts


@pytest.mark.parametrize("operation", ["load", "prepare"])
def test_public_rune_field_drift_is_refused_despite_matching_source_provenance(lifecycle: Any, operation: str) -> None:
    service, host = lifecycle
    before = service._load()
    source_file = service.rune.source_file
    assert source_file is not None
    intent_path = service.custody.root.parent / "intent.json"
    intent_path.write_text(before.intent.model_dump_json(by_alias=True))
    intent_path.chmod(0o600)
    changed = service.rune.model_dump(mode="json")
    changed["attachments"][0]["endpoint_port"] += 1
    service.rune = TetherRune.model_validate_json(json.dumps(changed)).bind_source_file(source_file)
    operation_call = service._load if operation == "load" else lambda: service.prepare(intent_path, dry_run=True)
    with pytest.raises(TetherError, match="differs"):
        operation_call()
    assert service._load_retained() == before
    assert not host.starts


def test_repeated_activation_preserves_epoch_routes_and_incarnations(lifecycle: Any) -> None:
    service, host = lifecycle
    assert service.activate()["changed"] is True
    state = service._load()
    catalog = (service.runtime_root / "catalog.json").read_bytes()
    starts = tuple(host.starts)
    assert service.activate()["changed"] is False
    assert service._load() == state
    assert tuple(host.starts) == starts
    assert (service.runtime_root / "catalog.json").read_bytes() == catalog


def test_wrong_generation_revoke_has_no_effect(lifecycle: Any) -> None:
    service, host = lifecycle
    service.activate()
    state = service._load()
    catalog = (service.runtime_root / "catalog.json").read_bytes()
    with pytest.raises(TetherError, match="generation"):
        service.revoke("b", None, "2")
    assert service._load() == state
    assert not host.stops
    assert (service.runtime_root / "catalog.json").read_bytes() == catalog


def test_revoke_is_repeatable_and_preserves_other_attachment(lifecycle: Any) -> None:
    service, host = lifecycle
    service.activate()
    before = service._load()
    unaffected = tuple(c.name for c in service._projection(before).runtime_configs if c.network_id == "c")
    assert service.revoke("b", None, "1")["physical_closure"] is True
    assert service.revoke("b", None, "1")["changed"] is False
    assert all(name not in host.stops for name in unaffected)
    assert all(service._load().incarnations[name] == before.incarnations[name] for name in unaffected)
    rows = json.loads((service.runtime_root / "catalog.json").read_bytes())["routes"]
    assert {row["selection"]["attachment_id"] for row in rows} == {"c"}


def test_resume_starts_owned_stopped_incarnation(lifecycle: Any) -> None:
    service, host = lifecycle
    service.activate()
    before = len(host.starts)
    for row in host.containers.values():
        row["State"]["Running"] = False
    service.resume()
    assert len(host.starts) > before
    assert all(row["State"]["Running"] for row in host.containers.values())


def test_activation_readiness_failure_does_not_publish_routes(lifecycle: Any) -> None:
    service, host = lifecycle
    host.failed_observation = "c"
    with pytest.raises(TetherError, match="Readiness"):
        service.activate()
    catalog = service.runtime_root / "catalog.json"
    assert not catalog.exists() or json.loads(catalog.read_bytes())["routes"] == []


def test_revoke_retries_physical_closure_after_catalog_failure(lifecycle: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    service, host = lifecycle
    service.activate()
    publish = service._catalog
    with monkeypatch.context() as patch:

        def fail_catalog(*args: Any) -> None:
            msg = "Catalog publication failed"
            raise TetherError(msg)

        patch.setattr(service, "_catalog", fail_catalog)
        with pytest.raises(TetherError, match="pending"):
            service.revoke("b", None, "1")
    assert service._catalog == publish
    result = service.revoke("b", None, "1")
    assert result["physical_closure"] is True
    assert host.stops
    rows = json.loads((service.runtime_root / "catalog.json").read_bytes())["routes"]
    assert {row["selection"]["attachment_id"] for row in rows} == {"c"}


def test_readmission_requires_next_generation_and_stays_inactive(lifecycle: Any) -> None:
    service, _ = lifecycle
    service.activate()
    service.revoke("b", None, "1")
    with pytest.raises(TetherError, match="generation"):
        service.admit("b", 1)
    assert service.admit("b", 2)["changed"] is True
    assert service.admit("b", 2)["changed"] is False
    assert "b" not in service._load().active
    assert "c" in service._load().active
    selected = next(row for row in service._load().snapshot.attachments if row.attachment_id == "b")
    assert selected.generation == 2
    assert selected.enabled


def test_activation_requires_core_before_any_network_effect(lifecycle: Any) -> None:
    service, host = lifecycle
    service.core_ready = False
    before = service._load()
    with pytest.raises(TetherError, match="Core"):
        service.activate()
    assert service._load() == before
    assert not host.starts
    assert not host.pods


def test_unretained_role_requires_pending_restart_cancellation(lifecycle: Any) -> None:
    service, host = lifecycle
    targets = {row.name for row in service._projection(service._load()).runtime_configs if row.network_id == "b"}
    host.pending_restarts.update(targets)
    host.refuse_quiescence = True
    with pytest.raises(TetherError, match="pending"):
        service.revoke("b", None, "1")
    assert host.pending_restarts == targets
    assert all(row["status"] == "pending" for row in service._load().revocations.values())
    host.refuse_quiescence = False
    assert service.revoke("b", None, "1")["physical_closure"] is True
    assert not host.pending_restarts
    assert targets <= set(host.stops)


def test_recover_start_before_role_and_pod_receipt_save(lifecycle: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    service, host = lifecycle
    write = service.custody.write
    with monkeypatch.context() as patch:

        def interrupt_seal(name: str, value: dict[str, Any], **kwargs: Any) -> bool:
            if name == "state.json" and value.get("incarnations"):
                message = "Interrupted before role seal"
                raise OSError(message)
            return write(name, value, **kwargs)

        patch.setattr(service.custody, "write", interrupt_seal)
        with pytest.raises(OSError, match="Interrupted"):
            service.activate()
    pending = service._load()
    assert pending.launches
    assert not pending.incarnations
    assert not pending.pods
    assert len(host.starts) == 1
    first = host.starts[0]
    service.resume()
    assert host.starts.count(first) == 1
    assert not service._load().launches
    assert first in service._load().incarnations
    assert service._load().pods


def test_revoke_closes_target_despite_unrelated_missing_key(lifecycle: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    service, host = lifecycle
    service.activate()
    before = service._load()
    untouched = {row.name for row in service._projection(before).runtime_configs if row.network_id == "c"}
    starts = tuple(host.starts)
    with monkeypatch.context() as patch:

        def strict_load_refused() -> NativeState:
            message = "Current image or configuration no longer admitted"
            raise TetherError(message)

        def strict_bind_refused(_state: NativeState) -> dict[str, Any]:
            message = "Unrelated attachment key is missing"
            raise TetherError(message)

        patch.setattr(service, "_load", strict_load_refused)
        patch.setattr(service, "_bind", strict_bind_refused)
        result = service.revoke("b", None, "1")
    assert result["physical_closure"] is True
    assert result["bindings_reconciled"] is False
    state = service._load()
    assert state.revocations["b:@:1"]["status"] == "closed"
    assert state.revocations["b:@:1"]["bindings_pending"] is True
    assert "b" not in state.active
    assert "c" in state.active
    assert not untouched.intersection(host.stops)
    assert tuple(host.starts) == starts
    with pytest.raises(TetherError, match="pending revocation"):
        service.resume()
    assert service.revoke("b", None, "1")["bindings_reconciled"] is True
    assert service.revoke("b", None, "1")["changed"] is False


def test_completed_journal_compacts_and_generation_churn_stays_bounded(lifecycle: Any) -> None:
    service, _ = lifecycle
    service.revoke("b", None, "1")
    journal = service._load().revocations["b:@:1"]
    assert "previous_snapshot" not in journal
    assert "incarnations" not in journal
    assert "pod" not in journal
    service.admit("b", 2)
    service.revoke("b", None, "2")
    assert set(service._load().revocations) == {"b:@:2"}


def test_other_pending_withdrawal_does_not_block_independent_denial(lifecycle: Any) -> None:
    service, host = lifecycle
    host.refuse_quiescence = True
    with pytest.raises(TetherError, match="pending"):
        service.revoke("b", None, "1")
    host.refuse_quiescence = False
    assert service.revoke("c", None, "1")["physical_closure"] is True
    assert service._load().revocations["b:@:1"]["status"] == "pending"
    assert service._load().revocations["c:@:1"]["status"] == "complete"
    assert service.revoke("b", None, "1")["physical_closure"] is True


def new_attachment(service: ServiceHarness, name: str = "d") -> ImportedAttachment:
    original = service.load_state().intent.rune.attachments[0]
    return original.model_copy(
        update={"id": name, "remote_lich_id": name, "private_key_ref": f"lychd-tether-{name}-private"}
    )


def test_register_new_road_without_rewriting_original_or_starting(lifecycle: Any) -> None:
    service, host = lifecycle
    service.activate()
    before = service._load()
    starts = tuple(host.starts)
    attachment = new_attachment(service)
    assert service.register_attachment(attachment)["changed"] is True
    assert service.register_attachment(attachment)["changed"] is False
    after = service._load()
    assert after.intent == before.intent
    assert service.rune.model_dump(mode="json") == before.intent.rune.model_dump(mode="json")
    assert after.snapshot == before.snapshot
    assert after.active == before.active
    assert after.incarnations == before.incarnations
    assert after.pods == before.pods
    assert tuple(host.starts) == starts
    assert service._projection(after).routes == service._projection(before).routes
    assert service._references(after)[attachment.private_key_ref] == "wireguard"
    service.admit("d", 1)
    admitted = service._load()
    assert "d" not in admitted.active
    assert {row.selection.attachment_id for row in service._projection(admitted).routes} == {"b", "c", "d"}


def test_registered_replacement_requires_closure_and_preserves_generation(lifecycle: Any) -> None:
    service, _ = lifecycle
    old = service._load().intent.rune.attachments[0]
    replacement = old.model_copy(update={"remote_lich_id": "replacement", "endpoint_port": 51821})
    with pytest.raises(TetherError, match="Revoke"):
        service.register_attachment(replacement)
    service.revoke("b", None, "1")
    service.register_attachment(replacement)
    admission = next(row for row in service._load().snapshot.attachments if row.attachment_id == "b")
    assert admission.generation == 1
    assert not admission.enabled
    with pytest.raises(TetherError, match="generation"):
        service.admit("b", 1)
    service.admit("b", 2)
    selected = next(row for row in service._projection(service._load()).routes if row.selection.attachment_id == "b")
    assert selected.selection.remote_lich_id == "replacement"
    assert selected.selection.generation == 2


def test_retired_reference_cannot_move_to_another_road(lifecycle: Any) -> None:
    service, _ = lifecycle
    original = service._load().intent.rune.attachments[0]
    service.revoke("b", None, "1")
    service.register_attachment(original.model_copy(update={"private_key_ref": "lychd-tether-b-rotated"}))
    incoming = new_attachment(service).model_copy(update={"private_key_ref": original.private_key_ref})
    with pytest.raises(TetherError, match="another road"):
        service.register_attachment(incoming)


def test_managed_topology_cannot_change_image_or_offered_envelope(lifecycle: Any) -> None:
    service, _ = lifecycle
    state = service._load()
    changed = state.intent.rune.model_copy(update={"quadlet": QuadletConfig(image="other@sha256:" + "b" * 64)})
    with pytest.raises(TetherError, match="only imported attachments"):
        service.effective_rune(state.model_copy(update={"topology": changed}))


def test_registration_refuses_foreign_runtime_before_state_mutation(lifecycle: Any) -> None:
    service, host = lifecycle
    incoming = new_attachment(service)
    before = service._load()
    import hashlib

    pod = "lychd-tether-" + hashlib.sha256(incoming.id.encode()).hexdigest()[:16]
    host.pods[pod] = {"Id": "foreign"}
    with pytest.raises(TetherError, match="existing runtime"):
        service.register_attachment(incoming)
    assert service._load() == before


def test_registration_dry_run_and_staged_update_have_no_admission(lifecycle: Any) -> None:
    service, host = lifecycle
    incoming = new_attachment(service)
    before = service._load()
    assert service.register_attachment(incoming, dry_run=True)["changed"] is True
    assert service._load() == before
    service.register_attachment(incoming)
    service.register_attachment(incoming.model_copy(update={"endpoint_port": 51821}))
    assert service._load().snapshot == before.snapshot
    assert not host.starts


def test_offered_only_registration_and_repeat_prepare_preserve_managed_road(
    lifecycle: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import Mock

    from lychd.domain.tether.models import OfferedNetwork

    service, host = lifecycle
    incoming = new_attachment(service)
    old = service._load()
    offered = OfferedNetwork(
        id="home",
        interface="wg0",
        address="10.55.0.1/24",
        listen_address="192.0.2.10",
        listen_port=51820,
        private_key_ref="lychd-tether-home-private",
    )
    initial = TetherRune(quadlet=old.intent.rune.quadlet, offered=offered)
    intent = TetherIntent(rune=initial)
    state = NativeState(
        intent=intent, snapshot=TetherSnapshot(installation_epoch=old.snapshot.installation_epoch), image=old.image
    )
    service.rune = initial
    service._save(state)
    service.register_attachment(incoming)
    registered = service._load()
    assert registered.intent == intent
    assert service._projection(registered).routes == ()
    assert service._projection(registered).consumer_mount is not None
    keys = Mock()
    keys.attest_many.return_value = {
        offered.private_key_ref: {
            "reference": offered.private_key_ref,
            "purpose": "wireguard",
            "public_key": "public",
            "fingerprint": "fingerprint",
        }
    }

    def declared_intent(_path: Path) -> TetherIntent:
        return intent

    monkeypatch.setattr(native, "load_intent", declared_intent)
    monkeypatch.setattr(service, "_empty_preparation", lambda: False)

    def key_gateway(_state: NativeState) -> Mock:
        return keys

    monkeypatch.setattr(service, "_keys", key_gateway)
    assert service.prepare(Path("/public-intent.json"))["changed"] is False
    assert service._load() == registered
    assert not host.starts


def test_effective_registry_preserves_other_runes(lifecycle: Any) -> None:
    from lychd.config.runes.base import RuneConfig
    from lychd.config.runes.registry import RuneRegistry

    service, _ = lifecycle
    original = service._load().intent.rune
    other = RuneConfig()
    registry = RuneRegistry((other, original))
    service.register_attachment(new_attachment(service))
    effective = service._effective_registry(service._load(), registry)
    assert effective.all()[0] == other
    assert effective.one(TetherRune) == service.effective_rune(service._load())
    assert registry.one(TetherRune) == original


def owner_peer(name: str, number: int) -> Any:
    from lychd.domain.tether.models import OfferedPeer, OwnerAccess

    ssh = "ssh-ed25519 " + base64.b64encode(b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + bytes(range(32))).decode()
    return OfferedPeer(
        id=name,
        generation=1,
        public_key=base64.b64encode(bytes(range(number, number + 32))).decode(),
        address=f"10.55.0.{number + 2}",
        owner_access=OwnerAccess(
            ssh_public_key=ssh, ssh_host_key_ref=f"lychd-tether-owner-{name}", listen_port=2222 + number
        ),
    )


def add_offered_network(service: ServiceHarness, peers: tuple[Any, ...]) -> NativeState:
    from lychd.domain.tether.models import OfferedNetwork

    state = service.load_state()
    offered = OfferedNetwork(
        id="home",
        interface="wg0",
        address="10.55.0.1/24",
        listen_address="192.0.2.10",
        listen_port=51820,
        private_key_ref="lychd-tether-home-private",
    )
    rune = state.intent.rune.model_copy(update={"offered": offered})
    intent = state.intent.model_copy(update={"rune": rune, "offered_peers": peers})
    updated = state.model_copy(
        update={"intent": intent, "snapshot": state.snapshot.model_copy(update={"offered_peers": peers})}
    )
    service.rune = rune
    service.save_state(updated)
    return updated


def test_hot_new_owner_preserves_other_peers_and_imported_incarnations(
    lifecycle: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import Mock

    service, host = lifecycle
    first, second = owner_peer("first", 0), owner_peer("second", 1)
    add_offered_network(service, (first,))
    keys = Mock()

    def key_gateway(_state: NativeState) -> Mock:
        return keys

    monkeypatch.setattr(service, "_keys", key_gateway)
    service.activate()
    before = service._load()
    starts = tuple(host.starts)
    before_configs = service._projection(before).runtime_configs
    owner_before = next(row for row in before_configs if row.role == "owner-ssh")
    imports_before = tuple(row for row in before_configs if row.network_id in {"b", "c"})
    assert service.enroll(second)["changed"] is True
    after = service._load()
    assert len(host.starts) == len(starts) + 1
    assert all(after.incarnations[name] == identity for name, identity in before.incarnations.items())
    owner_after = next(row for row in service._projection(after).runtime_configs if row.name == owner_before.name)
    assert owner_after.payload == owner_before.payload
    assert owner_after.name == owner_before.name
    assert (
        tuple(row for row in service._projection(after).runtime_configs if row.network_id in {"b", "c"})
        == imports_before
    )
    keys.ensure.assert_called_once_with(second.owner_access.ssh_host_key_ref, "ssh-host")
    assert service.enroll(second)["changed"] is False
    assert service._load() == after
    assert len(host.starts) == len(starts) + 1


def test_hot_first_owner_bridge_refuses_before_state_or_key_effects(
    lifecycle: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import Mock

    service, _ = lifecycle
    add_offered_network(service, ())
    service.activate()
    before = service._load()
    keys = Mock()

    def key_gateway(_state: NativeState) -> Mock:
        return keys

    monkeypatch.setattr(service, "_keys", key_gateway)
    with pytest.raises(TetherError, match="Pod policy"):
        service.enroll(owner_peer("first", 0))
    assert service._load() == before
    keys.ensure.assert_not_called()


def test_hot_missing_preshared_key_refuses_before_grant(lifecycle: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import Mock

    service, _ = lifecycle
    add_offered_network(service, (owner_peer("first", 0),))
    service.activate()
    before = service._load()
    keys = Mock()
    keys.attest_many.side_effect = TetherError("Missing key")

    def key_gateway(_state: NativeState) -> Mock:
        return keys

    monkeypatch.setattr(service, "_keys", key_gateway)
    second = owner_peer("second", 1).model_copy(update={"preshared_key_ref": "lychd-tether-peer-psk"})
    with pytest.raises(TetherError, match="Missing key"):
        service.enroll(second)
    assert service._load() == before
    keys.ensure.assert_not_called()


def test_hot_enrollment_retries_saved_peer_after_binding_failure(
    lifecycle: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import Mock

    service, host = lifecycle
    first, second = owner_peer("first", 0), owner_peer("second", 1)
    add_offered_network(service, (first,))
    keys = Mock()

    def key_gateway(_state: NativeState) -> Mock:
        return keys

    monkeypatch.setattr(service, "_keys", key_gateway)
    service.activate()
    starts = tuple(host.starts)
    before = service._load()
    with monkeypatch.context() as patch:

        def fail_bind(_state: NativeState) -> dict[str, Any]:
            message = "Binding interrupted"
            raise TetherError(message)

        patch.setattr(service, "_bind", fail_bind)
        with pytest.raises(TetherError, match="interrupted"):
            service.enroll(second)
    assert second in service._load().snapshot.offered_peers
    assert service.enroll(second)["changed"] is True
    assert len(host.starts) == len(starts) + 1
    assert all(service._load().incarnations[name] == value for name, value in before.incarnations.items())
    keys.ensure.assert_called_once()
    assert service.enroll(second)["changed"] is False


def test_failed_peer_key_preparation_retains_reference_owner_without_grant(
    lifecycle: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import Mock

    service, _ = lifecycle
    add_offered_network(service, (owner_peer("first", 0),))
    before = service._load()
    second = owner_peer("second", 1)
    keys = Mock()
    keys.ensure.side_effect = TetherError("Interrupted key preparation")

    def key_gateway(_state: NativeState) -> Mock:
        return keys

    monkeypatch.setattr(service, "_keys", key_gateway)
    with pytest.raises(TetherError, match="Interrupted"):
        service.enroll(second)
    retained = service._load()
    assert retained.snapshot == before.snapshot
    assert retained.active == before.active
    assert retained.key_owners[second.owner_access.ssh_host_key_ref] == "peer:second:ssh-host"
    third = owner_peer("third", 2)
    third = third.model_copy(
        update={
            "owner_access": third.owner_access.model_copy(
                update={"ssh_host_key_ref": second.owner_access.ssh_host_key_ref}
            )
        }
    )
    with pytest.raises(TetherError, match="another road"):
        service.enroll(third)
    keys.ensure.assert_called_once()


def test_failed_start_launch_retires_only_after_its_role_closes(
    lifecycle: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, host = lifecycle

    def fail_start(*_args: str) -> str:
        message = "Start failed before creating a container"
        raise TetherError(message)

    monkeypatch.setattr(host, "command", fail_start)
    for network in ("b", "c"):
        with pytest.raises(TetherError, match="Start failed"):
            service._activate(service._load(), (network,))
    pending = service._load()
    assert {row["network_id"] for row in pending.launches.values()} == {"b", "c"}
    host.refuse_quiescence = True
    with pytest.raises(TetherError, match="pending"):
        service.revoke("b", None, "1")
    assert service._load().launches == pending.launches
    host.refuse_quiescence = False
    assert service.revoke("b", None, "1")["physical_closure"] is True
    assert service._load().launches == {name: row for name, row in pending.launches.items() if row["network_id"] == "c"}
    original = pending.intent.rune.attachments[0]
    replacement = original.model_copy(update={"endpoint_port": 51821})
    assert service.register_attachment(replacement)["changed"] is True
    assert service.revoke("b", None, "1")["changed"] is False


def fail_after_pod_start(host: HostPort, *args: str) -> str:
    name = args[3].removesuffix(".service")
    pod = "-".join(name.split("-")[:3])
    host.invocations[pod + "-pod"] = host.invocations.get(pod + "-pod", 0) + 1
    host.pods[pod] = {"Id": pod}
    message = "Start failed after creating the Pod"
    raise TetherError(message)


def test_revocation_recovers_failed_start_pod_before_stopping_it(
    lifecycle: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, host = lifecycle

    def fail_start(*args: str) -> str:
        return fail_after_pod_start(host, *args)

    monkeypatch.setattr(host, "command", fail_start)
    with pytest.raises(TetherError, match="Start failed"):
        service._activate(service._load(), ("b",))
    assert host.pods
    assert not service._load().pods
    assert not host.containers
    stop_pod = host.stop_pod

    def verify_checkpoint(retained: dict[str, Any]) -> None:
        assert service._load().revocations["b:@:1"]["pod"] == retained
        stop_pod(retained)

    monkeypatch.setattr(host, "stop_pod", verify_checkpoint)
    assert service.revoke("b", None, "1")["physical_closure"] is True
    assert not host.pods
    assert not service._load().launches
    assert service.revoke("b", None, "1")["changed"] is False
    original = service._load().intent.rune.attachments[0]
    assert service.register_attachment(original.model_copy(update={"endpoint_port": 51821}))["changed"] is True


@pytest.mark.parametrize("proof", ["missing", "boot", "network", "policy", "unchanged_invocation"])
def test_revocation_refuses_pod_without_exact_failed_launch_proof(
    lifecycle: Any, monkeypatch: pytest.MonkeyPatch, proof: str
) -> None:
    service, host = lifecycle

    def fail_start(*args: str) -> str:
        return fail_after_pod_start(host, *args)

    monkeypatch.setattr(host, "command", fail_start)
    with pytest.raises(TetherError, match="Start failed"):
        service._activate(service._load(), ("b",))
    state = service._load()
    name, launch = next(iter(state.launches.items()))
    changes = {
        "boot": {"boot_id": "another-boot"},
        "network": {"network_id": "c"},
        "policy": {"policy_digest": "other-policy"},
        "unchanged_invocation": {"previous_pod_invocation_id": "1"},
    }
    launches = {} if proof == "missing" else {name: {**launch, **changes[proof]}}
    service._save(state.model_copy(update={"launches": launches}))
    before = dict(host.pods)

    def refuse_stop(_retained: dict[str, Any]) -> None:
        pytest.fail("An unproved Pod must never be stopped")

    monkeypatch.setattr(host, "stop_pod", refuse_stop)
    with pytest.raises(TetherError, match="pending"):
        service.revoke("b", None, "1")
    assert host.pods == before
    assert service._load().revocations["b:@:1"]["status"] == "pending"


@pytest.mark.parametrize("operation", ["projection", "binding_context", "bind_request", "attest_bind_request"])
def test_public_planning_and_commit_reobserve_changed_key_backend(
    lifecycle: tuple[ServiceHarness, HostPort], monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    from unittest.mock import Mock

    from lychd.config.runes.registry import RuneRegistry
    from lychd.config.settings import SettingsSnapshot
    from lychd.extensions.host import assemble_extensions
    from lychd.system.services.tether.keys import TetherKeys

    service, host = lifecycle
    state = service.load_state()
    settings = SettingsSnapshot(payload="{}").materialize()
    settings.extensions.builtins = ("tether",)
    settings.server.port = state.intent.web_port
    extensions = assemble_extensions(settings)
    runes = RuneRegistry((service.rune,))
    key_port = Mock(spec=TetherKeys)
    key_port.attest_many.return_value = {}

    def key_gateway(_state: NativeState) -> Mock:
        return key_port

    def declared() -> tuple[object, object, RuneRegistry, TetherRune]:
        return settings, extensions, runes, service.rune

    def compile_request(state_override: NativeState | None = None) -> object:
        return NativeTetherService.bind_request(service, state_override)

    monkeypatch.setattr(service, "_keys", key_gateway)
    monkeypatch.setattr(service, "_declared", declared)
    monkeypatch.setattr(service, "_attest_keys", service.observe_real_keys)
    monkeypatch.setattr(service, "bind_request", compile_request)
    request = service.bind_request()
    expected_references = tuple(sorted(attachment.private_key_ref for attachment in state.intent.rune.attachments))
    key_port.attest_many.assert_called_once_with(expected_references)
    before = service.load_state()
    key_port.attest_many.reset_mock()
    key_port.attest_many.side_effect = TetherError("Synthetic backend identity replaced")

    def invoke() -> None:
        if operation == "attest_bind_request":
            service.attest_bind_request(request)
        else:
            getattr(service, operation)()

    with pytest.raises(TetherError, match="identity replaced"):
        invoke()
    key_port.attest_many.assert_called_once_with(expected_references)
    assert service.load_state() == before
    assert not host.starts
    assert not host.stops


def test_preparation_status_uses_one_batch_for_all_reference_phases(
    lifecycle: tuple[ServiceHarness, HostPort], monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import Mock

    from lychd.system.services.tether.keys import KeyObservation, TetherKeys

    service, _host = lifecycle
    state = service.load_state()
    references = tuple(sorted(attachment.private_key_ref for attachment in state.intent.rune.attachments))
    observation = KeyObservation(
        {reference: {"reference": reference} for reference in references},
        dict.fromkeys(references, "ready"),
    )
    key_port = Mock(spec=TetherKeys)
    key_port.observe.return_value = observation

    def key_gateway(_state: NativeState) -> Mock:
        return key_port

    monkeypatch.setattr(service, "_empty_preparation", lambda: False)
    monkeypatch.setattr(service, "_keys", key_gateway)
    result = service.preparation_status()
    assert result["state"] == "prepared"
    assert result["missing_secrets"] == []
    assert result["owned_secrets"] == list(references)
    assert result["required_secrets"] == list(references)
    key_port.observe.assert_called_once_with()
    key_port.preparation_state.assert_not_called()
    key_port.owned_references.assert_not_called()
