from __future__ import annotations

# White-box cancellation test replaces the two narrow effect methods.
# pyright: reportPrivateUsage=false
import asyncio
import json
import stat
from threading import Event
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, call

import pytest
from pydantic import ValidationError

from lychd.config.settings import SwitchingSettings
from lychd.domain.orchestration.actuator import RuntimePreconditionError, TransitionIntent
from lychd.system.services.runtime import (
    HostReactorRuntimeActuator,
    SystemdRuntimeActuator,
    build_runtime_actuator,
    wait_for_host_reactor_idle,
)

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


def _recovery_registry() -> SimpleNamespace:
    specs = [SimpleNamespace(key=f"chat:{name}:model", animator_name=name) for name in ("new", "old-a", "old-b")]

    def soulstone(name: str) -> SimpleNamespace:
        return SimpleNamespace(service_name=f"lychd-{name}")

    return SimpleNamespace(
        list_capabilities=lambda: specs,
        get_soulstone_rune=soulstone,
        refresh_capability_states_for_animator=AsyncMock(),
    )


def _systemctl_result(returncode: int) -> SimpleNamespace:
    return SimpleNamespace(wait=AsyncMock(), returncode=returncode)


def _secure_reactor_dirs(tmp_path: Path) -> tuple[Path, Path]:
    inbox = tmp_path / "inbox"
    journal = tmp_path / "journal"
    inbox.mkdir(mode=0o700)
    journal.mkdir(mode=0o700)
    inbox.chmod(0o700)
    journal.chmod(0o700)
    return inbox, journal


async def _wait_until_exists(path: Path) -> None:
    for _ in range(100):
        if path.exists():
            return
        await asyncio.sleep(0)
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

    direct = build_runtime_actuator(SwitchingSettings(actuator="systemd"), registry)  # type: ignore[arg-type]
    reactor = build_runtime_actuator(
        SwitchingSettings(actuator="host-reactor", host_reactor_dir=tmp_path / "inbox"),
        registry,  # type: ignore[arg-type]
    )

    assert isinstance(direct, SystemdRuntimeActuator)
    assert isinstance(reactor, HostReactorRuntimeActuator)


@pytest.mark.asyncio
async def test_systemd_actuator_rolls_back_eviction_when_launch_fails(mocker: MockerFixture) -> None:
    specs = [
        SimpleNamespace(key="old:chat:model", animator_name="old"),
        SimpleNamespace(key="new:chat:model", animator_name="new"),
    ]
    states = {
        "old:chat:model": SimpleNamespace(is_active=True, runtime_started=True),
        "new:chat:model": SimpleNamespace(is_active=False, runtime_started=False),
    }

    def soulstone(name: str) -> SimpleNamespace:
        return SimpleNamespace(service_name=f"lychd-{name}")

    registry = SimpleNamespace(
        list_capabilities=lambda: specs,
        get_capability_state=states.get,
        get_soulstone_rune=soulstone,
        refresh_capability_states_for_animator=AsyncMock(),
    )
    successful_stop = SimpleNamespace(wait=AsyncMock(), returncode=0)
    failed_launch = SimpleNamespace(wait=AsyncMock(), returncode=1)
    successful_rollback = SimpleNamespace(wait=AsyncMock(), returncode=0)
    subprocess = mocker.patch(
        "lychd.system.services.runtime.asyncio.create_subprocess_exec",
        side_effect=[successful_stop, failed_launch, successful_rollback],
    )
    actuator = SystemdRuntimeActuator(registry)  # type: ignore[arg-type]
    intent = TransitionIntent(
        transition_id="c" * 32,
        config_generation="sha256:" + "d" * 64,
        target_animator="new",
        evict_animators=("old",),
        launch_animators=("new",),
        expected_active_animators=("old",),
    )

    with pytest.raises(RuntimeError, match="was rolled back"):
        await actuator.apply(intent)

    assert subprocess.call_args_list == [
        call("systemctl", "--user", "stop", "lychd-old.service"),
        call("systemctl", "--user", "start", "lychd-new.service"),
        call("systemctl", "--user", "start", "lychd-old.service"),
    ]


