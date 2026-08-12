from __future__ import annotations

# White-box shutdown-order tests exercise the narrow lifespan helper directly.
# pyright: reportPrivateUsage=false
import asyncio
from contextlib import asynccontextmanager
from functools import partial
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import ANY, AsyncMock, Mock

import pytest

from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import Settings
from lychd.domain.codex.runes import CodexPreauthRune
from lychd.interface.web.lifespan import (
    _next_relay_restart_delay,
    _reconcile_cancellations_at_startup,
    _reconcile_terminal_checkpoints_at_startup,
    _stop_delivery_relay,
    _stop_in_process_workers,
    _supervise_relay,
    _sync_preauths_at_startup,
    altar_services_lifespan,
)
from lychd.system.services.queues import connect_run_queues, disconnect_run_queues

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pytest_mock import MockerFixture


class _Queue:
    def __init__(
        self,
        name: str,
        events: list[str],
        *,
        fail_connect: bool = False,
        fail_disconnect: bool = False,
        cancel_disconnect: bool = False,
    ) -> None:
        self.name = name
        self._events = events
        self._fail_connect = fail_connect
        self._fail_disconnect = fail_disconnect
        self._cancel_disconnect = cancel_disconnect

    async def connect(self) -> None:
        self._events.append(f"connect:{self.name}")
        if self._fail_connect:
            msg = "broker unavailable"
            raise RuntimeError(msg)

    async def disconnect(self) -> None:
        self._events.append(f"disconnect:{self.name}")
        if self._cancel_disconnect:
            raise asyncio.CancelledError
        if self._fail_disconnect:
            msg = "disconnect unavailable"
            raise RuntimeError(msg)


def _record_event(events: list[str], event: str) -> None:
    events.append(event)


def _app_with_worker_plugin(plugin: object) -> SimpleNamespace:
    def get_plugin(_kind: object) -> object:
        return plugin

    return SimpleNamespace(plugins=SimpleNamespace(get=get_plugin))


async def _record_event_after_call(events: list[str], event: str, _value: object) -> None:
    events.append(event)


def _inject_reconciliation_failure(
    failure_stage: str,
    *,
    reconcile_runs: AsyncMock,
    reconcile_consents: AsyncMock,
    delegates: SimpleNamespace,
) -> str:
    """Fail one startup reconciliation stage and return its public error text."""
    failure = RuntimeError(f"{failure_stage} reconciliation failed")
    if failure_stage == "runs":
        reconcile_runs.side_effect = failure
    elif failure_stage == "consents":
        reconcile_consents.side_effect = failure
    else:
        delegates.refresh.side_effect = failure
    return "Delegate reconciliation is not clean" if failure_stage == "delegation" else str(failure)


@pytest.mark.asyncio
async def test_delivery_relay_shutdown_is_bounded_when_task_ignores_cancel() -> None:
    release = asyncio.Event()

    async def stubborn() -> None:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            await release.wait()

    task = asyncio.create_task(stubborn())
    await asyncio.sleep(0)

    with pytest.raises(TimeoutError, match="did not stop"):
        await _stop_delivery_relay(task, timeout_s=0.001)

    assert not task.done()
    release.set()
    await task


@pytest.mark.asyncio
@pytest.mark.parametrize("first_exit", ["return", "raise"])
async def test_relay_supervisor_restarts_unexpected_exit_until_shutdown(first_exit: str) -> None:
    stop = asyncio.Event()
    restarted = asyncio.Event()
    attempts = 0

    async def relay() -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            if first_exit == "raise":
                msg = "relay failed"
                raise RuntimeError(msg)
            return
        restarted.set()
        await stop.wait()

    task = asyncio.create_task(
        _supervise_relay("test", relay, stop, restart_delay_s=0),
    )
    await asyncio.wait_for(restarted.wait(), timeout=1)
    stop.set()
    await task

    assert attempts == 2


def test_relay_restart_backoff_is_exponential_and_capped() -> None:
    delay = 0.1
    observed: list[float] = []

    for _ in range(8):
        observed.append(delay)
        delay = _next_relay_restart_delay(delay, maximum=5.0)

    assert observed == [0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 5.0, 5.0]
    assert _next_relay_restart_delay(0, maximum=5.0) == 0


