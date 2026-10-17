"""Check the process trial's scope/freshness and an inert spawned-child refusal."""

# The historical metadata module owns the shared bounded source/dependency lists.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import re
import sys
import tomllib
from hashlib import sha256
from importlib.metadata import version

import pytest
from scripts.local_model_probe import ProbeProfile

from lychd.config.settings.root import SettingsSnapshot
from tests.integration import test_local_bridge_process_restart as runtime
from tests.unit.domain.animation import test_local_bridge_receipt as historical

_ROOT = historical._ROOT
_RECEIPT = _ROOT / "tests/fixtures/animator/local-bridge-vllm-process-restart.json"
_PROCESS_TEST = "tests/integration/test_local_bridge_process_restart.py"


def test_process_receipt_preserves_qualification_and_privacy_boundary() -> None:
    text = _RECEIPT.read_text()
    receipt = json.loads(text)
    assert receipt["schema"] == "local-bridge-vllm-process-restart@1"
    assert receipt["qualification_date"] == "2026-10-17"
    assert receipt["status"] == "passed"
    assert "The optional thinking policy was omitted" in receipt["identity_boundary"]
    assert receipt["source_identity"] == {
        "base_revision_declared": "bf1162f7df7ceaee75c0ab1c2f3180243b7edf94",
        "clean_checkout_attested": False,
        "atomic_transitive_closure_attested": False,
        "scope": "bounded-critical-source-and-test-fingerprints",
    }
    execution = receipt["execution"]
    assert execution["application"] == "real-create_app-two-spawned-processes"
    assert execution["http"] == "litestar.testing.TestClient"
    assert execution["runtime_actuator"] == "refusing-fixture-port"
    processes = receipt["processes"]
    assert processes["application_children"] == 2
    assert processes["start_method"] == "spawn"
    assert all(
        processes[key]
        for key in (
            "sequential",
            "distinct_child_identities_checked",
            "parent_identity_checked",
            "first_child_exited_before_second_start",
        )
    )
    assert processes["shutdown"] == "clean-TestClient-lifespan"
    assert processes["exit_codes"] == [0, 0]
    assert processes["forced_termination"] == [False, False]
    assert processes["joined"] == processes["reaped"] == [True, True]
    outcome = receipt["outcome"]
    assert outcome["boots"] == 2
    assert outcome["model_posts_by_boot"] == [1, 0]
    assert outcome["model_posts"] == outcome["model_responses"] == outcome["structured_output_calls"] == 1
    assert outcome["settled_turns"] == 2
    assert outcome["run_status"] == "DONE"
    assert all(
        outcome[key]
        for key in (
            "manifest_exact_match",
            "warm_on_both_boots",
            "retained_history_identical",
            "retained_turns_identical",
            "substrate_unpublished",
            "engine_disposed",
        )
    )
    assert all(
        outcome[key] == 0 for key in ("active_leases_after_each_boot", "model_boundary_violations", "lifecycle_calls")
    )
    assert receipt["model"]["model_bytes_attested"] is False
    assert receipt["model"]["maximum_model_posts"] == 3
    assert receipt["database"]["created_containers"] == 1
    assert receipt["database"]["container_removed"] is True
    assert receipt["database"]["required_resources"] == {
        "mem_limit": "512m",
        "nano_cpus": 1_000_000_000,
        "pids_limit": 128,
    }
    runner = receipt["runner"]
    assert runner["pytest_selected"] == runner["pytest_passed"] == runner["maximum_container_creates"] == 1
    assert runner["cleanup_verified"] is True
    assert all(
        runner[key] == 0
        for key in (
            "pytest_failed",
            "pytest_errors",
            "pytest_skipped",
            "remaining_containers",
            "remaining_captured_containers",
            "unresolved_creates",
        )
    )
    assert runner["outer_timeout_seconds"] == 250
    assert runner["operator_unit_stop_timeout_seconds"] == 5
    assert runner["coordinator_deadline_seconds"] == 240
    assert runner["test_wait_seconds"] == 210
    assert runner["coordinator_cleanup_reserve_seconds"] == 30
    assert {
        "process-crash-recovery",
        "selected-qwen3.8-non-thinking-policy",
        "useful-task-workload",
        "Granian-serving",
        "browser-and-full-accessibility",
        "managed-model-lifecycle",
    } <= set(receipt["unexercised"])
    assert receipt["freshness_check"] == "offline-metadata-source-and-selected-dependency-check-only"
    for key in ("retained_history_sha256", "retained_turns_sha256"):
        assert re.fullmatch(r"[0-9a-f]{64}", receipt[key])
    assert not any(
        forbidden in text
        for forbidden in (
            "://",
            "/home/",
            "/tmp/",  # noqa: S108 - refuse private host material
            "127.0.0.1",
            "::1",
            "password",
            "username",
            '"pid"',
            '"parent_pid"',
            '"response_id"',
            '"session_id"',
            '"run_id"',
            '"container_id"',
            '"prompt"',
            '"message_history"',
        )
    )


