"""Synthetic app for the real native launcher; no production service graph."""

from __future__ import annotations

import asyncio
import os
import resource
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Never

# Apply before importing the server/framework. These do not attest interpreter
# startup, aggregate process-tree limits or cgroup enforcement.
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
resource.setrlimit(resource.RLIMIT_FSIZE, (262144, 262144))

from litestar import Litestar, Request, get  # noqa: E402
from litestar.background_tasks import BackgroundTask  # noqa: E402
from litestar.response import Response  # noqa: E402

_CASE = os.environ["LYCHD_TEST_SERVER_CASE"]
_TOKEN = os.environ["LYCHD_TEST_SERVER_TOKEN"]
_PORT = int(os.environ["LYCHD_TEST_SERVER_PORT"])


@dataclass
class _Work:
    live: bool = False
    active: int = 0


_work = _Work()


def _event(message: str) -> None:
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


def _fail(message: str) -> Never:
    raise RuntimeError(message)


@asynccontextmanager
async def _lifespan(app: Litestar) -> AsyncGenerator[None]:
    _event("fixture-startup-enter")
    try:
        if _CASE == "startup-failure":
            _fail("synthetic-required-startup-failure")
        if _CASE == "warmup-stop":
            await asyncio.sleep(2)
        _work.live = True
        _event("fixture-startup-complete")
        yield
    finally:
        _event(f"fixture-close-enter:{_work.active}")
        if _work.active:
            _fail("synthetic-service-close-before-callback-retirement")
        _work.live = False
        if _CASE == "close-failure":
            _fail("synthetic-required-close-failure")
        _event("fixture-close-complete")


@get("/ready")
async def _ready() -> dict[str, str]:
    return {"marker": _TOKEN}


@get("/raw/{value:str}")
async def _raw(request: Request[Any, Any, Any], value: str) -> dict[str, str]:
    return {"marker": _TOKEN, "raw_path": request.scope["raw_path"].decode("ascii")}


@get("/hold")
async def _hold() -> dict[str, str]:
    _work.active += 1
    _event("fixture-request-enter")
    try:
        await asyncio.sleep(0.6)
        if not _work.live:
            _fail("synthetic-request-used-closed-service")
        _event("fixture-request-complete")
        return {"marker": _TOKEN}
    finally:
        _work.active -= 1
        _event("fixture-request-finally")


async def _tail() -> None:
    _work.active += 1
    _event("fixture-tail-enter")
    try:
        await asyncio.sleep(0.6)
        if not _work.live:
            _fail("synthetic-tail-used-closed-service")
        _event("fixture-tail-complete")
    finally:
        _work.active -= 1
        _event("fixture-tail-finally")


@get("/background")
async def _background() -> Response[dict[str, str]]:
    return Response(content={"marker": _TOKEN}, background=BackgroundTask(_tail))


def main() -> None:
    """Exercise the actual native grammar/runner with one explicit inert factory."""
    import lychd.app as application
    import lychd.config.settings.root as settings_module
    from lychd.__main__ import cli

    app = Litestar([_ready, _raw, _hold, _background], lifespan=[_lifespan])
    # The process mechanism is under test; personal Settings and the real
    # production service factory are deliberately outside this receipt.
    from lychd.config.settings.root import SettingsSnapshot

    settings = SettingsSnapshot(payload='{"server":{"database":{"profile":"memory"}}}').materialize()
    application.create_app = lambda: app
    settings_module.get_settings = lambda: settings
    cli.main(args=["serve", "--host", "127.0.0.1", "--port", str(_PORT)], prog_name="lychd")


if __name__ == "__main__":
    main()
