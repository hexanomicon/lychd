"""Explicit engineering voice-to-Horizon session; strict grammar, no native Echo grant."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import time
from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from lychd.compositions.blockworld.horizon_assist import AssistPolicy, AssistRequest, HorizonAssistService, parse_text
from lychd.compositions.blockworld.horizon_assist_runtime import LocalAssistRunner
from lychd.compositions.blockworld.horizon_behaviors import BehaviorDirective, HorizonBehaviorService
from lychd.compositions.blockworld.horizon_build import MAX_BUILD_BYTES, BuildPlan, HorizonBuildService, decode_plan
from lychd.compositions.blockworld.horizon_feedback import REPLY_LANGUAGES, feedback_text
from lychd.domain.artifacts import ArtifactRef
from lychd.domain.speech_probe import (
    MAX_INPUT_BYTES,
    MAX_PROFILE_BYTES,
    STOCK_VOICES,
    SpeechProbeError,
    StockVoice,
    TranscriptObservation,
    content_digest,
    load_speech_profile,
)
from lychd.system.services.horizon_control import HorizonBinding, HorizonControlSession
from lychd.system.services.horizon_observer import HorizonTargetObserver
from lychd.system.services.horizon_supervisor import HorizonSupervisor
from lychd.system.services.speech_probe import SpeechProbe
from lychd.system.services.voice_capture import VoiceCaptureError, VoiceCaptureUnsettled, capture_utterance
from lychd.system.services.voice_playback import VoicePlaybackError, VoicePlaybackUnsettled, play_reply
from scripts.voice_probe import PrivateWorkspace

_STOP_WORDS = {"stop", "zastav", "stoj", "stůj", "stuj", "quit", "koniec", "konec"}
_IDLE_WORDS = {"idle", "čakaj", "cakaj", "čekej", "cekej"}
_FOLLOW_WORDS = {"follow me", "nasleduj ma", "následuj mě", "nasleduj me"}
_BUILD_WORDS = {"build approved plan", "postav schválený plán", "postav schvaleny plan"}
_MAX_EVENT_BYTES = 2_097_152
_MAX_CONSOLE_BYTES = 256
_MAX_BEHAVIOR_SECONDS = 60


def _message(text: str) -> None:
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


@contextmanager
def _stage(timings: dict[str, float], name: str) -> Generator[None]:
    started = time.monotonic()
    try:
        yield
    finally:
        timings[name] = time.monotonic() - started


class VoiceSession:
    """One serial utterance passage sharing an arbiter with finite behavior Runs.

    Stop retires this entire session so admission racing with cancellation cannot
    acquire a fresh unfenced Run. Speech cancellation proves no server retirement.
    """

    def __init__(
        self,
        files: PrivateWorkspace,
        speech: SpeechProbe,
        runner: LocalAssistRunner,
        control: HorizonControlSession,
        *,
        language: str | None = None,
        reply_language: str | None = None,
        voice: StockVoice = "M1",
        behavior_seconds: int = 30,
        build_plan: BuildPlan | None = None,
        play_replies: bool = False,
    ) -> None:
        """Bind explicitly opened collaborators; capture remains disarmed."""
        self.files, self.speech, self.runner, self.control = files, speech, runner, control
        self.language = speech.profile.language_for_transcription(language)
        if reply_language is not None:
            speech.profile.language_for_synthesis(reply_language)
            if reply_language not in REPLY_LANGUAGES:
                msg = "This probe has reply wording only for explicitly selected sk, cs or en."
                raise ValueError(msg)
        self.reply_language = reply_language
        if type(play_replies) is not bool or (play_replies and reply_language is None):
            msg = "Playback requires an explicit boolean choice and reply language."
            raise ValueError(msg)
        self.play_replies = play_replies
        self.feedback_language = reply_language or (self.language if self.language in REPLY_LANGUAGES else "en")
        self.voice: StockVoice = voice
        if type(behavior_seconds) is not int or not 1 <= behavior_seconds <= _MAX_BEHAVIOR_SECONDS:
            msg = "Behavior duration must be a whole number of seconds from 1 to 60."
            raise ValueError(msg)
        self.behavior_seconds = behavior_seconds
        self.build_plan = build_plan
        self.supervisor = HorizonSupervisor(runner, control, behaviors=runner.behaviors, record=self._behavior_record)
        self.stopped = self.supervisor.stopped
        self.pipeline: asyncio.Task[dict[str, Any]] | None = None
        self.count = 0

    def begin(self, content: bytes | None = None, *, capture_seconds: int = 3) -> asyncio.Task[dict[str, Any]]:
        policy = self.runner.assist.policy
        if self.stopped.is_set() or (self.pipeline is not None and not self.pipeline.done()):
            msg = "Voice session stopped or already has an active utterance."
            raise ValueError(msg)
        if self.count >= policy.max_actions or datetime.now(UTC) >= policy.expires_at:
            msg = "Voice session utterance budget or deadline exhausted."
            raise ValueError(msg)
        self.supervisor.interrupt_behavior()
        self.count += 1
        self.pipeline = asyncio.create_task(self._utterance(content, capture_seconds), name="blockworld-utterance")
        return self.pipeline

    async def _events(self, run_id: str, identity: str) -> Path:
        services = self.runner.services
        if services is None:
            msg = "Native event assembly is unavailable."
            raise RuntimeError(msg)
        await services.bus.wait_persisted(run_id)
        events = await services.ledger.list_events(run_id, limit=100)
        raw = b"".join(event.model_dump_json().encode() + b"\n" for event in events)
        if len(raw) > _MAX_EVENT_BYTES:
            msg = "Native event evidence exceeds its private file bound."
            raise ValueError(msg)
        path = self.files.root / f"{identity}-events.jsonl"
        self.files.write_new(path, raw)
        return path

    def _require_running(self) -> None:
        if self.stopped.is_set():
            raise asyncio.CancelledError

    async def _behavior_record(self, record: dict[str, Any]) -> None:
        if record["source"] == "operator":
            return  # Its utterance owns the operator evidence and timing receipt.
        identity = str(uuid4())
        run_id = record["run_id"]
        if type(run_id) is str:
            record["events"] = str(await self._events(run_id, identity))
        path = self.files.root / f"{identity}-behavior.json"
        self.files.write_new(path, json.dumps(record).encode())
        if record["source"] != "idle" or record["kind"] != "unchanged":
            _message(json.dumps({"behavior": record["source"], "kind": record["kind"], "evidence": str(path)}))

    async def _start_build(self) -> dict[str, Any]:
        if self.build_plan is None:
            return {"kind": "refused", "detail": "No explicit private build plan supplied.", "run_id": None}
        try:
            await self.supervisor.start_build(self.build_plan)
        except ValueError:
            return {"kind": "refused", "detail": "Build plan or shared session authority refused.", "run_id": None}
        return {
            "kind": "build_started",
            "plan_id": self.build_plan.plan_id,
            "plan_digest": self.build_plan.digest,
            "run_id": None,
        }

    async def _execute(self, transcript: TranscriptObservation, identity: str) -> dict[str, Any]:
        phrase = transcript.text.strip().casefold().rstrip(".!?")
        if phrase in _BUILD_WORDS:
            return await self._start_build()
        if phrase in _IDLE_WORDS | _FOLLOW_WORDS:
            kind = "idle" if phrase in _IDLE_WORDS else "follow"
            try:
                await self.supervisor.start(
                    BehaviorDirective(kind=kind, task_id=identity, duration_s=float(self.behavior_seconds))
                )
            except ValueError:
                return {"kind": "refused", "detail": "Behavior policy or exact target unavailable.", "run_id": None}
            return {"kind": "behavior_started", "behavior": kind, "task_id": identity, "run_id": None}
        try:
            action = parse_text(transcript.text)
        except ValueError:
            return {"kind": "refused", "detail": "Unsupported or ambiguous strict-grammar instruction.", "run_id": None}
        request = AssistRequest(request_id=identity, action=action, transcript=transcript.text, source="transcript")
        evidence: Path | None = None
        try:
            outcome = await self.supervisor.submit_operator(request)
        finally:
            run_id = self.supervisor.run_ids.get(identity)
            if run_id is not None:
                evidence = await self._events(run_id, identity)
                _message(json.dumps({"run_id": run_id, "evidence": str(evidence)}))
        return {"kind": outcome.kind, "detail": outcome.detail, "run_id": run_id, "events": str(evidence)}

    async def _utterance(self, content: bytes | None, seconds: int) -> dict[str, Any]:
        identity = str(uuid4())
        timings: dict[str, float] = {}
        record: dict[str, Any] = {
            "profile_digest": self.speech.profile.digest,
            "native_echo_admission": False,
            "delivery": "experimental_process_local",
            "stage_seconds": timings,
            "disposition": "outcome_unknown",
        }
        try:
            result = await self._pipeline(identity, content, seconds, timings, record)
        except asyncio.CancelledError:
            record["cancellation"] = "cancelled_server_work_unknown"
            if "result" not in record:
                record["disposition"] = "cancelled_server_work_unknown"
            raise
        finally:
            self.files.write_new(self.files.root / f"{identity}-voice.json", json.dumps(record).encode())
        return result

    async def _capture(self, seconds: int) -> bytes:
        """Fence unknown recorder ownership before allowing another physical handoff."""
        _message("CAPTURE ACTIVE: finite utterance; stop/quit interrupts.")
        try:
            content = await capture_utterance(seconds=seconds)
        except asyncio.CancelledError:
            _message("CAPTURE OFF")
            raise
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            if isinstance(error, VoiceCaptureError) and not isinstance(error, VoiceCaptureUnsettled):
                _message("CAPTURE OFF")
            else:
                self.fence()
                _message("CAPTURE RETIREMENT UNKNOWN: session fenced; no further audio admitted.")
            raise
        else:
            _message("CAPTURE OFF")
        return content

    async def _pipeline(
        self, identity: str, content: bytes | None, seconds: int, timings: dict[str, float], record: dict[str, Any]
    ) -> dict[str, Any]:
        settling_started = time.monotonic()
        try:
            await self.supervisor.pause()
        finally:
            record["settlement_seconds"] = time.monotonic() - settling_started
        with _stage(timings, "capture"):
            if content is None:
                content = await self._capture(seconds)
        self._require_running()
        source_path, transcript_path = (
            self.files.root / f"{identity}-source.wav",
            self.files.root / f"{identity}-transcript.json",
        )
        self.files.write_new(source_path, content)
        source = ArtifactRef(
            artifact_id=identity,
            digest=content_digest(content),
            media_type="audio/wav",
            size=len(content),
            classification="private",
        )
        record["source"] = {"path": str(source_path), "digest": source.digest}
        with _stage(timings, "stt"):
            transcript = await self.speech.transcribe(source, content, language=self.language)
        self.files.write_new(transcript_path, transcript.model_dump_json().encode())
        record["transcript"] = str(transcript_path)
        self._require_running()
        if transcript.text.strip().casefold().rstrip(".!?") in _STOP_WORDS:
            await self.stop()
            result = {"kind": "stopped", "native_echo_admission": False}
            self._feedback(result)
            record.update({"result": result, "disposition": "stopped"})
            return result
        with _stage(timings, "graph"):
            result = await self._execute(transcript, identity)
        result.update(
            {
                "source_digest": source.digest,
                "native_echo_admission": False,
                "grammar": "fixed English/Slovak commands and English/Slovak/Czech behaviors; no LLM",
            }
        )
        self._feedback(result)
        result["reply_status"] = "not_requested" if self.reply_language is None else "not_attempted"
        record.update({"result": result, "disposition": result["kind"]})
        with _stage(timings, "tts"):
            audio = await self._reply(result, identity)
        if self.play_replies and audio is not None:
            self._require_running()
            with _stage(timings, "playback"):
                await self._play_reply(result, audio)
        return result

    async def _reply(self, result: dict[str, Any], identity: str) -> bytes | None:
        if self.reply_language is not None and not self.stopped.is_set():
            try:
                facts, audio = await self.speech.synthesize(
                    result["feedback"], language=self.reply_language, voice=self.voice
                )
            except asyncio.CancelledError:
                result["reply_status"] = "cancelled_server_work_unknown"
                raise
            except SpeechProbeError:
                result.update({"reply_status": "failed", "reply_failure": "synthesis_failed"})
                _message(feedback_text({"kind": "synthesis_failed"}, self.feedback_language))
            else:
                path = self.files.root / f"{identity}-reply.wav"
                self.files.write_new(path, audio)
                self.files.write_new(self.files.root / f"{identity}-reply.json", facts.model_dump_json().encode())
                result.update({"reply_status": "generated", "reply_audio": str(path), "playback": "not_attempted"})
                return audio
        return None

    async def _play_reply(self, result: dict[str, Any], audio: bytes) -> None:
        result.update({"playback": "in_progress", "human_hearing": "unconfirmed"})
        _message("PLAYBACK ACTIVE")
        try:
            result["playback"] = await play_reply(audio)
        except asyncio.CancelledError:
            result["playback"] = "interrupted"
            _message("PLAYBACK INTERRUPTED")
            raise
        except VoicePlaybackUnsettled:
            result.update({"playback": "settlement_unknown", "reply_failure": "playback_unsettled"})
            self.fence()
            _message(feedback_text({"kind": "playback_unsettled"}, self.feedback_language))
            await self.stop()
        except VoicePlaybackError:
            result.update({"playback": "failed", "reply_failure": "playback_failed"})
            _message(feedback_text({"kind": "playback_failed"}, self.feedback_language))
        else:
            _message("PLAYBACK FINISHED")

    def _feedback(self, result: dict[str, Any]) -> None:
        result.update(
            {"feedback_language": self.feedback_language, "feedback": feedback_text(result, self.feedback_language)}
        )
        _message(result["feedback"])

    def fence(self) -> None:
        """Prevent any new physical handoff before scheduling async cleanup."""
        self.stopped.set()
        self.supervisor.fence("voice_session_stopped")
        pending = self.pipeline
        if pending is not None and pending is not asyncio.current_task() and not pending.done():
            pending.cancel()

    async def stop(self) -> None:
        """Fence before yielding, then cancel and join local speech and native work."""
        self.fence()
        pending = self.pipeline
        try:
            await self.supervisor.stop()
        finally:
            if pending is not None and pending is not asyncio.current_task():
                await asyncio.gather(pending, return_exceptions=True)


async def console_lines() -> AsyncGenerator[str]:
    """Read bounded Linux stdin via a removable readiness callback, without a thread."""
    loop, queue, buffer = asyncio.get_running_loop(), asyncio.Queue[str | None](maxsize=8), bytearray()
    descriptor = sys.stdin.fileno()

    def ready() -> None:
        chunk = os.read(descriptor, _MAX_CONSOLE_BYTES)
        buffer.extend(chunk)
        while b"\n" in buffer:
            line, _, tail = buffer.partition(b"\n")
            buffer[:] = tail
            value = line.decode("utf-8", errors="replace").strip().casefold()
            if value in _STOP_WORDS:
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait(value)
                loop.remove_reader(descriptor)
                return
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(value)
        if not chunk or len(buffer) > _MAX_CONSOLE_BYTES:
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(None)
            loop.remove_reader(descriptor)

    loop.add_reader(descriptor, ready)
    try:
        while (line := await queue.get()) is not None:
            yield line
    finally:
        loop.remove_reader(descriptor)


def _report(task: asyncio.Task[dict[str, Any]]) -> None:
    try:
        result = task.result()
        keys = ("kind", "run_id", "events", "reply_status", "reply_failure", "reply_audio", "playback")
        _message(json.dumps({key: result[key] for key in keys if key in result}, ensure_ascii=False))
    except asyncio.CancelledError:
        _message("Stopped locally; speech server work may be unknown.")
    except Exception:  # noqa: BLE001 - do not expose private provider or game payloads
        _message("Voice attempt failed; no automatic replay. Inspect private evidence.")


async def interactive(session: VoiceSession, seconds: int) -> None:
    _message("Strict grammar; no LLM. Enter/record captures once; stop/quit ends this session. Microphone OFF.")
    lines = console_lines()
    stopping = asyncio.create_task(session.stopped.wait())
    reading: asyncio.Future[str] | None = None
    try:
        while not session.stopped.is_set():
            reading = asyncio.ensure_future(anext(lines))
            await asyncio.wait({reading, stopping}, return_when=asyncio.FIRST_COMPLETED)
            if stopping.done():
                break
            try:
                line = reading.result()
            except StopAsyncIteration:
                break
            if line in _STOP_WORDS:
                await session.stop()
                break
            if not line or line == "record":
                try:
                    session.begin(capture_seconds=seconds).add_done_callback(_report)
                except ValueError:
                    _message("Session busy, expired or exhausted; no capture started.")
            if session.stopped.is_set():
                break
    finally:
        tasks: list[asyncio.Future[Any]] = [task for task in (reading, stopping) if task is not None]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await lines.aclose()
        await session.stop()


def load_target_binding(files: PrivateWorkspace, path: Path) -> HorizonBinding:
    """Decode one private query binding without granting action authority."""

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                msg = "Duplicate target binding key."
                raise ValueError(msg)
            value[key] = item
        return value

    def invalid(_: str) -> Any:
        msg = "Nonfinite target binding value."
        raise ValueError(msg)

    value = json.loads(files.read(path, MAX_PROFILE_BYTES), object_pairs_hook=unique, parse_constant=invalid)
    if type(value) is not dict:
        msg = "Target profile must contain only its query binding."
        raise ValueError(msg)
    document = cast("dict[str, Any]", value)
    if set(document) != {"binding"} or type(document["binding"]) is not dict:
        msg = "Target profile must contain only its query binding."
        raise ValueError(msg)
    binding = dict(cast("dict[str, Any]", document["binding"]))
    if type(binding.get("endpoint")) is not str:
        msg = "Target binding requires an explicit socket path."
        raise ValueError(msg)
    binding["endpoint"] = Path(binding["endpoint"])
    return HorizonBinding(**binding)


async def _run_input(options: argparse.Namespace, session: VoiceSession, files: PrivateWorkspace) -> None:
    if options.source is not None:
        task = session.begin(files.read(options.source, MAX_INPUT_BYTES))
        result = await task
        _report(task)
        if result["kind"] in {"behavior_started", "build_started"}:
            await session.supervisor.wait_behavior()
    else:
        await interactive(session, options.capture_seconds)


async def operate(options: argparse.Namespace) -> None:
    from lychd.system.services.horizon_control import load_assist_profile

    files = PrivateWorkspace(options.workspace, tuple(options.checkout_root))
    speech = SpeechProbe(load_speech_profile(files.read(options.speech_profile, MAX_PROFILE_BYTES)))
    binding, policy_data, game_workspace = load_assist_profile(options.game_profile)
    if game_workspace != files.root:
        msg = "Speech and game evidence must use the same explicit private workspace."
        raise ValueError(msg)
    control = HorizonControlSession(binding)
    target = (
        HorizonTargetObserver(
            load_target_binding(files, options.target_profile), bot_binding=binding, settle_cancelled_reads=True
        )
        if options.target_profile is not None
        else None
    )
    assist = HorizonAssistService(AssistPolicy.model_validate_json(json.dumps(policy_data)), control)
    behaviors = HorizonBehaviorService(assist, target)
    plan = decode_plan(files.read(options.build_plan, MAX_BUILD_BYTES).decode()) if options.build_plan else None
    builds = HorizonBuildService(assist) if plan is not None else None
    runner = LocalAssistRunner(assist, control, behaviors=behaviors, builds=builds)
    session = VoiceSession(
        files,
        speech,
        runner,
        control,
        language=options.language,
        reply_language=options.reply_language,
        voice=options.voice,
        behavior_seconds=options.behavior_seconds,
        build_plan=plan,
        play_replies=options.play_replies,
    )
    await control.open()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, session.fence)
    try:
        if target is not None:
            await target.open()
        await runner.open()
        await _run_input(options, session, files)
    except asyncio.CancelledError:
        if not session.stopped.is_set():
            raise
        _message("Session stopped; inspect private evidence for completed or unknown effects.")
    finally:
        for signum in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(signum)
        try:
            await session.stop()
        finally:
            try:
                await runner.aclose()
            finally:
                if target is not None:
                    await target.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Explicit engineering voice → fixed grammar → native Horizon Run/Graph."
    )
    for flag in ("speech-profile", "game-profile", "workspace"):
        parser.add_argument(f"--{flag}", required=True, type=Path)
    parser.add_argument("--checkout-root", required=True, action="append", type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source", type=Path, help="One explicit canonical private WAV; no microphone capture.")
    source.add_argument(
        "--capture-seconds", type=int, choices=range(1, 16), help="Enter-to-record interactive session."
    )
    parser.add_argument(
        "--language", help="Declared STT language; required by whisper.cpp, optional for audio.cpp detection."
    )
    parser.add_argument(
        "--reply-language",
        choices=REPLY_LANGUAGES,
        help="Generate a private reply WAV; playback is separately selected.",
    )
    parser.add_argument(
        "--play-replies", action="store_true", help="Opt in to finite local reply playback after capture."
    )
    parser.add_argument("--voice", choices=STOCK_VOICES, default="M1")
    parser.add_argument("--behavior-seconds", type=int, choices=range(1, _MAX_BEHAVIOR_SECONDS + 1), default=30)
    parser.add_argument(
        "--target-profile", type=Path, help="Private query-only exact-person binding; remote follow only."
    )
    parser.add_argument(
        "--build-plan", type=Path, help="Private frozen one/three-cell plan; exact voice phrase admits it once."
    )
    options = parser.parse_args()
    if options.play_replies and options.reply_language is None:
        parser.error("--play-replies requires --reply-language")
    try:
        asyncio.run(operate(options))
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except Exception:  # noqa: BLE001 - private payloads must not enter CLI tracebacks
        sys.stderr.write("Voice session failed or outcome unknown; no replay. Inspect private evidence.\n")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
