from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import pytest

from lychd.domain.animation.schemas.concurrency import ConcurrencyIntent
from lychd.domain.orchestration.actuator import (
    RuntimeActuationRestoredError,
    TransitionIntent,
    build_compensation_intent,
    capability_config_generation,
)
from lychd.system.services.reactor import HostReactor, render_reactor_path_unit, render_reactor_service_unit

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


class _Spec:
    is_dynamic = False

    def __init__(self, animator_name: str = "local") -> None:
        self.animator_name = animator_name
        self.key = f"chat:{animator_name}:model"

    def model_dump(self, *, mode: str) -> dict[str, str]:
        assert mode == "json"
        return {"key": self.key, "animator_name": self.animator_name}


class _Actuator:
    """Typed apply/recover fake for the Host Reactor's narrow effect port."""

    def __init__(
        self,
        *,
        apply: Callable[[TransitionIntent], Awaitable[None]] | None = None,
        recover: Callable[[TransitionIntent], Awaitable[None]] | None = None,
    ) -> None:
        self.apply_mock = AsyncMock(side_effect=apply)
        self.recover_mock = AsyncMock(side_effect=recover)

    async def apply(self, intent: TransitionIntent) -> None:
        await self.apply_mock(intent)

    async def recover(self, intent: TransitionIntent) -> None:
        await self.recover_mock(intent)


@contextmanager
def _uncontended_lock() -> Iterator[None]:
    """Keep parallel unit tests isolated from the process-global host lock."""
    yield


def _host_reactor(
    registry: Any,
    *,
    inbox_dir: Path,
    journal_dir: Path,
    actuator: _Actuator,
    lock_factory: Callable[[], AbstractContextManager[object]] | None = None,
) -> HostReactor:
    """Construct a Reactor with explicit test-owned lifecycle authority."""
    return HostReactor(
        registry,
        inbox_dir=inbox_dir,
        journal_dir=journal_dir,
        actuator=actuator,
        lock_factory=lock_factory or _uncontended_lock,
    )


def _registry() -> Any:
    runes = {
        "local": SimpleNamespace(
            name="local",
            groups=[],
            service_name="lychd-local",
            concurrency=ConcurrencyIntent(),
        )
    }
    return SimpleNamespace(
        list_capabilities=lambda: [_Spec()],
        list_soulstone_runes=lambda: list(runes.values()),
        get_soulstone_rune=runes.get,
    )


def _swap_registry() -> Any:
    names = ("local", "old", "other")
    runes = {
        name: SimpleNamespace(
            name=name,
            groups=[],
            service_name=f"lychd-{name}",
            concurrency=ConcurrencyIntent(),
        )
        for name in names
    }
    return SimpleNamespace(
        list_capabilities=lambda: [_Spec(name) for name in names],
        list_soulstone_runes=lambda: list(runes.values()),
        get_soulstone_rune=runes.get,
    )


def _intent(registry: Any) -> TransitionIntent:
    return TransitionIntent(
        transition_id="a" * 32,
        config_generation=capability_config_generation(registry),
        target_animator="local",
        target_capability_key="chat:local:model",
        launch_animators=("local",),
    )


def _secure_dirs(tmp_path: Path) -> tuple[Path, Path]:
    inbox = tmp_path / "inbox"
    journal = tmp_path / "journal"
    inbox.mkdir(mode=0o700)
    journal.mkdir(mode=0o700)
    inbox.chmod(0o700)
    journal.chmod(0o700)
    return inbox, journal


def _write_intent(path: Path, intent: TransitionIntent) -> None:
    path.write_text(json.dumps(intent.model_dump(mode="json")), encoding="utf-8")
    path.chmod(0o600)


