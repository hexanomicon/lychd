"""Explicit CPU-ready voice/text companion session; no normal application startup."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import time
from collections.abc import AsyncGenerator, Callable, Coroutine, Generator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import uuid4

from lychd.compositions.blockworld.companion import (
    CompanionPolicy,
    CompanionRequest,
    CompanionResult,
    CompanionService,
    canonical_uuid,
    parse_text,
    strict_json,
)
from lychd.compositions.blockworld.companion_feedback import feedback_text, reply_text, voice_failure_text
from lychd.compositions.blockworld.companion_intent import (
    CompanionInstruction,
    CompanionIntentProfile,
    load_intent_profile,
    revalidate_intent_profile,
    validate_raw_instruction,
)
from lychd.domain.artifacts import ArtifactRef
from lychd.domain.speech_probe import (
    MAX_INPUT_BYTES,
    MAX_PROFILE_BYTES,
    SpeechProbeError,
    content_digest,
    load_speech_profile,
)
from lychd.lib.asyncio import complete_under_cancellation
from lychd.system.services.companion_bridge import BridgeBinding, CompanionBridge, CompanionBridgeError
from lychd.system.services.companion_control import (
    MAX_CONTROL_ATTEMPTS,
    CompanionControl,
    ControlContext,
    RecordGesture,
    load_control_profile,
)
from lychd.system.services.companion_session import CompanionSession, LocalCompanionRunner, SessionResult
from lychd.system.services.speech_probe import SpeechProbe
from lychd.system.services.voice_capture import (
    VoiceCaptureError,
    VoiceCaptureUnsettled,
    capture_held_utterance,
    capture_utterance,
)
from lychd.system.services.voice_playback import VoicePlaybackError, VoicePlaybackUnsettled, play_reply
from scripts.voice_probe import PrivateWorkspace

if TYPE_CHECKING:
    from rich.console import Console

STOP_WORDS = frozenset({":stop", "stop", "zastav", "stoj", "stůj", "stuj"})
MAX_CONSOLE_BYTES = 1024
MAX_RECEIPT_BYTES = 2_097_152


@dataclass(frozen=True)
class _CapturedInstruction:
    request_id: str
    generation: int
    target_id: str | None
    expires_at_ms: int


@dataclass(frozen=True)
class _ConsoleInput:
    request_id: str
    generation: int
    expires_at_ms: int
    eligible: bool


class _InstructionRefusedError(ValueError):
    """A local rejection before command admission returns an owned result future."""


def _host_tick() -> int | None:
    """Read an optional clock without making it an operation's failure."""
    try:
        value = time.monotonic_ns()
    except Exception:  # noqa: BLE001 - an unavailable observation cannot change control flow
        return None
    return value if type(value) is int and value >= 0 else None


def _milliseconds(start: int | None, end: int | None) -> int | None:
    return None if start is None or end is None or end < start else (end - start) // 1_000_000


_TIMING_STAGES = (
    "audio_wait",
    "capture",
    "supplied_audio_read",
    "source_retention",
    "transcription",
    "transcript_retention",
    "admission",
    "native_wait",
    "reply_audio_wait",
    "synthesis",
    "reply_artifact_retention",
    "playback",
    "voice_evidence_retention",
    "reply_evidence_retention",
    "spoken_stop",
)


class _VoiceTiming:
    """One finite host observation, retired by existing task owners without waiting."""

    def __init__(
        self,
        context: _CapturedInstruction,
        *,
        supplied: bool,
        files: PrivateWorkspace,
        present: Callable[[dict[str, Any]], None],
    ) -> None:
        self.context, self.files, self.present = context, files, present
        self.source = "supplied" if supplied else "microphone"
        self.origin = _host_tick()
        self.starts: dict[str, int | None] = {}
        self.stages: dict[str, dict[str, Any]] = {
            name: {"start_ms": None, "duration_ms": None, "status": "not_attempted"} for name in _TIMING_STAGES
        }
        self.owners = {"voice"}
        self.sealed = False
        self.native: dict[str, Any] = {
            "run_id": None,
            "run_identity": "not_observed",
            "native_kind": "not_observed",
            "native_end_basis": "not_attempted",
        }
        self.begin("audio_wait", at=self.origin)

    def begin(self, name: str, *, at: int | None = None) -> None:
        if self.sealed or name in self.starts:
            return
        tick = _host_tick() if at is None else at
        self.starts[name] = tick
        self.stages[name].update(start_ms=_milliseconds(self.origin, tick), status="pending")

    def end(self, name: str, status: str = "returned") -> None:
        if self.sealed or self.stages[name]["status"] != "pending":
            return
        self.stages[name].update(duration_ms=_milliseconds(self.starts[name], _host_tick()), status=status)

    def observed(self, result: SessionResult | None, run_id: str | None) -> None:
        if self.sealed:
            return
        self.end("native_wait")
        self.native = {
            "run_id": run_id,
            "run_identity": "known"
            if run_id is not None
            else (
                "absent"
                if result is not None and result.reason in {"cancelled_before_execution", "expired_before_execution"}
                else "unknown"
            ),
            "native_kind": "unknown" if result is None else result.kind,
            "native_end_basis": "local_outcome_unavailable" if result is None else "native_result_observed",
        }

    def retire(self, owner: str) -> None:
        self.owners.discard(owner)
        if self.owners or self.sealed:
            return
        for name in self.starts:
            self.end(name, "local_retirement_unknown")
        if "native_wait" in self.starts and self.native["native_end_basis"] == "not_attempted":
            self.native.update(
                run_identity="unknown", native_kind="unknown", native_end_basis="local_retirement_unknown"
            )
        self.sealed = True
        document = {
            "schema": "companion-host-timing@1",
            "request_id": self.context.request_id,
            "generation": self.context.generation,
            "expires_at_ms": self.context.expires_at_ms,
            "source": self.source,
            "origin": "host_voice_admission",
            "elapsed_ms": _milliseconds(self.origin, _host_tick()),
            "stages": self.stages,
            **self.native,
            "human_hearing": "unconfirmed",
        }
        path = self.files.root / f"{self.context.request_id}-timing.json"
        event: dict[str, Any] = {"kind": "voice_timing", **document}
        try:
            self.files.write_new(path, json.dumps(document, allow_nan=False).encode())
        except Exception:  # noqa: BLE001 - timing custody has no native or audio authority
            event["kind"] = "timing_evidence_failed"
        else:
            event["timing_evidence_path"] = str(path)
        self.present(event)


