"""Keep held-input qualification distinct from physical keys, microphone and hearing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
RECEIPT = ROOT / "tests/fixtures/blockworld/companion-cpu-runtime.json"


def test_held_input_qualification_retains_original_occurrence_and_physical_limits() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["held_input_requalification"]
    assert current["profile"] == "held-local-voice-control@1"
    assert current["maximum_capture_seconds"] == 15
    assert current["minimum_capture_ms"] == 250
    assert current["capture_port"] == "controlled-synthetic-pcm-feeder"
    assert current["live_clock_operation"] == "time@1"
    assert current["live_clock_mode"] == "night"
    assert current["live_native_runs_applied"] == current["generated_reply_wavs"] == 1
    for key in (
        "original_identity_and_deadline_retained",
        "duplicate_phases_do_not_replay",
        "release_before_start_blocks_delayed_capture",
        "sample_or_wall_limit_without_release_discards",
        "real_local_http",
        "cpu_whisper_supertonic",
        "native_run_graph",
        "live_closed_stopped",
    ):
        assert current[key] is True
    for key in (
        "physical_microphone",
        "physical_playback",
        "physical_keys_or_focus_qualified",
        "human_accuracy_benchmark",
        "gpu_or_interpreter_used",
        "wakeword_or_continuous_capture_added",
        "unchanged_historical_cohorts_reexecuted",
    ):
        assert current[key] is False
    assert current["human_hearing"] == "unconfirmed"
    prior = current["prior_changed_source_fingerprints"]
    assert {
        "scripts/companion_lab.py",
        "src/lychd/system/services/companion_control.py",
        "src/lychd/system/services/voice_capture.py",
    } <= set(prior)
    for name, digest in prior.items():
        assert digest != receipt["source_fingerprints"][name]
        assert len(digest) == 64
        assert all(character in "0123456789abcdef" for character in digest)
    qualified = current["newly_qualified_sources"]
    assert len(qualified) == 3
    assert set(qualified) == {
        "tests/unit/system/services/test_voice_capture_hold.py",
        "tests/unit/system/services/test_companion_control_hold.py",
        "tests/integration/test_companion_hold.py",
    }
    assert set(qualified) <= set(receipt["source_fingerprints"])
    identities = current["evidence_ids"]
    assert len(identities) == len(set(identities.values())) == 4
    previous = set(receipt["qualification_evidence_ids"].values())
    for name, cohort in receipt.items():
        if name != "held_input_requalification" and isinstance(cohort, dict):
            previous.update(cast("dict[str, Any]", cohort).get("evidence_ids", {}).values())
    assert not previous & set(identities.values())
    for identity in identities.values():
        parsed = UUID(identity)
        assert str(parsed) == identity
        assert parsed.version == 4