def test_reactor_threads_the_systemctl_client_budget(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    actuator_type = mocker.patch(
        "lychd.system.services.reactor.SystemdRuntimeActuator",
    )

    HostReactor(
        registry,
        inbox_dir=inbox,
        journal_dir=journal,
        systemctl_bin="/usr/bin/systemctl",
        systemctl_timeout_s=6.5,
        lock_factory=_uncontended_lock,
    )

    actuator_type.assert_called_once_with(
        registry,
        systemctl_bin="/usr/bin/systemctl",
        systemctl_timeout_s=6.5,
        observe_systemd=True,
    )


@pytest.mark.asyncio
async def test_reactor_claims_applies_and_journals_once(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    intent = _intent(registry)
    pending = inbox / f"{intent.transition_id}.json"
    _write_intent(pending, intent)
    actuator = _Actuator()
    reactor = _host_reactor(registry, inbox_dir=inbox, journal_dir=journal, actuator=actuator)

    assert await reactor.consume_all() == 1
    actuator.apply_mock.assert_awaited_once_with(intent)
    assert not pending.exists()
    assert (journal / f"{intent.transition_id}.completed.json").is_file()

    # A replay with the same delivery identity is retired without a second effect.
    _write_intent(pending, intent)
    assert await reactor.consume_all() == 0
    actuator.apply_mock.assert_awaited_once()
    assert not pending.exists()


@pytest.mark.asyncio
async def test_reactor_journals_verified_prior_world_restoration(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    intent = _intent(registry)
    _write_intent(inbox / f"{intent.transition_id}.json", intent)

    async def restore(_intent: TransitionIntent) -> None:
        message = "systemd transaction failed; prior runtime world restored"
        raise RuntimeActuationRestoredError(message)

    reactor = _host_reactor(
        registry,
        inbox_dir=inbox,
        journal_dir=journal,
        actuator=_Actuator(apply=restore),
    )

    with pytest.raises(RuntimeError, match="did not apply transition"):
        await reactor.consume_all()

    assert (journal / f"{intent.transition_id}.restored.json").is_file()
    assert not (journal / f"{intent.transition_id}.rejected.json").exists()


@pytest.mark.asyncio
async def test_reactor_holds_the_shared_lifecycle_lock_across_host_effects(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    intent = _intent(registry)
    _write_intent(inbox / f"{intent.transition_id}.json", intent)
    events: list[str] = []

    @contextmanager
    def lock() -> Iterator[None]:
        events.append("lock-enter")
        try:
            yield
        finally:
            events.append("lock-exit")

    async def apply(_intent: TransitionIntent) -> None:
        events.append("apply")

    reactor = _host_reactor(
        registry,
        inbox_dir=inbox,
        journal_dir=journal,
        actuator=_Actuator(apply=apply),
        lock_factory=lock,
    )

    assert await reactor.consume_all() == 1
    assert events == ["lock-enter", "apply", "lock-exit"]


@pytest.mark.asyncio
async def test_reactor_recovers_preexisting_processing_record(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    intent = _intent(registry)
    processing = journal / f"{intent.transition_id}.processing.json"
    _write_intent(processing, intent)
    actuator = _Actuator()
    reactor = _host_reactor(registry, inbox_dir=inbox, journal_dir=journal, actuator=actuator)

    assert await reactor.consume_all() == 1

    actuator.recover_mock.assert_awaited_once_with(intent)
    actuator.apply_mock.assert_not_awaited()
    assert not processing.exists()
    assert (journal / f"{intent.transition_id}.completed.json").is_file()


@pytest.mark.asyncio
async def test_reactor_keeps_uncertain_recovery_as_durable_processing_fence(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    intent = _intent(registry)
    processing = journal / f"{intent.transition_id}.processing.json"
    _write_intent(processing, intent)

    async def uncertain(_intent: TransitionIntent) -> None:
        message = "systemd world cannot be classified"
        raise RuntimeError(message)

    actuator = _Actuator(recover=uncertain)
    reactor = _host_reactor(registry, inbox_dir=inbox, journal_dir=journal, actuator=actuator)

    with pytest.raises(RuntimeError, match="cannot be classified"):
        await reactor.consume_all()

    assert processing.is_file()
    assert not (journal / f"{intent.transition_id}.rejected.json").exists()
    assert not (journal / f"{intent.transition_id}.contained.json").exists()


@pytest.mark.asyncio
async def test_uncertain_recovery_fences_later_pending_effects(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    recovered = _intent(registry)
    pending = recovered.model_copy(update={"transition_id": "b" * 32})
    processing_path = journal / f"{recovered.transition_id}.processing.json"
    pending_path = inbox / f"{pending.transition_id}.json"
    _write_intent(processing_path, recovered)
    _write_intent(pending_path, pending)

    async def uncertain(_intent: TransitionIntent) -> None:
        message = "systemd world cannot be classified"
        raise RuntimeError(message)

    actuator = _Actuator(recover=uncertain)
    reactor = _host_reactor(
        registry,
        inbox_dir=inbox,
        journal_dir=journal,
        actuator=actuator,
    )

    with pytest.raises(RuntimeError, match="cannot be classified"):
        await reactor.consume_all()

    actuator.recover_mock.assert_awaited_once_with(recovered)
    actuator.apply_mock.assert_not_awaited()
    assert processing_path.is_file()
    assert pending_path.is_file()


@pytest.mark.asyncio
async def test_reactor_persists_fresh_uncertain_actuation_as_containment(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    intent = _intent(registry)
    _write_intent(inbox / f"{intent.transition_id}.json", intent)

    async def uncertain(_intent: TransitionIntent) -> None:
        message = "systemd world cannot be restored"
        raise RuntimeError(message)

    reactor = _host_reactor(
        registry,
        inbox_dir=inbox,
        journal_dir=journal,
        actuator=_Actuator(apply=uncertain),
    )

    with pytest.raises(RuntimeError, match="cannot be restored"):
        await reactor.consume_all()

    assert (journal / f"{intent.transition_id}.contained.json").is_file()
    assert not (journal / f"{intent.transition_id}.rejected.json").exists()


@pytest.mark.asyncio
async def test_fresh_containment_fences_later_pending_effects(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    first = _intent(registry)
    second = first.model_copy(update={"transition_id": "b" * 32})
    _write_intent(inbox / f"{first.transition_id}.json", first)
    second_path = inbox / f"{second.transition_id}.json"
    _write_intent(second_path, second)

    async def uncertain(_intent: TransitionIntent) -> None:
        message = "systemd world cannot be restored"
        raise RuntimeError(message)

    actuator = _Actuator(apply=uncertain)
    reactor = _host_reactor(
        registry,
        inbox_dir=inbox,
        journal_dir=journal,
        actuator=actuator,
    )

    with pytest.raises(RuntimeError, match="cannot be restored"):
        await reactor.consume_all()

    actuator.apply_mock.assert_awaited_once_with(first)
    assert (journal / f"{first.transition_id}.contained.json").is_file()
    assert second_path.is_file()


@pytest.mark.asyncio
async def test_preexisting_containment_refuses_every_new_effect(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    contained = _intent(registry)
    pending = contained.model_copy(update={"transition_id": "b" * 32})
    _write_intent(journal / f"{contained.transition_id}.contained.json", contained)
    pending_path = inbox / f"{pending.transition_id}.json"
    _write_intent(pending_path, pending)
    actuator = _Actuator()
    reactor = _host_reactor(
        registry,
        inbox_dir=inbox,
        journal_dir=journal,
        actuator=actuator,
    )

    with pytest.raises(RuntimeError, match="containment is active"):
        await reactor.consume_all()

    actuator.apply_mock.assert_not_awaited()
    actuator.recover_mock.assert_not_awaited()
    assert pending_path.is_file()


@pytest.mark.asyncio
async def test_reactor_accepts_exact_inverse_of_completed_forward(tmp_path: Path) -> None:
    registry = _swap_registry()
    inbox, journal = _secure_dirs(tmp_path)
    forward = TransitionIntent(
        transition_id="f" * 32,
        config_generation=capability_config_generation(registry),
        target_animator="local",
        target_capability_key="chat:local:model",
        evict_animators=("old",),
        launch_animators=("local",),
        expected_active_animators=("old",),
    )
    original_record = journal / f"{forward.transition_id}.completed.json"
    _write_intent(original_record, forward)
    compensation = build_compensation_intent(forward).model_copy(update={"transition_id": "d" * 32})
    pending = inbox / f"{compensation.transition_id}.json"
    _write_intent(pending, compensation)
    actuator = _Actuator()
    reactor = _host_reactor(registry, inbox_dir=inbox, journal_dir=journal, actuator=actuator)

    assert await reactor.consume_all() == 1

    actuator.apply_mock.assert_awaited_once_with(compensation)
    actuator.recover_mock.assert_not_awaited()
    assert original_record.is_file()
    assert (journal / f"{compensation.transition_id}.completed.json").is_file()


@pytest.mark.asyncio
async def test_reactor_rejects_forged_compensation_and_preserves_original(tmp_path: Path) -> None:
    registry = _swap_registry()
    inbox, journal = _secure_dirs(tmp_path)
    forward = TransitionIntent(
        transition_id="e" * 32,
        config_generation=capability_config_generation(registry),
        target_animator="local",
        target_capability_key="chat:local:model",
        evict_animators=("old",),
        launch_animators=("local",),
        expected_active_animators=("old",),
    )
    original_record = journal / f"{forward.transition_id}.completed.json"
    _write_intent(original_record, forward)
    expected = build_compensation_intent(forward)
    forged = TransitionIntent.model_validate(
        {
            **expected.model_dump(mode="json"),
            "transition_id": "c" * 32,
            "launch_animators": ["other"],
        }
    )
    pending = inbox / f"{forged.transition_id}.json"
    _write_intent(pending, forged)
    actuator = _Actuator()
    reactor = _host_reactor(registry, inbox_dir=inbox, journal_dir=journal, actuator=actuator)

    with pytest.raises(RuntimeError, match="does not exactly invert"):
        await reactor.consume_all()

    actuator.recover_mock.assert_not_awaited()
    actuator.apply_mock.assert_not_awaited()
    assert original_record.is_file()
    assert (journal / f"{forged.transition_id}.declined.json").is_file()


@pytest.mark.asyncio
async def test_reactor_rejects_stale_config_and_retires_live_file(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    intent = _intent(registry).model_copy(update={"config_generation": "sha256:" + "f" * 64})
    pending = inbox / f"{intent.transition_id}.json"
    _write_intent(pending, intent)
    actuator = _Actuator()
    reactor = _host_reactor(registry, inbox_dir=inbox, journal_dir=journal, actuator=actuator)

    with pytest.raises(RuntimeError, match="stale config generation"):
        await reactor.consume_all()

    actuator.apply_mock.assert_not_awaited()
    assert not pending.exists()
    assert (journal / f"{intent.transition_id}.declined.json").is_file()


@pytest.mark.asyncio
async def test_reactor_rejects_unsafe_directory_mode(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    inbox.chmod(0o755)
    reactor = _host_reactor(
        registry,
        inbox_dir=inbox,
        journal_dir=journal,
        actuator=_Actuator(),
    )

    with pytest.raises(RuntimeError, match="mode 0o700"):
        await reactor.consume_all()


@pytest.mark.asyncio
async def test_reactor_recomputes_policy_before_host_effect(tmp_path: Path) -> None:
    specs = [_Spec("old"), _Spec("local")]
    runes = {
        name: SimpleNamespace(
            name=name,
            groups=[],
            service_name=f"lychd-{name}",
            concurrency=ConcurrencyIntent(),
        )
        for name in ("old", "local")
    }
    registry: Any = SimpleNamespace(
        list_capabilities=lambda: specs,
        list_soulstone_runes=lambda: list(runes.values()),
        get_soulstone_rune=runes.get,
    )
    inbox, journal = _secure_dirs(tmp_path)
    intent = TransitionIntent(
        transition_id="b" * 32,
        config_generation=capability_config_generation(registry),
        target_animator="local",
        target_capability_key="chat:local:model",
        launch_animators=("local",),
        expected_active_animators=("old",),
    )
    pending = inbox / f"{intent.transition_id}.json"
    _write_intent(pending, intent)
    actuator = _Actuator()
    reactor = _host_reactor(registry, inbox_dir=inbox, journal_dir=journal, actuator=actuator)

    with pytest.raises(RuntimeError, match="violates policy"):
        await reactor.consume_all()

    actuator.apply_mock.assert_not_awaited()
    assert not pending.exists()
    marker = journal / f"{intent.transition_id}.declined.json"
    assert json.loads(marker.read_text(encoding="utf-8"))["transition_id"] == intent.transition_id


@pytest.mark.asyncio
async def test_reactor_rejects_exact_capability_owned_by_another_animator(tmp_path: Path) -> None:
    registry = _swap_registry()
    inbox, journal = _secure_dirs(tmp_path)
    intent = TransitionIntent(
        transition_id="9" * 32,
        config_generation=capability_config_generation(registry),
        target_animator="local",
        target_capability_key="chat:other:model",
        launch_animators=("local",),
    )
    _write_intent(inbox / f"{intent.transition_id}.json", intent)
    actuator = _Actuator()
    reactor = _host_reactor(
        registry,
        inbox_dir=inbox,
        journal_dir=journal,
        actuator=actuator,
    )

    with pytest.raises(RuntimeError, match="belongs to animator 'other'"):
        await reactor.consume_all()

    actuator.apply_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_reactor_accepts_unambiguous_legacy_intent_without_capability_key(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    legacy = _intent(registry).model_copy(update={"target_capability_key": None})
    _write_intent(inbox / f"{legacy.transition_id}.json", legacy)
    actuator = _Actuator()
    reactor = _host_reactor(
        registry,
        inbox_dir=inbox,
        journal_dir=journal,
        actuator=actuator,
    )

    assert await reactor.consume_all() == 1
    actuator.apply_mock.assert_awaited_once_with(legacy)


@pytest.mark.asyncio
async def test_reactor_discards_oversized_untrusted_payload(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    pending = inbox / f"{'c' * 32}.json"
    pending.write_bytes(b"x" * (64 * 1024 + 1))
    pending.chmod(0o600)
    reactor = _host_reactor(
        registry,
        inbox_dir=inbox,
        journal_dir=journal,
        actuator=_Actuator(),
    )

    with pytest.raises(RuntimeError, match="exceeds"):
        await reactor.consume_all()

    assert not pending.exists()
    marker = journal / f"{'c' * 32}.rejected.json"
    assert marker.stat().st_size < 4096


def test_reactor_units_are_narrow_and_host_triggered(tmp_path: Path) -> None:
    service = render_reactor_service_unit(
        executable=tmp_path / "bin" / "lychd",
        environment={"XDG_DATA_HOME": str(tmp_path)},
    )
    path = render_reactor_path_unit(
        inbox_dir=tmp_path / "inbox",
        journal_dir=tmp_path / "journal",
    )

    assert f"ExecStart={tmp_path}/bin/lychd reactor consume" in service
    assert "Type=oneshot" in service
    assert "Restart=on-failure" in service
    assert "RestartSec=1s" in service
    assert f"PathExistsGlob={tmp_path}/inbox/*.json" in path
    assert f"PathExistsGlob={tmp_path}/journal/*.processing.json" in path
    assert "Unit=lychd-reactor.service" in path
    assert "sudo" not in service


def test_reactor_service_quotes_environment_as_one_assignment(tmp_path: Path) -> None:
    service = render_reactor_service_unit(
        executable=tmp_path / "bin" / "lychd",
        environment={"LABEL": 'two words and "quoted" ${LITERAL}'},
    )

    assert 'Environment="LABEL=two words and \\"quoted\\" ${LITERAL}"' in service


def test_reactor_service_rejects_systemd_environment_escapes(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="backslashes"):
        render_reactor_service_unit(
            executable=tmp_path / "bin" / "lychd",
            environment={"SAFE": r"value\x0aEnvironment=MALICE=1"},
        )
