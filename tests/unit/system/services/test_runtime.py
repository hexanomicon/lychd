from __future__ import annotations

# White-box cancellation test replaces the two narrow effect methods.
# pyright: reportPrivateUsage=false
import asyncio
import json
import os
import stat
from collections.abc import Generator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, call

import pytest
from pydantic import ValidationError

from lychd.config.settings.orchestration import SwitchingSettings
from lychd.domain.cortex.leases import AnimatorAdmission
from lychd.domain.orchestration.actuator import (
    RuntimeActuationRestoredError,
    RuntimeCancellationNoEffectError,
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
from tests.capability_workflows import build_capability_scenario

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def run_runtime_file_io_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the file boundary without depending on the runner's thread pool."""

    async def inline(function: object, /, *args: object, **kwargs: object) -> object:
        return function(*args, **kwargs)  # type: ignore[operator]

    monkeypatch.setattr("lychd.system.services.runtime.asyncio.to_thread", inline)


def _intent() -> TransitionIntent:
    return TransitionIntent(
        transition_id="a" * 32,
        config_generation="sha256:" + "b" * 64,
        target_animator="vision",
        target_capability_key="vision:default",
        evict_animators=("chat",),
        launch_animators=("vision",),
        expected_active_animators=("chat",),
    )


def _recovery_intent() -> TransitionIntent:
    return TransitionIntent(
        transition_id="d" * 32,
        config_generation="sha256:" + "e" * 64,
        target_animator="new",
        target_capability_key="new:default",
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
def _exit_failure_lock() -> Generator[None]:
    """Acquire successfully, then fail while relinquishing effect authority."""
    yield
    message = "synthetic post-effect lifecycle release failure"
    raise LifecycleError(message)


async def _wait_until_exists(path: Path) -> None:
    deadline = asyncio.get_running_loop().time() + 1.0
    while asyncio.get_running_loop().time() < deadline:
        if await asyncio.to_thread(path.exists):
            return
        await asyncio.sleep(0.001)
    pytest.fail(f"path was not published: {path}")


@pytest.mark.asyncio
async def test_host_reactor_publishes_one_atomic_restricted_intent(tmp_path: Path, mocker: MockerFixture) -> None:
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
async def test_host_reactor_requires_preprovisioned_directory(tmp_path: Path) -> None:
    journal = tmp_path / "journal"
    journal.mkdir(mode=0o700)
    journal.chmod(0o700)
    actuator = HostReactorRuntimeActuator(tmp_path / "missing", journal, ack_timeout_s=1)

    with pytest.raises(RuntimeError, match="does not exist"):
        await actuator.apply(_intent())


@pytest.mark.asyncio
async def test_host_reactor_rejects_symlinked_boundary_parent(tmp_path: Path) -> None:
    real_root = tmp_path / "real"
    real_root.mkdir()
    inbox, journal = _secure_reactor_dirs(real_root)
    linked_root = tmp_path / "linked"
    linked_root.symlink_to(real_root, target_is_directory=True)
    actuator = HostReactorRuntimeActuator(
        linked_root / inbox.name,
        linked_root / journal.name,
        ack_timeout_s=1,
    )

    with pytest.raises(RuntimeError, match="does not exist safely"):
        await actuator.apply(_intent())


@pytest.mark.parametrize(
    ("suffix", "error_type", "match", "content"),
    [
        ("rejected", RuntimeError, "rejected transition", '{"status":"rejected"}\n'),
        ("declined", RuntimePreconditionError, "declined transition", "{}\n"),
        ("restored", RuntimeActuationRestoredError, "restored its prior runtime world", "{}\n"),
    ],
)
@pytest.mark.asyncio
async def test_host_reactor_surfaces_terminal_outcome(
    tmp_path: Path,
    suffix: str,
    error_type: type[Exception],
    match: str,
    content: str,
) -> None:
    inbox, journal = _secure_reactor_dirs(tmp_path)
    outcome = journal / f"{_intent().transition_id}.{suffix}.json"
    outcome.write_text(content, encoding="utf-8")
    outcome.chmod(0o600)
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=1)

    with pytest.raises(error_type, match=match):
        await actuator.apply(_intent())

    assert list(inbox.iterdir()) == []


@pytest.mark.parametrize("cancel", [False, True], ids=["claim-timeout", "cancel-before-claim"])
@pytest.mark.asyncio
async def test_unclaimed_host_reactor_delivery_reopens_manager_gates_for_retry(
    tmp_path: Path,
    mocker: MockerFixture,
    *,
    cancel: bool,
) -> None:
    mocker.patch("lychd.system.services.runtime._ACK_POLL_SECONDS", 0.001)
    inbox, journal = _secure_reactor_dirs(tmp_path)
    scenario = build_capability_scenario(active={"a"})
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=1 if cancel else 0.001)
    scenario.manager._actuator = actuator
    published = asyncio.Event()
    write_atomic = actuator._write_atomic

    def record_publication(intent: TransitionIntent) -> None:
        write_atomic(intent)
        published.set()

    mocker.patch.object(actuator, "_write_atomic", side_effect=record_publication)

    for _attempt in range(2):
        if cancel:
            published.clear()
            transition = asyncio.create_task(scenario.manager.request_transition("b:chat:b-model", 100))
            await asyncio.wait_for(published.wait(), timeout=1)
            transition.cancel()
            with pytest.raises(asyncio.CancelledError):
                await transition
        else:
            with pytest.raises(RuntimePreconditionError, match="did not claim"):
                await scenario.manager.request_transition("b:chat:b-model", 100)

        assert list(inbox.iterdir()) == []
        assert list(journal.iterdir()) == []
        assert scenario.world.active == {"a"}
        assert scenario.manager.containment_reason is None
        assert not scenario.broker.paused
        assert scenario.leases.admission("a") is AnimatorAdmission.OPEN
        assert scenario.leases.admission("b") is AnimatorAdmission.OPEN


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


