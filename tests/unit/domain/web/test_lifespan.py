from __future__ import annotations

# White-box shutdown-order tests exercise the narrow lifespan helper directly.
# pyright: reportPrivateUsage=false
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from lychd.interface.web.lifespan import _stop_in_process_workers
from lychd.system.services.queues import connect_run_queues, disconnect_run_queues


class _Queue:
    def __init__(self, name: str, events: list[str], *, fail_connect: bool = False) -> None:
        self.name = name
        self._events = events
        self._fail_connect = fail_connect

    async def connect(self) -> None:
        self._events.append(f"connect:{self.name}")
        if self._fail_connect:
            msg = "broker unavailable"
            raise RuntimeError(msg)

    async def disconnect(self) -> None:
        self._events.append(f"disconnect:{self.name}")


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

    assert events == ["connect:runs", "connect:rites", "disconnect:runs"]


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
async def test_worker_stop_is_optional_for_focused_apps_without_saq() -> None:
    def missing(_kind: type[object]) -> object:
        raise KeyError

    app = SimpleNamespace(plugins=SimpleNamespace(get=missing))

    await _stop_in_process_workers(app)  # type: ignore[arg-type]
