"""O6: the `[orchestration]` settings — defaults, routing equivalence, env/TOML round-trip."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

import lychd.config.settings.root as settings_mod
from lychd.config.settings.orchestration import OrchestrationSettings, SwitchingSettings
from lychd.config.settings.root import Settings
from lychd.config.settings.server import ServerJobsSettings


def test_orchestration_defaults() -> None:
    orch = OrchestrationSettings()
    assert orch.switching.policy == "declared-conflicts"
    assert orch.switching.actuator == "host-reactor"
    assert orch.switching.min_priority_for_hard_swap == 40
    assert orch.switching.drain_timeout_s == 120.0
    assert orch.switching.systemctl_timeout_s == 120.0


def test_orchestration_env_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nested env vars override the switching knobs (env_nested_delimiter='__')."""
    monkeypatch.setenv("ORCHESTRATION__SWITCHING__MIN_PRIORITY_FOR_HARD_SWAP", "15")
    monkeypatch.setenv("ORCHESTRATION__SWITCHING__DRAIN_TIMEOUT_S", "7.5")
    monkeypatch.setenv("ORCHESTRATION__SWITCHING__SYSTEMCTL_TIMEOUT_S", "8.5")
    settings = Settings()
    assert settings.orchestration.switching.min_priority_for_hard_swap == 15
    assert settings.orchestration.switching.drain_timeout_s == 7.5
    assert settings.orchestration.switching.systemctl_timeout_s == 8.5


def test_orchestration_toml_round_trip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The `[orchestration]` block round-trips from the TOML settings source."""
    toml = tmp_path / "lychd.toml"
    toml.write_text(
        "[orchestration.switching]\n"
        'policy = "declared-conflicts"\n'
        "min_priority_for_hard_swap = 33\n"
        "systemctl_timeout_s = 9.5\n"
        "[server.jobs]\n"
        "interactive_concurrency = 9\n",
        encoding="utf-8",
    )
    toml.chmod(0o600)  # keep the codex-permission validator quiet
    monkeypatch.setattr(settings_mod, "PATH_LYCHD_TOML", toml)
    settings = Settings()
    assert settings.orchestration.switching.min_priority_for_hard_swap == 33
    assert settings.orchestration.switching.systemctl_timeout_s == 9.5
    assert settings.server.jobs.interactive_concurrency == 9
    assert settings.server.jobs.background_concurrency == 4


@pytest.mark.parametrize(
    ("field_name", "timeout_s"),
    [
        ("drain_timeout_s", 0.0),
        ("warmup_timeout_s", 0.0),
        ("systemctl_timeout_s", 0.0),
        ("reactor_ack_timeout_s", 0.0),
        ("drain_timeout_s", -1.0),
        ("drain_timeout_s", float("inf")),
        ("drain_timeout_s", float("-inf")),
        ("drain_timeout_s", float("nan")),
    ],
)
def test_switching_timeouts_require_finite_positive_budgets(field_name: str, timeout_s: float) -> None:
    with pytest.raises(ValidationError):
        SwitchingSettings.model_validate({field_name: timeout_s})


def test_v1_queue_topology_rejects_unimplemented_physical_queues() -> None:
    with pytest.raises(ValueError, match="gpu_concurrency"):
        ServerJobsSettings.model_validate({"gpu_concurrency": 1})

    with pytest.raises(ValueError, match="routing references unknown queues: gpu"):
        OrchestrationSettings.model_validate({"routing": {"bridge": {"queue": "gpu", "priority": 70}}})


@pytest.mark.parametrize("concurrency", [0, 129])
def test_queue_concurrency_is_strictly_bounded(concurrency: int) -> None:
    with pytest.raises(ValueError, match="concurrency"):
        ServerJobsSettings.model_validate({"interactive_concurrency": concurrency})


def test_job_admin_ui_path_is_an_absolute_vessel_route() -> None:
    assert ServerJobsSettings(admin_ui_path="/jobs/").admin_ui_path == "/jobs"
    with pytest.raises(ValueError, match="must start"):
        ServerJobsSettings(admin_ui_path="jobs")


def test_switch_policy_names_are_closed_at_the_config_boundary() -> None:
    assert SwitchingSettings(policy="evict-idle").policy == "evict-idle"
    with pytest.raises(ValidationError):
        SwitchingSettings.model_validate({"policy": "does-not-exist"})


def test_missing_routed_queues_fail_before_runtime_publication(monkeypatch: pytest.MonkeyPatch) -> None:
    """A composition cannot persist a run whose configured physical queue is absent."""
    import lychd.interface.web.altar_services as altar_mod
    from lychd.config.runes.registry import RuneRegistry

    settings = Settings()
    monkeypatch.setattr(altar_mod, "get_settings", lambda: settings)
    with pytest.raises(RuntimeError, match=r"rites.*runs|runs.*rites"):
        altar_mod.build_altar_services(
            queues={},
            runes=RuneRegistry(()),
            runtime_adapters=[],
            profile="memory",
        )
