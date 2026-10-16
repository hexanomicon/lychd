"""Guard dated installed metadata/privacy; never qualify the current source or host."""

from __future__ import annotations

import copy
import json
import math
import re
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import pytest

_ROOT = Path(__file__).resolve().parents[4]
_RECEIPT = _ROOT / "tests/fixtures/animator/local-bridge-vllm-installed-0cc0988.json"
_REVISION = "0cc09889731dd83ec4aa9495a50a77684636a9bc"
_CONTRACT = "3593cf40918aa78163eb69a76add31cf048cdda5"
_CRITICAL = {
    "src/lychd/system/services/runtime_topology.py": "35e4b1828350ad9d033d207dba41e65614192dec156ed769ddd2d096bd3e3587",
    "src/lychd/domain/animation/transmute.py": "09344e7f0890d4b2f74daece7f4b6e0bdb73c7c4945dc132acb129a5d1f10969",
}
_SHAPES = {
    "source_identity": {
        "revision_observed": str,
        "client_contract_revision_declared": str,
        "archive_host_image_file_count": int,
        "archive_host_image_map_sha256": str,
        "archive_host_image_maps_match": bool,
        "current_checkout_qualified": bool,
        "atomic_transitive_closure_attested": bool,
        "installed_dependency_versions_attested": bool,
    },
    "installation": {
        "vessel_image_id": str,
        "model_image_id": str,
        "host_cli": str,
        "loaded_owned_units": int,
        "loaded_covens": int,
        "same_Core_and_shared_pod_observed": bool,
        "core_boot_returncode": int,
        "bind_returncode": int,
        "loaded_topology_returncode": int,
        "application_source_root_owned_readonly": bool,
    },
    "host": {
        "kernel": str,
        "systemd": str,
        "podman": str,
        "gpu_model": str,
        "gpu_count": int,
        "gpu_memory_MiB_each": int,
        "gpu_driver": str,
        "version_observation": str,
    },
    "profile": {
        "served_model_id": str,
        "runtime": str,
        "dedicated": bool,
        "persistent_resident": bool,
        "configured_max_context": int,
        "configured_max_output_tokens": int,
        "admitted_runs": int,
        "model_bytes_attested": bool,
        "exclusive_operator_custody": str,
        "model_restart_policy": str,
        "compiled_model_manifest_sha256": str,
        "config_sha256": str,
        "rune_sha256": str,
    },
    "activation": {
        "route": str,
        "action": str,
        "launches": int,
        "evictions": int,
        "old_external_model_stopped_before_request": bool,
        "cold_before_request": bool,
        "client_returncode": int,
        "client_timed_out": bool,
        "client_elapsed_seconds": float,
        "completed_intent_and_custody_reconciled": bool,
        "exact_model_WARM_observed": bool,
        "inventory_observed_from_Core_pod": bool,
        "server_cancellation_inferred": bool,
    },
    "bridge": {
        "pattern": str,
        "pattern_digest": str,
        "run_status": str,
        "observed_new_runs": int,
        "submission_POSTs": int,
        "verification_POSTs": int,
        "model_POSTs_observed": int,
        "model_HTTP_status": int,
        "model_stop_completions": int,
        "zero_model_counters_before_run": bool,
        "stable_same_boot_API_reads": bool,
        "structured_API_projection_verified": bool,
        "Orb_account_verified": bool,
        "visible_history_sha256": str,
        "Orb_account_sha256": str,
        "queues_depth_after": int,
        "queues_active_after": int,
        "active_leases_after": int,
        "model_running_after": int,
        "model_waiting_after": int,
        "raw_model_history_exposed": bool,
        "raw_Run_result_exposed": bool,
        "restart_qualified": bool,
    },
    "resources": {
        "aggregate_CPU_RAM_GPU_containment_attested": bool,
        "native_fixture_rlimits_apply": bool,
        "historical_Docker_database_caps_apply": bool,
    },
}
_TOP_FIELDS = {
    "schema": str,
    "record_kind": str,
    "qualification_date": str,
    "status": str,
    "metadata_check": str,
    "identity_boundary": str,
    "source_fingerprints": dict,
    "qualification_evidence_sha256": dict,
    "unexercised": list,
    **dict.fromkeys(_SHAPES, dict),
}


