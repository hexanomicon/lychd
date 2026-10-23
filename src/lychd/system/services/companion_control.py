"""Opt-in local gesture control for the explicit companion engineering console.

This adapter authenticates a trusted local client, not physical human input or
Ward identity. It never receives speech, transcripts, game commands or provider
selection. Existing console owners retain capture, native effects and retirement.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from hmac import compare_digest
from typing import Any, cast
from uuid import uuid4

from lychd.compositions.blockworld.companion import CompanionResult, canonical_uuid, strict_json
from lychd.lib.asyncio import complete_under_cancellation

MAX_CONTROL_BODY = 2048
MAX_CONTROL_HEADERS = 4096
MAX_CONTROL_RESPONSE = 8192
MAX_CONTROL_PROFILE = 4096
MAX_CONTROL_CLIENTS = 8
MAX_CONTROL_ATTEMPTS = 128
MAX_CONTROL_STOPS = 64
CONTROL_IO_SECONDS = 2.0
GESTURE_ADMISSION_MS = 3000
MAX_FUTURE_SKEW_MS = 200
MAX_PORT = 65535
MAX_SERVER_ADDRESS = 255
MAX_CAPTURE_SECONDS = 15
MAX_FEEDBACK_CHARS = 400
ASCII_SPACE = 32
ASCII_DELETE = 127


class CompanionControlError(ValueError):
    """Closed local refusal with no foreign values in its message."""

    def __init__(self, status: int = 400) -> None:
        """Retain only the fixed HTTP refusal classification."""
        super().__init__("Local companion control refused.")
        self.status = status


@dataclass(frozen=True)
class ControlProfile:
    protocol: int
    endpoint: str
    token: str = field(repr=False)
    server_address: str
    player_id: str
    record_seconds: int

    def __post_init__(self) -> None:
        """Validate the complete local profile, including direct construction."""
        if any(type(value) is not str for value in (self.endpoint, self.token, self.server_address, self.player_id)):
            raise CompanionControlError
        if type(self.protocol) is not int or self.protocol != 1:
            raise CompanionControlError
        match = re.fullmatch(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})", self.endpoint)
        if match is None or not 1 <= int(match[1]) <= MAX_PORT:
            raise CompanionControlError
        if not re.fullmatch(r"[0-9a-f]{64}", self.token):
            raise CompanionControlError
        if (
            not self.server_address
            or len(self.server_address) > MAX_SERVER_ADDRESS
            or not self.server_address.isascii()
            or any(ord(character) <= ASCII_SPACE or ord(character) == ASCII_DELETE for character in self.server_address)
        ):
            raise CompanionControlError
        canonical_uuid(self.player_id)
        if type(self.record_seconds) is not int or not 1 <= self.record_seconds <= MAX_CAPTURE_SECONDS:
            raise CompanionControlError

    @property
    def port(self) -> int:
        return int(self.endpoint.rsplit(":", 1)[1])


def _object(raw: bytes, keys: set[str], limit: int) -> dict[str, Any]:
    try:
        supplied = strict_json(raw, limit=limit)
    except (ValueError, RecursionError):
        raise CompanionControlError from None
    if type(supplied) is not dict:
        raise CompanionControlError
    document = cast("dict[str, Any]", supplied)
    if set(document) != keys:
        raise CompanionControlError
    return document


def load_control_profile(raw: bytes) -> ControlProfile:
    """Read the exact private local control shape without effectful discovery."""
    keys = {"protocol", "endpoint", "token", "server_address", "player_id", "record_seconds"}
    document = _object(raw, keys, MAX_CONTROL_PROFILE)
    if any(type(document[key]) is not str for key in keys - {"protocol", "record_seconds"}):
        raise CompanionControlError
    return ControlProfile(**document)


@dataclass(frozen=True)
class ControlContext:
    """One synchronous owner observation; target is never supplied by the client."""

    generation: int
    target_id: str | None
    instruction_timeout_ms: int
    can_record: bool
    stopping: bool
    audio_blocked: bool
    voice_request_id: str | None
    voice_phase: str | None


@dataclass(frozen=True)
class RecordGesture:
    request_id: str
    generation: int
    expires_at_ms: int
    released: asyncio.Event | None = field(default=None, repr=False, compare=False)
    hold_seconds: int | None = None


@dataclass
class _HeldRecord:
    envelope: dict[str, Any]
    released: asyncio.Event
    release_digest: str | None = None


@dataclass
class _Operation:
    digest: str
    view: dict[str, Any]


def _operation(identity: str, kind: str, digest: str) -> _Operation:
    return _Operation(
        digest,
        {
            "request_id": identity,
            "operation": kind,
            "status": "pending",
            "phase": None,
            "game_kind": None,
            "feedback": None,
            "native_evidence_status": None,
            "reply_status": None,
            "playback": None,
            "reply_evidence_status": None,
            "reply_failure": None,
            "server_stop_id": None,
        },
    )


class CompanionControl:
    """Bounded request owner; no ambient registration or alternate game queue."""

    def __init__(
        self,
        profile: ControlProfile,
        *,
        expires_at_ms: int,
        context: Callable[[], ControlContext],
        record: Callable[[RecordGesture, ControlContext], asyncio.Task[None]],
        stop: Callable[[], asyncio.Task[CompanionResult]],
        max_attempts: int = MAX_CONTROL_ATTEMPTS,
        hold_seconds: int | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Bind one finite console and its existing capture/stop ownership callbacks."""
        self.profile = ControlProfile(**asdict(profile))
        if type(max_attempts) is not int or not 1 <= max_attempts <= MAX_CONTROL_ATTEMPTS:
            raise CompanionControlError
        if hold_seconds is not None and (type(hold_seconds) is not int or not 1 <= hold_seconds <= MAX_CAPTURE_SECONDS):
            raise CompanionControlError
        self.expires_at_ms, self.context, self.record, self.stop = expires_at_ms, context, record, stop
        self.max_attempts, self.clock = max_attempts, clock
        self.hold_seconds = hold_seconds
        self.session_id = str(uuid4())
        self._profile_digest = sha256(json.dumps(asdict(self.profile), sort_keys=True).encode()).hexdigest()
        self._server: asyncio.Server | None = None
        self._handlers: set[asyncio.Task[None]] = set()
        self._writers: set[asyncio.StreamWriter] = set()
        self._settlements: set[asyncio.Task[CompanionResult]] = set()
        self._operations: dict[str, _Operation] = {}
        self._holds: dict[str, _HeldRecord] = {}
        self._record_count = self._stop_count = 0
        self._last_record: str | None = None
        self._last_stop: str | None = None
        self._closed = False
        self._sealed = False

    def _context_id(self, context: ControlContext) -> str:
        return sha256(
            json.dumps(
                [
                    self.session_id,
                    self._profile_digest,
                    context.generation,
                    context.target_id,
                    context.instruction_timeout_ms,
                ]
            ).encode()
        ).hexdigest()

    def _can_record(self, context: ControlContext) -> bool:
        return (
            not self._closed
            and not self._sealed
            and self._record_count < self.max_attempts
            and int(self.clock() * 1000) + context.instruction_timeout_ms <= self.expires_at_ms
            and context.can_record
        )

    def state(self) -> dict[str, Any]:
        """Read existing owner facts without expiring, admitting or settling work."""
        context = self.context()
        return {
            "protocol": 1,
            "session_id": self.session_id,
            "context_id": self._context_id(context),
            "generation": context.generation,
            "session_expires_at_ms": self.expires_at_ms,
            "instruction_timeout_ms": context.instruction_timeout_ms,
            "can_record": self._can_record(context),
            "stopping": context.stopping,
            "audio_blocked": context.audio_blocked,
            "voice": None
            if context.voice_request_id is None
            else {"request_id": context.voice_request_id, "phase": context.voice_phase},
            "last_record": self.operation(self._last_record),
            "last_stop": self.operation(self._last_stop),
        }

    def operation(self, identity: str | None) -> dict[str, Any] | None:
        retained = None if identity is None else self._operations.get(identity)
        return None if retained is None else deepcopy(retained.view)

    async def open(self) -> None:
        if self._server is not None or self._closed:
            raise CompanionControlError
        self._server = await asyncio.start_server(
            self._connected, "127.0.0.1", self.profile.port, limit=MAX_CONTROL_HEADERS, backlog=MAX_CONTROL_CLIENTS
        )

    def _connected(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        if self._closed or len(self._handlers) >= MAX_CONTROL_CLIENTS:
            writer.close()
            return
        self._writers.add(writer)
        task = asyncio.create_task(self._serve(reader, writer), name="companion-control-http")
        self._handlers.add(task)
        task.add_done_callback(self._handlers.discard)

    @staticmethod
    async def _headers(reader: asyncio.StreamReader, size: int) -> dict[str, str]:
        headers: dict[str, str] = {}
        while (line := await reader.readuntil(b"\r\n")) != b"\r\n":
            size += len(line)
            if size > MAX_CONTROL_HEADERS:
                raise CompanionControlError
            name, value = line.removesuffix(b"\r\n").decode("ascii").split(":", 1)
            if not re.fullmatch(r"[A-Za-z0-9-]+", name) or name.lower() in headers:
                raise CompanionControlError
            headers[name.lower()] = value.strip(" \t")
        return headers

    async def _request(self, reader: asyncio.StreamReader) -> tuple[str, str, bytes, ControlContext]:
        async with asyncio.timeout(CONTROL_IO_SECONDS):
            first = await reader.readexactly(1)
            fence = self.context()  # first observed bytes, before any subsequent network wait
            first_time, first_mono = self.clock(), time.monotonic()
            line = first + await reader.readuntil(b"\r\n")
            if len(line) > MAX_CONTROL_BODY:
                raise CompanionControlError
            method, path, version = line.decode("ascii").removesuffix("\r\n").split(" ")
            if version != "HTTP/1.1" or method not in {"GET", "POST"}:
                raise CompanionControlError
            headers = await self._headers(reader, len(line))
            if (
                headers.get("host") != f"127.0.0.1:{self.profile.port}"
                or any(name in headers for name in ("origin", "transfer-encoding", "content-encoding"))
                or "?" in path
                or "#" in path
            ):
                raise CompanionControlError
            if not compare_digest(headers.get("authorization", ""), "Bearer " + self.profile.token):
                raise CompanionControlError(401)
            length = headers.get("content-length", "0")
            if not re.fullmatch(r"0|[1-9][0-9]{0,3}", length) or int(length) > MAX_CONTROL_BODY:
                raise CompanionControlError
            if (method == "GET" and int(length)) or (
                method == "POST" and headers.get("content-type") != "application/json"
            ):
                raise CompanionControlError
            body = await reader.readexactly(int(length))
            wall_elapsed = self.clock() - first_time
            if abs(wall_elapsed - (time.monotonic() - first_mono)) * 1000 > MAX_FUTURE_SKEW_MS:
                raise CompanionControlError(408)
            return method, path, body, fence

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            try:
                method, path, body, fence = await self._request(reader)
                status, result = self._dispatch(method, path, body, fence)
            except CompanionControlError as error:
                status, result = error.status, {"protocol": 1, "status": "refused"}
            except (UnicodeError, ValueError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, TimeoutError):
                status, result = 400, {"protocol": 1, "status": "refused"}
            raw = json.dumps(result, ensure_ascii=True, allow_nan=False).encode()
            if len(raw) > MAX_CONTROL_RESPONSE:
                status, raw = 500, b'{"protocol":1,"status":"refused"}'
            writer.write(
                f"HTTP/1.1 {status} Control\r\nContent-Type: application/json\r\nContent-Length: {len(raw)}\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n".encode()
                + raw
            )
            async with asyncio.timeout(CONTROL_IO_SECONDS):
                await writer.drain()
        except (ConnectionError, OSError, TimeoutError):
            pass
        finally:
            self._writers.discard(writer)
            writer.close()
            try:
                async with asyncio.timeout(CONTROL_IO_SECONDS):
                    await writer.wait_closed()
            except (ConnectionError, OSError, TimeoutError):
                pass

    def _dispatch(self, method: str, path: str, raw: bytes, fence: ControlContext) -> tuple[int, dict[str, Any]]:
        if self._closed:
            raise CompanionControlError(409)
        if method == "GET" and path == "/v1/state":
            return 200, self.state()
        if method == "GET" and path.startswith("/v1/operations/"):
            identity = canonical_uuid(path.removeprefix("/v1/operations/"))
            operation = self.operation(identity)
            return (404, {"protocol": 1, "status": "not_found"}) if operation is None else (200, operation)
        if method != "POST" or path not in {"/v1/record", "/v1/stop", "/v1/hold", "/v1/release"}:
            raise CompanionControlError
        if path in {"/v1/hold", "/v1/release"} and self.hold_seconds is None:
            raise CompanionControlError(409)
        if path == "/v1/release":
            return self._release(raw)
        return self._mutate(path, raw, fence)

    @staticmethod
    def _envelope(path: str, raw: bytes) -> dict[str, Any]:
        keys = {"protocol", "session_id", "request_id", "created_at_ms", "admit_before_ms"}
        strings = {"session_id", "request_id"}
        if path in {"/v1/record", "/v1/hold", "/v1/release"}:
            keys |= {"context_id", "generation", "expires_at_ms"}
            strings.add("context_id")
        if path == "/v1/release":
            keys |= {"released_at_ms", "release_before_ms"}
        body = _object(raw, keys, MAX_CONTROL_BODY)
        if any(type(body[key]) is not str for key in strings):
            raise CompanionControlError
        if any(type(body[key]) is not int for key in keys - strings):
            raise CompanionControlError
        canonical_uuid(body["request_id"])
        canonical_uuid(body["session_id"])
        return body

    def _mutate(self, path: str, raw: bytes, fence: ControlContext) -> tuple[int, dict[str, Any]]:
        body = self._envelope(path, raw)
        if body["protocol"] != 1 or body["session_id"] != self.session_id:
            raise CompanionControlError(409)
        identity = canonical_uuid(body["request_id"])
        digest = sha256(path.encode() + b"\x00" + raw).hexdigest()
        previous = self._operations.get(identity)
        if previous is not None:
            if previous.digest != digest:
                raise CompanionControlError(409)
            return 200, deepcopy(previous.view)
        now = int(self.clock() * 1000)
        if (
            body["admit_before_ms"] != body["created_at_ms"] + GESTURE_ADMISSION_MS
            or body["created_at_ms"] > now + MAX_FUTURE_SKEW_MS
            or now >= body["admit_before_ms"]
        ):
            raise CompanionControlError(408)
        if path == "/v1/stop":
            return self._admit_stop(identity, digest)
        current = self.context()
        if body["expires_at_ms"] > self.expires_at_ms:
            raise CompanionControlError(408)
        if (
            body["context_id"] != self._context_id(fence)
            or body["context_id"] != self._context_id(current)
            or body["generation"] != fence.generation
            or body["generation"] != current.generation
            or body["expires_at_ms"] != body["created_at_ms"] + fence.instruction_timeout_ms
            or now >= body["expires_at_ms"]
        ):
            raise CompanionControlError(409)
        return self._admit_record(
            identity,
            digest,
            body["expires_at_ms"],
            fence,
            current,
            held_body=body if path == "/v1/hold" else None,
        )

    def _release(self, raw: bytes) -> tuple[int, dict[str, Any]]:
        """Finish only the original hold; an early release permanently fences its later start."""
        body = self._envelope("/v1/release", raw)
        if body["protocol"] != 1 or body["session_id"] != self.session_id:
            raise CompanionControlError(409)
        identity = body["request_id"]
        digest = sha256(b"/v1/release\x00" + raw).hexdigest()
        held, previous = self._holds.get(identity), self._operations.get(identity)
        if held is not None and held.release_digest is not None:
            if digest != held.release_digest:
                raise CompanionControlError(409)
            return 200, deepcopy(self._operations[identity].view)
        if held is None and previous is not None:
            if previous.digest == digest:
                return 200, deepcopy(previous.view)
            raise CompanionControlError(409)
        now = int(self.clock() * 1000)
        if (
            body["release_before_ms"] != min(body["released_at_ms"] + GESTURE_ADMISSION_MS, body["expires_at_ms"])
            or body["released_at_ms"] < body["created_at_ms"]
            or body["released_at_ms"] > now + MAX_FUTURE_SKEW_MS
            or now >= body["release_before_ms"]
            or now >= body["expires_at_ms"]
            or body["released_at_ms"] >= body["expires_at_ms"]
            or body["admit_before_ms"] != body["created_at_ms"] + GESTURE_ADMISSION_MS
            or body["expires_at_ms"] > self.expires_at_ms
        ):
            raise CompanionControlError(408)
        original = {key: value for key, value in body.items() if key not in {"released_at_ms", "release_before_ms"}}
        if held is None:
            if self._record_count >= self.max_attempts:
                raise CompanionControlError(429)
            # This consumes a finite identity slot, not a new capture or native Run.
            self._record_count += 1
            tombstone = _operation(identity, "record", digest)
            tombstone.view["status"] = "refused"
            self._operations[identity], self._last_record = tombstone, identity
            return 200, deepcopy(tombstone.view)
        if original != held.envelope or body["generation"] != self.context().generation:
            raise CompanionControlError(409)
        held.release_digest = digest
        held.released.set()
        return 202, deepcopy(self._operations[identity].view)

    def _admit_record(
        self,
        identity: str,
        digest: str,
        expiry: int,
        fence: ControlContext,
        current: ControlContext,
        *,
        held_body: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        if self._sealed or self._record_count >= self.max_attempts:
            raise CompanionControlError(429)
        eligible = fence.can_record and self._can_record(current)
        self._record_count += 1
        operation = _operation(identity, "record", digest)
        self._operations[identity], self._last_record = operation, identity
        if not eligible:
            operation.view["status"] = "refused"
            return 409, deepcopy(operation.view)
        try:
            released = None if held_body is None else asyncio.Event()
            if held_body is not None and released is not None:
                self._holds[identity] = _HeldRecord(dict(held_body), released)
            task = self.record(
                RecordGesture(
                    identity, fence.generation, expiry, released, self.hold_seconds if released is not None else None
                ),
                fence,
            )
        except (ValueError, RuntimeError):
            operation.view["status"] = "refused"
            return 409, deepcopy(operation.view)
        task.add_done_callback(lambda task: self._capture_settled(identity, task))
        return 202, deepcopy(operation.view)

    def _capture_settled(self, identity: str, task: asyncio.Task[None]) -> None:
        operation = self._operations[identity]
        error = None if task.cancelled() else task.exception()
        if operation.view["status"] == "pending" and (task.cancelled() or error is not None):
            operation.view.update(status="unknown", phase=None)

    def _admit_stop(self, identity: str, digest: str) -> tuple[int, dict[str, Any]]:
        if self._stop_count >= MAX_CONTROL_STOPS:
            raise CompanionControlError(429)
        self._stop_count += 1
        self._sealed |= self._stop_count == MAX_CONTROL_STOPS
        operation = _operation(identity, "stop", digest)
        self._operations[identity], self._last_stop = operation, identity
        try:
            task = self.stop()  # callback must fence before returning an owned task
        except (ValueError, RuntimeError):
            operation.view["status"] = "unknown"
            self._sealed = True
        else:
            self._settlements.add(task)
            task.add_done_callback(lambda task: self._stop_settled(identity, task))
        return 202, deepcopy(operation.view)

    def _stop_settled(self, identity: str, task: asyncio.Task[CompanionResult]) -> None:
        self._settlements.discard(task)
        operation = self._operations[identity]
        error = None if task.cancelled() else task.exception()
        if task.cancelled() or error is not None:
            operation.view["status"] = "unknown"
            self._sealed = True
            return
        result = task.result()
        operation.view.update(
            status="unknown" if result.kind == "unknown" else "known",
            game_kind=result.kind,
            server_stop_id=result.request_id,
        )
        self._sealed |= result.kind == "unknown"

    def observe(self, event: dict[str, Any]) -> None:
        """Project only correlated host-owned closed facts, never raw recognized words."""
        operation = self._operations.get(event.get("request_id", ""))
        if operation is None or operation.view["operation"] != "record":
            return
        view, kind = operation.view, event.get("kind")
        if self._observe_voice_failure(event, view, kind):
            return
        if kind in {"reply_evidence", "speech_failed", "reply_evidence_failed"}:
            self._observe_audio(event, view)
        elif kind == "voice_stop_result" and event.get("game_kind") in {"applied", "refused", "cancelled", "unknown"}:
            self._observe_feedback(event, view)
            view.update(
                status="unknown" if event["game_kind"] == "unknown" else "known",
                phase=None,
                game_kind=event["game_kind"],
                server_stop_id=event.get("server_stop_id"),
            )
        elif "evidence" in event and "feedback" not in event:
            view["native_evidence_status"] = "recorded"
        elif kind == "native_evidence_failed":
            view["native_evidence_status"] = "failed"
        elif kind == "voice_stage" and event.get("phase") in {
            "waiting_audio",
            "recording_pending",
            "recording",
            "finishing",
            "reading_audio",
            "transcribing",
        }:
            view["phase"] = event["phase"]
        elif kind == "queued":
            view["phase"] = "queued"
        elif "feedback" in event and kind in {
            "applied",
            "refused",
            "cancelled",
            "expired",
            "unknown",
            "no_action",
            "clarification",
        }:
            self._observe_result(event, view, kind)

    @staticmethod
    def _observe_voice_failure(event: dict[str, Any], view: dict[str, Any], kind: str | None) -> bool:
        """Keep local input failure separate from game facts, including late presentation failure."""
        voice_failure = (
            kind in {"voice_refused", "voice_unknown"}
            or (kind in {"refused", "unknown"} and "voice_failure" in event)
            or (kind == "refused" and "feedback" not in event)
        )
        if not voice_failure:
            return False
        if view["game_kind"] is None:
            CompanionControl._observe_feedback(event, view)
            view.update(status="unknown" if kind in {"unknown", "voice_unknown"} else "refused", phase=None)
        return True

    @staticmethod
    def _observe_audio(event: dict[str, Any], view: dict[str, Any]) -> None:
        for key, allowed in {
            "reply_status": {"not_attempted", "generated", "failed", "cancelled_server_work_unknown"},
            "playback": {"not_attempted", "player_exited", "interrupted", "failed", "settlement_unknown"},
            "reply_failure": {"synthesis_failed", "artifact_write_failed", "playback_failed", "playback_unsettled"},
        }.items():
            if event.get(key) in allowed:
                view[key] = event[key]
        if event.get("evidence_status") in {"recorded", "failed"}:
            view["reply_evidence_status"] = event["evidence_status"]

    @staticmethod
    def _observe_feedback(event: dict[str, Any], view: dict[str, Any]) -> None:
        supplied_feedback = event.get("feedback")
        feedback = cast("dict[str, Any]", supplied_feedback) if type(supplied_feedback) is dict else {}
        if (
            set(feedback) == {"language", "text"}
            and feedback["language"] in {"sk", "cs", "en"}
            and type(feedback["text"]) is str
            and len(feedback["text"]) <= MAX_FEEDBACK_CHARS
        ):
            view["feedback"] = dict(feedback)

    @staticmethod
    def _observe_result(event: dict[str, Any], view: dict[str, Any], kind: str) -> None:
        CompanionControl._observe_feedback(event, view)
        view.update(status="unknown" if kind == "unknown" else "known", game_kind=kind, phase=None)
        if event.get("evidence_status") in {"pending", "recorded", "failed", "not_requested"} and (
            event["evidence_status"] != "pending" or view["native_evidence_status"] not in {"recorded", "failed"}
        ):
            view["native_evidence_status"] = event["evidence_status"]

    def seal(self) -> None:
        """Revoke new recording synchronously while retaining stop and query ownership."""
        self._sealed = True

    async def aclose(self) -> None:
        """Close admission before joining already-owned transport/stop settlement."""
        self._closed = True
        if self._server is not None:
            self._server.close()
        for writer in self._writers:
            writer.close()
        if self._server is not None:
            await complete_under_cancellation(self._server.wait_closed())
        if self._handlers:
            await complete_under_cancellation(asyncio.gather(*self._handlers, return_exceptions=True))
        if self._settlements:
            await complete_under_cancellation(asyncio.gather(*self._settlements, return_exceptions=True))