@pytest.mark.asyncio
async def test_systemd_actuator_rolls_back_before_propagating_cancellation() -> None:
    specs = [SimpleNamespace(key="old:chat:model", animator_name="old")]

    def active_state(_key: str) -> SimpleNamespace:
        return SimpleNamespace(is_active=True, runtime_started=True)

    def soulstone(name: str) -> SimpleNamespace:
        return SimpleNamespace(service_name=f"lychd-{name}")

    registry = SimpleNamespace(
        list_capabilities=lambda: specs,
        get_capability_state=active_state,
        get_soulstone_rune=soulstone,
        refresh_capability_states_for_animator=AsyncMock(),
    )
    actuator = SystemdRuntimeActuator(registry)  # type: ignore[arg-type]
    actuator._stop = AsyncMock()
    actuator._start = AsyncMock(side_effect=[asyncio.CancelledError(), None])
    intent = TransitionIntent(
        transition_id="e" * 32,
        config_generation="sha256:" + "f" * 64,
        target_animator="new",
        evict_animators=("old",),
        launch_animators=("new",),
        expected_active_animators=("old",),
    )

    with pytest.raises(asyncio.CancelledError):
        await actuator.apply(intent)

    assert actuator._start.await_args_list == [call("new"), call("old")]


@pytest.mark.asyncio
async def test_systemd_wait_cancellation_records_completed_effect_before_rollback(
    mocker: MockerFixture,
) -> None:
    specs = [SimpleNamespace(key="chat:local:model", animator_name="chat")]

    def active_state(_key: str) -> SimpleNamespace:
        return SimpleNamespace(is_active=True, runtime_started=True)

    def soulstone(name: str) -> SimpleNamespace:
        return SimpleNamespace(service_name=f"lychd-{name}")

    registry = SimpleNamespace(
        list_capabilities=lambda: specs,
        get_capability_state=active_state,
        get_soulstone_rune=soulstone,
        refresh_capability_states_for_animator=AsyncMock(),
    )
    wait_started = asyncio.Event()
    release_wait = asyncio.Event()

    async def delayed_wait() -> None:
        wait_started.set()
        await release_wait.wait()

    stopped = SimpleNamespace(wait=AsyncMock(side_effect=delayed_wait), returncode=0)
    restarted = _systemctl_result(0)
    subprocess = mocker.patch(
        "lychd.system.services.runtime.asyncio.create_subprocess_exec",
        side_effect=[stopped, restarted],
    )
    actuator = SystemdRuntimeActuator(registry)  # type: ignore[arg-type]

    apply_task = asyncio.create_task(actuator.apply(_intent()))
    await wait_started.wait()
    apply_task.cancel()
    release_wait.set()

    with pytest.raises(asyncio.CancelledError):
        await apply_task

    assert subprocess.call_args_list == [
        call("systemctl", "--user", "stop", "lychd-chat.service"),
        call("systemctl", "--user", "start", "lychd-chat.service"),
    ]


@pytest.mark.asyncio
async def test_host_systemd_actuator_observes_units_not_unreachable_model_probes(
    mocker: MockerFixture,
) -> None:
    specs = [
        SimpleNamespace(key="chat:local:model", animator_name="chat"),
        SimpleNamespace(key="vision:local:model", animator_name="vision"),
    ]

    def soulstone(name: str) -> SimpleNamespace:
        return SimpleNamespace(service_name=f"lychd-{name}")

    def unreachable_state(_key: str) -> SimpleNamespace:
        return SimpleNamespace(is_active=False, runtime_started=False)

    registry = SimpleNamespace(
        list_capabilities=lambda: specs,
        get_capability_state=unreachable_state,
        get_soulstone_rune=soulstone,
        refresh_capability_states_for_animator=AsyncMock(),
    )
    active = SimpleNamespace(wait=AsyncMock(), returncode=0)
    inactive = SimpleNamespace(wait=AsyncMock(), returncode=3)
    stopped = SimpleNamespace(wait=AsyncMock(), returncode=0)
    started = SimpleNamespace(wait=AsyncMock(), returncode=0)
    subprocess = mocker.patch(
        "lychd.system.services.runtime.asyncio.create_subprocess_exec",
        side_effect=[active, inactive, stopped, started],
    )
    actuator = SystemdRuntimeActuator(registry, observe_systemd=True)  # type: ignore[arg-type]

    await actuator.apply(_intent())

    assert subprocess.call_args_list == [
        call("systemctl", "--user", "is-active", "--quiet", "lychd-chat.service"),
        call("systemctl", "--user", "is-active", "--quiet", "lychd-vision.service"),
        call("systemctl", "--user", "stop", "lychd-chat.service"),
        call("systemctl", "--user", "start", "lychd-vision.service"),
    ]
    registry.refresh_capability_states_for_animator.assert_not_awaited()


