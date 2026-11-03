"""Real installed workers retire against inert transports before dependencies close."""

from __future__ import annotations

# White-box observations retain the existing launcher/worker compatibility checks.
# pyright: reportPrivateUsage=false
import asyncio
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from litestar import Litestar
from litestar.di import Provide
from litestar_saq import QueueConfig, SAQConfig, Worker
from saq.job import Job, Status
from saq.queue.base import Queue

from lychd.interface.web import lifespan
from lychd.system.services.queues import RuntimeQueuePlugin


class _InertQueue:
    """Only broker I/O is substituted; processing and shutdown use real workers."""

    def __init__(self, name: str, events: list[str], *, uncertain: bool = False) -> None:
        self.name = name
        self.events = events
        self.pending: asyncio.Queue[Job] = asyncio.Queue()
        self.finished = asyncio.Event()
        self.sweeping = asyncio.Event()
        self.release_sweep = asyncio.Event()
        self.uncertain = uncertain

    def job_id(self, key: str) -> str:
        return key

    async def connect(self) -> None:
        self.events.append(f"connect:{self.name}")

    async def disconnect(self) -> None:
        self.events.append(f"disconnect:{self.name}")

    async def dequeue(self, **_kwargs: Any) -> Job:
        return await self.pending.get()

    async def update(self, job: Job, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(job, key, value)

    async def finish(self, job: Job, status: Status, **kwargs: Any) -> None:
        job.status = status
        job.result = kwargs.get("result")
        self.finished.set()

    async def retry(self, _job: Job, _error: str | None) -> None:
        pytest.fail("A completed inert job must not retry during shutdown")

    async def schedule(self, _lock: int) -> list[str]:
        return []

    async def sweep(self, _lock: int) -> list[str]:
        self.sweeping.set()
        if self.uncertain:
            while not self.release_sweep.is_set():
                try:
                    await self.release_sweep.wait()
                except asyncio.CancelledError:
                    continue
        return []

    async def worker_info(self, _identity: str, **_kwargs: Any) -> dict[str, Any]:
        return {"queue_key": self.name, "stats": None, "metadata": None}

    async def jobs(self, _keys: Any) -> list[Job]:
        return []


def _forbid_manager_start(_manager: object) -> None:
    pytest.fail("Production workers must never start the unused heartbeat manager")


def _exception_tree(error: BaseException) -> Iterator[BaseException]:
    yield error
    if isinstance(error, BaseExceptionGroup):
        group = cast("BaseExceptionGroup[BaseException]", error)
        for child in group.exceptions:
            yield from _exception_tree(child)


@pytest.mark.parametrize(
    "patch",
    [
        {"web_enabled": True},
        {"use_server_lifespan": True},
        {"worker_processes": 2},
        {"queue_configs": [QueueConfig(broker_instance=object(), name="runs", tasks=[])]},
        {
            "queue_configs": [
                QueueConfig(broker_instance=object(), name="runs", tasks=[]),
                QueueConfig(broker_instance=object(), name="other", tasks=[]),
            ]
        },
        {"queue_instances": {}},
    ],
)
def test_runtime_profile_refuses_before_queue_construction(
    monkeypatch: pytest.MonkeyPatch, patch: dict[str, Any]
) -> None:
    config = SAQConfig(
        queue_configs=[
            QueueConfig(broker_instance=object(), name=name, tasks=[], separate_process=False)
            for name in ("runs", "rites")
        ]
    )
    for key, value in patch.items():
        setattr(config, key, value)
    monkeypatch.setattr(config, "get_queues", lambda: pytest.fail("Unsupported profile reached broker construction"))
    with pytest.raises(ValueError, match="fixed runs/rites"):
        RuntimeQueuePlugin(config)


def test_runtime_profile_refuses_separate_process_before_queue_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SAQConfig(
        queue_configs=[QueueConfig(broker_instance=object(), name=name, tasks=[]) for name in ("runs", "rites")]
    )
    monkeypatch.setattr(config, "get_queues", lambda: pytest.fail("Unsupported profile reached broker construction"))
    with pytest.raises(ValueError, match="fixed runs/rites"):
        RuntimeQueuePlugin(config)


@pytest.mark.asyncio
@pytest.mark.parametrize("disposition", ["success", "stop-failure", "uncertain-stop", "startup-failure"])
async def test_real_workers_drain_before_dependencies_or_preserve_them_on_uncertainty(  # noqa: C901, PLR0912, PLR0915 - real-worker lifecycle across shutdown and partial-startup dispositions
    monkeypatch: pytest.MonkeyPatch, disposition: str
) -> None:
    from litestar_saq.heartbeat import HeartbeatManager

    monkeypatch.setattr(HeartbeatManager, "start", _forbid_manager_start)
    events: list[str] = []
    started = {name: asyncio.Event() for name in ("runs", "rites")}
    processed = {name: asyncio.Event() for name in started}
    release_job = asyncio.Event()
    queues = {
        name: _InertQueue(name, events, uncertain=disposition == "uncertain-stop" and name == "runs")
        for name in started
    }

    async def execute(ctx: Any) -> str:
        name = ctx["worker"].queue.name
        assert "heartbeat_manager" not in ctx
        started[name].set()
        await release_job.wait()
        return "settled"

    async def startup(ctx: Any) -> None:
        events.append(f"startup:{ctx['worker'].queue.name}")

    async def before(ctx: Any) -> None:
        events.append(f"before:{ctx['worker'].queue.name}")

    async def after(ctx: Any) -> None:
        name = ctx["worker"].queue.name
        events.append(f"after:{name}")
        processed[name].set()

    async def shutdown(ctx: Any) -> None:
        name = ctx["worker"].queue.name
        events.append(f"shutdown:{name}")
        if disposition == "stop-failure" and name == "runs":
            message = "controlled shutdown failure"
            raise RuntimeError(message)

    config = SAQConfig(
        queue_configs=[
            QueueConfig(
                broker_instance=object(),
                name=name,
                tasks=[execute],
                separate_process=False,
                concurrency=1,
                startup=[startup],
                before_process=[before],
                after_process=[after],
                shutdown=[shutdown],
            )
            for name in queues
        ],
        queue_instances=cast("dict[str, Queue]", queues),
    )
    plugin = RuntimeQueuePlugin(config)
    workers = plugin.get_workers()
    assert plugin.get_workers() is workers
    assert all(type(worker) is Worker for worker in workers.values())
    assert all(worker.functions[execute.__qualname__] is execute for worker in workers.values())
    assert all(plugin.get_queue(name) is queue for name, queue in queues.items())
    app = Litestar(plugins=[plugin], lifespan=[lifespan.altar_services_lifespan])
    app.state.runes = object()
    assert app.plugins.get(RuntimeQueuePlugin) is plugin
    assert not app.plugins.cli  # Raw multi-process worker CLI registration is intentionally absent.
    provider = app.dependencies[config.queues_dependency_key]
    assert isinstance(provider, Provide)
    assert provider.dependency == config.provide_queues
    assert not app.on_shutdown
    if disposition != "startup-failure":
        for name, queue in queues.items():
            queue.pending.put_nowait(Job(function=execute.__qualname__, queue=cast("Queue", queue), key=f"{name}-job"))

    settings = SimpleNamespace(orchestration=SimpleNamespace(switching=SimpleNamespace(actuator="none")))
    services = SimpleNamespace(
        registry=SimpleNamespace(ensure_loaded=lambda: None, list_capabilities=list),
        substrate=SimpleNamespace(effects=None),
        run_engine=object(),
    )
    owned: set[asyncio.Task[Any]] = set()

    async def close_services() -> None:
        assert all(task.done() for task in owned)
        events.append("services")

    services.aclose = close_services
    monkeypatch.setattr("lychd.config.settings.root.get_settings", lambda: settings)
    extensions = SimpleNamespace(
        soulstone_registrations=(),
        portal_registrations=(),
        delegated_runtime_adapters={},
        delegated_runtime_catalog=(),
        observation_registrations=(),
        inspection_registrations=(),
    )
    monkeypatch.setattr("lychd.extensions.host.get_extensions", lambda: extensions)
    monkeypatch.setattr("lychd.system.services.runtime.wait_for_host_reactor_idle", AsyncMock())
    monkeypatch.setattr(lifespan, "_soft_activation_guard_at_startup", object)

    def build_services(**_kwargs: object) -> SimpleNamespace:
        return services

    def publish_substrate(_substrate: object) -> None:
        pass

    def start_relay(*args: object) -> asyncio.Task[bool]:
        stop = args[-1]
        assert isinstance(stop, asyncio.Event)
        return asyncio.create_task(stop.wait())

    monkeypatch.setattr(lifespan, "build_altar_services", build_services)
    monkeypatch.setattr(lifespan, "_recover_durable_state", AsyncMock())
    monkeypatch.setattr("lychd.domain.cortex.substrate.set_run_substrate", publish_substrate)
    monkeypatch.setattr("lychd.domain.cortex.substrate.reset_run_substrate", lambda: events.append("substrate"))
    for name in ("_start_delivery_relay", "_start_delegate_relay", "_start_consent_relay"):
        monkeypatch.setattr(lifespan, name, start_relay)
    if disposition == "uncertain-stop":
        real_stop = lifespan._stop_in_process_workers

        async def bounded_stop(application: Any) -> None:
            await real_stop(application, timeout_s=0.01)

        monkeypatch.setattr(lifespan, "_stop_in_process_workers", bounded_stop)

    if disposition == "startup-failure":

        async def fail_after_first_worker(application: Litestar) -> None:
            assert application is app
            async with asyncio.timeout(1):
                await queues["runs"].sweeping.wait()
            first = workers["runs"]
            owned.update(first.tasks)
            owned.add(first._saq_asyncio_tasks)
            assert not hasattr(workers["rites"], "_saq_asyncio_tasks")
            message = "controlled Litestar startup failure"
            raise RuntimeError(message)

        first_start = app.on_startup.index(workers["runs"].on_app_startup)
        app.on_startup.insert(first_start + 1, fail_after_first_worker)

    async def exercise() -> None:
        async with app.lifespan():
            assert disposition != "startup-failure"
            async with asyncio.timeout(1):
                await asyncio.gather(*(event.wait() for event in started.values()))
                await asyncio.gather(*(queue.sweeping.wait() for queue in queues.values()))
                release_job.set()
                await asyncio.gather(*(event.wait() for event in processed.values()))
            for worker in workers.values():
                owned.update(worker.tasks)
                owned.add(worker._saq_asyncio_tasks)  # Existing compatibility handle, observed only.

    try:
        if disposition == "success":
            await exercise()
            assert all(task.done() for task in owned)
            assert events[-4:] == ["substrate", "services", "disconnect:rites", "disconnect:runs"]
            assert events.count("shutdown:runs") == events.count("shutdown:rites") == 1
            before_late_stop = set(asyncio.all_tasks())
            await asyncio.gather(*(worker.stop() for worker in workers.values()))
            assert set(asyncio.all_tasks()) == before_late_stop
        elif disposition == "startup-failure":
            with pytest.raises((RuntimeError, BaseExceptionGroup)) as raised:
                await exercise()
            assert any(
                type(error) is RuntimeError and str(error) == "controlled Litestar startup failure"
                for error in _exception_tree(raised.value)
            )
            assert owned
            assert all(task.done() for task in owned)
            assert "startup:runs" in events
            assert "startup:rites" not in events
            assert events[-4:] == ["substrate", "services", "disconnect:rites", "disconnect:runs"]
            assert not any(queue.finished.is_set() for queue in queues.values())
        else:
            with pytest.raises(BaseExceptionGroup) as raised:
                await exercise()
            nested = list(_exception_tree(raised.value))
            assert any(
                isinstance(error, BaseExceptionGroup)
                and error.message == "In-process workers did not stop; shared dependencies remain live."
                for error in nested
            )
            if disposition == "stop-failure":
                assert any(
                    type(error) is RuntimeError and str(error) == "controlled shutdown failure" for error in nested
                )
            else:
                assert any(isinstance(error, TimeoutError) for error in nested)
                assert any(not task.done() for task in owned)
            assert "services" not in events
            assert "substrate" not in events
            assert not any(event.startswith("disconnect:") for event in events)
        if disposition != "startup-failure":
            assert all(queue.finished.is_set() for queue in queues.values())
            for name in queues:
                assert all(f"{stage}:{name}" in events for stage in ("startup", "before", "after"))
    finally:
        release_job.set()
        for queue in queues.values():
            queue.release_sweep.set()
        # Let released resistant upkeep return to its ordinary poll sleep before cancellation.
        await asyncio.sleep(0)
        for task in owned:
            if not task.done():
                task.cancel()
        await asyncio.gather(*owned, return_exceptions=True)
        await asyncio.gather(*(worker.stop() for worker in workers.values()), return_exceptions=True)


@pytest.mark.asyncio
async def test_runtime_workers_keep_selected_shared_telemetry_tracer(monkeypatch: pytest.MonkeyPatch) -> None:
    from litestar_saq import instrumentation

    selected = object()
    requested: list[str] = []

    def get_tracer(name: str) -> object:
        requested.append(name)
        return selected

    queues = {name: _InertQueue(name, []) for name in ("runs", "rites")}
    config = SAQConfig(
        queue_configs=[
            QueueConfig(broker_instance=object(), name=name, tasks=[], separate_process=False) for name in queues
        ],
        queue_instances=cast("dict[str, Queue]", queues),
        otel_tracer_name="runtime-worker-profile",
    )
    monkeypatch.setattr(config, "should_enable_otel", lambda: True)
    monkeypatch.setattr(instrumentation, "get_tracer", get_tracer)
    workers = RuntimeQueuePlugin(config).get_workers()
    try:
        assert requested == ["runtime-worker-profile"]
        assert all(
            cast("object | None", getattr(worker, "_otel_tracer")) is selected  # noqa: B009 - opaque dependency field
            for worker in workers.values()
        )
    finally:
        await asyncio.gather(*(worker.stop() for worker in workers.values()))


def test_production_assembly_pairs_runtime_workers_with_the_required_altar_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import advanced_alchemy.extensions.litestar as database_plugins
    from litestar.config.app import AppConfig

    from lychd import app as application
    from lychd.config import components
    from lychd.config.runes import registry as runes

    settings, extensions, rune_registry, database_plugin = object(), object(), object(), object()
    config = SAQConfig(
        queue_configs=[
            QueueConfig(broker_instance=object(), name=name, tasks=[], separate_process=False)
            for name in ("runs", "rites")
        ]
    )
    monkeypatch.setattr(application, "get_settings", lambda: settings)
    monkeypatch.setattr("lychd.extensions.host.get_extensions", lambda: extensions)

    def load_runes(_extensions: object) -> object:
        return rune_registry

    def build_database(_settings: object) -> object:
        return object()

    def build_queues(_settings: object) -> SAQConfig:
        return config

    def build_database_plugin(**_kwargs: object) -> object:
        return database_plugin

    monkeypatch.setattr(runes, "load_rune_registry", load_runes)
    monkeypatch.setattr(components, "build_db_config", build_database)
    monkeypatch.setattr(components, "build_saq_config", build_queues)
    monkeypatch.setattr(database_plugins, "SQLAlchemyPlugin", build_database_plugin)
    app_config = AppConfig(route_handlers=[])

    assembled = application.AppInit()._configure_composition(app_config)

    assert assembled == (settings, extensions, rune_registry)
    assert app_config.plugins[0] is database_plugin
    assert isinstance(app_config.plugins[1], RuntimeQueuePlugin)
    registered_lifespans = cast(
        "list[object]",
        getattr(app_config, "lifespan"),  # noqa: B009 - framework uses unspecialized context manager types
    )
    assert registered_lifespans == [lifespan.altar_services_lifespan]
