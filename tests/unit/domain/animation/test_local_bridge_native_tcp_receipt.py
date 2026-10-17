"""Check the dated native TCP receipt offline without opening runtime surfaces."""

# The historical metadata module owns the shared bounded source/dependency lists.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import re
import tomllib
from hashlib import sha256
from importlib.metadata import version

from tests.unit.domain.animation import test_local_bridge_receipt as historical

_ROOT = historical._ROOT
_RECEIPT = _ROOT / "tests/fixtures/animator/local-bridge-vllm-native-tcp.json"
_NATIVE_TEST = "tests/integration/test_local_bridge_native_tcp.py"
_NATIVE_SOURCES = {
    "src/lychd/__main__.py",
    "src/lychd/cli/base.py",
    "src/lychd/cli/commands.py",
    "src/lychd/config/settings/server.py",
    "src/lychd/cli/operator.py",
    "src/lychd/system/operator/__init__.py",
    "src/lychd/system/operator/models.py",
    "src/lychd/system/operator/composition.py",
    "src/lychd/system/operator/control.py",
    "src/lychd/interface/server.py",
    "src/lychd/interface/web/altar.py",
    "src/lychd/interface/web/orb.py",
    "tests/integration/test_local_bridge_process_restart.py",
    _NATIVE_TEST,
    "tests/integration/test_server_process.py",
    "tests/unit/domain/animation/test_local_bridge_native_tcp.py",
}
_NATIVE_DEPENDENCIES = (*historical._CORE_DEPENDENCIES, "click", "granian", "python-dotenv")


