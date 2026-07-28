from __future__ import annotations

# White-box cancellation test replaces the two narrow effect methods.
# pyright: reportPrivateUsage=false
import asyncio
import json
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from threading import Event
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, call

import pytest
from pydantic import ValidationError

from lychd.config.settings.orchestration import SwitchingSettings
from lychd.domain.orchestration.actuator import (
    RuntimeActuationRestoredError,
    RuntimePreconditionError,
    TransitionIntent,
)
from lychd.system.services.lifecycle.lock import LifecycleLock
from lychd.system.services.lifecycle.models import LifecycleError
from lychd.system.services.runtime import (
    HostReactorRuntimeActuator,
    SystemdRuntimeActuator,
    _ObservedRuntimeWorld,
    build_runtime_actuator,
    wait_for_host_reactor_idle,
)
from lychd.system.services.systemctl_process import SystemctlClientTimeoutError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def _intent() -> TransitionIntent:
    return TransitionIntent(
        transition_id="a" * 32,
        config_generation="sha256:" + "b" * 64,
        target_animator="vision",
        evict_animators=("chat",),
        launch_animators=("vision",),
        expected_active_animators=("chat",),
    )


def _recovery_intent() -> TransitionIntent:
    return TransitionIntent(
        transition_id="d" * 32,
        config_generation="sha256:" + "e" * 64,
        target_animator="new",
        evict_animators=("old-a", "old-b"),
        launch_animators=("new",),
        expected_active_animators=("old-a", "old-b"),
    )


def _systemctl_result(returncode: int) -> SimpleNamespace:
    return SimpleNamespace(wait=AsyncMock(), returncode=returncode)


class _HangingSystemctlProcess:
    """Process fake that exits only after the timeout helper terminates it."""

    def __init__(self) -> None:
        self.returncode: int | None = None
        self.terminate_calls = 0
        self._exited = asyncio.Event()

    async def wait(self) -> int:
        await self._exited.wait()
        assert self.returncode is not None
        return self.returncode

    def terminate(self) -> None:
        self.terminate_calls += 1
        self.returncode = -15
        self._exited.set()

    def kill(self) -> None:
        self.returncode = -9
        self._exited.set()


def _secure_reactor_dirs(tmp_path: Path) -> tuple[Path, Path]:
    inbox = tmp_path / "inbox"
    journal = tmp_path / "journal"
    inbox.mkdir(mode=0o700)
    journal.mkdir(mode=0o700)
    inbox.chmod(0o700)
    journal.chmod(0o700)
    return inbox, journal


@contextmanager
def _exit_failure_lock() -> Iterator[None]:
    """Acquire successfully, then fail while relinquishing effect authority."""
    yield
    message = "synthetic post-effect lifecycle release failure"
    raise LifecycleError(message)


async def _wait_until_exists(path: Path) -> None:
    deadline = asyncio.get_running_loop().time() + 1.0
    while asyncio.get_running_loop().time() < deadline:
        if path.exists():
            return
        await asyncio.sleep(0.001)
    pytest.fail(f"path was not published: {path}")


@pytest.mark.asyncio
async def test_host_reactor_publishes_one_atomic_restricted_intent(tmp_path: Path, mocker: MockerFixture) -> None:
    async def inline(function: object, *args: object) -> object:
        return function(*args)  # type: ignore[operator]

    mocker.patch("lychd.system.services.runtime.asyncio.to_thread", side_effect=inline)
    mocker.patch("lychd.system.services.runtime._ACK_POLL_SECONDS", 0.001)
    inbox, journal = _secure_reactor_dirs(tmp_path)
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=1)

    apply_task = asyncio.create_task(actuator.apply(_intent()))
    target = inbox / f"{'a' * 32}.json"
    await _wait_until_exists(target)

    assert json.loads(target.read_text(encoding="utf-8")) == _intent().model_dump(mode="json")
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert list(inbox.glob(".*.tmp")) == []
    assert not apply_task.done()

    target.replace(journal / f"{'a' * 32}.completed.json")
    await apply_task

    # A completed transition identity is idempotent and is never republished.
    await actuator.apply(_intent())
    assert not target.exists()