@pytest.mark.asyncio
async def test_queue_lifecycle_is_explicit_and_reverse_ordered() -> None:
    events: list[str] = []
    queues = {"runs": _Queue("runs", events), "rites": _Queue("rites", events)}

    connected = await connect_run_queues(queues)
    await disconnect_run_queues(connected)

    assert events == ["connect:runs", "connect:rites", "disconnect:rites", "disconnect:runs"]


@pytest.mark.asyncio
async def test_queue_connect_failure_rolls_back_connected_prefix() -> None:
    events: list[str] = []
    queues = {
        "runs": _Queue("runs", events),
        "rites": _Queue("rites", events, fail_connect=True),
    }

    with pytest.raises(RuntimeError, match="broker unavailable"):
        await connect_run_queues(queues)

    assert events == ["connect:runs", "connect:rites", "disconnect:rites", "disconnect:runs"]


@pytest.mark.asyncio
async def test_queue_disconnect_attempts_every_queue_then_reports_failure() -> None:
    events: list[str] = []
    queues = (
        _Queue("runs", events),
        _Queue("rites", events, fail_disconnect=True),
    )

    with pytest.raises(ExceptionGroup, match="failed to disconnect"):
        await disconnect_run_queues(queues)

    assert events == ["disconnect:rites", "disconnect:runs"]


@pytest.mark.asyncio
async def test_queue_disconnect_defers_cancellation_until_every_queue_is_attempted() -> None:
    events: list[str] = []
    queues = (
        _Queue("runs", events),
        _Queue("rites", events, cancel_disconnect=True),
    )

    with pytest.raises(asyncio.CancelledError):
        await disconnect_run_queues(queues)

    assert events == ["disconnect:rites", "disconnect:runs"]


@pytest.mark.asyncio
async def test_queue_disconnect_finishes_current_teardown_before_propagating_cancellation() -> None:
    events: list[str] = []
    started = asyncio.Event()
    release = asyncio.Event()

    class SlowQueue(_Queue):
        async def disconnect(self) -> None:
            events.append(f"disconnect-start:{self.name}")
            started.set()
            await release.wait()
            events.append(f"disconnect-done:{self.name}")

    runs = _Queue("runs", events)
    rites = SlowQueue("rites", events)
    teardown = asyncio.create_task(disconnect_run_queues((runs, rites)))
    await started.wait()

    teardown.cancel()
    await asyncio.sleep(0)
    assert not teardown.done()
    teardown.cancel()
    await asyncio.sleep(0)
    assert not teardown.done()

    release.set()
    with pytest.raises(asyncio.CancelledError):
        await teardown

    assert events == [
        "disconnect-start:rites",
        "disconnect-done:rites",
        "disconnect:runs",
    ]


@pytest.mark.asyncio
async def test_topology_a_workers_stop_before_shared_services_are_closed() -> None:
    in_process = SimpleNamespace(
        separate_process=False,
        stop=AsyncMock(),
        queue=SimpleNamespace(name="runs"),
    )
    external = SimpleNamespace(
        separate_process=True,
        stop=AsyncMock(),
        queue=SimpleNamespace(name="external"),
    )
    plugin = SimpleNamespace(get_workers=lambda: {"runs": in_process, "external": external})

    def plugin_get(_kind: type[object]) -> object:
        return plugin

    app = SimpleNamespace(plugins=SimpleNamespace(get=plugin_get))

    await _stop_in_process_workers(app)  # type: ignore[arg-type]

    in_process.stop.assert_awaited_once()
    external.stop.assert_not_awaited()


@pytest.mark.asyncio
async def test_worker_launcher_is_cancelled_and_awaited_before_teardown() -> None:
    launcher_stopped = asyncio.Event()

    async def launch() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            launcher_stopped.set()

    launcher = asyncio.create_task(launch())
    await asyncio.sleep(0)
    worker = SimpleNamespace(
        separate_process=False,
        stop=AsyncMock(),
        event=asyncio.Event(),
        tasks=set(),
        queue=SimpleNamespace(name="runs"),
        _saq_asyncio_tasks=launcher,
    )
    plugin = SimpleNamespace(get_workers=lambda: {"runs": worker})
    app = _app_with_worker_plugin(plugin)

    await _stop_in_process_workers(app)  # type: ignore[arg-type]

    assert launcher.done()
    assert launcher_stopped.is_set()


