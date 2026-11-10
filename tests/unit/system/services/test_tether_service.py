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
from typing import Any

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

    def bind_request(self, state_override: NativeState | None = None) -> Any:
        return SimpleNamespace(tether=self._projection(state_override or self._load()))

    def _bound(self, _request: Any) -> dict[str, dict[str, str]]:
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
    monkeypatch.setattr(native.time, "sleep", lambda _: None)
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
        service = ServiceHarness(custody=MemoryCustody(root / "custody"), host=host, runtime_root=root / "run")
        service.rune = rune
        service._save(
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
    service._materialize(state)
    service._materialize(state)
    assert service._load() == state
    assert service.custody.modes["runtime"] is True
    assert len(service._projection(state).networks) == 2


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