@pytest.mark.asyncio
async def test_host_reactor_requires_preprovisioned_directory(tmp_path: Path, mocker: MockerFixture) -> None:
    async def inline(function: object, *args: object) -> object:
        return function(*args)  # type: ignore[operator]

    mocker.patch("lychd.system.services.runtime.asyncio.to_thread", side_effect=inline)
    journal = tmp_path / "journal"
    journal.mkdir(mode=0o700)
    journal.chmod(0o700)
    actuator = HostReactorRuntimeActuator(tmp_path / "missing", journal, ack_timeout_s=1)

    with pytest.raises(RuntimeError, match="does not exist"):
        await actuator.apply(_intent())


@pytest.mark.asyncio
async def test_host_reactor_surfaces_terminal_rejection(tmp_path: Path) -> None:
    inbox, journal = _secure_reactor_dirs(tmp_path)
    rejected = journal / f"{_intent().transition_id}.rejected.json"
    rejected.write_text('{"status":"rejected"}\n', encoding="utf-8")
    rejected.chmod(0o600)
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=1)

    with pytest.raises(RuntimeError, match="rejected transition"):
        await actuator.apply(_intent())

    assert list(inbox.iterdir()) == []


@pytest.mark.asyncio
async def test_host_reactor_surfaces_safe_precondition_decline(tmp_path: Path) -> None:
    inbox, journal = _secure_reactor_dirs(tmp_path)
    declined = journal / f"{_intent().transition_id}.declined.json"
    declined.write_text("{}\n", encoding="utf-8")
    declined.chmod(0o600)
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=1)

    with pytest.raises(RuntimePreconditionError, match="declined transition"):
        await actuator.apply(_intent())

    assert list(inbox.iterdir()) == []


@pytest.mark.asyncio
async def test_host_reactor_surfaces_verified_prior_world_restoration(tmp_path: Path) -> None:
    inbox, journal = _secure_reactor_dirs(tmp_path)
    restored = journal / f"{_intent().transition_id}.restored.json"
    restored.write_text("{}\n", encoding="utf-8")
    restored.chmod(0o600)
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=1)

    with pytest.raises(RuntimeActuationRestoredError, match="restored its prior runtime world"):
        await actuator.apply(_intent())

    assert list(inbox.iterdir()) == []


@pytest.mark.asyncio
async def test_host_reactor_timeout_retracts_only_unclaimed_delivery(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    mocker.patch("lychd.system.services.runtime._ACK_POLL_SECONDS", 0.001)
    inbox, journal = _secure_reactor_dirs(tmp_path)
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=0.001)

    with pytest.raises(TimeoutError, match="did not claim"):
        await actuator.apply(_intent())

    assert list(inbox.iterdir()) == []
    assert list(journal.iterdir()) == []


@pytest.mark.asyncio
async def test_host_reactor_claim_holds_fence_past_ack_timeout(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    mocker.patch("lychd.system.services.runtime._ACK_POLL_SECONDS", 0.001)
    inbox, journal = _secure_reactor_dirs(tmp_path)
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=0.001)
    pending = inbox / f"{_intent().transition_id}.json"
    processing = journal / f"{_intent().transition_id}.processing.json"
    completed = journal / f"{_intent().transition_id}.completed.json"

    apply_task = asyncio.create_task(actuator.apply(_intent()))
    await _wait_until_exists(pending)
    pending.replace(processing)
    await asyncio.sleep(0.01)
    assert not apply_task.done()

    processing.replace(completed)
    await apply_task


@pytest.mark.asyncio
async def test_host_reactor_cancellation_waits_for_claimed_terminal_record(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    mocker.patch("lychd.system.services.runtime._ACK_POLL_SECONDS", 0.001)
    inbox, journal = _secure_reactor_dirs(tmp_path)
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=1)
    pending = inbox / f"{_intent().transition_id}.json"
    processing = journal / f"{_intent().transition_id}.processing.json"
    completed = journal / f"{_intent().transition_id}.completed.json"

    apply_task = asyncio.create_task(actuator.apply(_intent()))
    await _wait_until_exists(pending)
    pending.replace(processing)
    apply_task.cancel()
    await asyncio.sleep(0.01)
    assert not apply_task.done()

    processing.replace(completed)
    with pytest.raises(asyncio.CancelledError):
        await apply_task


