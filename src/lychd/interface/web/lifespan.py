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
from contextlib import asynccontextmanager
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
    """Return the SAQ queues the engine enqueues onto.

    Runtime seam: in the web test client (no SAQ plugin) this returns empty and the
    real engine is never exercised — the web tests use the fake engine. Production
    always carries the SAQ plugin, and every routed queue name MUST resolve: a
    missing queue raises loudly here (F3/H2) rather than silently returning a partial
    map that would black-hole every intent routed to the absent queue.
    """
    from litestar_saq import SAQPlugin

    try:
        plugin = app.plugins.get(SAQPlugin)
    except Exception:  # noqa: BLE001 - SAQ plugin genuinely absent (non-server contexts)
        return {}
    # No inner suppress: an unregistered queue name is a wiring bug, not a shrug.
    return {name: cast("RunQueue", plugin.get_queue(name)) for name in _RUN_QUEUE_NAMES}


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
    """Run the orphan-run reconcile once at startup.

    Must not block startup on a transient DB hiccup, but the old silent `suppress`
    hid real reconcile failures (F9/H2). Log loudly instead — the failure is
    visible, startup still proceeds.
    """
    from lychd.ghouls.runs import reconcile_runs

    try:
        await reconcile_runs({})
    except Exception:
        logger.exception("reconcile_at_startup_failed")
