"""`altar_services_lifespan` — the ONE web-layer assembly site (§TD-5).

Builds one queue-bound `AltarServices`, publishes its process `RunSubstrate`
(Topology A: the in-process ghoul shares this bus), stamps it on
`app.state.services`, warms the registry off the event loop, reconciles orphaned
runs at startup, and drains on shutdown.

This module is a composition root — importing `extensions.host` here is allowed.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import structlog

from lychd.domain.web.altar_services import build_altar_services
from lychd.system.services.queues import ManagedRunQueue, connect_run_queues, disconnect_run_queues

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from litestar import Litestar

    from lychd.config.runes.registry import RuneRegistry
    from lychd.config.settings.root import Settings
    from lychd.domain.cortex.engine import RunQueue

logger = structlog.get_logger()

_RUN_QUEUE_NAMES = ("runs", "rites")


def _collect_run_queues(app: Litestar) -> dict[str, RunQueue]:
    """Return the SAQ queues the engine enqueues onto.

    The production application always carries the SAQ plugin, and every routed queue
    name MUST resolve. A missing plugin or queue is a startup wiring error; returning
    an empty map would let the daemon boot with a run engine that can only black-hole
    work.
    """
    from litestar_saq import SAQPlugin

    plugin = app.plugins.get(SAQPlugin)
    return {name: cast("RunQueue", plugin.get_queue(name)) for name in _RUN_QUEUE_NAMES}


@asynccontextmanager
async def altar_services_lifespan(app: Litestar) -> AsyncIterator[None]:
    """Assemble, warm, publish, reconcile, and later drain the Altar services."""
    from lychd.config.settings.root import get_settings
    from lychd.extensions.host import get_extensions  # composition root only
    from lychd.system.host_tools import trusted_host_tool
    from lychd.system.services.runtime import wait_for_host_reactor_idle

    # F3: stamp the boot cutoff BEFORE the substrate is published (before any worker can
    # claim + set a run RUNNING). Reconcile sweeps only runs started before this instant,
    # so a run this process claims mid-startup is never mistaken for a dead-process orphan.
    boot_cutoff = datetime.now(UTC)

    exts = get_extensions()
    settings = get_settings()
    runes = cast("RuneRegistry", app.state.runes)
    services = None
    connected_queues: tuple[ManagedRunQueue, ...] = ()
    try:
        await wait_for_host_reactor_idle(settings.orchestration.switching)
        # Resolve and CONNECT every queue before constructing or publishing a
        # runtime handle. litestar-saq's in-process Worker starts detached and
        # does not connect its queue; relying on it produces a healthy-looking
        # app whose workers hot-loop on an unopened Postgres pool.
        queues = _collect_run_queues(app)
        connected_queues = await connect_run_queues(queues)
        systemctl_bin = None
        if settings.orchestration.switching.actuator == "systemd":
            systemctl_bin = trusted_host_tool("systemctl")
            if systemctl_bin is None:
                msg = "Direct systemd actuation cannot resolve a trusted systemctl executable."
                raise RuntimeError(msg)
        services = build_altar_services(
            queues=queues,
            runes=runes,
            runtime_adapters=exts.runtime_adapters,
            portal_factories=exts.portal_factories,
            settings=settings,
            systemctl_bin=systemctl_bin,
        )

        # Warm the registry off the event loop: runtime synthesis, Quadlet
        # transmutation, and initial probes are synchronous/bridged work. Rune
        # discovery already happened once in AppInit and cannot recur here.
        await asyncio.to_thread(services.registry.ensure_loaded)

        # Publish the already-complete runtime only after construction and registry
        # validation have succeeded.  There is no late dependency mutation.
        from lychd.domain.cortex.substrate import set_run_substrate

        set_run_substrate(services.substrate)

        # Preauthorization startup sync (DB profile only): upsert loaded Codex
        # preauthorizations before the first park.
        await _sync_preauths_at_startup(
            runes=runes,
            settings=settings,
        )
        await _reconcile_at_startup(boot_cutoff)
        await _reconcile_consents_at_startup(services.run_engine)

        # Publish the web-facing handle last: a partially warmed runtime is never
        # observable through app.state.
        app.state.services = services
        yield
    finally:
        from lychd.domain.cortex.substrate import reset_run_substrate

        # Litestar exits custom lifespan managers before running plugin
        # ``on_shutdown`` hooks. Topology-A SAQ workers share these services, so
        # drain them here first; otherwise a live graph can race the substrate
        # reset and bus/session cleanup. The plugin's later stop is idempotent.
        await _stop_in_process_workers(app)
        reset_run_substrate()
        try:
            if services is not None:
                await services.aclose()
        finally:
            await disconnect_run_queues(connected_queues)


async def _stop_in_process_workers(app: Litestar) -> None:
    """Await Topology-A workers before their shared runtime is dismantled."""
    from litestar_saq import SAQPlugin

    try:
        plugin = app.plugins.get(SAQPlugin)
    except (KeyError, LookupError):
        return
    workers = [worker for worker in plugin.get_workers().values() if not worker.separate_process]
    if not workers:
        return
    results = await asyncio.gather(*(worker.stop() for worker in workers), return_exceptions=True)
    for worker, result in zip(workers, results, strict=True):
        if isinstance(result, BaseException):
            logger.error(
                "saq_worker_shutdown_failed",
                queue_name=worker.queue.name,
                error=str(result),
            )


async def _reconcile_consents_at_startup(engine: Any) -> None:
    """Re-fire decided-but-unenqueued consent verdicts once at startup (loud on failure)."""
    from lychd.ghouls.runs import reconcile_consents

    try:
        await reconcile_consents({}, engine=engine)
    except Exception:
        logger.exception("reconcile_consents_at_startup_failed")


async def _sync_preauths_at_startup(
    *,
    runes: RuneRegistry,
    settings: Settings,
) -> None:
    """Upsert preauthorizations from the process's existing Rune snapshot."""
    if settings.server.database.profile != "postgres":
        return
    try:
        from lychd.db.engine import get_session_factory
        from lychd.domain.codex.runes import CodexPreauthRune
        from lychd.domain.codex.services import PreauthService

        preauthorizations = list(runes.of(CodexPreauthRune))
        factory = get_session_factory()
        async with factory() as session:
            count = await PreauthService(session=session).sync_from_runes(
                preauthorizations,
            )
        logger.info("preauth_sync_at_startup", count=count)
    except Exception:
        logger.exception("preauth_sync_at_startup_failed")


async def _reconcile_at_startup(boot_cutoff: datetime) -> None:
    """Run the orphan-run reconcile once at startup (gated on the boot cutoff, F3).

    Must not block startup on a transient DB hiccup, but the old silent `suppress`
    hid real reconcile failures (F9/H2). Log loudly instead — the failure is
    visible, startup still proceeds.
    """
    from lychd.ghouls.runs import reconcile_runs

    try:
        await reconcile_runs({}, boot_cutoff=boot_cutoff)
    except Exception:
        logger.exception("reconcile_at_startup_failed")