@pytest.mark.asyncio
async def test_host_reactor_cancellation_fences_inflight_atomic_publish(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    inbox, journal = _secure_reactor_dirs(tmp_path)
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=1)
    original_write = actuator._write_atomic
    started = Event()
    release = Event()

    def delayed_write(intent: TransitionIntent) -> None:
        started.set()
        assert release.wait(timeout=2)
        original_write(intent)

    mocker.patch.object(actuator, "_write_atomic", side_effect=delayed_write)
    apply_task = asyncio.create_task(actuator.apply(_intent()))
    assert await asyncio.to_thread(started.wait, 2)

    apply_task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await apply_task

    assert not (inbox / f"{_intent().transition_id}.json").exists()
    assert list(journal.iterdir()) == []


@pytest.mark.asyncio
async def test_host_reactor_post_link_fsync_failure_retracts_exposed_delivery(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    inbox, journal = _secure_reactor_dirs(tmp_path)
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=1)
    fsync_calls = 0
    failure_message = "directory durability failed"

    def fail_directory_fsync(_descriptor: int) -> None:
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 2:
            raise OSError(failure_message)

    mocker.patch("lychd.system.services.runtime.os.fsync", side_effect=fail_directory_fsync)

    with pytest.raises(OSError, match=failure_message):
        await actuator.apply(_intent())

    assert fsync_calls >= 3  # payload, failed publish-dir sync, retraction-dir sync
    assert not (inbox / f"{_intent().transition_id}.json").exists()
    assert list(inbox.glob(".*.tmp")) == []
    assert list(journal.iterdir()) == []


@pytest.mark.asyncio
async def test_host_reactor_post_link_failure_waits_for_concurrent_claim(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    inbox, journal = _secure_reactor_dirs(tmp_path)
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=1)
    transition_id = _intent().transition_id
    pending = inbox / f"{transition_id}.json"
    processing = journal / f"{transition_id}.processing.json"
    completed = journal / f"{transition_id}.completed.json"
    fsync_calls = 0
    failure_message = "post-link directory sync failed"

    def claim_then_fail(_descriptor: int) -> None:
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 2:
            pending.replace(processing)
            raise OSError(failure_message)

    mocker.patch("lychd.system.services.runtime._ACK_POLL_SECONDS", 0.001)
    mocker.patch("lychd.system.services.runtime.os.fsync", side_effect=claim_then_fail)
    apply_task = asyncio.create_task(actuator.apply(_intent()))
    await _wait_until_exists(processing)
    await asyncio.sleep(0.01)
    assert not apply_task.done()

    processing.replace(completed)
    with pytest.raises(OSError, match=failure_message):
        await apply_task


@pytest.mark.asyncio
async def test_startup_idle_fence_validates_both_reactor_directories(tmp_path: Path) -> None:
    inbox, journal = _secure_reactor_dirs(tmp_path)
    settings = SwitchingSettings(
        actuator="host-reactor",
        host_reactor_dir=inbox,
        reactor_ack_timeout_s=0.01,
    )

    await wait_for_host_reactor_idle(settings)

    journal.chmod(0o755)
    with pytest.raises(RuntimeError, match="journal directory must be owned"):
        await wait_for_host_reactor_idle(settings)