@pytest.mark.asyncio
async def test_systemd_recovery_resumes_only_unfinished_legal_prefix(
    mocker: MockerFixture,
) -> None:
    registry = _recovery_registry()
    subprocess = mocker.patch(
        "lychd.system.services.runtime.asyncio.create_subprocess_exec",
        side_effect=[
            _systemctl_result(3),  # new is not launched yet
            _systemctl_result(3),  # old-a was already evicted
            _systemctl_result(0),  # old-b remains active
            _systemctl_result(0),  # stop old-b
            _systemctl_result(0),  # start new
        ],
    )
    actuator = SystemdRuntimeActuator(registry, observe_systemd=True)  # type: ignore[arg-type]

    await actuator.recover(_recovery_intent())

    assert subprocess.call_args_list == [
        call("systemctl", "--user", "is-active", "--quiet", "lychd-new.service"),
        call("systemctl", "--user", "is-active", "--quiet", "lychd-old-a.service"),
        call("systemctl", "--user", "is-active", "--quiet", "lychd-old-b.service"),
        call("systemctl", "--user", "stop", "lychd-old-b.service"),
        call("systemctl", "--user", "start", "lychd-new.service"),
    ]


@pytest.mark.asyncio
async def test_systemd_recovery_accepts_already_completed_prefix(
    mocker: MockerFixture,
) -> None:
    registry = _recovery_registry()
    subprocess = mocker.patch(
        "lychd.system.services.runtime.asyncio.create_subprocess_exec",
        side_effect=[
            _systemctl_result(0),  # new is active
            _systemctl_result(3),
            _systemctl_result(3),
        ],
    )
    actuator = SystemdRuntimeActuator(registry, observe_systemd=True)  # type: ignore[arg-type]

    await actuator.recover(_recovery_intent())

    assert len(subprocess.call_args_list) == 3


@pytest.mark.asyncio
async def test_systemd_recovery_rejects_non_prefix_without_mutation(
    mocker: MockerFixture,
) -> None:
    registry = _recovery_registry()
    subprocess = mocker.patch(
        "lychd.system.services.runtime.asyncio.create_subprocess_exec",
        side_effect=[
            _systemctl_result(0),  # new launched too early
            _systemctl_result(3),  # old-a evicted
            _systemctl_result(0),  # old-b still active: not a legal prefix
        ],
    )
    actuator = SystemdRuntimeActuator(registry, observe_systemd=True)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="not a legal action prefix"):
        await actuator.recover(_recovery_intent())

    assert len(subprocess.call_args_list) == 3


@pytest.mark.asyncio
async def test_systemd_recovery_failure_compensates_the_entire_crash_prefix(
    mocker: MockerFixture,
) -> None:
    registry = _recovery_registry()
    subprocess = mocker.patch(
        "lychd.system.services.runtime.asyncio.create_subprocess_exec",
        side_effect=[
            _systemctl_result(3),  # new is not launched yet
            _systemctl_result(3),  # old-a was evicted before the crash
            _systemctl_result(0),  # old-b remains active
            _systemctl_result(0),  # finish evicting old-b
            _systemctl_result(1),  # launching new fails
            _systemctl_result(0),  # restore old-b
            _systemctl_result(0),  # restore the pre-crash old-a eviction too
        ],
    )
    actuator = SystemdRuntimeActuator(registry, observe_systemd=True)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="was rolled back"):
        await actuator.recover(_recovery_intent())

    assert subprocess.call_args_list[-4:] == [
        call("systemctl", "--user", "stop", "lychd-old-b.service"),
        call("systemctl", "--user", "start", "lychd-new.service"),
        call("systemctl", "--user", "start", "lychd-old-b.service"),
        call("systemctl", "--user", "start", "lychd-old-a.service"),
    ]