@pytest.mark.asyncio
async def test_worker_stop_has_an_outer_deadline() -> None:
    async def never_stop() -> None:
        await asyncio.Event().wait()

    worker = SimpleNamespace(
        separate_process=False,
        stop=never_stop,
        event=asyncio.Event(),
        tasks=set(),
        queue=SimpleNamespace(name="runs"),
    )
    plugin = SimpleNamespace(get_workers=lambda: {"runs": worker})
    app = _app_with_worker_plugin(plugin)

    with pytest.raises(BaseExceptionGroup, match="shared dependencies remain live") as exc_info:
        await _stop_in_process_workers(app, timeout_s=0.001)  # type: ignore[arg-type]

    assert any(isinstance(exc, TimeoutError) for exc in exc_info.value.exceptions)
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_worker_stop_failure_is_not_treated_as_safe_to_teardown() -> None:
    in_process = SimpleNamespace(
        separate_process=False,
        stop=AsyncMock(side_effect=RuntimeError("worker still running")),
        queue=SimpleNamespace(name="runs"),
    )
    plugin = SimpleNamespace(get_workers=lambda: {"runs": in_process})
    app = _app_with_worker_plugin(plugin)

    with pytest.raises(BaseExceptionGroup, match="shared dependencies remain live"):
        await _stop_in_process_workers(app)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_worker_stop_return_with_live_task_is_not_safe_to_teardown() -> None:
    release = asyncio.Event()

    async def stubborn() -> None:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            await release.wait()

    task = asyncio.create_task(stubborn())
    await asyncio.sleep(0)

    async def incomplete_stop() -> None:
        task.cancel()
        await asyncio.sleep(0)

    worker = SimpleNamespace(
        separate_process=False,
        stop=incomplete_stop,
        event=asyncio.Event(),
        tasks={task},
        queue=SimpleNamespace(name="runs"),
    )
    plugin = SimpleNamespace(get_workers=lambda: {"runs": worker})
    app = _app_with_worker_plugin(plugin)

    with pytest.raises(BaseExceptionGroup, match="shared dependencies remain live"):
        await _stop_in_process_workers(app)  # type: ignore[arg-type]

    assert not task.done()
    release.set()
    await task


@pytest.mark.asyncio
async def test_worker_stop_is_optional_for_focused_apps_without_saq() -> None:
    def missing(_kind: type[object]) -> object:
        raise KeyError

    app = SimpleNamespace(plugins=SimpleNamespace(get=missing))

    await _stop_in_process_workers(app)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_terminal_checkpoint_reconciliation_retries_every_terminal_status() -> None:
    from lychd.domain.cortex.runs import TERMINAL_STATUSES, RunStatus

    runs_by_status = {status: [SimpleNamespace(run_id=f"run-{status.value}")] for status in TERMINAL_STATUSES}

    async def list_by_status(status: RunStatus, **_kwargs: object) -> list[SimpleNamespace]:
        return runs_by_status[status]

    stasis = SimpleNamespace(delete=AsyncMock())
    ensure_terminal_evidence = AsyncMock()
    engine = SimpleNamespace(
        ledger=SimpleNamespace(list_by_status=list_by_status),
        stasis_store=stasis,
        ensure_terminal_evidence=ensure_terminal_evidence,
    )

    await _reconcile_terminal_checkpoints_at_startup(engine, required=True)

    assert {call.args[0] for call in stasis.delete.await_args_list} == {
        f"run-{status.value}" for status in TERMINAL_STATUSES
    }
    assert {call.args[0] for call in ensure_terminal_evidence.await_args_list} == {
        f"run-{status.value}" for status in TERMINAL_STATUSES
    }


