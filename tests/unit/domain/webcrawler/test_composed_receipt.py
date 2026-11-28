"""A historical composed passage cannot silently qualify changed critical inputs."""

from __future__ import annotations

import json
import tomllib
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest


def _require_current_source_freshness(root: Path, receipt: dict[str, Any]) -> None:
    """A historical observation cannot qualify current critical source bytes."""
    assert receipt.get("qualification_scope", "current") == "current", "historical receipt is not current qualification"
    for path, digest in receipt["source_fingerprints"].items():
        assert sha256((root / path).read_bytes()).hexdigest() == digest, path


def _require_current_dependencies(root: Path, receipt: dict[str, Any]) -> None:
    """Keep selected package and private-reference checks for a future current trial."""
    evidence_id = UUID(receipt["qualification_evidence_id"])
    assert evidence_id.version == 4
    assert str(evidence_id) == receipt["qualification_evidence_id"]
    dependencies = {
        name: version(name)
        for name in (
            "asyncpg",
            "sqlalchemy",
            "h11",
            "dnspython",
            "pydantic",
            "pydantic-ai-slim",
            "pydantic-graph",
        )
    }
    # Docker belongs to the optional container-test group; check its locked identity
    # even when the effect-free core environment does not install that SDK.
    locked = tomllib.loads((root / "uv.lock").read_text())
    dependencies["docker"] = next(item["version"] for item in locked["package"] if item["name"] == "docker")
    assert receipt["dependency_versions"] == dependencies


