"""Check historical qualification metadata and freshness without contacting a model or Docker."""

from __future__ import annotations

import json
import tomllib
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
_RECEIPT = _ROOT / "tests/fixtures/animator/local-bridge-vllm-runtime.json"
_SOURCES = {
    "scripts/local_model_probe.py",
    "src/lychd/app.py",
    "src/lychd/config/components.py",
    "src/lychd/config/constants.py",
    "src/lychd/config/settings/root.py",
    "src/lychd/config/settings/weaver.py",
    "src/lychd/domain/codex/local_access.py",
    "src/lychd/domain/codex/middleware.py",
    "src/lychd/domain/animation/model_factory.py",
    "src/lychd/domain/animation/services/loader.py",
    "src/lychd/domain/animation/services/registry.py",
    "src/lychd/domain/animation/services/adapters/runtimes/openai_compat.py",
    "src/lychd/domain/animation/services/adapters/surfaces.py",
    "src/lychd/domain/cortex/context.py",
    "src/lychd/domain/cortex/dispatcher.py",
    "src/lychd/domain/cortex/engine.py",
    "src/lychd/domain/cortex/graph_runner.py",
    "src/lychd/domain/cortex/leases.py",
    "src/lychd/domain/cortex/ledger.py",
    "src/lychd/agents/context_limits.py",
    "src/lychd/agents/factory.py",
    "src/lychd/agents/outputs.py",
    "src/lychd/agents/the_first_one.py",
    "src/lychd/agents/workflows/bridge_chat.py",
    "src/lychd/agents/workflows/nodes.py",
    "src/lychd/db/authority.py",
    "src/lychd/db/bootstrap.py",
    "src/lychd/db/engine.py",
    "src/lychd/db/sessions.py",
    "src/lychd/extensions/context.py",
    "src/lychd/extensions/manager.py",
    "src/lychd/extensions/builtin/animator/vllm/register.py",
    "src/lychd/extensions/builtin/animator/soulstones/vllm.py",
    "src/lychd/interface/api/lifecycle.py",
    "src/lychd/interface/server_policy.py",
    "src/lychd/interface/web/altar_services.py",
    "src/lychd/interface/web/bridge.py",
    "src/lychd/interface/web/lifespan.py",
    "src/lychd/ghouls/runs.py",
    "src/lychd/system/operator/admission.py",
    "src/lychd/system/services/queues.py",
    "tests/conftest.py",
    "tests/integration/test_local_bridge_runtime.py",
    "tests/integration/test_production_wiring.py",
}
_CORE_DEPENDENCIES = (
    "advanced-alchemy",
    "alembic",
    "asyncpg",
    "cryptography",
    "http-message-signatures",
    "httpx",
    "httpx2",
    "litestar",
    "litestar-saq",
    "openai",
    "psycopg",
    "pydantic",
    "pydantic-settings",
    "pydantic-ai-slim",
    "pydantic-graph",
    "saq",
    "sqlalchemy",
    "typing-extensions",
    "pytest",
)


