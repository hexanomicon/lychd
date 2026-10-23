"""The bounded manual qualification cannot silently follow changed source bytes."""

from __future__ import annotations

import hashlib
import json
from importlib.metadata import version
from pathlib import Path
from typing import Any, cast
from uuid import UUID

_ROOT = Path(__file__).resolve().parents[4]


def _receipt() -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads((_ROOT / "tests/fixtures/intercom/operator-public-source.json").read_text()),
    )


def test_qualified_bounded_sources_and_installed_mechanisms_remain_exact() -> None:
    receipt = _receipt()
    assert receipt["schema_version"] == 1
    assert receipt["profile"] == "outbound-public-text@1"
    pins = cast("dict[str, str]", receipt["source_pins"])
    assert len(pins) == 26
    assert {
        "src/lychd/db/models/run.py",
        "src/lychd/db/migrations/versions/0017_native_peer_graph.py",
        "tests/postgres_model_tables.py",
    } <= pins.keys()
    for relative, expected in pins.items():
        path = Path(relative)
        assert not path.is_absolute()
        assert ".." not in path.parts
        assert ".venv" not in path.parts
        source = (_ROOT / path).resolve()
        assert source.is_relative_to(_ROOT)
        assert source.is_file()
        assert hashlib.sha256(source.read_bytes()).hexdigest() == expected, relative
    dependencies = cast("dict[str, str]", receipt["production_dependencies"])
    assert all(version(name) == expected for name, expected in dependencies.items())


def test_manual_peer_evidence_does_not_promote_private_or_graph_operation() -> None:
    receipt = _receipt()
    assert receipt["independent_peer"]["sdk"] == "a2a-sdk==1.2.3"
    assert receipt["observed"]["production_sdk_cases"] == 4
    assert receipt["observed"]["actual_postgresql_tests"] == 15
    assert receipt["observed"]["no_uncertain_resubmit"] is True
    limits = receipt["limits"]
    for boundary in (
        "native_peer_graph",
        "run_cut_transport",
        "private_voice_context_egress",
        "incoming_ward_or_a2a",
        "automatic_fallback",
        "normal_boot_activation",
    ):
        assert limits[boundary] is False
    evidence = cast("dict[str, str]", receipt["evidence_ids"])
    assert len({UUID(value) for value in evidence.values()}) == len(evidence) == 4
