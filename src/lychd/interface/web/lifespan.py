"""`altar_services_lifespan` — the ONE web-layer assembly site (§TD-5).

Builds `AltarServices` once, stamps it on `app.state.services`, mirrors the
run-scoped collaborators on `app.state` (so the agents layer's `submit` can build
its `WorkflowServices`), registers the request-independent `route_path` Jinja global
(url reversal that also works inside Projector-rendered SSE payloads), warms the
registry off the event loop, and drains on shutdown.

This module is a composition root — importing `extensions.host` here is allowed.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, cast

from lychd.domain.web.altar_services import build_altar_services

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from litestar import Litestar
    from litestar.contrib.jinja import JinjaTemplateEngine


@asynccontextmanager
async def altar_services_lifespan(app: Litestar) -> AsyncIterator[None]:
    """Assemble, publish, warm, and later drain the Altar's web services."""
    from lychd.extensions.host import get_extensions  # composition root only

    engine = cast("JinjaTemplateEngine", app.template_engine)
    exts = get_extensions()
    services = build_altar_services(
        template_engine=engine,
        rune_schemas=exts.rune_schemas,
        runtime_adapters=exts.runtime_adapters,
    )

    app.state.services = services
    # Mirror the run-scoped handles on app.state so the agents layer's submit can
    # build its WorkflowServices (contract for the agents builder).
    app.state.registry = services.registry
    app.state.dispatcher = services.dispatcher
    app.state.orchestrator = services.orchestrator
    app.state.context_orchestrator = services.context_orchestrator
    app.state.fragments = services.fragments
    app.state.bridge_sessions = services.bridge_sessions
    app.state.tickets = services.tickets
    services.run_engine.bind(app.state)

    # Request-independent url reversal for every template (works in SSE too), plus
    # the frozen run-state `data-state` mapping as a Jinja filter.
    from lychd.domain.web.schemas import run_data_state

    engine.engine.globals["route_path"] = app.route_reverse  # pyright: ignore[reportArgumentType]
    engine.engine.filters["run_data_state"] = run_data_state

    # Warm the registry off the event loop: rune loading + quadlet transmutation is
    # synchronous disk IO, so force it at startup instead of stalling the first handler.
    await asyncio.to_thread(services.registry.ensure_loaded)
    try:
        yield
    finally:
        await services.aclose()