_PASSED_EXPECTED = {
    "source_identity": {
        "archive_host_image_file_count": 447,
        "archive_host_image_map_sha256": "ab0eda1f293162363b2d62b21730de8dd6dc925c886b2e86513c1c8b51364620",
        "archive_host_image_maps_match": True,
        "atomic_transitive_closure_attested": False,
        "client_contract_revision_declared": "3593cf40918aa78163eb69a76add31cf048cdda5",
        "current_checkout_qualified": False,
        "installed_dependency_versions_attested": False,
        "revision_observed": "0cc09889731dd83ec4aa9495a50a77684636a9bc",
    },
    "installation": {
        "application_source_root_owned_readonly": True,
        "bind_returncode": 0,
        "core_boot_returncode": 0,
        "host_cli": "noneditable-installed-production-CLI",
        "loaded_covens": 0,
        "loaded_owned_units": 8,
        "loaded_topology_returncode": 0,
        "model_image_id": "sha256:8a5213701489d9704e6fa18f8d09f7b93ff59c55484307e26fe49407dd696817",
        "same_Core_and_shared_pod_observed": True,
        "vessel_image_id": "sha256:d1efafe3b243d99de53454f87a25e88cc9634cf8fcb2e9d76c2047204c61e359",
    },
    "host": {
        "gpu_count": 2,
        "gpu_driver": "610.57.04",
        "gpu_memory_MiB_each": 24576,
        "gpu_model": "NVIDIA GeForce RTX 3090",
        "kernel": "7.1.8-1-default",
        "podman": "6.0.2",
        "systemd": "261.2",
        "version_observation": "earlier-same-campaign",
    },
    "profile": {
        "admitted_runs": 1,
        "compiled_model_manifest_sha256": "8dd19fa598a04b822241b2505936128934942d2e7295d3b59d23711654b1e420",
        "config_sha256": "d2ab463e29d1558835b0d475be990f06effd723038a7007ec3ab2ddda72f5bf6",
        "configured_max_context": 8192,
        "configured_max_output_tokens": 1024,
        "dedicated": True,
        "exclusive_operator_custody": "external-condition",
        "model_bytes_attested": False,
        "model_restart_policy": "always",
        "persistent_resident": False,
        "rune_sha256": "7b7188a629790c36e058cdd94d47ce5e6917161575a9a31d4a04813ea6605f64",
        "runtime": "vllm",
        "served_model_id": "Qwen3.8-27B",
    },
    "activation": {
        "action": "HARD_SWAP",
        "client_elapsed_seconds": 223.853,
        "client_returncode": 0,
        "client_timed_out": False,
        "cold_before_request": True,
        "completed_intent_and_custody_reconciled": True,
        "evictions": 0,
        "exact_model_WARM_observed": True,
        "inventory_observed_from_Core_pod": True,
        "launches": 1,
        "old_external_model_stopped_before_request": True,
        "route": "/orchestrator/activate",
        "server_cancellation_inferred": False,
    },
    "bridge": {
        "Orb_account_sha256": "563b5e0bea7feb9b8f00e30c9be106f69f09ad732fd0fbdbb1fccd8b58d2cdbe",
        "Orb_account_verified": True,
        "active_leases_after": 0,
        "model_HTTP_status": 200,
        "model_POSTs_observed": 1,
        "model_running_after": 0,
        "model_stop_completions": 1,
        "model_waiting_after": 0,
        "observed_new_runs": 1,
        "pattern": "bridge_chat@2",
        "pattern_digest": "aef1cd98c97ec921e9db1d3169955ec73456376907b396d0d0f2429f84b692eb",
        "queues_active_after": 0,
        "queues_depth_after": 0,
        "raw_Run_result_exposed": False,
        "raw_model_history_exposed": False,
        "restart_qualified": False,
        "run_status": "DONE",
        "stable_same_boot_API_reads": True,
        "structured_API_projection_verified": True,
        "submission_POSTs": 1,
        "verification_POSTs": 0,
        "visible_history_sha256": "db5c27eac299adda399f2ff465d49fc53e2e36ecb28a7caee878210b8ffc1988",
        "zero_model_counters_before_run": True,
    },
    "resources": {
        "aggregate_CPU_RAM_GPU_containment_attested": False,
        "historical_Docker_database_caps_apply": False,
        "native_fixture_rlimits_apply": False,
    },
    "": {
        "schema": "installed-local-bridge-observation@1",
        "record_kind": "sanitized-dated-installed-operator-observation",
        "qualification_date": "2026-10-16",
        "status": "passed",
        "metadata_check": "offline-dated-observation-metadata-and-privacy-only",
        "identity_boundary": "Historical 0cc observation; a changed compiler, attestor or installed artifact "
        "requires its own same-source qualification. Metadata edits do not requalify changed "
        "inputs.",
    },
}

