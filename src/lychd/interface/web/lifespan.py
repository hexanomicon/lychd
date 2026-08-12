"""`altar_services_lifespan` — the ONE web-layer assembly site (§TD-5).

Builds one queue-bound `AltarServices`, warms the registry off the event loop,
reconciles durable startup state, publishes its process `RunSubstrate` (Topology A:
the in-process ghoul shares this bus), stamps it on `app.state.services`, and drains
on shutdown.

This module is an application assembly root — importing `extensions.host` here is allowed.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import structlog

from lychd.domain.web.altar_services import build_altar_services
from lychd.system.services.queues import (
    ManagedRunQueue,
    connect_run_queues,
    disconnect_run_queues,
    protect_run_queues,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from litestar import Litestar

    from lychd.config.runes.registry import RuneRegistry
    from lychd.config.settings.root import Settings
    from lychd.domain.cortex.engine import RunQueue

logger = structlog.get_logger()

_RUN_QUEUE_NAMES = ("runs", "rites")
_STARTUP_RECONCILIATION_PAGE_SIZE = 128
_RELAY_RESTART_DELAY_S = 0.1
_RELAY_RESTART_MAX_DELAY_S = 5.0
_WORKER_SHUTDOWN_TIMEOUT_S = 30.0


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
    """Assemble, warm, reconcile, publish, and later drain the Altar services."""
    from lychd.config.settings.root import get_settings
    from lychd.extensions.host import get_extensions  # application assembly root only
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
    maintenance_stop = asyncio.Event()
    maintenance_tasks: list[asyncio.Task[None]] = []
    try:
        await wait_for_host_reactor_idle(settings.orchestration.switching)
        # Resolve and CONNECT every queue before constructing or publishing a
        # runtime handle. litestar-saq's in-process Worker starts detached and
        # does not connect its queue; relying on it produces a healthy-looking
        # app whose workers hot-loop on an unopened Postgres pool.
        queues = protect_run_queues(_collect_run_queues(app))
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
            portal_definitions=exts.portal_definitions,
            delegated_runtime_adapters=tuple(exts.delegated_runtime_adapters.values()),
            delegated_runtime_catalog=exts.delegated_runtime_catalog,
            settings=settings,
            systemctl_bin=systemctl_bin,
        )

        # Warm the registry off the event loop: runtime synthesis, Quadlet
        # transmutation, and initial probes are synchronous/bridged work. Rune
        # discovery already happened once in AppInit and cannot recur here.
        await asyncio.to_thread(services.registry.ensure_loaded)

        await _recover_durable_state(
            services=services,
            runes=runes,
            settings=settings,
            boot_cutoff=boot_cutoff,
        )

        from lychd.ghouls.runs import relay_consents, relay_delegated_runs, relay_run_deliveries

        maintenance_tasks.extend(
            (
                _start_delivery_relay(
                    relay_run_deliveries,
                    services.substrate,
                    maintenance_stop,
                ),
                _start_delegate_relay(
                    relay_delegated_runs,
                    services.run_engine,
                    maintenance_stop,
                ),
                _start_consent_relay(
                    relay_consents,
                    services.run_engine,
                    services.substrate,
                    maintenance_stop,
                ),
            )
        )

        # Publish only after required durable reconciliation succeeds. Workers
        # cannot claim work, and HTTP cannot resolve services, before this point.
        from lychd.domain.cortex.substrate import set_run_substrate

        set_run_substrate(services.substrate)

        # Publish the web-facing handle last: a partially warmed runtime is never
        # observable through app.state.
        app.state.services = services
        yield
    finally:
        from lychd.domain.cortex.substrate import reset_run_substrate

        maintenance_stop.set()
        relay_results = await asyncio.gather(
            *(_stop_delivery_relay(task) for task in maintenance_tasks),
            return_exceptions=True,
        )
        relay_errors = [result for result in relay_results if isinstance(result, BaseException)]
        if relay_errors:
            message = "Maintenance relays did not stop; shared dependencies remain live."
            raise BaseExceptionGroup(message, relay_errors)
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


async def _stop_in_process_workers(
    app: Litestar,
    *,
    timeout_s: float = _WORKER_SHUTDOWN_TIMEOUT_S,
) -> None:
    """Cancel and prove every Topology-A worker-owned task stopped."""
    workers = _in_process_workers(app)
    if not workers:
        return
    launchers, observed_worker_tasks, stop_tasks = _begin_worker_shutdown(workers)
    owned_tasks = {*launchers, *stop_tasks}
    done, pending = await asyncio.wait(owned_tasks, timeout=timeout_s)
    for task in pending:
        task.cancel()

    errors = _worker_shutdown_task_errors(
        done,
        pending,
        launchers=launchers,
        stop_tasks=stop_tasks,
        timeout_s=timeout_s,
    )
    errors.extend(_live_worker_task_errors(workers, observed_worker_tasks))
    if errors:
        message = "In-process workers did not stop; shared dependencies remain live."
        raise BaseExceptionGroup(message, errors)


def _in_process_workers(app: Litestar) -> list[Any]:
    """Resolve process-owned SAQ workers without requiring the plugin in focused apps."""
    from litestar_saq import SAQPlugin

    try:
        plugin = app.plugins.get(SAQPlugin)
    except (KeyError, LookupError):
        return []
    return [worker for worker in plugin.get_workers().values() if not worker.separate_process]


def _begin_worker_shutdown(
    workers: list[Any],
) -> tuple[
    dict[asyncio.Task[Any], Any],
    dict[int, set[asyncio.Task[Any]]],
    dict[asyncio.Task[Any], Any],
]:
    """Signal workers, fence their launcher tasks, and start explicit stops."""
    launchers: dict[asyncio.Task[Any], Any] = {}
    observed_worker_tasks: dict[int, set[asyncio.Task[Any]]] = {}
    for worker in workers:
        observed_worker_tasks[id(worker)] = set(getattr(worker, "tasks", ()))
        launcher = getattr(worker, "_saq_asyncio_tasks", None)
        if isinstance(launcher, asyncio.Task):
            launchers[launcher] = worker
            if not launcher.done():
                launcher.cancel()
        event = getattr(worker, "event", None)
        if event is not None:
            event.set()
    stop_tasks = {
        asyncio.create_task(worker.stop(), name=f"lychd-stop-saq-{worker.queue.name}"): worker for worker in workers
    }
    return launchers, observed_worker_tasks, stop_tasks


def _worker_shutdown_task_errors(
    done: set[asyncio.Task[Any]],
    pending: set[asyncio.Task[Any]],
    *,
    launchers: dict[asyncio.Task[Any], Any],
    stop_tasks: dict[asyncio.Task[Any], Any],
    timeout_s: float,
) -> list[BaseException]:
    """Translate owned-task outcomes into explicit teardown failures."""
    errors: list[BaseException] = []
    for task in done:
        worker = stop_tasks.get(task) or launchers.get(task)
        if worker is None:  # pragma: no cover - every task above has one owner
            continue
        if task.cancelled():
            if task in stop_tasks:
                errors.append(RuntimeError(f"SAQ worker {worker.queue.name!r} stop task was cancelled."))
            continue
        result_error = task.exception()
        if result_error is not None:
            errors.append(result_error)
            logger.error(
                "saq_worker_shutdown_failed",
                queue_name=worker.queue.name,
                error=str(result_error),
            )
    for task in pending:
        worker = stop_tasks.get(task) or launchers.get(task)
        queue_name = worker.queue.name if worker is not None else "unknown"
        errors.append(TimeoutError(f"SAQ worker {queue_name!r} did not stop within {timeout_s}s."))
    return errors


def _live_worker_task_errors(
    workers: list[Any],
    observed_worker_tasks: dict[int, set[asyncio.Task[Any]]],
) -> list[BaseException]:
    """Prove no task observed before or after stop remains alive."""
    errors: list[BaseException] = []
    for worker in workers:
        tasks = observed_worker_tasks[id(worker)] | set(getattr(worker, "tasks", ()))
        live_tasks = [task for task in tasks if not task.done()]
        if live_tasks:
            error = RuntimeError(f"SAQ worker {worker.queue.name!r} returned with {len(live_tasks)} live task(s).")
            errors.append(error)
            logger.error(
                "saq_worker_shutdown_incomplete",
                queue_name=worker.queue.name,
                live_tasks=len(live_tasks),
            )
    return errors


def _start_delivery_relay(
    relay: Any,
    substrate: Any,
    stop: asyncio.Event,
) -> asyncio.Task[None]:
    """Start the process-owned publisher after the startup flush succeeds."""
    return asyncio.create_task(
        _supervise_relay(
            "run-delivery",
            lambda: relay({"run_substrate": substrate}, stop=stop),
            stop,
        ),
        name="lychd-run-delivery-relay",
    )


def _start_delegate_relay(
    relay: Any,
    engine: Any,
    stop: asyncio.Event,
) -> asyncio.Task[None]:
    """Start bounded delegated-result polling after startup recovery."""
    return asyncio.create_task(
        _supervise_relay(
            "delegate",
            lambda: relay(engine=engine, stop=stop),
            stop,
        ),
        name="lychd-delegate-relay",
    )


def _start_consent_relay(
    relay: Any,
    engine: Any,
    substrate: Any,
    stop: asyncio.Event,
) -> asyncio.Task[None]:
    """Start bounded consent-result polling after startup recovery."""
    return asyncio.create_task(
        _supervise_relay(
            "consent",
            lambda: relay(engine=engine, substrate=substrate, stop=stop),
            stop,
        ),
        name="lychd-consent-relay",
    )


async def _supervise_relay(
    name: str,
    relay_factory: Callable[[], Awaitable[None]],
    stop: asyncio.Event,
    *,
    restart_delay_s: float = _RELAY_RESTART_DELAY_S,
    max_restart_delay_s: float = _RELAY_RESTART_MAX_DELAY_S,
) -> None:
    """Restart a process-owned relay with bounded backoff until shutdown."""
    restart_delay = restart_delay_s
    failures = 0
    while not stop.is_set():
        try:
            await relay_factory()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            failures += 1
            logger.exception(
                "maintenance_relay_failed",
                relay=name,
                error=str(exc),
                consecutive_failures=failures,
                restart_delay_s=restart_delay,
            )
        else:
            if stop.is_set():
                return
            failures += 1
            logger.error(
                "maintenance_relay_exited",
                relay=name,
                consecutive_failures=failures,
                restart_delay_s=restart_delay,
            )
        try:
            await asyncio.wait_for(stop.wait(), timeout=restart_delay)
        except TimeoutError:
            restart_delay = _next_relay_restart_delay(restart_delay, maximum=max_restart_delay_s)
            continue


def _next_relay_restart_delay(current: float, *, maximum: float) -> float:
    """Return deterministic capped exponential backoff for one failed relay."""
    if current <= 0:
        return 0
    return min(current * 2, maximum)


async def _stop_delivery_relay(task: asyncio.Task[None], *, timeout_s: float = 5.0) -> None:
    """Stop one relay or fail before its shared dependencies are dismantled."""
    task.cancel()
    done, _pending = await asyncio.wait({task}, timeout=timeout_s)
    if not done:
        logger.error("run_delivery_relay_shutdown_timed_out", timeout_s=timeout_s)
        msg = f"Maintenance relay did not stop within {timeout_s}s."
        raise TimeoutError(msg)
    try:
        task.result()
    except asyncio.CancelledError:
        return
    except Exception as exc:
        logger.exception("run_delivery_relay_shutdown_failed", error=str(exc))
        raise


async def _recover_durable_state(
    *,
    services: Any,
    runes: RuneRegistry,
    settings: Settings,
    boot_cutoff: datetime,
) -> None:
    """Reconcile every durable authority before workers or HTTP can observe it."""
    await _sync_preauths_at_startup(runes=runes, settings=settings)
    required = settings.server.database.profile == "postgres"
    await _reconcile_cancellations_at_startup(
        services.run_engine,
        required=required,
    )
    await _reconcile_terminal_checkpoints_at_startup(
        services.run_engine,
        required=required,
    )
    await _reconcile_at_startup(
        boot_cutoff,
        substrate=services.substrate,
        required=required,
    )
    await _reconcile_consents_at_startup(
        services.run_engine,
        substrate=services.substrate,
        required=required,
    )
    await _reconcile_delegates_at_startup(
        services.run_engine,
        required=required,
    )
    await _flush_deliveries_at_startup(
        substrate=services.substrate,
        required=required,
    )


async def _reconcile_cancellations_at_startup(
    engine: Any,
    *,
    required: bool,
) -> None:
    """Finish elected cancellations and repair missing terminal evidence."""
    from lychd.domain.cortex.runs import RunStatus

    try:
        for status, orphaned in (
            (RunStatus.CANCELLING, True),
            (RunStatus.CANCELLED, True),
        ):
            cursor: tuple[datetime, str] | None = None
            while True:
                runs = await engine.ledger.list_by_status(
                    status,
                    after=cursor,
                    limit=_STARTUP_RECONCILIATION_PAGE_SIZE,
                )
                for run in runs:
                    await engine.cancel(run.run_id, orphaned=orphaned)
                if len(runs) < _STARTUP_RECONCILIATION_PAGE_SIZE:
                    break
                cursor = (runs[-1].created_at, runs[-1].run_id)
    except Exception:
        logger.exception("reconcile_cancellations_at_startup_failed")
        if required:
            raise


async def _reconcile_terminal_checkpoints_at_startup(
    engine: Any,
    *,
    required: bool,
) -> None:
    """Idempotently remove checkpoints retained after terminal commit failures."""
    from lychd.domain.cortex.runs import TERMINAL_STATUSES

    try:
        for status in TERMINAL_STATUSES:
            cursor: tuple[datetime, str] | None = None
            while True:
                runs = await engine.ledger.list_by_status(
                    status,
                    after=cursor,
                    limit=_STARTUP_RECONCILIATION_PAGE_SIZE,
                )
                for run in runs:
                    await engine.ensure_terminal_evidence(run.run_id)
                    await engine.stasis_store.delete(run.run_id)
                if len(runs) < _STARTUP_RECONCILIATION_PAGE_SIZE:
                    break
                cursor = (runs[-1].created_at, runs[-1].run_id)
    except Exception:
        logger.exception("reconcile_terminal_checkpoints_at_startup_failed")
        if required:
            raise


async def _reconcile_consents_at_startup(
    engine: Any,
    *,
    substrate: Any,
    required: bool,
) -> None:
    """Re-fire decided-but-unenqueued consent verdicts before admission."""
    from lychd.ghouls.runs import reconcile_consents

    try:
        result = await reconcile_consents({"run_substrate": substrate}, engine=engine)
        _require_clean_reconciliation(result, label="Consent reconciliation")
    except Exception:
        logger.exception("reconcile_consents_at_startup_failed")
        if required:
            raise


async def _reconcile_delegates_at_startup(
    engine: Any,
    *,
    required: bool,
) -> None:
    """Refresh and re-admit durable delegated waits before admission."""
    from lychd.ghouls.runs import reconcile_delegated_runs

    try:
        result = await reconcile_delegated_runs(engine=engine)
        _require_clean_reconciliation(result, label="Delegate reconciliation")
    except Exception:
        logger.exception("reconcile_delegates_at_startup_failed")
        if required:
            raise


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
        raise


async def _reconcile_at_startup(
    boot_cutoff: datetime,
    *,
    substrate: Any,
    required: bool,
) -> None:
    """Run the orphan-run reconcile once at startup (gated on the boot cutoff, F3).

    PostgreSQL reconciliation is an admission prerequisite. The memory profile has
    no cross-process durability to recover, so its focused/local startup remains
    best-effort.
    """
    from lychd.ghouls.runs import reconcile_runs

    try:
        result = await reconcile_runs(
            {"run_substrate": substrate},
            boot_cutoff=boot_cutoff,
        )
        _require_clean_reconciliation(result, label="Run reconciliation")
    except Exception:
        logger.exception("reconcile_at_startup_failed")
        if required:
            raise


async def _flush_deliveries_at_startup(
    *,
    substrate: Any,
    required: bool,
) -> None:
    """Require one clean publication pass after wait-state recovery."""
    from lychd.ghouls.runs import flush_run_deliveries

    try:
        result = await flush_run_deliveries({"run_substrate": substrate})
        _require_clean_reconciliation(result, label="Run delivery flush")
    except Exception:
        logger.exception("flush_deliveries_at_startup_failed")
        if required:
            raise


def _require_clean_reconciliation(result: dict[str, Any], *, label: str) -> None:
    """Reject a degraded durable recovery pass before admission opens."""
    if result.get("status") == "reconciled":
        return
    msg = f"{label} is not clean ({result.get('probe_errors', 0)} probe errors)."
    raise RuntimeError(msg)
