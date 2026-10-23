"""Local control admission and projection, with no listener or physical effect ports."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import asdict, replace
from typing import Any
from uuid import UUID

import pytest

from lychd.compositions.blockworld.companion import CompanionResult
from lychd.system.services.companion_control import (
    CompanionControl,
    CompanionControlError,
    ControlContext,
    ControlProfile,
    RecordGesture,
    load_control_profile,
)


def identity(number: int) -> str:
    return str(UUID(int=number))


def profile() -> ControlProfile:
    return ControlProfile(
        protocol=1,
        endpoint="http://127.0.0.1:18186",
        token="ab" * 32,
        server_address="127.0.0.1:25572",
        player_id=identity(1),
        record_seconds=3,
    )


def encode(document: dict[str, Any]) -> bytes:
    return json.dumps(document, separators=(",", ":")).encode()


class Owner:
    """Synchronous console fence plus separately released, test-owned settlements."""

    def __init__(self, *, max_attempts: int = 128) -> None:
        self.now_ms = 1_000_000
        self.current = ControlContext(
            generation=7,
            target_id=identity(2),
            instruction_timeout_ms=10_000,
            can_record=True,
            stopping=False,
            audio_blocked=False,
            voice_request_id=None,
            voice_phase=None,
        )
        self.records: list[tuple[RecordGesture, ControlContext]] = []
        self.record_tasks: list[asyncio.Task[None]] = []
        self.stop_tasks: list[asyncio.Task[CompanionResult]] = []
        self.stop_ids: list[str] = []
        self.capture_release = asyncio.Event()
        self.stop_release = asyncio.Event()
        self.record_refuses = False
        self.stop_mode = "known"
        self.control = CompanionControl(
            profile(),
            expires_at_ms=self.now_ms + 60_000,
            context=lambda: self.current,
            record=self.record,
            stop=self.stop,
            max_attempts=max_attempts,
            clock=lambda: self.now_ms / 1000,
        )

    def record(self, gesture: RecordGesture, fence: ControlContext) -> asyncio.Task[None]:
        self.records.append((gesture, fence))
        if self.record_refuses:
            msg = "synthetic private recorder diagnostic"
            raise RuntimeError(msg)
        self.current = replace(
            self.current, can_record=False, voice_request_id=gesture.request_id, voice_phase="recording_pending"
        )

        async def capture() -> None:
            await self.capture_release.wait()

        task = asyncio.create_task(capture())
        self.record_tasks.append(task)
        return task

    def stop(self) -> asyncio.Task[CompanionResult]:
        # These observations must already hold when the dispatch call returns.
        self.current = replace(
            self.current, generation=self.current.generation + 1, can_record=False, stopping=True, audio_blocked=True
        )
        for task in self.record_tasks:
            if not task.done():
                task.cancel()
        server_id = identity(10_000 + len(self.stop_ids))
        self.stop_ids.append(server_id)
        if self.stop_mode == "raise":
            msg = "synthetic private retirement diagnostic"
            raise RuntimeError(msg)

        async def settle() -> CompanionResult:
            await self.stop_release.wait()
            if self.stop_mode == "failed":
                msg = "synthetic private settlement diagnostic"
                raise RuntimeError(msg)
            return CompanionResult(
                request_id=server_id,
                kind="unknown" if self.stop_mode == "unknown" else "applied",
                detail="synthetic private native detail",
            )

        task = asyncio.create_task(settle())
        self.stop_tasks.append(task)
        return task

    def record_document(self, number: int = 100, **changes: Any) -> dict[str, Any]:
        state = self.control.state()
        return {
            "protocol": 1,
            "session_id": state["session_id"],
            "request_id": identity(number),
            "context_id": state["context_id"],
            "generation": state["generation"],
            "created_at_ms": self.now_ms,
            "admit_before_ms": self.now_ms + 3000,
            "expires_at_ms": self.now_ms + state["instruction_timeout_ms"],
            **changes,
        }

    def stop_document(self, number: int = 200, **changes: Any) -> dict[str, Any]:
        return {
            "protocol": 1,
            "session_id": self.control.session_id,
            "request_id": identity(number),
            "created_at_ms": self.now_ms,
            "admit_before_ms": self.now_ms + 3000,
            **changes,
        }

    def dispatch(
        self, path: str, raw: bytes = b"", *, method: str = "POST", fence: ControlContext | None = None
    ) -> tuple[int, dict[str, Any]]:
        # Exercise admission without a socket, HTTP task, or alternate effect owner.
        return self.control._dispatch(  # pyright: ignore[reportPrivateUsage]
            method, path, raw, self.current if fence is None else fence
        )

    async def settle_captures(self) -> None:
        self.capture_release.set()
        await asyncio.gather(*self.record_tasks, return_exceptions=True)
        await asyncio.sleep(0)
        self.current = replace(self.current, can_record=True, voice_request_id=None, voice_phase=None)

    async def settle_stops(self) -> None:
        self.stop_release.set()
        await asyncio.gather(*self.stop_tasks, return_exceptions=True)
        await asyncio.sleep(0)
        self.current = replace(self.current, can_record=True, stopping=False, audio_blocked=False)

    async def aclose(self) -> None:
        self.capture_release.set()
        self.stop_release.set()
        await asyncio.gather(*self.record_tasks, *self.stop_tasks, return_exceptions=True)
        await asyncio.sleep(0)
        await self.control.aclose()
        assert all(task.done() for task in [*self.record_tasks, *self.stop_tasks])


@asynccontextmanager
async def owner(*, max_attempts: int = 128) -> AsyncGenerator[Owner]:
    fake = Owner(max_attempts=max_attempts)
    try:
        yield fake
    finally:
        await fake.aclose()


def assert_refused(fake: Owner, path: str, raw: bytes, status: int, *, fence: ControlContext | None = None) -> None:
    with pytest.raises(CompanionControlError) as refusal:
        fake.dispatch(path, raw, fence=fence)
    assert refusal.value.status == status
    assert str(refusal.value) == "Local companion control refused."


def test_profile_load_and_direct_construction_share_exact_private_shape() -> None:
    expected = profile()
    loaded = load_control_profile(encode(asdict(expected)))
    assert loaded == expected
    assert loaded.port == 18186
    assert expected.token not in repr(expected)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("protocol", True),
        ("protocol", 2),
        ("endpoint", "http://localhost:18186"),
        ("endpoint", "http://127.0.0.1:0"),
        ("endpoint", "http://127.0.0.1:65536"),
        ("endpoint", "http://127.0.0.1:18186/path"),
        ("endpoint", "http://127.0.0.1:18186?secret=private-synthetic"),
        ("endpoint", "http://private-synthetic@127.0.0.1:18186"),
        ("endpoint", "http://[::1]:18186"),
        ("token", "AB" * 32),
        ("token", "private-synthetic"),
        ("server_address", "private-synthetic\n"),
        ("server_address", "private synthetic"),
        ("server_address", "ž"),
        ("server_address", "x" * 256),
        ("player_id", "private-synthetic"),
        ("record_seconds", True),
        ("record_seconds", 0),
        ("record_seconds", 16),
    ],
)
def test_profile_rejects_unsafe_or_coerced_values_without_echo(field: str, value: Any) -> None:
    document = {**asdict(profile()), field: value}
    for construct in (lambda: ControlProfile(**document), lambda: load_control_profile(encode(document))):
        with pytest.raises(ValueError, match=r".+") as refusal:
            construct()
        assert "private-synthetic" not in str(refusal.value)
        assert profile().token not in str(refusal.value)


@pytest.mark.parametrize(
    "raw",
    [b"[]", b"null", b"{", b"{}", b'{"protocol":1,"protocol":1}', b" " * 4097],
)
def test_profile_rejects_non_object_duplicate_missing_and_oversize_documents(raw: bytes) -> None:
    with pytest.raises(CompanionControlError):
        load_control_profile(raw)


@pytest.mark.parametrize("mutation", ["extra", "missing", "boolean", "duplicate", "oversize", "identity"])
@pytest.mark.asyncio
async def test_record_envelope_has_no_text_or_coerced_identity_escape(mutation: str) -> None:
    async with owner() as fake:
        document = fake.record_document()
        if mutation == "extra":
            document["text"] = "private-synthetic recognized instruction"
        elif mutation == "missing":
            del document["expires_at_ms"]
        elif mutation == "boolean":
            document["generation"] = True
        elif mutation == "identity":
            document["request_id"] = identity(0xABC).upper()
        raw = encode(document)
        if mutation == "duplicate":
            raw = raw[:-1] + b',"protocol":1}'
        elif mutation == "oversize":
            raw += b" " * 2049
        with pytest.raises(ValueError, match=r".+") as refusal:
            fake.dispatch("/v1/record", raw)
        assert "private-synthetic" not in str(refusal.value)
        assert fake.records == []
        assert fake.stop_ids == []
        assert fake.control.state()["last_record"] is None


@pytest.mark.asyncio
async def test_record_preserves_original_identity_generation_expiry_and_target_fence() -> None:
    async with owner() as fake:
        fence = fake.current
        document = fake.record_document()
        fake.now_ms += 1500  # Executor wait consumes the original deadline; it does not renew it.
        status, operation = fake.dispatch("/v1/record", encode(document), fence=fence)
        assert status == 202
        assert operation["request_id"] == document["request_id"]
        assert operation["status"] == "pending"
        assert fake.records == [(RecordGesture(identity(100), 7, document["expires_at_ms"]), fence)]
        assert fake.records[0][1].target_id == identity(2)
        assert not fake.record_tasks[0].done()
        assert fake.stop_ids == []


@pytest.mark.asyncio
async def test_record_accepts_the_documented_future_skew_boundary_without_renewal() -> None:
    async with owner() as fake:
        document = fake.record_document(
            created_at_ms=fake.now_ms + 200,
            admit_before_ms=fake.now_ms + 3200,
            expires_at_ms=fake.now_ms + 10_200,
        )
        assert fake.dispatch("/v1/record", encode(document))[0] == 202
        assert fake.records[0][0].expires_at_ms == document["expires_at_ms"]


@pytest.mark.parametrize(
    ("context_changes", "body_changes", "advance_ms", "expected_status"),
    [
        ({"generation": 8}, {}, 0, 409),
        ({"target_id": identity(3)}, {}, 0, 409),
        ({"instruction_timeout_ms": 9000}, {}, 0, 409),
        ({}, {"context_id": "0" * 64}, 0, 409),
        ({}, {"generation": 8}, 0, 409),
        ({}, {"session_id": identity(50)}, 0, 409),
        ({}, {"created_at_ms": 1_000_201, "admit_before_ms": 1_003_201, "expires_at_ms": 1_010_201}, 0, 408),
        ({}, {"admit_before_ms": 1_003_001}, 0, 408),
        ({}, {"expires_at_ms": 1_010_001}, 0, 409),
        ({}, {}, 3000, 408),
        ({}, {}, 60_000, 408),
    ],
)
@pytest.mark.asyncio
async def test_stale_context_generation_and_original_deadlines_never_capture(
    context_changes: dict[str, Any], body_changes: dict[str, Any], advance_ms: int, expected_status: int
) -> None:
    async with owner(max_attempts=1) as fake:
        fence = fake.current
        document = fake.record_document(**body_changes)
        fake.current = replace(fake.current, **context_changes)
        fake.now_ms += advance_ms
        assert_refused(fake, "/v1/record", encode(document), expected_status, fence=fence)
        assert fake.records == []
        assert fake.stop_ids == []
        assert fake.control.operation(identity(100)) is None
        # Invalid envelopes have not silently consumed the one valid admission slot.
        fake.current, fake.now_ms = fence, 1_000_000
        assert fake.dispatch("/v1/record", encode(fake.record_document(101)))[0] == 202


@pytest.mark.asyncio
async def test_new_body_cannot_rebind_an_old_first_byte_target_or_generation_fence() -> None:
    async with owner() as fake:
        observed_first_byte = fake.current
        fake.current = replace(fake.current, generation=8, target_id=identity(3))
        current_body = encode(fake.record_document())
        assert_refused(fake, "/v1/record", current_body, 409, fence=observed_first_byte)
        assert fake.records == []
        assert fake.control.operation(identity(100)) is None


@pytest.mark.asyncio
async def test_expired_instruction_inside_short_admission_window_cannot_capture() -> None:
    async with owner() as fake:
        fake.current = replace(fake.current, instruction_timeout_ms=1000)
        document = fake.record_document()
        fence = fake.current
        fake.now_ms += 1000
        assert_refused(fake, "/v1/record", encode(document), 409, fence=fence)
        assert fake.records == []


@pytest.mark.parametrize(
    ("changes", "advance_ms", "status"),
    [
        ({"session_id": identity(50)}, 0, 409),
        ({"created_at_ms": 1_000_201, "admit_before_ms": 1_003_201}, 0, 408),
        ({"admit_before_ms": 1_003_001}, 0, 408),
        ({}, 3000, 408),
        ({}, 60_000, 408),
    ],
)
@pytest.mark.asyncio
async def test_stop_rejects_foreign_session_or_stale_gesture_before_fencing(
    changes: dict[str, Any], advance_ms: int, status: int
) -> None:
    async with owner() as fake:
        raw = encode(fake.stop_document(**changes))
        before = fake.current
        fake.now_ms += advance_ms
        assert_refused(fake, "/v1/stop", raw, status)
        assert fake.current == before
        assert fake.stop_ids == []
        assert fake.control.operation(identity(200)) is None


@pytest.mark.parametrize("busy_at", ["first_byte", "dispatch", "callback"])
@pytest.mark.asyncio
async def test_busy_and_callback_refusals_are_retained_and_consume_record_capacity(busy_at: str) -> None:
    async with owner(max_attempts=1) as fake:
        if busy_at == "first_byte":
            fake.current = replace(fake.current, can_record=False)
        fence = fake.current
        document = fake.record_document()
        fake.current = replace(fake.current, can_record=busy_at != "dispatch")
        fake.record_refuses = busy_at == "callback"
        status, refused = fake.dispatch("/v1/record", encode(document), fence=fence)
        assert (status, refused["status"]) == (409, "refused")
        assert len(fake.records) == (1 if busy_at == "callback" else 0)
        assert fake.record_tasks == []
        fake.current = replace(fake.current, can_record=True)
        fake.record_refuses = False
        assert not fake.control.state()["can_record"]
        assert_refused(fake, "/v1/record", encode(fake.record_document(101)), 429)
        assert fake.control.operation(identity(101)) is None
        fake.now_ms += 61_000
        assert fake.dispatch("/v1/record", encode(document)) == (200, refused)


@pytest.mark.asyncio
async def test_final_record_slot_is_admitted_then_fresh_identity_is_refused_without_eviction() -> None:
    async with owner(max_attempts=1) as fake:
        document = fake.record_document()
        assert fake.control.state()["can_record"]
        status, admitted = fake.dispatch("/v1/record", encode(document))
        assert (status, admitted["status"]) == (202, "pending")
        await fake.settle_captures()
        assert not fake.control.state()["can_record"]
        assert_refused(fake, "/v1/record", encode(fake.record_document(101)), 429)
        assert len(fake.records) == 1
        assert fake.control.operation(identity(100)) == admitted
        assert fake.control.operation(identity(101)) is None


@pytest.mark.asyncio
async def test_exact_duplicate_survives_expiry_and_full_capacity_but_changed_bytes_conflict() -> None:
    async with owner(max_attempts=1) as fake:
        document = fake.record_document()
        raw = encode(document)
        assert fake.dispatch("/v1/record", raw)[0] == 202
        fake.control.observe({"request_id": identity(100), "kind": "voice_stage", "phase": "transcribing"})
        retained = fake.control.operation(identity(100))
        fake.now_ms += 61_000
        fake.current = replace(fake.current, generation=20, target_id=identity(3))
        assert fake.dispatch("/v1/record", raw) == (200, retained)
        # Semantically identical JSON with different raw bytes remains a conflict.
        assert_refused(fake, "/v1/record", json.dumps(document, indent=1).encode(), 409)
        changed = {**document, "expires_at_ms": document["expires_at_ms"] + 1}
        assert_refused(fake, "/v1/record", encode(changed), 409)
        assert_refused(fake, "/v1/stop", encode(fake.stop_document(100)), 409)
        assert len(fake.records) == 1
        assert fake.stop_ids == []
        assert fake.control.operation(identity(100)) == retained


@pytest.mark.asyncio
async def test_stop_fences_and_cancels_synchronously_even_with_record_history_full() -> None:
    async with owner(max_attempts=1) as fake:
        assert fake.dispatch("/v1/record", encode(fake.record_document()))[0] == 202
        recording = fake.record_tasks[0]
        generation = fake.current.generation
        raw = encode(fake.stop_document())
        status, pending = fake.dispatch("/v1/stop", raw)
        # No await has occurred since dispatch, so a scheduled coroutine cannot satisfy this oracle.
        assert (status, pending["status"]) == (202, "pending")
        assert fake.current.generation == generation + 1
        assert fake.current.stopping
        assert fake.current.audio_blocked
        assert recording.cancelling() == 1
        assert len(fake.stop_ids) == 1
        assert len(fake.stop_tasks) == 1
        assert isinstance(fake.stop_tasks[0], asyncio.Task)
        assert not fake.stop_tasks[0].done()
        assert pending["server_stop_id"] is None
        await fake.settle_stops()
        settled = fake.control.operation(identity(200))
        assert settled is not None
        assert (settled["status"], settled["game_kind"]) == ("known", "applied")
        assert settled["server_stop_id"] == fake.stop_ids[0]
        assert settled["server_stop_id"] != identity(200)
        fake.now_ms += 61_000
        assert fake.dispatch("/v1/stop", raw) == (200, settled)
        assert_refused(fake, "/v1/stop", raw + b" ", 409)
        assert len(fake.stop_ids) == 1


@pytest.mark.asyncio
async def test_final_retained_stop_slot_seals_new_records_and_stops_without_forgetting_identity() -> None:
    async with owner() as fake:
        for number in range(63):
            assert fake.dispatch("/v1/stop", encode(fake.stop_document(200 + number)))[0] == 202
        await fake.settle_stops()
        assert fake.control.state()["can_record"]
        final_raw = encode(fake.stop_document(263))
        assert fake.dispatch("/v1/stop", final_raw)[0] == 202
        await fake.settle_stops()
        assert len(fake.stop_ids) == 64
        assert not fake.control.state()["can_record"]
        assert_refused(fake, "/v1/record", encode(fake.record_document()), 429)
        assert_refused(fake, "/v1/stop", encode(fake.stop_document(264)), 429)
        assert len(fake.stop_ids) == 64
        assert fake.records == []
        final = fake.control.operation(identity(263))
        fake.now_ms += 61_000
        assert fake.dispatch("/v1/stop", final_raw) == (200, final)
        assert_refused(fake, "/v1/stop", final_raw + b" ", 409)
        assert fake.control.operation(identity(200)) is not None


@pytest.mark.parametrize("mode", ["unknown", "failed", "cancelled", "raise"])
@pytest.mark.asyncio
async def test_unknown_failed_or_cancelled_stop_retirement_seals_fresh_control(mode: str) -> None:
    async with owner() as fake:
        fake.stop_mode = mode
        status, _ = fake.dispatch("/v1/stop", encode(fake.stop_document()))
        assert status == 202
        if mode == "cancelled":
            fake.stop_tasks[0].cancel()
        await fake.settle_stops()
        settled = fake.control.operation(identity(200))
        assert settled is not None
        assert settled["status"] == "unknown"
        assert not fake.control.state()["can_record"]
        assert_refused(fake, "/v1/record", encode(fake.record_document()), 429)
        assert fake.records == []
        assert "synthetic private" not in json.dumps(settled)


@pytest.mark.asyncio
async def test_projection_keeps_game_result_distinct_from_reply_failure_and_drops_private_payload() -> None:
    async with owner() as fake:
        assert fake.dispatch("/v1/record", encode(fake.record_document()))[0] == 202
        private = "private-synthetic transcript diagnostic profile audio"
        feedback = {"language": "en", "text": "The companion stopped."}
        fake.control.observe(
            {
                "request_id": identity(100),
                "kind": "applied",
                "feedback": feedback,
                "evidence_status": "pending",
                "transcript": private,
                "detail": private,
                "profile": asdict(profile()),
                "audio": private,
            }
        )
        feedback["text"] = private
        fake.control.observe(
            {
                "request_id": identity(100),
                "kind": "speech_failed",
                "feedback": {"language": "en", "text": private},
                "reply_status": "failed",
                "playback": "failed",
                "reply_failure": "synthesis_failed",
                "evidence_status": "failed",
                "detail": private,
            }
        )
        projected = fake.control.operation(identity(100))
        assert projected == {
            "request_id": identity(100),
            "operation": "record",
            "status": "known",
            "phase": None,
            "game_kind": "applied",
            "feedback": {"language": "en", "text": "The companion stopped."},
            "native_evidence_status": "pending",
            "reply_status": "failed",
            "playback": "failed",
            "reply_evidence_status": "failed",
            "reply_failure": "synthesis_failed",
            "server_stop_id": None,
        }
        serialized = json.dumps(fake.control.state())
        assert private not in serialized
        assert profile().token not in serialized
        assert profile().endpoint not in serialized
        assert profile().server_address not in serialized


@pytest.mark.asyncio
async def test_queries_are_copied_observations_without_expiry_admission_or_settlement_effects() -> None:
    async with owner() as fake:
        assert fake.dispatch("/v1/record", encode(fake.record_document()))[0] == 202
        fake.control.observe(
            {"request_id": identity(100), "kind": "no_action", "feedback": {"language": "sk", "text": "Hotovo."}}
        )
        original = fake.control.operation(identity(100))
        assert original is not None
        copied = fake.control.operation(identity(100))
        assert copied is not None
        copied["feedback"]["text"] = "caller mutation"
        copied["status"] = "unknown"
        state = fake.control.state()
        state["last_record"]["feedback"]["text"] = "nested caller mutation"
        state["voice"]["phase"] = "caller mutation"
        assert fake.control.operation(identity(100)) == original
        assert fake.control.state()["voice"]["phase"] == "recording_pending"
        before = (len(fake.records), len(fake.stop_ids), fake.current, fake.record_tasks[0].done())
        fake.now_ms += 61_000
        for _ in range(3):
            status, view = fake.dispatch("/v1/state", method="GET")
            assert status == 200
            assert not view["can_record"]
            assert view["last_record"] == original
            assert view["voice"]["request_id"] == identity(100)
            assert fake.dispatch(f"/v1/operations/{identity(100)}", method="GET") == (200, original)
            assert fake.dispatch(f"/v1/operations/{identity(999)}", method="GET") == (
                404,
                {"protocol": 1, "status": "not_found"},
            )
        assert before == (len(fake.records), len(fake.stop_ids), fake.current, fake.record_tasks[0].done())
        assert fake.control.operation(identity(999)) is None


@pytest.mark.asyncio
async def test_state_after_expiry_does_not_retire_pending_capture_or_claim_microphone_off() -> None:
    async with owner() as fake:
        assert fake.dispatch("/v1/record", encode(fake.record_document()))[0] == 202
        pending = fake.control.operation(identity(100))
        fake.now_ms += 61_000
        for _ in range(3):
            status, snapshot = fake.dispatch("/v1/state", method="GET")
            assert status == 200
            assert not snapshot["can_record"]
            assert snapshot["last_record"] == pending
            assert snapshot["last_record"]["status"] == "pending"
            assert snapshot["voice"] == {"request_id": identity(100), "phase": "recording_pending"}
            assert fake.control.operation(identity(100)) == pending
            assert not fake.record_tasks[0].done()
        assert len(fake.records) == 1
        assert fake.stop_ids == []


@pytest.mark.asyncio
async def test_projection_ignores_foreign_identity_invalid_stages_and_non_record_operations() -> None:
    async with owner() as fake:
        assert fake.dispatch("/v1/record", encode(fake.record_document()))[0] == 202
        record_before = fake.control.operation(identity(100))
        fake.control.observe({"request_id": identity(999), "kind": "voice_stage", "phase": "transcribing"})
        fake.control.observe({"request_id": identity(100), "kind": "voice_stage", "phase": "private transcript"})
        assert fake.control.operation(identity(100)) == record_before
        assert fake.dispatch("/v1/stop", encode(fake.stop_document()))[0] == 202
        stop_before = fake.control.operation(identity(200))
        fake.control.observe(
            {"request_id": identity(200), "kind": "applied", "feedback": {"language": "en", "text": "Foreign."}}
        )
        assert fake.control.operation(identity(200)) == stop_before
        assert fake.control.operation(identity(999)) is None
