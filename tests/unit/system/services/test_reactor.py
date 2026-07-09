from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import pytest

from lychd.domain.orchestration.actuator import (
    TransitionIntent,
    build_compensation_intent,
    capability_config_generation,
)
from lychd.system.services.reactor import HostReactor, render_reactor_path_unit, render_reactor_service_unit

if TYPE_CHECKING:
    from pathlib import Path


class _Spec:
    is_dynamic = False

    def __init__(self, animator_name: str = "local") -> None:
        self.animator_name = animator_name
        self.key = f"chat:{animator_name}:model"

    def model_dump(self, *, mode: str) -> dict[str, str]:
        assert mode == "json"
        return {"key": self.key, "animator_name": self.animator_name}


def _registry() -> Any:
    runes = {
        "local": SimpleNamespace(
            service_name="lychd-local",
            concurrency=SimpleNamespace(dedicated=True, persistent_resident=False),
        )
    }
    return SimpleNamespace(
        list_capabilities=lambda: [_Spec()],
        get_soulstone_rune=runes.get,
    )


def _swap_registry() -> Any:
    names = ("local", "old", "other")
    runes = {
        name: SimpleNamespace(
            service_name=f"lychd-{name}",
            concurrency=SimpleNamespace(dedicated=True, persistent_resident=False),
        )
        for name in names
    }
    return SimpleNamespace(
        list_capabilities=lambda: [_Spec(name) for name in names],
        get_soulstone_rune=runes.get,
    )


def _intent(registry: Any) -> TransitionIntent:
    return TransitionIntent(
        transition_id="a" * 32,
        config_generation=capability_config_generation(registry),
        target_animator="local",
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


@pytest.mark.asyncio
async def test_reactor_claims_applies_and_journals_once(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    intent = _intent(registry)
    pending = inbox / f"{intent.transition_id}.json"
    _write_intent(pending, intent)
    actuator = SimpleNamespace(apply=AsyncMock())
    reactor = HostReactor(registry, inbox_dir=inbox, journal_dir=journal, actuator=actuator)  # type: ignore[arg-type]

    assert await reactor.consume_all() == 1
    actuator.apply.assert_awaited_once_with(intent)
    assert not pending.exists()
    assert (journal / f"{intent.transition_id}.completed.json").is_file()

    # A replay with the same delivery identity is retired without a second effect.
    _write_intent(pending, intent)
    assert await reactor.consume_all() == 0
    actuator.apply.assert_awaited_once()
    assert not pending.exists()


@pytest.mark.asyncio
async def test_reactor_recovers_preexisting_processing_record(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    intent = _intent(registry)
    processing = journal / f"{intent.transition_id}.processing.json"
    _write_intent(processing, intent)
    actuator = SimpleNamespace(apply=AsyncMock(), recover=AsyncMock())
    reactor = HostReactor(registry, inbox_dir=inbox, journal_dir=journal, actuator=actuator)  # type: ignore[arg-type]

    assert await reactor.consume_all() == 1

    actuator.recover.assert_awaited_once_with(intent)
    actuator.apply.assert_not_awaited()
    assert not processing.exists()
    assert (journal / f"{intent.transition_id}.completed.json").is_file()


@pytest.mark.asyncio
async def test_reactor_accepts_exact_inverse_of_completed_forward(tmp_path: Path) -> None:
    registry = _swap_registry()
    inbox, journal = _secure_dirs(tmp_path)
    forward = TransitionIntent(
        transition_id="f" * 32,
        config_generation=capability_config_generation(registry),
        target_animator="local",
        evict_animators=("old",),
        launch_animators=("local",),
        expected_active_animators=("old",),
    )
    original_record = journal / f"{forward.transition_id}.completed.json"
    _write_intent(original_record, forward)
    compensation = build_compensation_intent(forward).model_copy(update={"transition_id": "d" * 32})
    pending = inbox / f"{compensation.transition_id}.json"
    _write_intent(pending, compensation)
    actuator = SimpleNamespace(apply=AsyncMock(), recover=AsyncMock())
    reactor = HostReactor(registry, inbox_dir=inbox, journal_dir=journal, actuator=actuator)  # type: ignore[arg-type]

    assert await reactor.consume_all() == 1

    actuator.recover.assert_awaited_once_with(compensation)
    actuator.apply.assert_not_awaited()
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
    actuator = SimpleNamespace(apply=AsyncMock(), recover=AsyncMock())
    reactor = HostReactor(registry, inbox_dir=inbox, journal_dir=journal, actuator=actuator)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="does not exactly invert"):
        await reactor.consume_all()

    actuator.recover.assert_not_awaited()
    actuator.apply.assert_not_awaited()
    assert original_record.is_file()
    assert (journal / f"{forged.transition_id}.declined.json").is_file()


@pytest.mark.asyncio
async def test_reactor_rejects_stale_config_and_retires_live_file(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    intent = _intent(registry).model_copy(update={"config_generation": "sha256:" + "f" * 64})
    pending = inbox / f"{intent.transition_id}.json"
    _write_intent(pending, intent)
    actuator = SimpleNamespace(apply=AsyncMock())
    reactor = HostReactor(registry, inbox_dir=inbox, journal_dir=journal, actuator=actuator)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="stale config generation"):
        await reactor.consume_all()

    actuator.apply.assert_not_awaited()
    assert not pending.exists()
    assert (journal / f"{intent.transition_id}.declined.json").is_file()


@pytest.mark.asyncio
async def test_reactor_rejects_unsafe_directory_mode(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    inbox.chmod(0o755)
    reactor = HostReactor(registry, inbox_dir=inbox, journal_dir=journal)

    with pytest.raises(RuntimeError, match="mode 0o700"):
        await reactor.consume_all()


@pytest.mark.asyncio
async def test_reactor_recomputes_policy_before_host_effect(tmp_path: Path) -> None:
    specs = [_Spec("old"), _Spec("local")]
    runes = {
        name: SimpleNamespace(
            service_name=f"lychd-{name}",
            concurrency=SimpleNamespace(dedicated=True, persistent_resident=False),
        )
        for name in ("old", "local")
    }
    registry = SimpleNamespace(list_capabilities=lambda: specs, get_soulstone_rune=runes.get)
    inbox, journal = _secure_dirs(tmp_path)
    intent = TransitionIntent(
        transition_id="b" * 32,
        config_generation=capability_config_generation(registry),  # type: ignore[arg-type]
        target_animator="local",
        launch_animators=("local",),
        expected_active_animators=("old",),
    )
    pending = inbox / f"{intent.transition_id}.json"
    _write_intent(pending, intent)
    actuator = SimpleNamespace(apply=AsyncMock())
    reactor = HostReactor(registry, inbox_dir=inbox, journal_dir=journal, actuator=actuator)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="violates policy"):
        await reactor.consume_all()

    actuator.apply.assert_not_awaited()
    assert not pending.exists()
    marker = journal / f"{intent.transition_id}.declined.json"
    assert json.loads(marker.read_text(encoding="utf-8"))["transition_id"] == intent.transition_id


@pytest.mark.asyncio
async def test_reactor_discards_oversized_untrusted_payload(tmp_path: Path) -> None:
    registry = _registry()
    inbox, journal = _secure_dirs(tmp_path)
    pending = inbox / f"{'c' * 32}.json"
    pending.write_bytes(b"x" * (64 * 1024 + 1))
    pending.chmod(0o600)
    reactor = HostReactor(
        registry,
        inbox_dir=inbox,
        journal_dir=journal,
        actuator=SimpleNamespace(apply=AsyncMock()),  # type: ignore[arg-type]
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