@pytest.mark.asyncio
async def test_cancellation_reconciliation_pages_both_statuses(mocker: MockerFixture) -> None:
    from datetime import UTC, datetime, timedelta

    from lychd.domain.cortex.runs import RunStatus

    mocker.patch("lychd.interface.web.lifespan._STARTUP_RECONCILIATION_PAGE_SIZE", 2)
    now = datetime.now(UTC)
    runs_by_status = {
        status: [
            SimpleNamespace(run_id=f"{status.value}-{index}", created_at=now + timedelta(seconds=index))
            for index in range(3)
        ]
        for status in (RunStatus.CANCELLING, RunStatus.CANCELLED)
    }

    async def list_by_status(
        status: RunStatus,
        *,
        after: tuple[datetime, str] | None,
        limit: int,
    ) -> list[SimpleNamespace]:
        rows = runs_by_status[status]
        if after is not None:
            rows = [row for row in rows if (row.created_at, row.run_id) > after]
        return rows[:limit]

    engine = SimpleNamespace(
        ledger=SimpleNamespace(list_by_status=list_by_status),
        cancel=AsyncMock(),
    )

    await _reconcile_cancellations_at_startup(engine, required=True)

    assert engine.cancel.await_count == 6
    assert engine.cancel.await_args_list[0].kwargs == {"orphaned": True}
    assert engine.cancel.await_args_list[-1].kwargs == {"orphaned": True}


@pytest.mark.parametrize("failure_stage", ["runs", "consents", "delegation"])
@pytest.mark.asyncio
async def test_postgres_reconciliation_failure_blocks_publication_and_cleans_up(
    mocker: MockerFixture,
    failure_stage: str,
) -> None:
    cleanup_events: list[str] = []
    settings = SimpleNamespace(
        server=SimpleNamespace(database=SimpleNamespace(profile="postgres")),
        orchestration=SimpleNamespace(
            switching=SimpleNamespace(actuator="none"),
        ),
    )
    app = SimpleNamespace(
        state=SimpleNamespace(runes=object()),
        plugins=object(),
    )
    delegates = SimpleNamespace(refresh=AsyncMock())
    ledger = SimpleNamespace(
        list_by_status=AsyncMock(
            return_value=[SimpleNamespace(run_id="delegate-run", delegated_job_id="delegate-job")],
        ),
    )
    run_engine = SimpleNamespace(
        delegates=delegates,
        ledger=ledger,
        resume_delegate=AsyncMock(),
    )
    services = SimpleNamespace(
        registry=SimpleNamespace(ensure_loaded=Mock()),
        substrate=object(),
        run_engine=run_engine,
        aclose=AsyncMock(side_effect=lambda: cleanup_events.append("services")),
    )
    extensions = SimpleNamespace(
        runtime_adapters=(),
        portal_definitions=(),
        delegated_runtime_adapters={},
        delegated_runtime_catalog=(),
    )
    queues = {"runs": object(), "rites": object()}
    connected_queues = tuple(queues.values())

    mocker.patch("lychd.config.settings.root.get_settings", return_value=settings)
    mocker.patch("lychd.extensions.host.get_extensions", return_value=extensions)
    mocker.patch(
        "lychd.system.services.runtime.wait_for_host_reactor_idle",
        new=AsyncMock(),
    )
    mocker.patch(
        "lychd.interface.web.lifespan._collect_run_queues",
        return_value=queues,
    )
    mocker.patch(
        "lychd.interface.web.lifespan.connect_run_queues",
        new=AsyncMock(return_value=connected_queues),
    )
    mocker.patch(
        "lychd.interface.web.lifespan.build_altar_services",
        return_value=services,
    )
    mocker.patch(
        "lychd.interface.web.lifespan.asyncio.to_thread",
        new=AsyncMock(),
    )
    mocker.patch(
        "lychd.interface.web.lifespan._sync_preauths_at_startup",
        new=AsyncMock(),
    )
    mocker.patch(
        "lychd.interface.web.lifespan._reconcile_cancellations_at_startup",
        new=AsyncMock(),
    )
    mocker.patch(
        "lychd.interface.web.lifespan._reconcile_terminal_checkpoints_at_startup",
        new=AsyncMock(),
    )

    reconcile_runs = AsyncMock(
        return_value={"status": "reconciled", "count": 0, "probe_errors": 0},
    )
    reconcile_consents = AsyncMock(
        return_value={"status": "reconciled", "count": 0, "probe_errors": 0},
    )
    mocker.patch("lychd.ghouls.runs.reconcile_runs", new=reconcile_runs)
    mocker.patch("lychd.ghouls.runs.reconcile_consents", new=reconcile_consents)
    expected_failure = _inject_reconciliation_failure(
        failure_stage,
        reconcile_runs=reconcile_runs,
        reconcile_consents=reconcile_consents,
        delegates=delegates,
    )

    publish_substrate = mocker.patch(
        "lychd.domain.cortex.substrate.set_run_substrate",
    )

    mocker.patch(
        "lychd.domain.cortex.substrate.reset_run_substrate",
        new=Mock(side_effect=partial(_record_event, cleanup_events, "substrate")),
    )
    stop_workers = AsyncMock(
        side_effect=partial(_record_event_after_call, cleanup_events, "workers"),
    )
    mocker.patch(
        "lychd.interface.web.lifespan._stop_in_process_workers",
        new=stop_workers,
    )
    disconnect_queues = AsyncMock(
        side_effect=partial(_record_event_after_call, cleanup_events, "queues"),
    )
    mocker.patch(
        "lychd.interface.web.lifespan.disconnect_run_queues",
        new=disconnect_queues,
    )

    admission_opened = False
    with pytest.raises(RuntimeError, match=expected_failure):
        async with altar_services_lifespan(app):  # type: ignore[arg-type]
            admission_opened = True

    assert not admission_opened
    assert not hasattr(app.state, "services")
    publish_substrate.assert_not_called()
    reconcile_runs.assert_awaited_once_with(
        {"run_substrate": services.substrate},
        boot_cutoff=ANY,
    )
    if failure_stage != "runs":
        reconcile_consents.assert_awaited_once_with(
            {"run_substrate": services.substrate},
            engine=run_engine,
        )
    stop_workers.assert_awaited_once_with(app)
    services.aclose.assert_awaited_once()
    disconnect_queues.assert_awaited_once_with(connected_queues)
    assert cleanup_events == ["workers", "substrate", "services", "queues"]