@pytest.mark.parametrize("cancellations", [1, 2])
@pytest.mark.asyncio
async def test_host_reactor_cancellation_waits_for_claimed_terminal_record(
    tmp_path: Path,
    mocker: MockerFixture,
    cancellations: int,
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
    try:
        for _ in range(cancellations):
            apply_task.cancel()
            await asyncio.sleep(0.01)
            assert not apply_task.done()
    finally:
        processing.replace(completed)
    with pytest.raises(asyncio.CancelledError) as cancelled:
        await apply_task
    assert type(cancelled.value) is asyncio.CancelledError  # Claimed completion is not a no-effect receipt.


@pytest.mark.parametrize("cancellations", [1, 2])
@pytest.mark.asyncio
async def test_host_reactor_cancellation_fences_inflight_atomic_publish(
    tmp_path: Path,
    mocker: MockerFixture,
    cancellations: int,
) -> None:
    inbox, journal = _secure_reactor_dirs(tmp_path)
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=1)
    original_write = actuator._write_atomic
    started = asyncio.Event()
    release = asyncio.Event()

    async def controlled_offload(function: object, /, *args: object, **kwargs: object) -> object:
        if function == original_write:
            started.set()
            await release.wait()
        return function(*args, **kwargs)  # type: ignore[operator]

    mocker.patch("lychd.system.services.runtime.asyncio.to_thread", side_effect=controlled_offload)
    apply_task = asyncio.create_task(actuator.apply(_intent()))
    await asyncio.wait_for(started.wait(), timeout=1)

    try:
        for _ in range(cancellations):
            apply_task.cancel()
            await asyncio.sleep(0.01)
            assert not apply_task.done()
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await apply_task

    assert not (inbox / f"{_intent().transition_id}.json").exists()
    assert list(journal.iterdir()) == []


@pytest.mark.parametrize("retraction_fails", [False, True], ids=["durable-retraction", "uncertain-retraction"])
@pytest.mark.asyncio
async def test_post_link_failure_reopens_manager_only_after_durable_retraction(
    tmp_path: Path,
    mocker: MockerFixture,
    *,
    retraction_fails: bool,
) -> None:
    inbox, journal = _secure_reactor_dirs(tmp_path)
    scenario = build_capability_scenario(active={"a"})
    scenario.manager._actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=1)
    fsync_calls = 0
    publication_error = OSError("publication durability failed")
    retraction_error = OSError("retraction durability failed")

    def fail_directory_fsync(_descriptor: int) -> None:
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 2:
            raise publication_error
        if fsync_calls == 3 and retraction_fails:
            raise retraction_error

    mocker.patch("lychd.system.services.runtime.os.fsync", side_effect=fail_directory_fsync)

    if retraction_fails:
        with pytest.raises(OSError, match="retraction durability failed") as failure:
            await scenario.manager.request_transition("b:chat:b-model", 100)
        assert failure.value is retraction_error
        assert scenario.manager.containment_reason is not None
    else:
        with pytest.raises(RuntimePreconditionError, match="retracted before host claim") as declined:
            await scenario.manager.request_transition("b:chat:b-model", 100)
        assert declined.value.__cause__ is publication_error
        assert scenario.manager.containment_reason is None

    assert fsync_calls == 3  # payload, failed publish-dir sync, retraction-dir sync
    assert list(inbox.iterdir()) == []
    assert list(journal.iterdir()) == []
    assert scenario.world.active == {"a"}
    assert scenario.broker.paused is retraction_fails
    admission = AnimatorAdmission.DRAINING if retraction_fails else AnimatorAdmission.OPEN
    assert scenario.leases.admission("a") is admission
    assert scenario.leases.admission("b") is admission


