"""`altar_services_lifespan` — the ONE web-layer assembly site (§TD-5).

Builds `AltarServices` once, stamps it on `app.state.services`, wires the real
`RunEngine` + process `RunSubstrate` against the SAQ queues (Topology A: the
in-process ghoul shares this bus), registers the request-independent `route_path`
Jinja global + `run_data_state` filter, warms the registry off the event loop,
reconciles orphaned runs at startup, and drains on shutdown.

This module is a composition root — importing `extensions.host` here is allowed.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING, cast

import structlog

from lychd.domain.web.altar_services import build_altar_services

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from litestar import Litestar
    from litestar.contrib.jinja import JinjaTemplateEngine

    from lychd.domain.cortex.engine import RunQueue

logger = structlog.get_logger()

_RUN_QUEUE_NAMES = ("runs", "rites")


def _collect_run_queues(app: Litestar) -> dict[str, RunQueue]:
    """Return the SAQ queues the engine enqueues onto (empty if SAQ is absent).

    Runtime seam: in the web test client (no SAQ plugin) this is empty and the real
    engine is never exercised — the web tests use the fake engine. Production always
    carries the SAQ plugin.
    """
    from litestar_saq import SAQPlugin

    queues: dict[str, RunQueue] = {}
    with suppress(Exception):
        plugin = app.plugins.get(SAQPlugin)
        for name in _RUN_QUEUE_NAMES:
            with suppress(Exception):
                queues[name] = cast("RunQueue", plugin.get_queue(name))
    return queues


@asynccontextmanager
async def altar_services_lifespan(app: Litestar) -> AsyncIterator[None]:
    """Assemble, publish, wire, warm, reconcile, and later drain the Altar services."""
    from lychd.extensions.host import get_extensions  # composition root only

    engine = cast("JinjaTemplateEngine", app.template_engine)
    exts = get_extensions()
    services = build_altar_services(
        template_engine=engine,
        rune_schemas=exts.rune_schemas,
        runtime_adapters=exts.runtime_adapters,
    )

    app.state.services = services

    # Wire the real run engine + publish the process RunSubstrate (Topology A: the
    # in-process ghoul and the SSE handler share this event bus).
    services.wire_runtime(_collect_run_queues(app))

    # Request-independent url reversal for every template (works in SSE too), plus
    # the frozen run-state `data-state` mapping as a Jinja filter.
    from lychd.domain.web.schemas import run_data_state

    engine.engine.globals["route_path"] = app.route_reverse  # pyright: ignore[reportArgumentType]
    engine.engine.filters["run_data_state"] = run_data_state

    # Warm the registry off the event loop: rune loading + quadlet transmutation is
    # synchronous disk IO, so force it at startup instead of stalling the first handler.
    await asyncio.to_thread(services.registry.ensure_loaded)

    # Reconcile orphaned RUNNING runs a dead process left behind (durable ledger only;
    # a no-op under the in-memory ledger, which starts empty each process).
    await _reconcile_at_startup()
    try:
        yield
    finally:
        from lychd.domain.cortex.substrate import reset_run_substrate

        await services.aclose()
        reset_run_substrate()


async def _reconcile_at_startup() -> None:
    """Run the orphan-run reconcile once, guarded (never blocks startup)."""
    from lychd.ghouls.runs import reconcile_runs

    with suppress(Exception):
        await reconcile_runs({})
