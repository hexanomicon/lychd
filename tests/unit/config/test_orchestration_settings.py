"""O6: the `[orchestration]` settings — defaults, routing equivalence, env/TOML round-trip."""

from __future__ import annotations

from pathlib import Path

import pytest

import lychd.config.settings.root as settings_mod
from lychd.config.settings.orchestration import OrchestrationSettings
from lychd.config.settings.root import Settings
from lychd.config.settings.server import ServerJobsSettings
from lychd.domain.cortex.engine import DEFAULT_ROUTING, RouteRule


def test_orchestration_defaults() -> None:
    orch = OrchestrationSettings()
    assert orch.switching.policy == "evict-idle"
    assert orch.switching.actuator == "host-reactor"
    assert orch.switching.min_priority_for_hard_swap == 40
    assert orch.switching.drain_timeout_s == 120.0
    assert orch.whim.idle_evict_after_s == 0
    assert orch.whim.preload == []


def test_default_routing_settings_equal_engine_default() -> None:
    """The settings routing default MUST equal the code-side `DEFAULT_ROUTING` table."""
    routing = OrchestrationSettings().routing
    as_route_rules = {source: RouteRule(rule.queue, rule.priority) for source, rule in routing.items()}
    assert as_route_rules == DEFAULT_ROUTING


def test_orchestration_env_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nested env vars override the switching knobs (env_nested_delimiter='__')."""
    monkeypatch.setenv("ORCHESTRATION__SWITCHING__MIN_PRIORITY_FOR_HARD_SWAP", "15")
    monkeypatch.setenv("ORCHESTRATION__SWITCHING__DRAIN_TIMEOUT_S", "7.5")
    settings = Settings()
    assert settings.orchestration.switching.min_priority_for_hard_swap == 15
    assert settings.orchestration.switching.drain_timeout_s == 7.5


def test_orchestration_toml_round_trip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The `[orchestration]` block round-trips from the TOML settings source."""
    toml = tmp_path / "lychd.toml"
    toml.write_text(
        "[orchestration.switching]\n"
        'policy = "evict-idle"\n'
        "min_priority_for_hard_swap = 33\n"
        "[server.jobs]\n"
        "interactive_concurrency = 9\n",
        encoding="utf-8",
    )
    toml.chmod(0o600)  # keep the codex-permission validator quiet
    monkeypatch.setattr(settings_mod, "PATH_LYCHD_TOML", toml)
    settings = Settings()
    assert settings.orchestration.switching.min_priority_for_hard_swap == 33
    assert settings.server.jobs.interactive_concurrency == 9
    assert settings.server.jobs.background_concurrency == 4


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


def test_unknown_switch_policy_fails_loudly_at_composition(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bogus `switching.policy` fails at the composition root, naming the registered ones."""
    from litestar.contrib.jinja import JinjaTemplateEngine

    import lychd.domain.web.altar_services as altar_mod

    bad = Settings()
    bad.orchestration.switching.policy = "does-not-exist"
    monkeypatch.setattr(altar_mod, "get_settings", lambda: bad)

    templates = Path(__file__).resolve().parents[2].parent / "src" / "lychd" / "domain" / "web" / "templates"
    with pytest.raises(ValueError, match="evict-idle"):
        altar_mod.build_altar_services(
            template_engine=JinjaTemplateEngine(directory=templates),
            queues={},
            rune_schemas=[],
            runtime_adapters=[],
            profile="memory",
        )


def test_missing_routed_queues_fail_before_runtime_publication(monkeypatch: pytest.MonkeyPatch) -> None:
    """A composition cannot persist a run whose configured physical queue is absent."""
    from litestar.contrib.jinja import JinjaTemplateEngine

    import lychd.domain.web.altar_services as altar_mod

    settings = Settings()
    monkeypatch.setattr(altar_mod, "get_settings", lambda: settings)
    templates = Path(__file__).resolve().parents[2].parent / "src" / "lychd" / "domain" / "web" / "templates"

    with pytest.raises(RuntimeError, match=r"rites.*runs|runs.*rites"):
        altar_mod.build_altar_services(
            template_engine=JinjaTemplateEngine(directory=templates),
            queues={},
            rune_schemas=[],
            runtime_adapters=[],
            profile="memory",
        )