@pytest.mark.asyncio
async def test_preauth_sync_reuses_the_app_rune_snapshot(
    mocker: MockerFixture,
) -> None:
    """Web startup cannot discover a second Rune generation for preauth."""
    settings = Settings()
    preauth = CodexPreauthRune(
        slug="existing-snapshot",
        tool_pattern="request_coven_swap",
    )
    runes = RuneRegistry((preauth,))
    rediscovery = mocker.patch(
        "lychd.config.runes.registry.load_rune_registry",
        side_effect=AssertionError("Rune discovery must not recur"),
    )
    session = object()

    @asynccontextmanager
    async def session_factory() -> AsyncIterator[object]:
        yield session

    mocker.patch(
        "lychd.db.engine.get_session_factory",
        return_value=session_factory,
    )
    service = mocker.patch("lychd.domain.codex.services.PreauthService")
    service.return_value.sync_from_runes = AsyncMock(return_value=1)

    await _sync_preauths_at_startup(
        runes=runes,
        settings=settings,
    )

    rediscovery.assert_not_called()
    service.assert_called_once_with(session=session)
    service.return_value.sync_from_runes.assert_awaited_once_with([preauth])


@pytest.mark.asyncio
async def test_preauth_sync_failure_blocks_postgres_startup(
    mocker: MockerFixture,
) -> None:
    settings = Settings()
    runes = RuneRegistry(())
    failure = RuntimeError("projection unavailable")
    mocker.patch(
        "lychd.db.engine.get_session_factory",
        side_effect=failure,
    )
    startup_logger = mocker.patch("lychd.interface.web.lifespan.logger")

    with pytest.raises(RuntimeError, match="projection unavailable"):
        await _sync_preauths_at_startup(
            runes=runes,
            settings=settings,
        )

    startup_logger.exception.assert_called_once_with("preauth_sync_at_startup_failed")