_HISTORICAL_MAP_DIGESTS = {
    "source_fingerprints": "b58aff63cb2185a2bf48218b764046e23f41d9ebee153b2cedaaec98f06f7a99",
    "qualification_evidence_sha256": "57eefddf4daa3445d76bd8dffa074f9f66b96cead6d342a8021653a6b987684a",
}

_UNEXERCISED = frozenset(
    [
        "current-checkout-installed-body",
        "Coven-topology",
        "full-caged-public-stop",
        "managed-model-shutdown",
        "compensation-and-crash-recovery",
        "installed-restart-persistence",
        "raw-model-history",
        "real-browser-login-navigation-SSE",
        "live-cancellation",
        "shared-load-and-capacity",
        "aggregate-CPU-RAM-GPU-containment",
        "model-byte-identity",
        "general-tools",
        "autonomy-and-evolution",
    ]
)

_SUCCESS_FIELDS = tuple(
    (section, key, value) for section, fields in _PASSED_EXPECTED.items() for key, value in fields.items()
)


def _shape(value: Any, fields: dict[str, type]) -> None:
    assert type(value) is dict
    mapping = cast("dict[str, Any]", value)
    assert set(mapping) == set(fields)
    assert all(type(mapping[name]) is expected for name, expected in fields.items())


def _privacy(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in cast("dict[object, Any]", value).items():
            assert isinstance(key, str)
            assert key.lower() not in {
                "pid",
                "pgid",
                "session_id",
                "run_id",
                "response_id",
                "container_id",
                "transition_id",
                "prompt",
                "answer",
                "credential",
                "password",
                "authorization",
                "cookie",
                "token",
            }
            _privacy(key)
            _privacy(child)
    elif isinstance(value, list):
        for child in cast("list[Any]", value):
            _privacy(child)
    elif isinstance(value, str):
        assert not re.search(r"[a-z][a-z0-9+.-]*://|127\.0\.0\.1|::1", value, re.IGNORECASE)
        assert not re.search(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", value, re.IGNORECASE)
        assert not re.search(
            r"authorization|password\s*[:=]|bearer\s|basic\s|caged-bridge-|prompt\s+(?:bytes|text|content)",
            value,
            re.IGNORECASE,
        )
        assert not re.search(r"[a-z]:[\\/]|\\\\", value, re.IGNORECASE)
        if value != "/orchestrator/activate":
            assert not re.search(r"(?<![\w.-])/[\w.-]+", value)


def _validate(receipt: Any) -> None:
    _shape(receipt, _TOP_FIELDS)
    _privacy(receipt)
    for name, fields in _SHAPES.items():
        _shape(receipt[name], fields)
        for key, value in receipt[name].items():
            if type(value) is int:
                assert value >= 0
            if type(value) is float:
                assert math.isfinite(value)
                assert value >= 0
            if key.endswith(("_sha256", "_digest")):
                assert isinstance(value, str)
                assert re.fullmatch(r"[0-9a-f]{64}", value)
    # The dated pass is a conjunction: shape-valid counterfactuals cannot keep it.
    for section, expected in _PASSED_EXPECTED.items():
        actual = receipt[section] if section else receipt
        assert all(actual[key] == value for key, value in expected.items()), section
    fingerprints = receipt["source_fingerprints"]
    assert _CRITICAL.items() <= fingerprints.items()
    for path, digest in fingerprints.items():
        assert re.fullmatch(r"src/lychd/[a-zA-Z0-9_/]+\.(?:py|jinja)", path)
        assert isinstance(digest, str)
        assert re.fullmatch(r"[0-9a-f]{64}", digest)
    for name, wanted in _HISTORICAL_MAP_DIGESTS.items():
        mapping = receipt[name]
        assert all(isinstance(key, str) and isinstance(value, str) for key, value in mapping.items())
        assert all(re.fullmatch(r"[0-9a-f]{64}", value) for value in mapping.values())
        canonical = json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()
        assert sha256(canonical).hexdigest() == wanted
    evidence = receipt["qualification_evidence_sha256"]
    assert all(re.fullmatch(r"[a-z_]+", key) for key in evidence)
    assert all(isinstance(value, str) for value in receipt["unexercised"])
    assert len(receipt["unexercised"]) == len(_UNEXERCISED)
    assert set(receipt["unexercised"]) == _UNEXERCISED


def _decode(text: str) -> dict[str, Any]:
    def unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        mapping = dict(pairs)
        if len(mapping) != len(pairs):
            message = "Duplicate receipt field"
            raise ValueError(message)
        return mapping

    return json.loads(text, object_pairs_hook=unique_fields)


def _receipt() -> dict[str, Any]:
    return _decode(_RECEIPT.read_text())


def test_dated_installed_observation_preserves_metadata_and_privacy() -> None:
    _validate(_receipt())


@pytest.mark.parametrize(
    "text", ['{"scope":"private prompt bytes","scope":"safe"}', '{"scope": {"value": 1, "value": 2}}']
)
def test_duplicate_fields_cannot_hide_unchecked_bytes(text: str) -> None:
    with pytest.raises(ValueError, match="Duplicate receipt field"):
        _decode(text)


@pytest.mark.parametrize(
    "private_text",
    [
        "/home/operator/private",
        "/opt/private",
        "data=/tmp/private",
        r"C:\private\value",
        r"\\host\private",
        "https://private.example/value",
        "http:\u002f\u002fprivate.example/value",
        "12345678-1234-1234-1234-123456789abc",
        "Authorization: Basic synthetic-private-value",
        "password=synthetic-private-value",
        "caged-bridge-" + "a" * 24,
        "prompt content synthetic-private-value",
    ],
)
def test_dated_metadata_refuses_private_text_in_an_existing_field(private_text: str) -> None:
    receipt = _receipt()
    receipt["identity_boundary"] += " " + private_text
    with pytest.raises(AssertionError):
        _validate(receipt)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("source_identity", "current_checkout_qualified", True),
        ("source_identity", "revision_observed", "f" * 40),
        ("source_identity", "client_contract_revision_declared", _REVISION),
        ("bridge", "observed_new_runs", True),
        ("activation", "client_returncode", False),
        ("activation", "client_elapsed_seconds", float("nan")),
        ("activation", "route", "/api/v1/orchestrator/activate"),
        ("bridge", "restart_qualified", True),
        ("resources", "aggregate_CPU_RAM_GPU_containment_attested", True),
        ("bridge", "session_id", "private-session"),
    ],
)
def test_dated_metadata_refuses_scope_type_or_unknown_field(section: str, key: str, value: Any) -> None:
    receipt = _receipt()
    receipt[section][key] = value
    with pytest.raises(AssertionError):
        _validate(receipt)


