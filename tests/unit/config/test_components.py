"""build_saq_config: Topology A wiring + the rites-queue claim (F1/F3, H1/H2)."""

from __future__ import annotations

import pytest

from lychd.config.components import build_saq_config
from lychd.config.settings.root import Settings


def _settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("LYCHD_DB_PASSWORD", "test-db-password")
    return Settings()


def _queues(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    config = build_saq_config(_settings(monkeypatch))
    return {qc.name: qc for qc in config.queue_configs}


def test_topology_a_both_queues_run_in_process(monkeypatch: pytest.MonkeyPatch) -> None:
    """F1/H1: BOTH queues carry `separate_process=False` — no forked workers remain."""
    queues = _queues(monkeypatch)
    assert set(queues) == {"runs", "rites"}
    assert all(qc.separate_process is False for qc in queues.values())  # type: ignore[attr-defined]


def test_no_server_lifespan_forks(monkeypatch: pytest.MonkeyPatch) -> None:
    """F1/H1: `use_server_lifespan=False` stops the plugin from spawning worker forks."""
    config = build_saq_config(_settings(monkeypatch))
    assert config.use_server_lifespan is False


def test_saq_admin_ui_is_optional_and_uses_the_vessel_http_server(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch)
    config = build_saq_config(settings)
    assert config.web_enabled is False
    assert config.web_path == "/saq"

    settings.server.jobs.admin_ui_enabled = True
    settings.server.jobs.admin_ui_path = "/jobs"
    config = build_saq_config(settings)
    assert config.web_enabled is True
    assert config.web_path == "/jobs"


def test_rites_queue_can_claim_perform_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """F3/H2: rite-routed intents (`source=rite` → `rites`) must be claimable — perform_run is registered.

    `QueueConfig.__post_init__` resolves task dotted-paths to the functions themselves,
    so assert by function identity (perform_run present on BOTH the runs and rites queues).
    """
    from lychd.ghouls.runs import perform_run

    queues = _queues(monkeypatch)
    assert perform_run in list(queues["rites"].tasks)  # type: ignore[attr-defined]
    assert perform_run in list(queues["runs"].tasks)  # type: ignore[attr-defined]
