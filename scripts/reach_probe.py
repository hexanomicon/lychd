"""Run one private, headless Reach turn through the networkless native OCI worker.

Only the audience plan-delivery receipt is simulated. Cognition and document
reads remain in the worker; the existing host broker contacts the fixed local
Qwen endpoint. No Discord connection, web acquisition or model lifecycle control occurs.
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import signal
import sys
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, NoReturn, cast
from uuid import uuid4

from pydantic import Field

from lychd.compositions.reach.documents import (
    LEGACY_MAX_CORPUS_BYTES,
    MAX_CORPUS_BYTES,
    MAX_CORPUS_MANIFEST_BYTES,
    MAX_DOCUMENT_BYTES,
    PublicCorpus,
    parse_corpus_manifest,
    read_research_document,
    verify_corpus,
)
from lychd.compositions.reach.expressions import GifId
from lychd.compositions.reach.operator_diagnostics import parse_diagnostic
from lychd.compositions.reach.operator_model_wire import (
    OperatorConversationProfile,
    OperatorModelRequest,
    OperatorModelResponse,
    validate_generation_payload,
)
from lychd.compositions.reach.operator_observation import ReachPatternObservation
from lychd.compositions.reach.operator_trace import ReachTraceEvent, TraceCorrelation
from lychd.compositions.reach.operator_wire import (
    MAX_WIRE_BYTES,
    ReachHistoryEntry,
    ReachWorkerReady,
    ReachWorkerRequest,
    ReachWorkerResult,
    ReachWorkerStatus,
    protocol_bytes,
    strict_json,
)
from lychd.compositions.reach.research_wire import OperatorResearchRequest, OperatorResearchResponse, SourceId
from lychd.compositions.reach.schemas import ReachEvent, ReachPolicy, ReachRule, Record

if __package__:
    from scripts import reach_operator as operator
    from scripts.reach_model_broker import OperatorModelBroker
    from scripts.reach_podman_model import PodmanModelTransport
    from scripts.reach_trace_archive import TraceArchive
    from scripts.reach_trace_capture import TraceCapture
else:
    import reach_operator as operator
    from reach_model_broker import OperatorModelBroker
    from reach_podman_model import PodmanModelTransport
    from reach_trace_archive import TraceArchive
    from reach_trace_capture import TraceCapture

MAX_STDOUT_FRAMES = 64
MAX_DIAGNOSTIC_FRAMES = 2048
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_MODEL_CALLS = 12
MAX_DEBUG_CHARS = 24_000
MAX_TIMEOUT_SECONDS = 480
SYNTHETIC = {
    "platform": "discord",
    "account_id": "900000000000000001",
    "agent_subject_id": "900000000000000002",
    "space_id": "900000000000000003",
    "conversation_id": "900000000000000004",
    "subject_id": "900000000000000005",
    "event_id": "900000000000000006",
}


class ProbeError(ValueError):
    """A fixed local code, never a rendered provider or persona exception."""


def refuse(code: str) -> NoReturn:
    raise ProbeError(code)


class HistoryItem(Record):
    text: str = Field(min_length=1, max_length=2000, repr=False)
    speaker: Literal["operator", "agent"] = "operator"
    age_seconds: int = Field(default=1, ge=1, le=600)


class Scenario(Record):
    """One bounded private question and optional assertions about observable results."""

    question: str = Field(min_length=1, max_length=2000, repr=False)
    direct: bool = False
    history: tuple[HistoryItem, ...] = Field(default=(), max_length=20, repr=False)
    plan_delivery: Literal["succeeded", "rejected", "unknown"] = "succeeded"
    expected_status: ReachWorkerStatus | None = None
    required_source_ids: tuple[SourceId, ...] = Field(default=(), max_length=4)
    expected_gif_id: GifId | None = None


def make_request(scenario: Scenario, now: datetime) -> tuple[ReachPolicy, ReachWorkerRequest]:
    """Bind synthetic identities explicitly, including a distinct opted-in DM place."""
    place = "900000000000000007" if scenario.direct else SYNTHETIC["conversation_id"]
    policy = ReachPolicy(
        platform="discord",
        account_id=SYNTHETIC["account_id"],
        agent_subject_id=SYNTHETIC["agent_subject_id"],
        space_id=SYNTHETIC["space_id"],
        allowed_conversation_ids=(SYNTHETIC["conversation_id"],),
        allowed_direct_subject_ids=(SYNTHETIC["subject_id"],),
        rules=(ReachRule(name="headless_probe", subject_ids=(SYNTHETIC["subject_id"],), actions=("converse",)),),
        context_message_limit=20,
        context_max_age_seconds=600,
        event_ttl_seconds=600,
    )
    event = ReachEvent(
        platform="discord",
        account_id=SYNTHETIC["account_id"],
        event_id=SYNTHETIC["event_id"],
        space_id=None if scenario.direct else SYNTHETIC["space_id"],
        conversation_id=place,
        subject_id=SYNTHETIC["subject_id"],
        subject_label="Probe operator",
        mention_subject_ids=() if scenario.direct else (SYNTHETIC["agent_subject_id"],),
        trigger="message" if scenario.direct else "mention",
        action="converse",
        question=scenario.question,
        occurred_at=now,
    )
    history = tuple(
        ReachHistoryEntry(
            subject_id=SYNTHETIC["agent_subject_id" if item.speaker == "agent" else "subject_id"],
            subject_label="Probe agent" if item.speaker == "agent" else "Probe operator",
            event_id=str(900000000000000100 + index),
            conversation_id=place,
            text=item.text,
            occurred_at=now - timedelta(seconds=item.age_seconds),
        )
        for index, item in enumerate(scenario.history)
    )
    return policy, ReachWorkerRequest(request_id=str(uuid4()), event=event, history=history)


def freeze_corpus(directory: Path, output: Path) -> PublicCorpus:
    """Verify the entire selected export, then mount only its detached exact bytes."""
    operator.external_path(directory)
    raw = operator.read_regular(directory / "manifest.json", MAX_CORPUS_MANIFEST_BYTES)
    manifest = parse_corpus_manifest(raw)
    contents: list[bytes] = []
    total = 0
    limit = LEGACY_MAX_CORPUS_BYTES if manifest.schema_version == 1 else MAX_CORPUS_BYTES
    for item in manifest.documents:
        raw_document = operator.read_regular(directory / item.file, MAX_DOCUMENT_BYTES)
        total += len(raw_document)
        if total > limit:
            refuse("probe_corpus_budget")
        contents.append(raw_document)
    corpus = verify_corpus(manifest, tuple(contents))
    operator.private_directory(output)
    operator.write_private(output / "manifest.json", raw)
    for item, content in zip(manifest.documents, contents, strict=True):
        operator.write_private(output / item.file, content)
    return corpus


def object_value(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        refuse("probe_protocol")
    return cast("dict[str, Any]", value)


class Turn:
    """One finite protocol state machine; it cannot invent acquisition evidence."""

    def __init__(
        self,
        scenario: Scenario,
        policy: ReachPolicy,
        request: ReachWorkerRequest,
        profile: OperatorConversationProfile,
        corpus: PublicCorpus,
        archive: TraceArchive,
        *,
        capture_model_output: bool = False,
    ) -> None:
        """Pin inputs and archive custody before the child is started."""
        self.scenario, self.policy, self.request = scenario, policy, request
        self.profile, self.corpus = profile, corpus
        self.archive = archive
        self.events: list[ReachTraceEvent] = []
        self.trace_failed = False
        self.capture = TraceCapture(
            self.observe, source_ids=frozenset(f"doc:{d.path}" for d in corpus.manifest.documents)
        )
        self.capture_model_output = capture_model_output
        self.ready: ReachWorkerReady | None = None
        self.result: ReachWorkerResult | None = None
        self.run_id: str | None = None
        self.plan: str | None = None
        self.proposed_plan: str | None = None
        self.plan_call_id: str | None = None
        self.planned_ids: tuple[str, ...] = ()
        self.offered_ids: frozenset[str] = frozenset()
        self.reads: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []
        self.debug: list[str] = []
        self.synthesis = 0
        self.total_bytes = 0
        self.stdout_frames = 0
        self.diagnostic_frames = 0
        self.unstructured_diagnostics = 0
        self.seen_call_ids: set[str] = set()
        self.patterns: dict[str, Any] | None = None
        self.cleanup: dict[str, Any] = {"process_retired": False, "container_removed": False, "container_id": None}
        self.projection: dict[str, Any] = {}

    def observe(self, event: ReachTraceEvent) -> None:
        """Retain finite structural metadata independently of best-effort emitter semantics."""
        if len(self.events) >= MAX_DIAGNOSTIC_FRAMES or (
            event.producer == "core"
            and event.source_id is not None
            and event.source_id not in (self.capture.source_ids or frozenset())
        ):
            self.trace_failed = True
            return
        if (
            event.producer == "core"
            and event.name == "source_read"
            and (
                self.plan is None
                or self.scenario.plan_delivery != "succeeded"
                or event.request_id != self.request.request_id
                or event.run_id != self.run_id
            )
        ):
            self.trace_failed = True
        self.events.append(event)
        self.archive.emit(event)

    def correlation(self, value: TraceCorrelation | None) -> dict[str, Any]:
        if (
            value is None
            or self.ready is None
            or value.generation != self.ready.generation
            or value.request_id != self.request.request_id
            or (self.run_id is not None and self.run_id != value.run_id)
        ):
            refuse("probe_correlation")
        self.run_id = value.run_id
        return value.model_dump(exclude_none=True)

    def model_prompt(self, frame: OperatorModelRequest) -> dict[str, Any]:
        generation = validate_generation_payload(self.profile, frame.payload_json)
        messages = cast("list[dict[str, Any]]", generation["messages"])
        return object_value(strict_json(cast("str", messages[-1]["content"]).encode()))

    def before_model(self, frame: OperatorModelRequest) -> dict[str, Any]:
        """Require the native planning/ack/read/synthesis order before any local inference."""
        if len(self.calls) >= MAX_MODEL_CALLS or frame.call_id in self.seen_call_ids:
            refuse("probe_model_budget")
        if frame.binding_digest != self.profile.digest:
            refuse("probe_binding")
        if self.ready is None:
            if frame.operation != "probe" or frame.correlation is not None or self.calls:
                refuse("probe_bootstrap_binding")
        else:
            self.correlation(frame.correlation)
        self.seen_call_ids.add(frame.call_id)
        prompt: dict[str, Any] = {}
        phase = "probe"
        if frame.operation == "generate":
            prompt = self.model_prompt(frame)
            phase = self.generation_phase(prompt)
        self.calls.append({"call_id": frame.call_id, "operation": frame.operation, "phase": phase})
        return prompt

    def generation_phase(self, prompt: dict[str, Any]) -> str:
        phase = str(prompt.get("research_phase", "answer"))
        if prompt.get("question") != self.request.event.question:
            refuse("probe_question_binding")
        if phase == "synthesis":
            self.capture_synthesis(prompt)
        elif self.plan is not None or phase not in {"planning", "answer"}:
            refuse("probe_phase")
        else:
            offered = prompt.get("available_research_sources", [])
            if not isinstance(offered, list):
                refuse("probe_catalogue")
            self.offered_ids = frozenset(str(object_value(item).get("id")) for item in cast("list[Any]", offered))
        return phase

    def capture_synthesis(self, prompt: dict[str, Any]) -> None:
        if (
            self.plan is None
            or self.scenario.plan_delivery != "succeeded"
            or self.synthesis
            or prompt.get("research_request_id") != self.request.request_id
            or prompt.get("research_plan") != self.plan
            or prompt.get("corpus_digest") != self.corpus.digest
        ):
            refuse("probe_synthesis_binding")
        self.synthesis += 1
        sources = prompt.get("research_sources")
        if not isinstance(sources, list):
            refuse("probe_source_metadata")
        records = [object_value(item) for item in cast("list[Any]", sources)]
        if tuple(item.get("id") for item in records) != self.planned_ids:
            refuse("probe_source_binding")
        self.reads.extend(self.read_projection(item) for item in records)
        omitted = prompt.get("omitted_recent_messages")
        if type(omitted) is not int or not 0 <= omitted <= len(self.request.history):
            refuse("probe_history_metadata")
        self.projection = {"omitted_recent_messages": omitted, "source_count": len(records)}

    def read_projection(self, item: dict[str, Any]) -> dict[str, Any]:
        """Verify exact metadata and the actual transient projection against frozen source bytes."""
        source_id = item.get("id")
        if not isinstance(source_id, str) or not source_id.startswith("doc:"):
            refuse("probe_web_refused")
        source = read_research_document(self.corpus, source_id, question=self.request.event.question)
        expected = source.model_dump(mode="json", exclude={"text"})
        text = item.get("text")
        if (
            not isinstance(text, str)
            or not source.text.startswith(text)
            or {key: item.get(key) for key in expected} != expected
            or item.get("projection_digest") != sha256(text.encode()).hexdigest()
            or type(item.get("projection_truncated")) is not bool
            or item["projection_truncated"] != (len(text) < len(source.text))
        ):
            refuse("probe_source_metadata")
        return {
            **expected,
            "projection_digest": item["projection_digest"],
            "projection_truncated": item["projection_truncated"],
            "projected_chars": len(text),
        }

    def after_model(self, frame: OperatorModelRequest, response: OperatorModelResponse) -> None:
        self.calls[-1].update({"status": response.status, "reason": response.reason})
        if response.status != "ok" or frame.operation != "generate":
            return
        value = object_value(strict_json(response.payload_json.encode()))
        choices = cast("list[dict[str, Any]]", value["choices"])
        content = cast("str", choices[0]["message"]["content"])
        if self.capture_model_output:
            if sum(map(len, self.debug)) + len(content) > MAX_DEBUG_CHARS:
                refuse("probe_debug_budget")
            self.debug.append(content)
        try:
            decision = object_value(strict_json(content.encode()))
        except (ValueError, UnicodeError, RecursionError):
            return  # Native validation owns model output; no permissive repair here.
        if decision.get("kind") == "research":
            ids = decision.get("source_ids")
            if isinstance(ids, list) and all(isinstance(item, str) for item in cast("list[Any]", ids)):
                self.planned_ids = tuple(cast("list[str]", ids))
                self.calls[-1]["selected_source_ids"] = self.planned_ids
                text = decision.get("text")
                self.proposed_plan = text.strip() if isinstance(text, str) else None

    def research(self, frame: OperatorResearchRequest) -> OperatorResearchResponse:
        """Simulate exactly one audience receipt; never pretend to acquire web material."""
        binding = self.correlation(frame.correlation)
        if (
            frame.binding_digest != self.profile.digest
            or frame.request_id != self.request.request_id
            or frame.event != self.request.event
            or frame.call_id in self.seen_call_ids
            or self.plan is not None
            or frame.plan != self.proposed_plan
            or not self.planned_ids
            or any(item not in self.offered_ids for item in self.planned_ids)
        ):
            refuse("probe_research_binding")
        self.seen_call_ids.add(frame.call_id)
        self.plan, self.plan_call_id = frame.plan, frame.call_id
        self.capture.host.record("research_plan", status=self.scenario.plan_delivery, call_id=frame.call_id, **binding)
        web = frame.source_ids or any(not item.startswith("doc:") for item in self.planned_ids)
        accepted = self.scenario.plan_delivery == "succeeded" and not web
        response = OperatorResearchResponse(
            call_id=frame.call_id,
            request_id=frame.request_id,
            binding_digest=frame.binding_digest,
            status="ok" if accepted else "refused",
            reason=None if accepted else "probe_web_refused" if web else "probe_plan_not_delivered",
        )
        self.capture.host.record("research_call", status=response.status, call_id=frame.call_id, **binding)
        if web:
            refuse("probe_web_refused")
        return response

    def accept_ready(self, ready: ReachWorkerReady) -> None:
        """Stamp the synthetic invocation after worker startup while retaining its request identity."""
        if self.ready is not None or (
            ready.policy_digest,
            ready.corpus_digest,
            ready.model_binding_digest,
            ready.adaptive_context,
            ready.research_enabled,
            ready.expressions,
        ) != (
            self.policy.digest,
            self.corpus.digest,
            self.profile.digest,
            self.profile.adaptive_context,
            self.profile.research.enabled,
            self.profile.expressions,
        ):
            refuse("probe_ready_binding")
        if self.patterns is not None and self.patterns["generation"] != ready.generation:
            refuse("probe_pattern_binding")
        policy, request = make_request(self.scenario, max(datetime.now(UTC), ready.started_at))
        if policy.digest != self.policy.digest:
            refuse("probe_policy_binding")
        self.request = request.model_copy(update={"request_id": self.request.request_id})
        self.ready = ready
        self.capture.ready(ready)

    def accept_result(self, result: ReachWorkerResult) -> None:
        if (
            self.ready is None
            or self.result is not None
            or result.request_id != self.request.request_id
            or result.policy_digest != self.policy.digest
            or result.corpus_digest != self.corpus.digest
            or result.model_binding_digest != self.profile.digest
            or (self.run_id is not None and result.run_id != self.run_id)
        ):
            refuse("probe_result_binding")
        self.result = result
        self.capture.result(result)

    def account(self, raw: bytes, *, diagnostic: bool) -> None:
        self.total_bytes += len(raw)
        if diagnostic:
            self.diagnostic_frames += 1
        else:
            self.stdout_frames += 1
        if (
            len(raw) > MAX_WIRE_BYTES
            or self.total_bytes > MAX_TOTAL_BYTES
            or self.stdout_frames > MAX_STDOUT_FRAMES
            or self.diagnostic_frames > MAX_DIAGNOSTIC_FRAMES
        ):
            refuse("probe_frame_budget")

    async def diagnostics(self, reader: asyncio.StreamReader) -> None:
        """Consume Core-only typed observations; foreign stderr never enters artifacts."""
        while raw := await read_line(reader):
            self.account(raw, diagnostic=True)
            if not raw.startswith(b"{"):
                self.unstructured_diagnostics += 1
                continue
            value = object_value(strict_json(raw))
            if value.get("kind") == "reach_trace":
                event = ReachTraceEvent.model_validate_json(raw)
                if event.producer != "core":
                    refuse("probe_trace_custody")
                if event.request_id is not None and event.request_id != self.request.request_id:
                    refuse("probe_trace_binding")
                self.capture.child(event, "core")
            elif value.get("kind") == "operation_observation":
                # Existing typed parser verifies this metadata without retaining foreign fields.
                if not operator.capture_structured(raw, "core", self.capture):
                    refuse("probe_diagnostic_protocol")
            else:
                parse_diagnostic(raw)

    def oracle(self) -> list[str]:
        """Judge explicit scenario assertions independently from native Run success."""
        failures = self.result_assertions()
        failures.extend(self.evidence_assertions())
        return failures

    def result_assertions(self) -> list[str]:
        failures: list[str] = []
        result = self.result
        if result is None:
            failures.append("missing_result")
        elif self.scenario.expected_status is not None and result.status != self.scenario.expected_status:
            failures.append("expected_status")
        elif (
            self.scenario.expected_status is None
            and result.status in {"error", "refused"}
            and (self.scenario.plan_delivery == "succeeded" or self.plan is None)
        ):
            failures.append("native_failure")
        if self.scenario.expected_gif_id is not None and (
            result is None or result.gif_id != self.scenario.expected_gif_id
        ):
            failures.append("expected_gif_id")
        read_ids = {item.source_id for item in self.events if item.name == "source_read" and item.status == "ok"}
        if not set(self.scenario.required_source_ids) <= read_ids:
            failures.append("required_source_ids")
        return failures

    def evidence_assertions(self) -> list[str]:
        failures: list[str] = []
        if self.scenario.plan_delivery != "succeeded":
            if self.plan is None:
                failures.append("missing_plan")
            if self.reads or self.synthesis or any(item.name == "source_read" for item in self.events):
                failures.append("read_before_delivery")
        if any(item.get("status") != "ok" for item in self.calls):
            failures.append("model_unavailable")
        if not any(item["operation"] == "generate" for item in self.calls):
            failures.append("missing_real_generation")
        if self.trace_failed:
            failures.append("trace_budget")
        if self.ready is not None and any(
            (item.generation is not None and item.generation != self.ready.generation)
            or (item.run_id is not None and item.run_id != (self.result.run_id if self.result else self.run_id))
            or (item.request_id is not None and item.request_id != self.request.request_id)
            for item in self.events
            if item.producer == "core"
        ):
            failures.append("trace_binding")
        if self.patterns is None or not any(item.name == "native_node" for item in self.events):
            failures.append("missing_native_trace")
        return failures


async def read_line(reader: asyncio.StreamReader) -> bytes:
    try:
        return await reader.readuntil(b"\n")
    except asyncio.IncompleteReadError as error:
        if error.partial:
            refuse("probe_truncated_frame")
        return b""
    except asyncio.LimitOverrunError:
        refuse("probe_frame_budget")


async def worker_response(
    turn: Turn, raw: bytes, writer: asyncio.StreamWriter, broker: OperatorModelBroker
) -> bytes | None:
    """Handle one closed worker control frame after the outer exchange admits its budget and phase."""
    kind = object_value(strict_json(raw)).get("kind")
    if kind == "reach_pattern_observation":
        if turn.patterns is not None or turn.ready is not None:
            refuse("probe_pattern_order")
        turn.patterns = ReachPatternObservation.model_validate_json(raw).model_dump(mode="json")
    elif kind == "ready":
        turn.accept_ready(ReachWorkerReady.model_validate_json(raw))
        turn.capture.request(turn.request)
        return protocol_bytes(turn.request)
    elif kind == "model_request":
        frame = OperatorModelRequest.model_validate_json(raw)
        turn.before_model(frame)
        model = await broker.handle(frame)
        turn.after_model(frame, model)
        return model.model_dump_json().encode() + b"\n"
    elif kind == "research_request":
        return turn.research(OperatorResearchRequest.model_validate_json(raw)).model_dump_json().encode() + b"\n"
    elif kind == "result":
        turn.accept_result(ReachWorkerResult.model_validate_json(raw))
        writer.close()
    else:
        refuse("probe_core_frame")
    return None


async def exchange(turn: Turn, process: asyncio.subprocess.Process, broker: OperatorModelBroker) -> None:
    if process.stdin is None or process.stdout is None:
        refuse("probe_child_pipe")
    while raw := await read_line(process.stdout):
        turn.account(raw, diagnostic=False)
        if turn.result is not None:
            refuse("probe_after_result")
        response = await worker_response(turn, raw, process.stdin, broker)
        if response is not None:
            turn.account(response, diagnostic=False)
            process.stdin.write(response)
            await process.stdin.drain()
    if turn.result is None:
        refuse("probe_core_eof")


async def finish_task[T](task: asyncio.Task[T]) -> tuple[T, bool]:
    """Join an owned operation through repeated cancellation without abandoning its handle."""
    interrupted = False
    while True:
        try:
            return await asyncio.shield(task), interrupted
        except asyncio.CancelledError:
            interrupted = True
            if task.done():
                return task.result(), interrupted


async def cleanup_owned(
    turn: Turn, process: asyncio.subprocess.Process | None, cidfile: Path, engine: str, tasks: list[asyncio.Task[Any]]
) -> None:
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    try:
        if process is not None:
            await operator.retire(process)
        turn.cleanup["process_retired"] = True
    finally:
        try:
            if await asyncio.to_thread(cidfile.exists):
                identity = (await asyncio.to_thread(operator.read_regular, cidfile, 128)).decode("ascii").strip()
                if operator.CONTAINER_ID.fullmatch(identity) is None:
                    refuse("probe_container_identity")
                turn.cleanup["container_id"] = identity
            elif process is not None:
                refuse("probe_container_identity_missing")
            await operator.remove_owned(engine, cidfile)
            turn.cleanup["container_removed"] = True
        finally:
            if not turn.cleanup["process_retired"] or not turn.cleanup["container_removed"]:
                turn.cleanup["retained_workspace"] = str(cidfile.parent)


async def supervise(
    turn: Turn, arguments: list[str], cidfile: Path, *, engine: str, model_transport: str, budget_seconds: float
) -> None:
    """Retire the one owned process and exact CID on every terminal path, without retries."""
    process: asyncio.subprocess.Process | None = None
    tasks: list[asyncio.Task[Any]] = []
    loop = asyncio.get_running_loop()
    current = asyncio.current_task()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, current.cancel if current is not None else lambda: None)
    try:
        async with asyncio.timeout(budget_seconds):
            spawning = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    *arguments,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    limit=MAX_WIRE_BYTES,
                    env=operator.safe_environment(engine),
                )
            )
            try:
                spawned = await asyncio.shield(spawning)
                process = spawned
            except asyncio.CancelledError:
                # A successful OS spawn must never lose its process handle at cancellation.
                process, _interrupted = await finish_task(spawning)
                raise
            if spawned.stderr is None:
                refuse("probe_child_pipe")
            broker = OperatorModelBroker(
                turn.profile,
                transport=PodmanModelTransport() if model_transport == "podman" else None,
                trace=turn.capture.host,
            )
            tasks = [
                asyncio.create_task(exchange(turn, spawned, broker)),
                asyncio.create_task(turn.diagnostics(spawned.stderr)),
            ]
            await asyncio.gather(*tasks)
            if await spawned.wait() != 0:
                refuse("probe_core_exit")
    finally:
        cleanup = asyncio.create_task(cleanup_owned(turn, process, cidfile, engine, tasks))
        try:
            _settled, interrupted = await finish_task(cleanup)
            if interrupted:
                raise asyncio.CancelledError
        finally:
            for signum in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(signum)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        self.exit(2, "reach_probe_arguments_refused\n")


def parser() -> argparse.ArgumentParser:
    result = Parser(description=__doc__)
    result.add_argument("--engine", choices=("docker", "podman"), required=True)
    result.add_argument("--core-image", required=True)
    result.add_argument("--conversation-profile", type=Path, required=True)
    result.add_argument("--corpus-dir", type=Path, required=True)
    result.add_argument("--scenario", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--model-transport", choices=("podman", "http"), default="podman")
    result.add_argument("--timeout-seconds", type=int, default=420)
    result.add_argument("--capture-model-output", action="store_true")
    return result


def render_report(report: dict[str, Any], turn: Turn) -> bytes:
    rows = [
        "# Headless Reach probe",
        "",
        f"Outcome: {report['outcome']}",
        f"Native Run: `{report['run_id'] or 'unobserved'}`",
        "",
        "## Native station observations",
        "",
        "| Native sequence | Station | Observation |",
        "| --- | --- | --- |",
    ]
    native = sorted(
        (event for event in turn.events if event.producer == "core" and event.name == "native_node"),
        key=lambda event: (event.native_seq is None, event.native_seq or 0, event.trace_seq),
    )
    rows.extend(
        f"| {event.native_seq if event.native_seq is not None else 'unknown'} | `{event.node}` | {event.status} |"
        for event in native
    )
    rows += ["", "## Model calls in host order", "", "| Call | Status |", "| --- | --- |"]
    rows.extend(f"| {call['operation']} ({call['phase']}) | {call.get('status', 'unknown')} |" for call in turn.calls)
    rows += ["", "## Source and receipt evidence", "", "| Evidence | Status |", "| --- | --- |"]
    if turn.plan is not None:
        rows.append(f"| Synthetic audience plan receipt | {turn.scenario.plan_delivery} |")
    rows.extend(
        f"| Acquired `{event.source_id}` | {event.status} |" for event in turn.events if event.name == "source_read"
    )
    rows.extend(f"| Synthesis projection `{item['id']}` | {item['status']} |" for item in turn.reads)
    rows += [
        f"| Native result | {turn.result.status if turn.result else 'missing'} |",
        "",
        "The plan receipt is synthetic. This probe uses the native OCI worker and fixed local model broker.",
        "Each table keeps its own ordering domain; source projections are captured as metadata only.",
        "This report does not qualify live Discord delivery, web acquisition or the complete host broker.",
        "Source bodies and persona/provider payloads are excluded. See turn.json for the plan and answer.",
        "",
    ]
    return "\n".join(rows).encode()


@contextmanager
def workspace(directory: Path, cleanup: dict[str, Any]) -> Generator[Path]:
    """Keep the exact CID and frozen inputs if retirement or removal remains uncertain."""
    frozen = Path(tempfile.mkdtemp(prefix="input-", dir=directory))
    try:
        yield frozen
    finally:
        if cleanup.get("process_retired") is True and cleanup.get("container_removed") is True:
            shutil.rmtree(frozen)


def execute(args: argparse.Namespace) -> int:
    """Freeze selected inputs outside Git and publish owner-only inspection artifacts."""
    if not 1 <= args.timeout_seconds <= MAX_TIMEOUT_SECONDS or operator.IMAGE_ID.fullmatch(args.core_image) is None:
        refuse("probe_arguments")
    operator.external_path(args.output)
    if args.output.exists():
        refuse("probe_output_exists")
    profile_raw = operator.read_regular(args.conversation_profile, MAX_WIRE_BYTES, private=True)
    strict_json(profile_raw)
    profile = OperatorConversationProfile.model_validate_json(profile_raw)
    scenario_raw = operator.read_regular(args.scenario, MAX_WIRE_BYTES, private=True)
    strict_json(scenario_raw)
    scenario = Scenario.model_validate_json(scenario_raw)
    operator.private_directory(args.output)
    cleanup: dict[str, Any] = {"process_retired": True, "container_removed": True, "container_id": None}
    with workspace(args.output, cleanup) as frozen:
        corpus = freeze_corpus(args.corpus_dir, frozen / "corpus")
        if any(
            item not in {f"doc:{d.path}" for d in corpus.manifest.documents} for item in scenario.required_source_ids
        ):
            refuse("probe_expected_source")
        if scenario.expected_gif_id is not None:
            profile.expressions.validate_selection(None, scenario.expected_gif_id)
        policy, request = make_request(scenario, datetime.now(UTC))
        operator.write_private(frozen / "policy.json", policy.model_dump_json().encode())
        operator.write_private(frozen / "conversation.json", profile.model_dump_json().encode())
        cidfile = frozen / "core.cid"
        arguments = operator.container_arguments(args.engine, args.core_image, cidfile, offline=True)
        arguments += operator.bind(frozen / "policy.json", "/run/reach/policy.json")
        arguments += operator.bind(frozen / "conversation.json", "/run/reach/conversation.json")
        arguments += operator.bind(frozen / "corpus", "/run/reach/corpus")
        arguments += [
            "--entrypoint",
            "python",
            args.core_image,
            "/work/scripts/reach_worker.py",
            "--policy",
            "/run/reach/policy.json",
            "--corpus-dir",
            "/run/reach/corpus",
            "--conversation-profile",
            "/run/reach/conversation.json",
        ]
        archive = TraceArchive(args.output / "traces")
        turn = Turn(scenario, policy, request, profile, corpus, archive, capture_model_output=args.capture_model_output)
        cleanup.update({"process_retired": False, "container_removed": False})
        turn.cleanup = cleanup
        health, failures = run_turn(turn, args, arguments, cidfile)
        return publish_reports(args, turn, profile_raw, scenario_raw, health, failures)


def run_turn(
    turn: Turn, args: argparse.Namespace, arguments: list[str], cidfile: Path
) -> tuple[dict[str, int | bool], list[str]]:
    archive = turn.archive
    error: str | None = None
    try:
        asyncio.run(
            supervise(
                turn,
                arguments,
                cidfile,
                engine=args.engine,
                model_transport=args.model_transport,
                budget_seconds=args.timeout_seconds,
            )
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        error = "probe_cancelled"
    except TimeoutError:
        error = "probe_timeout"
    except ProbeError as failure:
        error = str(failure)
    except Exception:  # noqa: BLE001 - exception values may contain private provider/persona bytes
        error = "probe_failed"
    finally:
        turn.capture.close(0 if error is None else 1)
        flushed = archive.flush()
        closed = archive.close()
    health = archive.health()
    failures = turn.oracle()
    if not flushed or not closed or health["dropped_total"] or health["write_failures"]:
        failures.append("trace_archive_failed")
    if error is not None:
        failures.append(error)
    return health, failures


def publish_reports(
    args: argparse.Namespace,
    turn: Turn,
    profile_raw: bytes,
    scenario_raw: bytes,
    health: dict[str, int | bool],
    failures: list[str],
) -> int:
    profile, corpus, policy, request, scenario = turn.profile, turn.corpus, turn.policy, turn.request, turn.scenario
    report = {
        "schema_version": 1,
        "outcome": "passed" if not failures else "failed",
        "failures": failures,
        "core_image": args.core_image,
        "engine": args.engine,
        "model_transport": args.model_transport,
        "model_id": profile.model_id,
        "profile_digest": profile.digest,
        "profile_file_sha256": sha256(profile_raw).hexdigest(),
        "scenario_file_sha256": sha256(scenario_raw).hexdigest(),
        "corpus_digest": corpus.digest,
        "corpus_manifest": corpus.manifest.model_dump(mode="json"),
        "policy_digest": policy.digest,
        "synthetic_policy": policy.model_dump(mode="json"),
        "synthetic_event_identity": {
            **SYNTHETIC,
            "conversation_id": request.event.conversation_id,
            "space_id": request.event.space_id,
        },
        "audience_plan_receipt": {
            "synthetic": True,
            "status": scenario.plan_delivery,
            "observed": turn.plan is not None,
            "call_id": turn.plan_call_id,
        },
        "request_id": request.request_id,
        "run_id": turn.result.run_id if turn.result else turn.run_id,
        "generation": turn.ready.generation if turn.ready else None,
        "model_calls": turn.calls,
        "real_model_generation_succeeded": any(
            call["operation"] == "generate" and call.get("status") == "ok" for call in turn.calls
        ),
        "native_run_observed": any(item.name == "run_started" for item in turn.events),
        "source_read_count": sum(item.name == "source_read" for item in turn.events),
        "source_projection_capture": "metadata_only",
        "trace_archive_health": health,
        "unstructured_diagnostic_lines": turn.unstructured_diagnostics,
        "cleanup": turn.cleanup,
        "limits": {
            "timeout_seconds": args.timeout_seconds,
            "model_calls": MAX_MODEL_CALLS,
            "stdout_frames": MAX_STDOUT_FRAMES,
            "diagnostic_frames": MAX_DIAGNOSTIC_FRAMES,
            "frame_bytes": MAX_WIRE_BYTES,
            "total_bytes": MAX_TOTAL_BYTES,
        },
        "claims": {"live_discord": False, "web_acquisition": False, "full_host_broker": False},
    }
    value: dict[str, Any] = {
        "plan": turn.plan,
        "selected_source_ids": turn.planned_ids,
        "source_reads": turn.reads,
        "synthesis_projection": turn.projection,
        "acquisition_source_reads": [
            item.model_dump(mode="json", exclude_none=True) for item in turn.events if item.name == "source_read"
        ],
        "result": turn.result.model_dump(mode="json") if turn.result else None,
        "patterns": turn.patterns,
    }
    if args.capture_model_output:
        value["model_decision_texts"] = turn.debug
    operator.write_private(args.output / "turn.json", operator.json_bytes(value))
    operator.write_private(args.output / "report.json", operator.json_bytes(report))
    operator.write_private(args.output / "report.md", render_report(report, turn))
    return 0 if not failures else 1


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return execute(args)
    except (KeyboardInterrupt, asyncio.CancelledError):
        sys.stderr.write("reach_probe_cancelled\n")
        return 130
    except Exception:  # noqa: BLE001 - ordinary errors never render selected private input or provider bodies
        sys.stderr.write("reach_probe_refused\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