@pytest.mark.parametrize("path", tuple(_CRITICAL))
def test_dated_metadata_cannot_refresh_or_omit_critical_historical_inputs(path: str) -> None:
    receipt = _receipt()
    changed = copy.deepcopy(receipt)
    changed["source_fingerprints"][path] = "f" * 64
    with pytest.raises(AssertionError):
        _validate(changed)
    del receipt["source_fingerprints"][path]
    with pytest.raises(AssertionError):
        _validate(receipt)


@pytest.mark.parametrize(("section", "key", "expected"), _SUCCESS_FIELDS)
def test_every_dated_success_field_refuses_a_type_correct_counterfactual(section: str, key: str, expected: Any) -> None:
    receipt = _receipt()
    if type(expected) is bool:
        changed = not expected
    elif type(expected) is int:
        changed = expected + 1
    elif type(expected) is float:
        changed = expected + 1.0
    else:
        assert isinstance(expected, str)
        if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", expected):
            changed = ("0" if expected[0] != "0" else "1") + expected[1:]
        elif re.fullmatch(r"sha256:[0-9a-f]{64}", expected):
            changed = "sha256:" + ("0" if expected[7] != "0" else "1") + expected[8:]
        else:
            changed = expected + "-counterfactual"
    actual = receipt[section] if section else receipt
    actual[key] = changed
    with pytest.raises(AssertionError):
        _validate(receipt)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("installation", "core_boot_returncode", 1),
        ("installation", "loaded_topology_returncode", 1),
        ("installation", "same_Core_and_shared_pod_observed", False),
        ("activation", "client_timed_out", True),
        ("activation", "cold_before_request", False),
        ("activation", "inventory_observed_from_Core_pod", False),
        ("bridge", "submission_POSTs", 0),
        ("bridge", "model_HTTP_status", 500),
        ("bridge", "model_stop_completions", 0),
        ("bridge", "queues_depth_after", 1),
        ("bridge", "zero_model_counters_before_run", False),
        ("bridge", "structured_API_projection_verified", False),
        ("bridge", "Orb_account_verified", False),
    ],
)
def test_independent_review_contradictory_success_cases_refuse(section: str, key: str, value: Any) -> None:
    receipt = _receipt()
    receipt[section][key] = value
    with pytest.raises(AssertionError):
        _validate(receipt)


@pytest.mark.parametrize("name", tuple(_HISTORICAL_MAP_DIGESTS))
@pytest.mark.parametrize("change", ["extra", "missing", "different"])
def test_historical_source_and_evidence_maps_cannot_silently_change(name: str, change: str) -> None:
    receipt = _receipt()
    mapping = receipt[name]
    key = next(key for key in mapping if key not in _CRITICAL)
    if change == "extra":
        added = "src/lychd/synthetic_extra.py" if name == "source_fingerprints" else "synthetic_extra"
        mapping[added] = "0" * 64
    elif change == "missing":
        del mapping[key]
    else:
        mapping[key] = "0" * 64
    with pytest.raises(AssertionError):
        _validate(receipt)


@pytest.mark.parametrize("boundary", sorted(_UNEXERCISED))
def test_every_unqualified_boundary_is_retained(boundary: str) -> None:
    receipt = _receipt()
    receipt["unexercised"].remove(boundary)
    with pytest.raises(AssertionError):
        _validate(receipt)


def test_unqualified_boundary_list_refuses_duplicate_metadata() -> None:
    receipt = _receipt()
    receipt["unexercised"].append(receipt["unexercised"][0])
    with pytest.raises(AssertionError):
        _validate(receipt)
