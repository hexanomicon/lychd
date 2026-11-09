"""Fail-closed qualification profile and owned-container settlement contracts."""

from __future__ import annotations

import copy
import io
import json
import socket
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
    assert qualification["profile"] in q.PROFILE_ENGINES
    if qualification["profile"] == q.CI_PROFILE_NAME:
        q.validate_engine(qualification["engine"], q.CI_PROFILE_NAME)
        custody = qualification["apparmor_custody"]
        assert custody["phase"] == "removed"
        assert custody["restriction_before"] == custody["restriction_after"] == "1"
        assert custody["kernel"]["name"] == q.CI_APPARMOR_NAME
        assert custody["kernel"]["mode"] == "unconfined"
        assert custody["kernel"]["raw_sha256"] == custody["compiled_sha256"]
        assert custody["source_sha256"] == qualification["source_sha256"]["scripts/scout-qualification.apparmor"]
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
    } | ({"scripts/scout-qualification.apparmor"} if qualification["profile"] == q.CI_PROFILE_NAME else set())
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


@pytest.mark.parametrize("profile", [q.PROFILE_NAME, q.CI_PROFILE_NAME])
def test_each_profile_requires_its_exact_engine_without_cross_adoption(profile: str) -> None:
    engine, api, runtime = q.PROFILE_ENGINES[profile]
    measured: Json = {"Version": engine, "ApiVersion": api, "Components": [{"Name": "runc", "Version": runtime}]}
    q.validate_engine(measured, profile)
    other = q.CI_PROFILE_NAME if profile == q.PROFILE_NAME else q.PROFILE_NAME
    with pytest.raises(ValueError, match="Unsupported"):
        q.validate_engine(measured, other)
    measured["Components"][0]["Version"] = "0.0.0"
    with pytest.raises(ValueError, match="Unsupported"):
        q.validate_engine(measured, profile)


def test_ci_admission_preserves_c2_and_unrelated_bootstrap_settings() -> None:
    baseline = _host()
    local = q.derive_profile(baseline, "{}")
    ci = q.derive_profile(baseline, "{}", qualification_profile=q.CI_PROFILE_NAME)
    assert "apparmor=unconfined" not in local["SecurityOpt"]
    assert ci["SecurityOpt"] == [*local["SecurityOpt"], "apparmor=" + q.CI_APPARMOR_NAME]
    assert "/proc/sys/crypto" in local["MaskedPaths"]
    assert ci["MaskedPaths"] == [path for path in local["MaskedPaths"] if path != "/proc/sys/crypto"]
    assert {key: value for key, value in ci.items() if key not in {"SecurityOpt", "MaskedPaths"}} == {
        key: value for key, value in local.items() if key not in {"SecurityOpt", "MaskedPaths"}
    }
    with pytest.raises(ValueError, match="Unknown qualification"):
        q.derive_profile(baseline, "{}", qualification_profile="unreviewed")


@pytest.mark.parametrize(
    "endpoint", ["tcp://127.0.0.1:2375", "unix://remote/tmp/docker.sock", "/tmp/docker.sock", "unix:///tmp/%2f.sock"]
)
def test_ci_refuses_remote_ambiguous_or_implicit_endpoints(endpoint: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    monkeypatch.setenv("LYCHD_SCOUT_DOCKER_SOCKET", endpoint)
    monkeypatch.setenv("DOCKER_HOST", endpoint)
    with pytest.raises(ValueError, match="explicit local Unix"):
        q.controller_socket(q.CI_PROFILE_NAME)


def test_ci_binds_only_matching_actual_socket_and_refuses_context_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "engine.sock"
    endpoint = "unix://" + str(path)
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    monkeypatch.setenv("LYCHD_SCOUT_DOCKER_SOCKET", endpoint)
    monkeypatch.setenv("DOCKER_HOST", endpoint)
    path.write_text("not a socket")
    with pytest.raises(ValueError, match="Unsafe Docker socket"):
        q.controller_socket(q.CI_PROFILE_NAME)
    path.unlink()
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(str(path))
        assert q.controller_socket(q.CI_PROFILE_NAME) == str(path)
        monkeypatch.setenv("DOCKER_HOST", "unix:///different.sock")
        with pytest.raises(ValueError, match="endpoints differ"):
            q.controller_socket(q.CI_PROFILE_NAME)
        monkeypatch.setenv("DOCKER_HOST", endpoint)
        monkeypatch.setenv("DOCKER_CONTEXT", "another-engine")
        with pytest.raises(ValueError, match="context override"):
            q.controller_socket(q.CI_PROFILE_NAME)


def test_c2_does_not_adopt_ci_socket_or_remote_docker_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    monkeypatch.setenv("LYCHD_SCOUT_DOCKER_SOCKET", "unix:///tmp/engine.sock")
    with pytest.raises(ValueError, match="fixed local Docker"):
        q.controller_socket(q.PROFILE_NAME)
    monkeypatch.delenv("LYCHD_SCOUT_DOCKER_SOCKET")
    monkeypatch.setenv("DOCKER_HOST", "tcp://remote:2375")
    with pytest.raises(ValueError, match="endpoint mismatch"):
        q.controller_socket(q.PROFILE_NAME)


def test_named_policy_fingerprint_detects_replacement_mode_and_ambiguous_identity(tmp_path: Path) -> None:
    profile = tmp_path / "owned.1"
    profile.mkdir()
    (profile / "name").write_text(q.CI_APPARMOR_NAME)
    (profile / "mode").write_text("unconfined")
    (profile / "raw_data").write_bytes(b"compiled fixture policy")
    first = q.apparmor_fingerprint(tmp_path)
    assert first is not None
    assert first["raw_sha256"] == sha256(b"compiled fixture policy").hexdigest()
    (profile / "raw_data").write_bytes(b"replaced policy")
    assert q.apparmor_fingerprint(tmp_path) != first
    (profile / "mode").write_text("complain")
    with pytest.raises(ValueError, match="Unexpected AppArmor profile mode"):
        q.apparmor_fingerprint(tmp_path)
    (profile / "mode").write_text("unconfined")
    duplicate = tmp_path / "foreign.2"
    duplicate.mkdir()
    (duplicate / "name").write_text(q.CI_APPARMOR_NAME)
    with pytest.raises(ValueError, match="Ambiguous AppArmor profile"):
        q.apparmor_fingerprint(tmp_path)


@pytest.mark.parametrize("labelled", [False, True])
def test_policy_cleanup_refuses_foreign_profile_users_or_unsettled_owned_containers(
    tmp_path: Path, labelled: bool
) -> None:
    class Engine:
        def request(self, _method: str, path: str) -> object:
            if path == "/containers/json?all=1":
                return [{"Id": IDENTITY}]
            return {
                "Config": {"Labels": {q.LABEL: "owner"} if labelled else {}},
                "AppArmorProfile": "other" if labelled else q.CI_APPARMOR_NAME,
            }

    with pytest.raises(ValueError, match="still uses qualification authority"):
        q.ensure_apparmor_unused(Engine(), tmp_path)


def test_policy_cleanup_refuses_missing_terminal_result_before_daemon_queries(tmp_path: Path) -> None:
    occurrence = tmp_path / "scout-qualification.fixture"
    occurrence.mkdir()
    (occurrence / "occurrence.json").write_text("{}")

    class Engine:
        def request(self, *_args: object) -> object:
            raise AssertionError("An unresolved controller must stop cleanup before daemon effects")

    with pytest.raises(ValueError, match="no terminal result"):
        q.ensure_apparmor_unused(Engine(), tmp_path)


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
