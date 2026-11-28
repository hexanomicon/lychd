"""Keep the maintained local network proof bound to its actual tested closure."""

from __future__ import annotations

import json
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path


def test_maintained_authority_qualification_matches_source_and_dependencies() -> None:
    root = Path(__file__).resolve().parents[4]
    receipt = json.loads((root / "tests/fixtures/scout/linux-authority-runtime.json").read_text())
    assert receipt["schema"] == "scout-network-authority-local-proof@1"
    assert receipt["status"] == "passed"
    assert receipt["network"] == "isolated-loopback-only"
    assert receipt["authority"] == "production-current-network-gate-with-fixture-preparation-and-claim"
    assert receipt["durable_admission"] == "not_exercised"
    assert receipt["extraction_and_inference"] == "not_exercised"
    assert receipt["dependency_versions"] == {name: version(name) for name in ("h11", "dnspython", "pydantic")}
    assert set(receipt["source_fingerprints"]) == {
        "src/lychd/domain/codex/local_access.py",
        "src/lychd/domain/cortex/cancellation.py",
        "src/lychd/domain/scout/attempts.py",
        "src/lychd/domain/scout/authority.py",
        "src/lychd/domain/scout/destination.py",
        "src/lychd/domain/scout/transport.py",
        "src/lychd/system/services/scout_dns.py",
        "src/lychd/system/services/scout_socket.py",
        "src/lychd/system/services/scout_http.py",
        "src/lychd/system/services/scout_fetch.py",
        "tests/scout_network_fixture.py",
        "tests/integration/test_scout_authority_runtime.py",
    }
    for path, digest in receipt["source_fingerprints"].items():
        assert sha256((root / path).read_bytes()).hexdigest() == digest, path
    assert set(receipt["checks"]) == {
        "real_current_authority_dns_tls_http_exact_request_and_accounting",
        "same_host_path_and_query_substitution_prevents_http_bytes",
        "authentication_revoked_at_sni_prevents_http_bytes",
        "policy_revoked_at_sni_prevents_http_bytes",
        "claim_revoked_at_sni_prevents_http_bytes",
        "run_revoked_at_sni_prevents_http_bytes",
        "shutdown_revoked_at_sni_prevents_http_bytes",
        "connects_budget_0_prevents_next_network_effect",
        "transmissions_budget_0_prevents_next_network_effect",
        "wire_bytes_budget_0_prevents_next_network_effect",
        "connects_budget_2_prevents_next_network_effect",
        "wire_bytes_budget_after_dns_prevents_client_hello",
        "source_fingerprints_unchanged",
    }
    assert receipt["successful_passage"]["connects"] == 3
    assert receipt["successful_passage"]["accepted_wire_bytes"] > receipt["successful_passage"]["dns_wire_bytes"] > 0
    assert receipt["tls_versions"]
    assert set(receipt["tls_versions"]) <= {"TLSv1.2", "TLSv1.3"}
