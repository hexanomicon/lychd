"""Fail-closed qualification profile and owned-container settlement contracts."""

from __future__ import annotations

import copy
import io
import json
import tarfile
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from scripts import scout_qualification as q

Json = dict[str, Any]
IMAGE = "sha256:" + "a" * 64
IDENTITY = "b" * 64


def test_maintained_oci_proof_matches_runtime_source_and_paired_network_receipts() -> None:
    """A new recipe, lock or network receipt needs an actual qualification occurrence."""
    root = Path(__file__).resolve().parents[2]
    record = json.loads((root / "tests/fixtures/scout/linux-oci-extraction-runtime.json").read_text())
    assert record["schema"] == "scout-oci-static-proof@1"
    qualification, receipt = record["qualification"], record["receipt"]
    assert qualification["profile"] == q.PROFILE_NAME
    assert qualification["host_namespace_quota_unchanged"]
    assert qualification["owned_containers_removed_and_404_observed"]
    assert receipt["status"] == "passed"
    assert receipt["profile"] == "scout-static-extract@1"
    assert "network_filesystem_environment_descriptor_namespace_and_process_denial" in receipt["checks"]
    assert "runtime_and_code_unchanged" in receipt["checks"]
    assert set(qualification["source_sha256"]) == {
        "Containerfile.tests",
        "Containerfile.scout-qualification",
        "scripts/container_scout_qualification.sh",
        "scripts/scout_qualification.py",
        "Makefile",
        "pyproject.toml",
        "uv.lock",
    }
    assert set(record["paired_receipt_sha256"]) == {
        "tests/fixtures/scout/linux-fetch-runtime.json",
        "tests/fixtures/scout/linux-authority-runtime.json",
    }
    for path, digest in (qualification["source_sha256"] | record["paired_receipt_sha256"]).items():
        assert sha256((root / path).read_bytes()).hexdigest() == digest, path
    for path in (
        "src/lychd/system/scout_worker.py",
        "src/lychd/system/services/scout_extraction.py",
        "src/lychd/domain/scout/extraction.py",
        "tests/integration/test_scout_extraction_runtime.py",
    ):
        assert sha256((root / path).read_bytes()).hexdigest() == receipt["runtime"]["code"][Path(path).name], path


def _host() -> Json:
    return {
        "ReadonlyPaths": ["/proc/sys", "/proc/bus"],
        "MaskedPaths": ["/proc/keys"],
        "SecurityOpt": ["no-new-privileges", 'seccomp={"defaultAction":"SCMP_ACT_ERRNO"}'],
        "Memory": 2 * 1024**3,
        "NanoCpus": 2_000_000_000,
        "PidsLimit": 256,
        "NetworkMode": "none",
        "Privileged": False,
        "CapDrop": ["ALL"],
        "CapAdd": sorted(q.CAPS),
        "Sysctls": {"net.ipv4.ip_unprivileged_port_start": "0"},
        "PublishAllPorts": False,
    }


@pytest.mark.parametrize(
    ("readonly", "masks"),
    [
        ([], ["/proc/keys"]),
        (["/proc/bus"], ["/proc/keys"]),
        (["/proc/sys"], []),
        (["/proc/sys", "/proc/sys"], ["/proc/keys"]),
    ],
)
def test_missing_or_ambiguous_default_paths_refuse(readonly: list[str], masks: list[str]) -> None:
    baseline = _host()
    baseline.update(ReadonlyPaths=readonly, MaskedPaths=masks)
    with pytest.raises(ValueError, match="default path restrictions"):
        q.derive_profile(baseline, "{}")


@pytest.mark.parametrize(
    ("field", "value"),
    [("ReadonlyPaths", ["/proc/bus"]), ("MaskedPaths", []), ("SecurityOpt", ["seccomp=unconfined"]), ("Memory", 0)],
)
def test_ignored_or_extra_daemon_changes_refuse(field: str, value: object) -> None:
    baseline = _host()
    expected = q.derive_profile(baseline, '{"defaultAction":"SCMP_ACT_ERRNO"}')
    actual = copy.deepcopy(expected)
    actual[field] = value
    with pytest.raises((ValueError, json.JSONDecodeError)):
        q.validate_profile(actual, baseline, expected)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("Binds", ["/arbitrary:/host"]),
        ("Memory", 0),
        ("NanoCpus", 0),
        ("PidsLimit", 0),
        ("CapAdd", ["CAP_SYS_ADMIN"]),
        ("Privileged", True),
    ],
)
def test_bootstrap_cannot_smuggle_host_authority(field: str, value: object) -> None:
    host = _host()
    host[field] = value
    container: Json = {
        "Image": IMAGE,
        "HostConfig": host,
        "Mounts": [],
        "Config": {
            "Image": IMAGE,
            "User": "0:0",
            "Entrypoint": ["/usr/bin/timeout"],
            "Cmd": q.COMMAND,
            "Env": [],
            "Volumes": None,
        },
    }
    with pytest.raises(ValueError, match="Unexpected"):
        q.boundary(container, IMAGE, [])