@pytest.mark.asyncio
async def test_cancellation_during_post_link_retraction_preserves_no_effect_proof(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    inbox, journal = _secure_reactor_dirs(tmp_path)
    scenario = build_capability_scenario(active={"a"})
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=1)
    scenario.manager._actuator = actuator
    retracting = asyncio.Event()
    release_retraction = asyncio.Event()
    fsync = os.fsync
    fsync_calls = 0

    def fail_publication_sync(descriptor: int) -> None:
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 2:
            message = "publication durability failed"
            raise OSError(message)
        fsync(descriptor)

    async def controlled_offload(function: object, /, *args: object, **kwargs: object) -> object:
        if function == actuator._cancel_pending:
            retracting.set()
            await release_retraction.wait()
        return function(*args, **kwargs)  # type: ignore[operator]

    mocker.patch("lychd.system.services.runtime.os.fsync", side_effect=fail_publication_sync)
    mocker.patch("lychd.system.services.runtime.asyncio.to_thread", side_effect=controlled_offload)
    transition = asyncio.create_task(scenario.manager.request_transition("b:chat:b-model", 100))
    await asyncio.wait_for(retracting.wait(), timeout=1)
    try:
        for _ in range(2):
            transition.cancel()
            await asyncio.sleep(0)
            assert not transition.done()
            assert scenario.broker.paused
    finally:
        release_retraction.set()
    with pytest.raises(RuntimeCancellationNoEffectError, match="retracted before host claim"):
        await transition

    assert fsync_calls == 3
    assert list(inbox.iterdir()) == []
    assert list(journal.iterdir()) == []
    assert scenario.world.active == {"a"}
    assert scenario.manager.containment_reason is None
    assert not scenario.broker.paused
    assert scenario.leases.admission("a") is AnimatorAdmission.OPEN
    assert scenario.leases.admission("b") is AnimatorAdmission.OPEN