def test_maintained_local_bridge_receipt_keeps_its_exact_boundary() -> None:
    receipt = json.loads(_RECEIPT.read_text())
    assert set(receipt) == {
        "schema",
        "record_kind",
        "qualification_date",
        "status",
        "source_identity",
        "execution",
        "model",
        "outcome",
        "database",
        "runner",
        "retained_history_sha256",
        "timings_seconds",
        "qualification_evidence",
        "dependency_versions",
        "source_fingerprints",
        "freshness_check",
        "identity_boundary",
        "unexercised",
    }
    assert receipt["schema"] == "local-bridge-vllm-runtime@1"
    assert receipt["record_kind"] == "sanitized_public_local_bridge_qualification"
    assert receipt["qualification_date"] == "2026-10-17"
    assert receipt["status"] == "passed"
    assert receipt["source_identity"] == {
        "base_revision_declared": "df637032e41c34a9c86f5fe24d7be022f501914d",
        "clean_checkout_attested": False,
        "atomic_transitive_closure_attested": False,
        "scope": "bounded-critical-source-and-test-fingerprints",
    }
    assert receipt["execution"] == {
        "http": "litestar.testing.TestClient",
        "application": "real-create_app-two-in-process-lifespans",
        "worker": "real-in-process-SAQ",
        "graph": "real-Bridge-Graph",
        "dispatch": "real-Dispatcher-and-LeaseLedger",
        "agent": "real-AgentForge-and-Pydantic-AI",
        "database": "real-disposable-PostgreSQL",
        "input_assembly": "source-registered-builtins-explicit-SettingsSnapshot-and-RuneRegistry",
        "runtime_actuator": "refusing-fixture-port",
        "model_transport": "real-streaming-OpenAI-compatible-chat",
    }
    assert receipt["model"] == {
        "served_model_id": "Qwen3.8-27B",
        "model_bytes_attested": False,
        "context_tokens": 4096,
        "max_output_tokens": 256,
        "cooperative_deadline_seconds": 30,
        "maximum_model_posts": 3,
    }
    assert receipt["outcome"] == {
        "boots": 2,
        "run_status": "DONE",
        "pattern_id": "bridge_chat",
        "pattern_revision": "2",
        "manifest_exact_match": True,
        "warm_on_both_boots": True,
        "settled_turns": 2,
        "model_posts": 1,
        "model_responses": 1,
        "structured_output_calls": 1,
        "structured_output_name": "final_result",
        "wire_finish_reason": "tool_calls",
        "retained_history_identical": True,
        "model_posts_on_second_boot": 0,
        "active_leases_after_each_boot": 0,
        "model_boundary_violations": 0,
        "lifecycle_calls": 0,
        "substrate_unpublished": True,
    }
    assert receipt["database"] == {
        "image_id": "sha256:1963bc48febf543433baa1ce3edcc6cc08154de722e22495f86681cc9a849026",
        "created_containers": 1,
        "container_removed": True,
        "published_interface": "literal-loopback-only",
        "required_resources": {"mem_limit": "512m", "nano_cpus": 1_000_000_000, "pids_limit": 128},
    }
    assert receipt["runner"] == {
        "cleanup_verified": True,
        "coordinator_cleanup_reserve_seconds": 30,
        "coordinator_deadline_seconds": 240,
        "default_make_ryuk_profile": False,
        "operator_unit_stop_timeout_seconds": 5,
        "outer_timeout_seconds": 250,
        "profile": "local-bridge-runtime-real-model-cached-PG-R2-owned-coordinator-resource-hook",
        "pytest_errors": 0,
        "pytest_failed": 0,
        "pytest_passed": 1,
        "pytest_selected": 1,
        "pytest_skipped": 0,
        "remaining_containers": 0,
        "ryuk_disabled_in_runner_process": True,
        "test_wait_seconds": 210,
        "unresolved_creates": 0,
    }
    assert set(receipt["unexercised"]) == {
        "browser-and-full-accessibility",
        "separate-process-restart",
        "process-crash-recovery",
        "installed-Vessel",
        "Vessel-network-namespace",
        "managed-model-lifecycle",
        "shared-load-and-capacity",
        "live-cancellation",
        "model-byte-identity",
        "general-purpose-tools",
        "durable-semantic-memory",
        "evolution-and-promotion",
        "remote-access-and-hostile-browser",
    }
    assert len(receipt["retained_history_sha256"]) == 64
    assert set(receipt["retained_history_sha256"]) <= set("0123456789abcdef")
    # This is a metadata/freshness gate, not a replay or a new live result.
    assert receipt["freshness_check"] == "offline-metadata-source-and-selected-dependency-check-only"
    assert not any(
        item in _RECEIPT.read_text()
        for item in (
            "://",
            "/home/",
            "/tmp/",  # noqa: S108 - refuse private host paths in published metadata
            "127.0.0.1",
            "::1",
            "password",
            "username",
            "response_id",
            "session_id",
            "run_id",
        )
    )


def test_maintained_local_bridge_receipt_matches_critical_sources() -> None:
    receipt = json.loads(_RECEIPT.read_text())
    assert set(receipt["source_fingerprints"]) == _SOURCES
    evidence = receipt["qualification_evidence"]
    assert set(evidence) == {
        "application_receipt_sha256",
        "candidate_manifest_sha256",
        "coordinator_receipt_sha256",
        "coordinator_source_sha256",
        "joined_test_sha256_before_trial",
        "model_profile_sha256",
        "pytest_log_sha256",
        "resource_launcher_source_sha256",
        "resource_receipt_sha256",
    }
    assert (
        evidence["joined_test_sha256_before_trial"]
        == receipt["source_fingerprints"]["tests/integration/test_local_bridge_runtime.py"]
    )
    assert evidence["coordinator_source_sha256"] == "6c1505e1959442b2a9de0078a9c7e2d1f719c3a9d9cc97c26246cac6022daca8"
    assert (
        evidence["resource_launcher_source_sha256"]
        == "b8105f73913316031e7241529ff4676b8672ac106754d76b8daea209a18afa78"
    )
    for digest in evidence.values():
        assert len(digest) == 64
        assert set(digest) <= set("0123456789abcdef")
    for path, digest in receipt["source_fingerprints"].items():
        assert sha256((_ROOT / path).read_bytes()).hexdigest() == digest, path


def test_maintained_local_bridge_receipt_matches_selected_dependencies() -> None:
    receipt = json.loads(_RECEIPT.read_text())
    dependencies = {name: version(name) for name in _CORE_DEPENDENCIES}
    # Core CI need not install the optional container SDK. Its locked versions
    # still belong to this profile; unrelated lockfile edits do not stale it.
    locked = tomllib.loads((_ROOT / "uv.lock").read_text())
    dependencies.update(
        {item["name"]: item["version"] for item in locked["package"] if item["name"] in {"docker", "testcontainers"}}
    )
    assert receipt["dependency_versions"] == dependencies
