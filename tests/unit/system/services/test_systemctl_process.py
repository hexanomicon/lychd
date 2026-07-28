from __future__ import annotations

# These focused process-lifecycle tests intentionally exercise narrow private seams.
# pyright: reportPrivateUsage=false
import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from lychd.domain.orchestration.actuator import RuntimePreconditionError
from lychd.system.services.runtime_topology import RuntimeTopologyAttestor
from lychd.system.services.systemctl_process import (
    SystemctlClientTimeoutError,
    wait_systemctl_client,
)

if TYPE_CHECKING:
    from asyncio.subprocess import Process

    from pytest_mock import MockerFixture


class _HangingSystemctlProcess:
    """Process fake that can ignore TERM to exercise the bounded KILL fallback."""

    def __init__(self, *, ignore_terminate: bool = False) -> None:
        self.returncode: int | None = None
        self.terminate_calls = 0
        self.kill_calls = 0
        self._ignore_terminate = ignore_terminate
        self._exited = asyncio.Event()

    async def wait(self) -> int:
        await self._exited.wait()
        assert self.returncode is not None
        return self.returncode

    async def communicate(self) -> tuple[bytes, bytes]:
        await self._exited.wait()
        return b"", b""

    def terminate(self) -> None:
        self.terminate_calls += 1
        if not self._ignore_terminate:
            self.returncode = -15
            self._exited.set()

    def kill(self) -> None:
        self.kill_calls += 1
        self.returncode = -9
        self._exited.set()


@pytest.mark.asyncio
async def test_timeout_escalates_to_kill_and_reaps_the_client(mocker: MockerFixture) -> None:
    mocker.patch(
        "lychd.system.services.systemctl_process._TERMINATE_GRACE_SECONDS",
        0.001,
    )
    process = _HangingSystemctlProcess(ignore_terminate=True)

    with pytest.raises(SystemctlClientTimeoutError, match="timed out"):
        await wait_systemctl_client(
            cast("Process", process),
            timeout_s=0.001,
            operation="systemctl start",
        )

    assert process.terminate_calls == 1
    assert process.kill_calls == 1
    assert process.returncode == -9


@pytest.mark.asyncio
async def test_topology_timeout_terminates_client_and_declines_before_effect(
    mocker: MockerFixture,
) -> None:
    process = _HangingSystemctlProcess()
    subprocess = mocker.patch(
        "lychd.system.services.runtime_topology.asyncio.create_subprocess_exec",
        return_value=process,
    )
    attestor = RuntimeTopologyAttestor(
        SimpleNamespace(),  # type: ignore[arg-type]
        systemctl_bin="/usr/bin/systemctl",
        systemctl_timeout_s=0.001,
    )

    with pytest.raises(RuntimePreconditionError, match=r"Cannot attest.*timed out"):
        await attestor._list_target_units("list-unit-files")

    subprocess.assert_awaited_once()
    assert process.terminate_calls == 1
    assert process.kill_calls == 0
    assert process.returncode == -15