@pytest.mark.parametrize("retraction_fails", [False, True], ids=["durable-retraction", "uncertain-retraction"])
@pytest.mark.asyncio
async def test_claim_timeout_withdrawal_retains_outcome_through_cancellation(  # noqa: PLR0915 - preserve the full withdrawal and manager outcome oracle
    tmp_path: Path,
    mocker: MockerFixture,
    *,
    retraction_fails: bool,
) -> None:
    inbox, journal = _secure_reactor_dirs(tmp_path)
    scenario = build_capability_scenario(active={"a"})
    actuator = HostReactorRuntimeActuator(inbox, journal, ack_timeout_s=0.001)
    scenario.manager._actuator = actuator
    retracting = asyncio.Event()
    release_receipt = asyncio.Event()
    transition_id = ""
    fsync = os.fsync
    fsync_calls = 0
    retraction_error = OSError("retraction durability failed")

    def sync_directory(descriptor: int) -> None:
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 3 and retraction_fails:
            raise retraction_error
        fsync(descriptor)

    async def controlled_offload(function: object, /, *args: object, **kwargs: object) -> object:
        nonlocal transition_id
        if function != actuator._cancel_pending:
            return function(*args, **kwargs)  # type: ignore[operator]
        transition_id = str(args[0])
        outcome: object = None
        failure: OSError | None = None
        try:
            outcome = actuator._cancel_pending(transition_id)
        except OSError as exc:
            failure = exc
        # The offloaded unlink/fsync has finished, but the caller has not yet
        # received its outcome. Cancelling that await cannot erase the receipt.
        retracting.set()
        await release_receipt.wait()
        if failure is not None:
            raise failure
        return outcome

    mocker.patch("lychd.system.services.runtime._ACK_POLL_SECONDS", 0.001)
    mocker.patch("lychd.system.services.runtime.os.fsync", side_effect=sync_directory)
    mocker.patch("lychd.system.services.runtime.asyncio.to_thread", side_effect=controlled_offload)
    transition = asyncio.create_task(scenario.manager.request_transition("b:chat:b-model", 100))
    try:
        await asyncio.wait_for(retracting.wait(), timeout=1)
        for _ in range(2):
            transition.cancel()
            await asyncio.sleep(0)
            assert not transition.done()
            assert scenario.broker.paused
        release_receipt.set()
        done, _ = await asyncio.wait({transition}, timeout=1)
        assert transition in done, "Withdrawal outcome was lost; waiting for a journal that cannot arrive."
        if retraction_fails:
            with pytest.raises(OSError, match="retraction durability failed") as failure:
                await transition
            assert failure.value is retraction_error
            assert scenario.manager.containment_reason is not None
        else:
            with pytest.raises(RuntimeCancellationNoEffectError, match="retracted before host claim"):
                await transition
            assert scenario.manager.containment_reason is None
    finally:
        release_receipt.set()
        if not transition.done():
            # Teardown also settles the pre-fix negative control's stranded waiter.
            (journal / f"{transition_id}.contained.json").touch(mode=0o600)
            await asyncio.gather(transition, return_exceptions=True)

    assert fsync_calls == 3
    assert list(inbox.iterdir()) == []
    assert list(journal.iterdir()) == []
    assert scenario.world.active == {"a"}
    assert scenario.broker.paused is retraction_fails
    admission = AnimatorAdmission.DRAINING if retraction_fails else AnimatorAdmission.OPEN
    assert scenario.leases.admission("a") is admission
    assert scenario.leases.admission("b") is admission


@pytest.mark.parametrize("cancellations", [0, 2])
@pytest.mark.asyncio
async def test_host_reactor_post_link_failure_waits_for_concurrent_claim(
    tmp_path: Path,
    mocker: MockerFixture,
    cancellations: int,
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

    try:
        for _ in range(cancellations):
            apply_task.cancel()
            await asyncio.sleep(0.01)
            assert not apply_task.done()
    finally:
        processing.replace(completed)
    if cancellations:
        with pytest.raises(asyncio.CancelledError) as cancelled:
            await apply_task
        assert type(cancelled.value) is asyncio.CancelledError
    else:
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


@pytest.mark.parametrize("recover", [False, True], ids=["forward-failure", "crash-recovery"])
@pytest.mark.asyncio
async def test_systemd_compensation_requires_settled_jobs_before_restoration(*, recover: bool) -> None:
    actuator = _observing_actuator("chat", "vision")
    prior = _ObservedRuntimeWorld(("chat",), ("chat",))
    partial = _ObservedRuntimeWorld(("vision",), ())
    actuator._observe_runtime_world = AsyncMock(side_effect=[partial, prior] if recover else [prior, partial, prior])
    actuator._run_systemctl = AsyncMock(return_value=1)
    unsettled = RuntimeError("compensation jobs still pending")
    actuator._await_relevant_jobs_quiescent = AsyncMock(side_effect=[None, unsettled])
    operation = actuator.recover if recover else actuator.apply

    with pytest.raises(RuntimeError, match="compensation jobs still pending") as caught:
        await operation(_intent())

    assert caught.value is unsettled


@pytest.mark.asyncio
async def test_systemd_actuator_removes_failed_coexisting_launch_during_compensation() -> None:
    actuator = _observing_actuator("old", "vision")
    intent = TransitionIntent(
        transition_id="2" * 32,
        config_generation="sha256:" + "3" * 64,
        target_animator="vision",
        target_capability_key="vision:default",
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
        target_capability_key="vision:default",
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
    )

    world = await actuator._observe_runtime_world()

    assert world == _ObservedRuntimeWorld(("chat",), ("chat",))
    assert subprocess.call_args_list == [
        call("/usr/bin/systemctl", "--user", "is-active", "--quiet", "lychd-animator-chat.target"),
        call("/usr/bin/systemctl", "--user", "is-active", "--quiet", "lychd-chat.service"),
        call("/usr/bin/systemctl", "--user", "is-active", "--quiet", "lychd-animator-vision.target"),
        call("/usr/bin/systemctl", "--user", "is-active", "--quiet", "lychd-vision.service"),
    ]
