from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from lychd.config import QuadletConfig
from lychd.domain.animation.schemas import GenericSoulstoneConfig
from lychd.domain.orchestration.actuator import RuntimePreconditionError, TransitionIntent
from lychd.system.services.runtime_topology import RuntimeTopologyAttestor
from lychd.system.services.scribe import OwnedBindings
from lychd.system.services.systemctl_process import (
    SystemctlClientTimeoutError,
    wait_systemctl_client,
)

if TYPE_CHECKING:
    from asyncio.subprocess import Process
    from pathlib import Path

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
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    process = _HangingSystemctlProcess()
    subprocess = mocker.patch(
        "lychd.system.services.runtime_topology.asyncio.create_subprocess_exec",
        return_value=process,
    )
    stone = GenericSoulstoneConfig(
        name="alpha",
        quadlet=QuadletConfig(image="example/alpha:latest"),
    )
    attestor = RuntimeTopologyAttestor(
        SimpleNamespace(list_soulstone_runes=lambda: [stone]),  # type: ignore[arg-type]
        systemctl_bin="/usr/bin/systemctl",
        systemctl_timeout_s=0.001,
        owned_bindings_provider=lambda: OwnedBindings(
            receipt_present=True,
            generation="sha256:test-generation",
            quadlet_sources=(tmp_path / "quadlet" / "lychd-alpha.container",),
            systemd_sources=(tmp_path / "systemd" / "lychd-animator-alpha.target",),
        ),
    )
    intent = TransitionIntent(
        config_generation="sha256:" + "a" * 64,
        target_animator="alpha",
        target_capability_key="alpha:default",
        launch_animators=("alpha",),
    )

    with pytest.raises(RuntimePreconditionError, match=r"Cannot attest.*timed out"):
        await attestor.attest(intent)

    subprocess.assert_awaited_once()
    assert process.terminate_calls == 1
    assert process.kill_calls == 0
    assert process.returncode == -15