@contextmanager
def _measure(timing: _VoiceTiming | None, name: str) -> Generator[None]:
    if timing is not None:
        timing.begin(name)
    status = "returned"
    try:
        yield
    except asyncio.CancelledError:
        status = "cancelled_local"
        raise
    except BaseException:
        status = "raised_local"
        raise
    finally:
        if timing is not None:
            timing.end(name, status)


type VoicePhase = Literal[
    "waiting_audio", "recording_pending", "recording", "finishing", "reading_audio", "transcribing"
]
type ReplyPhase = Literal["waiting_audio", "synthesizing", "generated", "player_pending"]


@dataclass(frozen=True)
class _AudioOperation:
    request_id: str
    phase: VoicePhase | ReplyPhase
    source: Literal["microphone", "supplied", "reply"]


def stop_requested(text: str) -> bool:
    return text.strip().casefold().rstrip(".!?") in STOP_WORDS


def _message(value: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
    sys.stdout.flush()


def _queue_console_line[T](
    queue: asyncio.Queue[tuple[str, T] | None], raw: bytearray, stamp: T, emit: Callable[[dict[str, Any]], None]
) -> None:
    try:
        value = raw.decode("utf-8").strip()
    except UnicodeError:
        emit({"kind": "refused", "detail": "Console input must be UTF-8."})
        return
    if len(raw) > MAX_CONSOLE_BYTES:
        emit({"kind": "refused", "detail": "Console line exceeds its bound."})
        return
    if stop_requested(value) or value == ":quit":
        while not queue.empty():
            queue.get_nowait()
    if queue.full():
        emit({"kind": "refused", "detail": "Console admission queue is full."})
    else:
        queue.put_nowait((value, stamp))


async def console_lines[T](  # noqa: C901 - one bounded Linux fd owns byte and priority queues
    capture: Callable[[], T], *, emit: Callable[[dict[str, Any]], None] = _message
) -> AsyncGenerator[tuple[str, T]]:
    """Stamp each line's first observed bytes, preserving priority and finite buffering."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, T] | None] = asyncio.Queue(maxsize=8)
    buffer = bytearray()
    discarding = False
    ended = False
    stamp: tuple[T] | None = None
    descriptor = sys.stdin.fileno()

    def ready() -> None:
        nonlocal discarding, ended, stamp
        chunk = os.read(descriptor, MAX_CONSOLE_BYTES + 1)
        if not chunk:
            loop.remove_reader(descriptor)
            ended = True
            if buffer:
                emit({"kind": "refused", "detail": "Incomplete console line at EOF."})
            if not queue.full():
                queue.put_nowait(None)
            return
        if discarding:
            _, separator, chunk = chunk.partition(b"\n")
            if not separator:
                return
            discarding = False
        buffer.extend(chunk)
        if buffer and stamp is None:
            stamp = (capture(),)
        while b"\n" in buffer:
            raw, _, rest = buffer.partition(b"\n")
            buffer[:] = rest
            current = stamp
            stamp = (capture(),) if rest else None
            if current is None:
                msg = "Console line lost its acquisition stamp."
                raise RuntimeError(msg)
            _queue_console_line(queue, raw, current[0], emit)
        if len(buffer) > MAX_CONSOLE_BYTES:
            buffer.clear()
            stamp = None
            discarding = True
            emit({"kind": "refused", "detail": "Console line exceeds its bound."})

    loop.add_reader(descriptor, ready)
    try:
        while not ended or not queue.empty():
            line = await queue.get()
            if line is None:
                break
            yield line
    finally:
        loop.remove_reader(descriptor)


class CompanionConsole:
    """Keep capture, native requests, private evidence and optional replies separate."""

    def __init__(
        self,
        files: PrivateWorkspace,
        session: CompanionSession,
        *,
        speech: SpeechProbe | None = None,
        language: str | None = None,
        reply_language: str | None = None,
        play_replies: bool = False,
        target_id: str | None = None,
        intent_profile: CompanionIntentProfile | None = None,
        instruction_timeout_s: float = 30,
        output: Literal["json", "human"] = "json",
    ) -> None:
        """Bind explicit session and optional speech; microphone capture stays disarmed."""
        self.files, self.session, self.speech = files, session, speech
        self.language, self.reply_language, self.play_replies = language, reply_language, play_replies
        self.target_id = None if target_id is None else canonical_uuid(target_id)
        if output not in {"json", "human"}:
            msg = "Console output must be json or human."
            raise ValueError(msg)
        self.output = output
        self.control: CompanionControl | None = None
        self._terminal: Console | None = None
        self._presentation_failed = False
        self._voice_operation: _AudioOperation | None = None
        self._reply_operations: dict[str, _AudioOperation] = {}
        if not 1 <= instruction_timeout_s <= 60:  # noqa: PLR2004 - one instruction's finite lifetime
            msg = "Instruction timeout must be 1-60 seconds."
            raise ValueError(msg)
        self.intent_profile = None if intent_profile is None else revalidate_intent_profile(intent_profile)
        self.instruction_timeout_s = instruction_timeout_s
        self.voice_task: asyncio.Task[None] | None = None
        self.replies: set[asyncio.Task[None]] = set()
        self._audio_replies: set[asyncio.Task[None]] = set()
        self._reply_outcomes: dict[str, tuple[asyncio.Future[SessionResult], asyncio.Future[SessionResult | None]]] = {}
        self._reply_lock = asyncio.Lock()
        self._capture_lock = asyncio.Lock()
        self._audio_blocked = False
        self._stopping = 0
        if speech is not None:
            speech.profile.language_for_transcription(language)
        if reply_language is not None:
            if speech is None:
                msg = "Speech replies require an explicit local speech profile."
                raise ValueError(msg)
            reply_text("applied", reply_language)
            speech.profile.language_for_synthesis(reply_language)
        if play_replies and reply_language is None:
            msg = "Playback requires an explicit reply language."
            raise ValueError(msg)
        if output == "human":
            reply_text("applied", self.reply_language or self.language or "en")

    def present(self, value: dict[str, Any]) -> None:
        """Keep foreground rendering failure outside action, receipt and retirement authority."""
        self._observe_control(value)
        try:
            if self.output == "json":
                _message(value)
            else:
                from rich.text import Text

                from lychd.cli.base import get_console
                from lychd.cli.companion_view import format_companion_event

                line = format_companion_event(
                    value, language=cast("Literal['sk', 'cs', 'en']", self.reply_language or self.language or "en")
                )
                if line is not None:
                    if self._terminal is None:
                        self._terminal = get_console()
                    self._terminal.print(Text(line), highlight=False)
        except Exception:  # noqa: BLE001 - presentation cannot erase a known result or bypass owned retirement
            self._presentation_failed = True

    def _observe_control(self, value: dict[str, Any]) -> None:
        if self.control is not None:
            try:
                self.control.observe(value)
            except Exception:  # noqa: BLE001 - a local projection cannot change effects or retirement
                self._presentation_failed = True

    def _notice(self, value: dict[str, Any]) -> None:
        if self.output == "human":
            self.present(value)
        else:
            self._observe_control(value)

    def control_context(self) -> ControlContext:
        """Observe the gesture fence before transport waits, preserving the explicit target."""
        state = self.session.snapshot()
        return ControlContext(
            generation=state.generation,
            target_id=self.target_id,
            instruction_timeout_ms=int(self.instruction_timeout_s * 1000),
            can_record=(
                state.opened
                and not state.closed
                and not state.fenced
                and not self._stopping
                and not self._audio_blocked
                and self.speech is not None
                and (self.voice_task is None or self.voice_task.done())
            ),
            stopping=bool(self._stopping) or state.stopping,
            audio_blocked=self._audio_blocked,
            voice_request_id=None if self._voice_operation is None else self._voice_operation.request_id,
            voice_phase=None if self._voice_operation is None else self._voice_operation.phase,
        )

    def record_gesture(self, gesture: RecordGesture, context: ControlContext) -> asyncio.Task[None]:
        """Admit the validated original gesture without creating a replacement occurrence."""
        control = self.control
        if (
            control is None
            or context.generation != self.session.capture_generation()
            or context.target_id != self.target_id
        ):
            msg = "Local gesture context is no longer current."
            raise ValueError(msg)
        return self._begin_voice(
            None,
            seconds=control.profile.record_seconds if gesture.released is None else gesture.hold_seconds,
            context=_CapturedInstruction(
                gesture.request_id, gesture.generation, context.target_id, gesture.expires_at_ms
            ),
            released=gesture.released,
        )

    def status(self) -> dict[str, Any]:
        """Observe local owners only; this query cannot admit or settle a command."""
        return {
            "kind": "status",
            "session": asdict(self.session.snapshot()),
            "voice": None if self._voice_operation is None else asdict(self._voice_operation),
            "replies": [asdict(operation) for operation in self._reply_operations.values()],
            "audio_blocked": self._audio_blocked,
            "stopping": bool(self._stopping),
            "target_id": self.target_id,
            "presentation_failed": self._presentation_failed,
        }

    def _voice_stage(self, context: _CapturedInstruction, phase: VoicePhase, *, supplied: bool) -> None:
        operation = _AudioOperation(context.request_id, phase, "supplied" if supplied else "microphone")
        self._voice_operation = operation
        self._notice({"kind": "voice_stage", **asdict(operation)})

    def _reply_stage(self, request_id: str, phase: ReplyPhase) -> None:
        operation = _AudioOperation(request_id, phase, "reply")
        self._reply_operations[request_id] = operation
        self._notice({"kind": "reply_stage", **asdict(operation)})

    async def record(self, document: dict[str, Any]) -> None:
        try:
            raw = json.dumps(document, ensure_ascii=False, allow_nan=False).encode()
            if len(raw) > MAX_RECEIPT_BYTES:
                msg = "Native evidence exceeds the private receipt bound."
                raise ValueError(msg)  # noqa: TRY301 - malformed evidence follows the same custody failure path
            path = self.files.root / f"{uuid4()}-native.json"
            self.files.write_new(path, raw)
        except (OSError, RuntimeError, TypeError, ValueError):
            self._notice({"kind": "native_evidence_failed", "request_id": document.get("request_id")})
            raise
        self.present(
            {
                "request_id": document.get("request_id"),
                "run_id": document.get("run_id"),
                "kind": document.get("kind"),
                "evidence": str(path),
            }
        )

    def submit(
        self, text: str, *, source: Literal["text", "transcript"] = "text", generation: int | None = None
    ) -> asyncio.Future[SessionResult]:
        context = self._capture_instruction(generation=generation)
        return self._submit(text, source=source, context=context)

    def _capture_instruction(self, *, generation: int | None = None) -> _CapturedInstruction:
        return _CapturedInstruction(
            str(uuid4()),
            self.session.capture_generation() if generation is None else generation,
            self.target_id,
            int((time.time() + self.instruction_timeout_s) * 1000),
        )

    def _capture_line(self) -> _ConsoleInput:
        context = self._capture_instruction()
        return _ConsoleInput(context.request_id, context.generation, context.expires_at_ms, not self._stopping)

    def _line_context(self, item: _ConsoleInput) -> _CapturedInstruction:
        if not item.eligible or self._stopping or item.generation != self.session.capture_generation():
            msg = "Console input predates stop or stop remains unsettled."
            raise ValueError(msg)
        if item.expires_at_ms <= int(time.time() * 1000):
            msg = "Console input expired before handling."
            raise ValueError(msg)
        # :target and following commands retain their order even within one fd read.
        return _CapturedInstruction(item.request_id, item.generation, self.target_id, item.expires_at_ms)

    def _admit_input(
        self,
        text: str,
        *,
        source: Literal["text", "transcript"],
        context: _CapturedInstruction,
        source_artifacts: tuple[ArtifactRef, ...] = (),
    ) -> tuple[CompanionRequest | CompanionInstruction, asyncio.Future[SessionResult]]:
        """Mark known local rejection before returning an admitted command future."""
        try:
            instruction = text.strip(" \t\r\n") if source == "transcript" else text
            request: CompanionRequest | CompanionInstruction
            try:
                action = parse_text(instruction, target_id=context.target_id)
            except ValueError:
                if self.intent_profile is None:
                    raise
                validate_raw_instruction(instruction)
                request = CompanionInstruction(
                    request_id=context.request_id,
                    original_text=text,
                    source=source,
                    language=cast("Literal['sk', 'cs', 'en']", self.language or "en"),
                    generation=context.generation,
                    target_id=context.target_id,
                    source_artifacts=source_artifacts,
                    profile_digest=self.intent_profile.digest,
                    expires_at_ms=context.expires_at_ms,
                )
            else:
                request = CompanionRequest(
                    request_id=context.request_id,
                    action=action,
                    transcript=text,
                    source=source,
                    generation=context.generation,
                    expires_at_ms=context.expires_at_ms,
                    source_artifacts=source_artifacts,
                )
            future = self.session.enqueue(request, captured_generation=context.generation)
        except ValueError as error:
            raise _InstructionRefusedError(str(error)) from None

        return request, future

    def _submit(  # noqa: C901 - keep admitted outcome and observational callback ownership together
        self,
        text: str,
        *,
        source: Literal["text", "transcript"],
        context: _CapturedInstruction,
        source_artifacts: tuple[ArtifactRef, ...] = (),
        timing: _VoiceTiming | None = None,
    ) -> asyncio.Future[SessionResult]:
        """Attach reply ownership only after command admission has returned its future."""
        request, future = self._admit_input(text, source=source, context=context, source_artifacts=source_artifacts)
        if timing is not None:
            timing.begin("native_wait")

        outcome: asyncio.Future[SessionResult | None] = asyncio.get_running_loop().create_future()
        caller: asyncio.Future[SessionResult] = asyncio.get_running_loop().create_future()
        self._reply_outcomes[request.request_id] = future, outcome

        def resolved(native: asyncio.Future[SessionResult]) -> None:
            error = None if native.cancelled() else native.exception()
            if not outcome.done():
                outcome.set_result(None if native.cancelled() or error is not None else native.result())
            if not caller.done():
                if native.cancelled():
                    caller.cancel()
                elif error is not None:
                    caller.set_exception(error)
                else:
                    caller.set_result(native.result())

        if future.done():
            resolved(future)
        else:
            future.add_done_callback(resolved)
        if timing is not None:
            timing.owners.add("reply")
        try:
            watcher = asyncio.create_task(self._reply(outcome, request, timing), name="companion-outcome-reply")
        except BaseException:
            if timing is not None:
                timing.retire("reply")
            raise
        self.replies.add(watcher)
        watcher.add_done_callback(self.replies.discard)
        if timing is not None:
            watcher.add_done_callback(lambda _: timing.retire("reply"))
        self._queued_notice(request.request_id)
        return caller

    def _queued_notice(self, request_id: str) -> None:
        queued: dict[str, Any] = {"kind": "queued", "request_id": request_id}
        if self.output == "human":
            snapshot = self.session.snapshot()
            queued.update({"local_pending": len(snapshot.pending), "local_capacity": snapshot.capacity})
        self.present(queued)

    async def _reply(
        self,
        future: asyncio.Future[SessionResult | None],
        request: CompanionRequest | CompanionInstruction,
        timing: _VoiceTiming | None = None,
    ) -> None:
        """Own one request's outcome and receipt; stop cancels only its audio stage."""
        result = await complete_under_cancellation(future)
        self._reply_outcomes.pop(request.request_id, None)
        run_id = result.run_id if result is not None else getattr(self.session, "run_ids", {}).get(request.request_id)
        if timing is not None:
            timing.observed(result, run_id)
        document = (
            asdict(result)
            if result is not None
            else {
                "request_id": request.request_id,
                "run_id": run_id,
                "kind": "unknown",
                "reason": None,
                "detail": "Native result unavailable after settlement.",
            }
        )
        document["result"] = None if result is None or result.result is None else result.result.model_dump(mode="json")
        document["game_status"] = "known" if result is not None else "unavailable"
        language = self.reply_language or self.language or "en"
        text = feedback_text(
            request,
            None if result is None else result.result,
            kind="unknown" if result is None else result.kind,
            language=language,
            outcome=result,
            at_ms=int(time.time() * 1000),
        )
        document["feedback"] = {"language": language, "text": text}
        self.present(document)
        if self.speech is None or self.reply_language is None:
            return
        evidence: dict[str, Any] = {
            "request_id": request.request_id,
            "run_id": run_id,
            "run_identity": "known"
            if run_id is not None
            else (
                "absent"
                if result is not None and result.reason in {"cancelled_before_execution", "expired_before_execution"}
                else "unknown"
            ),
            "game_status": document["game_status"],
            "kind": None if result is None else result.kind,
            "reason": None if result is None else result.reason,
            "feedback": document["feedback"],
            "reply_status": "not_attempted",
            "reply_audio": None,
            "synthesis_observation": None,
            "playback": "not_attempted",
            "human_hearing": "unconfirmed",
        }
        self._reply_stage(request.request_id, "waiting_audio")
        if timing is not None:
            timing.begin("reply_audio_wait")
        audio = asyncio.create_task(
            self._reply_audio(evidence, text, request.generation, timing), name="companion-reply-audio"
        )
        self._audio_replies.add(audio)
        try:
            await asyncio.shield(audio)
        except asyncio.CancelledError:
            audio.cancel()
            await complete_under_cancellation(asyncio.gather(audio, return_exceptions=True))
        finally:
            self._audio_replies.discard(audio)
            self._reply_operations.pop(request.request_id, None)
            with _measure(timing, "reply_evidence_retention"):
                self._retain_reply(evidence)

    async def _reply_audio(  # noqa: C901 - retain existing audio/error custody around observational spans
        self, evidence: dict[str, Any], text: str, generation: int, timing: _VoiceTiming | None = None
    ) -> None:
        speech, language = self.speech, self.reply_language
        if speech is None or language is None:
            return
        async with self._reply_lock, self._capture_lock:
            if timing is not None:
                timing.end("reply_audio_wait")
            if self._audio_blocked or generation != self.session.capture_generation():
                return
            self._reply_stage(evidence["request_id"], "synthesizing")
            try:
                with _measure(timing, "synthesis"):
                    observation, content = await speech.synthesize(text, language=language, voice="M1")
            except asyncio.CancelledError:
                evidence["reply_status"] = "cancelled_server_work_unknown"
                raise
            except (SpeechProbeError, OSError, RuntimeError, ValueError):
                evidence.update({"reply_status": "failed", "reply_failure": "synthesis_failed"})
                return
            evidence["reply_status"] = "generated"
            self._reply_stage(evidence["request_id"], "generated")
            path = self.files.root / f"{evidence['request_id']}-reply.wav"
            try:
                with _measure(timing, "reply_artifact_retention"):
                    self.files.write_new(path, content)
                    evidence["reply_audio"] = str(path)
                    self.files.write_new(path.with_suffix(".json"), observation.model_dump_json().encode())
                    evidence["synthesis_observation"] = str(path.with_suffix(".json"))
            except (OSError, RuntimeError, ValueError):
                evidence["reply_failure"] = "artifact_write_failed"
                return
            if self.play_replies and generation == self.session.capture_generation():
                self._reply_stage(evidence["request_id"], "player_pending")
                try:
                    with _measure(timing, "playback"):
                        evidence["playback"] = await play_reply(content)
                except asyncio.CancelledError:
                    evidence["playback"] = "interrupted"
                    raise
                except VoicePlaybackUnsettled:
                    # Latch before releasing capture ownership to a waiting recorder.
                    self._audio_blocked = True
                    evidence.update({"playback": "settlement_unknown", "reply_failure": "playback_unsettled"})
                except VoicePlaybackError:
                    evidence.update({"playback": "failed", "reply_failure": "playback_failed"})

    def _retain_reply(self, evidence: dict[str, Any]) -> None:
        """Publish only retained receipt paths, with closed correlated failure codes."""
        path = self.files.root / f"{evidence['request_id']}-reply-evidence.json"
        try:
            raw = json.dumps(evidence, ensure_ascii=False, allow_nan=False).encode()
            if len(raw) > MAX_RECEIPT_BYTES:
                msg = "Reply evidence exceeds the private receipt bound."
                raise ValueError(msg)  # noqa: TRY301 - a bounded receipt has the same failure settlement
            self.files.write_new(path, raw)
        except (OSError, RuntimeError, ValueError):
            self.present(
                {
                    **evidence,
                    "game_kind": evidence["kind"],
                    "kind": "reply_evidence_failed",
                    "evidence_status": "failed",
                }
            )
        else:
            self.present(
                {
                    "request_id": evidence["request_id"],
                    "run_id": evidence["run_id"],
                    "kind": "speech_failed" if "reply_failure" in evidence else "reply_evidence",
                    "reply_failure": evidence.get("reply_failure"),
                    "evidence_status": "recorded",
                    "evidence": str(path),
                    "reply_status": evidence["reply_status"],
                    "playback": evidence["playback"],
                    "human_hearing": "unconfirmed",
                }
            )

    def begin_voice(self, path: Path | None = None, *, seconds: int = 3) -> asyncio.Task[None]:
        return self._begin_voice(path, seconds=seconds, context=self._capture_instruction())

    def _begin_voice(
        self,
        path: Path | None,
        *,
        seconds: int | None,
        context: _CapturedInstruction,
        released: asyncio.Event | None = None,
    ) -> asyncio.Task[None]:
        if type(seconds) is not int or not 1 <= seconds <= 15:  # noqa: PLR2004 - recorder contract
            msg = "Capture requires 1-15 whole seconds."
            raise ValueError(msg)
        if (
            self._stopping
            or self._audio_blocked
            or self.speech is None
            or (self.voice_task is not None and not self.voice_task.done())
        ):
            msg = "Select a CPU speech profile and settle the previous utterance first."
            raise ValueError(msg)
        timing = _VoiceTiming(context, supplied=path is not None, files=self.files, present=self.present)
        self._voice_stage(context, "waiting_audio", supplied=path is not None)
        self.voice_task = asyncio.create_task(
            self._voice(path, seconds, context, timing, released=released), name="companion-utterance"
        )
        self.voice_task.add_done_callback(self._voice_settled)
        self.voice_task.add_done_callback(lambda _: timing.retire("voice"))
        return self.voice_task

    def _voice_settled(self, task: asyncio.Task[None]) -> None:
        if task is self.voice_task:
            self._voice_operation = None

    async def _capture(
        self, seconds: int, *, released: asyncio.Event | None = None, context: _CapturedInstruction | None = None
    ) -> bytes:
        """Reopen only settled capture failures; unknown ownership keeps audio latched."""
        if released is None:
            self.present({"capture": "active", "seconds": seconds})
        try:
            if released is None:
                content = await capture_utterance(seconds=seconds)
            else:
                if context is None or released.is_set():
                    msg = "Released hold cannot open a recorder later."
                    raise VoiceCaptureError(msg)
                content = await capture_held_utterance(
                    released=released,
                    max_seconds=seconds,
                    on_started=lambda: self._voice_stage(context, "recording", supplied=False),
                    on_finishing=lambda: self._voice_stage(context, "finishing", supplied=False),
                )
        except asyncio.CancelledError:
            # The helper joins owned retirement before propagating cancellation.
            self.present({"capture": "off"})
            raise
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            if isinstance(error, VoiceCaptureError) and not isinstance(error, VoiceCaptureUnsettled):
                self.present({"capture": "off"})
                raise
            self._audio_blocked = True
            self.present({"capture": "unknown", "detail": "Recorder retirement unconfirmed; further audio disabled."})
            raise
        else:
            self.present({"capture": "off"})
        return content

    async def _voice(  # noqa: PLR0915 - one occurrence keeps host stages, cancellation and final evidence together
        self,
        path: Path | None,
        seconds: int,
        context: _CapturedInstruction,
        timing: _VoiceTiming,
        *,
        released: asyncio.Event | None = None,
    ) -> None:
        """Retain failed host boundaries without rewriting native or stop dispositions."""
        speech = self.speech
        if speech is None:
            msg = "No speech profile selected."
            raise ValueError(msg)
        identity, generation = context.request_id, context.generation
        record: dict[str, Any] = {
            "request_id": identity,
            "kind": "unknown",
            "native_echo_admission": False,
            "generation": generation,
            "target_id": context.target_id,
            "expires_at_ms": context.expires_at_ms,
        }
        started = _host_tick()
        failure = "input_unavailable"
        try:
            async with self._capture_lock:
                timing.end("audio_wait")
                if (
                    self._stopping
                    or self._audio_blocked
                    or generation != self.session.capture_generation()
                    or context.expires_at_ms <= int(time.time() * 1000)
                ):
                    msg = "Audio retirement, stop or the captured instruction deadline is unsettled."
                    raise ValueError(msg)  # noqa: TRY301 - recheck after waiting for audio ownership
                if path is None:
                    failure = "capture_failed"
                    self._voice_stage(context, "recording_pending", supplied=False)
                    with _measure(timing, "capture"):
                        content = (
                            await self._capture(seconds)
                            if released is None
                            else await self._capture(seconds, released=released, context=context)
                        )
                else:
                    failure = "audio_read_failed"
                    self._voice_stage(context, "reading_audio", supplied=True)
                    with _measure(timing, "supplied_audio_read"):
                        content = self.files.read(path, MAX_INPUT_BYTES)
            if released is not None and (
                not released.is_set()
                or self._stopping
                or self._audio_blocked
                or generation != self.session.capture_generation()
                or context.expires_at_ms <= int(time.time() * 1000)
            ):
                msg = "Held instruction expired or stopped before transcription."
                raise VoiceCaptureError(msg)
            failure = "source_retention_failed"
            with _measure(timing, "source_retention"):
                artifact = self._retain_voice_artifact(identity, "source", content)
            failure = "transcription_failed"
            self._voice_stage(context, "transcribing", supplied=path is not None)
            with _measure(timing, "transcription"):
                transcript = await speech.transcribe(artifact, content, language=self.language)
            self._voice_operation = None
            self._notice(
                {
                    "kind": "heard",
                    "request_id": identity,
                    "text": transcript.text,
                    "source": "supplied" if path is not None else "microphone",
                }
            )
            failure = "transcript_retention_failed"
            with _measure(timing, "transcript_retention"):
                transcript_artifact = self._retain_voice_artifact(
                    identity, "transcript", transcript.model_dump_json().encode()
                )
            record["transcript"] = transcript.text
            if stop_requested(transcript.text):
                with _measure(timing, "spoken_stop"):
                    await self._spoken_stop(identity, record)
            else:
                failure = "admission_unknown"
                with _measure(timing, "admission"):
                    self._submit(
                        transcript.text,
                        source="transcript",
                        context=context,
                        source_artifacts=(artifact, transcript_artifact),
                        timing=timing,
                    )
                record["kind"] = "queued"
        except asyncio.CancelledError:
            record["kind"] = "cancelled_server_inference_unknown"
            raise
        except (SpeechProbeError, OSError, RuntimeError, ValueError) as error:
            self._present_voice_failure(identity, record, failure, error)
        finally:
            self._voice_operation = None
            elapsed = _milliseconds(started, _host_tick())
            record["seconds"] = None if elapsed is None else elapsed / 1000
            try:
                with _measure(timing, "voice_evidence_retention"):
                    self.files.write_new(self.files.root / f"{identity}-voice.json", json.dumps(record).encode())
            except (OSError, RuntimeError, ValueError):
                self.present({"kind": "voice_evidence_failed", "request_id": identity})

    def _retain_voice_artifact(
        self, identity: str, part: Literal["source", "transcript"], content: bytes
    ) -> ArtifactRef:
        """Retain exact private bytes before publishing their material reference."""
        source = part == "source"
        suffix = "source.wav" if source else "transcript.json"
        self.files.write_new(self.files.root / f"{identity}-{suffix}", content)
        return ArtifactRef(
            artifact_id=identity if source else f"{identity}-transcript",
            media_type="audio/wav" if source else "application/json",
            size=len(content),
            digest=content_digest(content),
            classification="private",
        )

    def _present_voice_failure(self, identity: str, record: dict[str, Any], failure: str, error: Exception) -> None:
        """Project a failed host boundary without deriving remote cause or renewing authority."""
        if isinstance(error, _InstructionRefusedError):
            failure = "instruction_refused"
        unknown = failure == "admission_unknown"
        if self._audio_blocked:
            failure = "audio_unsettled"
        record["kind"], record["voice_failure"] = "unknown" if unknown else "refused", failure
        language = self.reply_language or (self.language if self.language in {"sk", "cs", "en"} else "en")
        self.present(
            {
                "kind": ("voice_unknown" if unknown else "voice_refused") if self.output == "human" else record["kind"],
                "request_id": identity,
                "voice_failure": failure,
                "feedback": {"language": language, "text": voice_failure_text(failure, language)},
                "detail": "Speech or strict instruction admission failed.",
            }
        )

    async def _spoken_stop(self, identity: str, record: dict[str, Any]) -> None:
        """Correlate stop uncertainty separately from pre-native voice rejection."""
        try:
            result = await self.stop()
        except (OSError, RuntimeError, ValueError):
            record["kind"] = "unknown"
            language = self.reply_language or (self.language if self.language in {"sk", "cs", "en"} else "en")
            self.present(
                {
                    "kind": "voice_stop_result",
                    "request_id": identity,
                    "game_kind": "unknown",
                    "server_stop_id": None,
                    "feedback": {"language": language, "text": voice_failure_text("stop_unconfirmed", language)},
                }
            )
            return
        record["kind"], record["stop_request_id"] = result.kind, result.request_id
        self._notice(
            {
                "kind": "voice_stop_result",
                "request_id": identity,
                "game_kind": result.kind,
                "server_stop_id": result.request_id,
            }
        )

    def begin_stop(self) -> asyncio.Task[CompanionResult]:
        """Fence and cancel synchronously before returning owned asynchronous settlement."""
        self._stopping += 1
        try:
            settlement = self.session.stop()
            tasks = [*self._audio_replies]
            if (
                self.voice_task is not None
                and not self.voice_task.done()
                and self.voice_task is not asyncio.current_task()
            ):
                tasks.append(self.voice_task)
            for task in tasks:
                task.cancel()
            self._notice({"kind": "stop_requested"})
            return asyncio.create_task(
                self._finish_stop(settlement, tasks, [*self.replies]), name="companion-console-stop"
            )
        except BaseException:
            self._stopping -= 1
            raise

    async def stop(self) -> CompanionResult:
        """Join a synchronous fence without losing custody to caller cancellation."""
        return await complete_under_cancellation(self.begin_stop())

    async def _finish_stop(
        self,
        settlement: Coroutine[Any, Any, CompanionResult],
        tasks: list[asyncio.Task[None]],
        replies: list[asyncio.Task[None]],
    ) -> CompanionResult:
        try:
            result = await complete_under_cancellation(self._settle_stop(settlement, tasks, replies))
            if isinstance(result, BaseException):
                self._notice({"kind": "stop_unknown"})
                raise result
            document = result.model_dump(mode="json")
            if self.output == "human":
                document["control"] = "stop"
            self.present(document)
            return result
        finally:
            self._stopping -= 1

    async def _settle_stop(
        self,
        settlement: Coroutine[Any, Any, CompanionResult],
        audio: list[asyncio.Task[None]],
        replies: list[asyncio.Task[None]],
    ) -> CompanionResult | BaseException:
        try:
            try:
                result = await settlement
            finally:
                for identity, (native, outcome) in self._reply_outcomes.items():
                    if not outcome.done():
                        retained = getattr(self.session, "outcomes", {}).get(identity)
                        outcome.set_result(
                            retained
                            if retained is not None
                            else (
                                native.result()
                                if native.done() and not native.cancelled() and native.exception() is None
                                else None
                            )
                        )
                await complete_under_cancellation(asyncio.gather(*audio, *replies, return_exceptions=True))
        except (Exception, asyncio.CancelledError) as error:  # noqa: BLE001 - propagate outside cancellation shields
            return error
        return result

    async def run(self) -> None:
        ready: dict[str, Any] = {
            "ready": True,
            "commands": "stav | čakaj | nasleduj ma | choď X Y Z | pozri X Y Z | blok X Y Z | povedz TEXT | stop",
            "console": ":record [1-15] | :wav ABS_PATH | :target UUID | :language [INPUT [REPLY]] | :status | :quit",
        }
        if self.output == "human":
            ready.update(
                {
                    "language": self.language or "en",
                    "reply_language": self.reply_language,
                    "target_id": self.target_id,
                    "recognizer": None if self.speech is None else self.speech.profile.transcriber_binding.model.family,
                    "interpretation_selected": self.intent_profile is not None,
                }
            )
        self.present(ready)
        try:
            async for line, item in console_lines(self._capture_line, emit=self.present):
                try:
                    if stop_requested(line):
                        await self.stop()
                    elif line == ":quit":
                        return
                    else:
                        self._handle_line(line, item)
                except (ValueError, OSError):
                    self.present(
                        {
                            "kind": "refused",
                            "detail": "Unsupported, expired or stopped input, full queue or unavailable profile.",
                        }
                    )
        finally:
            if self.control is not None:
                self.control.seal()
            await self.stop()

    def _handle_line(self, line: str, item: _ConsoleInput) -> None:
        """Admit the original stamp and apply local selections in console order."""
        context = self._line_context(item)
        if line.startswith(":record"):
            parts = line.split()
            if parts[0] != ":record" or len(parts) > 2:  # noqa: PLR2004 - command plus one optional duration
                msg = "Use :record with one optional duration."
                raise ValueError(msg)
            self._begin_voice(None, seconds=int(parts[1]) if len(parts) > 1 else 3, context=context)
        elif line.startswith(":wav "):
            self._begin_voice(Path(line[5:]), seconds=3, context=context)
        elif line.startswith(":target "):
            self.target_id = canonical_uuid(line[8:].strip())
            self.present({"target_id": self.target_id})
        elif line == ":status":
            self.present(self.status())
        elif line.startswith(":language"):
            self._language_command(line, context.request_id)
        elif line:
            self._submit(line, source="text", context=context)

    def _language_command(self, line: str, request_id: str) -> None:
        """Validate both local choices atomically without mutating already-owned work."""
        parts = line.split()
        if parts[0] != ":language" or len(parts) > 3:  # noqa: PLR2004 - command and two optional locales
            msg = "Use :language [INPUT [REPLY]] with sk, cs or en."
            raise ValueError(msg)
        if len(parts) > 1:
            language = parts[1]
            reply_language = parts[2] if len(parts) == 3 else self.reply_language  # noqa: PLR2004 - optional reply locale
            if language not in {"sk", "cs", "en"} or reply_language not in {None, "sk", "cs", "en"}:
                msg = "Language selection requires sk, cs or en."
                raise ValueError(msg)
            if self.speech is None:
                msg = "Language selection requires an explicit local speech profile."
                raise ValueError(msg)
            if (
                (self.voice_task is not None and not self.voice_task.done())
                or self._voice_operation is not None
                or self.replies
                or self._reply_outcomes
            ):
                self.present({"kind": "language_busy", "request_id": request_id})
                return
            self.speech.profile.language_for_transcription(language)
            if reply_language is not None:
                self.speech.profile.language_for_synthesis(reply_language)
            self.language, self.reply_language = language, reply_language
        self.present(
            {
                "kind": "language",
                "request_id": request_id,
                "language": self.language,
                "reply_language": self.reply_language,
            }
        )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workspace", type=Path, required=True)
    result.add_argument("--checkout-root", type=Path, action="append", required=True)
    result.add_argument("--bridge-profile", type=Path, required=True)
    result.add_argument("--speech-profile", type=Path)
    result.add_argument("--intent-profile", type=Path)
    result.add_argument("--control-profile", type=Path)
    result.add_argument("--hold-seconds", type=int, choices=range(1, 16), metavar="1-15")
    result.add_argument("--instruction-timeout", type=float, default=30)
    result.add_argument("--language", choices=("sk", "cs", "en"))
    result.add_argument("--reply-language", choices=("sk", "cs", "en"))
    result.add_argument("--play-replies", action="store_true")
    result.add_argument("--output", choices=("json", "human"), default="json")
    result.add_argument("--target-id")
    result.add_argument("--duration", type=int, default=900)
    result.add_argument("--max-actions", type=int, default=128)
    result.add_argument("--allow-weather", action="store_true")
    result.add_argument("--allow-time", action="store_true")
    result.add_argument("--lease-seconds", type=float, default=15)
    result.add_argument(
        "--bounds", type=float, nargs=6, required=True, metavar=("MIN_X", "MIN_Y", "MIN_Z", "MAX_X", "MAX_Y", "MAX_Z")
    )
    return result


def _load_bridge_binding(files: PrivateWorkspace, path: Path) -> BridgeBinding:
    raw_binding = strict_json(files.read(path, MAX_PROFILE_BYTES))
    if type(raw_binding) is not dict:
        msg = "Bridge profile requires exactly endpoint, token and actor_id."
        raise ValueError(msg)
    binding_document = cast("dict[str, Any]", raw_binding)
    if set(binding_document) != {"endpoint", "token", "actor_id"} or any(
        type(value) is not str for value in binding_document.values()
    ):
        msg = "Bridge profile requires exactly three string fields."
        raise ValueError(msg)
    return BridgeBinding(
        endpoint=binding_document["endpoint"], token=binding_document["token"], actor_id=binding_document["actor_id"]
    )


def _load_speech(files: PrivateWorkspace, path: Path | None) -> SpeechProbe | None:
    if path is not None:
        profile = load_speech_profile(files.read(path, MAX_PROFILE_BYTES))
        if any(
            (binding.backend, binding.device) != ("cpu", "host")
            for binding in (profile.transcriber_binding, profile.synthesizer_binding)
        ):
            msg = "This lab accepts only the selected CPU/host speech profile."
            raise ValueError(msg)
        return SpeechProbe(profile)
    return None


async def run(args: argparse.Namespace) -> None:
    if not 1 <= args.duration <= 1800:  # noqa: PLR2004 - bounded interactive lab session
        msg = "Session duration must be 1-1800 seconds."
        raise ValueError(msg)
    if not 1 <= args.instruction_timeout <= 60:  # noqa: PLR2004 - one instruction's finite lifetime
        msg = "Instruction timeout must be 1-60 seconds."
        raise ValueError(msg)
    files = PrivateWorkspace(args.workspace, tuple(args.checkout_root))
    binding = _load_bridge_binding(files, args.bridge_profile)
    speech = _load_speech(files, args.speech_profile)
    intent_profile = (
        None if args.intent_profile is None else load_intent_profile(files.read(args.intent_profile, MAX_PROFILE_BYTES))
    )
    control_profile = (
        None
        if args.control_profile is None
        else load_control_profile(files.read(args.control_profile, MAX_PROFILE_BYTES))
    )
    if args.hold_seconds is not None and (control_profile is None or speech is None):
        msg = "Held input requires explicit game controls and a local speech profile."
        raise ValueError(msg)
    minimum, maximum = args.bounds[:3], args.bounds[3:]
    policy = CompanionPolicy(
        session_id=str(uuid4()),
        principal="companion-lab",
        expires_at=datetime.now(UTC) + timedelta(seconds=args.duration),
        min_x=minimum[0],
        min_y=minimum[1],
        min_z=minimum[2],
        max_x=maximum[0],
        max_y=maximum[1],
        max_z=maximum[2],
        max_actions=args.max_actions,
        allow_weather=args.allow_weather,
        allow_time=args.allow_time,
        lease_s=args.lease_seconds,
    )
    bridge = CompanionBridge(binding)
    runner = LocalCompanionRunner(CompanionService(policy, bridge), bridge, intent_profile=intent_profile)
    session = CompanionSession(runner, bridge)
    console = CompanionConsole(
        files,
        session,
        speech=speech,
        language=args.language,
        reply_language=args.reply_language,
        play_replies=args.play_replies,
        target_id=args.target_id,
        intent_profile=intent_profile,
        instruction_timeout_s=args.instruction_timeout,
        output=args.output,
    )
    session.record = console.record
    if control_profile is not None:
        console.control = CompanionControl(
            control_profile,
            expires_at_ms=int(policy.expires_at.timestamp() * 1000),
            context=console.control_context,
            record=console.record_gesture,
            stop=console.begin_stop,
            max_attempts=min(args.max_actions, MAX_CONTROL_ATTEMPTS),
            hold_seconds=args.hold_seconds,
        )
    loop = asyncio.get_running_loop()
    main = asyncio.current_task()
    if main is None:
        msg = "Missing owned console task."
        raise RuntimeError(msg)
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, main.cancel)
    try:
        await session.open()
        if console.control is not None:
            await console.control.open()
        console.present({"server": bridge.state.model_dump(mode="json") if bridge.state is not None else None})
        await console.run()
    finally:
        try:
            if console.control is not None:
                await console.control.aclose()
        finally:
            try:
                await session.aclose()
            finally:
                for sig in (signal.SIGINT, signal.SIGTERM):
                    loop.remove_signal_handler(sig)


def main() -> int:
    try:
        asyncio.run(run(parser().parse_args()))
    except (asyncio.CancelledError, KeyboardInterrupt):
        return 130
    except (CompanionBridgeError, SpeechProbeError, OSError, ValueError, RuntimeError):
        sys.stderr.write(
            "Companion lab refused or failed. Inspect private profiles and server readiness; no automatic replay.\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
