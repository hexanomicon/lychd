"""Explicit inert factory substitution for the generated native systemd proof.

The installation shim forwards the compiler's unchanged arguments to the real
Click command. Only Settings and the production application factory are replaced.
No database, queue, Podman, Rune, model, or operator configuration is loaded.
"""

from __future__ import annotations

import json
import os
import resource
import stat
import sys
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from litestar import Litestar


def _event(path: Path, event: str) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"event": event, "monotonic_ns": time.monotonic_ns(), "pid": os.getpid()}) + "\n")


def _load(config_path: Path) -> tuple[dict[str, Any], str, Path]:
    config = cast("dict[str, Any]", json.loads(config_path.read_text(encoding="utf-8")))
    assert set(config) == {"case", "token", "port", "credential_path", "events_path"}
    assert config["case"] in {"close-failure", "clean"}
    expected_args = ["serve", "--host", "127.0.0.1", "--port", str(config["port"])]
    assert sys.argv[1:] == expected_args
    # The real CLI's intentional dotenv load must see only this private fixture.
    os.chdir(config_path.parent)
    credential_path = Path(config["credential_path"])
    metadata = credential_path.lstat()
    assert stat.S_ISREG(metadata.st_mode)
    assert stat.S_IMODE(metadata.st_mode) == 0o600
    assert metadata.st_uid == os.getuid()
    password = credential_path.read_text(encoding="ascii")
    events = Path(config["events_path"])
    _event(events, "fixture-cli-argv-accepted")
    return config, password, events


def main(config_path: Path) -> None:
    """Enter the owned native CLI with one fresh, file-referenced credential."""
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_FSIZE, (262144, 262144))
    config, password, events = _load(config_path)

    from litestar import Litestar, get
    from litestar.datastructures import State

    import lychd.app as application
    import lychd.config.settings.root as settings_module
    from lychd.__main__ import cli
    from lychd.config.settings.root import SettingsSnapshot
    from lychd.domain.codex.local_access import LocalOperatorAccess
    from lychd.interface.api.lifecycle import StopAdmissionState, stop_admission
    from lychd.system.operator.admission import StopAdmissionProtocol

    access = LocalOperatorAccess(access_password=password)
    authentication = access.authenticate(username=b"magus", password=password.encode("ascii"))
    assert authentication is not None
    admission = StopAdmissionState(
        protocol=StopAdmissionProtocol(password),
        access=access,
        authentication=authentication,
        production=True,
    )

    @asynccontextmanager
    async def lifespan(app: Litestar) -> AsyncGenerator[None]:
        access.bind_control_loop()
        _event(events, "fixture-startup-enter")
        try:
            admission.publish()
            _event(events, "fixture-startup-complete")
            yield
        finally:
            # Retirement in the owned runner must already have withdrawn this.
            _event(events, "fixture-close-enter")
            assert not admission.published
            assert admission.launcher_profile is None
            if config["case"] == "close-failure":
                _event(events, "fixture-required-close-failure")
                message = "synthetic-required-close-failure"
                raise RuntimeError(message)
            _event(events, "fixture-close-complete")

    @get("/ready")
    async def ready() -> dict[str, str]:
        return {"marker": config["token"]}

    app = Litestar([ready, stop_admission], lifespan=[lifespan], state=State({"stop_admission": admission}))
    settings = SettingsSnapshot(payload='{"server":{"database":{"profile":"memory"}}}').materialize()
    application.create_app = lambda: app
    settings_module.get_settings = lambda: settings
    # The fixture deliberately never arms admission: the native launcher owns it.
    cli.main(args=sys.argv[1:], prog_name="lychd")


if __name__ == "__main__":
    main(Path(globals()["CONFIG_PATH"]))