@pytest.mark.asyncio
async def test_startup_idle_fence_waits_for_crash_processing_record(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    mocker.patch("lychd.system.services.runtime._ACK_POLL_SECONDS", 0.001)
    inbox, journal = _secure_reactor_dirs(tmp_path)
    settings = SwitchingSettings(
        actuator="host-reactor",
        host_reactor_dir=inbox,
        reactor_ack_timeout_s=1,
    )
    processing = journal / f"{_intent().transition_id}.processing.json"
    processing.write_text("{}\n", encoding="utf-8")
    processing.chmod(0o600)

    fence = asyncio.create_task(wait_for_host_reactor_idle(settings))
    await asyncio.sleep(0.01)
    assert not fence.done()

    processing.unlink()
    await fence


def test_transition_intent_rejects_path_or_command_injection() -> None:
    with pytest.raises(ValidationError):
        TransitionIntent.model_validate({**_intent().model_dump(), "target_animator": "../../bin/sh"})
    with pytest.raises(ValidationError):
        TransitionIntent.model_validate({**_intent().model_dump(), "transition_id": "../escape"})


@pytest.mark.parametrize(
    ("update", "message"),
    [
        ({"evict_animators": ("chat", "chat")}, "duplicate"),
        ({"launch_animators": ("vision", "chat")}, "both evicted and launched"),
        ({"target_animator": "other"}, "target_animator"),
        ({"expected_active_animators": ()}, "Evicted animators"),
        ({"expected_active_animators": ("chat", "vision")}, "already be expected active"),
    ],
)
def test_transition_intent_rejects_ambiguous_transition_sets(
    update: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        TransitionIntent.model_validate({**_intent().model_dump(), **update})


def test_runtime_actuator_factory_is_configuration_owned(tmp_path: Path) -> None:
    registry = SimpleNamespace()

    direct = build_runtime_actuator(
        SwitchingSettings(actuator="systemd", systemctl_timeout_s=7.5),
        registry,  # type: ignore[arg-type]
        systemctl_bin="/usr/bin/systemctl",
    )
    reactor = build_runtime_actuator(
        SwitchingSettings(actuator="host-reactor", host_reactor_dir=tmp_path / "inbox"),
        registry,  # type: ignore[arg-type]
    )

    assert isinstance(direct, SystemdRuntimeActuator)
    assert direct._systemctl_timeout_s == 7.5
    assert isinstance(reactor, HostReactorRuntimeActuator)


def test_direct_systemd_actuation_requires_an_absolute_attested_executable() -> None:
    registry = SimpleNamespace()

    with pytest.raises(ValueError, match="absolute attested systemctl"):
        SystemdRuntimeActuator(registry, systemctl_bin="systemctl")  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="injected attested systemctl"):
        build_runtime_actuator(
            SwitchingSettings(actuator="systemd"),
            registry,  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_direct_systemd_factory_refuses_effect_without_lifecycle_authority(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    lock_path = tmp_path / "lifecycle.lock"
    registry = SimpleNamespace()
    subprocess = mocker.patch(
        "lychd.system.services.runtime.asyncio.create_subprocess_exec",
    )
    actuator = build_runtime_actuator(
        SwitchingSettings(actuator="systemd"),
        registry,  # type: ignore[arg-type]
        systemctl_bin="/usr/bin/systemctl",
        lock_factory=lambda: LifecycleLock(lock_path),
    )

    with (
        LifecycleLock(lock_path),
        pytest.raises(RuntimePreconditionError, match="could not acquire lifecycle authority"),
    ):
        await actuator.apply(_intent())

    subprocess.assert_not_called()


@pytest.mark.asyncio
async def test_direct_systemd_does_not_misclassify_post_entry_lock_failure() -> None:
    actuator = SystemdRuntimeActuator(
        SimpleNamespace(),  # type: ignore[arg-type]
        systemctl_bin="/usr/bin/systemctl",
        observe_systemd=True,
        lock_factory=_exit_failure_lock,
    )
    actuator._apply_locked = AsyncMock()
    actuator._recover_locked = AsyncMock()

    with pytest.raises(LifecycleError, match="post-effect"):
        await actuator.apply(_intent())
    with pytest.raises(LifecycleError, match="post-effect"):
        await actuator.recover(_intent())

    actuator._apply_locked.assert_awaited_once_with(_intent())
    actuator._recover_locked.assert_awaited_once_with(_intent())


def _runtime_registry(*names: str) -> SimpleNamespace:
    stones = {name: SimpleNamespace(name=name) for name in names}
    return SimpleNamespace(
        list_soulstone_runes=lambda: list(stones.values()),
        list_capabilities=list,
        get_soulstone_rune=stones.get,
        refresh_capability_states_for_animator=AsyncMock(),
    )


def _observing_actuator(*names: str, systemctl_timeout_s: float = 120.0) -> SystemdRuntimeActuator:
    actuator = SystemdRuntimeActuator(
        _runtime_registry(*names),  # type: ignore[arg-type]
        systemctl_bin="/usr/bin/systemctl",
        systemctl_timeout_s=systemctl_timeout_s,
        observe_systemd=True,
    )
    actuator._topology_attestor.attest = AsyncMock()
    actuator._pending_relevant_jobs = AsyncMock(return_value=())
    actuator._await_relevant_jobs_quiescent = AsyncMock()
    return actuator


@pytest.mark.asyncio
async def test_systemd_actuator_submits_one_target_transaction_without_explicit_stop() -> None:
    actuator = _observing_actuator("chat", "vision")
    actuator._observe_runtime_world = AsyncMock(
        side_effect=[
            _ObservedRuntimeWorld(("chat",), ("chat",)),
            _ObservedRuntimeWorld(("vision",), ("vision",)),
        ]
    )
    actuator._run_systemctl = AsyncMock(return_value=0)

    await actuator.apply(_intent())

    actuator._run_systemctl.assert_awaited_once_with(
        "start",
        ("lychd-animator-vision.target",),
    )
    attest = actuator._topology_attestor.attest
    assert isinstance(attest, AsyncMock)
    attest.assert_awaited_once_with(_intent())


@pytest.mark.asyncio
async def test_systemd_actuator_accepts_desired_world_even_after_nonzero_client_result() -> None:
    actuator = _observing_actuator("chat", "vision")
    actuator._observe_runtime_world = AsyncMock(
        side_effect=[
            _ObservedRuntimeWorld(("chat",), ("chat",)),
            _ObservedRuntimeWorld(("vision",), ("vision",)),
        ]
    )
    actuator._run_systemctl = AsyncMock(return_value=1)

    await actuator.apply(_intent())

    actuator._run_systemctl.assert_awaited_once()


@pytest.mark.asyncio
async def test_systemd_actuator_reports_verified_prior_world_restoration() -> None:
    actuator = _observing_actuator("chat", "vision")
    actuator._observe_runtime_world = AsyncMock(
        side_effect=[
            _ObservedRuntimeWorld(("chat",), ("chat",)),
            _ObservedRuntimeWorld(("chat",), ("chat",)),
        ]
    )
    actuator._run_systemctl = AsyncMock(return_value=1)

    with pytest.raises(RuntimeActuationRestoredError, match="restored its prior runtime world"):
        await actuator.apply(_intent())

    actuator._run_systemctl.assert_awaited_once()


@pytest.mark.asyncio
async def test_systemd_actuator_compensates_target_active_service_failed_world() -> None:
    actuator = _observing_actuator("chat", "vision")
    actuator._observe_runtime_world = AsyncMock(
        side_effect=[
            _ObservedRuntimeWorld(("chat",), ("chat",)),
            _ObservedRuntimeWorld(("vision",), ()),
            _ObservedRuntimeWorld(("chat",), ("chat",)),
        ]
    )
    actuator._run_systemctl = AsyncMock(side_effect=[1, 0])

    with pytest.raises(RuntimeActuationRestoredError, match="prior runtime world was restored"):
        await actuator.apply(_intent())

    assert actuator._run_systemctl.await_args_list == [
        call("start", ("lychd-animator-vision.target",)),
        call("start", ("lychd-animator-chat.target",)),
    ]


@pytest.mark.asyncio
async def test_systemd_actuator_removes_failed_coexisting_launch_during_compensation() -> None:
    actuator = _observing_actuator("old", "vision")
    intent = TransitionIntent(
        transition_id="2" * 32,
        config_generation="sha256:" + "3" * 64,
        target_animator="vision",
        launch_animators=("vision",),
        expected_active_animators=("old",),
    )
    actuator._observe_runtime_world = AsyncMock(
        side_effect=[
            _ObservedRuntimeWorld(("old",), ("old",)),
            _ObservedRuntimeWorld(("old", "vision"), ("old",)),
            _ObservedRuntimeWorld(("old",), ("old",)),
        ]
    )
    actuator._run_systemctl = AsyncMock(side_effect=[1, 0])

    with pytest.raises(RuntimeActuationRestoredError, match="prior runtime world was restored"):
        await actuator.apply(intent)

    assert actuator._run_systemctl.await_args_list == [
        call("start", ("lychd-animator-vision.target",)),
        call("stop", ("lychd-animator-vision.target",)),
    ]


@pytest.mark.asyncio
async def test_systemd_actuator_declines_stale_target_reservation_before_effect() -> None:
    actuator = _observing_actuator("chat", "vision")
    actuator._observe_runtime_world = AsyncMock(return_value=_ObservedRuntimeWorld(("chat",), ()))
    actuator._run_systemctl = AsyncMock()

    with pytest.raises(RuntimePreconditionError, match="target reservations"):
        await actuator.apply(_intent())

    actuator._run_systemctl.assert_not_awaited()


@pytest.mark.asyncio
async def test_systemd_actuator_declines_pending_jobs_before_effect() -> None:
    actuator = _observing_actuator("chat", "vision")
    actuator._pending_relevant_jobs = AsyncMock(return_value=("lychd-animator-chat.target",))
    actuator._observe_runtime_world = AsyncMock()
    actuator._run_systemctl = AsyncMock()

    with pytest.raises(RuntimePreconditionError, match="in-flight systemd jobs"):
        await actuator.apply(_intent())

    actuator._observe_runtime_world.assert_not_awaited()
    actuator._run_systemctl.assert_not_awaited()


@pytest.mark.asyncio
async def test_systemd_actuator_maps_client_timeout_before_effect_to_safe_decline() -> None:
    actuator = _observing_actuator("chat", "vision")
    actuator._pending_relevant_jobs = AsyncMock(
        side_effect=SystemctlClientTimeoutError("systemctl list-jobs", 1),
    )
    actuator._observe_runtime_world = AsyncMock()
    actuator._run_systemctl = AsyncMock()

    with pytest.raises(RuntimePreconditionError, match="before any effect"):
        await actuator.apply(_intent())

    actuator._observe_runtime_world.assert_not_awaited()
    actuator._run_systemctl.assert_not_awaited()


@pytest.mark.asyncio
async def test_systemd_actuator_classifies_and_compensates_after_effect_client_timeout(
    mocker: MockerFixture,
) -> None:
    actuator = _observing_actuator("chat", "vision", systemctl_timeout_s=0.001)
    actuator._observe_runtime_world = AsyncMock(
        side_effect=[
            _ObservedRuntimeWorld(("chat",), ("chat",)),
            _ObservedRuntimeWorld(("vision",), ()),
            _ObservedRuntimeWorld(("chat",), ("chat",)),
        ]
    )
    timed_out = _HangingSystemctlProcess()
    subprocess = mocker.patch(
        "lychd.system.services.runtime.asyncio.create_subprocess_exec",
        side_effect=[timed_out, _systemctl_result(0)],
    )

    with pytest.raises(RuntimeActuationRestoredError, match="prior runtime world was restored"):
        await actuator.apply(_intent())

    assert timed_out.terminate_calls == 1
    assert subprocess.call_args_list == [
        call(
            "/usr/bin/systemctl",
            "--user",
            "start",
            "--job-mode=fail",
            "lychd-animator-vision.target",
        ),
        call(
            "/usr/bin/systemctl",
            "--user",
            "start",
            "--job-mode=fail",
            "lychd-animator-chat.target",
        ),
    ]


@pytest.mark.asyncio
async def test_systemd_actuator_shields_cancellation_then_restores_prior_world() -> None:
    actuator = _observing_actuator("chat", "vision")
    actuator._observe_runtime_world = AsyncMock(
        side_effect=[
            _ObservedRuntimeWorld(("chat",), ("chat",)),
            _ObservedRuntimeWorld(("vision",), ("vision",)),
            _ObservedRuntimeWorld(("vision",), ("vision",)),
            _ObservedRuntimeWorld(("chat",), ("chat",)),
        ]
    )
    effect_started = asyncio.Event()
    release_effect = asyncio.Event()
    calls: list[tuple[str, tuple[str, ...]]] = []

    async def run_systemctl(action: str, unit_names: tuple[str, ...]) -> int:
        calls.append((action, unit_names))
        if len(calls) == 1:
            effect_started.set()
            await release_effect.wait()
        return 0

    actuator._run_systemctl = run_systemctl
    apply_task = asyncio.create_task(actuator.apply(_intent()))
    await effect_started.wait()
    apply_task.cancel()
    release_effect.set()

    with pytest.raises(asyncio.CancelledError):
        await apply_task

    assert calls == [
        ("start", ("lychd-animator-vision.target",)),
        ("start", ("lychd-animator-chat.target",)),
    ]


@pytest.mark.asyncio
async def test_systemd_compensation_without_launch_stops_target_once() -> None:
    actuator = _observing_actuator("vision")
    intent = TransitionIntent(
        transition_id="f" * 32,
        operation="compensation",
        rollback_of="e" * 32,
        config_generation="sha256:" + "1" * 64,
        target_animator="vision",
        evict_animators=("vision",),
        expected_active_animators=("vision",),
    )
    actuator._observe_runtime_world = AsyncMock(
        side_effect=[
            _ObservedRuntimeWorld(("vision",), ("vision",)),
            _ObservedRuntimeWorld((), ()),
        ]
    )
    actuator._run_systemctl = AsyncMock(return_value=0)

    await actuator.apply(intent)

    actuator._run_systemctl.assert_awaited_once_with(
        "stop",
        ("lychd-animator-vision.target",),
    )


@pytest.mark.asyncio
async def test_systemd_recovery_accepts_exact_desired_world_without_mutation() -> None:
    actuator = _observing_actuator("new", "old-a", "old-b")
    actuator._observe_runtime_world = AsyncMock(return_value=_ObservedRuntimeWorld(("new",), ("new",)))
    actuator._run_systemctl = AsyncMock()

    await actuator.recover(_recovery_intent())

    actuator._run_systemctl.assert_not_awaited()


@pytest.mark.asyncio
async def test_systemd_recovery_retries_one_full_transaction_from_exact_prior_world() -> None:
    actuator = _observing_actuator("new", "old-a", "old-b")
    actuator._observe_runtime_world = AsyncMock(
        side_effect=[
            _ObservedRuntimeWorld(("old-a", "old-b"), ("old-a", "old-b")),
            _ObservedRuntimeWorld(("new",), ("new",)),
        ]
    )
    actuator._run_systemctl = AsyncMock(return_value=0)

    await actuator.recover(_recovery_intent())

    actuator._run_systemctl.assert_awaited_once_with(
        "start",
        ("lychd-animator-new.target",),
    )


@pytest.mark.asyncio
async def test_systemd_recovery_compensates_partial_world_in_one_multi_target_request() -> None:
    actuator = _observing_actuator("new", "old-a", "old-b")
    actuator._observe_runtime_world = AsyncMock(
        side_effect=[
            _ObservedRuntimeWorld(("new", "old-b"), ("old-b",)),
            _ObservedRuntimeWorld(("old-a", "old-b"), ("old-a", "old-b")),
        ]
    )
    actuator._run_systemctl = AsyncMock(return_value=0)

    with pytest.raises(RuntimeActuationRestoredError, match="Recovered partial transition"):
        await actuator.recover(_recovery_intent())

    actuator._run_systemctl.assert_awaited_once_with(
        "start",
        (
            "lychd-animator-old-a.target",
            "lychd-animator-old-b.target",
        ),
    )


@pytest.mark.asyncio
async def test_host_systemd_world_observes_targets_and_services_for_every_soulstone(
    mocker: MockerFixture,
) -> None:
    registry = _runtime_registry("chat", "vision")
    subprocess = mocker.patch(
        "lychd.system.services.runtime.asyncio.create_subprocess_exec",
        side_effect=[
            _systemctl_result(0),
            _systemctl_result(0),
            _systemctl_result(3),
            _systemctl_result(3),
        ],
    )
    actuator = SystemdRuntimeActuator(
        registry,  # type: ignore[arg-type]
        systemctl_bin="/usr/bin/systemctl",
        observe_systemd=True,
    )

    world = await actuator._observe_runtime_world()

    assert world == _ObservedRuntimeWorld(("chat",), ("chat",))
    assert subprocess.call_args_list == [
        call("/usr/bin/systemctl", "--user", "is-active", "--quiet", "lychd-animator-chat.target"),
        call("/usr/bin/systemctl", "--user", "is-active", "--quiet", "lychd-chat.service"),
        call("/usr/bin/systemctl", "--user", "is-active", "--quiet", "lychd-animator-vision.target"),
        call("/usr/bin/systemctl", "--user", "is-active", "--quiet", "lychd-vision.service"),
    ]
