"""build_saq_config: Topology A wiring + the rites-queue claim (F1/F3, H1/H2)."""

from __future__ import annotations

from lychd.config.components import build_saq_config
from lychd.config.settings import get_settings


def _queues() -> dict[str, object]:
    config = build_saq_config(get_settings())
    return {qc.name: qc for qc in config.queue_configs}


def test_topology_a_both_queues_run_in_process() -> None:
    """F1/H1: BOTH queues carry `separate_process=False` — no forked workers remain."""
    queues = _queues()
    assert set(queues) == {"runs", "rites"}
    assert all(qc.separate_process is False for qc in queues.values())  # type: ignore[attr-defined]


def test_no_server_lifespan_forks() -> None:
    """F1/H1: `use_server_lifespan=False` stops the plugin from spawning worker forks."""
    config = build_saq_config(get_settings())
    assert config.use_server_lifespan is False


def test_rites_queue_can_claim_perform_run() -> None:
    """F3/H2: rite-routed intents (`source=rite` → `rites`) must be claimable — perform_run is registered.

    `QueueConfig.__post_init__` resolves task dotted-paths to the functions themselves,
    so assert by function identity (perform_run present on BOTH the runs and rites queues).
    """
    from lychd.ghouls.runs import perform_run

    queues = _queues()
    assert perform_run in list(queues["rites"].tasks)  # type: ignore[attr-defined]
    assert perform_run in list(queues["runs"].tasks)  # type: ignore[attr-defined]