def test_process_receipt_matches_qualified_sources_and_provenance() -> None:
    receipt = json.loads(_RECEIPT.read_text())
    assert set(receipt["source_fingerprints"]) == historical._SOURCES | {_PROCESS_TEST}
    evidence = receipt["qualification_evidence"]
    assert evidence["process_test_sha256_before_trial"] == receipt["source_fingerprints"][_PROCESS_TEST]
    assert set(evidence) == {
        "application_receipt_sha256",
        "candidate_manifest_sha256",
        "coordinator_receipt_sha256",
        "coordinator_source_sha256",
        "model_profile_sha256",
        "process_test_sha256_before_trial",
        "pytest_log_sha256",
        "resource_launcher_source_sha256",
        "resource_receipt_sha256",
    }
    assert evidence["coordinator_source_sha256"] == "6c1505e1959442b2a9de0078a9c7e2d1f719c3a9d9cc97c26246cac6022daca8"
    assert (
        evidence["resource_launcher_source_sha256"]
        == "b8105f73913316031e7241529ff4676b8672ac106754d76b8daea209a18afa78"
    )
    for digest in evidence.values():
        assert re.fullmatch(r"[0-9a-f]{64}", digest)
    for path, digest in receipt["source_fingerprints"].items():
        assert sha256((_ROOT / path).read_bytes()).hexdigest() == digest, path


def test_process_receipt_matches_selected_dependencies() -> None:
    receipt = json.loads(_RECEIPT.read_text())
    dependencies = {name: version(name) for name in historical._CORE_DEPENDENCIES}
    # Container SDKs stay optional in ordinary CI; their exact lock entries still bind this trial.
    locked = tomllib.loads((_ROOT / "uv.lock").read_text())
    dependencies.update(
        {item["name"]: item["version"] for item in locked["package"] if item["name"] in {"docker", "testcontainers"}}
    )
    assert receipt["dependency_versions"] == dependencies


@pytest.mark.skipif(sys.platform != "linux", reason="the process proof uses Linux pipe bounds")
def test_spawn_refuses_invalid_snapshot_without_runtime_or_private_input_disclosure() -> None:
    marker = "private-input-must-not-escape-the-spawned-child"
    snapshot = SettingsSnapshot(payload=json.dumps({"unexpected_process_receipt_input": marker}))
    profile = ProbeProfile(
        base_url="http://127.0.0.1:1/v1",
        model_id="synthetic-inert-model",
        source_revision="0" * 40,
        context_tokens=1024,
        max_tokens=32,
        deadline_seconds=1,
    )
    # The strict snapshot schema refuses before Rune, service, DB or model construction.
    report = runtime._spawn_boot(snapshot, profile, None)
    assert report["outcome"] == "failed"
    assert report["error_type"] == "ValidationError"
    assert report["exitcode"] == 1
    assert report["joined"] is True
    assert report["reaped"] is True
    assert report["forced_termination"] is False
    assert report["model_posts"] == report["lifecycle_calls"] == 0
    assert report["boundary_violations"] == []
    assert report["substrate_unpublished"] is True
    assert report["engine_disposed"] is True
    assert report["start_method"] == "spawn"
    assert "retained" not in report
    assert report["error_file"] == "test_local_bridge_process_restart.py"
    assert report["error_line"] > 0
    assert marker not in json.dumps(report)
    assert "unexpected_process_receipt_input" not in json.dumps(report)