class _Engine:
    def __init__(self, container: Json | None) -> None:
        self.container = container
        self.calls: list[str] = []
        self.removed = False

    def request(self, method: str, path: str, *_args: object, **_kwargs: object) -> Json | None:
        self.calls.append(method + " " + path)
        if method == "DELETE":
            self.removed = True
            return None
        if "/logs?" in path:
            raise q.EngineError(500, b"export failed")
        if self.removed or self.container is None:
            raise q.EngineError(404, b"not found")
        return self.container


def _controller(tmp_path: Path) -> q.Controller:
    control = q.Controller(tmp_path, IMAGE)
    control.engine = _Engine(
        {
            "Id": IDENTITY,
            "Image": IMAGE,
            "Name": "/" + control.name("proof"),
            "Config": {"Labels": {q.LABEL: control.occurrence, q.LABEL + ".phase": "proof"}},
            "State": {"Running": False},
        }
    )
    return control


def test_export_failure_still_settles_owned_container(tmp_path: Path) -> None:
    control = _controller(tmp_path)
    control.register(IDENTITY, "proof")
    with pytest.raises(RuntimeError, match="Safe export failed"):
        control.remove(IDENTITY, "proof")
    assert not control.owned
    assert control.engine.removed
    assert control.summary["settlement"]["proof"]["removed_and_404_observed"]


def test_wrong_owner_never_receives_delete(tmp_path: Path) -> None:
    control = _controller(tmp_path)
    control.engine.container["Config"]["Labels"][q.LABEL] = "another-occurrence"
    with pytest.raises(ValueError, match="ownership"):
        control.remove(IDENTITY, "proof")
    assert not any(call.startswith("DELETE") for call in control.engine.calls)


def test_kill_ack_with_running_state_still_force_removes(tmp_path: Path) -> None:
    control = _controller(tmp_path)
    control.engine.container["State"]["Running"] = True
    control.register(IDENTITY, "proof")
    with pytest.raises(RuntimeError, match="Safe export failed"):
        control.remove(IDENTITY, "proof")
    assert control.engine.removed
    assert not control.owned


def test_ambiguous_create_reconciles_only_unique_owned_identity(tmp_path: Path) -> None:
    control = _controller(tmp_path)
    control.reconcile("proof")
    assert control.owned == {IDENTITY: "proof"}
    assert control.engine.calls == [f"GET /containers/{control.name('proof')}/json"]


def test_identity_remains_registered_when_receipt_write_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    control = _controller(tmp_path)

    def failed_save(*_args: object) -> None:
        message = "artifact directory unavailable"
        raise OSError(message)

    monkeypatch.setattr(control, "save", failed_save)
    with pytest.raises(OSError, match="artifact directory"):
        control.register(IDENTITY, "proof")
    assert control.owned == {IDENTITY: "proof"}


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("export/fixture.key", tarfile.REGTYPE),
        ("export/../../outside.json", tarfile.REGTYPE),
        ("export/boundary.json", tarfile.SYMTYPE),
    ],
)
def test_export_rejects_tls_keys_traversal_and_links(tmp_path: Path, name: str, kind: bytes) -> None:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        member = tarfile.TarInfo(name)
        member.type = kind
        archive.addfile(member)
    with pytest.raises(ValueError, match="Unapproved export"):
        q.export_archive(buffer.getvalue(), tmp_path)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("mutation", ["missing-boundary", "wrong-schema", "checks-string", "missing-extraction"])
def test_incomplete_or_substituted_proof_receipts_refuse(tmp_path: Path, mutation: str) -> None:
    records: dict[str, Json] = {
        "boundary.json": {"profile": q.PROFILE_NAME},
        "static-receipt.json": {"profile": "scout-static-extract@1", "status": "passed", "checks": ["measured"]},
        "fetch-receipt.json": {
            "schema": "scout-fetch-local-proof@1",
            "status": "passed",
            "checks": ["measured"],
            "extraction": "passed_with_explicit_runtime_profile",
        },
        "authority-receipt.json": {
            "schema": "scout-network-authority-local-proof@1",
            "status": "passed",
            "checks": ["measured"],
        },
    }
    if mutation == "missing-boundary":
        records.pop("boundary.json")
    elif mutation == "wrong-schema":
        records["authority-receipt.json"]["schema"] = "scout-fetch-local-proof@1"
    elif mutation == "checks-string":
        records["static-receipt.json"]["checks"] = "not a measured list"
    else:
        records["fetch-receipt.json"].pop("extraction")
    for name, record in records.items():
        (tmp_path / name).write_text(json.dumps(record))
    with pytest.raises(ValueError, match=r"closure|receipt|extraction"):
        q.validate_exports(tmp_path)
