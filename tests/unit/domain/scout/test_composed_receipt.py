"""A historical composed passage cannot silently qualify changed critical inputs."""

from __future__ import annotations

import json
import tomllib
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from uuid import UUID


def test_maintained_composed_passage_matches_source_and_dependencies() -> None:
    root = Path(__file__).resolve().parents[4]
    receipt = json.loads((root / "tests/fixtures/scout/linux-composed-runtime.json").read_text())
    assert receipt["schema"] == "scout-composed-local-proof@1"
    assert receipt["status"] == "passed"
    assert receipt["network"] == "isolated-loopback-only"
    assert receipt["admission"] == "credential-consent-store-issued-claim"
    assert receipt["execution"] == "explicit-service-and-node-choreography"
    assert receipt["model"] == "deterministic-FunctionModel"
    assert receipt["record_kind"] == "sanitized_public_composed_qualification"
    evidence_id = UUID(receipt["qualification_evidence_id"])
    assert evidence_id.version == 4
    assert str(evidence_id) == receipt["qualification_evidence_id"]
    assert set(receipt["unexercised"]) == {
        "HTTP-routes",
        "SAQ-worker-process",
        "Graph-checkpoint-resume",
        "model-inference",
        "public-Internet",
    }
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
    assert set(receipt["source_fingerprints"]) == {
        "src/lychd/domain/codex/local_access.py",
        "src/lychd/domain/codex/ledger.py",
        "src/lychd/domain/cortex/cancellation.py",
        "src/lychd/domain/cortex/engine.py",
        "src/lychd/domain/cortex/ledger.py",
        "src/lychd/domain/scout/attempts.py",
        "src/lychd/domain/scout/authority.py",
        "src/lychd/domain/scout/destination.py",
        "src/lychd/domain/scout/transport.py",
        "src/lychd/domain/scout/extraction.py",
        "src/lychd/domain/scout/profile.py",
        "src/lychd/domain/scout/review.py",
        "src/lychd/db/scout.py",
        "src/lychd/db/models/scout.py",
        "src/lychd/db/sessions.py",
        "src/lychd/interface/web/scout_admission.py",
        "src/lychd/interface/web/scout_review.py",
        "src/lychd/agents/workflows/scout_chat.py",
        "src/lychd/agents/scout_context.py",
        "src/lychd/system/scout_worker.py",
        "src/lychd/system/services/scout_workflow.py",
        "src/lychd/system/services/scout_dns.py",
        "src/lychd/system/services/scout_socket.py",
        "src/lychd/system/services/scout_http.py",
        "src/lychd/system/services/scout_fetch.py",
        "src/lychd/system/services/scout_extraction.py",
        "tests/agents/fakes.py",
        "tests/agents/conftest.py",
        "tests/scout_fixtures.py",
        "tests/scout_network_fixture.py",
        "tests/scout_postgres_fixture.py",
        "tests/postgres_model_tables.py",
        "tests/scout_workflow_fixture.py",
        "tests/integration/test_scout_extraction_runtime.py",
        "tests/integration/test_scout_composed_runtime.py",
    }
    for path, digest in receipt["source_fingerprints"].items():
        assert sha256((root / path).read_bytes()).hexdigest() == digest, path
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
