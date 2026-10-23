"""Held control phases preserve one identity, release custody and finite admission."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Any

import pytest

from lychd.cli.companion_view import format_companion_event
from lychd.system.services.companion_control import CompanionControl, CompanionControlError
from tests.unit.system.services.test_companion_control import Owner, encode, owner, profile


@asynccontextmanager
async def held_owner(*, max_attempts: int = 128) -> AsyncGenerator[Owner]:
    async with owner(max_attempts=max_attempts) as fake:
        await fake.control.aclose()
        fake.control = CompanionControl(
            profile(),
            expires_at_ms=fake.now_ms + 60_000,
            context=lambda: fake.current,
            record=fake.record,
            stop=fake.stop,
            max_attempts=max_attempts,
            hold_seconds=15,
            clock=lambda: fake.now_ms / 1000,
        )
        yield fake


def release(fake: Owner, original: dict[str, Any], **changes: Any) -> bytes:
    return encode(
        {
            **original,
            "released_at_ms": fake.now_ms,
            "release_before_ms": min(fake.now_ms + 3000, original["expires_at_ms"]),
            **changes,
        }
    )


@pytest.mark.parametrize("maximum", [0, 16, True, 1.5])
def test_hold_duration_is_explicit_and_bounded(maximum: Any) -> None:
    fake = Owner()
    with pytest.raises(CompanionControlError):
        CompanionControl(
            profile(),
            expires_at_ms=1,
            context=lambda: fake.current,
            record=fake.record,
            stop=fake.stop,
            hold_seconds=maximum,
        )


@pytest.mark.asyncio
async def test_old_profile_does_not_silently_enable_longer_capture() -> None:
    async with owner() as fake:
        for path in ("/v1/hold", "/v1/release"):
            with pytest.raises(CompanionControlError) as caught:
                fake.dispatch(path, encode(fake.record_document()))
            assert caught.value.status == 409
        assert not fake.records
        assert fake.control.profile.record_seconds == 3


@pytest.mark.asyncio
async def test_owned_release_after_start_window_preserves_identity_and_does_not_reenter_capture() -> None:
    async with held_owner(max_attempts=1) as fake:
        original = fake.record_document()
        status, view = fake.dispatch("/v1/hold", encode(original))
        assert status == 202
        assert view["operation"] == "record"
        admitted, captured = fake.records[0]
        assert admitted.request_id == original["request_id"]
        assert admitted.hold_seconds == 15
        assert admitted.released is not None
        assert not admitted.released.is_set()
        assert captured.target_id == fake.current.target_id
        fake.now_ms += 4000
        fake.control.seal()
        fake.current = replace(fake.current, target_id=None)  # Original target stays with the voice owner.
        raw = release(fake, original)
        assert fake.dispatch("/v1/release", raw)[0] == 202
        assert admitted.released.is_set()
        assert len(fake.records) == 1
        fake.now_ms += 20_000
        assert fake.dispatch("/v1/release", raw)[0] == 200
        with pytest.raises(CompanionControlError) as changed:
            fake.dispatch("/v1/release", raw + b" ")
        assert changed.value.status == 409
        assert len(fake.records) == 1


@pytest.mark.asyncio
async def test_release_first_tombstone_cannot_be_evicted_or_start_delayed_capture() -> None:
    async with held_owner(max_attempts=1) as fake:
        original = fake.record_document()
        raw = release(fake, original)
        status, view = fake.dispatch("/v1/release", raw)
        assert status == 200
        assert view["status"] == "refused"
        assert not fake.records
        assert fake.dispatch("/v1/release", raw) == (200, view)
        with pytest.raises(CompanionControlError) as late:
            fake.dispatch("/v1/hold", encode(original))
        assert late.value.status == 409
        with pytest.raises(CompanionControlError) as full:
            fake.dispatch("/v1/release", release(fake, fake.record_document(101)))
        assert full.value.status == 429
        assert not fake.records
        assert fake.dispatch("/v1/stop", encode(fake.stop_document()))[0] == 202


@pytest.mark.parametrize("changed", ["context_id", "generation", "expires_at_ms", "created_at_ms"])
@pytest.mark.asyncio
async def test_release_cannot_replace_original_envelope(changed: str) -> None:
    async with held_owner() as fake:
        original = fake.record_document()
        fake.dispatch("/v1/hold", encode(original))
        changed_value = "f" * 64 if changed == "context_id" else original[changed] + 1
        with pytest.raises(CompanionControlError):
            fake.dispatch("/v1/release", release(fake, original, **{changed: changed_value}))
        assert fake.records[0][0].released is not None
        assert not fake.records[0][0].released.is_set()


@pytest.mark.parametrize("failure", ["late_forwarding", "expired_instruction", "future_release", "after_stop"])
@pytest.mark.asyncio
async def test_late_or_stopped_release_never_finishes_audio(failure: str) -> None:
    async with held_owner() as fake:
        original = fake.record_document()
        fake.dispatch("/v1/hold", encode(original))
        raw = release(fake, original)
        if failure == "late_forwarding":
            fake.now_ms += 3000
        elif failure == "expired_instruction":
            fake.now_ms = original["expires_at_ms"]
            raw = release(fake, original)
        elif failure == "future_release":
            raw = release(fake, original, released_at_ms=fake.now_ms + 201, release_before_ms=fake.now_ms + 3201)
        else:
            fake.dispatch("/v1/stop", encode(fake.stop_document()))
        with pytest.raises(CompanionControlError):
            fake.dispatch("/v1/release", raw)
        assert fake.records[0][0].released is not None
        assert not fake.records[0][0].released.is_set()


@pytest.mark.asyncio
async def test_fixed_capture_is_not_releasable_as_a_hold() -> None:
    async with held_owner() as fake:
        original = fake.record_document()
        fake.dispatch("/v1/record", encode(original))
        assert fake.records[0][0].released is None
        with pytest.raises(CompanionControlError):
            fake.dispatch("/v1/release", release(fake, original))


@pytest.mark.parametrize("language", ["sk", "cs", "en"])
@pytest.mark.parametrize("phase", ["recording", "finishing"])
def test_held_audio_status_is_localized_without_inventing_game_result(language: Any, phase: str) -> None:
    line = format_companion_event(
        {"kind": "voice_stage", "request_id": "held", "source": "microphone", "phase": phase}, language=language
    )
    assert line is not None
    assert "unknown" not in line
    assert "neznám" not in line
    assert "Run" not in line
    assert "applied" not in line