def test_composed_passage_preserves_its_declared_qualification_scope() -> None:
    root = Path(__file__).resolve().parents[4]
    raw = (root / "tests/fixtures/scout/linux-composed-runtime.json").read_bytes()
    receipt = json.loads(raw)
    scope = receipt.get("qualification_scope", "current")
    assert scope in {"current", "historical"}
    assert receipt["schema"] == "scout-composed-local-proof@1"
    assert receipt["status"] == "passed"
    assert receipt["network"] == "isolated-loopback-only"
    assert receipt["admission"] == "credential-consent-store-issued-claim"
    assert receipt["execution"] == "explicit-service-and-node-choreography"
    assert receipt["model"] == "deterministic-FunctionModel"
    assert receipt["record_kind"] == "sanitized_public_composed_qualification"
    assert set(receipt["unexercised"]) == {
        "HTTP-routes",
        "SAQ-worker-process",
        "Graph-checkpoint-resume",
        "model-inference",
        "public-Internet",
    }
    if scope == "historical":
        assert sha256(raw).hexdigest() == "81fe67208e0e5d625b114d0f257291628572884fc43351e36107fdd4d9ebac33"
        assert receipt["observed_on"] == "2026-10-19"
        assert receipt["historical_retirement"] == {
            "retired_on": "2026-10-26",
            "reason": "integrated-source-closure-changed",
            "no_current_qualification": True,
        }
        assert receipt["dependency_versions"] == {
            "asyncpg": "0.32.0",
            "sqlalchemy": "2.0.54",
            "docker": "7.2.0",
            "h11": "0.16.0",
            "dnspython": "2.8.0",
            "pydantic": "2.14.0",
            "pydantic-ai-slim": "2.55.0",
            "pydantic-graph": "2.55.0",
        }
    else:
        _require_current_dependencies(root, receipt)
    module_name = "scout" if scope == "historical" else "webcrawler"
    expected_sources = {
        "src/lychd/domain/codex/local_access.py",
        "src/lychd/domain/codex/ledger.py",
        "src/lychd/domain/cortex/bridge_preference.py",
        "src/lychd/domain/cortex/cancellation.py",
        "src/lychd/domain/cortex/engine.py",
        "src/lychd/domain/cortex/ledger.py",
        "src/lychd/domain/cortex/runs.py",
        "src/lychd/domain/scout/attempts.py",
        "src/lychd/domain/scout/authority.py",
        "src/lychd/domain/scout/destination.py",
        "src/lychd/domain/scout/transport.py",
        "src/lychd/domain/scout/extraction.py",
        f"src/lychd/domain/{module_name}/profile.py",
        f"src/lychd/domain/{module_name}/review.py",
        f"src/lychd/db/{module_name}.py",
        f"src/lychd/db/models/{module_name}.py",
        "src/lychd/db/sessions.py",
        f"src/lychd/interface/web/{module_name}_admission.py",
        f"src/lychd/interface/web/{module_name}_review.py",
        f"src/lychd/agents/workflows/{module_name}_chat.py",
        f"src/lychd/agents/{module_name}_context.py",
        "src/lychd/agents/router.py",
        "src/lychd/system/scout_worker.py",
        f"src/lychd/system/services/{module_name}_workflow.py",
        "src/lychd/system/services/scout_dns.py",
        "src/lychd/system/services/scout_socket.py",
        "src/lychd/system/services/scout_http.py",
        "src/lychd/system/services/scout_fetch.py",
        "src/lychd/system/services/scout_extraction.py",
        "tests/agents/fakes.py",
        "tests/agents/conftest.py",
        f"tests/{module_name}_fixtures.py",
        "tests/scout_network_fixture.py",
        "tests/scout_postgres_fixture.py",
        "tests/postgres_model_tables.py",
        f"tests/{module_name}_workflow_fixture.py",
        "tests/integration/test_scout_extraction_runtime.py",
        f"tests/integration/test_{module_name}_composed_runtime.py",
    }
    if scope == "historical":
        expected_sources.remove("tests/postgres_model_tables.py")
    assert set(receipt["source_fingerprints"]) == expected_sources
    if scope == "current":
        _require_current_source_freshness(root, receipt)
    assert not any(
        item in json.dumps(receipt)
        for item in ("/home/", "/tmp/", '"container_id"', '"python_root"')  # noqa: S108 - refuse private paths
    )
    database = receipt["database"]
    assert database["network"] == "none"
    assert database["published_ports"] is False
    assert database["ready"] is True
    assert database["image_id"].startswith("sha256:")
    assert database["container_created"] is True
    assert database["container_removed"] is True
    assert database["anonymous_volumes_removed"] is True
    assert database["socket_directory_removed"] is True
    assert set(receipt["passages"]) == {"success", "revoked_at_sni"}
    success, revoked = receipt["passages"]["success"], receipt["passages"]["revoked_at_sni"]
    assert success["outcome"] == "succeeded"
    assert success["child"] == "reaped"
    assert success["extraction_processes"] == success["model_requests"] == success["http_requests"] == 1
    assert revoked["outcome"] == "refused"
    assert revoked["child"] == "not_started"
    assert revoked["extraction_processes"] == revoked["model_requests"] == revoked["http_requests"] == 0
    assert success["tls_versions"]
    for passage in (success, revoked):
        assert passage["usage"]["connects"] == 3
        assert passage["usage"]["wire_bytes"] > 0
        assert passage["usage"]["transmissions"] > 0
        assert set(passage["tls_versions"]) <= {"TLSv1.2", "TLSv1.3"}


def test_current_source_freshness_refuses_historical_observations(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="historical receipt is not current qualification"):
        _require_current_source_freshness(tmp_path, {"qualification_scope": "historical", "source_fingerprints": {}})


def test_current_source_freshness_detects_changed_critical_inputs(tmp_path: Path) -> None:
    source = tmp_path / "critical.py"
    source.write_bytes(b"original critical input")
    receipt = {"source_fingerprints": {"critical.py": sha256(source.read_bytes()).hexdigest()}}
    _require_current_source_freshness(tmp_path, receipt)

    source.write_bytes(b"changed critical input")
    with pytest.raises(AssertionError, match=r"critical\.py"):
        _require_current_source_freshness(tmp_path, receipt)
