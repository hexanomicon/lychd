"""Keep the historical CPU qualification bound to its tested source and declared limits."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
RECEIPT = ROOT / "tests/fixtures/blockworld/companion-cpu-runtime.json"
PYTHON_SOURCES = {
    "scripts/companion_lab.py",
    "src/lychd/cli/companion_view.py",
    "tests/unit/cli/test_companion_view.py",
    "tests/unit/cli/test_companion_human.py",
    "tests/integration/test_companion_status.py",
    "scripts/qualify_companion_lab.py",
    "scripts/voice_probe.py",
    "scripts/blockworld_voice.py",
    "src/lychd/compositions/blockworld/companion.py",
    "src/lychd/compositions/blockworld/companion_feedback.py",
    "src/lychd/compositions/blockworld/companion_intent.py",
    "src/lychd/compositions/blockworld/local_runtime.py",
    "src/lychd/system/services/companion_bridge.py",
    "src/lychd/system/services/companion_session.py",
    "src/lychd/system/services/companion_control.py",
    "tests/unit/system/services/test_companion_control.py",
    "tests/unit/system/services/test_companion_control_hold.py",
    "tests/integration/test_companion_control.py",
    "tests/integration/test_companion_hold.py",
    "src/lychd/system/services/companion_intent.py",
    "src/lychd/system/services/speech_probe.py",
    "src/lychd/system/services/voice_capture.py",
    "tests/unit/system/services/test_voice_capture.py",
    "tests/unit/system/services/test_voice_capture_hold.py",
    "src/lychd/system/services/voice_playback.py",
    "tests/unit/system/services/test_voice_playback.py",
    "src/lychd/domain/speech_probe.py",
    "tests/integration/test_companion.py",
    "tests/integration/test_companion_cell.py",
    "tests/integration/test_companion_weather.py",
    "tests/integration/test_companion_time.py",
    "tests/unit/cli/test_companion_lab.py",
    "tests/unit/cli/test_companion_weather_option.py",
    "tests/unit/cli/test_companion_time_option.py",
    "tests/unit/cli/test_companion_timing.py",
    "tests/unit/cli/test_companion_language.py",
    "tests/unit/cli/test_voice_probe.py",
    "tests/unit/cli/test_blockworld_voice.py",
    "tests/unit/domain/test_speech_probe.py",
    "tests/unit/system/services/test_speech_probe.py",
    "tests/unit/compositions/blockworld/test_companion_feedback.py",
    "tests/unit/compositions/blockworld/test_companion_voice_feedback.py",
    "tests/integration/test_companion_voice_recovery.py",
    "tests/unit/compositions/blockworld/test_companion_intent.py",
    "tests/unit/system/services/test_companion_intent.py",
}
JAVA_BUILD = {
    "build.gradle",
    "settings.gradle",
    "gradle.properties",
    "gradle.lockfile",
    "gradle/verification-metadata.xml",
    "gradle/wrapper/gradle-wrapper.jar",
    "gradle/wrapper/gradle-wrapper.properties",
    "gradlew",
    "gradlew.bat",
}


def qualified_sources() -> set[str]:
    """The bounded critical slice deliberately makes no transitive closure claim."""
    java = ROOT / "clients/minecraft"
    voice = ROOT / "clients/minecraft-voice"
    return (
        PYTHON_SOURCES
        | {"LICENSE", "clients/MINECRAFT-NOTICE.txt"}
        | {f"clients/minecraft/{name}" for name in JAVA_BUILD}
        | {str(path.relative_to(ROOT)) for path in (java / "src").rglob("*") if path.is_file()}
        | {
            f"clients/minecraft-voice/{name}"
            for name in JAVA_BUILD
            if not name.startswith(("gradle/wrapper/", "gradlew"))
        }
        | {str(path.relative_to(ROOT)) for path in (voice / "src").rglob("*") if path.is_file()}
    )


def test_local_control_qualification_keeps_wire_and_physical_interaction_distinct() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["control_requalification"]
    assert current["profile"] == "private-local-voice-control@1"
    assert set(current["prior_changed_source_fingerprints"]) == {"scripts/companion_lab.py"}
    assert (
        current["prior_changed_source_fingerprints"]["scripts/companion_lab.py"]
        != receipt["source_fingerprints"]["scripts/companion_lab.py"]
    )
    assert current["synthetic_cpu_game_cases_applied"] == current["generated_reply_wavs"] == 2
    assert current["production_java_transport_and_parser"] is True
    assert current["capture_port"] == "controlled-synthetic-wav"
    assert current["original_identity_and_deadline_retained"] is True
    assert current["native_socket_cases"] == 22
    assert current["counterfactual_cases_rejected"] == 5
    assert current["pure_java_tests"] == 20
    assert current["actor_closed_stopped"] is True
    assert current["unchanged_historical_cohorts_reexecuted"] is False
    assert current["game_client_launched"] is current["focused_key_menu_hud_verified"] is False
    assert current["physical_microphone"] is current["physical_playback"] is current["gpu_or_intent_used"] is False
    identities = current["evidence_ids"]
    assert set(identities) == {"cross_language", "native_sockets", "client_build", "negative_controls"}
    assert len(set(identities.values())) == len(identities)
    for identity in identities.values():
        parsed = UUID(identity)
        assert str(parsed) == identity
        assert parsed.version == 4


def test_companion_qualification_source_freshness() -> None:
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["schema"] == "companion-cpu-runtime@1"
    assert receipt["status"] == "passed-with-explicit-human-checks-pending"
    assert set(receipt["source_fingerprints"]) == qualified_sources()
    for name, digest in receipt["source_fingerprints"].items():
        assert sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    assert sha256((ROOT / "uv.lock").read_bytes()).hexdigest() == receipt["uv_lock_sha256"]


def test_publication_packaging_keeps_runtime_and_human_qualification_separate() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["publication_packaging_requalification"]
    assert current["profile"] == "companion-mod-publication-packaging@1"
    assert set(current["prior_changed_source_fingerprints"]) == {
        "clients/minecraft/build.gradle",
        "clients/minecraft/src/main/resources/fabric.mod.json",
        "clients/minecraft-voice/build.gradle",
        "clients/minecraft-voice/src/main/resources/fabric.mod.json",
    }
    for name, digest in current["prior_changed_source_fingerprints"].items():
        assert digest != receipt["source_fingerprints"][name]
    assert set(current["newly_qualified_sources"]) == {"LICENSE", "clients/MINECRAFT-NOTICE.txt"}
    for name, classes, cases in (("server", 34, 43), ("voice_client", 20, 28)):
        artifact = current["artifacts"][name]
        assert artifact["production_classes_unchanged"] == classes
        assert artifact["pure_java_cases"] == cases
        assert len(artifact["sha256"]) == 64
        assert artifact["packaged_license_and_notice_exact"] is True
        assert artifact["test_and_foreign_classes_absent"] is True
        assert artifact["source_url_and_disclaimer"] is True
    assert current["gradle_cache_excluded_from_source_candidate"] is True
    assert current["game_binaries_or_private_profiles_published"] is False
    assert current["new_gameplay_or_speech_qualification"] is False
    assert current["all_historical_cohorts_reexecuted"] is False
    assert current["legal_approval_claimed"] is False
    assert current["human_microphone_or_hearing_qualified"] is False
    assert current["exact_corresponding_source_required_before_binary_distribution"] is True
    identities = current["evidence_ids"]
    assert len(identities) == len(set(identities.values())) == 2
    for identity in identities.values():
        assert str(UUID(identity)) == identity
        assert UUID(identity).version == 4


def test_voice_recovery_qualification_keeps_local_failure_and_game_outcome_separate() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["voice_recovery_requalification"]
    assert current["profile"] == "local-voice-failure-recovery@1"
    assert set(current["prior_changed_source_fingerprints"]) == {
        "scripts/companion_lab.py",
        "src/lychd/compositions/blockworld/companion_feedback.py",
        "src/lychd/cli/companion_view.py",
        "src/lychd/system/services/companion_control.py",
        "clients/minecraft-voice/src/test/java/org/lychd/voice/HudTextTest.java",
    }
    for name, digest in current["prior_changed_source_fingerprints"].items():
        assert digest != receipt["source_fingerprints"][name]
    assert set(current["newly_qualified_sources"]) == {
        "tests/integration/test_companion_voice_recovery.py",
        "tests/unit/compositions/blockworld/test_companion_voice_feedback.py",
    }
    assert current["native_socket_voice_cases"] == 19
    assert current["pure_feedback_cases"] == 41
    assert current["affected_cases"] == 828
    assert current["pure_java_tests"] == 28
    assert current["languages"] == ["sk", "cs", "en"]
    for key in (
        "pre_native_failure_has_no_invented_game_outcome",
        "duplicate_gesture_does_not_repeat_audio_or_inference",
        "fresh_gesture_recovers_after_settled_failure",
        "unknown_audio_remains_latched",
        "post_enqueue_failure_preserves_later_native_result",
        "admission_uncertainty_survives_audio_latch",
        "failed_spoken_stop_is_correlated_unknown",
        "failed_spoken_stop_json_terminal_visible",
        "existing_java_feedback_shape_retained",
    ):
        assert current[key] is True
    for key in (
        "all_historical_cohorts_reexecuted",
        "game_client_launched",
        "game_artifact_redeployed",
        "fresh_gui_rendering_qualified",
        "human_microphone_or_hearing_qualified",
        "automatic_hud_reconciliation_after_unknown",
    ):
        assert current[key] is False
    for key in ("actual_audio_operations", "speech_provider_calls", "live_game_commands", "gpu_model_calls"):
        assert current[key] == 0
    identities = current["evidence_ids"]
    assert set(identities) == {"native_socket_fixtures", "pure_feedback", "pure_java", "independent_review"}
    assert len(set(identities.values())) == len(identities)
    assert not set(identities.values()) & set(receipt["controller_deadline_requalification"]["evidence_ids"].values())
    for identity in identities.values():
        parsed = UUID(identity)
        assert str(parsed) == identity
        assert parsed.version == 4


def test_controller_deadline_qualification_preserves_authority_and_observation_limits() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["controller_deadline_requalification"]
    assert current["profile"] == "host-controller-deadline@1"
    assert set(current["prior_changed_source_fingerprints"]) == {
        "src/lychd/compositions/blockworld/companion.py",
        "src/lychd/compositions/blockworld/companion_feedback.py",
        "scripts/companion_lab.py",
        "tests/integration/test_companion.py",
        "tests/unit/compositions/blockworld/test_companion_feedback.py",
        "tests/unit/cli/test_companion_human.py",
    }
    for name, digest in current["prior_changed_source_fingerprints"].items():
        assert digest != receipt["source_fingerprints"][name]
        assert len(digest) == 64
    assert current["affected_cases"] == 660
    assert current["languages"] == ["sk", "cs", "en"]
    assert current["pattern_revision"] == "2"
    assert current["implementation_revision"] == "py.3"
    assert current["checkpoint_schema"] == "companion-state-v3"
    assert current["live_ordinary_posts"] == current["live_priority_stop_posts"] == 2
    assert current["successful_probe"]["configured_lease_ms"] == 4000
    assert current["successful_probe"]["original_command_ms"] == 2000
    assert current["successful_probe"]["ordinary_posts"] == current["successful_probe"]["priority_stop_posts"] == 1
    for key in (
        "exact_outgoing_clipped_deadline_retained",
        "native_run_and_event_correlated",
        "identical_request_reuses_original_future_and_deadline",
        "observed_active_then_inactive_id",
        "cleanup_stop_applied_and_actor_stopped",
        "earlier_harness_failure_retained_and_settled_before_new_occurrence",
    ):
        assert current[key] is True
    for key in (
        "old_pinned_runs_migrated",
        "wire_deadline_receipt_added",
        "controller_renewal_added",
        "ending_cause_inferred",
        "all_historical_cohorts_reexecuted",
        "game_clients_rebuilt",
        "human_microphone_or_hearing_qualified",
    ):
        assert current[key] is False
    for key in ("actual_audio_operations", "speech_provider_calls", "gpu_model_calls"):
        assert current[key] == 0
    identities = current["evidence_ids"]
    assert set(identities) == {"initial_probe", "corrected_probe", "affected_tests", "independent_review"}
    assert len(set(identities.values())) == len(identities)
    assert not set(identities.values()) & set(receipt["playback_route_requalification"]["evidence_ids"].values())
    for identity in identities.values():
        parsed = UUID(identity)
        assert str(parsed) == identity
        assert parsed.version == 4


def test_default_playback_qualification_separates_generation_settlement_and_hearing() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["playback_route_requalification"]
    assert current["profile"] == "host-default-finite-playback@1"
    assert set(current["prior_changed_source_fingerprints"]) == {"src/lychd/system/services/voice_playback.py"}
    for name, digest in current["prior_changed_source_fingerprints"].items():
        assert digest != receipt["source_fingerprints"][name]
        assert len(digest) == 64
    assert current["newly_qualified_sources"] == ["tests/unit/system/services/test_voice_playback.py"]
    assert current["playback_helper_cases"] == 32
    assert current["focused_cases"] == 256
    assert current["unsupported_device_no_launch_cases"] == 7
    assert current["actual_synthesis_calls"] == current["actual_playback_calls"] == 1
    assert current["requested_language"] == "sk"
    assert current["stock_voice"] == "M1"
    assert current["requested_device"] == "default"
    assert current["frame_count"] == 66084
    assert current["sample_rate_hz"] == 44100
    assert current["channels"] == 1
    assert current["sample_width_bytes"] == 2
    assert current["wave_bytes"] == current["frame_count"] * 2 + 44
    assert current["frame_count"] / current["sample_rate_hz"] <= 4
    assert current["wave_bytes"] - 44 <= 1048576
    assert current["player_exit"] == 0
    for key in (
        "exact_inspected_wav_forwarded",
        "owned_player_group_retired",
        "explicit_pulse_has_no_fallback",
        "independent_retirement_cancellation_is_unknown",
        "synthesis_and_playback_evidence_separate",
    ):
        assert current[key] is True
    for key in ("actual_capture_calls", "actual_transcription_calls", "actual_game_commands", "gpu_model_calls"):
        assert current[key] == 0
    for key in (
        "all_historical_cohorts_reexecuted",
        "game_clients_rebuilt",
        "host_routing_or_volume_changed",
        "physical_output_identity_attested",
        "human_speech_recognition_qualified",
        "model_weights_attested_by_profile",
        "raw_audio_delegated_or_published",
    ):
        assert current[key] is False
    assert current["human_hearing"] == "unconfirmed"
    identities = current["evidence_ids"]
    assert set(identities) == {"finite_synthesis", "finite_playback", "independent_review"}
    assert len(set(identities.values())) == len(identities)
    assert not set(identities.values()) & set(receipt["capture_recovery_requalification"]["evidence_ids"].values())
    for identity in identities.values():
        parsed = UUID(identity)
        assert str(parsed) == identity
        assert parsed.version == 4


def test_capture_recovery_keeps_synthetic_settlement_and_historical_device_evidence_distinct() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["capture_recovery_requalification"]
    assert current["profile"] == "settled-capture-recovery@1"
    assert set(current["prior_changed_source_fingerprints"]) == {
        "src/lychd/system/services/voice_capture.py",
        "scripts/companion_lab.py",
        "scripts/blockworld_voice.py",
        "tests/unit/system/services/test_voice_capture.py",
        "tests/unit/cli/test_companion_lab.py",
        "tests/unit/cli/test_blockworld_voice.py",
    }
    for name, digest in current["prior_changed_source_fingerprints"].items():
        assert digest != receipt["source_fingerprints"][name]
        assert len(digest) == 64
    assert current["focused_cases"] == 252
    assert current["capture_helper_cases"] == 28
    for key in (
        "settled_failure_requires_fresh_gesture",
        "unknown_launch_and_retirement_keep_audio_closed",
        "cancellation_during_final_retirement_propagates",
        "independently_cancelled_launch_and_retirement_are_unknown",
        "waiting_reply_suppressed_after_unsettled_capture",
        "horizon_unknown_capture_fences_session",
    ):
        assert current[key] is True
    for key in ("actual_audio_operations", "game_commands", "speech_provider_calls", "gpu_model_calls"):
        assert current[key] == 0
    for key in ("all_historical_cohorts_reexecuted", "game_clients_rebuilt", "human_voice_or_hearing_qualified"):
        assert current[key] is False
    identities = current["evidence_ids"]
    assert set(identities) == {"focused_tests", "cancellation_controls", "independent_review"}
    assert len(set(identities.values())) == len(identities)
    assert not set(identities.values()) & set(receipt["capture_route_requalification"]["evidence_ids"].values())
    for identity in identities.values():
        parsed = UUID(identity)
        assert str(parsed) == identity
        assert parsed.version == 4


def test_default_capture_qualification_does_not_claim_human_voice_or_source_identity() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["capture_route_requalification"]
    assert current["profile"] == "host-default-finite-capture@1"
    assert set(current["prior_changed_source_fingerprints"]) == {"src/lychd/system/services/voice_capture.py"}
    for name, digest in current["prior_changed_source_fingerprints"].items():
        assert digest != receipt["source_fingerprints"][name]
        assert len(digest) == 64
    assert current["newly_qualified_sources"] == ["tests/unit/system/services/test_voice_capture.py"]
    assert current["capture_helper_cases"] == 20
    assert current["invalid_device_no_launch_cases"] == 7
    assert current["capture_attempts"] == 1
    assert current["device"] == "default"
    assert current["frame_count"] == current["sample_rate_hz"] == 16000
    assert current["channels"] == 1
    assert current["sample_width_bytes"] == 2
    assert current["wave_bytes"] == current["frame_count"] * 2 + 44
    assert current["recorder_exit"] == 0
    for key in (
        "actual_recorder_launched",
        "explicit_pulse_has_no_fallback",
        "exact_source_inspector_passed",
        "owned_process_group_retired",
    ):
        assert current[key] is True
    for key in (
        "all_historical_cohorts_reexecuted",
        "game_clients_rebuilt",
        "raw_audio_delegated_or_published",
        "physical_source_identity_attested",
        "human_speech_or_accuracy_qualified",
        "transcription_or_synthesis_requested",
        "playback_started",
        "gpu_model_activated",
        "capture_changed_host_audio_routing",
    ):
        assert current[key] is False
    ready = current["session_readiness"]
    assert ready["scope"] == "prepared-private-local-assembly"
    assert ready["old_session_refusal_http_status"] == 409
    assert ready["explicit_stop_game_kind"] == "applied"
    assert ready["foreground_exit_code"] == 0
    assert ready["ordinary_game_commands_or_voice_requests"] == 0
    assert ready["native_command_artifacts_or_audio_in_session_workspaces"] == 0
    for key in (
        "authenticated_account_control_allowlist_target_match",
        "non_operator_player",
        "fresh_foreground_control_session",
        "human_output_sk_whisper_strict_observed",
        "query_status_did_not_admit_work",
        "original_stop_request_and_distinct_server_id_retained",
        "control_listener_closed",
        "same_actor_stopped",
        "failed_supervisor_attempt_retained",
    ):
        assert ready[key] is True
    assert ready["old_session_refusal_changed_owner_state"] is False
    assert ready["human_prism_join_qualified"] is ready["physical_keys_or_focus_qualified"] is False
    assert ready["human_hearing"] == "unconfirmed"
    identities = current["evidence_ids"]
    assert set(identities) == {"finite_capture", "foreground_readiness", "independent_review"}
    assert len(set(identities.values())) == len(identities)
    assert not set(identities.values()) & set(receipt["hud_requalification"]["evidence_ids"].values())
    for identity in identities.values():
        parsed = UUID(identity)
        assert str(parsed) == identity
        assert parsed.version == 4


def test_multiline_hud_qualification_keeps_display_and_human_evidence_distinct() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["hud_requalification"]
    assert current["profile"] == "software-client-multiline-hud@1"
    assert set(current["prior_changed_source_fingerprints"]) == {
        f"clients/minecraft-voice/{name}"
        for name in (
            "src/main/java/org/lychd/voice/HudText.java",
            "src/main/java/org/lychd/voice/VoiceClient.java",
            "src/gametest/java/org/lychd/voice/ClientControlGameTest.java",
            "src/gametest/java/org/lychd/voice/FixtureLifecycle.java",
            "src/gametest/java/org/lychd/voice/FixtureObservation.java",
            "src/gametest/java/org/lychd/voice/ProtocolFixture.java",
            "src/gametest/java/org/lychd/voice/gametest/mixin/OverlayObserver.java",
            "src/gametest/resources/fabric.mod.json",
        )
    }
    for name, digest in current["prior_changed_source_fingerprints"].items():
        assert digest != receipt["source_fingerprints"][name]
        assert len(digest) == 64
    assert current["newly_qualified_sources"] == [
        "clients/minecraft-voice/src/test/java/org/lychd/voice/HudTextTest.java"
    ]
    assert (
        current["delivered_client_jar_sha256"]
        != receipt["client_runtime_requalification"]["delivered_client_jar_sha256"]
    )
    assert current["pure_java_tests"] == 26
    assert current["runtime_main_classes_equal_delivery"] == 20
    assert (current["record_ingress"], current["stop_ingress"]) == (5, 4)
    assert current["production_initializations"] == 1
    assert current["display_cases"] == current["full_settled_screenshots_inspected"] == 5
    assert current["synthetic_semantic_payloads"] == 3
    assert current["mixed_failure_locales"] == ["en", "sk", "cs"]
    assert current["maximum_literal_feedback_utf16_units"] == 400
    assert current["window_pixels"] == [640, 480]
    assert current["scaled_gui_pixels"] == [320, 240]
    assert 0 < current["maximum_submitted_text_width"] <= current["scaled_gui_pixels"][0] - 16
    assert 0 < current["maximum_submitted_bottom"] <= current["scaled_gui_pixels"][1] - 4
    for key in (
        "actual_game_client_launched",
        "scenario_assertions_reached",
        "complete_content_fit",
        "fresh_panel_required_after_f1",
        "hidden_hud_and_menu_with_extraction_progress",
        "post_production_init_stopping_witness",
        "initial_join_toasts_retired_before_screenshots",
        "all_five_channels_and_null_unreported",
        "failed_pre_repair_runtime_retained",
        "actual_stopping_event",
        "production_workers_retired",
        "fixture_workers_retired",
        "owned_container_removed",
        "gpu_audio_nodes_absent",
        "delivery_archives_exclude_fixture",
    ):
        assert current[key] is True
    assert current["overflow_policy"] == "own-id-display-space-notice-or-empty-below-notice-minimum"
    assert current["game_exit_code"] == 0
    assert (current["renderer_backend"], current["renderer_device"]) == ("Vulkan", "llvmpipe")
    assert current["cpu_limit"] == 2
    assert current["memory_limit_bytes"] == 4 * 1024**3
    assert current["swap_limit_bytes"] == 0
    assert current["network_interfaces"] == ["lo"]
    for key in (
        "historical_cohorts_all_reexecuted",
        "timed_out",
        "credential_leak_detected",
        "native_host_command_or_speech_requested",
        "physical_keys_or_focus_qualified",
        "human_account_used",
        "physical_microphone",
        "physical_playback",
        "other_fonts_or_transient_overlay_visibility_qualified",
        "default_build_starts_client_gametest",
    ):
        assert current[key] is False
    assert current["human_hearing"] == "unconfirmed"
    identities = current["evidence_ids"]
    assert set(identities) == {"actual_client", "default_build", "independent_review"}
    assert len(set(identities.values())) == len(identities)
    assert not set(identities.values()) & set(receipt["client_runtime_requalification"]["evidence_ids"].values())
    for identity in identities.values():
        parsed = UUID(identity)
        assert str(parsed) == identity
        assert parsed.version == 4


def test_software_client_qualification_keeps_synthetic_input_and_visual_limits() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["client_runtime_requalification"]
    assert current["profile"] == "software-client-control@1"
    assert set(current["prior_changed_source_fingerprints"]) == {
        "clients/minecraft-voice/build.gradle",
        "clients/minecraft-voice/gradle.lockfile",
    }
    for name, digest in current["prior_changed_source_fingerprints"].items():
        assert digest != receipt["source_fingerprints"][name]
    sources = ROOT / "clients/minecraft-voice/src/gametest"
    assert set(current["newly_qualified_sources"]) == {
        str(path.relative_to(ROOT)) for path in sources.rglob("*") if path.is_file()
    }
    assert current["production_java_sources_unchanged"] is True
    assert current["runtime_main_classes_equal_delivery"] == current["pure_java_tests"] == 20
    assert current["actual_game_client_launched"] is current["scenario_assertions_reached"] is True
    assert current["production_initializations"] == 1
    assert current["record_ingress"] == 5
    assert current["stop_ingress"] == 4
    assert current["own_hud_callback_observations"] > 0
    assert current["game_exit_code"] == 0
    assert current["timed_out"] is current["separate_official_pass_log_attested"] is False
    for key in (
        "actual_menu_and_disconnect",
        "held_record_did_not_replay",
        "stop_before_blocked_ordinary_response",
        "original_gesture_identity_and_deadline_retained",
        "actual_stopping_event",
        "production_workers_retired",
        "fixture_workers_retired",
        "protocol_healthy",
        "gpu_audio_nodes_absent",
        "host_home_absent",
        "owned_container_removed",
        "delivery_archives_exclude_fixture",
    ):
        assert current[key] is True
    assert (current["renderer_backend"], current["renderer_device"]) == ("Vulkan", "llvmpipe")
    assert current["cpu_limit"] == 2
    assert current["memory_limit_bytes"] == 4 * 1024**3
    assert current["swap_limit_bytes"] == 0
    assert current["network_interfaces"] == ["lo"]
    assert current["synthetic_protocol_result"] == "no_action"
    for key in (
        "unchanged_historical_cohorts_reexecuted",
        "credential_leak_detected",
        "native_host_command_or_speech_requested",
        "physical_keys_or_focus_qualified",
        "human_account_used",
        "physical_microphone",
        "physical_playback",
        "default_build_starts_client_gametest",
    ):
        assert current[key] is False
    assert current["hud_visual_readability"] == "clipped-at-640x480"
    assert current["human_hearing"] == "unconfirmed"
    identities = current["evidence_ids"]
    assert set(identities) == {"actual_client", "default_build", "independent_review"}
    assert len(set(identities.values())) == len(identities)
    assert not set(identities.values()) & set(receipt["control_requalification"]["evidence_ids"].values())
    for identity in identities.values():
        parsed = UUID(identity)
        assert str(parsed) == identity
        assert parsed.version == 4


def test_companion_qualification_keeps_its_evidence_boundary() -> None:
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["source_identity"]["atomic_transitive_closure_attested"] is False
    assert receipt["source_identity"]["clean_checkout_attested"] is False
    checks = receipt["headless_checks"]
    assert checks["observed_head_turn_degrees"] > 10
    assert checks["observed_movement_blocks"] > 0.2
    assert checks["navigation_destination_completion_claimed"] is False
    assert checks["queued_commands_cancelled_by_stop"] == 3
    assert checks["lost_ack_unknown_without_repost"] is True
    assert checks["pre_run_cancellation_records"] == 3
    assert checks["historical_stop_replay_and_collision"] is True
    assert checks["same_actor_after_restart"] is True
    assert checks["stale_boot_http_status"] == 409
    assert receipt["speech"]["synthetic_only"] is True
    assert receipt["speech"]["slovak_examples_admitted"] is False
    assert receipt["speech"]["transcriber_family"] == "parakeet-tdt-0.6b-v3"
    alternative = receipt["speech"]["explicit_alternative"]
    assert alternative["schema_version"] == 2
    assert alternative["transcriber_family"] == "whisper-small"
    assert alternative["slovak_idle_applied"] is True
    assert alternative["english_state_applied"] is True
    assert alternative["slovak_say_refused"] is True
    assert alternative["czech_say_refused"] is True
    assert alternative["operation_provenance_verified"] is True
    assert alternative["original_transcript_framing_retained"] is True
    assert alternative["captured_voice_identity_verified"] is True
    assert alternative["automatic_fallback"] is False
    assert alternative["human_microphone"] is False
    assert "qualification_evidence_sha256" not in receipt
    evidence_ids = receipt["qualification_evidence_ids"]
    assert set(evidence_ids) == {
        "headless",
        "restart",
        "synthetic_voice",
        "synthetic_whisper",
        "optional_local_intent",
        "synthetic_controller",
        "controller_negative_control",
        "refusal_reasons",
        "reply_evidence",
    }
    assert len(set(evidence_ids.values())) == len(evidence_ids)
    for identity in evidence_ids.values():
        parsed = UUID(identity)
        assert str(parsed) == identity
        assert parsed.version == 4
    assert {"human_microphone", "physical_playback", "prism_join", "live_player_follow", "windows"} <= set(
        receipt["unexercised"]
    )


def test_console_ingress_requalification_keeps_current_and_historical_checks_distinct() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["source_requalification"]
    assert current["profile"] == "console-ingress-requalification@1"
    assert set(current["prior_changed_source_fingerprints"]) == {
        "scripts/companion_lab.py",
        "tests/unit/cli/test_companion_lab.py",
    }
    for name, digest in current["prior_changed_source_fingerprints"].items():
        assert digest != receipt["source_fingerprints"][name]
        assert len(digest) == 64
        assert all(char in "0123456789abcdef" for char in digest)
    assert current["unchanged_historical_cohorts_reexecuted"] is False
    assert current["reader_native_transport_cases"] == current["original_console_negative_controls_rejected"] == 2
    assert current["fresh_headless_game_passed"] is True
    assert current["synthetic_cpu_voice_cases_applied"] == current["generated_reply_wavs"] == 2
    assert current["human_microphone"] is current["physical_playback"] is False
    assert current["gpu_or_intent_used"] is False
    assert current["accuracy_benchmark"] is False
    identities = current["evidence_ids"]
    assert set(identities) == {"headless", "console_ingress", "synthetic_voice"}
    assert len(set(identities.values())) == len(identities)
    for identity in identities.values():
        parsed = UUID(identity)
        assert str(parsed) == identity
        assert parsed.version == 4
    assert not set(identities.values()) & set(receipt["qualification_evidence_ids"].values())


def test_optional_local_intent_qualification_keeps_its_evidence_boundary() -> None:
    receipt = json.loads(RECEIPT.read_text())
    interpretation = receipt["optional_local_intent"]
    assert interpretation["native_run_graph_dispatcher_forge"] is True
    assert interpretation["exact_response_identity_verified"] is True
    assert interpretation["literal_loopback_only"] is True
    assert interpretation["typed_control_model_requests"] == 0
    assert interpretation["max_requests_per_instruction"] == 1
    assert interpretation["max_tokens"] == 512
    assert interpretation["model_timeout_seconds"] == 15
    assert interpretation["tool_calls"] == 0
    assert interpretation["automatic_retry"] is False
    assert interpretation["automatic_fallback"] is False
    assert interpretation["closed_decisions_retained"] is True
    assert interpretation["qualification_cases"] == 11
    assert interpretation["synthetic_slovak_idle_applied"] is True
    assert interpretation["synthetic_czech_state_applied"] is True
    assert interpretation["synthetic_english_idle_applied"] is True
    assert interpretation["synthetic_negated_follow_decision"] == "no_action"
    assert interpretation["synthetic_unsupported_build_decision"] == "no_action"
    assert interpretation["multiple_actions_no_game_effect"] is True
    assert interpretation["configured_offline_follow_target_refused"] is True
    assert interpretation["artifact_identity_and_original_transcript_verified"] is True
    assert interpretation["active_leases_after"] == 0
    assert interpretation["model_device_attested"] is False
    assert interpretation["loaded_weights_attested"] is False
    assert interpretation["human_microphone"] is False
    assert interpretation["physical_playback"] is False
    assert interpretation["live_player_follow"] is False
    assert interpretation["accuracy_benchmark"] is False


def test_synthetic_controller_qualification_keeps_its_evidence_boundary() -> None:
    receipt = json.loads(RECEIPT.read_text())
    controller = receipt["synthetic_controller"]
    assert controller["real_engine_navigation_and_physics"] is True
    assert controller["synthetic_player_in_actual_player_list"] is True
    assert controller["production_sources_unchanged"] is True
    assert controller["fixture_ticks"] == 166
    assert controller["movement_wait_and_resume_observed"] is True
    assert controller["approach_bounding_boxes_disjoint"] is True
    assert controller["refused_navigation_retains_original_follow_deadline"] is True
    assert controller["state_and_chat_do_not_replace_follow"] is True
    assert controller["queued_expiry_and_priority_stop"] is True
    assert controller["target_excess_distance_disconnect_and_death"] is True
    assert controller["lease_clock"] == "synthetic-50ms-per-controller-tick"
    assert controller["real_time_latency_qualified"] is False
    assert controller["cleanup_and_private_ticket_release"] is True
    assert controller["delivery_archives_exclude_test_assets"] is True
    assert controller["default_build_starts_gametest"] is False
    assert controller["wait_only_counterfactual_rejected_for_nonmovement"] is True
    assert controller["counterfactual_cleanup_and_ticket_release"] is True
    assert controller["authenticated_human_follow"] is False
    assert controller["cross_chunk_navigation"] is False
    assert controller["wrong_dimension_transfer"] is False


def test_refusal_reason_qualification_keeps_its_evidence_boundary() -> None:
    receipt = json.loads(RECEIPT.read_text())
    reasons = receipt["refusal_reasons"]
    assert reasons["qualification_cases"] == reasons["generated_reply_wavs"] == 9
    assert reasons["host_known_reasons"] == [
        "target_unavailable",
        "bounds",
        "interpretation_budget_exhausted",
        "interpretation_response_refused",
        "interpretation_unavailable",
    ]
    assert reasons["request_run_result_and_feedback_correlated"] is True
    assert reasons["denied_cases_action_posts"] == 0
    assert reasons["action_posts_evidence"] == "instrumented-transport-assertions"
    assert reasons["typed_state_fallback_cases"] == 3
    assert reasons["typed_state_fallback_model_dispatches"] == 0
    assert reasons["raw_diagnostic_classification"] is False
    assert reasons["automatic_retry"] is False
    assert reasons["human_microphone"] is False
    assert reasons["physical_playback"] is False


def test_reply_evidence_qualification_keeps_its_evidence_boundary() -> None:
    receipt = json.loads(RECEIPT.read_text())
    reply = receipt["reply_evidence"]
    assert reply["qualification_cases"] == 7
    assert reply["generated_reply_wavs"] == 5
    assert reply["suppressed_stale_replies"] == 2
    assert reply["request_run_and_game_outcome_correlated"] is True
    assert reply["unchanged_synthesis_metadata_and_digests_verified"] is True
    assert reply["caller_cancellation_preserves_later_actual_run"] is True
    assert reply["known_pre_run_absence_recorded"] is True
    assert reply["all_reply_owners_settled"] is True
    assert reply["active_leases_after"] == 0
    assert reply["player_process_started"] is False
    assert reply["human_microphone"] is False
    assert reply["physical_playback"] is False
    assert reply["human_hearing"] == "unconfirmed"


def test_human_console_requalification_keeps_live_and_portable_evidence_separate() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["interaction_requalification"]
    assert current["profile"] == "private-human-console@1"
    assert set(current["prior_changed_source_fingerprints"]) == {
        "scripts/companion_lab.py",
        "src/lychd/system/services/companion_session.py",
    }
    assert set(current["newly_qualified_sources"]) == {
        "src/lychd/cli/companion_view.py",
        "tests/unit/cli/test_companion_view.py",
        "tests/unit/cli/test_companion_human.py",
        "tests/integration/test_companion_status.py",
    }
    for name, digest in current["prior_changed_source_fingerprints"].items():
        assert digest != receipt["source_fingerprints"][name]
        assert len(digest) == 64
        assert all(char in "0123456789abcdef" for char in digest)
    assert current["portable_cases"] == {"human_console": 12, "pure_view": 48, "native_status": 2}
    assert current["real_cli_synthetic_voice_cases"] == current["generated_reply_wavs"] == 2
    for key in (
        "query_did_not_admit_native_work",
        "native_and_audio_failures_distinct",
        "empty_server_headless_passed",
    ):
        assert current[key] is True
    for key in (
        "earlier_cohorts_all_reexecuted",
        "json_added_raw_recognition",
        "human_microphone",
        "physical_playback",
        "gpu_or_intent_used",
        "accuracy_benchmark",
    ):
        assert current[key] is False
    identities = current["evidence_ids"]
    assert set(identities) == {"headless", "real_cli_synthetic_voice", "portable_failures"}
    assert len(set(identities.values())) == len(identities)
    earlier = set(receipt["qualification_evidence_ids"].values()) | set(
        receipt["source_requalification"]["evidence_ids"].values()
    )
    assert not earlier & set(identities.values())
    for identity in identities.values():
        parsed = UUID(identity)
        assert str(parsed) == identity
        assert parsed.version == 4


def test_cell_observation_qualification_retains_provenance_and_unqualified_boundaries() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["cell_observation_requalification"]
    assert (current["profile"], current["operation"], current["observation_profile"]) == (
        "bounded-one-cell-observation@1",
        "inspect@1",
        "blockworld.cell@1",
    )
    assert current["wire_envelope_protocol"] == 1
    assert current["legacy_state_and_action_shapes_unchanged"] is True
    assert (current["implementation_revision"], current["checkpoint_schema"]) == ("py.4", "companion-state-v4")
    for name, digest in current["prior_changed_source_fingerprints"].items():
        assert digest != receipt["source_fingerprints"][name]
    assert current["native_fixture_cases"] == 93
    assert current["pure_java_cases"] == 31
    assert current["required_world_tests"] == 2
    assert current["controller_fixture_ticks"] == 166
    assert current["controller_fixture_qualified"] is current["controller_fixture_cleanup"] is True
    assert current["successful_read_preserves_original_short_lease"] is True
    assert current["counterfactual_worlds_rejected"] == 2
    assert current["counterfactual_owned_cleanup"] is True
    assert current["real_unloaded_chunk_branch_executed"] is False
    assert current["live_native_runs"] == current["live_action_posts"] == 3
    assert current["live_cell_reads"] == 2
    assert current["live_blocks_observed"] == ["minecraft:grass_block", "minecraft:air"]
    assert current["live_nondefault_property"] == {"snowy": "false"}
    assert current["live_controller_original_limit_ms"] == 2500
    assert current["live_reads_preserved_controller"] is True
    assert current["live_original_limit_elapsed_without_active_controller"] is True
    assert current["live_stop_posts"] == 1
    assert current["live_closed_stopped"] is True
    assert current["same_actor_after_restart"] is True
    assert current["stop_java_exit_status"] == 143
    assert current["graceful_world_save_attested"] is False
    assert current["server_artifact_test_assets_excluded"] is True
    assert len(current["server_artifact_sha256"]) == 64
    assert current["server_artifact_production_classes_matched"] == 25
    assert current["unchanged_historical_cohorts_reexecuted"] is False
    assert current["game_client_launched"] is current["physical_microphone"] is current["physical_playback"] is False
    assert current["gpu_or_model_or_speech_used"] is False
    identities = current["evidence_ids"]
    assert len(identities) == len(set(identities.values())) == 5
    for identity in identities.values():
        assert str(UUID(identity)) == identity
        assert UUID(identity).version == 4


def test_voice_timing_qualification_keeps_host_and_human_evidence_distinct() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["voice_timing_requalification"]
    assert current["profile"] == "companion-host-timing@1"
    assert set(current["prior_changed_source_fingerprints"]) == {
        "scripts/companion_lab.py",
        "src/lychd/cli/companion_view.py",
    }
    for name, digest in current["prior_changed_source_fingerprints"].items():
        assert digest != receipt["source_fingerprints"][name]
    assert current["newly_qualified_sources"] == ["tests/unit/cli/test_companion_timing.py"]
    assert current["portable_timing_cases"] == 32
    assert current["actual_transcription_calls"] == current["live_native_runs_applied"] == 1
    assert current["actual_synthesis_calls"] == 2
    assert current["single_synthetic_example_ms"] == {
        "local_elapsed": 5053,
        "transcription": 2511,
        "queue_and_native_result": 99,
        "synthesis": 2392,
    }
    assert current["origin"] == "accepted_host_voice_admission"
    for key in (
        "preentry_cancellation_retains_timing",
        "local_unavailable_outcome_does_not_wait_for_native",
        "timing_failure_has_no_native_or_audio_authority",
        "disabled_replies_keep_existing_custody",
        "fixed_relative_stages_not_summed",
        "closed_localized_status_and_endpoint",
        "live_closed_stopped",
    ):
        assert current[key] is True
    for key in (
        "all_historical_cohorts_reexecuted",
        "physical_microphone",
        "physical_playback",
        "human_accuracy_benchmark",
        "game_client_launched",
        "game_artifact_redeployed",
        "gpu_or_interpreter_used",
        "native_echo_timing_shipped",
    ):
        assert current[key] is False
    assert current["human_hearing"] == "unconfirmed"
    for identity in current["evidence_ids"].values():
        assert str(UUID(identity)) == identity
        assert UUID(identity).version == 4


def test_synthetic_multilingual_cohort_retains_failures_without_human_accuracy_claim() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["multilingual_synthetic_requalification"]
    assert current["profile"] == "resident-cpu-synthetic-multilang@1"
    assert current["cases"] == 12
    assert current["ordinary_runs_applied"] == current["generated_reply_wavs"] == 4
    assert current["spoken_stop_applied"] == current["expected_negative_refusal"] == 1
    assert current["unexpected_refusals"] == 6
    assert current["matched_kinds_including_stop_and_negative"] == 6
    assert current["ordinary_applied_cases"] == ["en-state", "sk-idle", "en-say", "sk-mixed"]
    assert current["unexpected_refused_cases"] == [
        "sk-state",
        "cs-state",
        "cs-idle",
        "en-idle",
        "sk-say",
        "cs-say",
    ]
    assert current["actual_transcription_calls"] == 12
    assert current["actual_synthesis_calls"] == 16
    for key in (
        "production_source_fingerprints_unchanged",
        "original_transcript_and_native_input_match",
        "failed_cases_have_no_invented_run_or_reply",
        "coupled_tts_stt_failures_not_attributed",
        "unexpected_movement_and_inspection_guarded",
        "closed_stopped",
    ):
        assert current[key] is True
    for key in (
        "all_historical_live_cohorts_reexecuted",
        "human_accuracy_benchmark",
        "physical_microphone",
        "physical_playback",
        "human_hearing_qualified",
        "game_client_launched",
        "gpu_or_interpreter_used",
        "hosted_voice_requested",
        "provider_changed",
        "model_installed",
        "automatic_fallback",
        "cold_start_latency_measured",
        "new_provider_dialect_shipped",
    ):
        assert current[key] is False
    for identity in current["evidence_ids"].values():
        assert str(UUID(identity)) == identity
        assert UUID(identity).version == 4


def test_language_control_qualification_preserves_existing_utterance_and_profile_ownership() -> None:
    receipt = json.loads(RECEIPT.read_text())
    current = receipt["host_language_control_requalification"]
    assert current["profile"] == "companion-console-language@1"
    assert current["portable_cases"] == 32
    assert current["languages"] == ["sk", "cs", "en"]
    assert set(current["prior_changed_source_fingerprints"]) == {
        "scripts/companion_lab.py",
        "src/lychd/cli/companion_view.py",
        "tests/unit/cli/test_companion_view.py",
    }
    for name, digest in current["prior_changed_source_fingerprints"].items():
        assert digest != receipt["source_fingerprints"][name]
    assert current["newly_qualified_sources"] == ["tests/unit/cli/test_companion_language.py"]
    for key in (
        "query_has_no_game_or_speech_request",
        "both_validations_before_mutation",
        "busy_change_refuses_not_queues",
        "original_pending_locales_and_request_preserved",
        "omitted_reply_preserves_disabled_state",
        "playback_preference_and_audio_latch_preserved",
        "reader_generation_and_deadline_fences_preserved",
        "same_reader_batch_order_preserved",
        "version2_independent_bindings_preserved",
    ):
        assert current[key] is True
    for key in (
        "profile_rewritten",
        "new_provider_or_model_selected",
        "automatic_language_detection_added",
        "actual_speech_requests",
        "actual_game_commands",
        "physical_audio_qualified",
        "game_client_launched",
        "gpu_or_interpreter_used",
        "all_historical_live_cohorts_reexecuted",
    ):
        assert current[key] is False