def test_native_tcp_receipt_preserves_its_observed_scope_and_privacy() -> None:
    text = _RECEIPT.read_text()
    receipt = json.loads(text)
    assert receipt["schema"] == "local-bridge-vllm-native-tcp@1"
    assert receipt["record_kind"] == "sanitized_public_local_bridge_native_tcp_qualification"
    assert receipt["qualification_date"] == "2026-10-17"
    assert receipt["status"] == "passed"
    assert "The optional thinking policy was omitted" in receipt["identity_boundary"]
    assert receipt["source_identity"] == {
        "revision_observed": "bf1162f7df7ceaee75c0ab1c2f3180243b7edf94",
        "clean_checkout_observed": False,
        "atomic_transitive_closure_attested": False,
        "scope": "bounded-critical-source-and-test-fingerprints",
    }
    execution = receipt["execution"]
    assert execution["application"] == "production-source-CLI-two-native-TCP-boots"
    assert execution["http"] == "real-loopback-TCP-httpx2-client"
    assert execution["server"] == "Granian-embedded-owned-native-launcher"
    assert execution["lifespan"] == "test-local-wrapper-yields-real-production-lifespan"
    assert execution["runtime_actuator"] == "refusing-fixture-port"
    assert execution["engine_disposal"] == "supplemental-test-cleanup-after-normal-CLI-return"
    assert receipt["authentication"] == {
        "authenticated_TCP_ready_on_both_boots": True,
        "refused_message_admissions": {
            "no_auth": 401,
            "wrong_auth": 401,
            "foreign_origin": 403,
            "missing_csrf": 403,
        },
        "durable_runs_before_admitted_turn": 0,
        "model_posts_before_admitted_turn": 0,
    }
    assert receipt["freshness_check"] == "offline-metadata-source-and-selected-dependency-check-only"
    assert (
        "Updating metadata or hashes alone does not requalify changed critical inputs." in receipt["identity_boundary"]
    )
    for name in ("retained_history_sha256", "retained_turns_sha256"):
        assert re.fullmatch(r"[0-9a-f]{64}", receipt[name])
    assert not re.search(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", text)
    assert not any(
        forbidden in text
        for forbidden in (
            "://",
            "/home/",
            "/tmp/",  # noqa: S108 - refuse private host material
            "/run/user/",
            "127.0.0.1",
            "::1",
            "password",
            "username",
            '"pid"',
            '"parent_pid"',
            '"group"',
            '"start_time"',
            '"response_id"',
            '"session_id"',
            '"run_id"',
            '"container_id"',
            '"prompt"',
            '"message_history"',
        )
    )


def test_native_tcp_receipt_requires_normal_processes_and_identical_retained_state() -> None:
    receipt = json.loads(_RECEIPT.read_text())
    processes = receipt["processes"]
    assert processes["application_children"] == 2
    assert processes["start_method"] == "spawn"
    assert all(
        processes[name]
        for name in (
            "sequential",
            "distinct_child_identities_checked",
            "parent_identity_checked",
            "start_time_identity_checked",
            "first_child_exited_before_second_start",
        )
    )
    assert processes["exit_codes"] == [0, 0]
    assert processes["forced_termination"] == [False, False]
    for name in ("joined", "reaped", "group_absent", "listener_closed", "CLI_returned", "production_lifespan_closed"):
        assert processes[name] == [True, True]
    assert processes["shutdown"] == "test-owned-SIGTERM-and-normal-production-CLI-return"
    assert processes["authenticated_host_stop_exercised"] is False
    outcome = receipt["outcome"]
    assert outcome["boots"] == 2
    assert outcome["model_posts_by_boot"] == [1, 0]
    assert outcome["model_posts"] == outcome["model_responses"] == outcome["structured_output_calls"] == 1
    assert outcome["settled_turns"] == 2
    assert outcome["run_status"] == "DONE"
    assert (outcome["pattern_id"], outcome["pattern_revision"]) == ("bridge_chat", "2")
    assert outcome["structured_output_name"] == "final_result"
    assert outcome["wire_finish_reason"] == "tool_calls"
    assert all(
        outcome[name]
        for name in (
            "manifest_exact_match",
            "warm_on_both_boots",
            "retained_history_identical",
            "retained_turns_identical",
            "substrate_unpublished",
            "supplemental_engine_disposal_completed",
        )
    )
    assert all(
        outcome[name] == 0 for name in ("active_leases_after_each_boot", "model_boundary_violations", "lifecycle_calls")
    )
    assert outcome["external_compute_unknown"] is False


def test_native_tcp_receipt_keeps_model_resource_and_cleanup_limits_explicit() -> None:
    receipt = json.loads(_RECEIPT.read_text())
    assert receipt["model"] == {
        "served_model_id": "Qwen3.8-27B",
        "model_bytes_attested": False,
        "context_tokens": 4096,
        "max_output_tokens": 256,
        "cooperative_deadline_seconds": 30,
        "maximum_model_posts": 3,
        "concurrent_runs": 1,
    }
    limits = {
        "AS": [3 * 1024**3] * 2,
        "CPU": [90, 100],
        "FSIZE": [8 * 1024**2] * 2,
        "NOFILE": [256] * 2,
        "CORE": [0, 0],
    }
    assert receipt["native_resources"] == {
        "scope": "per-process-after-interpreter-and-module-startup",
        "observed_limits_by_boot": [limits, limits],
        "aggregate_CPU_RAM_GPU_limit_attested": False,
    }
    database = receipt["database"]
    assert database["created_containers"] == 1
    assert database["container_removed"] is True
    assert database["published_interface"] == "literal-loopback-only"
    assert database["required_resources"] == {"mem_limit": "512m", "nano_cpus": 1_000_000_000, "pids_limit": 128}
    assert database["effective_cgroup_limits"] == {
        "memory_bytes": 512 * 1024**2,
        "cpu_quota_period_microseconds": [100_000, 100_000],
        "pids": 128,
    }
    assert database["GPU_device_requests"] is False
    assert "GPU_devices" not in database
    assert database["removed_after_two_observed_absent_native_groups"] is True
    runner = receipt["runner"]
    assert runner["pytest_selected"] == runner["pytest_passed"] == 1
    assert runner["outer_timeout_seconds"] == 250
    assert runner["operator_unit_stop_timeout_seconds"] == 5
    assert runner["coordinator_deadline_seconds"] == 240
    assert runner["test_wait_seconds"] == 210
    assert runner["coordinator_cleanup_reserve_seconds"] == 30
    assert runner["ryuk_disabled_in_runner_process"] is True
    assert runner["default_make_ryuk_profile"] is False
    assert runner["native_test_removal_guard_exercised"] is True
    assert "native_removal_guard_observed" not in runner
    assert runner["cleanup_verified"] is True
    assert runner["timed_out"] is runner["mutant_applied"] is False
    assert all(
        runner[name] == 0
        for name in (
            "pytest_failed",
            "pytest_errors",
            "pytest_skipped",
            "returncode",
            "remaining_containers",
            "remaining_volumes",
        )
    )
    assert {
        "installed-command-or-caged-Vessel",
        "Vessel-network-namespace",
        "managed-model-lifecycle",
        "process-crash-recovery",
        "selected-qwen3.8-non-thinking-policy",
        "useful-task-workload",
        "real-browser-and-accessibility",
        "browser-SSE-and-reconnect",
        "authenticated-host-stop",
        "autonomous-software-labor",
        "aggregate-native-resource-containment",
    } <= set(receipt["unexercised"])


def test_native_tcp_receipt_matches_qualified_sources_and_provenance() -> None:
    receipt = json.loads(_RECEIPT.read_text())
    assert set(receipt["source_fingerprints"]) == historical._SOURCES | _NATIVE_SOURCES
    evidence = receipt["qualification_evidence"]
    assert evidence["native_test_sha256_before_trial"] == receipt["source_fingerprints"][_NATIVE_TEST]
    assert set(evidence) == {
        "application_receipt_sha256",
        "candidate_manifest_sha256",
        "coordinator_receipt_sha256",
        "coordinator_source_sha256",
        "model_profile_sha256",
        "native_test_sha256_before_trial",
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


def test_native_tcp_receipt_matches_selected_dependencies() -> None:
    receipt = json.loads(_RECEIPT.read_text())
    dependencies = {name: version(name) for name in _NATIVE_DEPENDENCIES}
    # Optional SDKs use exact lock entries in ordinary offline CI.
    locked = tomllib.loads((_ROOT / "uv.lock").read_text())
    dependencies.update(
        {item["name"]: item["version"] for item in locked["package"] if item["name"] in {"docker", "testcontainers"}}
    )
    assert receipt["dependency_versions"] == dependencies
